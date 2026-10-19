"""Part 1, step 4: LLM-based analysis of every snapshot with a free, local open-weight model.

Runs a local LLM through Ollama (https://ollama.com), so it costs nothing and needs no API key.
For each company-year snapshot the model returns, as schema-constrained JSON:
  (a) values_change_vs_prior  -- none / minor / substantive / no_prior, judged on VALUES content
                                 (a reworded menu or legal footer is not a values change)
  (b) themes                  -- codes from config/theme_codebook.json, each with a short quoted
                                 piece of evidence and a salience of 1-3
  (c) linguistic_shift        -- one or two sentences on tone/emphasis shifts vs. the prior year
  plus page_type and an analyst note flagging anything a researcher should check.

Design choices (each documented again in part1/README.md):
  * Keyword coding (code_themes.py) is kept as a transparent baseline; this script reports
    per-theme agreement (Cohen's kappa) between the two methods as a validity check.
  * Speed on a laptop CPU: the model sees the current page (capped at MAX_PAGE_CHARS) plus only
    the sentences ADDED and REMOVED since the prior consecutive year, instead of two full pages.
  * Captures whose archive digest is identical to the prior year's are not re-sent: the prior
    year's coding is reused and values change is recorded as "none" (status reused_identical).
  * The model's JSON is constrained by a schema (Ollama structured outputs); codes outside the
    codebook are impossible, and each theme's evidence is checked against the page text.
    Themes whose evidence cannot be found are dropped and counted (n_unverified_dropped),
    because small models sometimes paraphrase or invent quotes.
  * temperature 0 and a fixed seed, so reruns give the same output; every response is cached
    in data/part1/llm_local/, so the run is resumable after an interruption.

Setup (once):
  1. Install Ollama: https://ollama.com/download
  2. ollama pull qwen2.5:3b          (about 2 GB; use qwen2.5:7b instead if you have a GPU)
Usage:
  python part1/analyze_llm.py --check            # is Ollama running and the model available?
  python part1/analyze_llm.py --limit 5          # timing test: codes 5 snapshots, prints an ETA
  python part1/analyze_llm.py                    # full run (resumable), then merges + reports
  python part1/analyze_llm.py --merge-only       # rebuild dataset columns + agreement report
Run AFTER part1/build_dataset.py; re-run --merge-only if you rebuild the dataset.

Outputs:
  data/part1/llm_local/<ticker>_<year>.json      raw model output per snapshot (cache)
  data/part1/part1_stated_values.csv             LLM columns merged in (see merge_into_dataset)
  data/part1/llm_vs_lexicon_agreement.json       per-theme kappa + change-detection crosstab
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import statistics as st
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import CONFIG, DATA  # noqa: E402

P1 = DATA / "part1"
TEXT_DIR = P1 / "text"
CACHE = P1 / "llm_local"
DATASET = P1 / "part1_stated_values.csv"
AGREEMENT = P1 / "llm_vs_lexicon_agreement.json"
CACHE.mkdir(parents=True, exist_ok=True)

OLLAMA = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")
MAX_PAGE_CHARS = 6000   # p90 page is ~4,300 chars; longer pages are mostly repeated menus
MAX_DIFF_CHARS = 1500   # per side (added / removed sentences)
PAGE_TYPES = ["values_or_mission", "general_about", "careers_or_culture", "homepage", "other", "not_usable"]
CHANGE_LABELS = ["none", "minor", "substantive", "no_prior"]

CODEBOOK = json.loads((CONFIG / "theme_codebook.json").read_text(encoding="utf-8"))["categories"]
CODES = list(CODEBOOK)

SCHEMA = {
    "type": "object",
    "properties": {
        "themes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "enum": CODES},
                    "evidence": {"type": "string"},
                    "salience": {"type": "integer", "enum": [1, 2, 3]},
                },
                "required": ["code", "evidence", "salience"],
            },
        },
        "page_type": {"type": "string", "enum": PAGE_TYPES},
        "values_change_vs_prior": {"type": "string", "enum": CHANGE_LABELS},
        "linguistic_shift": {"type": "string"},
        "analyst_notes": {"type": "string"},
    },
    "required": ["themes", "page_type", "values_change_vs_prior", "linguistic_shift", "analyst_notes"],
}

SYSTEM = (
    "You code corporate 'About Us' and values pages for an organizational-behavior study. "
    "Use only the text you are given. Be conservative: assign a theme only when the page clearly "
    "presents it as something the company values or prioritizes, not a passing product mention. "
    "Evidence must be copied exactly from the CURRENT PAGE, at most 15 words. Answer in JSON only."
)

PROMPT = """CODEBOOK (code: definition)
{codebook}

