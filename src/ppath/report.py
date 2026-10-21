"""Transparency outputs: fit diagnostics, missing-data accounting, sample comparisons,
decoupling scenarios, descriptive statistics, estimation samples, the stable-versus-
sensitive summary and the appendix tables."""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import analysis as an
from . import config
from .tables import latex_longtable, latex_table

COVERAGE_FIGURE = {
    "life_expectancy": "Life expectancy",
    "child_mortality": "Under-5 mortality",
    "electricity_access": "Electricity access",
    "employment": "Employment",
    "secondary_enrollment": "Secondary enrolment",
    "co2_cons_pc": "Consumption CO$_2$",
    "co2_prod_pc": "Production CO$_2$",
    "gdp_ppp_pc": "GDP per person",
}

TREND_FIGURE = {
    "life_expectancy": ("Life expectancy (years)", 74.0, False),
    "child_mortality": ("Under-5 mortality (per 1,000)", 25.0, True),
    "electricity_access": ("Electricity access (%)", 95.0, False),
    "employment": ("Employment (% of labour force)", 94.0, False),
    "co2_cons_pc": ("Consumption CO$_2$ (t per person)", config.CO2_BOUNDARY.value, True),
    "gdp_ppp_pc": ("GDP per person (2011 int.$)", None, True),
}

QCODE = {
    "Shortfall, within boundary": "SW",
    "Shortfall and overshoot": "SO",
    "Foundation met, overshoot": "MO",
    "Safe and just": "SJ",
}


def _fmt(x, f=".1f", na="--"):
    return na if x is None or (isinstance(x, float) and not np.isfinite(x)) or pd.isna(x) else format(x, f)


def _tex(s: str) -> str:
    return str(s).replace("&", "\\&").replace("%", "\\%").replace("_", "\\_")


