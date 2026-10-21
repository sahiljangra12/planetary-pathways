"""Tests for the data, measures and estimators. Run with ``pytest``."""

from __future__ import annotations

import re

import numpy as np
import pandas as pd
import pytest

from ppath import analysis as an
from ppath import config, data
from ppath import indicators as ind
from ppath.numbers import Numbers


@pytest.fixture(scope="module")
def panel():
    p, flow = data.build_panel()
    return p, flow


# ------------------------------------------------------------------ sample
def test_sample_is_un_states_only(panel):
    p, _ = panel
    states = set(data.load_states()["iso3"])
    assert set(p["iso3"]) <= states
    assert not p["iso3"].str.startswith("OWID").any()


def test_sample_size_and_threshold(panel):
    p, flow = panel
    assert p["iso3"].nunique() == flow["population_ge_threshold"]
    mean_pop = p.groupby("iso3")["population"].mean()
    assert (mean_pop >= config.MIN_POPULATION).all()


def test_known_members_present(panel):
    p, _ = panel
    for iso in ["TTO", "PSE", "IND", "CHN", "USA", "NGA"]:  # TTO was wrongly dropped in the thesis
        assert iso in set(p["iso3"]), iso


def test_panel_is_unique_and_complete_grid(panel):
    p, _ = panel
    assert not p.duplicated(["iso3", "year"]).any()
    n_years = config.LAST_YEAR - config.FIRST_YEAR + 1
    assert (p.groupby("iso3")["year"].nunique() == n_years).all()


def test_periods_do_not_overlap():
    years = [y for lo, hi in config.PERIODS.values() for y in range(lo, hi + 1)]
    assert len(years) == len(set(years))
    assert min(years) == config.FIRST_YEAR and max(years) == config.LAST_YEAR


def test_gdp_is_constant_ppp(panel):
    p, _ = panel
    usa = p[p["iso3"] == "USA"].set_index("year")["gdp_ppp_pc"]
    # Maddison 2011 int$: US GDP per person was roughly 37k in 1990 and 58-62k in 2019
    assert 30_000 < usa.loc[1990] < 45_000
    assert 50_000 < usa.loc[2019] < 70_000


# ------------------------------------------------------------- transforms
def test_interior_interpolation_never_extrapolates():
    s = pd.Series([np.nan, 1.0, np.nan, np.nan, 4.0, np.nan])
    out = data.interpolate_interior(s, max_gap=3)
    assert np.isnan(out.iloc[0]) and np.isnan(out.iloc[-1])
    assert out.iloc[2] == pytest.approx(2.0) and out.iloc[3] == pytest.approx(3.0)


def test_interior_interpolation_respects_gap_limit():
    s = pd.Series([1.0, np.nan, np.nan, np.nan, np.nan, 6.0])
    out = data.interpolate_interior(s, max_gap=3)
    assert out.iloc[1:5].isna().all()


def test_nearest_fill_respects_distance():
    years = pd.Series(range(2000, 2010))
    s = pd.Series([np.nan] * 9 + [5.0])
    out = data.nearest_fill(s, years, max_years=5)
    assert out.iloc[3] != out.iloc[3]  # 6 years away: stays missing
    assert out.iloc[4] == 5.0


# --------------------------------------------------------------- measures
def _row(**kw):
    base = dict(
        life_expectancy=80.0,
        child_mortality=5.0,
        electricity_access=100.0,
        employment=96.0,
        secondary_enrollment=100.0,
        co2_cons_pc=1.0,
    )
    base.update(kw)
    return base


def test_attainment_ratio_direction_and_cap():
    t_le = config.SOCIAL_THRESHOLDS[0]
    t_u5 = next(t for t in config.SOCIAL_THRESHOLDS if t.var == "child_mortality")
    assert ind.attainment_ratio(pd.Series([74.0, 37.0, 90.0]), t_le).tolist() == [1.0, 0.5, 1.0]
    assert ind.attainment_ratio(pd.Series([25.0, 50.0, 5.0]), t_u5).tolist() == [1.0, 0.5, 1.0]


