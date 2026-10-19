# Part 3 summary — Authenticity index

## Question
Where do firms’ About-page value themes align with what their proxy statements emphasize?

## Method
For each company-year with both a usable About snapshot and a DEF 14A, compare the
**keyword** 12-theme salience vectors from Parts 1 and 2 (same instrument on both sides):

**authenticity = cosine(stated, lived) − 0.5 × cheap_talk**

where cheap talk is the mean positive gap (stated − lived). Firm means average over years
with both sides; sector means average firms. Validity checks are in
`data/part3/validity_report.json` (`python part3/validity_checks.py`).

**Matched company-years:** 396. **AVGO is not scored** (no usable stated–lived overlap in
the panel after missing About text / proxies).

## Distribution of the authenticity index
Across the 396 matched company-years (`validity_report.json`):
- **Mean 0.54**, **SD 0.22** (min −0.25, max 1.0).
- Middle half of scores lies between **0.42 and 0.69** (25th–75th percentiles).
- **57%** of the variance is **between firms**; **43%** is within firms over time.

## Results (and what they really mean)
Sector mean authenticity:

| Sector | Mean authenticity | Mean cheap talk |
| --- | ---: | ---: |
| Healthcare | 0.60 | 0.04 |
| Energy | 0.58 | 0.01 |
| Consumer Discretionary | 0.55 | 0.04 |
| Financials | 0.48 | 0.05 |
| Technology | 0.47 | 0.03 |

**These sector rankings mostly reflect the websites, not sharp differences in proxies.**
About **95%** of usable proxies hit **10 or more** of the 12 themes (`lived_share_hitting_10plus`
= 0.949; mean themes per proxy ≈ 11.1 vs ≈ 4.7 on About pages). When almost every proxy
looks “full,” cosine alignment is driven by how rich or sparse the About-page vector is.
I am saying that plainly so the table is not over-interpreted as a ranking of “true”
corporate authenticity.

### Placebo (wrong-firm) check
Matching each About page to a **random other firm’s** proxy in the same year yields mean
authenticity **0.51**, versus **0.54** for the true pairing (difference 0.03;
one-sided *p* ≈ 0.005 over 200 permutations). The true pairs are slightly better than
chance, but the gap is small—consistent with proxies being saturated with themes.

## Limitations (at least two)
1. **Proxy theme saturation.** Keyword coding on long DEF 14As fires on nearly every
   theme (~95% of proxies hit ≥10 codes). That compresses lived-side variation and makes
   the authenticity score behave like a transform of stated-side density.
2. **ESG-in-pay flag is almost always on.** The structural flag
   `esg_in_compensation` is true in roughly **85%** of matched company-years (338/396),
   so it is a weak discriminator for known-groups checks.
3. **AVGO unscored** — missing from firm-level tables; do not treat Technology’s mean as
   a complete 10-firm average.
4. The 0.5 cheap-talk weight is a modeling choice; raw alignment and cheap talk are also
   reported.

## Deliverables
`authenticity_company_year.csv`, `authenticity_firm.csv`, `sector_summary.csv`,
`validity_report.json`.
