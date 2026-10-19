# Part 3 summary — Authenticity index

## Question
Where do firms’ About-page value themes align with what their proxy statements emphasize?

## Method
For each company-year with both a usable About snapshot and a DEF 14A, compare the
12-theme salience vectors from Parts 1 and 2:

**authenticity = cosine(stated, lived) − 0.5 × cheap_talk**

where cheap talk is the average positive gap (stated salience minus lived salience).
Higher authenticity means the website themes also show up in the proxy; high cheap talk
means the website emphasizes values the proxy barely echoes.

**Matched company-years in this run:** 396.

## Results
Sector mean authenticity (higher = more aligned):

| Sector | Mean authenticity | Mean cheap talk | Share ESG-near-comp (firm avg) |
| --- | ---: | ---: | ---: |
| Healthcare | 0.60 | 0.04 | 0.82 |
| Energy | 0.58 | 0.01 | 0.93 |
| Consumer Discretionary | 0.55 | 0.04 | 0.78 |
| Financials | 0.48 | 0.05 | 0.84 |
| Technology | 0.47 | 0.03 | 0.92 |

On this POC measure, Healthcare and Energy look more aligned than Technology and
Financials. Energy also shows the lowest mean cheap talk.

## Interpretation guide
- High authenticity, low cheap talk → About themes also appear in governance text.  
- High cheap talk → website says more than the proxy reflects.  
- Low alignment with low cheap talk → quiet on both sides (not the same as hypocrisy).

## Deliverables
`data/part3/authenticity_company_year.csv`, `authenticity_firm.csv`, `sector_summary.csv`.

## Limitations
Scores inherit dictionary noise from Parts 1–2. The 0.5 cheap-talk weight is a modeling
choice, not a structural constant — reweight using the reported components if needed.
