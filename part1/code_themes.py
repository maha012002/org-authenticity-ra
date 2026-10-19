"""Part 1, step 3: change detection + dictionary (lexicon) thematic coding.

(a) changed_from_prior — deterministic only:
    identical Wayback digest => identical page; otherwise text similarity buckets:
      >= 0.98  no_substantive_change
      0.85-0.98 minor_edit
      < 0.85   substantive_change
    If the seed URL differs from the prior year, flag url_changed (site redesign).

(b) theme_categories — keyword lexicon against config/theme_codebook.json.
    Each hit stores a short evidence snippet and salience 1–3 from cue frequency.
    Conservative cues (precision over recall); same lexicon is reused in Part 2.

(c) page_type / values_change — rule-based from keywords and similarity.

Caches: data/part1/lexicon/<ticker>_<year>.json
Usage:  python part1/code_themes.py [--tickers MSFT JNJ]
"""
from __future__ import annotations

import argparse
import csv
import difflib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import CONFIG, DATA  # noqa: E402

P1 = DATA / "part1"
TEXT_DIR = P1 / "text"
CACHE_DIR = P1 / "lexicon"
CHANGES = P1 / "change_detection.csv"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Conservative keyword cues. Prefer precision over recall.
LEXICON: dict[str, list[str]] = {
    "integrity": ["integrity", "ethic", "honesty", "trust", "transparency", "compliance", "doing the right thing"],
    "customer": ["customer", "client", "patient", "satisfaction", "serve our"],
    "innovation": ["innovation", "innovative", "creativity", "r&d", "research", "pioneer", "invent"],
    "collaboration": ["collaboration", "teamwork", "partnership", "working together", "one team"],
    "respect_people": ["respect", "dignity", "employee", "wellbeing", "well-being", "talent", "career development"],
    "diversity_inclusion": ["diversity", "inclusion", "inclusive", "equity", "belonging", "representation"],
    "performance_execution": ["excellence", "accountability", "quality", "execution", "results", "agility", "performance"],
    "environment_sustainability": ["sustainability", "sustainable", "climate", "carbon", "emissions", "environment", "net zero"],
    "community_social_impact": ["community", "philanthropy", "social responsibility", "corporate social", "societal", "charit"],
    "safety": ["safety", "safe workplace", "health and safety", "patient safety"],
    "shareholder_value": ["shareholder", "stockholder", "long-term value", "return to"],
    "purpose_mission": ["our mission", "our purpose", "mission is", "purpose is", "why we exist"],
}


def similarity(a: str, b: str) -> float:
    norm = lambda s: re.sub(r"\s+", " ", s.lower()).strip()  # noqa: E731
    return round(difflib.SequenceMatcher(None, norm(a), norm(b), autojunk=False).ratio(), 4)


def change_class(prev: dict | None, cur: dict, prev_text: str | None, cur_text: str) -> dict:
    if prev is None or prev_text is None:
        return {"similarity_to_prior": "", "change_class": "no_prior_snapshot", "url_changed": ""}
    url_changed = prev["seed_url"] != cur["seed_url"]
    if prev["digest"] and prev["digest"] == cur["digest"]:
        return {"similarity_to_prior": 1.0, "change_class": "identical", "url_changed": url_changed}
    sim = similarity(prev_text, cur_text)
    cls = "no_substantive_change" if sim >= 0.98 else "minor_edit" if sim >= 0.85 else "substantive_change"
    return {"similarity_to_prior": sim, "change_class": cls, "url_changed": url_changed}


def _evidence_snip(text: str, cue: str) -> str:
    low = text.lower()
    i = low.find(cue.lower())
    if i < 0:
        return cue
    start = max(0, text.rfind(" ", 0, i) + 1)
    end = text.find(" ", i + len(cue))
    if end < 0:
        end = min(len(text), i + len(cue) + 80)
    snip = re.sub(r"\s+", " ", text[start:end].strip())
    return " ".join(snip.split()[:20])


def code_lexicon(text: str, prior_text: str | None) -> dict:
    """Dictionary theme coding. Returns a JSON-serializable coding record."""
    low = text.lower()
    themes = []
    for code, cues in LEXICON.items():
        hits = [c for c in cues if c in low]
        if not hits:
            continue
        count = sum(low.count(c) for c in hits)
        salience = 3 if count >= 3 else 2 if count >= 2 else 1
        themes.append({"code": code, "evidence": _evidence_snip(text, hits[0]), "salience": salience})

    if prior_text is None:
        values_change, linguistic = "no_prior", ""
    else:
        sim = similarity(prior_text, text)
        values_change = "none" if sim >= 0.98 else "minor" if sim >= 0.85 else "substantive"
        linguistic = f"Text similarity to prior year = {sim}"

    page_type = "values_or_mission" if any(
        k in low for k in ("mission", "credo", "our values", "purpose")
    ) else "general_about"
    if len(text) < 300:
        page_type = "not_usable"

    return {
        "themes": themes,
        "page_type": page_type,
        "values_change_vs_prior": values_change,
        "linguistic_shift": linguistic,
        "analyst_notes": "Dictionary (keyword) coded against theme_codebook.json; evidence is a cue snippet.",
        "_model": "lexicon-v1",
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Change detection + lexicon theme coding")
    ap.add_argument("--tickers", nargs="*")
    ap.add_argument("--force", action="store_true", help="re-code even if cache exists")
    args = ap.parse_args()

    with open(P1 / "snapshots_manifest.csv", newline="", encoding="utf-8") as f:
        manifest = [r for r in csv.DictReader(f) if r["status"] in ("ok", "redirect_followed")]
    if args.tickers:
        manifest = [r for r in manifest if r["ticker"] in set(args.tickers)]

    by_ticker: dict[str, list[dict]] = {}
    for r in manifest:
        by_ticker.setdefault(r["ticker"], []).append(r)

    change_rows = []
    for ticker, rows in by_ticker.items():
        rows.sort(key=lambda r: int(r["year"]))
        prev, prev_text = None, None
        for r in rows:
            stem = f"{ticker.replace('.', '-')}_{r['year']}"
            tpath = TEXT_DIR / f"{stem}.txt"
            if not tpath.exists():
                continue
            text = tpath.read_text(encoding="utf-8")
            is_consecutive = prev is not None and int(prev["year"]) == int(r["year"]) - 1
            ch = change_class(prev if is_consecutive else None, r,
                              prev_text if is_consecutive else None, text)
            change_rows.append({"ticker": ticker, "year": r["year"], **ch})

            cache = CACHE_DIR / f"{stem}.json"
            if args.force or not cache.exists():
                out = code_lexicon(text, prev_text if is_consecutive else None)
                cache.write_text(json.dumps(out, indent=2), encoding="utf-8")
                print(f"{stem}: {len(out.get('themes', []))} themes")
            prev, prev_text = r, text

    with open(CHANGES, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["ticker", "year", "similarity_to_prior", "change_class", "url_changed"])
        w.writeheader()
        w.writerows(change_rows)
    print(f"Change detection: {CHANGES}")


if __name__ == "__main__":
    main()
