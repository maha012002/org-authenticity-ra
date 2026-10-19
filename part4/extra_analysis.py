"""Part 4: extra analyses that go beyond the core authenticity index.

Analyses:
  A. COVID-era stated-values shift: compare 2019 vs 2021 About-page theme vectors
     (did firms add DEI / community / environment language around the pandemic?).
  B. Redesign vs values: among consecutive years with url_changed=True, how often
     does change_class say substantive_change? (false-positive risk of redesigns).
  C. ESG-in-pay diffusion: share of firms with esg_in_compensation=1 by year/sector.
  D. Cheap-talk leaders: firms with highest mean cheap_talk_score (say > do).

Outputs under data/part4/.
"""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import CONFIG, DATA, load_companies  # noqa: E402

OUT = DATA / "part4"
OUT.mkdir(parents=True, exist_ok=True)
CODES = list(json.loads((CONFIG / "theme_codebook.json").read_text())["categories"])


def load_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> None:
    stated = load_csv(DATA / "part1" / "part1_stated_values.csv")
    lived = load_csv(DATA / "part2" / "part2_lived_values.csv")
    firms = load_csv(DATA / "part3" / "authenticity_firm.csv")
    changes = []
    ch_path = DATA / "part1" / "change_detection.csv"
    if ch_path.exists():
        changes = load_csv(ch_path)

    # A. COVID shift 2019 -> 2021
    by_ty = {(r["ticker"], int(r["year"])): r for r in stated}
    covid_rows = []
    for comp in load_companies():
        t = comp["ticker"]
        a, b = by_ty.get((t, 2019)), by_ty.get((t, 2021))
        if not a or not b:
            continue
        if a.get("snapshot_status") not in ("ok", "redirect_followed"):
            continue
        if b.get("snapshot_status") not in ("ok", "redirect_followed"):
            continue
        row = {"ticker": t, "company_name": comp["company_name"], "sector": comp["sector"]}
        for c in CODES:
            row[f"d_{c}"] = int(b.get(f"theme__{c}") or 0) - int(a.get(f"theme__{c}") or 0)
        row["net_theme_delta"] = sum(row[f"d_{c}"] for c in CODES)
        covid_rows.append(row)
    with open(OUT / "covid_stated_shift_2019_2021.csv", "w", newline="", encoding="utf-8") as f:
        fields = ["ticker", "company_name", "sector", "net_theme_delta"] + [f"d_{c}" for c in CODES]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(covid_rows)

    # Theme-level mean deltas
    theme_shift = []
    for c in CODES:
        vals = [r[f"d_{c}"] for r in covid_rows]
        theme_shift.append({
            "theme": c,
            "mean_delta_2019_to_2021": round(sum(vals) / len(vals), 4) if vals else "",
            "n_firms": len(vals),
            "share_increased": round(sum(v > 0 for v in vals) / len(vals), 4) if vals else "",
        })
    with open(OUT / "covid_theme_mean_deltas.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["theme", "mean_delta_2019_to_2021", "n_firms", "share_increased"])
        w.writeheader()
        w.writerows(theme_shift)

    # B. Redesign vs values-change false positives
    redesign = {"n_url_changed": 0, "substantive_among_url_changed": 0, "identical_among_url_changed": 0}
    for r in changes:
        if str(r.get("url_changed")).lower() in ("true", "1"):
            redesign["n_url_changed"] += 1
            if r.get("change_class") == "substantive_change":
                redesign["substantive_among_url_changed"] += 1
            if r.get("change_class") in ("identical", "no_substantive_change"):
                redesign["identical_among_url_changed"] += 1
    with open(OUT / "redesign_vs_values.json", "w", encoding="utf-8") as f:
        json.dump(redesign, f, indent=2)

    # C. ESG-in-pay by year
    by_year = defaultdict(list)
    for r in lived:
        if r.get("proxy_status") == "ok" and r.get("esg_in_compensation") in ("0", "1"):
            by_year[int(r["year"])].append(int(r["esg_in_compensation"]))
    esg_year = [{"year": y, "n": len(by_year[y]),
                 "pct_esg_in_compensation": round(sum(by_year[y]) / len(by_year[y]), 4)}
                for y in sorted(by_year)]
    with open(OUT / "esg_in_pay_by_year.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["year", "n", "pct_esg_in_compensation"])
        w.writeheader()
        w.writerows(esg_year)

    # D. Cheap-talk ranking
    ranked = sorted(
        [r for r in firms if r.get("mean_cheap_talk") not in ("", None)],
        key=lambda r: -float(r["mean_cheap_talk"]),
    )
    with open(OUT / "cheap_talk_ranking.csv", "w", newline="", encoding="utf-8") as f:
        fields = ["ticker", "company_name", "sector", "mean_cheap_talk", "mean_authenticity",
                  "mean_alignment", "mean_understatement", "n_years_both", "pct_esg_in_comp"]
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(ranked)

    print(f"Part 4 outputs in {OUT}")
    print(f"  COVID pairs: {len(covid_rows)}")
    print(f"  URL-changed transitions: {redesign['n_url_changed']}")
    print(f"  ESG-in-pay years: {esg_year}")


if __name__ == "__main__":
    main()
