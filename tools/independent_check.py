"""Independent re-implementation of the paper's headline results.

This script deliberately does NOT import the ``ppath`` package. It re-derives the
sample, the measures, the classifications and the main estimates directly from
the raw files with separately written code, and compares each result with the
value printed in the paper (``paper/numbers.tex``) at the precision shown there.

Usage: python tools/independent_check.py      (exit code 1 if any check fails)
"""

from __future__ import annotations

import re
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
B = 1.61
YEARS = range(1990, 2023)
PERIODS = {"P1": (1990, 2000), "P2": (2001, 2010), "P3": (2011, 2022)}
THR = {"life_expectancy": (74.0, True), "child_mortality": (25.0, False),
       "electricity_access": (95.0, True), "employment": (94.0, True)}

# ----------------------------------------------------------------------------- load
states = pd.read_csv(RAW / "sovereign_states.csv")
states.columns = [c.lower() for c in states.columns]
iso_states = set(states[[c for c in states.columns if "iso" in c][0]])
wdi = pd.read_excel(RAW / "thesis_dataset.xlsx", sheet_name="Data")
wdi = wdi[["iso3", "country", "year", "population", "life_expectancy", "child_mortality",
           "electricity_access", "unemployment", "secondary_enrollment"]].rename(
    columns={"population": "pop_wdi"})
owid = pd.read_csv(RAW / "owid-co2-data.csv", low_memory=False)
owid = owid[owid["iso_code"].isin(iso_states)][["iso_code", "year", "population", "gdp",
                                                 "consumption_co2_per_capita", "co2_per_capita"]]
owid = owid.rename(columns={"iso_code": "iso3", "consumption_co2_per_capita": "cons",
                            "co2_per_capita": "prod"})

grid = pd.DataFrame([(i, y) for i in sorted(iso_states) for y in YEARS], columns=["iso3", "year"])
df = grid.merge(wdi.drop(columns="country"), how="left").merge(owid, how="left")
df["population"] = df["population"].fillna(df["pop_wdi"])
df["employment"] = 100 - df["unemployment"]
df["gdp_pc"] = df["gdp"] / df["population"]
names = wdi.drop_duplicates("iso3").set_index("iso3")["country"]
df["country"] = df["iso3"].map(names)

keep = df.groupby("iso3")["population"].mean()
keep = keep[keep >= 1e6].index
df = df[df["iso3"].isin(keep)].sort_values(["iso3", "year"]).reset_index(drop=True)


# --------------------------------------------------------------- gap handling
def fill_short(s: pd.Series, k: int = 3) -> pd.Series:
    out = s.copy()
    vals = s.to_numpy(dtype=float)
    isn = np.isnan(vals)
    i = 0
    while i < len(vals):
        if isn[i]:
            j = i
            while j < len(vals) and isn[j]:
                j += 1
            if i > 0 and j < len(vals) and (j - i) <= k:
                for t in range(i, j):
                    out.iloc[t] = vals[i - 1] + (vals[j] - vals[i - 1]) * (t - i + 1) / (j - i + 1)
            i = j
        else:
            i += 1
    return out


def fill_long_and_edges(s: pd.Series, k: int = 5) -> pd.Series:
    vals = s.to_numpy(dtype=float)
    obs = np.flatnonzero(~np.isnan(vals))
    out = vals.copy()
    if len(obs) == 0:
        return s
    for t in range(len(vals)):
        if np.isnan(vals[t]):
            if obs[0] < t < obs[-1]:  # interior: linear between neighbours
                lo = obs[obs < t].max()
                hi = obs[obs > t].min()
                out[t] = vals[lo] + (vals[hi] - vals[lo]) * (t - lo) / (hi - lo)
            else:  # edge: nearest observation within k years (ties to earlier)
                d = np.abs(obs - t)
                j = int(np.argmin(d))
                if d[j] <= k:
                    out[t] = vals[obs[j]]
    return pd.Series(out, index=s.index)


value_cols = ["population", "life_expectancy", "child_mortality", "electricity_access", "employment",
              "secondary_enrollment", "cons", "prod", "gdp_pc"]
for c in value_cols:
    df[c] = df.groupby("iso3")[c].transform(fill_short)
for c in ["secondary_enrollment", "electricity_access"]:
    df[c] = df.groupby("iso3")[c].transform(fill_long_and_edges)


