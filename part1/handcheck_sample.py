"""Spot-check ~20 LLM-coded pages: does each theme's evidence appear in the page text?"""
from __future__ import annotations

import json
import random
from pathlib import Path

CACHE = Path(__file__).resolve().parents[1] / "data" / "part1" / "llm_local"
TEXT = Path(__file__).resolve().parents[1] / "data" / "part1" / "text"
OUT = Path(__file__).resolve().parents[1] / "data" / "part1" / "handcheck_20.json"


def main() -> None:
    files = sorted(CACHE.glob("*.json"))
    random.seed(42)
    sample = random.sample(files, min(20, len(files)))
    rows = []
    for f in sample:
        d = json.loads(f.read_text(encoding="utf-8"))
        stem = f.stem
        tpath = TEXT / f"{stem}.txt"
        text = tpath.read_text(encoding="utf-8", errors="replace") if tpath.exists() else ""
        low = text.lower()
        themes = d.get("themes", [])
        ok_ev = bad_ev = 0
        for th in themes:
            ev = (th.get("evidence") or "")[:40].lower()
            if ev and ev in low:
                ok_ev += 1
            else:
                bad_ev += 1
        rows.append({
            "stem": stem,
            "n_themes": len(themes),
            "page_type": d.get("page_type", ""),
            "values_change_vs_prior": d.get("values_change_vs_prior", ""),
            "evidence_ok": ok_ev,
            "evidence_missing_in_text": bad_ev,
            "analyst_notes": (d.get("analyst_notes") or "")[:120],
        })
    summary = {
        "n": len(rows),
        "total_themes": sum(r["n_themes"] for r in rows),
        "evidence_ok": sum(r["evidence_ok"] for r in rows),
        "evidence_missing_in_text": sum(r["evidence_missing_in_text"] for r in rows),
        "zero_theme_pages": sum(r["n_themes"] == 0 for r in rows),
        "rows": rows,
    }
    OUT.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote {OUT}")
    print(
        f"n={summary['n']} themes={summary['total_themes']} "
        f"evidence_ok={summary['evidence_ok']} missing={summary['evidence_missing_in_text']} "
        f"zero_theme={summary['zero_theme_pages']}"
    )


if __name__ == "__main__":
    main()