def test_quadrants():
    df = pd.DataFrame(
        [
            _row(co2_cons_pc=1.0),  # safe and just
            _row(co2_cons_pc=5.0),  # met, overshoot
            _row(life_expectancy=60.0, co2_cons_pc=0.5),  # shortfall, within
            _row(life_expectancy=60.0, co2_cons_pc=5.0),  # shortfall, overshoot
        ]
    )
    q = ind.score(df)["quadrant"].astype(str).tolist()
    assert q == ["Safe and just", "Foundation met, overshoot", "Shortfall, within boundary", "Shortfall and overshoot"]


def test_foundation_requires_complete_data():
    df = pd.DataFrame([_row(employment=np.nan), _row(employment=np.nan, life_expectancy=60.0)])
    s = ind.score(df)
    assert pd.isna(s["foundation_met"].iloc[0])  # unknown indicator: cannot claim the foundation is met
    assert s["foundation_met"].iloc[1] == False  # noqa: E712  a known shortfall is still a shortfall


def test_boundary_is_strict_inequality():
    s = ind.score(pd.DataFrame([_row(co2_cons_pc=config.CO2_BOUNDARY.value)]))
    assert s["overshoot"].iloc[0] == False  # noqa: E712


def test_tolerance_rule():
    df = pd.DataFrame([_row(life_expectancy=71.0)])  # 96% of 74
    assert ind.score(df)["foundation_met"].iloc[0] == False  # noqa: E712
    assert ind.score(df, cutoff=0.95)["foundation_met"].iloc[0] == True  # noqa: E712


def test_boundary_values():
    assert config.CO2_BOUNDARY.value == 1.61
    assert config.CO2_BOUNDARY_15.value == pytest.approx(500e9 / 81 / 7.84e9, abs=0.005)


# ------------------------------------------------------------- estimators
def test_logit_requirement_recovers_truth():
    rng = np.random.default_rng(0)
    co2 = np.exp(rng.uniform(np.log(0.1), np.log(30), 4000))
    true_req, slope = 4.0, 3.0
    p = 1 / (1 + np.exp(-slope * (np.log(co2) - np.log(true_req))))
    d = pd.DataFrame({"y": rng.uniform(size=len(co2)) < p, "c": co2})
    val, status = an.logit_requirement(d, "y", "c")
    assert status == "ok"
    assert val == pytest.approx(true_req, rel=0.08)


def test_pooled_requirement_recovers_trend():
    rng = np.random.default_rng(1)
    rows = []
    for i in range(200):
        base = np.exp(rng.uniform(np.log(0.2), np.log(25)))
        for t in range(2000, 2021):
            req = 8.0 * 0.96 ** (t - 2000)
            co2 = base * np.exp(rng.normal(0, 0.05))
            p = 1 / (1 + np.exp(-3 * (np.log(co2) - np.log(req))))
            rows.append({"iso3": f"C{i}", "year": t, "y": rng.uniform() < p, "c": co2})
    d = pd.DataFrame(rows)
    out = an.pooled_requirement(d, "y", "c", [2000, 2020], reps=50, seed=0)
    assert out["req_2000"] == pytest.approx(8.0, rel=0.15)
    assert out["pct_per_year"] == pytest.approx(-4.0, abs=0.8)
    assert out["pct_per_year_lo"] < out["pct_per_year"] < out["pct_per_year_hi"]


