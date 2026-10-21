"""Social attainment, boundary overshoot and the four-quadrant typology."""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config


def attainment_ratio(x: pd.Series, t: config.Threshold) -> pd.Series:
    """Achievement relative to the threshold, capped at 1 (1 = threshold met)."""
    x = x.astype(float)
    if t.higher_is_better:
        r = x / t.value
    else:
        # zero mortality is full attainment, not missing
        r = (t.value / x.where(x > 0)).mask(x == 0, 1.0)
    return r.clip(upper=1.0)


def add_social(df: pd.DataFrame, thresholds=None, min_indicators=None) -> pd.DataFrame:
    """Add per-indicator ratios, the mean attainment score and threshold counts."""
    thresholds = thresholds or config.SOCIAL_THRESHOLDS
    min_indicators = min_indicators or config.MIN_SOCIAL_INDICATORS
    out = df.copy()
    ratios = pd.DataFrame({t.var: attainment_ratio(out[t.var], t) for t in thresholds}, index=out.index)
    met = ratios.ge(1.0).where(ratios.notna())
    n_obs = ratios.notna().sum(axis=1)
    ok = n_obs >= min_indicators
    out["social_n_obs"] = n_obs
    out["social_complete"] = n_obs == len(thresholds)
    out["_ratio_min_observed"] = ratios.min(axis=1)  # over observed indicators only
    out["_ratio_mean_observed"] = ratios.mean(axis=1)
    out["social_attainment"] = ratios.mean(axis=1).where(ok)
    out["social_min_ratio"] = ratios.min(axis=1).where(ok)
    out["social_n_met"] = met.sum(axis=1).where(ok)
    out["social_share_met"] = (met.sum(axis=1) / n_obs).where(ok)
    out["social_all_met"] = (out["social_share_met"] == 1.0).where(ok)
    return out


def add_overshoot(df: pd.DataFrame, co2_col: str = "co2_cons_pc", boundary: float | None = None) -> pd.DataFrame:
    boundary = boundary or config.CO2_BOUNDARY.value
    out = df.copy()
    out["overshoot_ratio"] = out[co2_col] / boundary
    out["overshoot"] = (out["overshoot_ratio"] > 1).where(out[co2_col].notna())
    return out


def add_quadrant(df: pd.DataFrame, cutoff: float | None = None, rule: str = "min") -> pd.DataFrame:
    """Classify into the four configurations of the thesis, now threshold-anchored.

    rule = "min": foundation met if every observed indicator is within (1 - cutoff)
                  of its threshold, i.e. the lowest capped ratio is >= cutoff (main)
    rule = "mean": foundation met if the mean capped ratio is >= cutoff
    rule = "all": foundation met only if every observed threshold is met exactly
    """
    cutoff = config.FOUNDATION_CUTOFF if cutoff is None else cutoff
    out = df.copy()
    complete = out["social_complete"].astype(bool)
    lo = out["_ratio_min_observed"]
    if rule == "min":
        short = lo < cutoff  # any observed indicator falls short -> shortfall is known
        met = pd.Series(np.where(short, False, np.where(complete & lo.notna(), True, np.nan)), index=out.index)
    elif rule == "all":
        short = lo < 1.0
        met = pd.Series(np.where(short, False, np.where(complete & lo.notna(), True, np.nan)), index=out.index)
    elif rule == "mean":
        m = out["_ratio_mean_observed"]
        met = (m >= cutoff).where(complete & m.notna())
    else:
        raise ValueError(rule)
    met = met.astype(object).where(met.notna())
    met = met.map(lambda v: bool(v) if v == v and v is not None else np.nan)
    out["foundation_met"] = met
    valid = met.notna() & out["overshoot"].notna()
    labels = [
        config.QUADRANTS[(bool(m), bool(o))] if v else np.nan
        for m, o, v in zip(met.fillna(False), out["overshoot"].fillna(False), valid, strict=True)
    ]
    out["quadrant"] = pd.Categorical(labels, categories=config.QUADRANT_ORDER)
    return out


def score(
    df: pd.DataFrame,
    co2_col="co2_cons_pc",
    boundary=None,
    cutoff=None,
    rule="min",
    thresholds=None,
    min_indicators=None,
) -> pd.DataFrame:
    """Full scoring in one call (used by the main specification and every robustness check)."""
    out = add_social(df, thresholds=thresholds, min_indicators=min_indicators)
    out = add_overshoot(out, co2_col=co2_col, boundary=boundary)
    return add_quadrant(out, cutoff=cutoff, rule=rule)
