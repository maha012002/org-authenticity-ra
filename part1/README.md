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
3. **`code_themes.py`** — (a) Deterministic change detection (archive digest + text
   similarity; `url_changed` if the seed URL moved). (b) Dictionary coding of themes
   against `config/theme_codebook.json`, with a short evidence snippet per theme.
4. **`build_dataset.py`** — One row per company-year (all 450), including gaps.

## Page-identification criteria
- A page qualifies if it is the company’s own statement of who it is / what it values:
  About, Who-we-are, Mission/Values, Credo, or Leadership-principles on a corporate domain.
- Candidates are tried in priority order each year; the first clean archive wins so the
  series can follow redesigns. `url_changed` marks a URL switch so a redesign is not
  automatically treated as a values rewrite.
- Rule-based `page_type` marks weak pages (`not_usable` if extracted text &lt; 300 chars;
  `values_or_mission` vs `general_about` from cue words). Rows with careers/homepage
  seeds need hand review.
- **Seed notes after the run:** Apple later years can land on `apple.com/careers` (weak
  for stated values). J&amp;J correctly follows Credo URL moves
  (`about-jnj` → `credo` → `our-credo`).

## Missing snapshots and redirects
- Prefer HTTP 200 + HTML closest to July 1.
- If only redirects exist that year, follow the chain inside the archive (max 5 hops,
  must stay on web.archive.org) → status `redirect_followed`.
- Otherwise `missing`. No borrowing from neighbouring years. Change detection only
  compares consecutive years that both exist.

## Theme categories
Codebook: `config/theme_codebook.json` (12 codes).

| Group | Codes | Anchor |
| --- | --- | --- |
| Classic culture | integrity, customer, innovation, collaboration, respect_people, performance_execution | Guiso et al. (2015); MIT SMR Culture 500 |
| ESG-era / comparison | diversity_inclusion, environment_sustainability, community_social_impact, safety, shareholder_value, purpose_mission | Needed so Parts 1 and 2 share one vocabulary |

Kept all 12 after reading MSFT/JNJ and spot-checking others. Did not merge DEI into
“respect” — that would hide a distinct ESG-era signal.

## Coding method (dictionary)
For each cleaned About page, scan for conservative keyword cues per code (see
`LEXICON` in `code_themes.py`). If any cue hits, assign the theme with:
- **evidence** = short snippet around the first cue  
- **salience** = 1–3 from how often cues appear  

This is transparent and reproducible. It can miss paraphrases and can over-match
boilerplate; that tradeoff is intentional for a scalable POC.

## Assumptions
- Mid-year (July 1) is a neutral sampling date within each calendar year.
- About-page text is *stated* culture by design (marketing copy is the object of study).
- Gaps are informative and should remain visible in the panel.

## Known limitations
- Archive coverage is uneven; JS-rendered pages may archive as empty shells.
- One snapshot per year can miss a mid-year rewrite and back.
- Dictionary coding is keyword-based (precision over recall).
- Weak seeds (e.g. Apple careers) should be fixed before scaling to all 500 firms.

## With more time
Fix weak seeds; hand-validate ~20 rows against the codebook; parse more About URL
variants; extend `companies.csv` / seeds to the full S&P 500.
