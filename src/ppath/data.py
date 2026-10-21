"""Load the raw sources and build one harmonised country-year panel.

Sources
-------
* World Development Indicators / FAOSTAT / ILOSTAT extract compiled for the thesis
  (``thesis_dataset.xlsx``): social outcomes, land, fertiliser, water.
* Global Carbon Budget 2025 via Our World in Data (``owid-co2-data.csv``):
  production- and consumption-based CO2, GHG incl. land use, population.
* Maddison Project Database 2023 via Our World in Data: PPP GDP (2011 int$).
* Our World in Data energy dataset: primary energy per capita, renewable share.

Every transformation is a pure function of these files, so the panel can be
rebuilt byte-for-byte from ``data/raw``.
"""

from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd

from . import config

WDI_VARS = {
    "population": "population_wdi",
    "life_expectancy": "life_expectancy",
    "child_mortality": "child_mortality",
    "infant_mortality": "infant_mortality",
    "electricity_access": "electricity_access",
    "secondary_enrollment": "secondary_enrollment",
    "unemployment": "unemployment",
    "female_labor": "female_labor",
    "urban_population_pct": "urban_pct",
    "forest_km2": "forest_km2",
    "forest_pct": "forest_pct",
    "land_total": "land_km2",
    "arable_land_pct": "arable_pct",
    "fertilizer": "fertilizer_kg_ha",
    "water_stress": "water_stress",
    "pm25": "pm25",
    "renewable_energy": "renewable_share",
    "agri_land": "agri_land_pct",
    "energy_use_pc": "energy_use_pc",
}

OWID_CO2_VARS = {
    "consumption_co2_per_capita": "co2_cons_pc",
    "co2_per_capita": "co2_prod_pc",
    "co2_including_luc_per_capita": "co2_luc_pc",
    "ghg_per_capita": "ghg_pc",
    "methane_per_capita": "ch4_pc",
    "nitrous_oxide_per_capita": "n2o_pc",
    "trade_co2_share": "trade_co2_share",
    "gdp": "gdp_ppp",
    "population": "population",
}

OWID_ENERGY_VARS = {
    "energy_per_capita": "energy_pc_kwh",
}


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_states() -> pd.DataFrame:
    states = pd.read_csv(config.STATES)
    states.columns = [c.lower() for c in states.columns]
    iso_col = next(c for c in states.columns if "iso" in c)
    states = states.rename(columns={iso_col: "iso3"})
    assert states["iso3"].is_unique, "duplicate ISO3 codes in state list"
    return states


def load_wdi() -> pd.DataFrame:
    df = pd.read_excel(config.WDI_PANEL, sheet_name="Data")
    keep = ["country", "iso3", "year", *WDI_VARS]
    df = df[keep].rename(columns=WDI_VARS)
    df["year"] = df["year"].astype(int)
    return df


def load_owid_co2() -> pd.DataFrame:
    df = pd.read_csv(config.OWID_CO2, low_memory=False)
    df = df[df["iso_code"].notna() & ~df["iso_code"].str.startswith("OWID")]
    df = df[["iso_code", "year", *OWID_CO2_VARS]].rename(columns={"iso_code": "iso3", **OWID_CO2_VARS})
    return df


def load_owid_energy() -> pd.DataFrame:
    df = pd.read_csv(config.OWID_ENERGY, low_memory=False)
    df = df[df["iso_code"].notna() & ~df["iso_code"].str.startswith("OWID")]
    return df[["iso_code", "year", *OWID_ENERGY_VARS]].rename(columns={"iso_code": "iso3", **OWID_ENERGY_VARS})


def interpolate_interior(s: pd.Series, max_gap: int) -> pd.Series:
    """Linearly fill interior gaps of at most ``max_gap`` consecutive years.

    Leading and trailing gaps are never filled (no extrapolation).
    """
    filled = s.interpolate(method="linear", limit_area="inside")
    isna = s.isna()
    run_id = (isna != isna.shift()).cumsum()
    run_len = isna.groupby(run_id).transform("sum")
    too_long = isna & (run_len > max_gap)
    return filled.mask(too_long)


def nearest_fill(s: pd.Series, years: pd.Series, max_years: int) -> pd.Series:
    """Fill missing values with the nearest observed value of the same series,
    provided it is at most ``max_years`` away. Ties go to the earlier year."""
    obs_years = years[s.notna()].to_numpy()
    if len(obs_years) == 0 or max_years <= 0:
        return s
    obs_vals = s[s.notna()].to_numpy()
    out = s.copy()
    for i in np.flatnonzero(s.isna().to_numpy()):
        dist = np.abs(obs_years - years.iloc[i])
        j = int(np.argmin(dist))
        if dist[j] <= max_years:
            out.iloc[i] = obs_vals[j]
    return out


