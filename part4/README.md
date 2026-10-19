# Part 4 — Extra analyses

One motivating question, plus supporting checks:

1. **COVID-era stated shift (2019 → 2021)** — Did About-page themes move toward DEI /
   purpose? (main finding)
2. **Redesign confound** — When `url_changed`, how often is change class substantive?
   (control for the COVID question)
3. **ESG-in-pay diffusion** — Share of proxies with ESG language near compensation, by year
4. **Cheap-talk ranking** — Firms with the largest mean stated − lived gaps

```bash
python part4/extra_analysis.py
```

Outputs: `data/part4/`. Narrative: `part4/SUMMARY.md`.

## Assumptions
- Comparing 2019 vs 2021 About-page keyword salience is a fair window for “COVID-era”
  stated-values language (46 firms with text in both years).
- `url_changed` marks a redesign / seed switch that can rewrite page copy even when the
  firm’s values did not change.
- The ESG-near-compensation flag is a presence check on proxy text, not a count of formal
  ESG pay metrics in the CD&A.

## Limitations
- The redesign control is coarse: **37/42** URL changes co-occur with `substantive_change`,
  so we cannot cleanly partial out “true” values rewrites from site migrations in the
  COVID window.
- ESG-in-pay diffusion reaches **98%** by 2024; the series is mostly saturated and will
  not discriminate firms well in later years.
- Cheap-talk ranks use the Part 3 keyword-based gap; they are exploratory, not causal
  evidence of hypocrisy.
- COVID and cheap-talk tables use the **keyword** About themes, not the LLM coding.

## With more time
Recompute the COVID and cheap-talk tables using **LLM-coded** About themes (not only the
keyword baseline), and replace the ESG-in-pay keyword flag with a parsed CD&A metric list
so the diffusion curve is not inflated by boilerplate near the word “compensation.”
