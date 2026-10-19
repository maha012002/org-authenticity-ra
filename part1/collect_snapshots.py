"""Part 1, step 1: collect one archived "About Us" snapshot per company-year (2016-2024)
from the Wayback Machine CDX API.

Selection rules (also documented in part1/README.md):
  * Candidate URLs per company come from config/about_url_seeds.csv, in priority order.
    Companies redesign sites, so the "about" page often moves; several candidates let one
    company's series follow the page across URL changes.
  * For each year, take the FIRST candidate (by priority) that has an archived HTTP-200
    text/html capture in that year, choosing the capture closest to July 1 (mid-year, so
    years are evenly spaced).
  * If no candidate has a 200 capture that year but one has a 3xx capture, follow the
    redirect chain inside the archive (max 5 hops, must stay on web.archive.org) and
    record the final URL. Status = "redirect_followed".
  * Otherwise the year is "missing". We never borrow a neighbouring year's snapshot;
    the gap is recorded, with the nearest available year noted for transparency.

Outputs (resumable; re-running skips finished company-years):
  data/part1/cdx/<ticker>__<n>.json     raw CDX responses (cache)
  data/part1/html/<ticker>_<year>.html  archived HTML
  data/part1/snapshots_manifest.csv     one row per company-year with provenance
  data/part1/coverage_report.csv        years captured per company

Usage:
  python part1/collect_snapshots.py                 # all 50 companies
  python part1/collect_snapshots.py --tickers MSFT JNJ   # a subset (good first test)
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import DATA, YEARS, RateLimiter, load_companies, load_seeds, make_session  # noqa: E402

OUT = DATA / "part1"
CDX_DIR = OUT / "cdx"
HTML_DIR = OUT / "html"
MANIFEST = OUT / "snapshots_manifest.csv"
COVERAGE = OUT / "coverage_report.csv"
for d in (OUT, CDX_DIR, HTML_DIR):
    d.mkdir(parents=True, exist_ok=True)

CDX_ENDPOINT = "https://web.archive.org/cdx/search/cdx"
MANIFEST_FIELDS = [
    "ticker", "company_name", "sector", "year", "status", "seed_url", "seed_priority",
    "capture_timestamp", "original_url", "final_url", "archived_status", "digest",
    "wayback_url", "n_200_captures_in_year", "note",
]

limiter = RateLimiter(1.5)  # Wayback asks clients to be gentle; ~0.7 req/s


def cdx_query(session, url: str, cache_path: Path) -> list[dict]:
    """All captures 2016-2024 for one URL, collapsed to at most one per month."""
    if cache_path.exists():
        return json.loads(cache_path.read_text())
    limiter.wait()
    params = {
        "url": url,
        "from": str(YEARS[0]),
        "to": str(YEARS[-1]),
        "output": "json",
        "fl": "timestamp,original,statuscode,mimetype,digest",
        "collapse": "timestamp:6",  # one capture per YYYYMM keeps responses small
    }
    r = session.get(CDX_ENDPOINT, params=params, timeout=60)
    r.raise_for_status()
    rows = r.json() if r.text.strip() else []
    records = [dict(zip(rows[0], row)) for row in rows[1:]] if rows else []
    cache_path.write_text(json.dumps(records))
    return records


def closest_to_midyear(captures: list[dict], year: int) -> dict:
    target = datetime(year, 7, 1)
    return min(captures, key=lambda c: abs(datetime.strptime(c["timestamp"][:8], "%Y%m%d") - target))


def pick_capture(per_seed: list[tuple[int, str, list[dict]]], year: int):
    """Apply the selection rule. Returns (kind, priority, seed_url, capture, n_200) or None."""
    y = str(year)
    # Pass 1: a clean 200 HTML capture from the highest-priority seed that has one.
    for prio, seed, caps in per_seed:
        ok = [c for c in caps if c["timestamp"].startswith(y)
              and c["statuscode"] == "200" and "html" in c["mimetype"]]
        if ok:
            return "ok", prio, seed, closest_to_midyear(ok, year), len(ok)
    # Pass 2: a redirect we can follow inside the archive.
    for prio, seed, caps in per_seed:
        redir = [c for c in caps if c["timestamp"].startswith(y) and c["statuscode"].startswith("3")]
        if redir:
            return "redirect", prio, seed, closest_to_midyear(redir, year), 0
    return None


def fetch_archived(session, capture: dict, follow: bool) -> tuple[str, str, str]:
    """Download archived HTML. 'id_' gives the original bytes without the Wayback toolbar.
    For redirects we let Wayback resolve the chain and keep the final archived URL."""
    limiter.wait()
    if follow:
        url = f"https://web.archive.org/web/{capture['timestamp']}/{capture['original']}"
        r = session.get(url, timeout=60, allow_redirects=True)
        if len(r.history) > 5:
            raise RuntimeError(f"redirect chain too long ({len(r.history)} hops)")
        if "web.archive.org" not in r.url:
            raise RuntimeError(f"redirect left the archive: {r.url}")
    else:
        url = f"https://web.archive.org/web/{capture['timestamp']}id_/{capture['original']}"
        r = session.get(url, timeout=60)
    r.raise_for_status()
    r.encoding = r.encoding or r.apparent_encoding
    return r.text, url, r.url


def load_manifest() -> dict[tuple[str, int], dict]:
    if not MANIFEST.exists():
        return {}
    with open(MANIFEST, newline="", encoding="utf-8") as f:
        return {(r["ticker"], int(r["year"])): r for r in csv.DictReader(f)}


def save_manifest(rows: dict[tuple[str, int], dict]) -> None:
    with open(MANIFEST, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS)
        w.writeheader()
        for key in sorted(rows):
            w.writerow(rows[key])


def nearest_available_year(per_seed, year: int) -> str:
    years = {int(c["timestamp"][:4]) for _, _, caps in per_seed for c in caps if c["statuscode"] == "200"}
    if not years:
        return "no 200 captures for any seed in 2016-2024"
    near = min(years, key=lambda y: abs(y - year))
    return f"nearest year with a 200 capture: {near}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", nargs="*", help="limit to these tickers")
    ap.add_argument("--contact", default="research-contact@example.com",
                    help="email for the User-Agent header (polite crawling)")
    args = ap.parse_args()

    session = make_session(f"Penn-RA-authenticity-study/0.1 (academic research; {args.contact})")
    companies = load_companies()
    seeds = load_seeds()
    if args.tickers:
        companies = [c for c in companies if c["ticker"] in set(args.tickers)]
    manifest = load_manifest()

    for comp in companies:
        t = comp["ticker"]
        per_seed = []
        for i, seed in enumerate(seeds.get(t, []), start=1):
            try:
                caps = cdx_query(session, seed, CDX_DIR / f"{t.replace('.', '-')}__{i}.json")
            except Exception as e:  # keep going; one bad seed shouldn't stop the run
                print(f"  [cdx error] {t} {seed}: {e}")
                caps = []
            per_seed.append((i, seed, caps))

        for year in YEARS:
            key = (t, year)
            html_path = HTML_DIR / f"{t.replace('.', '-')}_{year}.html"
            if key in manifest and manifest[key]["status"] in ("ok", "redirect_followed") and html_path.exists():
                continue
            row = {f: "" for f in MANIFEST_FIELDS}
            row.update(ticker=t, company_name=comp["company_name"], sector=comp["sector"], year=year)
            pick = pick_capture(per_seed, year)
            if pick is None:
                row.update(status="missing", note=nearest_available_year(per_seed, year))
            else:
                kind, prio, seed, cap, n200 = pick
                row.update(seed_url=seed, seed_priority=prio, capture_timestamp=cap["timestamp"],
                           original_url=cap["original"], archived_status=cap["statuscode"],
                           digest=cap["digest"], n_200_captures_in_year=n200)
                try:
                    html, wb_url, final = fetch_archived(session, cap, follow=(kind == "redirect"))
                    html_path.write_text(html, encoding="utf-8")
                    row.update(status="ok" if kind == "ok" else "redirect_followed",
                               wayback_url=wb_url, final_url=final)
                except Exception as e:
                    row.update(status="fetch_error", note=str(e)[:200])
            manifest[key] = row
            print(f"{t} {year}: {row['status']} {row['seed_url']}")
        save_manifest(manifest)  # checkpoint after every company

    # Coverage summary: the brief asks us to document every gap.
    with open(COVERAGE, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ticker", "sector", "years_ok", "years_redirect", "years_missing", "years_error", "seeds_used"])
        for comp in load_companies():
            rows = [manifest.get((comp["ticker"], y)) for y in YEARS]
            rows = [r for r in rows if r]
            count = lambda s: sum(r["status"] == s for r in rows)  # noqa: E731
            w.writerow([comp["ticker"], comp["sector"], count("ok"), count("redirect_followed"),
                        count("missing") + (len(YEARS) - len(rows)), count("fetch_error"),
                        ";".join(sorted({r["seed_url"] for r in rows if r["seed_url"]}))])
    print(f"\nManifest: {MANIFEST}\nCoverage: {COVERAGE}")


if __name__ == "__main__":
    main()
