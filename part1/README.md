# Part 1 — Stated Values (Wayback Machine “About Us” pages)

## Goal
Measure what each firm *says* it values on its corporate About / mission / credo page,
once per year from 2016–2024, in a way that can later be compared to proxy-statement
language (Part 2).

## What I did
1. **`collect_snapshots.py`** — For each company, query the Wayback CDX API for several
   candidate About/values URLs (`config/about_url_seeds.csv`). Pick one capture per year
   (2016–2024), closest to July 1, preferring HTTP 200 HTML.
2. **`extract_text.py`** — Strip navigation, chrome, cookie banners, and the Wayback
   toolbar. Primary extractor: trafilatura; BeautifulSoup fallback for thin/JS pages.
3. **`code_themes.py`** — Deterministic change detection (archive digest + text similarity;
   `url_changed` if the seed URL moved) **and** a transparent **keyword baseline** over the
   12-theme codebook (cue → evidence snippet → salience 1–3).
4. **`analyze_llm.py`** — Local open-weight LLM (**Qwen 2.5 7B** via Ollama) judges values
   change, codes themes with quoted evidence (schema-constrained JSON; unverified quotes
   dropped), and notes linguistic shifts. One cache folder per model under
   `data/part1/llm_local_<model>/`.
5. **`handcheck_sheet.py`** — Sample 20 pages (4 per sector) for human judgment of theme
   labels and `page_type`; scores precision/recall vs the keyword baseline.
6. **`build_dataset.py`** — One row per company-year (all 450), including gaps. LLM columns
   are merged after the LLM pass.

## Why a local LLM *and* a keyword baseline
I wanted a coder that can catch paraphrase (“we exist to…” ≈ purpose/mission) without
paying for a commercial API. Qwen 2.5 7B via Ollama does that on my laptop (RTX 4050),
with temperature 0, a fixed seed, and JSON schema so invented codebook codes are
impossible. The keyword dictionary stays as the **transparent baseline**: every cue is
auditable, Part 2 uses the same instrument for lived values, and Part 3’s authenticity
index therefore compares like with like. Agreement between the two methods
(`data/part1/llm_vs_lexicon_agreement.json`) plus the hand-check are the validity checks
on the LLM pass.

## LLM vs keyword agreement (7B run)
From `llm_vs_lexicon_agreement.json` after coding 417 usable pages (10 identical digests
reused):

| Metric | Value |
| --- | ---: |
| Mean Cohen’s κ across themes | **0.42** |
| Themes dropped for unverified evidence | 86 |
| Zero-theme pages (LLM / lexicon) | 23 / 30 |
| Mean κ vs prior 3B run (robustness) | 0.26 |

Highest κ: integrity (0.62), environment_sustainability (0.58), purpose_mission (0.53).  
Lowest κ: shareholder_value (0.23), collaboration (0.26), performance_execution (0.30).  
Moderate agreement: the lexicon still over-fires on boilerplate, but 7B invents far fewer
unverifiable quotes than 3B (86 drops vs 723), so the LLM theme sets are denser and more
aligned with the dictionary.

## Hand-check (20 pages)
`python part1/handcheck_sheet.py make` then fill / score → `handcheck_results.json`:

| Method | Precision | Recall |
| --- | ---: | ---: |
| LLM (7B) | **0.85** | 0.74 |
| Keyword lexicon | 0.70 | **0.85** |

LLM `page_type` accuracy: **0.80**. Failures are mostly empty archive shells or a homepage
mislabeled as `general_about`.

## Page-identification criteria
- A page qualifies if it is the company’s own statement of who it is / what it values:
  About, Who-we-are, Mission/Values, Credo, or Leadership-principles on a corporate domain.
- Candidates are tried in priority order each year; the first clean archive wins so the
  series can follow redesigns. `url_changed` marks a URL switch so a redesign is not
  automatically treated as a values rewrite.
- **Seed notes:** Apple later years can land on `apple.com/careers` (weak for stated
  values). J&J correctly follows Credo URL moves (`about-jnj` → `credo` → `our-credo`).

## Missing snapshots and redirects
- Prefer HTTP 200 + HTML closest to July 1.
- If only redirects exist that year, follow the chain inside the archive (max 5 hops,
  must stay on web.archive.org) → status `redirect_followed`.
- Otherwise `missing`. No borrowing from neighbouring years.

## Theme categories
Codebook: `config/theme_codebook.json` (12 codes). Classic culture codes follow Guiso et
al. (2015) / MIT SMR Culture 500; ESG-era codes (DEI, environment, community, safety,
shareholder, purpose) exist so Parts 1–3 share one vocabulary. Kept all 12 after reading
MSFT/JNJ and spot-checking others.

## Assumptions
- Mid-year (July 1) is a neutral sampling date within each calendar year.
- About-page text is *stated* culture by design (marketing copy is the object of study).
- Gaps are informative and should remain visible in the panel.

## Known limitations
- Archive coverage is uneven; JS-rendered pages may archive as empty shells.
- One snapshot per year can miss a mid-year rewrite and back.
- Local models can still paraphrase quotes; the verifier drops them (86 this run).
- Keyword baseline over-matches boilerplate; LLM under-matches some clear cues (lower recall).

## With more time
Fix weak seeds (Apple careers); expand the hand-check beyond 20 pages; extend seeds to all
S&P 500.