def test_decoupling_classes():
    years = np.arange(2011, 2023)

    def country(iso, gc, gy, level0):
        return pd.DataFrame(
            {
                "iso3": iso,
                "country": iso,
                "year": years,
                "co2_cons_pc": level0 * (1 + gc) ** (years - 2011),
                "gdp_ppp_pc": 10_000 * (1 + gy) ** (years - 2011),
                "life_expectancy": 70.0,
            }
        )

    p = pd.concat(
        [
            country("ABS", -0.03, 0.02, 10),
            country("REL", 0.01, 0.03, 5),
            country("CPL", 0.04, 0.02, 3),
            country("NOG", -0.01, -0.01, 3),
        ]
    )
    dec = an.decoupling(p, 2011, 2022).set_index("iso3")
    assert dec.loc["ABS", "class"] == "Absolute"
    assert dec.loc["REL", "class"] == "Relative"
    assert dec.loc["CPL", "class"] == "Coupled"
    assert dec.loc["NOG", "class"] == "No income growth"
    assert dec.loc["ABS", "co2_growth"] == pytest.approx(-3.0, abs=1e-6)
    # required rate: from the 2022 level to 1.61 t by 2050
    level = 10 * 0.97**11
    assert dec.loc["ABS", "required_growth"] == pytest.approx(100 * ((1.61 / level) ** (1 / 28) - 1))


def test_transition_matrix_counts():
    ps = pd.DataFrame(
        {
            "iso3": ["A", "B", "A", "B"],
            "period": ["x", "x", "y", "y"],
            "quadrant": pd.Categorical(
                ["Safe and just", "Shortfall and overshoot", "Foundation met, overshoot", "Shortfall and overshoot"],
                categories=config.QUADRANT_ORDER,
            ),
        }
    )
    m = an.transition_matrix(ps, "x", "y")
    assert m.to_numpy().sum() == 2
    assert m.loc["Safe and just", "Foundation met, overshoot"] == 1
    assert an.persistence(m) == 0.5


# ------------------------------------------------------------------ outputs
def test_numbers_formatting():
    n = Numbers()
    n.add("aaa", 1234, fmt=",")
    n.add("bbb", -0.04, fmt=".1f")
    assert n.values["aaa"] == "1{,}234" and n.values["bbb"] == "0.0"
    with pytest.raises(ValueError):
        n.add("bad1", 1)
    with pytest.raises(ValueError):
        n.add("ccc", float("nan"), fmt=".1f")


def test_generated_numbers_file_is_valid():
    path = config.PAPER / "numbers.tex"
    if not path.exists():
        pytest.skip("pipeline not run yet")
    text = path.read_text()
    names = re.findall(r"\\newcommand\{\\(n[A-Za-z]+)\}", text)
    assert len(names) == len(set(names))
    assert "nan" not in text.lower().replace("\\n", "")


def test_zero_mortality_is_full_attainment():
    t_u5 = next(t for t in config.SOCIAL_THRESHOLDS if t.var == "child_mortality")
    out = ind.attainment_ratio(pd.Series([0.0, np.nan, 50.0]), t_u5)
    assert out.iloc[0] == 1.0 and np.isnan(out.iloc[1]) and out.iloc[2] == 0.5


def test_period_labels_match_years():
    for label, (lo, hi) in config.PERIODS.items():
        assert label == f"{lo}–{hi}"


def test_fit_logit_reports_separation_and_no_variation():
    x = np.linspace(-2, 2, 40)
    X = np.column_stack([np.ones_like(x), x])
    params, status, _ = an.fit_logit((x > 0).astype(float), X)  # perfectly separated
    assert params is None and status in ("separation", "not_converged", "error")
    params, status, _ = an.fit_logit(np.ones_like(x), X)
    assert params is None and status == "no_variation"


def test_decoupling_scenarios_arithmetic():
    req = 100 * ((1.61 / 5.0) ** (1 / 28) - 1)  # about -3.97% a year
    above = pd.DataFrame({"co2_growth": [-2.0, -3.0], "required_growth": [req, req], "co2_last": [5.0, 5.0],
                          "last_year": [2022, 2022]})
    sc = an.decoupling_scenarios(above, boundary=1.61).set_index("scenario")
    assert sc.loc["Each at the rate required by 2050", "n_by_2050"] == 2
    assert sc.loc["Achieved 2011--2022 rates", "n_by_2050"] == 0
    assert sc.loc["Each country doubles its rate", "n_by_2050"] == 2  # -4% and -6% both beat the required -3.97%
    assert an.years_to_boundary(5.0, 0.0, 1.61) == np.inf
