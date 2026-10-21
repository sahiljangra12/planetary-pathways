"""Study configuration: paths, sample rules, periods, boundaries and thresholds.

Every numeric threshold carries its source. Changing a value here changes every
result, table, figure and number in the paper, because nothing downstream is
hand-typed.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
RESULTS = ROOT / "results"
TABLES = RESULTS / "tables"
FIGURES = ROOT / "figures"
PAPER = ROOT / "paper"

OWID_CO2 = RAW / "owid-co2-data.csv"
OWID_ENERGY = RAW / "owid-energy-data.csv"
WDI_PANEL = RAW / "thesis_dataset.xlsx"
STATES = RAW / "sovereign_states.csv"

SEED = 20261020

# --------------------------------------------------------------------------
# Sample
# --------------------------------------------------------------------------
FIRST_YEAR = 1990
LAST_YEAR = 2022  # last year with full coverage of PPP GDP (Maddison 2023)
MIN_POPULATION = 1_000_000  # mean population over the study window; as Fanning et al. (2022)

# Periods (inclusive, non-overlapping). The thesis periods, with the final
# period ending at the last year of complete data.
PERIODS: dict[str, tuple[int, int]] = {
    "1990–2000": (1990, 2000),
    "2001–2010": (2001, 2010),
    "2011–2022": (2011, 2022),
}
MIN_YEARS_FOR_PERIOD_MEAN = 0.5  # share of years in a period that must be observed
MAX_INTERPOLATION_GAP = 3  # years; interior gaps only, never extrapolated
# Slow-moving coverage indicators are additionally interpolated across interior gaps
# of any length and filled from the nearest observed year of the same country at the
# edges, at most this many years away. This is
# needed because a country cannot be classified as meeting the social foundation
# while one of its indicators is unknown.
EDGE_FILL_VARS = ["secondary_enrollment", "electricity_access"]
EDGE_FILL_YEARS = 5


# --------------------------------------------------------------------------
# Biophysical boundary (climate)
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Boundary:
    key: str
    value: float
    unit: str
    label: str
    source: str


CO2_BOUNDARY = Boundary(
    key="co2_2c",
    value=1.61,
    unit="t CO2 per capita per year",
    label="2\\textdegree C, 66\\% (1000 Gt CO$_2$, 2011--2100)",
    source="oneill2018",
)
# Sensitivity: IPCC AR6 WG1 remaining budget from 2020 of 500 Gt CO2 for a 50%
# chance of 1.5 C, spread evenly over 2020-2100 across the 2020 world population.
WORLD_POP_2020 = 7.84e9
CO2_BOUNDARY_15 = Boundary(
    key="co2_15c",
    value=round(500e9 / 81 / WORLD_POP_2020, 2),
    unit="t CO2 per capita per year",
    label="1.5\\textdegree C, 50\\% (500 Gt CO$_2$ from 2020)",
    source="ipcc2021spm",
)


# --------------------------------------------------------------------------
# Social thresholds
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Threshold:
    var: str
    label: str
    value: float
    higher_is_better: bool
    unit: str
    source: str


EDUCATION = Threshold("secondary_enrollment", "Secondary enrolment", 95.0, True, "\\% gross", "fanning2022")
SOCIAL_THRESHOLDS: list[Threshold] = [
    Threshold("life_expectancy", "Life expectancy", 74.0, True, "years", "fanning2022"),
    Threshold("child_mortality", "Under-5 mortality", 25.0, False, "per 1,000 live births", "un2015sdg"),
    Threshold("electricity_access", "Access to electricity", 95.0, True, "\\% of population", "fanning2022"),
    Threshold("employment", "Employment", 94.0, True, "\\% of labour force", "fanning2022"),
]
# Secondary enrolment is reported as a robustness check rather than in the main
# set: the series covers about two thirds of country-years and has multi-year
# gaps for several large countries, so including it would make classification
# depend on data availability rather than outcomes.
SOCIAL_WITH_EDUCATION = [*SOCIAL_THRESHOLDS, EDUCATION]
# Robustness: drop employment, the indicator most affected by business cycles.
CORE_SOCIAL = ["life_expectancy", "child_mortality", "electricity_access"]

# --------------------------------------------------------------------------
# Typology
# --------------------------------------------------------------------------
QUADRANTS = {
    (False, False): "Shortfall, within boundary",
    (False, True): "Shortfall and overshoot",
    (True, True): "Foundation met, overshoot",
    (True, False): "Safe and just",
}
QUADRANT_ORDER = [
    "Shortfall, within boundary",
    "Shortfall and overshoot",
    "Foundation met, overshoot",
    "Safe and just",
]
# A country meets the social foundation when every indicator meets its threshold
# (lowest capped ratio >= 1), as in Fanning et al. (2022). Allowing each indicator to
# fall up to 5% short (cutoff 0.95) and a mean-based rule are robustness checks.
FOUNDATION_CUTOFF = 1.0
MIN_SOCIAL_INDICATORS = 3  # of 4 must be observed for the continuous attainment score

# Decoupling
DECOUPLING_MIN_YEARS = 8  # minimum observations for a trend
PARIS_YEAR = 2050  # target year for the "years to boundary" calculation

BOOTSTRAP_REPS = 2000
# Annual cross-sections with fewer scored countries than this are not estimated
# (in 1990 the ILO employment series has not started, so almost no country can be scored).
MIN_CROSS_SECTION = 90
GMM_MAX_COMPONENTS = 8
