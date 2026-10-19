# Submission checklist

Intake survey (Google Form): **already completed** (outside this repo).

## What to turn in from this repository
1. **Code + config** — runnable Part 1–4 pipeline (`README.md` has the run order).
2. **Data outputs** — especially:
   - `data/part1/part1_stated_values.csv`
   - `data/part2/part2_lived_values.csv`
   - `data/part3/authenticity_firm.csv`, `sector_summary.csv`
   - `data/part4/*`
3. **Written explanations**
   - `part1/SUMMARY.md` … `part4/SUMMARY.md` (methods + results per part)
   - `part1/README.md` … `part4/README.md` (detailed design choices)
   - `DECISIONS.md` (judgment log)

## Method used for theme coding
- **Part 1 (required LLM pipeline):** local open-weight LLM via Ollama (`part1/analyze_llm.py`)
  codes values change, themes with quoted evidence, and linguistic shifts.
- **Keyword baseline:** shared 12-theme dictionary (`part1/code_themes.py`), also applied to
  proxy statements in Part 2 so the Part 3 index compares like with like. Agreement between
  the two Part 1 methods: `data/part1/llm_vs_lexicon_agreement.json`.

## Do not include
- Secrets or private `.env` files  
- Anything beyond the contact email already used in polite crawler User-Agents
