# Part 3 — Authenticity index

## Goal
Quantify, for each company-year with both an About snapshot and a DEF 14A, how closely
**stated** theme salience matches **lived** theme salience (keyword vectors on both sides).

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
`validity_checks.py` adds distribution stats, a wrong-firm placebo, and known-groups gaps.

## Why this form
Pure alignment rewards firms that are quiet on both sides. Subtracting a cheap-talk
penalty separates “consistently silent” from “talks values the proxy never echoes.”
The 0.5 weight is a transparent judgment call (see `DECISIONS.md`); raw alignment and
cheap-talk are also reported so a reader can reweight.

## Run
```bash
python part3/authenticity_index.py
python part3/validity_checks.py
```

## Outputs
- `data/part3/authenticity_company_year.csv`
- `data/part3/authenticity_firm.csv`
- `data/part3/sector_summary.csv`
- `data/part3/validity_report.json`

## Assumptions
- Keyword theme vectors from Parts 1 and 2 are comparable year-by-year (same codebook,
  same salience scale 0–3).
- Cosine similarity is a reasonable summary of 12-theme alignment; the 0.5 cheap-talk
  weight is a modeling choice, not an estimated parameter.
- Firm-level means are meaningful when a firm has at least one matched company-year
  (49 firms; AVGO dropped).

## Limitations
- Authenticity scores are tightly bunched in practice (mean 0.54, SD 0.22; IQR 0.42–0.69),
  so small rank gaps are easy to over-interpret.
- Lived-side saturation (~95% of proxies hit ≥10 themes; mean ~11.1 themes per proxy vs
  ~4.7 on About pages) makes sector rankings mostly website-driven.
- Placebo gap is small (true mean 0.54 vs shuffled 0.51), so the index has limited
  firm-specific signal beyond theme density.
- ESG-in-pay is on in 338/396 matched years (~85%), so known-groups checks using that
  flag are weak.

## With more time
Count a lived theme only when a firm’s proxy **stresses it more than other firms’
proxies that same year** (e.g. relative salience or TF–IDF-style rarity across the cross
section). That would cut through the current problem that ~95% of proxies hit 10+ themes
and would make the lived side more discriminative for authenticity rankings.
