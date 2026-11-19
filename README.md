# Social shortfall, climate overshoot and the carbon cost of development

Replication package for *Social Shortfall, Climate Overshoot and the Falling Carbon Cost of
Development: Evidence from 114 Countries, 1990–2022* (SAHIL, working paper, 2026).

The study asks whether countries have met basic social needs within a fair per-capita share of the
climate boundary. It builds a panel of 155 countries for 1990–2022 (114 with consumption-based emissions) and combines four social thresholds
(life expectancy, under-5 mortality, access to electricity, employment) with consumption-based CO₂
emissions from the Global Carbon Budget 2025. It estimates how the CO₂ per person associated with
meeting those thresholds has changed over time. It also compares the pace of decoupling with the pace
needed to reach the boundary by 2050.

The classification of countries into four configurations of social attainment and climate
pressure is anchored to published thresholds and an equal-per-capita carbon budget, not to the
sample's own distribution.

## Paper

**Interactive site:** https://sahiljangra12.github.io/planetary-pathways/ (explore the evidence country by country and year by year; source in `docs/`).

The compiled paper is [`paper/main.pdf`](paper/main.pdf). Headline results:

- None of the 114 countries with consumption-based emissions met all four social thresholds while
  emitting within the 1.61 t CO₂ per person boundary in any year; all 36 countries that crossed the
  social foundation did so while overshooting.
- The CO₂ per person at which half of countries meet the foundation fell from about 26 t (1991) to
  8.5 t (2022; 95% CI 6.5–11.2), about 3.6% a year, still 5.3 times the boundary.
- Absolute decoupling spread from 24 to 48 countries, but only 2 of the 41 decouplers above the
  boundary are cutting fast enough to reach it by 2050.

These are descriptive cross-country associations, not causal estimates (see the paper's limitations).

## Reproduce everything

```bash
python -m venv .venv && source .venv/bin/activate      # Python 3.12+ for the pinned versions
pip install -r requirements-lock.txt                    # exact versions used for the paper
pip install -e . --no-deps
python -m ppath            # data -> results -> tables -> figures -> paper/numbers.tex (~15 min)
pytest                     # tests of the sample, measures and estimators
python tools/check_paper.py          # macros, citations, typed numbers
python tools/independent_check.py    # re-derives headline numbers without the ppath package
python tools/wdi_spotcheck.py        # compares the WDI extract with values from the live World Bank API
cd paper && latexmk -pdf main.tex
```

`python -m ppath --quick` uses fewer bootstrap replications for development.

**No result in the paper is typed by hand.** The pipeline writes every quoted result to
`paper/numbers.tex` as a LaTeX macro and every table to `results/tables/`. The paper only
references these, so it always matches the code. The only numbers typed in the text are
definitions, thresholds, years, labels, notation and values quoted from the literature; each one
is listed with its category in `tools/typed_numbers_reviewed.tsv`, and `tools/check_paper.py`
fails if a typed number appears that is not on that list.

`tools/independent_check.py` re-implements the sample, classification, crossers, carbon
requirement, decoupling, scenarios and fixed effects from the raw files with pandas/statsmodels
only, and compares each result with `paper/numbers.tex`.

## Layout

```
data/raw/            Inputs exactly as downloaded, with SHA256SUMS
data/processed/      The harmonised country-year panel (generated)
src/ppath/           Analysis package
  config.py          Sample rules, periods, every threshold and boundary with its source
  data.py            Loading, merging, gap handling, period means
  indicators.py      Social attainment, overshoot, the four configurations
  analysis.py        Carbon requirement, fixed effects, decoupling, transitions, checks
  pipeline.py        Runs the study and writes all outputs
  figures.py, tables.py, numbers.py
tests/               pytest suite
tools/check_paper.py Static checks on the paper source
tools/independent_check.py   Independent re-derivation of the headline numbers
tools/wdi_spotcheck.py       Comparison of the WDI extract with the live World Bank API
verification/       World Bank API values used by wdi_spotcheck.py
results/             CSV/JSON outputs and LaTeX tables (generated)
figures/             PDF + PNG figures (generated)
paper/               main.tex, references.bib, numbers.tex (generated), main.pdf
```

## Data sources

| Variable | Source |
|---|---|
| Life expectancy, under-5 mortality, electricity access, unemployment, secondary enrolment | World Bank WDI (extract in `thesis_dataset.xlsx`) |
| Production- and consumption-based CO₂ | Global Carbon Budget 2025, via [owid/co2-data](https://github.com/owid/co2-data) |
| GHG incl. land use | Jones et al. (2023, 2025 update), via owid/co2-data |
| GDP per person, 2011 int.$ PPP | Maddison Project Database 2023, via owid/co2-data |
| Sample | 193 UN member states + Palestine (`sovereign_states.csv`) |

## Licence

Code: MIT (see `LICENSE`). Data remain under the terms of their original providers: Our World in Data (CC BY 4.0) and the World Bank WDI (CC BY 4.0).

## Python versions

The pinned environment in `requirements-lock.txt` (used to produce the paper) needs Python 3.12
or newer, because NumPy 2.5 does. The package itself also runs on Python 3.11 with the newest
compatible library versions; `RELEASE_CHECKLIST.md` records how its results compare.

## Verification record

See `RELEASE_CHECKLIST.md` for the environments used, the test results, the comparison of
independent runs, the checksums of every input and of the final PDF, and the checks that remain
for the author. `paper/numbers.tex` contains exactly the numbers quoted in the paper;
`tools/check_paper.py` fails if any is missing or unused, if any citation is unknown or uncited,
or if a typed number has not been reviewed.