# --------------------------------------------------------------- classification
def classify(d: pd.DataFrame, co2: str = "cons", thr: dict = THR, cutoff: float = 1.0) -> pd.DataFrame:
    d = d.copy()
    ratios = {}
    for v, (t, hib) in thr.items():
        x = d[v]
        r = x / t if hib else t / x.where(x > 0)
        if not hib:
            r = r.mask(x == 0, 1.0)
        ratios[v] = r.clip(upper=1)
    R = pd.DataFrame(ratios)
    complete = R.notna().all(axis=1)
    any_short = (R < cutoff).any(axis=1)
    met = pd.Series(np.nan, index=d.index, dtype=object)
    met[any_short] = False
    met[~any_short & complete] = True
    d["met"] = met
    d["over"] = (d[co2] > B).where(d[co2].notna())
    ok = d["met"].notna() & d["over"].notna()
    d["cfg"] = np.where(ok, np.where(d["met"] == True, np.where(d["over"] == True, "MO", "SJ"),  # noqa: E712
                                    np.where(d["over"] == True, "SO", "SW")), None)  # noqa: E712
    d["minratio"] = R.min(axis=1).where(R.notna().sum(axis=1) >= 3)
    return d


ann = classify(df)
ann = ann[ann["year"] >= 1991]

# period means (at least half the years observed)
per_rows = []
for iso, g in df.groupby("iso3"):
    for p, (lo, hi) in PERIODS.items():
        h = g[g["year"].between(lo, hi)]
        row = {"iso3": iso, "period": p}
        for c in value_cols:
            row[c] = h[c].mean() if h[c].notna().mean() >= 0.5 else np.nan
        per_rows.append(row)
per = classify(pd.DataFrame(per_rows))

R: dict[str, float | str] = {}
R["NCountries"] = df["iso3"].nunique()
R["NCons"] = df.dropna(subset=["cons"])["iso3"].nunique()
R["NEverSafeYears"] = int((ann["cfg"] == "SJ").sum())
for p, key in [("P1", "One"), ("P2", "Two")]:
    nxt = {"P1": "P2", "P2": "P3"}[p]
    a = per[per["period"] == p].set_index("iso3")["cfg"]
    b = per[per["period"] == nxt].set_index("iso3")["cfg"]
    both = pd.concat([a, b], axis=1, keys=["a", "b"]).dropna()
    R[f"Persist{key}"] = round(100 * (both["a"] == both["b"]).mean())
    if p == "P2":
        R["IntoSafe"] = int(((both["b"] == "SJ") & (both["a"] != "SJ")).sum())
counts = per[per["period"] == "P3"]["cfg"].value_counts()

# crossers
cross, sust = [], []
for iso, g in ann.dropna(subset=["met"]).groupby("iso3"):
    g = g.sort_values("year")
    if g["met"].iloc[0] is False or g["met"].iloc[0] == False:  # noqa: E712
        first = g[g["met"] == True]  # noqa: E712
        if len(first) and pd.notna(first["over"].iloc[0]):
            cross.append((iso, first["over"].iloc[0], first["cons"].iloc[0]))
for iso, g in ann.groupby("iso3"):
    g = g.sort_values("year").reset_index(drop=True)
    first_obs = g.dropna(subset=["met"])
    if not len(first_obs) or first_obs["met"].iloc[0] != False:  # noqa: E712
        continue
    m = (g["met"] == True).to_numpy()  # noqa: E712
    for i in range(len(g) - 2):
        if m[i] and m[i + 1] and m[i + 2]:
            if pd.notna(g.loc[i, "over"]):
                sust.append((iso, g.loc[i, "over"], g.loc[i, "cons"]))
            break
R["NCrossers"] = len(cross)
R["NCrossersAbove"] = sum(1 for c in cross if c[1] == True)  # noqa: E712
R["CrossCarbonMedian"] = round(float(np.median([c[2] for c in cross])), 1)
R["NCrossersSust"] = len(sust)
R["NCrossersSustAbove"] = sum(1 for c in sust if c[1] == True)  # noqa: E712


# --------------------------------------------------------------- carbon requirement
def logit(y, X):
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # any warning = failure here, to be strict
        return sm.Logit(y, X).fit(disp=0, maxiter=300)


def pooled(d: pd.DataFrame, co2: str):
    d = d.dropna(subset=["met", co2])
    d = d[d[co2] > 0]
    y = (d["met"] == True).astype(float).to_numpy()  # noqa: E712
    X = np.column_stack([np.ones(len(d)), np.log(d[co2]), d["year"] - 2000])
    a, b, c = logit(y, X).params
    req = {t: float(np.exp(-(a + c * (t - 2000)) / b)) for t in (1991, 2000, 2022)}
    return req, 100 * (np.exp(-c / b) - 1)


