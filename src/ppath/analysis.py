"""Analyses for the four research questions.

RQ1  How many countries fall short socially and overshoot the climate boundary,
     and how has that changed since 1990?
RQ2  How much CO2 per person has meeting the social foundation required, and is
     that requirement falling?
RQ3  Which countries decoupled consumption-based CO2 from income, and are they
     decoupling fast enough to reach the boundary by 2050?
RQ4  Which pressure-development configurations persist, and how do countries
     move between them?
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
from linearmodels.panel import PanelOLS
from sklearn.metrics import adjusted_rand_score
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler
from statsmodels.tools.sm_exceptions import ConvergenceWarning, PerfectSeparationError, PerfectSeparationWarning

from . import config

# ---------------------------------------------------------------------------
# RQ1: distribution over time
# ---------------------------------------------------------------------------


def quadrant_shares(scored: pd.DataFrame, by: str = "year", weight: str | None = None) -> pd.DataFrame:
    d = scored.dropna(subset=["quadrant"])
    if weight:
        w = d.groupby([by, "quadrant"], observed=False)[weight].sum()
        return (w / w.groupby(level=0).transform("sum")).unstack()
    return d.groupby(by)["quadrant"].value_counts(normalize=True).unstack()[config.QUADRANT_ORDER]


def balanced(scored: pd.DataFrame, col: str = "quadrant") -> pd.DataFrame:
    """Keep countries observed in every year (so shares are not driven by entry/exit)."""
    n_years = scored["year"].nunique()
    ok = scored.dropna(subset=[col]).groupby("iso3")["year"].nunique()
    return scored[scored["iso3"].isin(ok[ok == n_years].index)]


# ---------------------------------------------------------------------------
# RQ2: carbon requirement of meeting the social foundation
# ---------------------------------------------------------------------------


FIT_OK = "ok"


def fit_logit(y: np.ndarray, X: np.ndarray) -> tuple[np.ndarray | None, str, list[str]]:
    """Fit a logit by maximum likelihood and classify the outcome of the fit.

    Warnings are recorded, not suppressed. A fit is accepted only if the optimiser
    reports convergence, no (quasi-)perfect separation is detected and all
    parameters are finite. Returns (params or None, status, warning messages).
    Status is one of: ok, no_variation, separation, not_converged, error, nonfinite.
    """
    if np.nanmin(y) == np.nanmax(y):
        return None, "no_variation", []
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            res = sm.Logit(y, X).fit(disp=0, maxiter=200)
        except PerfectSeparationError:
            return None, "separation", [str(w.message) for w in caught]
        except Exception as exc:  # numerical failure of the optimiser
            return None, "error", [repr(exc)]
    msgs = [f"{w.category.__name__}: {w.message}" for w in caught]
    if any(issubclass(w.category, PerfectSeparationWarning) for w in caught):
        return None, "separation", msgs
    if not res.mle_retvals.get("converged", False) or any(issubclass(w.category, ConvergenceWarning) for w in caught):
        return None, "not_converged", msgs
    if not np.all(np.isfinite(res.params)):
        return None, "nonfinite", msgs
    return np.asarray(res.params), FIT_OK, msgs


def logit_requirement(d: pd.DataFrame, outcome: str, co2_col: str) -> tuple[float, str]:
    """CO2 per capita at which the fitted probability of meeting the outcome is 0.5.

    Logit of P(outcome) on log CO2 per capita; the 50% point is exp(-a/b).
    Returns (value, status). The value is NaN when the fit failed (status says why)
    or when the slope is not positive (status "nonpositive_slope"), in which case a
    50% point on a rising curve does not exist.
    """
    d = d[[outcome, co2_col]].dropna()
    d = d[d[co2_col] > 0]
    y = d[outcome].astype(float).to_numpy()
    X = sm.add_constant(np.log(d[co2_col].to_numpy()))
    params, status, _ = fit_logit(y, X)
    if status != FIT_OK:
        return np.nan, status
    a, b = params
    if b <= 0:
        return np.nan, "nonpositive_slope"
    return float(np.exp(-a / b)), FIT_OK


def requirement_by_year(scored: pd.DataFrame, outcome: str, co2_col: str, reps: int, seed: int) -> pd.DataFrame:
    """Annual carbon requirement with country-bootstrap 95% intervals.

    Years with fewer than MIN_CROSS_SECTION classified countries are skipped. For
    each year the status of the point estimate and the number of failed bootstrap
    fits (by reason) are recorded; failed replications are excluded from the
    percentile interval and reported, never silently dropped.
    """
    rng = np.random.default_rng(seed)
    rows = []
    for year, d in scored.groupby("year"):
        d = d.dropna(subset=[outcome, co2_col])
        if len(d) < config.MIN_CROSS_SECTION:
            continue
        est, status = logit_requirement(d, outcome, co2_col)
        boots, fails = [], {}
        idx = np.arange(len(d))
        for _ in range(reps):
            b, st = logit_requirement(d.iloc[rng.choice(idx, size=len(idx), replace=True)], outcome, co2_col)
            if st == FIT_OK:
                boots.append(b)
            else:
                fails[st] = fails.get(st, 0) + 1
        boots = np.array(boots, dtype=float)
        rows.append(
            {
                "year": year,
                "n": len(d),
                "n_met": int(d[outcome].astype(bool).sum()),
                "share_met": d[outcome].astype(float).mean(),
                "requirement": est,
                "status": status,
                "lo": np.quantile(boots, 0.025) if len(boots) else np.nan,
                "hi": np.quantile(boots, 0.975) if len(boots) else np.nan,
                "boot_ok": len(boots),
                "boot_failed": reps - len(boots),
                "boot_fail_reasons": ";".join(f"{k}={v}" for k, v in sorted(fails.items())),
            }
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# RQ2 (within-country): two-way fixed-effects models
# ---------------------------------------------------------------------------


def fe_models(panel: pd.DataFrame, outcomes: dict[str, str], pressure: str, control_income: bool) -> pd.DataFrame:
    rows = []
    for name, y in outcomes.items():
        cols = [y, pressure, "gdp_ppp_pc"] if control_income else [y, pressure]
        d = panel.dropna(subset=cols).copy()
        d = d[(d[pressure] > 0) & (d["gdp_ppp_pc"] > 0 if control_income else True)]
        d["log_pressure"] = np.log(d[pressure])
        exog = ["log_pressure"]
        if control_income:
            d["log_gdp"] = np.log(d["gdp_ppp_pc"])
            exog.append("log_gdp")
        d = d.set_index(["iso3", "year"])
        mod = PanelOLS(d[y], d[exog], entity_effects=True, time_effects=True)
        res = mod.fit(cov_type="clustered", cluster_entity=True)
        for v in exog:
            rows.append(
                {
                    "outcome": name,
                    "pressure": pressure,
                    "income_control": control_income,
                    "term": v,
                    "coef": res.params[v],
                    "se": res.std_errors[v],
                    "p": res.pvalues[v],
                    "n_obs": int(res.nobs),
                    "n_countries": int(res.entity_info["total"]),
                    "r2_within": res.rsquared_within,
                }
            )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# RQ3: decoupling
# ---------------------------------------------------------------------------


def _trend(y: pd.Series, years: pd.Series) -> tuple[float, float, float]:
    """Annual growth rate (%) of y from a log-linear OLS trend, with its 95% CI."""
    X = sm.add_constant(years - years.min())
    res = sm.OLS(np.log(y), X).fit()
    b = res.params.iloc[1]
    lo, hi = res.conf_int().iloc[1]
    return 100 * (np.exp(b) - 1), 100 * (np.exp(lo) - 1), 100 * (np.exp(hi) - 1)


def decoupling(
    panel: pd.DataFrame, start: int, end: int, co2_col: str = "co2_cons_pc", boundary: float | None = None
) -> pd.DataFrame:
    boundary = boundary or config.CO2_BOUNDARY.value
    rows = []
    d = panel[panel["year"].between(start, end)]
    for iso, g in d.groupby("iso3"):
        g = g.dropna(subset=[co2_col, "gdp_ppp_pc"])
        g = g[(g[co2_col] > 0) & (g["gdp_ppp_pc"] > 0)]
        if len(g) < config.DECOUPLING_MIN_YEARS:
            continue
        gc, gc_lo, gc_hi = _trend(g[co2_col], g["year"])
        gy, _, _ = _trend(g["gdp_ppp_pc"], g["year"])
        if gy <= 0:
            cls = "No income growth"
        elif gc < 0:
            cls = "Absolute"
        elif gc < gy:
            cls = "Relative"
        else:
            cls = "Coupled"
        last = g.sort_values("year").iloc[-1]
        level = last[co2_col]
        horizon = config.PARIS_YEAR - int(last["year"])
        required = 100 * ((boundary / level) ** (1 / horizon) - 1) if level > boundary else 0.0
        if level <= boundary:
            years_to = 0.0
        elif gc < 0:
            years_to = np.log(boundary / level) / np.log(1 + gc / 100)
        else:
            years_to = np.inf
        rows.append(
            {
                "iso3": iso,
                "country": g["country"].iloc[0],
                "n_years": len(g),
                "co2_growth": gc,
                "co2_growth_lo": gc_lo,
                "co2_growth_hi": gc_hi,
                "gdp_growth": gy,
                "class": cls,
                "robust_absolute": cls == "Absolute" and gc_hi < 0,
                "co2_last": level,
                "last_year": int(last["year"]),
                "above_boundary": bool(level > boundary),
                "required_growth": required,
                "on_track": (level <= boundary) or (gc <= required),
                "years_to_boundary": years_to,
                "le_change": g["life_expectancy"].iloc[-1] - g["life_expectancy"].iloc[0]
                if g["life_expectancy"].notna().iloc[[0, -1]].all()
                else np.nan,
            }
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# RQ4: configurations and transitions
# ---------------------------------------------------------------------------


def transition_matrix(period_scored: pd.DataFrame, origin: str, dest: str) -> pd.DataFrame:
    a = period_scored[period_scored["period"] == origin].set_index("iso3")["quadrant"]
    b = period_scored[period_scored["period"] == dest].set_index("iso3")["quadrant"]
    both = pd.concat([a.rename("from"), b.rename("to")], axis=1).dropna()
    m = pd.crosstab(both["from"], both["to"], dropna=False)
    return m.reindex(index=config.QUADRANT_ORDER, columns=config.QUADRANT_ORDER, fill_value=0)


def persistence(m: pd.DataFrame) -> float:
    return float(np.trace(m.to_numpy()) / m.to_numpy().sum())


def frontier(period_scored: pd.DataFrame, period: str, n: int = 10) -> pd.DataFrame:
    """Countries meeting the social foundation with the lowest per-capita CO2."""
    d = period_scored[(period_scored["period"] == period) & (period_scored["foundation_met"] == True)]  # noqa: E712
    return d.nsmallest(n, "overshoot_ratio")


def gmm_check(period_scored: pd.DataFrame, co2_col: str, seed: int) -> dict:
    """Data-driven check: does a Gaussian mixture recover the four configurations?"""
    d = period_scored.dropna(subset=[co2_col, "social_attainment", "quadrant"]).copy()
    X = StandardScaler().fit_transform(np.column_stack([np.log(d[co2_col]), d["social_attainment"]]))
    bics = {}
    models = {}
    for k in range(1, config.GMM_MAX_COMPONENTS + 1):
        gm = GaussianMixture(n_components=k, covariance_type="full", n_init=10, random_state=seed).fit(X)
        bics[k] = gm.bic(X)
        models[k] = gm
    k_best = min(bics, key=bics.get)
    ari4 = adjusted_rand_score(d["quadrant"].astype(str), models[4].predict(X))
    ari_best = adjusted_rand_score(d["quadrant"].astype(str), models[k_best].predict(X))
    # bootstrap stability of the 4-component solution
    rng = np.random.default_rng(seed)
    ref = models[4].predict(X)
    stab = []
    for _ in range(200):
        idx = rng.choice(len(X), size=len(X), replace=True)
        gm = GaussianMixture(n_components=4, covariance_type="full", n_init=3, random_state=int(rng.integers(1e9))).fit(
            X[idx]
        )
        stab.append(adjusted_rand_score(ref, gm.predict(X)))
    return {
        "bic": bics,
        "k_best": k_best,
        "ari_k4": ari4,
        "ari_best": ari_best,
        "stability_k4_median": float(np.median(stab)),
        "n": len(d),
    }


def long_difference(
    period_df: pd.DataFrame, outcome: str, pressure: str, first: str | None = None, last: str | None = None
) -> dict:
    """Change in outcome between first and last period on change in log pressure and log income.

    A cross-country 'long difference' removes time-invariant country traits without
    assuming that year-to-year fluctuations carry the signal.
    """
    first = first or list(config.PERIODS)[0]
    last = last or list(config.PERIODS)[-1]
    a = period_df[period_df["period"] == first].set_index("iso3")
    b = period_df[period_df["period"] == last].set_index("iso3")
    d = (
        pd.DataFrame(
            {
                "dy": b[outcome] - a[outcome],
                "dp": np.log(b[pressure]) - np.log(a[pressure]),
                "dg": np.log(b["gdp_ppp_pc"]) - np.log(a["gdp_ppp_pc"]),
                "y0": a[outcome],
            }
        )
        .replace([np.inf, -np.inf], np.nan)
        .dropna()
    )
    X = sm.add_constant(d[["dp", "dg", "y0"]])
    res = sm.OLS(d["dy"], X).fit(cov_type="HC3")
    return {
        "outcome": outcome,
        "pressure": pressure,
        "coef": res.params["dp"],
        "se": res.bse["dp"],
        "p": res.pvalues["dp"],
        "coef_gdp": res.params["dg"],
        "p_gdp": res.pvalues["dg"],
        "n": int(res.nobs),
    }


def _pooled_fit(d: pd.DataFrame, outcome: str, co2_col: str, ref_year: int) -> tuple[tuple | None, str]:
    y = d[outcome].astype(float).to_numpy()
    X = np.column_stack([np.ones(len(d)), np.log(d[co2_col].to_numpy()), d["year"].to_numpy() - ref_year])
    params, status, _ = fit_logit(y, X)
    if status != FIT_OK:
        return None, status
    a, b, c = params
    if b <= 0:
        return None, "nonpositive_slope"
    return (a, b, c), FIT_OK


def pooled_requirement(
    scored: pd.DataFrame, outcome: str, co2_col: str, years: list[int], reps: int, seed: int, ref_year: int = 2000
) -> dict:
    """Pooled logit P(outcome) = F(a + b log CO2 + c (year - ref)).

    The CO2 level at which P = 0.5 in year t is exp(-(a + c (t - ref)) / b), so the
    requirement changes by exp(-c / b) - 1 per year. Confidence intervals come from a
    country-cluster bootstrap (whole countries are resampled with all their years).
    """
    d = scored.dropna(subset=[outcome, co2_col])
    d = d[d[co2_col] > 0]
    d = d[
        d["year"].isin(
            d.groupby("year")[outcome]
            .transform("size")
            .pipe(lambda n: d.loc[n >= config.MIN_CROSS_SECTION, "year"])
            .unique()
        )
    ]

    def summarise(params):
        a, b, c = params
        out = {f"req_{t}": float(np.exp(-(a + c * (t - ref_year)) / b)) for t in years}
        out["pct_per_year"] = float(100 * (np.exp(-c / b) - 1))
        return out

    point, status = _pooled_fit(d, outcome, co2_col, ref_year)
    if point is None:
        raise RuntimeError(f"pooled logit failed on the full sample: {status}")
    est = summarise(point)
    a_, b_, c_ = point
    rng = np.random.default_rng(seed)
    groups = {k: v.index.to_numpy() for k, v in d.groupby("iso3")}
    keys = np.array(list(groups))
    boots, fails = [], {}
    for _ in range(reps):
        pick = rng.choice(keys, size=len(keys), replace=True)
        idx = np.concatenate([groups[k] for k in pick])
        p, st = _pooled_fit(d.loc[idx], outcome, co2_col, ref_year)
        if p is not None:
            boots.append(summarise(p))
        else:
            fails[st] = fails.get(st, 0) + 1
    boots = pd.DataFrame(boots)
    out = {
        "n_obs": len(d),
        "n_countries": d["iso3"].nunique(),
        "n_years": d["year"].nunique(),
        "first_year": int(d["year"].min()),
        "last_year": int(d["year"].max()),
        "n_met": int(d[outcome].astype(bool).sum()),
        "slope_log_co2": float(b_),
        "slope_year": float(c_),
        "boot_ok": len(boots),
        "boot_failed": reps - len(boots),
        "boot_fail_reasons": fails,
    }
    for k, v in est.items():
        out[k] = v
        out[f"{k}_lo"] = float(boots[k].quantile(0.025))
        out[f"{k}_hi"] = float(boots[k].quantile(0.975))
    return out


# ---------------------------------------------------------------------------
# Missing data and sample composition
# ---------------------------------------------------------------------------


def classification_status(scored: pd.DataFrame, co2_col: str = "co2_cons_pc") -> pd.Series:
    """Why each country-year is or is not classified into a configuration."""
    st = pd.Series("Classified", index=scored.index)
    no_co2 = scored[co2_col].isna()
    undetermined = scored["foundation_met"].isna()
    st[no_co2 & ~undetermined] = "No consumption CO2"
    st[undetermined & ~no_co2] = "Social status undetermined"
    st[undetermined & no_co2] = "Both missing"
    return st


def compare_groups(df: pd.DataFrame, flag: pd.Series, variables: dict[str, str]) -> pd.DataFrame:
    """Compare countries in (flag True) and out of a sample: means, medians, Mann-Whitney p."""
    from scipy.stats import mannwhitneyu

    rows = []
    for col, label in variables.items():
        a = df.loc[flag, col].dropna()
        b = df.loc[~flag, col].dropna()
        p = mannwhitneyu(a, b).pvalue if len(a) > 2 and len(b) > 2 else np.nan
        rows.append(
            {
                "variable": label,
                "in_mean": a.mean(),
                "in_median": a.median(),
                "in_n": len(a),
                "out_mean": b.mean(),
                "out_median": b.median(),
                "out_n": len(b),
                "p_mannwhitney": p,
            }
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Decoupling scenarios
# ---------------------------------------------------------------------------


def years_to_boundary(level: float, rate_pct: float, boundary: float) -> float:
    if level <= boundary:
        return 0.0
    if rate_pct >= 0:
        return np.inf
    return float(np.log(boundary / level) / np.log(1 + rate_pct / 100))


def decoupling_scenarios(above: pd.DataFrame, boundary: float | None = None) -> pd.DataFrame:
    """Counterfactual rates for absolute decouplers above the boundary.

    Each scenario replaces every country's achieved 2011-2022 rate with an
    alternative constant annual rate from the last observed level. These are
    arithmetic illustrations, not forecasts.
    """
    boundary = boundary or config.CO2_BOUNDARY.value
    achieved = above["co2_growth"]
    scenarios = {
        "Achieved 2011--2022 rates": achieved,
        "Each country doubles its rate": 2 * achieved,
        "All at the 90th-percentile rate": pd.Series(achieved.quantile(0.10), index=above.index),
        "All at the fastest achieved rate": pd.Series(achieved.min(), index=above.index),
        "Each at the rate required by 2050": above["required_growth"],
    }
    rows = []
    for name, rate in scenarios.items():
        yrs = np.array([years_to_boundary(lv, r, boundary) for lv, r in zip(above["co2_last"], rate, strict=True)])
        reach = above["last_year"].to_numpy() + yrs
        rows.append(
            {
                "scenario": name,
                "median_rate": float(np.median(rate)),
                "n_by_2050": int((reach <= config.PARIS_YEAR + 1e-9).sum()),
                "n": len(above),
                "median_year": float(np.median(reach)),
            }
        )
    return pd.DataFrame(rows)


def descriptives(df: pd.DataFrame, variables: dict[str, str], by: str = "period") -> pd.DataFrame:
    rows = []
    for col, label in variables.items():
        for k, g in df.groupby(by, sort=False):
            x = g[col].dropna()
            rows.append(
                {
                    "variable": label,
                    by: k,
                    "n": len(x),
                    "mean": x.mean(),
                    "sd": x.std(),
                    "p10": x.quantile(0.1),
                    "median": x.median(),
                    "p90": x.quantile(0.9),
                }
            )
    return pd.DataFrame(rows)
