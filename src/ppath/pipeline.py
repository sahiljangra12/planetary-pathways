"""Run the full study: data -> measures -> analyses -> tables, figures, numbers.

    python -m ppath            # full run (about two minutes)
    python -m ppath --quick    # fewer bootstrap replications, for development

Every number quoted in the paper is written to ``paper/numbers.tex`` as a LaTeX
macro by this module; the paper contains no hand-typed results.
"""

from __future__ import annotations

import argparse
import json
import logging
import platform
from datetime import UTC, datetime

import country_converter as coco
import numpy as np
import pandas as pd

from . import analysis as an
from . import config, data, figures
from . import indicators as ind
from .numbers import Numbers
from .report import COVERAGE_FIGURE, TREND_FIGURE, transparency_outputs, write_extra_tables
from .tables import latex_table

logging.getLogger("country_converter").setLevel(logging.ERROR)

SOCIAL_VARS = [t.var for t in config.SOCIAL_WITH_EDUCATION]
PERIOD_VARS = SOCIAL_VARS + [
    "co2_cons_pc",
    "co2_prod_pc",
    "ghg_pc",
    "gdp_ppp_pc",
    "population",
    "renewable_share",
    "forest_pct",
    "agri_land_pct",
    "fertilizer_kg_ha",
    "pm25",
    "energy_use_pc",
    "infant_mortality",
]
LABEL_COUNTRIES = [
    "USA",
    "CHN",
    "IND",
    "BRA",
    "NGA",
    "DEU",
    "CRI",
    "LKA",
    "VNM",
    "QAT",
    "BGD",
    "ETH",
    "IDN",
    "ZAF",
    "PER",
    "JPN",
    "MEX",
    "PAK",
    "COL",
]


def ascii_slug(text: str) -> str:
    """File-system-safe ASCII version of a label (en dashes become hyphens)."""
    out = text.replace("–", "-").replace("—", "-").replace(" ", "_")
    out = "".join(ch for ch in out if ch.isascii() and (ch.isalnum() or ch in "-_."))
    assert out.isascii()
    return out


def headline(scored_year: pd.DataFrame, period_scored: pd.DataFrame, pooled: dict, co2_col: str) -> dict:
    """Headline metrics recomputed identically for every robustness specification."""
    last = scored_year[scored_year["year"] == config.LAST_YEAR].dropna(subset=["quadrant"])
    p_last = period_scored[period_scored["period"] == list(config.PERIODS)[-1]].dropna(subset=["quadrant"])
    met = p_last[p_last["foundation_met"] == True]  # noqa: E712
    return {
        "n_countries": int(last["iso3"].nunique()),
        "share_foundation_last": float((last["foundation_met"] == True).mean()),  # noqa: E712
        "share_overshoot_last": float((last["overshoot"] == True).mean()),  # noqa: E712
        "n_safe_just_last_year": int((last["quadrant"] == "Safe and just").sum()),
        "n_safe_just_last_period": int((p_last["quadrant"] == "Safe and just").sum()),
        "safe_just_last_year": "; ".join(sorted(last.loc[last["quadrant"] == "Safe and just", "country"])),
        "safe_just_last_period": "; ".join(sorted(p_last.loc[p_last["quadrant"] == "Safe and just", "country"])),
        "min_co2_met_last_period": float(met[co2_col].min()) if len(met) else np.nan,
        "requirement_last": pooled[f"req_{config.LAST_YEAR}"],
        "requirement_trend": pooled["pct_per_year"],
        "requirement_trend_lo": pooled["pct_per_year_lo"],
        "requirement_trend_hi": pooled["pct_per_year_hi"],
    }


