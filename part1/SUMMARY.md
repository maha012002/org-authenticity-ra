# Part 1 summary — Stated values

## Question
What values do large U.S. firms advertise on their corporate About / mission pages, and
how stable are those statements from 2016 to 2024?

## Sample and data
50 S&P 500 firms (10 per sector × Technology, Financials, Healthcare, Consumer
Discretionary, Energy). For each firm-year I collected one Wayback Machine capture of a
candidate About/values URL, preferring the archive closest to July 1. Multiple seed URLs
per firm (priority order) let the series follow redesigns. Missing years stay missing.

**Coverage in this run:** 417 of 450 company-years have a usable snapshot (93%).

## Method
1. **Collect** archived HTML via the Wayback CDX API; follow in-archive redirects when
   needed; never fill gaps from neighbouring years.
2. **Extract** main text (trafilatura, BeautifulSoup fallback).
3. **Detect change** with Wayback digests and text similarity; flag `url_changed` when
   the winning seed URL moves.
4. **Code themes** with a shared 12-category dictionary (keyword cues → theme + evidence
   snippet + salience 1–3), anchored in Guiso et al. (2015) and MIT SMR Culture 500,
   plus ESG-era codes for Part 2/3 comparability.

## Main findings (operational)
- Multi-seed URLs matter: firms such as J&J move Credo content across URLs; priority
  search recovers a continuous series.
- Some seeds are weak (Apple careers in later years) — those rows need caution.
- Year-to-year About text is often stable; large text shifts frequently coincide with
  URL changes (redesigns), which Part 4 quantifies.

## Deliverable
`data/part1/part1_stated_values.csv` — 450 rows with cleaned text, change class,
theme salience columns (`theme__*`), provenance (seed URL, Wayback URL), and notes.

## Limitations
Dictionary coding misses paraphrase and can hit boilerplate; archive shells yield short
or empty text; one July snapshot can miss intra-year churn. These are acceptable for a
proof of concept and are documented for later hardening.
