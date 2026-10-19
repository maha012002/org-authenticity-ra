# Part 4 summary — Extra analyses

## Main question
Did companies’ stated values shift toward DEI and purpose around 2020, and is that shift
real or just a site redesign?

## Finding: COVID-era stated shift (2019 → 2021)
Among **46** firms with usable About text in both years, mean keyword salience rose most for:
- **diversity_inclusion** (+0.41)
- **purpose_mission** (+0.33)
- **performance_execution** (+0.24)
- **customer** / **environment_sustainability** (+0.20 each)

So About-page language did move toward DEI and purpose in the pandemic window — useful
context when reading authenticity scores for those years.

## Control: redesign vs “values change”
Of **42** consecutive years where the winning About URL changed, **37** were also coded
`substantive_change` on text similarity (3 stayed identical). Redesigns often rewrite page
copy. The `url_changed` flag is therefore essential: without it, a site migration looks
like a values rewrite. The 2019→2021 DEI/purpose rise should be read with that confound
in mind — some of the panel’s “change” is URL churn, not a board-level values rewrite.

## Related checks (same Part 4 outputs)
**ESG language near compensation.** Share of proxies with ESG/DEI/climate cues near pay
language rose from **61%** (2016) to **98%** (2024). Treat as an upper-bound diffusion
measure (dictionary flag, not a parsed CD&A metric list).

**Cheap-talk ranking.** Highest mean cheap-talk firms in this run include Charles Schwab,
Citigroup, Nike, Tesla, and NVIDIA (`data/part4/cheap_talk_ranking.csv`). Candidates for
qualitative follow-up, not automatic accusations of hypocrisy.

## Deliverables
`covid_stated_shift_2019_2021.csv`, `covid_theme_mean_deltas.csv`,
`redesign_vs_values.json`, `esg_in_pay_by_year.csv`, `cheap_talk_ranking.csv`.