def transparency_outputs(
    N, panel, scored, valid, pm, pscored, req, req_health, req_prod, pooled, fe, ld, decs, rob, gm, reps, rob_reps
) -> dict:
    out: dict = {}
    R = config.RESULTS

    # ---------------------------------------------------------- fit diagnostics
    for key, r in [("Main", req), ("Health", req_health), ("Prod", req_prod)]:
        N.add(f"reqPointFail{key}", int((r["status"] != an.FIT_OK).sum()))
        N.add(f"reqBootFail{key}", int(r["boot_failed"].sum()), fmt=",")
        N.add(f"reqBootTotal{key}", int((r["boot_ok"] + r["boot_failed"]).sum()), fmt=",")
    N.add("reqYearsMain", len(req))
    N.add("reqBootFailMaxMain", 100 * (req["boot_failed"] / (req["boot_ok"] + req["boot_failed"])).max(), fmt=".1f")
    worst = req.loc[req["boot_failed"].idxmax()]
    N.add("reqBootFailWorstYear", int(worst["year"]), fmt="d")
    N.add("reqBootFailWorstReasons", worst["boot_fail_reasons"].replace("_", " ").replace(";", "; ") or "none", fmt="s")
    for key, name in [("Main", "main"), ("Health", "health"), ("Prod", "production")]:
        N.add(f"pooledBootFail{key}", int(pooled[name]["boot_failed"]))
    N.add("pooledCountriesMain", int(pooled["main"]["n_countries"]))
    N.add("pooledNMain", int(pooled["main"]["n_obs"]), fmt=",")
    N.add("pooledMetMain", int(pooled["main"]["n_met"]), fmt=",")

    # ------------------------------------------------- classification status
    st = an.classification_status(valid)
    vc = st.value_counts()
    N.add("csTotal", len(st), fmt=",")
    N.add("csClassified", int(vc.get("Classified", 0)), fmt=",")
    N.add("csNoCO", int(vc.get("No consumption CO2", 0)), fmt=",")
    N.add("csUndetermined", int(vc.get("Social status undetermined", 0)), fmt=",")
    und = valid[st == "Social status undetermined"]
    miss_ind = {t.label: int(und[t.var].isna().sum()) for t in config.SOCIAL_THRESHOLDS}
    top_missing = max(miss_ind, key=miss_ind.get)
    N.add("csUndTopIndicator", top_missing.lower(), fmt="s")
    n_und = und["iso3"].nunique()
    N.add("csUndCountries", "one country" if n_und == 1 else f"{n_und} countries", fmt="s")
    out["status_counts"] = vc

    # ---------------------------- who lacks consumption-based CO2? (2011-2022)
    last = list(config.PERIODS)[-1]
    p_last = pscored[pscored["period"] == last].copy()
    p_last["population_m"] = p_last["population"] / 1e6
    has = p_last["co2_cons_pc"].notna()
    comp_vars = {
        "population_m": "Population (millions)",
        "gdp_ppp_pc": "GDP per person (2011 int.\\$)",
        "life_expectancy": "Life expectancy (years)",
        "child_mortality": "Under-5 mortality (per 1,000)",
        "electricity_access": "Electricity access (\\%)",
        "employment": "Employment (\\%)",
        "co2_prod_pc": "Production CO$_2$ (t per person)",
    }
    comp = an.compare_groups(p_last, has, comp_vars)
    comp.to_csv(R / "missing_consumption_comparison.csv", index=False)
    out["comparison"] = comp
    c = comp.set_index("variable")
    N.add("missInN", int(has.sum()))
    N.add("missOutN", int((~has).sum()))
    N.add("missGdpIn", c.loc["GDP per person (2011 int.\\$)", "in_median"], fmt=",.0f")
    N.add("missGdpOut", c.loc["GDP per person (2011 int.\\$)", "out_median"], fmt=",.0f")
    N.add("missProdIn", c.loc["Production CO$_2$ (t per person)", "in_median"], fmt=".1f")
    N.add("missProdOut", c.loc["Production CO$_2$ (t per person)", "out_median"], fmt=".1f")
    N.add("missLEIn", c.loc["Life expectancy (years)", "in_median"], fmt=".1f")
    N.add("missLEOut", c.loc["Life expectancy (years)", "out_median"], fmt=".1f")
    N.add("missPopIn", c.loc["Population (millions)", "in_median"], fmt=".1f")
    N.add("missPopOut", c.loc["Population (millions)", "out_median"], fmt=".1f")
    out_cont = p_last.loc[~has, "continent"].value_counts()
    N.add("missOutAfrica", int(out_cont.get("Africa", 0)))
    N.add("missOutAsia", int(out_cont.get("Asia", 0)))
    # production-based configurations of countries without consumption data
    from . import indicators as ind

    prod_last = ind.score(pm[pm["period"] == last], co2_col="co2_prod_pc")
    out_q = prod_last[prod_last["iso3"].isin(p_last.loc[~has, "iso3"])]["quadrant"].value_counts()
    N.add("missOutWithin", int(out_q.get("Shortfall, within boundary", 0)))
    N.add("missOutClassified", int(out_q.sum()))
    N.add("missOutSafe", int(out_q.get("Safe and just", 0)))

    # ------------------------------------------------- decoupling scenarios
    d2 = decs["2011--2022"]
    above = d2[(d2["class"] == "Absolute") & d2["above_boundary"]]
    sc = an.decoupling_scenarios(above)
    sc.to_csv(R / "decoupling_scenarios.csv", index=False)
    out["scenarios"] = sc
    s_ = sc.set_index("scenario")
    N.add("scenDouble", int(s_.loc["Each country doubles its rate", "n_by_2050"]))
    N.add("scenNinety", int(s_.loc["All at the 90th-percentile rate", "n_by_2050"]))
    N.add("scenNinetyRate", -s_.loc["All at the 90th-percentile rate", "median_rate"], fmt=".1f")
    N.add("scenFastest", int(s_.loc["All at the fastest achieved rate", "n_by_2050"]))
    N.add("scenFastestRate", -s_.loc["All at the fastest achieved rate", "median_rate"], fmt=".1f")
    N.add("scenAchievedYear", s_.loc["Achieved 2011--2022 rates", "median_year"], fmt=".0f")
    N.add("scenDoubleYear", s_.loc["Each country doubles its rate", "median_year"], fmt=".0f")

    # ------------------------------------------------------------ descriptives
    cons_iso = panel.dropna(subset=["co2_cons_pc"])["iso3"].unique()
    pm_cons = pscored[pscored["iso3"].isin(cons_iso)].copy()
    desc_vars = {
        "life_expectancy": "Life expectancy (years)",
        "child_mortality": "Under-5 mortality (per 1,000)",
        "electricity_access": "Electricity access (\\%)",
        "employment": "Employment (\\%)",
        "co2_cons_pc": "Consumption CO$_2$ (t per person)",
        "co2_prod_pc": "Production CO$_2$ (t per person)",
        "gdp_ppp_pc": "GDP per person (2011 int.\\$)",
        "social_min_ratio": "Weakest attainment ratio",
    }
    desc = an.descriptives(pm_cons, desc_vars)
    desc.to_csv(R / "descriptives.csv", index=False)
    out["descriptives"] = desc
    dd = desc.set_index(["variable", "period"])
    first = list(config.PERIODS)[0]
    N.add("descCOFirst", dd.loc[("Consumption CO$_2$ (t per person)", first), "median"], fmt=".1f")
    N.add("descCOLast", dd.loc[("Consumption CO$_2$ (t per person)", last), "median"], fmt=".1f")
    N.add("descUFirst", dd.loc[("Under-5 mortality (per 1,000)", first), "median"], fmt=".0f")
    N.add("descULast", dd.loc[("Under-5 mortality (per 1,000)", last), "median"], fmt=".0f")
    N.add("descElecFirst", dd.loc[("Electricity access (\\%)", first), "median"], fmt=".0f")
    N.add("descElecLast", dd.loc[("Electricity access (\\%)", last), "median"], fmt=".0f")
    N.add("descGdpFirst", dd.loc[("GDP per person (2011 int.\\$)", first), "median"], fmt=",.0f")
    N.add("descGdpLast", dd.loc[("GDP per person (2011 int.\\$)", last), "median"], fmt=",.0f")

    # ------------------------------------------------- stable vs sensitive
    main = rob.iloc[0]
    rows = []

    def rng(col, f, scale=1.0):
        v = rob[col] * scale
        return f"{format(v.min(), f)}--{format(v.max(), f)}"

    n_specs = len(rob)
    rows.append(
        [
            "No country in the safe and just space, 2011--2022",
            str(int(main["n_safe_just_last_period"])),
            f"0--{int(rob['n_safe_just_last_period'].max())}",
            f"{int((rob['n_safe_just_last_period'] == 0).sum())} of {n_specs}",
        ]
    )
    rows.append(
        [
            "Requirement above the 2\\textdegree C boundary in 2022 (t)",
            f"{main['requirement_last']:.1f}",
            rng("requirement_last", ".1f"),
            f"{int((rob['requirement_last'] > config.CO2_BOUNDARY.value).sum())} of {n_specs}",
        ]
    )
    decl = -rob["requirement_trend"]
    rows.append(
        [
            "Requirement falling (\\% per year, 95\\% CI below 0)",
            f"{-main['requirement_trend']:.1f}",
            f"{decl.min():.1f}--{decl.max():.1f}",
            f"{int((rob['requirement_trend_hi'] < 0).sum())} of {n_specs}",
        ]
    )
    rows.append(
        [
            "Share of countries meeting the foundation, 2022 (\\%)",
            f"{100 * main['share_foundation_last']:.0f}",
            rng("share_foundation_last", ".0f", 100.0),
            "level varies",
        ]
    )
    rows.append(
        [
            "Share of countries overshooting, 2022 (\\%)",
            f"{100 * main['share_overshoot_last']:.0f}",
            rng("share_overshoot_last", ".0f", 100.0),
            "level varies",
        ]
    )
    rows.append(
        [
            "Lowest CO$_2$ among countries meeting the foundation (t)",
            f"{main['min_co2_met_last_period']:.1f}",
            rng("min_co2_met_last_period", ".1f"),
            "level varies",
        ]
    )
    out["stability_rows"] = rows
    N.add("robSafeZeroSpecs", int((rob["n_safe_just_last_period"] == 0).sum()))
    N.add("robSpecs", n_specs)

    # -------------------------------------------------- estimation samples
    bal_n = valid.dropna(subset=["quadrant"]).groupby("iso3")["year"].nunique()
    est_rows = [
        [
            "Configurations, annual (Fig.~\\ref{fig:shares})",
            "Balanced panel, 1991--2022",
            f"{int((bal_n == valid['year'].nunique()).sum())} countries $\\times$ {valid['year'].nunique()} years",
            "Descriptive; no sampling inference",
        ],
        [
            "Configurations, period means (Table~\\ref{tab:counts})",
            "Consumption sample",
            f"{int(pscored['quadrant'].notna().sum())} country-periods",
            "Descriptive",
        ],
        [
            "Annual carbon requirement (Fig.~\\ref{fig:requirement})",
            f"Classified country-years, years with $\\geq${config.MIN_CROSS_SECTION} countries",
            f"{int(req['n'].min())}--{int(req['n'].max())} countries per year",
            f"Country bootstrap, {reps:,} reps; {int(req['boot_failed'].sum()):,} failed fits".replace(",", "{,}"),
        ],
        [
            "Pooled carbon requirement (headline)",
            "Same, pooled 1991--2022",
            f"{pooled['main']['n_obs']:,} obs., {pooled['main']['n_countries']} countries".replace(",", "{,}"),
            f"Country-cluster bootstrap, {reps:,} reps; {pooled['main']['boot_failed']} failed".replace(",", "{,}"),
        ],
        [
            "Fixed-effects models (Table~\\ref{tab:fe})",
            "Country-years with outcome, CO$_2$ and GDP",
            f"{int(fe['n_obs'].min()):,}--{int(fe['n_obs'].max()):,} obs.".replace(",", "{,}"),
            "Clustered by country",
        ],
        [
            "Long differences (Table~\\ref{tab:longdiff})",
            "Countries observed in both end periods",
            f"{int(ld['n'].min())}--{int(ld['n'].max())} countries",
            "HC3",
        ],
        [
            "Decoupling (Table~\\ref{tab:decoupling})",
            f"$\\geq$ {config.DECOUPLING_MIN_YEARS} years in window",
            f"{len(decs['2001--2010'])} and {len(decs['2011--2022'])} countries",
            "OLS trend CIs",
        ],
        [
            "Mixture check (Appendix)",
            "Classified country-periods",
            f"{gm['n']} country-periods",
            "200 bootstrap refits",
        ],
        [
            "Robustness (Table~\\ref{tab:robustness})",
            "Varies by specification",
            f"{n_specs} specifications",
            f"Cluster bootstrap, {rob_reps} reps each",
        ],
    ]
    out["estimation_rows"] = est_rows
    return out


