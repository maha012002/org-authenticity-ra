"""Part 1, step 4: assemble the deliverable dataset -- one row per company-year (all 450,
including missing years, so gaps are visible rather than silently dropped).

Required columns: ticker, company_name, sector, year, page_text_clean, changed_from_prior,
theme_categories, analyst_notes. Extra columns document provenance and let Part 3 use
theme salience directly (theme__<code> = salience 0-3).

Output: data/part1/part1_stated_values.csv
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import CONFIG, DATA, YEARS, load_companies  # noqa: E402

P1 = DATA / "part1"
OUT = P1 / "part1_stated_values.csv"


def main() -> None:
    codes = list(json.loads((CONFIG / "theme_codebook.json").read_text())["categories"])
    with open(P1 / "snapshots_manifest.csv", newline="", encoding="utf-8") as f:
        manifest = {(r["ticker"], int(r["year"])): r for r in csv.DictReader(f)}
    changes = {}
    if (P1 / "change_detection.csv").exists():
        with open(P1 / "change_detection.csv", newline="", encoding="utf-8") as f:
            changes = {(r["ticker"], int(r["year"])): r for r in csv.DictReader(f)}

    # values_change_vs_prior kept under legacy column name llm_values_change for CSV stability
    fields = ["ticker", "company_name", "sector", "year", "snapshot_status", "page_text_clean",
              "changed_from_prior", "similarity_to_prior", "llm_values_change", "url_changed",
              "theme_categories", "linguistic_shift", "page_type", "analyst_notes",
              "seed_url", "capture_timestamp", "wayback_url", "text_chars"] + [f"theme__{c}" for c in codes]

    rows = []
    for comp in load_companies():
        t = comp["ticker"]
        for y in YEARS:
            m = manifest.get((t, y), {})
            stem = f"{t.replace('.', '-')}_{y}"
            tpath, lpath = P1 / "text" / f"{stem}.txt", P1 / "llm" / f"{stem}.json"
            text = tpath.read_text(encoding="utf-8") if tpath.exists() else ""
            llm = json.loads(lpath.read_text()) if lpath.exists() else {}
            ch = changes.get((t, y), {})
            themes = llm.get("themes", [])
            sal = {c: 0 for c in codes}
            for th in themes:
                sal[th["code"]] = max(sal[th["code"]], int(th.get("salience", 1)))
            notes = [n for n in [m.get("note", ""), llm.get("analyst_notes", ""), llm.get("error", "")] if n]
            rows.append({
                "ticker": t, "company_name": comp["company_name"], "sector": comp["sector"], "year": y,
                "snapshot_status": m.get("status", "not_attempted"),
                "page_text_clean": text,
                "changed_from_prior": ch.get("change_class", ""),
                "similarity_to_prior": ch.get("similarity_to_prior", ""),
                "llm_values_change": llm.get("values_change_vs_prior", ""),
                "url_changed": ch.get("url_changed", ""),
                "theme_categories": ";".join(sorted({th["code"] for th in themes})),
                "linguistic_shift": llm.get("linguistic_shift", ""),
                "page_type": llm.get("page_type", ""),
                "analyst_notes": " | ".join(notes),
                "seed_url": m.get("seed_url", ""), "capture_timestamp": m.get("capture_timestamp", ""),
                "wayback_url": m.get("wayback_url", ""), "text_chars": len(text),
                **{f"theme__{c}": sal[c] for c in codes},
            })
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    have = sum(r["snapshot_status"] in ("ok", "redirect_followed") for r in rows)
    print(f"{OUT}: {len(rows)} company-years, {have} with a usable snapshot ({have / len(rows):.0%}).")


if __name__ == "__main__":
    main()