def run(quick: bool = False) -> dict:
    reps = 200 if quick else config.BOOTSTRAP_REPS
    rob_reps = 100 if quick else 500
    seed = config.SEED
    N = Numbers()
    # remove stale outputs so every file in results/, figures/ and tables/ comes from this run
    for d, pats in [
        (config.RESULTS, ("*.csv", "*.json")),
        (config.TABLES, ("*.tex",)),
        (config.FIGURES, ("*.pdf", "*.png")),
    ]:
        if d.exists():
            for pat in pats:
                for f in d.glob(pat):
                    f.unlink()
    config.RESULTS.mkdir(exist_ok=True)
    config.TABLES.mkdir(parents=True, exist_ok=True)
    config.PROCESSED.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ data
    panel, flow = data.build_panel()
    panel["continent"] = coco.convert(panel["iso3"].tolist(), to="continent", not_found=None)
    panel.to_csv(config.PROCESSED / "panel.csv", index=False)
    cov = data.coverage_table(panel, PERIOD_VARS + ["ch4_pc", "n2o_pc", "water_stress", "fertilizer_pc"])
    cov.to_csv(config.RESULTS / "coverage.csv", index=False)

    N.add("nStates", flow["un_states"])
    N.add("nCountries", flow["population_ge_threshold"])
    N.add("nCons", panel.dropna(subset=["co2_cons_pc"])["iso3"].nunique())
    N.add("nGDP", panel.dropna(subset=["gdp_ppp_pc"])["iso3"].nunique())
    N.add("firstYear", config.FIRST_YEAR, fmt="d")
    N.add("lastYear", config.LAST_YEAR, fmt="d")
    N.add("pctInterpolated", 100 * flow["share_values_interpolated"], fmt=".2f")
    N.add("pctFilledElectricity", 100 * flow["edge_filled_electricity_access"], fmt=".1f")
    N.add("boundary", config.CO2_BOUNDARY.value, fmt="g")
    N.add("boundaryFifteen", config.CO2_BOUNDARY_15.value, fmt="g")
    N.add("minSocial", config.MIN_SOCIAL_INDICATORS, fmt="d")
    N.add("minPopMillion", config.MIN_POPULATION / 1e6, fmt="g")
    N.add("minCross", config.MIN_CROSS_SECTION)
    N.add("decMinYears", config.DECOUPLING_MIN_YEARS)
    N.add("bootReps", reps, fmt=",")
    N.add("robReps", rob_reps, fmt=",")
    cons_pop_share = (
        panel[panel["year"] == config.LAST_YEAR]
        .assign(has=lambda d: d["co2_cons_pc"].notna())
        .pipe(lambda d: d.loc[d["has"], "population"].sum() / d["population"].sum())
    )
    N.add("consPopShare", 100 * cons_pop_share, fmt=".0f")

    # ------------------------------------------------------- main scoring
    scored = ind.score(panel)
    pm = data.period_means(panel, PERIOD_VARS)
    pm["continent"] = pm["iso3"].map(panel.drop_duplicates("iso3").set_index("iso3")["continent"])
    pscored = ind.score(pm)
    scored.to_csv(config.RESULTS / "scored_country_year.csv", index=False)
    pscored.to_csv(config.RESULTS / "scored_country_period.csv", index=False)

    # ------------------------------------------------------------- RQ1
    valid = scored[scored["year"] >= config.FIRST_YEAR + 1]  # employment series starts in 1991
    bal = an.balanced(valid)
    shares = an.quadrant_shares(bal)
    shares_pop = an.quadrant_shares(bal, weight="population")[config.QUADRANT_ORDER]
    shares.to_csv(config.RESULTS / "quadrant_shares_balanced.csv")
    shares_pop.to_csv(config.RESULTS / "quadrant_shares_balanced_popweighted.csv")
    y0, y1 = int(shares.index.min()), int(shares.index.max())
    N.add("balancedN", bal["iso3"].nunique())
    N.add("shareYearStart", y0, fmt="d")
    for key, q, share_too, pop_too in [
        ("Within", "Shortfall, within boundary", True, True),
        ("Trap", "Shortfall and overshoot", True, True),
        ("Over", "Foundation met, overshoot", False, True),
    ]:
        if share_too:
            N.add(f"share{key}Start", 100 * shares.loc[y0, q], fmt=".0f")
            N.add(f"share{key}End", 100 * shares.loc[y1, q], fmt=".0f")
        if pop_too:
            N.add(f"pop{key}Start", 100 * shares_pop.loc[y0, q], fmt=".0f")
            N.add(f"pop{key}End", 100 * shares_pop.loc[y1, q], fmt=".0f")
    over_start = 100 * shares.loc[y0, ["Shortfall and overshoot", "Foundation met, overshoot"]].sum()
    over_end = 100 * shares.loc[y1, ["Shortfall and overshoot", "Foundation met, overshoot"]].sum()
    met_start = 100 * shares.loc[y0, ["Foundation met, overshoot", "Safe and just"]].sum()
    met_end = 100 * shares.loc[y1, ["Foundation met, overshoot", "Safe and just"]].sum()
    N.add("overStart", over_start, fmt=".0f")
    N.add("overEnd", over_end, fmt=".0f")
    N.add("metStart", met_start, fmt=".0f")
    N.add("metEnd", met_end, fmt=".0f")
    ever_safe = scored[scored["quadrant"] == "Safe and just"]
    N.add("nEverSafeYears", len(ever_safe))
    ever_safe.groupby(["iso3", "country"])["year"].agg(["min", "max", "count"]).to_csv(
        config.RESULTS / "safe_and_just_country_years.csv"
    )

    # ------------------------------------------------------------- RQ2
    req = an.requirement_by_year(valid, "foundation_met", "co2_cons_pc", reps, seed)
    health = ind.score(
        panel,
        thresholds=[t for t in config.SOCIAL_THRESHOLDS if t.var in ("life_expectancy", "child_mortality")],
        min_indicators=2,
    )
    req_health = an.requirement_by_year(health, "foundation_met", "co2_cons_pc", reps, seed)
    prod = ind.score(panel, co2_col="co2_prod_pc")
    req_prod = an.requirement_by_year(
        prod[prod["year"] >= config.FIRST_YEAR + 1], "foundation_met", "co2_prod_pc", reps, seed
    )
    for name, r in [("main", req), ("health", req_health), ("production", req_prod)]:
        r.to_csv(config.RESULTS / f"requirement_{name}.csv", index=False)
    yrs = list(range(config.FIRST_YEAR + 1, config.LAST_YEAR + 1))
    pooled = {
        name: an.pooled_requirement(sc, "foundation_met", col, yrs, reps, seed)
        for name, sc, col in [
            ("main", valid, "co2_cons_pc"),
            ("health", health, "co2_cons_pc"),
            ("production", prod[prod["year"] >= config.FIRST_YEAR + 1], "co2_prod_pc"),
        ]
    }
    json.dump(pooled, open(config.RESULTS / "requirement_pooled.json", "w"), indent=2)
    pm_, ph, pp = pooled["main"], pooled["health"], pooled["production"]
    a, z = config.FIRST_YEAR + 1, config.LAST_YEAR
    N.add("reqStart", pm_[f"req_{a}"], fmt=".0f")
    N.add("reqStartLo", pm_[f"req_{a}_lo"], fmt=".0f")
    N.add("reqStartHi", pm_[f"req_{a}_hi"], fmt=".0f")
    N.add("reqMid", pm_["req_2000"], fmt=".1f")
    N.add("reqEnd", pm_[f"req_{z}"], fmt=".1f")
    N.add("reqEndLo", pm_[f"req_{z}_lo"], fmt=".1f")
    N.add("reqEndHi", pm_[f"req_{z}_hi"], fmt=".1f")
    N.add("reqEndMultiple", pm_[f"req_{z}"] / config.CO2_BOUNDARY.value, fmt=".1f")
    N.add("reqTrend", -pm_["pct_per_year"], fmt=".1f")
    N.add("reqTrendLo", -pm_["pct_per_year_hi"], fmt=".1f")
    N.add("reqTrendHi", -pm_["pct_per_year_lo"], fmt=".1f")
    N.add("reqHealthStart", ph[f"req_{a}"], fmt=".1f")
    N.add("reqHealthEnd", ph[f"req_{z}"], fmt=".1f")
    N.add("reqHealthEndLo", ph[f"req_{z}_lo"], fmt=".1f")
    N.add("reqHealthEndHi", ph[f"req_{z}_hi"], fmt=".1f")
    N.add("reqTrendHealth", -ph["pct_per_year"], fmt=".1f")
    N.add("reqProdEnd", pp[f"req_{z}"], fmt=".1f")
    N.add("reqTrendProd", -pp["pct_per_year"], fmt=".1f")
    ann = req.dropna(subset=["requirement"]).set_index("year")
    N.add("reqAnnualEnd", ann.loc[z, "requirement"], fmt=".1f")
    # illustrative only: years until the requirement reaches the boundary at the estimated pace
    years_to = np.log(config.CO2_BOUNDARY.value / pm_[f"req_{z}"]) / np.log(1 + pm_["pct_per_year"] / 100)
    N.add("reqReachYear", int(z + np.ceil(years_to)), fmt="d")

    front = an.frontier(pscored, list(config.PERIODS)[-1], n=10)
    front["co2"] = front["co2_cons_pc"]
    front.to_csv(config.RESULTS / "frontier.csv", index=False)
    N.add("frontierMin", front["co2"].min(), fmt=".1f")
    N.add("frontierMinCountry", front.iloc[0]["country"], fmt="s")
    N.add("frontierMinMultiple", front["co2"].min() / config.CO2_BOUNDARY.value, fmt=".1f")

    N.add("frontierFourth", front["co2"].iloc[3], fmt=".1f")
    met_last = pscored[(pscored["period"] == list(config.PERIODS)[-1]) & (pscored["foundation_met"] == True)]  # noqa: E712
    top = met_last.dropna(subset=["co2_cons_pc"]).nlargest(1, "co2_cons_pc").iloc[0]
    N.add("metMaxCons", top["co2_cons_pc"], fmt=".0f")
    N.add("metMaxCountry", top["country"], fmt="s")
    N.add("reqEndFifteenMultiple", pm_[f"req_{z}"] / config.CO2_BOUNDARY_15.value, fmt=".0f")
    N.add("reqFactor", pm_[f"req_{a}"] / pm_[f"req_{z}"], fmt=".1f")
    cons_sample = scored[scored["co2_cons_pc"].notna()]
    le0 = cons_sample.loc[cons_sample["year"] == a, "life_expectancy"].mean()
    le1 = cons_sample.loc[cons_sample["year"] == z, "life_expectancy"].mean()
    N.add("leStart", le0, fmt=".1f")
    N.add("leEnd", le1, fmt=".1f")
    N.add("leGain", le1 - le0, fmt=".1f")
    near = last_p_ = pscored[
        (pscored["period"] == list(config.PERIODS)[-1])
        & (pscored["social_min_ratio"] >= 0.9)
        & (pscored["foundation_met"] == False)  # noqa: E712
        & pscored["co2_cons_pc"].notna()
    ]
    del last_p_
    nc = near["continent"].value_counts()
    N.add("nearN", len(near))
    N.add("nearEurope", int(nc.get("Europe", 0)))
    N.add("nearAmerica", int(nc.get("America", 0)))
    N.add("nearMedianMultiple", (near["co2_cons_pc"] / config.CO2_BOUNDARY.value).median(), fmt=".1f")
    bal_mid = bal[bal["year"] == 2005]
    N.add(
        "chinaPopShare",
        100 * bal_mid.loc[bal_mid["iso3"] == "CHN", "population"].sum() / bal_mid["population"].sum(),
        fmt=".0f",
    )
    chn = scored[(scored["iso3"] == "CHN") & (scored["foundation_met"] == True)]  # noqa: E712
    N.add("chinaFirstMet", int(chn["year"].min()), fmt="d")
    ind_over = scored[(scored["iso3"] == "IND") & (scored["overshoot"] == True)]  # noqa: E712
    N.add("indiaFirstOver", int(ind_over["year"].min()), fmt="d")
    N.add(
        "indiaEndCons", scored.loc[(scored["iso3"] == "IND") & (scored["year"] == z), "co2_cons_pc"].iloc[0], fmt=".2f"
    )
    last_p = pscored[pscored["period"] == list(config.PERIODS)[-1]]
    w = last_p[last_p["quadrant"] == "Shortfall, within boundary"]["continent"].value_counts()
    N.add("withinLastTotal", int(w.sum()))
    N.add("withinLastAfrica", int(w.get("Africa", 0)))
    N.add("withinLastAsia", int(w.get("Asia", 0)))

    # within-country models
    outcomes = {"Life expectancy (years)": "life_expectancy", "Social attainment (0--1)": "social_attainment"}
    fe = pd.concat(
        [an.fe_models(scored, outcomes, p, c) for p in ("co2_cons_pc", "co2_prod_pc", "ghg_pc") for c in (False, True)],
        ignore_index=True,
    )
    fe.to_csv(config.RESULTS / "fe_models.csv", index=False)
    key = fe[(fe["term"] == "log_pressure") & (fe["pressure"] == "co2_cons_pc") & fe["income_control"]]
    le = key[key["outcome"].str.startswith("Life")].iloc[0]
    N.add("feLE", le["coef"], fmt=".2f")
    N.add("feLESe", le["se"], fmt=".2f")
    N.add("feLETen", le["coef"] * np.log(1.1), fmt=".2f")
    N.add("feLEDouble", le["coef"] * np.log(2), fmt=".2f")
    N.add("feN", le["n_obs"], fmt=",")
    N.add("feCountries", le["n_countries"])
    ghg = fe[
        (fe["term"] == "log_pressure")
        & (fe["pressure"] == "ghg_pc")
        & fe["income_control"]
        & fe["outcome"].str.startswith("Life")
    ].iloc[0]
    N.add("feGhgP", ghg["p"], fmt=".2f")
    ld = pd.DataFrame(
        [
            an.long_difference(pm.assign(**{"social_attainment": pscored["social_attainment"]}), y, p)
            for y in ("life_expectancy", "social_attainment")
            for p in ("co2_cons_pc", "co2_prod_pc")
        ]
    )
    ld.to_csv(config.RESULTS / "long_difference.csv", index=False)
    ldl = ld[(ld["outcome"] == "life_expectancy") & (ld["pressure"] == "co2_cons_pc")].iloc[0]
    N.add("ldLE", ldl["coef"], fmt=".2f")
    N.add("ldLEP", ldl["p"], fmt=".2f")
    N.add("ldN", ldl["n"])

    # ------------------------------------------------------------- RQ3
    windows = {"2001--2010": (2001, 2010), "2011--2022": (2011, 2022)}
    decs = {}
    for w, (a, b) in windows.items():
        decs[w] = an.decoupling(panel, a, b)
        decs[w]["window"] = w
    dec_all = pd.concat(decs.values(), ignore_index=True)
    dec_all.to_csv(config.RESULTS / "decoupling.csv", index=False)
    dec_prod = an.decoupling(panel, 2011, 2022, co2_col="co2_prod_pc")
    dec_prod.to_csv(config.RESULTS / "decoupling_production_2011_2022.csv", index=False)
    d2 = decs["2011--2022"]
    d1 = decs["2001--2010"]
    abs2 = d2[d2["class"] == "Absolute"]
    above = abs2[abs2["above_boundary"]]
    N.add("decN", len(d2))
    N.add("decAbsEarly", int((d1["class"] == "Absolute").sum()))
    N.add("decAbsLate", len(abs2))
    N.add("decAbsLateRobust", int(d2["robust_absolute"].sum()))
    N.add("decRelLate", int((d2["class"] == "Relative").sum()))
    N.add("decCoupledLate", int((d2["class"] == "Coupled").sum()))
    N.add("decNoGrowthLate", int((d2["class"] == "No income growth").sum()))
    N.add("decAbsAbove", len(above))
    N.add("decAbsBelow", len(abs2) - len(above))
    N.add("decAboveOnTrack", int(above["on_track"].sum()))
    N.add("decAboveOnTrackList", ", ".join(above.loc[above["on_track"], "country"]) or "none", fmt="s")
    N.add("decMedianAchieved", -above["co2_growth"].median(), fmt=".1f")
    N.add("decMedianRequired", -above["required_growth"].median(), fmt=".1f")
    N.add("decMedianYears", above["years_to_boundary"].median(), fmt=".0f")
    N.add("decLEUp", int((abs2["le_change"] > 0).sum()))
    fastest = above.sort_values("co2_growth").iloc[0]
    N.add("decSpeedRatio", above["required_growth"].median() / above["co2_growth"].median(), fmt=".1f")
    N.add("decFastest", fastest["country"], fmt="s")
    N.add("decFastestRate", -fastest["co2_growth"], fmt=".1f")
    N.add("decFastestRequired", -fastest["required_growth"], fmt=".1f")

    # ------------------------------------------------------------- RQ4
    plist = list(config.PERIODS)
    counts = pd.crosstab(pscored["period"], pscored["quadrant"]).reindex(
        index=plist, columns=config.QUADRANT_ORDER, fill_value=0
    )
    counts.to_csv(config.RESULTS / "quadrant_counts_by_period.csv")
    mats = {f"{a} to {b}": an.transition_matrix(pscored, a, b) for a, b in zip(plist[:-1], plist[1:], strict=True)}
    for k, m in mats.items():
        m.to_csv(config.RESULTS / f"transitions_{ascii_slug(k)}.csv")
    m1, m2 = mats.values()
    N.add("persistOne", 100 * an.persistence(m1), fmt=".0f")
    N.add("persistTwo", 100 * an.persistence(m2), fmt=".0f")
    trap_row = m2.loc["Shortfall and overshoot"]
    N.add("trapToOver", int(trap_row["Foundation met, overshoot"]))
    N.add("trapTotal", int(trap_row.sum()))
    within_row = m2.loc["Shortfall, within boundary"]
    N.add("withinStay", int(within_row["Shortfall, within boundary"]))
    N.add("withinTotal", int(within_row.sum()))
    N.add("withinToTrap", int(within_row["Shortfall and overshoot"]))
    N.add("withinToOver", int(within_row["Foundation met, overshoot"]))
    N.add(
        "intoSafe",
        int(
            sum(
                m.loc[[q for q in config.QUADRANT_ORDER if q != "Safe and just"], "Safe and just"].sum()
                for m in mats.values()
            )
        ),
    )
    # countries that start below the social foundation and later meet it: where do they cross?
    # same window as every other classification (1991 onwards; 1990 lacks employment data)
    obs = valid.dropna(subset=["foundation_met"]).sort_values("year")
    first_obs = obs.groupby("iso3").first()
    started_short = first_obs.index[first_obs["foundation_met"] == False]  # noqa: E712
    first_met = obs[obs["foundation_met"] == True].groupby("iso3").first()  # noqa: E712
    crossers = first_met[first_met.index.isin(started_short) & first_met["overshoot"].notna()]
    N.add("nCrossers", len(crossers))
    N.add("nCrossersAbove", int((crossers["overshoot"] == True).sum()))  # noqa: E712
    N.add("crossCarbonMedian", crossers["co2_cons_pc"].median(), fmt=".1f")
    N.add("crossCarbonMultiple", round(crossers["co2_cons_pc"].median(), 1) / config.CO2_BOUNDARY.value, fmt=".1f")
    crossers[["country", "year", "co2_cons_pc", "overshoot"]].to_csv(config.RESULTS / "foundation_crossers.csv")
    # stricter: the first year from which the foundation is met in three consecutive years
    sust_rows = []
    for iso in started_short:
        g = valid[valid["iso3"] == iso].sort_values("year").reset_index(drop=True)
        met = (g["foundation_met"] == True).to_numpy()  # noqa: E712
        for i in range(len(g) - 2):
            if met[i] and met[i + 1] and met[i + 2]:
                if pd.notna(g.loc[i, "overshoot"]):
                    sust_rows.append(g.loc[i, ["iso3", "country", "year", "co2_cons_pc", "overshoot"]])
                break
    sust = pd.DataFrame(sust_rows)
    sust.to_csv(config.RESULTS / "foundation_crossers_sustained.csv", index=False)
    N.add("nCrossersSust", len(sust))
    N.add("nCrossersSustAbove", int((sust["overshoot"] == True).sum()))  # noqa: E712
    N.add("crossSustCarbonMedian", sust["co2_cons_pc"].median(), fmt=".1f")
    # countries without consumption-based data: annual check with production-based emissions
    prod_all = ind.score(panel, co2_col="co2_prod_pc")
    prod_all = prod_all[prod_all["year"] >= config.FIRST_YEAR + 1]
    no_cons = set(panel["iso3"]) - set(panel.dropna(subset=["co2_cons_pc"])["iso3"])
    pa = prod_all[prod_all["iso3"].isin(no_cons)]
    N.add("noConsSafeYears", int((pa["quadrant"] == "Safe and just").sum()))
    N.add("noConsClassifiedYears", int(pa["quadrant"].notna().sum()), fmt=",")
    ps_all = prod_all[prod_all["quadrant"] == "Safe and just"]
    ps_all.groupby(["iso3", "country"])["year"].agg(["min", "max", "count"]).to_csv(
        config.RESULTS / "safe_and_just_production_country_years.csv"
    )
    N.add("prodSafeYearsAll", len(ps_all))
    ps_names = sorted(ps_all["country"].unique())
    ps_text = " and ".join([", ".join(ps_names[:-1]), ps_names[-1]]) if len(ps_names) > 1 else "".join(ps_names)
    N.add("prodSafeCountriesAll", ps_text or "none", fmt="s")

    gm = an.gmm_check(pscored, "co2_cons_pc", seed)
    json.dump(
        {k: (v if not isinstance(v, dict) else {str(a): b for a, b in v.items()}) for k, v in gm.items()},
        open(config.RESULTS / "gmm_check.json", "w"),
        indent=2,
    )
    N.add("gmmK", gm["k_best"])
    N.add("gmmAri", gm["ari_k4"], fmt=".2f")
    N.add("gmmStab", gm["stability_k4_median"], fmt=".2f")
    N.add("gmmN", gm["n"])

    # --------------------------------------------------------- robustness
    specs = {
        "Main specification": {},
        "Production-based CO$_2$": {"co2_col": "co2_prod_pc"},
        "Production-based, same countries": {"co2_col": "co2_prod_pc", "same": True},
        f"1.5\\textdegree C boundary ({config.CO2_BOUNDARY_15.value:g} t)": {"boundary": config.CO2_BOUNDARY_15.value},
        "Within 5\\% of every threshold": {"cutoff": 0.95},
        "Mean attainment $\\geq$ 0.95": {"rule": "mean"},
        "Adding secondary enrolment (5)": {"thresholds": config.SOCIAL_WITH_EDUCATION, "min_indicators": 4},
        "Without employment (3)": {
            "thresholds": [t for t in config.SOCIAL_THRESHOLDS if t.var in config.CORE_SOCIAL],
            "min_indicators": 3,
        },
        "No interpolation or gap filling": {"raw": True},
    }
    raw_panel = None
    rob_rows = []
    for name, sp in specs.items():
        sp = dict(sp)
        src = panel
        if sp.pop("raw", False):
            if raw_panel is None:
                old = (config.MAX_INTERPOLATION_GAP, config.EDGE_FILL_YEARS)
                config.MAX_INTERPOLATION_GAP, config.EDGE_FILL_YEARS = 0, 0
                raw_panel, _ = data.build_panel()
                config.MAX_INTERPOLATION_GAP, config.EDGE_FILL_YEARS = old
            src = raw_panel
        if sp.pop("same", False):
            src = src[src["iso3"].isin(panel.dropna(subset=["co2_cons_pc"])["iso3"].unique())]
        co2_col = sp.get("co2_col", "co2_cons_pc")
        s_y = ind.score(src, **sp)
        s_p = ind.score(data.period_means(src, PERIOD_VARS), **sp)
        s_y = s_y[s_y["year"] >= config.FIRST_YEAR + 1]
        r = an.pooled_requirement(s_y, "foundation_met", co2_col, [config.LAST_YEAR], rob_reps, seed)
        h = headline(s_y, s_p, r, co2_col)
        rob_rows.append({"Specification": name, **h})
    rob = pd.DataFrame(rob_rows)
    # how much do classifications depend on interpolation and gap filling?
    raw_scored = ind.score(raw_panel)
    cmp_ = scored[["iso3", "year", "quadrant"]].merge(
        raw_scored[["iso3", "year", "quadrant"]], on=["iso3", "year"], suffixes=("", "_raw")
    )
    both = cmp_.dropna(subset=["quadrant", "quadrant_raw"])
    N.add("fillSameShare", 100 * (both["quadrant"].astype(str) == both["quadrant_raw"].astype(str)).mean(), fmt=".1f")
    N.add("fillOnlyMain", int((cmp_["quadrant"].notna() & cmp_["quadrant_raw"].isna()).sum()))
    N.add("fillClassified", int(cmp_["quadrant"].notna().sum()), fmt=",")
    rob.to_csv(config.RESULTS / "robustness.csv", index=False)
    N.add("robReqMin", rob["requirement_last"].min(), fmt=".1f")
    N.add("robReqMax", rob["requirement_last"].max(), fmt=".1f")
    N.add("robTrendMin", -rob["requirement_trend"].max(), fmt=".1f")
    N.add("robTrendMax", -rob["requirement_trend"].min(), fmt=".1f")
    N.add("robTrendAllNeg", "all" if (rob["requirement_trend_hi"] < 0).all() else "not all", fmt="s")
    N.add("robSafeMax", rob["n_safe_just_last_period"].max())
    by_spec = rob.set_index("Specification")["requirement_last"]
    N.add("robReqNoEmp", by_spec["Without employment (3)"], fmt=".1f")
    N.add("robReqTol", by_spec["Within 5\\% of every threshold"], fmt=".1f")
    tol = rob.set_index("Specification").loc["Within 5\\% of every threshold"]
    N.add("robTolSafePeriod", (tol["safe_just_last_period"] or "none").replace("; ", " and "), fmt="s")
    N.add("robTolSafeYear", (tol["safe_just_last_year"] or "none").replace("; ", " and "), fmt="s")
    N.add("robTolSafeYearN", int(tol["n_safe_just_last_year"]))
    N.add("robReqEdu", by_spec["Adding secondary enrolment (5)"], fmt=".1f")
    prod_p = ind.score(data.period_means(panel, PERIOD_VARS), co2_col="co2_prod_pc")
    prod_safe = prod_p[(prod_p["period"] == plist[-1]) & (prod_p["quadrant"] == "Safe and just")]
    N.add("prodSafeList", ", ".join(prod_safe["country"]) or "none", fmt="s")
    if len(prod_safe) == 1:
        N.add("prodSafeProd", prod_safe["co2_prod_pc"].iloc[0], fmt=".2f")
        N.add("prodSafeCons", prod_safe["co2_cons_pc"].iloc[0], fmt=".2f")

    # ---------------------------------------------------- transparency
    extra = transparency_outputs(
        N, panel, scored, valid, pm, pscored, req, req_health, req_prod, pooled, fe, ld, decs, rob, gm, reps, rob_reps
    )

    # ------------------------------------------------------------ figures
    figures.fig_space(pscored, plist[-1], LABEL_COUNTRIES)
    figures.fig_shares(shares, shares_pop, bal["iso3"].nunique())
    figures.fig_requirement({"main": req, "health": req_health, "production": req_prod}, pooled, yrs)
    figures.fig_decoupling(d2)
    figures.fig_transitions(
        {f"{a} → {b}": m for (a, b), m in zip(zip(plist[:-1], plist[1:], strict=True), mats.values(), strict=True)}
    )
    figures.fig_gmm(gm["bic"])
    figures.fig_framework()
    figures.fig_coverage(panel, COVERAGE_FIGURE)
    figures.fig_trends(
        panel[panel["co2_cons_pc"].notna() | panel["iso3"].isin(panel.dropna(subset=["co2_cons_pc"])["iso3"].unique())],
        TREND_FIGURE,
    )

    # ------------------------------------------------------------- tables
    write_tables(panel, cov, counts, fe, ld, d2, decs, rob, front, flow)
    write_extra_tables(extra, pscored, decs, req, pooled)

    # -------------------------------------------------------------- done
    N.write(config.PAPER / "numbers.tex")
    meta = {
        "run_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "python": platform.python_version(),
        "pandas": pd.__version__,
        "numpy": np.__version__,
        "bootstrap_reps": reps,
        "inputs": {
            p.name: data.sha256(p) for p in sorted(config.RAW.glob("*")) if p.is_file() and p.name != "SHA256SUMS"
        },
    }
    json.dump(meta, open(config.RESULTS / "run_metadata.json", "w"), indent=2)
    return N.values