req, trend = pooled(ann, "cons")
R["ReqStart"] = round(req[1991])
R["ReqMid"] = round(req[2000], 1)
R["ReqEnd"] = round(req[2022], 1)
R["ReqTrend"] = round(-trend, 1)
R["ReqEndMultiple"] = round(req[2022] / B, 1)
d22 = ann[(ann["year"] == 2022)].dropna(subset=["met", "cons"])
fit = logit((d22["met"] == True).astype(float).to_numpy(),  # noqa: E712
            sm.add_constant(np.log(d22["cons"].to_numpy())))
R["ReqAnnualEnd"] = round(float(np.exp(-fit.params[0] / fit.params[1])), 1)
health = classify(df[df["year"] >= 1990], thr={k: v for k, v in THR.items()
                                                 if k in ("life_expectancy", "child_mortality")})
hreq, htrend = pooled(health, "cons")
R["ReqHealthEnd"] = round(hreq[2022], 1)
R["ReqTrendHealth"] = round(-htrend, 1)
noemp = classify(df[df["year"] >= 1991], thr={k: v for k, v in THR.items() if k != "employment"})
R["RobReqNoEmp"] = round(pooled(noemp, "cons")[0][2022], 1)
edu = dict(THR, secondary_enrollment=(95.0, True))
R["RobReqEdu"] = round(pooled(classify(df[df["year"] >= 1991], thr=edu), "cons")[0][2022], 1)
tol = classify(df[df["year"] >= 1991], cutoff=0.95)
R["RobReqTol"] = round(pooled(tol, "cons")[0][2022], 1)
prod = classify(df[df["year"] >= 1991], co2="prod")
R["ReqProdEnd"] = round(pooled(prod, "prod")[0][2022], 1)
R["ProdSafeYearsAll"] = int((prod["cfg"] == "SJ").sum())


# --------------------------------------------------------------- decoupling
def trend_rate(y, t):
    X = sm.add_constant(t - t.min())
    res = sm.OLS(np.log(y), X).fit()
    return 100 * (np.exp(res.params.iloc[1]) - 1), 100 * (np.exp(res.conf_int().iloc[1, 1]) - 1)


def decouple(lo, hi):
    rows = []
    for iso, g in df[df["year"].between(lo, hi)].groupby("iso3"):
        g = g.dropna(subset=["cons", "gdp_pc"])
        g = g[(g["cons"] > 0) & (g["gdp_pc"] > 0)]
        if len(g) < 8:
            continue
        gc, gc_hi = trend_rate(g["cons"], g["year"])
        gy, _ = trend_rate(g["gdp_pc"], g["year"])
        cls = "none" if gy <= 0 else "abs" if gc < 0 else "rel" if gc < gy else "cpl"
        last = g.sort_values("year").iloc[-1]
        req_r = 100 * ((B / last["cons"]) ** (1 / (2050 - last["year"])) - 1) if last["cons"] > B else 0.0
        rows.append(dict(iso=iso, cls=cls, gc=gc, gc_hi=gc_hi, level=last["cons"], year=last["year"], req=req_r))
    return pd.DataFrame(rows)


d1, d2 = decouple(2001, 2010), decouple(2011, 2022)
R["DecAbsEarly"] = int((d1["cls"] == "abs").sum())
R["DecAbsLate"] = int((d2["cls"] == "abs").sum())
R["DecAbsLateRobust"] = int(((d2["cls"] == "abs") & (d2["gc_hi"] < 0)).sum())
R["DecN"] = len(d2)
above = d2[(d2["cls"] == "abs") & (d2["level"] > B)]
R["DecAbsAbove"] = len(above)
R["DecAboveOnTrack"] = int((above["gc"] <= above["req"]).sum())
R["DecMedianAchieved"] = round(-above["gc"].median(), 1)
R["DecMedianRequired"] = round(-above["req"].median(), 1)


def n_by_2050(rates):
    yrs = [0 if lv <= B else (np.inf if r >= 0 else np.log(B / lv) / np.log(1 + r / 100))
           for lv, r in zip(above["level"], rates, strict=True)]
    return int(sum(y + yr <= 2050 + 1e-9 for y, yr in zip(above["year"], yrs, strict=True)))


R["ScenDouble"] = n_by_2050(2 * above["gc"])
R["ScenFastest"] = n_by_2050([above["gc"].min()] * len(above))

