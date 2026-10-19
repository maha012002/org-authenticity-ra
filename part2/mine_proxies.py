"""Part 2, step 2: mine DEF 14A text for lived-value signals using the shared theme codebook.

Proxies are long and formulaic. This script:
  1. Scores each codebook theme with the same keyword lexicon as Part 1
     (salience 0-3 from cue frequency in a head+tail text sample).
  2. Extracts structural flags that reveal board priorities:
     - ESG/DEI near compensation / incentive language
     - Board diversity / human-capital discussion
     - Climate / GHG / emissions language
     - ESG-related shareholder proposals

Output: data/part2/part2_lived_values.csv  (one row per company-year)
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import CONFIG, DATA, YEARS, load_companies  # noqa: E402
from part1.code_themes import code_lexicon  # noqa: E402

P2 = DATA / "part2"
TEXT_DIR = P2 / "proxy_text"
MANIFEST = P2 / "proxy_manifest.csv"
OUT = P2 / "part2_lived_values.csv"
MAX_CHARS = 200_000  # proxies are long; score on a large head+tail sample

# Section cues that mark "revealed priority" language (compensation / governance).
COMP_WINDOW = re.compile(
    r".{0,120}(compensation|incentive|award|bonus|pay.?for.?performance|"
    r"performance.?metric|named executive).{0,120}",
    re.I | re.S,
)
ESG_TERMS = re.compile(
    r"\b(ESG|sustainability|climate|DEI|diversity|inclusion|human capital|"
    r"greenhouse|GHG|carbon|social responsibility)\b",
    re.I,
)


def sample_text(text: str) -> str:
    if len(text) <= MAX_CHARS:
        return text
    half = MAX_CHARS // 2
    return text[:half] + "\n...\n" + text[-half:]


def structural_flags(text: str) -> dict:
    flags = {
        "esg_in_compensation": 0,
        "dei_board_or_hc": 0,
        "climate_disclosure": 0,
        "shareholder_proposal_esg": 0,
        "n_esg_term_hits": 0,
    }
    flags["n_esg_term_hits"] = len(ESG_TERMS.findall(text))
    # ESG near compensation language
    for m in COMP_WINDOW.finditer(text):
        if ESG_TERMS.search(m.group(0)):
            flags["esg_in_compensation"] = 1
            break
    low = text.lower()
    if re.search(r"board.{0,40}divers|divers.{0,40}board|human capital", low):
        flags["dei_board_or_hc"] = 1
    if re.search(r"climate|greenhouse|ghg|carbon neutral|net.?zero|emissions", low):
        flags["climate_disclosure"] = 1
    if re.search(r"shareholder proposal.{0,200}(climate|diversity|ESG|human capital|emission)", low):
        flags["shareholder_proposal_esg"] = 1
    return flags


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", nargs="*")
    args = ap.parse_args()

    codes = list(json.loads((CONFIG / "theme_codebook.json").read_text())["categories"])
    manifest = {}
    if MANIFEST.exists():
        with open(MANIFEST, newline="", encoding="utf-8") as f:
            manifest = {(r["ticker"], int(r["year"])): r for r in csv.DictReader(f)}

    fields = [
        "ticker", "company_name", "sector", "year", "proxy_status", "filing_date",
        "text_chars", "theme_categories", "analyst_notes", "esg_in_compensation",
        "dei_board_or_hc", "climate_disclosure", "shareholder_proposal_esg",
        "n_esg_term_hits", "doc_url",
    ] + [f"theme__{c}" for c in codes]

    companies = load_companies()
    if args.tickers:
        companies = [c for c in companies if c["ticker"] in set(args.tickers)]

    rows = []
    for comp in companies:
        t = comp["ticker"]
        for y in YEARS:
            m = manifest.get((t, y), {})
            stem = f"{t.replace('.', '-')}_{y}"
            tpath = TEXT_DIR / f"{stem}.txt"
            text = tpath.read_text(encoding="utf-8", errors="replace") if tpath.exists() else ""
            sample = sample_text(text)
            sal = {c: 0 for c in codes}
            themes = []
            notes = []
            if text and m.get("status") == "ok":
                coded = code_lexicon(sample, None)
                themes = coded["themes"]
                for th in themes:
                    sal[th["code"]] = max(sal[th["code"]], int(th.get("salience", 1)))
                notes.append("Dictionary-coded proxy text (same codebook as Part 1).")
            else:
                notes.append(m.get("note") or "no usable proxy text")
            flags = structural_flags(sample) if text else {
                "esg_in_compensation": 0, "dei_board_or_hc": 0, "climate_disclosure": 0,
                "shareholder_proposal_esg": 0, "n_esg_term_hits": 0,
            }
            rows.append({
                "ticker": t, "company_name": comp["company_name"], "sector": comp["sector"], "year": y,
                "proxy_status": m.get("status", "not_attempted"),
                "filing_date": m.get("filing_date", ""),
                "text_chars": len(text) or m.get("text_chars", ""),
                "theme_categories": ";".join(sorted({th["code"] for th in themes})),
                "analyst_notes": " | ".join(n for n in notes if n),
                "doc_url": m.get("doc_url", ""),
                **flags,
                **{f"theme__{c}": sal[c] for c in codes},
            })
            print(f"{t} {y}: {rows[-1]['proxy_status']} themes={len(themes)} esg_comp={flags['esg_in_compensation']}")

    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    ok = sum(r["proxy_status"] == "ok" for r in rows)
    print(f"\n{OUT}: {len(rows)} rows, {ok} with proxy text ({ok / len(rows):.0%}).")


if __name__ == "__main__":
    main()
