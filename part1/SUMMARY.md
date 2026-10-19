# Part 1 summary — Stated values

## Question
What values do large U.S. firms advertise on their corporate About / mission pages, and
how stable are those statements from 2016 to 2024?

## Sample and data
50 S&P 500 firms (10 per sector × Technology, Financials, Healthcare, Consumer
Discretionary, Energy). One Wayback capture per firm-year, closest to July 1, from a
priority list of About/values URL seeds. Missing years stay missing.

**Coverage:** 417 / 450 company-years have a usable snapshot (93%).

## Method
1. Collect archived HTML (CDX API; follow in-archive redirects; never forward-fill gaps).
2. Extract main text (trafilatura / BeautifulSoup fallback).
3. **Keyword baseline** (`code_themes.py`): digest + similarity change classes, plus
   dictionary theme coding on the shared 12-code codebook.
4. **Local LLM** (`analyze_llm.py`, **Qwen 2.5 7B** via Ollama): schema-constrained JSON for
   values change, themes with evidence, linguistic shift. Identical digests reuse the
   prior year’s coding. Unverified evidence quotes are dropped. Cache folder is
   per-model (`data/part1/llm_local_qwen2.5-7b/`; the earlier 3B run is kept for
   robustness comparison).

I used both on purpose: the LLM handles paraphrase; the keyword pass is transparent,
feeds Part 2/3 with the same instrument, and gives a Cohen’s κ agreement report.

## Agreement and hand-check
From `data/part1/llm_vs_lexicon_agreement.json` (417 coded pages; 10 identical digests
reused):
- **Mean κ across themes = 0.42** (best: integrity 0.62, environment 0.58, purpose 0.53;
  weakest: shareholder_value 0.23, collaboration 0.26).
- Unverified theme quotes dropped: **86** (much lower than the 3B run).
- Zero-theme pages: LLM 23 / lexicon 30.
- Page-type mix: mostly `values_or_mission` (365), plus `general_about` (42),
  `homepage` (5), `other` (5).
- **3B vs 7B robustness** (same pages): mean κ ≈ **0.26** — the larger model is not a
  carbon copy of the small one; 7B agrees better with the keyword baseline.

On a **20-page theme hand-check** (`handcheck_sheet.py` → `handcheck_results.json`):
- LLM precision **0.85**, recall **0.74**; lexicon precision **0.70**, recall **0.85**.
- LLM `page_type` accuracy **0.80** (4/20 wrong: empty/shell pages or homepage mislabeled).

## Operational findings
- Multi-seed URLs matter (e.g. J&J Credo path changes).
- Some seeds are weak (Apple careers / thin archive shells) — treat those rows cautiously.
- Large text shifts often coincide with `url_changed` (redesigns); Part 4 quantifies this.

## Deliverable
`data/part1/part1_stated_values.csv` (LLM + lexicon columns), plus
`llm_vs_lexicon_agreement.json`, `handcheck_results.json`, and per-model LLM caches.

## Limitations
Archive shells, single July snapshot, and imperfect LLM–lexicon agreement. Part 3’s
authenticity index deliberately uses the **keyword** theme vectors on both sides so the
comparison stays apples-to-apples.
