"""Fetch the latest public data for the study site's "latest data" layer.

Run weekly by .github/workflows/live-data.yml. It downloads the newest values of
the four social indicators (World Bank WDI API) and consumption- and
production-based CO2 per person (Global Carbon Budget via Our World in Data),
and writes docs/data/live.json.

This layer is descriptive and provisional. It does not change the paper's
estimates, which are fixed to the data vintage in data/raw. For years after the
paper's last year (2022) it applies the paper's classification rule to the raw
latest observations: a country meets the social foundation only if all four
thresholds are observed and met, and overshoots if consumption-based CO2 per
person exceeds 1.61 t. No interpolation or gap filling is applied here.

Standard library only, so the workflow needs no installs.
"""

from __future__ import annotations

import csv
import io
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "data" / "live.json"
SITE = ROOT / "docs" / "climate-data.js"
FIRST = 2018
WDI = {
    "le": ("SP.DYN.LE00.IN", "Life expectancy at birth (years)"),
    "cm": ("SH.DYN.MORT", "Under-5 mortality (per 1,000 live births)"),
    "el": ("EG.ELC.ACCS.ZS", "Access to electricity (% of population)"),
    "un": ("SL.UEM.TOTL.ZS", "Unemployment, ILO modelled estimate (% of labour force)"),
    "pop": ("SP.POP.TOTL", "Population, total"),
}
OWID = "https://raw.githubusercontent.com/owid/co2-data/master/owid-co2-data.csv"
THRESH = {"le": (74, True), "cm": (25, False), "el": (95, True), "em": (94, True)}
BOUNDARY = 1.61
LAST_PAPER_YEAR = 2022
UA = {"User-Agent": "planetary-pathways-live-data/1.0 (+https://github.com/sahiljangra12/planetary-pathways)"}


def get(url: str, tries: int = 4) -> bytes:
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
                return r.read()
        except Exception as e:  # network hiccups: back off and retry
            if k == tries - 1:
                raise
            print(f"retry {url}: {e}", file=sys.stderr)
            time.sleep(5 * (k + 1))
    raise RuntimeError("unreachable")


def wdi(code: str, year_to: int) -> tuple[dict, str]:
    """{iso3: {year: value}} for all countries, plus the source's last-updated date."""
    out: dict[str, dict[int, float]] = {}
    page, pages, updated = 1, 1, ""
    while page <= pages:
        url = (f"https://api.worldbank.org/v2/country/all/indicator/{code}"
               f"?format=json&per_page=20000&date={FIRST}:{year_to}&page={page}")
        payload = json.loads(get(url))
        if not isinstance(payload, list) or len(payload) < 2:
            raise RuntimeError(f"unexpected response for {code}: {str(payload)[:200]}")
        meta, rows = payload
        pages, updated = int(meta.get("pages", 1)), meta.get("lastupdated", updated)
        for r in rows or []:
            iso, v = r.get("countryiso3code"), r.get("value")
            if iso and v is not None:
                out.setdefault(iso, {})[int(r["date"])] = float(v)
        page += 1
    return out, updated


def num(row: dict, key: str) -> float | None:
    v = row.get(key)
    return None if v in (None, "") else float(v)


def owid() -> dict:
    """{iso3: {year: (consumption, production)}} CO2 per person, years >= FIRST."""
    out: dict[str, dict[int, tuple]] = {}
    rows = csv.DictReader(io.StringIO(get(OWID).decode("utf-8")))
    for r in rows:
        iso, y = r["iso_code"], r["year"]
        if not iso or iso.startswith("OWID") or not y or int(y) < FIRST:
            continue
        out.setdefault(iso, {})[int(y)] = (num(r, "consumption_co2_per_capita"), num(r, "co2_per_capita"))
    return out


def sample() -> dict[str, str]:
    """The paper's 155 countries and names, read from the site data."""
    txt = SITE.read_text(encoding="utf-8")
    data = json.loads(txt[txt.index("{"):txt.rstrip().rstrip(";").rindex("}") + 1])
    return {iso: c["n"] for iso, c in data["C"].items()}


def classify(v: dict) -> dict:
    """Paper rule applied to one country-year of raw values."""
    soc = {"le": v.get("le"), "cm": v.get("cm"), "el": v.get("el"),
           "em": None if v.get("un") is None else 100 - v["un"]}
    met = [None if soc[k] is None else (soc[k] >= t if hi else soc[k] <= t) for k, (t, hi) in THRESH.items()]
    known_short = any(m is False for m in met)
    complete = all(m is not None for m in met)
    foundation = False if known_short else (True if complete else None)
    cons = v.get("cons")
    over = None if cons is None else cons > BOUNDARY
    if foundation is None or over is None:
        conf = None
    else:
        conf = ["Shortfall, within boundary", "Shortfall and overshoot",
                "Safe and just", "Foundation met, overshoot"][2 * foundation + over]
    return {"met": sum(bool(m) for m in met), "observed": sum(m is not None for m in met),
            "foundation": foundation, "overshoot": over, "configuration": conf}


def main() -> int:
    now = datetime.now(timezone.utc)
    names = sample()
    series, updated = {}, {}
    for key, (code, _) in WDI.items():
        series[key], updated[key] = wdi(code, now.year)
    co2 = owid()
    countries = {}
    for iso, name in names.items():
        years = sorted({y for s in series.values() for y in s.get(iso, {})} | set(co2.get(iso, {})))
        rows = {}
        for y in years:
            v = {k: series[k].get(iso, {}).get(y) for k in WDI}
            cons, prod = co2.get(iso, {}).get(y, (None, None))
            v.update(cons=cons, prod=prod)
            if all(x is None for x in v.values()):
                continue
            row = {k: (None if x is None else round(x, 3)) for k, x in v.items()}
            if y > LAST_PAPER_YEAR:
                row["provisional"] = classify(v)
            rows[y] = row
        latest = {k: max((y for y, r in rows.items() if r.get(k) is not None), default=None)
                  for k in [*WDI, "cons", "prod"]}
        countries[iso] = {"n": name, "years": rows, "latest": latest}
    payload = {
        "fetched": now.strftime("%Y-%m-%dT%H:%MZ"),
        "sources": {
            **{k: {"code": c, "label": lab, "source": "World Bank WDI API", "last_updated": updated[k]}
               for k, (c, lab) in WDI.items()},
            "cons": {"label": "Consumption-based CO2 per person (t)", "source": "Global Carbon Budget via OWID"},
            "prod": {"label": "Production-based CO2 per person (t)", "source": "Global Carbon Budget via OWID"},
        },
        "rule": "Provisional: paper thresholds applied to raw latest observations, no interpolation; "
                "not part of the paper's estimates.",
        "countries": countries,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    n_prov = sum(1 for c in countries.values() for r in c["years"].values()
                 if r.get("provisional", {}).get("configuration"))
    print(f"wrote {OUT.relative_to(ROOT)}: {len(countries)} countries, {n_prov} provisional classifications")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
