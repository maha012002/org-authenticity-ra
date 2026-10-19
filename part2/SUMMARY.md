# Part 2 summary — Lived values

## Question
What priorities do the same 50 firms reveal in mandatory DEF 14A proxy statements
(2016–2024), and how do those map onto the Part 1 theme codebook?

## Method
I pulled one DEF 14A per company-year from SEC EDGAR (prefer January–June filings),
converted HTML to text, and applied:
1. The **same keyword dictionary** as Part 1 for the 12 value themes.  
2. **Structural flags** for ESG language near compensation, board/DEI or human capital,
   climate disclosure, and ESG-related shareholder proposals.

CIK overrides were required for BlackRock and ExxonMobil because the public ticker map
pointed at entities without the historical proxy series.

**Coverage in this run:** 443 of 450 company-years have proxy text (98%).

## Why this design
Proxies are comparable across firms and years. Pay and governance sections are where
boards show what they reward — closer to “lived” priorities than marketing About pages
or voluntary ESG PDFs.

## Main findings (operational)
- Coverage is high enough for a firm-year panel after CIK fixes.  
- ESG-related language near compensation becomes very common by the early 2020s
  (see Part 4 trend).  
- Theme hits are widespread in long proxies; the structural flags are the sharper
  lived-values measures.

## Deliverable
`data/part2/part2_lived_values.csv` with theme salience columns and flags.

## Limitations
Keyword hits in 100+ page documents are noisy; fiscal lag means filing year ≠ pay year;
a handful of years remain missing on EDGAR.
