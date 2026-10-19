# Organizational Authenticity — RA Recruitment Assignment

Proof of concept on **50 S&P 500 firms** (10 largest in each of Technology, Financials,
Healthcare, Consumer Discretionary, Energy), **2016–2024**.

**Research question:** Do the values companies *advertise* on About / mission pages match
the priorities that show up in their mandatory proxy statements (DEF 14A)? The gap between
stated and lived values is the authenticity signal this pipeline measures.

The Qualtrics intake survey is already completed separately. This repository is the
technical + written deliverable (code, data, decisions, and 1–2 page summaries per part).

## Layout
```
config/            companies, About-page URL seeds, theme codebook
common.py          shared paths, polite HTTP session (retries + rate limit)
part1/             stated values: Wayback → text → dictionary coding → dataset
part2/             lived values: SEC DEF 14A → text mining
part3/             authenticity index (stated vs lived)
part4/             extra analyses (COVID shift, redesign check, ESG-in-pay, rankings)
data/              outputs (caches, manifests, final CSVs)
DECISIONS.md       every judgment call and why
*/SUMMARY.md       written summaries for each part
```

## Method in one paragraph
For each firm-year we archive one About/values page (Wayback), clean the text, detect
year-to-year change with digests + similarity, and score 12 value themes with a shared
**keyword dictionary**. Independently we pull that year’s DEF 14A from EDGAR and score the
same themes plus governance flags (e.g. ESG language near compensation). Part 3 compares
the two theme profiles; Part 4 stress-tests the design.

## Run order
```bash
python -m venv .venv && .venv\Scripts\activate          # Windows
pip install -r requirements.txt

# Part 1 (~1–2 h for Wayback collect)
python part1/collect_snapshots.py --contact you@upenn.edu
python part1/extract_text.py
python part1/code_themes.py          # or: python part1/analyze_llm.py
python part1/build_dataset.py        # -> data/part1/part1_stated_values.csv

# Part 2
python part2/fetch_proxy_statements.py --contact you@upenn.edu
python part2/mine_proxies.py         # -> data/part2/part2_lived_values.csv

# Part 3 + 4
python part3/authenticity_index.py
python part4/extra_analysis.py
```

## Status
- [x] Part 1 collection, extraction, change detection, dictionary coding, dataset
- [x] Part 2 collection + text mining
- [x] Part 3 authenticity index
- [x] Part 4 extra analyses
- [x] Written summaries (`part1`–`part4`/`SUMMARY.md`) and `DECISIONS.md`
- [x] Qualtrics survey (completed outside this repo)

## Key outputs
| File | What it is |
| --- | --- |
| `data/part1/part1_stated_values.csv` | Stated themes, 450 company-years |
| `data/part2/part2_lived_values.csv` | Lived themes + proxy flags |
| `data/part3/authenticity_firm.csv` | Firm-level authenticity scores |
| `data/part3/sector_summary.csv` | Sector rollup |
| `data/part4/*` | COVID, redesign, ESG-in-pay, cheap-talk ranking |
