# Part 3 — Authenticity index

## Goal
Quantify, for each company-year with both an About snapshot and a DEF 14A, how closely
**stated** theme salience matches **lived** theme salience.

## Definition
Let \(s\) and \(\ell\) be 12-dimensional salience vectors (0–3) from Parts 1 and 2.

| Quantity | Meaning |
| --- | --- |
| `alignment_cosine` | Cosine similarity of \(s\) and \(\ell\) |
| `theme_jaccard` | Overlap of non-zero theme sets |
| `cheap_talk_score` | Mean of \(\max(s_i - \ell_i, 0)\) — says more than proxy shows |
| `understatement_score` | Mean of \(\max(\ell_i - s_i, 0)\) |
| `authenticity_index` | `alignment_cosine − 0.5 × cheap_talk_score` |

Firm-level means average over years where both sides exist. Sector summaries average firms.

## Why this form
Pure alignment rewards firms that are quiet on both sides. Subtracting a cheap-talk
penalty separates “consistently silent” from “talks values the proxy never echoes.”
The 0.5 weight is a transparent judgment call (see `DECISIONS.md`); raw alignment and
cheap-talk are also reported so a reader can reweight.

## Run
```bash
python part3/authenticity_index.py
```

## Outputs
- `data/part3/authenticity_company_year.csv`
- `data/part3/authenticity_firm.csv`
- `data/part3/sector_summary.csv`