# --------------------------------------------------------------- fixed effects (dummy-variable OLS)
# fixed effects use all years 1990-2022 (no social classification needed)
fe = classify(df).dropna(subset=["life_expectancy", "cons", "gdp_pc"])
fe = fe[(fe["cons"] > 0) & (fe["gdp_pc"] > 0)].copy()
fe["lc"] = np.log(fe["cons"])
fe["lg"] = np.log(fe["gdp_pc"])
X = pd.get_dummies(fe[["iso3", "year"]].astype(str), drop_first=True, dtype=float)
X = sm.add_constant(pd.concat([fe[["lc", "lg"]], X], axis=1))
res = sm.OLS(fe["life_expectancy"], X).fit(cov_type="cluster", cov_kwds={"groups": fe["iso3"].astype("category").cat.codes})
R["FeLE"] = round(float(res.params["lc"]), 2)

# --------------------------------------------------------------- shares, transitions, frontier
yrs = ann["year"].nunique()
okc = ann.dropna(subset=["cfg"]).groupby("iso3")["year"].nunique()
bal = ann[ann["iso3"].isin(okc[okc == yrs].index)]
R["BalancedN"] = bal["iso3"].nunique()
for y, tag in [(1991, "Start"), (2022, "End")]:
    sh = bal[bal["year"] == y]["cfg"].value_counts(normalize=True)
    R[f"Met{tag}"] = round(100 * (sh.get("MO", 0) + sh.get("SJ", 0)))
    R[f"Over{tag}"] = round(100 * (sh.get("MO", 0) + sh.get("SO", 0)))
    R[f"ShareWithin{tag}"] = round(100 * sh.get("SW", 0))
    R[f"ShareTrap{tag}"] = round(100 * sh.get("SO", 0))
a2 = per[per["period"] == "P2"].set_index("iso3")["cfg"]
b2 = per[per["period"] == "P3"].set_index("iso3")["cfg"]
t2 = pd.concat([a2, b2], axis=1, keys=["a", "b"]).dropna()
R["TrapTotal"] = int((t2["a"] == "SO").sum())
R["TrapToOver"] = int(((t2["a"] == "SO") & (t2["b"] == "MO")).sum())
R["WithinTotal"] = int((t2["a"] == "SW").sum())
R["WithinStay"] = int(((t2["a"] == "SW") & (t2["b"] == "SW")).sum())
p3 = per[per["period"] == "P3"]
met3 = p3[(p3["met"] == True) & p3["cons"].notna()]  # noqa: E712
R["FrontierMin"] = round(float(met3["cons"].min()), 1)
R["MetMaxCons"] = round(float(met3["cons"].max()))
near = p3[(p3["minratio"] >= 0.9) & (p3["met"] == False) & p3["cons"].notna()]  # noqa: E712
R["NearN"] = len(near)
cs = ann[ann["cons"].notna()]
R["LeGain"] = round(cs[cs["year"] == 2022]["life_expectancy"].mean() - cs[cs["year"] == 1991]["life_expectancy"].mean(), 1)
R["ChinaFirstMet"] = int(ann[(ann["iso3"] == "CHN") & (ann["met"] == True)]["year"].min())  # noqa: E712
R["IndiaFirstOver"] = int(ann[(ann["iso3"] == "IND") & (ann["over"] == True)]["year"].min())  # noqa: E712

# --------------------------------------------------------------- compare
num = (ROOT / "paper" / "numbers.tex").read_text()
printed = {k: v for k, v in re.findall(r"\\newcommand\{\\n([A-Za-z]+)\}\{([^}]*)\}", num)}
alias = {"NCountries": "NCountries", "NCons": "NCons"}
fails = 0
print(f"{'quantity':24s} {'independent':>12s} {'paper':>10s}  result")
for k, v in R.items():
    p = printed.get(alias.get(k, k))
    if p is None:
        print(f"{k:24s} {v!s:>12s} {'(none)':>10s}  NOT IN PAPER")
        fails += 1
        continue
    p_clean = p.replace("{,}", "").replace(",", "")
    try:
        ok = abs(float(p_clean) - float(v)) < 1e-9
    except ValueError:
        ok = str(v) == p_clean
    fails += not ok
    print(f"{k:24s} {v!s:>12s} {p:>10s}  {'PASS' if ok else 'FAIL'}")
print(f"\n2011-2022 period configurations (independent): {counts.to_dict()}")
print(f"\n{len(R) - fails} of {len(R)} checks passed")
sys.exit(1 if fails else 0)