def write_extra_tables(extra: dict, pscored: pd.DataFrame, decs: dict, req: pd.DataFrame, pooled: dict) -> None:
    T = config.TABLES
    # descriptives
    desc = extra["descriptives"]
    plist = list(config.PERIODS)
    rows = []
    for var in desc["variable"].unique():
        cells = [var]
        for p in plist:
            r = desc[(desc["variable"] == var) & (desc["period"] == p)].iloc[0]
            big = "GDP" in var
            f = ",.0f" if big else ".2f" if "ratio" in var else ".1f"
            cells.append(
                f"{format(r['median'], f)} [{format(r['p10'], f)}, {format(r['p90'], f)}]".replace(",", "{,}")
                if big
                else f"{format(r['median'], f)} [{format(r['p10'], f)}, {format(r['p90'], f)}]"
            )
        cells.append(str(int(desc[desc["variable"] == var]["n"].min())))
        rows.append(cells)
    latex_table(
        T / "tab_descriptives.tex",
        ["Variable", *plist, "Min.\\ N"],
        rows,
        "lrrrr",
        caption="Descriptive statistics of the consumption-based sample, period means.",
        label="tab:desc",
        notes="Median across countries, with the 10th and 90th percentiles in brackets. Min.\\ N: the "
        "smallest number of countries with a value in any period.",
        colsep="3pt",
        size="\\footnotesize",
    )
    # missing-data comparison
    comp = extra["comparison"]
    rows = [
        [
            r["variable"],
            _fmt(r["in_median"], ",.1f").replace(",", "{,}"),
            _fmt(r["out_median"], ",.1f").replace(",", "{,}"),
            _fmt(r["p_mannwhitney"], ".3f"),
        ]
        for _, r in comp.iterrows()
    ]
    n_in, n_out = int(comp["in_n"].max()), int(comp["out_n"].max())
    latex_table(
        T / "tab_missing.tex",
        ["Variable (2011--2022 means)", f"With data (n={n_in})", f"Without (n={n_out})", "$p$"],
        rows,
        "lrrr",
        caption="Countries with and without consumption-based CO$_2$ estimates.",
        label="tab:missing",
        notes="Medians across countries. $p$: two-sided Mann--Whitney test of equal distributions.",
    )
    # decoupling scenarios
    sc = extra["scenarios"]
    rows = [
        [
            r["scenario"],
            f"{-r['median_rate']:.1f}",
            f"{int(r['n_by_2050'])} of {int(r['n'])}",
            _fmt(r["median_year"], ".0f") if np.isfinite(r["median_year"]) else "never",
        ]
        for _, r in sc.iterrows()
    ]
    latex_table(
        T / "tab_scenarios.tex",
        ["Scenario", "Median cut (\\%/yr)", "Reach 1.61 t by 2050", "Median year reached"],
        rows,
        "lrrr",
        caption="Illustrative scenarios for the absolute decouplers above the boundary.",
        label="tab:scenarios",
        notes="Each scenario applies a constant annual rate of change in consumption-based CO$_2$ per person "
        "from each country's 2022 level. The 90th-percentile and fastest rates are those achieved by "
        "this group in 2011--2022. These are arithmetic illustrations, not forecasts.",
    )
    # estimation samples
    latex_table(
        T / "tab_samples.tex",
        ["Analysis", "Sample", "Size", "Uncertainty and failures"],
        extra["estimation_rows"],
        ">{\\raggedright\\arraybackslash}p{0.25\\linewidth}>{\\raggedright\\arraybackslash}p{0.25\\linewidth}"
        ">{\\raggedright\\arraybackslash}p{0.2\\linewidth}>{\\raggedright\\arraybackslash}p{0.22\\linewidth}",
        caption="Estimation samples and inference for each analysis.",
        label="tab:samples",
        size="\\footnotesize",
        colsep="3pt",
    )
    # stable vs sensitive
    latex_table(
        T / "tab_stability.tex",
        ["Result", "Main", "Range", "Holds in"],
        extra["stability_rows"],
        ">{\\raggedright\\arraybackslash}p{0.5\\linewidth}rrr",
        caption="Which results are stable across specifications and which are not.",
        label="tab:stability",
        notes="Range across the specifications of Table~\\ref{tab:robustness}. ``Level varies'' marks "
        "quantities whose value depends on the specification even though the qualitative conclusion "
        "does not.",
        size="\\small",
    )
    # appendix: countries
    pv = pscored.pivot_table(
        index=["iso3", "country"], columns="period", values="quadrant", aggfunc="first", observed=False
    )
    last = plist[-1]
    lp = pscored[pscored["period"] == last].set_index("iso3")
    rows = []
    for (iso, name), r in pv.sort_index(level=1).iterrows():
        x = lp.loc[iso]
        cfg = [QCODE.get(r.get(p), "--") if isinstance(r.get(p), str) else "--" for p in plist]
        rows.append(
            [
                _tex(name),
                _fmt(x["co2_cons_pc"]),
                _fmt(x["co2_prod_pc"]),
                _fmt(x["life_expectancy"]),
                _fmt(x["child_mortality"]),
                _fmt(x["electricity_access"], ".0f"),
                _fmt(x["employment"]),
                *cfg,
            ]
        )
    latex_longtable(
        T / "tab_countries.tex",
        [
            "Country",
            "CO$_2$ cons.",
            "CO$_2$ prod.",
            "Life exp.",
            "U5MR",
            "Elec.",
            "Empl.",
            *[p.replace("–", "--") for p in plist],
        ],
        rows,
        "@{}lrrrrrrccc@{}",
        caption=f"Country values ({last.replace('–', '--')} means) and configurations by period.",
        label="tab:countries",
        notes="CO$_2$ in t per person per year. U5MR: under-5 mortality per 1,000 live births. Elec.: "
        "electricity access (\\%). Empl.: employment (\\% of labour force). Configurations: SW "
        "shortfall within the boundary; SO shortfall and overshoot; MO foundation met with "
        "overshoot; SJ safe and just; -- not classified (no consumption-based CO$_2$ or an "
        "undetermined social status).",
    )
    # appendix: decoupling by country
    d2 = decs["2011--2022"].sort_values("country")
    rows = [
        [
            _tex(r["country"]),
            f"{r['co2_growth']:.1f} [{r['co2_growth_lo']:.1f}, {r['co2_growth_hi']:.1f}]",
            f"{r['gdp_growth']:.1f}",
            r["class"],
            f"{r['co2_last']:.2f}",
            f"{r['required_growth']:.1f}" if r["above_boundary"] else "within",
        ]
        for _, r in d2.iterrows()
    ]
    latex_longtable(
        T / "tab_decoupling_countries.tex",
        ["Country", "CO$_2$ trend (\\%/yr)", "GDP trend", "Class", "CO$_2$ 2022", "Required"],
        rows,
        "@{}lrrlrr@{}",
        caption="Decoupling of consumption-based CO$_2$ from GDP per person by country, 2011--2022.",
        label="tab:deccountries",
        notes="Trends are annual rates (\\%) from log-linear regressions, with 95\\% confidence intervals "
        "for CO$_2$. Required: constant annual rate needed to reach 1.61 t per person by 2050.",
    )
    # appendix: annual requirement
    rows = [
        [
            str(int(r["year"])),
            str(int(r["n"])),
            f"{100 * r['share_met']:.0f}",
            _fmt(r["requirement"]),
            f"[{_fmt(r['lo'])}, {_fmt(r['hi'])}]",
            str(int(r["boot_failed"])),
            f"{pooled['main'][f'req_{int(r.year)}']:.1f}",
        ]
        for _, r in req.iterrows()
    ]
    latex_longtable(
        T / "tab_requirement_annual.tex",
        ["Year", "N", "Met (\\%)", "Annual", "95\\% CI", "Failed", "Pooled"],
        rows,
        "@{}rrrrrrr@{}",
        caption="Annual and pooled estimates of the carbon requirement (t CO$_2$ per person).",
        label="tab:reqannual",
        notes="Annual: cross-sectional logit for that year, with a country-bootstrap interval. Failed: "
        "bootstrap replications whose fit did not converge or showed separation, which are "
        "excluded from the interval. Pooled: estimate for that year from the pooled model.",
    )
