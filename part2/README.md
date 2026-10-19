# Part 2 — Lived values (SEC DEF 14A proxy statements)

## Goal
Measure priorities firms *reveal* in mandatory annual proxy statements, using the **same
theme vocabulary** as Part 1 so stated vs lived gaps are comparable.

## Why proxy statements (not ESG PDFs)
Voluntary sustainability / DEI reports start in different years, move around IR sites,
and are self-selected. DEF 14A filings are:
- **Mandatory** for U.S.-listed firms  
- Stored in one place (EDGAR)  
- Where boards explain executive pay, board composition, risk oversight, and shareholder
  proposals — a clearer “revealed preference” signal for this POC  

**Unit of observation:** calendar year of *filing*. A spring 2024 proxy usually describes
fiscal 2023 pay (lag noted in the summary).

## What I did
1. **`fetch_proxy_statements.py`** — Map ticker → CIK, list DEF 14As 2016–2024, prefer
   the earliest January–June filing (annual-meeting season), else earliest that year.
   Cache HTML + plain text. CIK overrides for BLK and XOM where the SEC ticker map
   pointed at post-reorg shells.
2. **`mine_proxies.py`** — Score the shared codebook with the same dictionary as Part 1,
   plus structural flags:
   - `esg_in_compensation` — ESG/DEI/climate terms near pay / incentive language  
   - `dei_board_or_hc` — board diversity or human-capital discussion  
   - `climate_disclosure` — climate / GHG / emissions language  
   - `shareholder_proposal_esg` — ESG-related shareholder proposals  

## Assumptions
- Theme keyword hits in a long proxy are a noisy signal of emphasis, not proof that a
  theme is a formal pay metric — use `esg_in_compensation` for the sharper claim.
- Missing DEF 14A years stay `missing` (not imputed).
- Berkshire is queried as `BRK-B` on EDGAR.

## Known limitations
- Dictionary coding over-matches boilerplate (“diversity” in a risk factor).
- No table parsing of CD&A metric lists yet.
- A few firm-years remain missing after CIK fixes (e.g. XOM 2021 on EDGAR).

## With more time
Parse compensation tables for named ESG metrics; hand-validate ~20 filings; add 10-K
human-capital items as a robustness check.

## Deliverable
`data/part2/part2_lived_values.csv` (+ `proxy_manifest.csv`, HTML/text caches).
