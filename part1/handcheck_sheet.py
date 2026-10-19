"""Part 1, step 5: human hand-check of theme labels -- precision of the LLM vs. the keyword baseline.

The automated evidence check (does the quote appear on the page?) cannot tell whether a theme
label is CORRECT. This script builds a sheet for a human reader to judge exactly that, then
scores it.

  make   -- sample 20 usable pages (4 per sector, fixed seed) and write two sheets:
            data/part1/handcheck_themes.csv  one row per (page, theme) assigned by the LLM,
                                            the keyword coder, or both. Fill `human_correct`
                                            with y or n: does the page really express this
                                            value as something the company prioritizes?
            data/part1/handcheck_pages.csv   one row per page. Fill `human_page_type_ok` (y/n)
                                            and `human_missed_themes` (codes neither label
                                            list caught, separated by ;).
            Read each page in data/part1/text/<stem>.txt. Judge blind to which method
            assigned a theme if you can: sort the themes sheet by stem and code first.
  score  -- read the filled sheets and write data/part1/handcheck_results.json:
            precision of each method (share of its labels you marked correct), recall
            estimate (share of all true themes each method found), and page_type accuracy.

Usage:
  python part1/handcheck_sheet.py make  [--model qwen2.5:7b]
  python part1/handcheck_sheet.py score
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import CONFIG, DATA  # noqa: E402

P1 = DATA / "part1"
THEMES_SHEET = P1 / "handcheck_themes.csv"
PAGES_SHEET = P1 / "handcheck_pages.csv"
RESULTS = P1 / "handcheck_results.json"
CODEBOOK = json.loads((CONFIG / "theme_codebook.json").read_text(encoding="utf-8"))["categories"]
CODES = list(CODEBOOK)
SEED, PER_SECTOR = 7, 4


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def make(model: str) -> None:
    llm_dir = P1 / f"llm_local_{model.replace(':', '-')}"
    if not llm_dir.exists():
        sys.exit(f"No cached run for {model} at {llm_dir}. Run part1/analyze_llm.py --model {model} first.")
    with open(P1 / "part1_stated_values.csv", newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["snapshot_status"] in ("ok", "redirect_followed")]
    stem = lambda r: f"{r['ticker'].replace('.', '-')}_{r['year']}"  # noqa: E731
    rows = [r for r in rows if (llm_dir / f"{stem(r)}.json").exists()]

    rng = random.Random(SEED)
    sample = []
    for sector in sorted({r["sector"] for r in rows}):
        pool = [r for r in rows if r["sector"] == sector]
        sample += rng.sample(pool, min(PER_SECTOR, len(pool)))

    theme_rows, page_rows = [], []
    for r in sample:
        s = stem(r)
        llm = load_json(llm_dir / f"{s}.json")
        lex = load_json(P1 / "lexicon" / f"{s}.json")
        llm_ev = {t["code"]: t.get("evidence", "") for t in llm.get("themes", [])}
        lex_ev = {t["code"]: t.get("evidence", "") for t in lex.get("themes", [])}
        for code in CODES:
            if code not in llm_ev and code not in lex_ev:
                continue
            by = "both" if code in llm_ev and code in lex_ev else ("llm" if code in llm_ev else "lexicon")
            theme_rows.append({
                "stem": s, "sector": r["sector"], "code": code, "definition": CODEBOOK[code],
                "assigned_by": by, "llm_evidence": llm_ev.get(code, ""), "lexicon_evidence": lex_ev.get(code, ""),
                "human_correct": "", "notes": "",
            })
        page_rows.append({
            "stem": s, "sector": r["sector"], "page_text_file": f"data/part1/text/{s}.txt",
            "llm_page_type": llm.get("page_type", ""), "llm_themes": ";".join(llm_ev),
            "lexicon_themes": ";".join(lex_ev), "human_page_type_ok": "", "human_missed_themes": "",
            "notes": "",
        })

    for path, data in ((THEMES_SHEET, theme_rows), (PAGES_SHEET, page_rows)):
        if path.exists():
            sys.exit(f"{path} already exists; delete it first if you really want a fresh sheet.")
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(data[0]))
            w.writeheader()
            w.writerows(data)
    print(f"{len(page_rows)} pages, {len(theme_rows)} theme labels to judge.\n"
          f"Fill in: {THEMES_SHEET}\n         {PAGES_SHEET}")


def yes(v: str) -> bool | None:
    v = (v or "").strip().lower()
    return True if v in ("y", "yes", "1") else False if v in ("n", "no", "0") else None


def score() -> None:
    with open(THEMES_SHEET, newline="", encoding="utf-8") as f:
        themes = list(csv.DictReader(f))
    with open(PAGES_SHEET, newline="", encoding="utf-8") as f:
        pages = list(csv.DictReader(f))
    judged = [t for t in themes if yes(t["human_correct"]) is not None]
    if len(judged) < len(themes):
        print(f"Warning: {len(themes) - len(judged)} theme rows not judged yet (left out of the scores).")

    def precision(method: str) -> dict:
        mine = [t for t in judged if t["assigned_by"] in (method, "both")]
        ok = sum(yes(t["human_correct"]) for t in mine)
        return {"labels_judged": len(mine), "correct": ok,
                "precision": round(ok / len(mine), 3) if mine else None}

    # True themes per page = labels marked correct + themes the reader says both methods missed.
    true_by_page: dict[str, set] = {}
    for t in judged:
        if yes(t["human_correct"]):
            true_by_page.setdefault(t["stem"], set()).add(t["code"])
    for p in pages:
        missed = {c.strip() for c in p["human_missed_themes"].split(";") if c.strip() in CODEBOOK}
        true_by_page.setdefault(p["stem"], set()).update(missed)

    def recall(method: str) -> dict:
        found = total = 0
        for p in pages:
            truth = true_by_page.get(p["stem"], set())
            got = set(filter(None, p[f"{method}_themes"].split(";")))
            found += len(truth & got)
            total += len(truth)
        return {"true_themes": total, "found": found, "recall": round(found / total, 3) if total else None}

    pt = [yes(p["human_page_type_ok"]) for p in pages if yes(p["human_page_type_ok"]) is not None]
    results = {
        "pages": len(pages), "theme_labels_judged": len(judged),
        "llm": {**precision("llm"), **recall("llm")},
        "lexicon": {**precision("lexicon"), **recall("lexicon")},
        "llm_page_type_accuracy": round(sum(pt) / len(pt), 3) if pt else None,
        "note": "Recall is estimated: true themes = labels judged correct + themes the reader added "
                "as missed by both methods. One reader, not blind to the method if not sorted first.",
    }
    RESULTS.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=["make", "score"])
    ap.add_argument("--model", default="qwen2.5:7b")
    args = ap.parse_args()
    make(args.model) if args.action == "make" else score()


if __name__ == "__main__":
    main()
