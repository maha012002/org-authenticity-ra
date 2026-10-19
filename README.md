# Organizational Authenticity — RA Recruitment Assignment

Proof of concept on **50 S&P 500 firms** (10 largest in each of Technology, Financials,
Healthcare, Consumer Discretionary, Energy), **2016–2024**.

**Research question:** Do the values companies *advertise* on About / mission pages match
the priorities that show up in their mandatory proxy statements (DEF 14A)? The gap between
stated and lived values is the authenticity signal this pipeline measures.

The intake survey (Google Form) is already completed separately. This repository is the
technical + written deliverable (code, data, decisions, and 1–2 page summaries per part).

## Layout
```
config/            companies, About-page URL seeds, theme codebook
common.py          shared paths, polite HTTP session (retries + rate limit)
part1/             stated values: Wayback → text → local-LLM analysis (+ keyword baseline) → dataset
part2/             lived values: SEC DEF 14A → text mining
part3/             authenticity index (stated vs lived)
part4/             extra analyses (COVID shift, redesign check, ESG-in-pay, rankings)
data/              outputs (caches, manifests, final CSVs)
DECISIONS.md       every judgment call and why
*/SUMMARY.md       written summaries for each part
```

## Method in one paragraph
For each firm-year we archive one About/values page (Wayback), clean the text, and detect
year-to-year change deterministically (archive digest + text similarity). A **local open-weight
LLM** (Qwen 2.5 **7B** via Ollama, schema-constrained JSON, temperature 0) then judges whether the
*values* content changed, codes 12 value themes with quoted evidence, and describes linguistic
shifts. A **keyword dictionary** over the same 12 themes is kept as a transparent baseline, and
the two methods' agreement is reported per theme (Cohen's kappa). Independently we pull that
year’s DEF 14A from EDGAR and score the same themes with the same dictionary, plus governance
flags (e.g. ESG language near compensation). Part 3 compares the two keyword theme profiles, so
both sides use the same instrument, and tests the index with a placebo check; Part 4
stress-tests the design.

## Run order
```bash
python -m venv .venv && .venv\Scripts\activate          # Windows
pip install -r requirements.txt

# Part 1 (~1–2 h for Wayback collect)
python part1/collect_snapshots.py --contact you@upenn.edu
python part1/extract_text.py
python part1/code_themes.py          # keyword baseline + deterministic change detection
python part1/build_dataset.py        # -> data/part1/part1_stated_values.csv

# Part 1 LLM step (free, local): install Ollama from https://ollama.com, then
ollama pull qwen2.5:7b
python part1/analyze_llm.py --limit 5   # timing test, prints an ETA
python part1/analyze_llm.py             # full run (resumable); merges LLM columns + agreement report
python part1/handcheck_sheet.py make    # human hand-check sheet (20 pages); fill it in, then:
python part1/handcheck_sheet.py score   # -> data/part1/handcheck_results.json

# Part 2
python part2/fetch_proxy_statements.py --contact you@upenn.edu
python part2/mine_proxies.py         # -> data/part2/part2_lived_values.csv

# Part 3 + 4
python part3/authenticity_index.py
python part3/validity_checks.py      # distribution, placebo test, known-groups check
python part4/extra_analysis.py
```

## Status
- [x] Part 1 collection, extraction, change detection, keyword baseline, dataset
- [x] Part 1 local-LLM analysis (7B) + LLM-vs-keyword agreement + 20-page hand-check
- [x] Part 2 collection + text mining
- [x] Part 3 authenticity index + validity checks
- [x] Part 4 extra analyses
- [x] Written summaries (`part1`–`part4`/`SUMMARY.md`) and `DECISIONS.md`
- [x] Intake survey (Google Form, completed outside this repo)

## Key outputs
| File | What it is |
| --- | --- |
| `data/part1/part1_stated_values.csv` | Stated themes (LLM + keyword baseline), 450 company-years |
| `data/part1/llm_vs_lexicon_agreement.json` | Per-theme agreement between the LLM and keyword coding |
| `data/part1/handcheck_results.json` | Human hand-check precision/recall / page_type accuracy |
| `data/part2/part2_lived_values.csv` | Lived themes + proxy flags |
| `data/part3/authenticity_firm.csv` | Firm-level authenticity scores |
| `data/part3/sector_summary.csv` | Sector rollup |
| `data/part3/validity_report.json` | Distribution, placebo test, known-groups check |
| `data/part4/*` | COVID, redesign, ESG-in-pay, cheap-talk ranking |

## Use of AI tools
I used Cursor (with an AI coding assistant) to help write and debug pipeline scripts, fix
environment issues (SSL, SEC CIK overrides, Ollama setup), and draft repository docs. I also
pulled git bundles from Claude (an AI assistant) that added the local-LLM Part 1 step, Part 3
validity checks, the 7B rerun path, and the theme hand-check sheet. I ran the full Qwen 2.5 7B
coding pass on my laptop (~1.4 h), reviewed agreement and validity outputs, completed a 20-page
theme/page-type hand-check, and edited the Part 1 / Part 3 summaries so the interpretation
(including the website-driven sector ranking and placebo result) is in my own words.
Separately, Part 1 uses a **local open-weight LLM (Qwen 2.5 7B via Ollama)** as a research
instrument for theme coding—not as a substitute for my write-up.
