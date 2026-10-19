# Part 4 summary — Extra analyses

## Why these four
They answer threats to validity and add a simple longitudinal story on top of Part 3.

## 1. COVID-era stated shift (2019 → 2021)
Among 46 firms with usable About text in both years, mean salience rose most for:
- **diversity_inclusion** (+0.41)  
- **purpose_mission** (+0.33)  
- **performance_execution** (+0.24)  
- **customer** / **environment_sustainability** (+0.20 each)  

So About-page language did shift toward DEI and purpose around the pandemic window —
useful context when interpreting authenticity scores in those years.

## 2. Redesign vs “values change”
Of **42** consecutive years where the winning About URL changed, **37** were also coded
`substantive_change` on text similarity. Redesigns often rewrite page copy. The
`url_changed` flag is therefore essential: without it, a site migration looks like a
values rewrite.

## 3. ESG language near compensation
Share of proxies with ESG/DEI/climate cues near pay language:

| Year | Pct |
| --- | ---: |
| 2016 | 61% |
| 2019 | 86% |
| 2021 | 94% |
| 2024 | 98% |

Treat this as an **upper-bound diffusion** measure (dictionary flag, not a parsed CD&A
metric list). Directionally, lived ESG talk in the pay section became nearly universal.

## 4. Cheap-talk ranking
Highest mean cheap-talk firms in this run include Charles Schwab, Citigroup, Nike,
Tesla, and NVIDIA (`data/part4/cheap_talk_ranking.csv`). These are candidates for
qualitative follow-up, not automatic accusations of hypocrisy.

## Deliverables
`covid_stated_shift_2019_2021.csv`, `covid_theme_mean_deltas.csv`,
`redesign_vs_values.json`, `esg_in_pay_by_year.csv`, `cheap_talk_ranking.csv`.
