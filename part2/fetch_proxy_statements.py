"""Part 2, step 1: collect proxy statements (SEC form DEF 14A) for the 50 companies, 2016-2024.

Why proxy statements (justify further in part2/README.md):
  * Every US-listed company must file one each year, in a standard place (SEC EDGAR), so
    coverage is near-complete and comparable -- unlike voluntary ESG/DEI reports, which
    start at different years, move around IR sites and change format.
  * They disclose what boards actually reward: executive-pay metrics (incl. any ESG/DEI
    modifiers), board composition, risk oversight, shareholder proposals. That is the
    "revealed priorities" side of the stated-vs-lived comparison.

Selection rule per company-year:
  * Calendar year of FILING = year (a 2024 proxy describes fiscal 2023 pay; note this lag).
  * If several DEF 14As were filed that year (e.g. a special-meeting proxy for a merger),
    take the earliest one filed January-June (annual-meeting season); if none in that window,
    the earliest that year. All alternatives are listed in the manifest's `other_def14a` column.
  * Foreign filers / companies without DEF 14A in a year => status "missing" with a note.

SEC fair-access rules: <= 10 requests/second and a User-Agent with a real contact email.

Usage:  python part2/fetch_proxy_statements.py --contact you@upenn.edu [--tickers MSFT JNJ]
Outputs: data/part2/proxy_html/, data/part2/proxy_text/, data/part2/proxy_manifest.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import DATA, YEARS, RateLimiter, load_companies, make_session  # noqa: E402

P2 = DATA / "part2"
HTML_DIR, TEXT_DIR, CACHE = P2 / "proxy_html", P2 / "proxy_text", P2 / "edgar_cache"
for d in (P2, HTML_DIR, TEXT_DIR, CACHE):
    d.mkdir(parents=True, exist_ok=True)
MANIFEST = P2 / "proxy_manifest.csv"
FIELDS = ["ticker", "company_name", "sector", "year", "status", "cik", "form", "filing_date",
          "accession", "doc_url", "text_chars", "other_def14a", "note"]

limiter = RateLimiter(0.15)  # ~6-7 req/s, under SEC's 10/s ceiling

# SEC ticker map sometimes points at a post-reorg shell with no historical DEF 14As.
# Override keeps the panel complete (document in DECISIONS.md / part2 README).
CIK_OVERRIDE = {
    "BLK": 1364742,  # BlackRock Finance, Inc. — map's 2012383 is post-reorg shell
    "XOM": 34088,    # EXXON MOBIL CORP — map's 2115436 is ExxonMobil Holdings Corp
}


def get_json(session, url: str, cache_name: str) -> dict:
    path = CACHE / cache_name
    if path.exists():
        return json.loads(path.read_text())
    limiter.wait()
    r = session.get(url, timeout=60)
    r.raise_for_status()
    path.write_text(r.text)
    return r.json()


def ticker_to_cik(session) -> dict[str, int]:
    data = get_json(session, "https://www.sec.gov/files/company_tickers.json", "company_tickers.json")
    return {v["ticker"].upper(): int(v["cik_str"]) for v in data.values()}


def all_filings(session, cik: int) -> list[dict]:
    """Flatten EDGAR submissions JSON, including the paginated older-filings files."""
    sub = get_json(session, f"https://data.sec.gov/submissions/CIK{cik:010d}.json", f"sub_{cik}.json")
    blocks = [sub["filings"]["recent"]]
    for extra in sub["filings"].get("files", []):
        blocks.append(get_json(session, f"https://data.sec.gov/submissions/{extra['name']}", extra["name"]))
    out = []
    for b in blocks:
        for i in range(len(b["form"])):
            out.append({k: b[k][i] for k in ("form", "filingDate", "accessionNumber", "primaryDocument")})
    return out


def choose_proxy(filings: list[dict], year: int) -> tuple[dict | None, list[dict]]:
    cands = sorted([f for f in filings if f["form"] == "DEF 14A" and f["filingDate"].startswith(str(year))],
                   key=lambda f: f["filingDate"])
    if not cands:
        return None, []
    season = [f for f in cands if int(f["filingDate"][5:7]) <= 6]
    pick = (season or cands)[0]
    return pick, [f for f in cands if f is not pick]


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text("\n")
    text = re.sub(r"[ \t\xa0]+", " ", text)
    return re.sub(r"\n\s*\n+", "\n\n", text).strip()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--contact", required=True, help="your email; SEC requires it in the User-Agent")
    ap.add_argument("--tickers", nargs="*")
    args = ap.parse_args()

    session = make_session(f"Penn RA application research {args.contact}")
    ciks = ticker_to_cik(session)
    companies = load_companies()
    if args.tickers:
        companies = [c for c in companies if c["ticker"] in set(args.tickers)]

    rows = {}
    if MANIFEST.exists():
        with open(MANIFEST, newline="", encoding="utf-8") as f:
            rows = {(r["ticker"], int(r["year"])): r for r in csv.DictReader(f)}

    for comp in companies:
        t = comp["ticker"]
        cik = CIK_OVERRIDE.get(t) or ciks.get(t.replace(".", "-").upper())  # EDGAR: BRK-B
        filings = all_filings(session, cik) if cik else []
        for year in YEARS:
            stem = f"{t.replace('.', '-')}_{year}"
            if rows.get((t, year), {}).get("status") == "ok" and (TEXT_DIR / f"{stem}.txt").exists():
                continue
            row = {f: "" for f in FIELDS}
            row.update(ticker=t, company_name=comp["company_name"], sector=comp["sector"], year=year, cik=cik or "")
            if not cik:
                row.update(status="missing", note="ticker not found in SEC ticker map")
            else:
                pick, others = choose_proxy(filings, year)
                if pick is None:
                    row.update(status="missing", note="no DEF 14A filed this calendar year")
                else:
                    acc = pick["accessionNumber"].replace("-", "")
                    url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{pick['primaryDocument']}"
                    row.update(form=pick["form"], filing_date=pick["filingDate"], accession=pick["accessionNumber"],
                               doc_url=url, other_def14a=";".join(o["filingDate"] for o in others))
                    try:
                        limiter.wait()
                        r = session.get(url, timeout=120)
                        r.raise_for_status()
                        (HTML_DIR / f"{stem}.htm").write_text(r.text, encoding="utf-8")
                        text = html_to_text(r.text)
                        (TEXT_DIR / f"{stem}.txt").write_text(text, encoding="utf-8")
                        row.update(status="ok", text_chars=len(text))
                    except Exception as e:
                        row.update(status="fetch_error", note=str(e)[:200])
            rows[(t, year)] = row
            print(f"{t} {year}: {row['status']} {row['filing_date']}")
        with open(MANIFEST, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
            for k in sorted(rows):
                w.writerow(rows[k])
    print(f"\nManifest: {MANIFEST}")


if __name__ == "__main__":
    main()
