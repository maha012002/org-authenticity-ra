# Decisions log

Judgment calls made while building the proof of concept. Alternatives and reasons are
recorded so the summaries stay auditable.

| Date | Part | Decision | Alternatives considered | Why |
| --- | --- | --- | --- | --- |
| 2026-10-15 | 1 | One capture per year, closest to July 1 | Earliest / latest in year | Even spacing across years |
| 2026-10-15 | 1 | Multiple seed URLs per firm, priority order | Single fixed URL | About pages move in redesigns |
| 2026-10-15 | 1 | Never fill a missing year from a neighbour | Forward-fill | Would hide real gaps and fake stability |
| 2026-10-15 | 1 | Change = archive digest + text similarity (+ `url_changed`) | Subjective “values change” only | Transparent, reproducible baseline |
| 2026-10-15 | 2 | Proxy statements (DEF 14A) from EDGAR | ESG/DEI reports from IR sites | Mandatory, standard coverage; pay language reveals priorities |
| 2026-10-19 | 1–2 | Dictionary (keyword) coding on a shared 12-theme codebook | Hand-code only; open-ended tagging | Scalable, auditable, same vocabulary for stated vs lived |
| 2026-10-19 | 2 | Structural flags (ESG-near-comp, climate, DEI/HC, proposals) on top of themes | Theme scores alone | Proxies are long; flags are sharper “revealed priority” signals |
| 2026-10-19 | 2 | CIK overrides: BLK→1364742, XOM→34088 | Trust `company_tickers.json` alone | Map pointed at post-reorg shells without historical DEF 14As |
| 2026-10-19 | 3 | `authenticity = cosine(stated, lived) − 0.5 × cheap_talk` | Cosine only; binary hypocrisy flag | Cosine alone rewards mutual silence; penalty is transparent |
| 2026-10-19 | 4 | Four extras: COVID shift, redesign confound, ESG-in-pay trend, cheap-talk rank | Scandal event study | Feasible on the POC panel; redesign check protects Part 1 validity |
