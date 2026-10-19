"""Part 3: authenticity index — compare Part 1 stated themes vs Part 2 lived themes.

For each company-year with both a usable About snapshot and a DEF 14A:
  * Build salience vectors (0-3) over the shared codebook.
  * gap_theme = stated - lived  (positive => talks more than proxies show)
  * cosine similarity of the two vectors (alignment)
  * jaccard of non-zero theme sets
  * cheap_talk_score = mean(max(stated - lived, 0)) over themes
  * understatement_score = mean(max(lived - stated, 0))
  * authenticity_index = alignment - 0.5 * cheap_talk_score   (higher = more aligned)

Also writes firm-level means (2016-2024) for cross-sectional comparison.

Outputs:
  data/part3/authenticity_company_year.csv
  data/part3/authenticity_firm.csv
  data/part3/sector_summary.csv
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import CONFIG, DATA, load_companies  # noqa: E402

P1 = DATA / "part1" / "part1_stated_values.csv"
P2 = DATA / "part2" / "part2_lived_values.csv"
OUT = DATA / "part3"
OUT.mkdir(parents=True, exist_ok=True)


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return round(dot / (na * nb), 4)


def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return round(len(a & b) / len(a | b), 4)


def main() -> None:
    codes = list(json.loads((CONFIG / "theme_codebook.json").read_text())["categories"])
    with open(P1, newline="", encoding="utf-8") as f:
        stated = {(r["ticker"], int(r["year"])): r for r in csv.DictReader(f)}
    with open(P2, newline="", encoding="utf-8") as f:
        lived = {(r["ticker"], int(r["year"])): r for r in csv.DictReader(f)}

    cy_fields = [
        "ticker", "company_name", "sector", "year", "has_stated", "has_lived",
        "alignment_cosine", "theme_jaccard", "cheap_talk_score", "understatement_score",
        "authenticity_index", "stated_n_themes", "lived_n_themes",
        "esg_in_compensation", "climate_disclosure", "dei_board_or_hc",
    ] + [f"gap__{c}" for c in codes]

    cy_rows = []
    for comp in load_companies():
        t = comp["ticker"]
        for y in range(2016, 2025):
            s, l = stated.get((t, y), {}), lived.get((t, y), {})
            has_s = s.get("snapshot_status") in ("ok", "redirect_followed") and int(s.get("text_chars") or 0) >= 300
            has_l = l.get("proxy_status") == "ok"
            sv = [int(s.get(f"theme__{c}") or 0) for c in codes] if has_s else [0] * len(codes)
            lv = [int(l.get(f"theme__{c}") or 0) for c in codes] if has_l else [0] * len(codes)
            gaps = [sv[i] - lv[i] for i in range(len(codes))]
            cheap = round(sum(max(g, 0) for g in gaps) / len(codes), 4)
            under = round(sum(max(-g, 0) for g in gaps) / len(codes), 4)
            align = cosine(sv, lv) if (has_s and has_l) else ""
            jac = jaccard({c for c, v in zip(codes, sv) if v}, {c for c, v in zip(codes, lv) if v}) if (has_s and has_l) else ""
            auth = ""
            if has_s and has_l:
                auth = round(float(align) - 0.5 * cheap, 4)
            cy_rows.append({
                "ticker": t, "company_name": comp["company_name"], "sector": comp["sector"], "year": y,
                "has_stated": int(has_s), "has_lived": int(has_l),
                "alignment_cosine": align, "theme_jaccard": jac,
                "cheap_talk_score": cheap if (has_s and has_l) else "",
                "understatement_score": under if (has_s and has_l) else "",
                "authenticity_index": auth,
                "stated_n_themes": sum(v > 0 for v in sv),
                "lived_n_themes": sum(v > 0 for v in lv),
                "esg_in_compensation": l.get("esg_in_compensation", ""),
                "climate_disclosure": l.get("climate_disclosure", ""),
                "dei_board_or_hc": l.get("dei_board_or_hc", ""),
                **{f"gap__{c}": gaps[i] if (has_s and has_l) else "" for i, c in enumerate(codes)},
            })

    with open(OUT / "authenticity_company_year.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cy_fields)
        w.writeheader()
        w.writerows(cy_rows)

    # Firm-level means over years with both sides present
    firm_fields = [
        "ticker", "company_name", "sector", "n_years_both", "mean_authenticity",
        "mean_alignment", "mean_cheap_talk", "mean_understatement", "pct_esg_in_comp",
    ]
    firm_rows = []
    for comp in load_companies():
        t = comp["ticker"]
        both = [r for r in cy_rows if r["ticker"] == t and r["authenticity_index"] != ""]
        if not both:
            firm_rows.append({
                "ticker": t, "company_name": comp["company_name"], "sector": comp["sector"],
                "n_years_both": 0, "mean_authenticity": "", "mean_alignment": "",
                "mean_cheap_talk": "", "mean_understatement": "", "pct_esg_in_comp": "",
            })
            continue
        def avg(key):
            return round(sum(float(r[key]) for r in both) / len(both), 4)
        esg = [r for r in both if str(r.get("esg_in_compensation")) in ("0", "1")]
        firm_rows.append({
            "ticker": t, "company_name": comp["company_name"], "sector": comp["sector"],
            "n_years_both": len(both),
            "mean_authenticity": avg("authenticity_index"),
            "mean_alignment": avg("alignment_cosine"),
            "mean_cheap_talk": avg("cheap_talk_score"),
            "mean_understatement": avg("understatement_score"),
            "pct_esg_in_comp": round(sum(int(r["esg_in_compensation"]) for r in esg) / len(esg), 4) if esg else "",
        })

    with open(OUT / "authenticity_firm.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=firm_fields)
        w.writeheader()
        w.writerows(firm_rows)

    # Sector summary
    sectors = sorted({r["sector"] for r in firm_rows})
    sec_fields = ["sector", "n_firms", "mean_authenticity", "mean_cheap_talk", "mean_pct_esg_in_comp"]
    sec_rows = []
    for sec in sectors:
        rs = [r for r in firm_rows if r["sector"] == sec and r["mean_authenticity"] != ""]
        if not rs:
            continue
        sec_rows.append({
            "sector": sec, "n_firms": len(rs),
            "mean_authenticity": round(sum(float(r["mean_authenticity"]) for r in rs) / len(rs), 4),
            "mean_cheap_talk": round(sum(float(r["mean_cheap_talk"]) for r in rs) / len(rs), 4),
            "mean_pct_esg_in_comp": round(
                sum(float(r["pct_esg_in_comp"]) for r in rs if r["pct_esg_in_comp"] != "") /
                max(1, sum(r["pct_esg_in_comp"] != "" for r in rs)), 4),
        })
    with open(OUT / "sector_summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=sec_fields)
        w.writeheader()
        w.writerows(sec_rows)

    n_both = sum(r["authenticity_index"] != "" for r in cy_rows)
    print(f"Wrote {OUT / 'authenticity_company_year.csv'} ({n_both} matched company-years)")
    print(f"Wrote {OUT / 'authenticity_firm.csv'} and {OUT / 'sector_summary.csv'}")


if __name__ == "__main__":
    main()