COMPANY: {company} ({ticker}), YEAR: {year}

CURRENT PAGE ({year}):
<<<
{page}
>>>

{change_block}

Return JSON with:
- themes: every codebook theme the page clearly expresses, each with exact evidence and salience
  (3 = central or repeated, 2 = clearly stated, 1 = brief mention)
- page_type: what kind of page this is ("not_usable" if it is mostly navigation, an error page or empty)
- values_change_vs_prior: {change_instruction}
- linguistic_shift: one or two sentences on how tone or emphasis shifted vs. the prior year, or "" if none
- analyst_notes: one sentence on anything a researcher should double-check, or ""
"""


# --------------------------------------------------------------------------- helpers
def norm(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", s.lower())).strip()


def sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [p.strip() for p in parts if len(p.strip()) > 20]


def sentence_diff(prev: str, cur: str) -> tuple[str, str]:
    """Sentences added to and removed from the page since the prior year (order kept)."""
    prev_set, cur_set = {norm(s) for s in sentences(prev)}, {norm(s) for s in sentences(cur)}
    added = [s for s in sentences(cur) if norm(s) not in prev_set]
    removed = [s for s in sentences(prev) if norm(s) not in cur_set]
    clip = lambda xs: "\n".join(f"- {x}" for x in xs)[:MAX_DIFF_CHARS] or "(none)"  # noqa: E731
    return clip(added), clip(removed)


def evidence_found(evidence: str, page_norm: str) -> bool:
    """Exact (normalized) match, or at least 80% of the evidence's content words on the page."""
    ev = norm(evidence)
    if not ev:
        return False
    if ev in page_norm:
        return True
    words = [w for w in ev.split() if len(w) > 3]
    page_words = set(page_norm.split())
    return bool(words) and sum(w in page_words for w in words) / len(words) >= 0.8


def load_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def stem_of(ticker: str, year) -> str:
    return f"{ticker.replace('.', '-')}_{year}"


# --------------------------------------------------------------------------- model call
def check_ollama(model: str) -> None:
    try:
        tags = requests.get(f"{OLLAMA}/api/tags", timeout=10).json()
    except Exception as e:
        sys.exit(f"Ollama is not reachable at {OLLAMA} ({e}). Install it and make sure it is running.")
    names = {m["name"] for m in tags.get("models", [])}
    if model not in names and f"{model}:latest" not in names:
        sys.exit(f"Model '{model}' not found. Run:  ollama pull {model}\nInstalled: {sorted(names) or 'none'}")
    print(f"Ollama OK at {OLLAMA}; model '{model}' is installed.")


def call_model(model: str, prompt: str, num_ctx: int) -> dict:
    body = {
        "model": model,
        "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
        "stream": False,
        "format": SCHEMA,
        "options": {"temperature": 0, "seed": 42, "num_ctx": num_ctx},
        "keep_alive": "30m",
    }
    r = requests.post(f"{OLLAMA}/api/chat", json=body, timeout=900)
    r.raise_for_status()
    return json.loads(r.json()["message"]["content"])


def code_snapshot(model: str, row: dict, text: str, prior_text: str | None, prior_year) -> dict:
    page = text[:MAX_PAGE_CHARS]
    if prior_text is None:
        change_block = "PRIOR YEAR: no snapshot for the immediately preceding year."
        change_instruction = 'must be "no_prior"'
    else:
        added, removed = sentence_diff(prior_text, text)
        change_block = (f"CHANGES SINCE {prior_year}:\nSentences ADDED:\n{added}\n\nSentences REMOVED:\n{removed}")
        change_instruction = ('"none" if no values-related wording changed, "minor" for small rewording, '
                              '"substantive" if values were added, dropped or reframed')
    prompt = PROMPT.format(
        codebook="\n".join(f"- {k}: {v}" for k, v in CODEBOOK.items()),
        company=row["company_name"], ticker=row["ticker"], year=row["year"],
        page=page, change_block=change_block, change_instruction=change_instruction,
    )
    num_ctx = 4096 if len(prompt) < 9000 else 8192   # ~4 chars per token
    out = call_model(model, prompt, num_ctx)

    page_norm = norm(text)
    kept, dropped = [], 0
    for th in out.get("themes", []):
        if th.get("code") in CODEBOOK and evidence_found(th.get("evidence", ""), page_norm):
            kept.append(th)
        else:
            dropped += 1
    out["themes"] = kept
    out["n_unverified_dropped"] = dropped
    if prior_text is None:
        out["values_change_vs_prior"] = "no_prior"   # enforce; the model cannot see a prior year
    out["_model"] = model
    out["_page_truncated"] = len(text) > MAX_PAGE_CHARS
    return out


