"""Part 3, step 2: distributional properties + validity checks for the authenticity index.

The brief asks for (a) basic distributional properties and (b) at least one validity check.
This script reports four things, all computed from existing Part 1-3 outputs (no network):

1. Distribution of the company-year index: n, mean, SD, quartiles, min/max, and how much
   of the variance is between firms vs. within firms over time (does it vary on both axes?).
2. Saturation diagnostic: how many of the 12 themes each source registers per document.
   If proxy statements (100+ pages) hit nearly every theme, the "lived" vector carries
   little firm-specific information and alignment mostly reflects the website side.
3. Placebo (permutation) test -- the main validity check. Pair each firm-year's stated
   vector with the lived vector of a DIFFERENT firm in the same year. If the index captures
   firm-specific alignment, true pairs should score clearly higher than mismatched pairs.
   If true and placebo scores are similar, the index mostly measures generic overlap.
4. Known-groups check: do firms that tie executive pay to ESG metrics (Part 2 flag) score
   higher on environment-theme alignment? (Expected direction: yes.)

Output: data/part3/validity_report.json (+ printed summary)
Usage:  python part3/validity_checks.py
"""
from __future__ import annotations

import csv
import json
import math
import random
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import CONFIG, DATA  # noqa: E402

CODES = list(json.loads((CONFIG / "theme_codebook.json").read_text())["categories"])
SEED, N_PERM = 42, 200


def load(path: Path) -> dict:
    with open(path, newline="", encoding="utf-8") as f:
        return {(r["ticker"], int(r["year"])): r for r in csv.DictReader(f)}


def vec(row: dict) -> list[int]:
    return [int(row.get(f"theme__{c}") or 0) for c in CODES]


def cosine(a, b) -> float:
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(y * y for y in b))
    return 0.0 if na == 0 or nb == 0 else sum(x * y for x, y in zip(a, b)) / (na * nb)


def index(sv, lv) -> float:
    """Same formula as authenticity_index.py: cosine - 0.5 * mean positive gap."""
    cheap = sum(max(s - l, 0) for s, l in zip(sv, lv)) / len(CODES)
    return cosine(sv, lv) - 0.5 * cheap


def describe(xs: list[float]) -> dict:
    q = st.quantiles(xs, n=4)
    return {"n": len(xs), "mean": round(st.mean(xs), 3), "sd": round(st.stdev(xs), 3),
            "min": round(min(xs), 3), "p25": round(q[0], 3), "median": round(q[1], 3),
            "p75": round(q[2], 3), "max": round(max(xs), 3)}


def main() -> None:
    p1 = load(DATA / "part1" / "part1_stated_values.csv")
    p2 = load(DATA / "part2" / "part2_lived_values.csv")
    cy = load(DATA / "part3" / "authenticity_company_year.csv")
    rows = [r for r in cy.values() if r["authenticity_index"] not in ("", None)]
    report: dict = {}

    # 1. Distribution + variance decomposition (between-firm vs within-firm).
    xs = [float(r["authenticity_index"]) for r in rows]
    report["distribution"] = describe(xs)
    by_firm: dict[str, list[float]] = {}
    for r in rows:
        by_firm.setdefault(r["ticker"], []).append(float(r["authenticity_index"]))
    grand = st.mean(xs)
    between = sum(len(v) * (st.mean(v) - grand) ** 2 for v in by_firm.values())
    within = sum((x - st.mean(v)) ** 2 for v in by_firm.values() for x in v)
    report["variance_share_between_firms"] = round(between / (between + within), 3)
    report["firms_scored"] = len(by_firm)
    report["firms_not_scored"] = sorted({r["ticker"] for r in cy.values()} - set(by_firm))

    # 2. Saturation: share of the 12 themes registered per document.
    matched = [(k, p1[k], p2[k]) for k in ((r["ticker"], int(r["year"])) for r in rows)]
    s_n = [sum(v > 0 for v in vec(s)) for _, s, _ in matched]
    l_n = [sum(v > 0 for v in vec(l)) for _, _, l in matched]
    report["themes_per_doc"] = {
        "stated_mean": round(st.mean(s_n), 2), "lived_mean": round(st.mean(l_n), 2),
        "lived_share_hitting_all_12": round(sum(n == len(CODES) for n in l_n) / len(l_n), 3),
        "lived_share_hitting_10plus": round(sum(n >= 10 for n in l_n) / len(l_n), 3),
    }

    # 3. Placebo test: true pairs vs. same-year pairs with a different firm's proxy.
    true_scores = [index(vec(s), vec(l)) for _, s, l in matched]
    by_year: dict[int, list[tuple]] = {}
    for (t, y), s, l in matched:
        by_year.setdefault(y, []).append((t, s, l))
    rng = random.Random(SEED)
    perm_means = []
    for _ in range(N_PERM):
        scores = []
        for y, group in by_year.items():
            if len(group) < 2:
                continue
            for t, s, _ in group:
                other = rng.choice([g for g in group if g[0] != t])
                scores.append(index(vec(s), vec(other[2])))
        perm_means.append(st.mean(scores))
    true_mean = st.mean(true_scores)
    p_value = (sum(m >= true_mean for m in perm_means) + 1) / (N_PERM + 1)
    report["placebo_test"] = {
        "true_pair_mean": round(true_mean, 3),
        "placebo_mean": round(st.mean(perm_means), 3),
        "placebo_sd_of_means": round(st.stdev(perm_means), 4),
        "difference": round(true_mean - st.mean(perm_means), 3),
        "one_sided_p": round(p_value, 4),
        "n_permutations": N_PERM,
    }

    # 4. Known groups: environment-theme alignment by ESG-in-pay flag.
    env = CODES.index("environment_sustainability")
    groups: dict[str, list[float]] = {"esg_in_pay": [], "no_esg_in_pay": []}
    for (t, y), s, l in matched:
        if not vec(s)[env] and not vec(l)[env]:
            continue
        gap = abs(vec(s)[env] - vec(l)[env])
        key = "esg_in_pay" if str(l.get("esg_in_compensation", "")).strip() in ("1", "True", "true") else "no_esg_in_pay"
        groups[key].append(gap)
    report["known_groups_env_gap"] = {k: {"n": len(v), "mean_abs_gap": round(st.mean(v), 3) if v else None}
                                      for k, v in groups.items()}

    out = DATA / "part3" / "validity_report.json"
    out.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