def build_panel() -> tuple[pd.DataFrame, dict]:
    """Return the analysis panel (one row per country-year) and a sample-flow log."""
    states = load_states()
    wdi = load_wdi()
    co2 = load_owid_co2()
    energy = load_owid_energy()

    years = range(config.FIRST_YEAR, config.LAST_YEAR + 1)
    grid = pd.MultiIndex.from_product([states["iso3"], years], names=["iso3", "year"]).to_frame(index=False)

    panel = (
        grid.merge(wdi.drop(columns="country"), on=["iso3", "year"], how="left")
        .merge(co2, on=["iso3", "year"], how="left")
        .merge(energy, on=["iso3", "year"], how="left")
    )

    names = wdi.drop_duplicates("iso3").set_index("iso3")["country"]
    panel.insert(1, "country", panel["iso3"].map(names))

    # Derived variables -------------------------------------------------------
    panel["population"] = panel["population"].fillna(panel["population_wdi"])
    panel["gdp_ppp_pc"] = panel["gdp_ppp"] / panel["population"]
    panel["employment"] = 100 - panel["unemployment"]
    arable_ha = panel["arable_pct"] / 100 * panel["land_km2"] * 100
    panel["fertilizer_pc"] = panel["fertilizer_kg_ha"] * arable_ha / panel["population"]
    panel = panel.sort_values(["iso3", "year"]).reset_index(drop=True)
    panel["forest_change_pct"] = panel.groupby("iso3")["forest_km2"].pct_change(fill_method=None) * 100

    flow = {"un_states": len(states)}
    # Sample: UN member states + Palestine with mean population >= threshold
    mean_pop = panel.groupby("iso3")["population"].mean()
    flow["with_population_data"] = int(mean_pop.notna().sum())
    keep = mean_pop[mean_pop >= config.MIN_POPULATION].index
    flow["population_ge_threshold"] = len(keep)
    panel = panel[panel["iso3"].isin(keep)].copy()

    # Interior interpolation of short gaps -----------------------------------
    raw_missing = panel.isna().mean()
    value_cols = [c for c in panel.columns if c not in ("iso3", "country", "year")]
    panel[value_cols] = panel.groupby("iso3")[value_cols].transform(
        lambda s: interpolate_interior(s, config.MAX_INTERPOLATION_GAP)
    )
    flow["share_values_interpolated"] = float((raw_missing - panel.isna().mean())[value_cols].clip(lower=0).mean())
    for v in config.EDGE_FILL_VARS if config.EDGE_FILL_YEARS > 0 else []:
        before = panel[v].notna().mean()
        # interior gaps of any length (bracketed by observations), then short edges
        panel[v] = panel.groupby("iso3")[v].transform(lambda s: s.interpolate(method="linear", limit_area="inside"))
        panel[v] = panel.groupby("iso3", group_keys=False).apply(
            lambda g, v=v: nearest_fill(g[v], g["year"], config.EDGE_FILL_YEARS)
        )
        flow[f"edge_filled_{v}"] = float(panel[v].notna().mean() - before)

    # Period label
    panel["period"] = None
    for label, (lo, hi) in config.PERIODS.items():
        panel.loc[panel["year"].between(lo, hi), "period"] = label
    assert panel["period"].notna().all()
    assert not panel.duplicated(["iso3", "year"]).any()
    return panel.reset_index(drop=True), flow


def period_means(panel: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Country-period means; a value is kept only if enough years are observed."""
    g = panel.groupby(["iso3", "country", "period"], sort=False)
    means = g[cols].mean()
    share = g[cols].apply(lambda d: d.notna().mean())
    means = means.where(share >= config.MIN_YEARS_FOR_PERIOD_MEAN)
    return means.reset_index()


def coverage_table(panel: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    rows = []
    for c in cols:
        s = panel[["iso3", "period", c]].dropna()
        rows.append(
            {
                "variable": c,
                "country_years": len(s),
                "share_of_panel": len(s) / len(panel),
                "countries": s["iso3"].nunique(),
                "first_year": int(panel.loc[panel[c].notna(), "year"].min()) if len(s) else np.nan,
                "last_year": int(panel.loc[panel[c].notna(), "year"].max()) if len(s) else np.nan,
            }
        )
    return pd.DataFrame(rows)