# --------------------------------------------------------------------------- main loop
def snapshot_rows() -> list[dict]:
    """Usable snapshots with their deterministic change class, ordered by ticker and year."""
    manifest = {(r["ticker"], int(r["year"])): r for r in load_csv(P1 / "snapshots_manifest.csv")}
    changes = {(r["ticker"], int(r["year"])): r for r in load_csv(P1 / "change_detection.csv")}
    rows = []
    for key, m in manifest.items():
        if m["status"] not in ("ok", "redirect_followed"):
            continue
        if not (TEXT_DIR / f"{stem_of(*key)}.txt").exists():
            continue
        rows.append({**m, "change_class": changes.get(key, {}).get("change_class", "")})
    return sorted(rows, key=lambda r: (r["ticker"], int(r["year"])))


def run(model: str, limit: int | None, tickers: set | None) -> None:
    rows = snapshot_rows()
    if tickers:
        rows = [r for r in rows if r["ticker"] in tickers]
    todo = [r for r in rows if not (CACHE / f"{stem_of(r['ticker'], r['year'])}.json").exists()]
    print(f"{len(rows)} usable snapshots; {len(rows) - len(todo)} already coded; {len(todo)} to go.")
    by_key = {(r["ticker"], int(r["year"])): r for r in rows}

    timings, n_called = [], 0
    for r in todo:
        if limit is not None and n_called >= limit:
            break
        t, y = r["ticker"], int(r["year"])
        stem = stem_of(t, y)
        text = (TEXT_DIR / f"{stem}.txt").read_text(encoding="utf-8")
        prior = by_key.get((t, y - 1))
        prior_path = CACHE / f"{stem_of(t, y - 1)}.json"

        if r["change_class"] == "identical" and prior and prior_path.exists():
            out = json.loads(prior_path.read_text(encoding="utf-8"))
            out.update(values_change_vs_prior="none", linguistic_shift="",
                       analyst_notes="Identical archive capture to prior year; prior-year coding reused.",
                       _status="reused_identical")
        else:
            prior_text = (TEXT_DIR / f"{stem_of(t, y - 1)}.txt").read_text(encoding="utf-8") if prior else None
            start = time.monotonic()
            try:
                out = code_snapshot(model, r, text, prior_text, y - 1 if prior else None)
                out["_status"] = "coded"
            except Exception as e:
                print(f"  {stem}: ERROR {str(e)[:150]} (will retry on next run)")
                continue  # not cached, so the next run retries it
            secs = time.monotonic() - start
            out["_seconds"] = round(secs, 1)
            timings.append(secs)
            n_called += 1
        (CACHE / f"{stem}.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

        left = len([x for x in todo if not (CACHE / f"{stem_of(x['ticker'], x['year'])}.json").exists()])
        eta = (st.mean(timings) * left / 3600) if timings else 0
        print(f"{stem}: {out['_status']}, {len(out['themes'])} themes, change={out['values_change_vs_prior']}"
              f" | {left} left, ETA ~{eta:.1f} h")
    if timings:
        print(f"\nMean {st.mean(timings):.1f} s per model call on this machine.")


# --------------------------------------------------------------------------- merge + agreement
def merge_into_dataset() -> None:
    """Put LLM output in the brief's required columns; keep keyword output under clear names.

    Renames (only when the dataset still has build_dataset.py's original columns):
      theme_categories   -> lexicon_theme_categories   (keyword baseline)
      llm_values_change  -> rule_values_change          (was rule-based despite its old name)
      linguistic_shift   -> rule_change_note            (similarity ratio text)
      page_type          -> rule_page_type
    New / refilled from the LLM: theme_categories, llm_values_change, linguistic_shift,
      llm_page_type, llm_status, llm_model, llm_n_unverified_dropped, llm_theme__<code> (0-3).
    theme__<code> salience columns stay keyword-based: Parts 3-4 compare them with Part 2's
    keyword salience, so both sides of the authenticity index use the same instrument.
    """
    rows = load_csv(DATASET)
    fields = list(rows[0].keys())
    renames = {"theme_categories": "lexicon_theme_categories", "llm_values_change": "rule_values_change",
               "linguistic_shift": "rule_change_note", "page_type": "rule_page_type"}
    if "lexicon_theme_categories" not in fields:   # first merge after build_dataset.py
        for r in rows:
            for old, new in renames.items():
                r[new] = r.pop(old, "")
        fields = [renames.get(f, f) for f in fields]
    llm_cols = ["theme_categories", "llm_values_change", "linguistic_shift", "llm_page_type",
                "llm_status", "llm_model", "llm_n_unverified_dropped"] + [f"llm_theme__{c}" for c in CODES]
    anchor = fields.index("changed_from_prior") + 1
    base = [f for f in fields if f not in llm_cols]
    fields = base[:anchor] + llm_cols[:4] + base[anchor:] + [c for c in llm_cols[4:]]

    for r in rows:
        path = CACHE / f"{stem_of(r['ticker'], r['year'])}.json"
        out = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
        sal = {c: 0 for c in CODES}
        if out:
            for th in out.get("themes", []):
                sal[th["code"]] = max(sal[th["code"]], int(th.get("salience", 1)))
        r.update({
            "theme_categories": ";".join(c for c in CODES if sal[c]) if out else "",
            "llm_values_change": out.get("values_change_vs_prior", "") if out else "",
            "linguistic_shift": out.get("linguistic_shift", "") if out else "",
            "llm_page_type": out.get("page_type", "") if out else "",
            "llm_status": out.get("_status", "coded") if out else (
                "no_snapshot" if r.get("snapshot_status") not in ("ok", "redirect_followed") else "not_coded"),
            "llm_model": out.get("_model", "") if out else "",
            "llm_n_unverified_dropped": out.get("n_unverified_dropped", "") if out else "",
            **{f"llm_theme__{c}": sal[c] if out else "" for c in CODES},
        })
        if out and out.get("analyst_notes") and out["analyst_notes"] not in r.get("analyst_notes", ""):
            r["analyst_notes"] = " | ".join(x for x in [r.get("analyst_notes", ""), "LLM: " + out["analyst_notes"]] if x)

    with open(DATASET, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"Merged LLM columns into {DATASET}")
    agreement_report(rows)


def kappa(a: list[bool], b: list[bool]) -> float | None:
    n = len(a)
    if n == 0:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return None if pe == 1 else round((po - pe) / (1 - pe), 3)


def agreement_report(rows: list[dict]) -> None:
    coded = [r for r in rows if r.get("llm_status") in ("coded", "reused_identical")]
    if not coded:
        print("No LLM-coded rows yet; skipping agreement report.")
        return
    per_theme = {}
    for c in CODES:
        llm = [int(r[f"llm_theme__{c}"] or 0) > 0 for r in coded]
        lex = [int(r[f"theme__{c}"] or 0) > 0 for r in coded]
        per_theme[c] = {"llm_prevalence": round(sum(llm) / len(llm), 3),
                        "lexicon_prevalence": round(sum(lex) / len(lex), 3),
                        "kappa": kappa(llm, lex)}
    ks = [v["kappa"] for v in per_theme.values() if v["kappa"] is not None]
    crosstab: dict[str, dict[str, int]] = {}
    for r in coded:
        crosstab.setdefault(r.get("changed_from_prior", ""), {}).setdefault(r["llm_values_change"], 0)
        crosstab[r.get("changed_from_prior", "")][r["llm_values_change"]] += 1
    report = {
        "n_llm_coded": len(coded),
        "n_reused_identical": sum(r["llm_status"] == "reused_identical" for r in coded),
        "zero_theme_pages": {"llm": sum(not r["theme_categories"] for r in coded),
                             "lexicon": sum(not r.get("lexicon_theme_categories") for r in coded)},
        "unverified_themes_dropped_total": sum(int(r["llm_n_unverified_dropped"] or 0) for r in coded),
        "mean_kappa_across_themes": round(st.mean(ks), 3) if ks else None,
        "per_theme": per_theme,
        "deterministic_change_vs_llm_values_change": crosstab,
    }
    AGREEMENT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "per_theme"}, indent=2))
    print(f"Full report: {AGREEMENT}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--limit", type=int, help="code at most N snapshots (timing test)")
    ap.add_argument("--tickers", nargs="*")
    ap.add_argument("--check", action="store_true", help="only check Ollama + model")
    ap.add_argument("--merge-only", action="store_true", help="skip coding; merge cache + report")
    args = ap.parse_args()

    if not args.merge_only:
        check_ollama(args.model)
        if args.check:
            return
        run(args.model, args.limit, set(args.tickers) if args.tickers else None)
    merge_into_dataset()


if __name__ == "__main__":
    main()
