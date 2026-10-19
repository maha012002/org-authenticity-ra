# Part 4 — Extra analyses

Four checks that go beyond the core index and protect (or extend) the design:

1. **COVID-era stated shift (2019 → 2021)** — Which About-page themes rose?
2. **Redesign confound** — When `url_changed`, how often is change class substantive?
3. **ESG-in-pay diffusion** — Share of proxies with ESG language near compensation, by year
4. **Cheap-talk ranking** — Firms with the largest mean stated − lived gaps

```bash
python part4/extra_analysis.py
```

Outputs: `data/part4/`. Narrative: `part4/SUMMARY.md`.

## With more time
Recompute the COVID and cheap-talk tables using **LLM-coded** About themes (not only the
keyword baseline), and replace the ESG-in-pay keyword flag with a parsed CD&A metric list
so the diffusion curve is not inflated by boilerplate near the word “compensation.”
