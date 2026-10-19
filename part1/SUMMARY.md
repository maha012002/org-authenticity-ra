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
4. **Local LLM** (`analyze_llm.py`, Qwen 2.5 3B via Ollama): schema-constrained JSON for
   values change, themes with evidence, linguistic shift. Identical digests reuse the
   prior year’s coding. Unverified evidence quotes are dropped.

I used both on purpose: the LLM handles paraphrase; the keyword pass is transparent,
feeds Part 2/3 with the same instrument, and gives a Cohen’s κ agreement report.

## Agreement and hand-check
From `data/part1/llm_vs_lexicon_agreement.json` (416 coded pages):
- **Mean κ across themes = 0.23** (best: purpose_mission 0.45; weakest: shareholder_value 0.07).
- Lexicon marks more pages with themes than the LLM (29 vs 90 zero-theme pages).
- On a random hand-check of **20 pages** (`handcheck_20.json`), **87%** of kept theme
  evidence strings appeared in the page text (68/78).

## Operational findings
- Multi-seed URLs matter (e.g. J&J Credo path changes).
- Some seeds are weak (Apple careers) — treat those rows cautiously.
- Large text shifts often coincide with `url_changed` (redesigns); Part 4 quantifies this.

## Deliverable
`data/part1/part1_stated_values.csv` (LLM + lexicon columns), plus
`llm_vs_lexicon_agreement.json` and `llm_local/` caches.

## Limitations
Archive shells, single July snapshot, and imperfect LLM–lexicon agreement. Part 3’s
authenticity index deliberately uses the **keyword** theme vectors on both sides so the
comparison stays apples-to-apples.