def write_tables(panel, cov, counts, fe, ld, d2, decs, rob, front, flow):
    T = config.TABLES
    # Table 1: indicators and thresholds
    rows = [
        [
            t.label + ("$^{a}$" if t.var == "secondary_enrollment" else ""),
            t.unit,
            ("$\\geq$ " if t.higher_is_better else "$\\leq$ ") + f"{t.value:g}",
            f"\\citet{{{t.source}}}",
        ]
        for t in config.SOCIAL_WITH_EDUCATION
    ]
    rows.append(
        [
            "Consumption-based CO$_2$",
            "t per person per year",
            f"$\\leq$ {config.CO2_BOUNDARY.value:g}",
            f"\\citet{{{config.CO2_BOUNDARY.source}}}",
        ]
    )
    rows.append(
        [
            "\\quad sensitivity (1.5\\textdegree C)",
            "t per person per year",
            f"$\\leq$ {config.CO2_BOUNDARY_15.value:g}",
            f"\\citet{{{config.CO2_BOUNDARY_15.source}}}",
        ]
    )
    latex_table(
        T / "tab_thresholds.tex",
        ["Indicator", "Unit", "Threshold", "Source"],
        rows,
        "llll",
        caption="Social thresholds and the climate boundary.",
        label="tab:thresholds",
        colsep="4pt",
        notes="$^{a}$Robustness check only (see Section~\\ref{sec:data}). "
        "Social thresholds follow \\citet{fanning2022}, except under-5 mortality, which uses "
        "SDG target 3.2. The 2\\textdegree C boundary divides a 1{,}000 Gt CO$_2$ budget "
        "(2011--2100, 66\\% probability) evenly over time and across 7 billion people "
        "\\citep{oneill2018}. The 1.5\\textdegree C value divides the IPCC remaining budget of "
        "500 Gt CO$_2$ from 2020 (50\\% probability) over 2020--2100 and the 2020 population.",
    )
    # Table 2: data sources and coverage
    src = {
        "life_expectancy": ("Life expectancy at birth", "WDI (UN WPP)"),
        "child_mortality": ("Under-5 mortality", "WDI (UN IGME)"),
        "electricity_access": ("Access to electricity", "WDI (SDG 7.1.1)"),
        "secondary_enrollment": ("Secondary gross enrolment", "WDI (UNESCO UIS)"),
        "employment": ("Employment (100 $-$ unemployment)", "WDI (ILO modelled)"),
        "co2_cons_pc": ("Consumption-based CO$_2$ per person", "Global Carbon Budget 2025"),
        "co2_prod_pc": ("Production-based CO$_2$ per person", "Global Carbon Budget 2025"),
        "ghg_pc": ("GHG incl.\\ land use per person", "\\citet{jones2023}"),
        "gdp_ppp_pc": ("GDP per person (2011 int.\\$)", "Maddison Project 2023"),
    }
    c = cov.set_index("variable")
    rows = [
        [
            lab,
            s,
            f"{int(c.loc[v, 'countries'])}",
            f"{int(c.loc[v, 'first_year'])}--{int(c.loc[v, 'last_year'])}",
            f"{100 * c.loc[v, 'share_of_panel']:.0f}",
        ]
        for v, (lab, s) in src.items()
    ]
    latex_table(
        T / "tab_data.tex",
        ["Variable", "Source", "Countries", "Years", "Coverage (\\%)"],
        rows,
        "llrrr",
        caption="Variables, sources and coverage in the analysis panel.",
        label="tab:data",
        colsep="3pt",
        notes=f"Panel of {flow['population_ge_threshold']} countries $\\times$ "
        f"{config.LAST_YEAR - config.FIRST_YEAR + 1} years. Coverage is the share of country-years "
        "with a value after interpolating interior gaps of at most "
        f"{config.MAX_INTERPOLATION_GAP} years. WDI: World Development Indicators.",
    )
    # Table 3: quadrant counts by period
    rows = [
        [p] + [str(int(counts.loc[p, q])) for q in config.QUADRANT_ORDER] + [str(int(counts.loc[p].sum()))]
        for p in counts.index
    ]
    latex_table(
        T / "tab_counts.tex",
        ["Period", "Shortfall, within", "Shortfall, overshoot", "Met, overshoot", "Safe and just", "Total"],
        rows,
        "lrrrrr",
        caption="Countries in each configuration, by period (period means, consumption-based CO$_2$).",
        label="tab:counts",
        notes="Foundation met: all four social indicators at or beyond their thresholds. Overshoot: "
        f"consumption-based CO$_2$ above {config.CO2_BOUNDARY.value:g} t per person.",
    )
    # Table 4: FE models
    rows = []
    for pr, lab in [
        ("co2_cons_pc", "Consumption CO$_2$"),
        ("co2_prod_pc", "Production CO$_2$"),
        ("ghg_pc", "GHG incl.\\ land use"),
    ]:
        for oc in fe["outcome"].unique():
            cells = [lab if oc == fe["outcome"].unique()[0] else "", oc]
            for ctrl in (False, True):
                r = fe[
                    (fe["pressure"] == pr)
                    & (fe["outcome"] == oc)
                    & (fe["income_control"] == ctrl)
                    & (fe["term"] == "log_pressure")
                ].iloc[0]
                cells.append(f"{r['coef']:.3f}{stars(r['p'])} ({r['se']:.3f})")
            cells.append(f"{int(r['n_obs']):,}")
            rows.append(cells)
    latex_table(
        T / "tab_fe.tex",
        ["Pressure", "Outcome", "Without income", "With log GDP", "N"],
        rows,
        "llrrr",
        caption="Within-country association between log emissions per person and social outcomes.",
        label="tab:fe",
        notes="Coefficients on log emissions per person from two-way fixed-effects models (country and "
        "year effects); standard errors clustered by country in parentheses. "
        "$^{*}p<0.05$, $^{**}p<0.01$, $^{***}p<0.001$.",
    )
    # Table 5: decoupling
    order = ["Absolute", "Relative", "Coupled", "No income growth"]
    rows = []
    for w, d in decs.items():
        vc = d["class"].value_counts()
        rows.append([w] + [str(int(vc.get(k, 0))) for k in order] + [str(int(d["robust_absolute"].sum())), str(len(d))])
    latex_table(
        T / "tab_decoupling.tex",
        ["Window", "Absolute", "Relative", "Coupled", "No growth", "Absolute (CI $<$ 0)", "N"],
        rows,
        "lrrrrrr",
        caption="Decoupling of consumption-based CO$_2$ per person from GDP per person.",
        label="tab:decoupling",
        notes="Annual growth rates from log-linear trends. Absolute: income rising, emissions falling. "
        "Relative: both rising, emissions more slowly. Coupled: emissions rising at least as fast as "
        "income. The last column requires the 95\\% confidence interval of the emissions trend to "
        "lie below zero.",
    )
    # Table 6: robustness
    rows = [
        [
            r["Specification"],
            str(int(r["n_countries"])),
            f"{100 * r['share_foundation_last']:.0f}",
            f"{100 * r['share_overshoot_last']:.0f}",
            str(int(r["n_safe_just_last_period"])),
            f"{r['min_co2_met_last_period']:.1f}",
            f"{r['requirement_last']:.1f}",
            f"{-r['requirement_trend']:.1f}",
        ]
        for _, r in rob.iterrows()
    ]
    latex_table(
        T / "tab_robustness.tex",
        [
            "Specification",
            "N",
            "Met (\\%)",
            "Over (\\%)",
            "Safe \\& just",
            "Lowest t",
            "Req.\\ (t)",
            "Decline (\\%/yr)",
        ],
        rows,
        "lrrrrrrr",
        caption="Headline results under alternative specifications.",
        label="tab:robustness",
        notes=f"Met and Over: shares of countries in {config.LAST_YEAR} meeting the social foundation and "
        "overshooting the boundary. Safe \\& just: countries in that configuration in the "
        f"{list(config.PERIODS)[-1]} (period means). Lowest t: lowest per-capita CO$_2$ among countries "
        "meeting the foundation in that period. Req.: CO$_2$ per person at which half of countries meet "
        f"the foundation in {config.LAST_YEAR} and Decline: its average annual fall, both "
        "from the pooled logit model (Section~\\ref{sec:methods}).",
        size="\\footnotesize",
        colsep="3.5pt",
    )
    # Table 7: frontier
    rows = [
        [
            r["country"],
            f"{r['co2_cons_pc']:.2f}",
            f"{r['co2_cons_pc'] / config.CO2_BOUNDARY.value:.1f}",
            f"{r['life_expectancy']:.1f}",
            f"{r['child_mortality']:.1f}",
            f"{r['social_min_ratio']:.2f}",
        ]
        for _, r in front.iterrows()
    ]
    latex_table(
        T / "tab_frontier.tex",
        ["Country", "CO$_2$ (t)", "$\\times$ boundary", "Life exp.", "U5MR", "Lowest ratio"],
        rows,
        "lrrrrr",
        caption=f"The ten lowest-carbon countries meeting the social foundation, {list(config.PERIODS)[-1]}.",
        label="tab:frontier",
        notes="Period means of consumption-based CO$_2$ per person. U5MR: under-5 mortality per 1,000 "
        "live births. Lowest ratio: the weakest social indicator relative to its threshold.",
    )
    # Appendix: long differences
    rows = [
        [
            r["outcome"].replace("_", " ").capitalize(),
            "Consumption" if r["pressure"] == "co2_cons_pc" else "Production",
            f"{r['coef']:.2f}{stars(r['p'])} ({r['se']:.2f})",
            f"{r['coef_gdp']:.2f}{stars(r['p_gdp'])}",
            str(int(r["n"])),
        ]
        for _, r in ld.iterrows()
    ]
    latex_table(
        T / "tab_longdiff.tex",
        ["Outcome", "CO$_2$ accounting", "$\\Delta$ log CO$_2$", "$\\Delta$ log GDP", "N"],
        rows,
        "llrrr",
        caption=f"Long differences between {list(config.PERIODS)[0]} and {list(config.PERIODS)[-1]}.",
        label="tab:longdiff",
        notes="OLS of the change in the outcome on the change in log CO$_2$ and log GDP per person, "
        f"controlling for the {list(config.PERIODS)[0]} level; HC3 standard errors in parentheses. "
        "$^{*}p<0.05$, $^{**}p<0.01$, $^{***}p<0.001$.",
    )


def stars(p: float) -> str:
    return "$^{***}$" if p < 0.001 else "$^{**}$" if p < 0.01 else "$^{*}$" if p < 0.05 else ""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="ppath")
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args(argv)
    vals = run(quick=args.quick)
    print(f"Done: {len(vals)} numbers written to {config.PAPER / 'numbers.tex'}")
    return 0
