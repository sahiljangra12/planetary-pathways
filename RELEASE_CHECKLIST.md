# Release checklist

Prepared 2026-10-21 for *Social Shortfall, Climate Overshoot and the Falling Carbon Cost of Development*
(SAHIL, working paper). Every item marked [x] was checked in the runs recorded below; items marked [ ]
remain for the author.

## Replication runs (2,000 bootstrap replications each)

| Run | Environment | Input checksums | Tests | `check_paper.py` | `independent_check.py` | Compared with development run |
|---|---|---|---|---|---|---|
| Development | Python 3.13.16, packages = lock versions | OK | 25 passed | pass | 54 of 54 | – |
| Clean room A | fresh venv, Python 3.13.16, only `requirements-lock.txt` (numpy 2.5.3, pandas 3.0.5, linearmodels 7.1) | OK | 25 passed | pass | 54 of 54 | `numbers.tex`, all LaTeX tables, all CSV/JSON results and the panel byte-identical |
| Clean room B | fresh venv, Python 3.11.15, newest compatible packages (numpy 2.4.6, pandas 3.0.6, scipy 1.17.1, linearmodels 7.1) | OK | 25 passed | pass | 54 of 54 | `numbers.tex`, all LaTeX tables, JSON results and the panel byte-identical; 5 CSV files differ only in floating-point digits (max. absolute difference 3e-10) |

The clean-room runs used a copy of the package with no generated outputs. After they ran, only the
appendix reproducibility paragraph and `tools/typed_numbers_reviewed.tsv` were edited; no code or input
data changed. Rendered figures can differ by a few pixels across environments (font rasterisation);
the plotted data are identical.

## Data

- [x] Input files match `data/raw/SHA256SUMS` in every run.
- [x] WDI extract compared with the World Bank API (release of 2026-10-08, retrieved 2026-10-21) for the
  18 countries nearest a threshold, 410 values (`tools/wdi_spotcheck.py`, `verification/`): life
  expectancy and unemployment identical; electricity access differs in one value by 0.1; under-5
  mortality revised by up to 2.0 per 1,000. Substituting the API values changes 0 classifications.
- [ ] Author: full re-download of every WDI series for all countries and years (only the
  threshold-adjacent subset above was compared).

## Results

- [x] Headline numbers re-derived without the `ppath` package (`tools/independent_check.py`, 54 of 54
  agree): samples 155/114, 36 crossers (30 sustained), requirement 26 t to 8.5 t (95% CI 6.5–11.2),
  3.6%/yr, 5.3 times the boundary, health-only 2.6 t, without employment 2.9 t, with enrolment 9.0 t,
  83% persistence, decoupling 24 to 48 countries, scenarios, fixed effects.
- [x] Logistic fits: all 32 annual point estimates converged with a positive slope; failed
  bootstrap replications are counted by reason and reported (main: 14 of 64,000; pooled: 0).
  No warnings are suppressed.
- [x] Zero under-5 mortality counts as full attainment; a missing indicator never yields "foundation
  met" (tests).
- [x] Employment = 100 minus the ILO modelled unemployment rate, as in the SI of O'Neill et al. (2018)
  and Fanning et al. (2022); limitations disclosed (Sections 4 and 7).
- [x] Period labels 1990–2000, 2001–2010, 2011–2022 throughout; classifications, transitions, crossers
  and persistence use 1991–2022 (1990 lacks employment data); fixed-effects models use 1990–2022,
  as stated in Section 5.

## Manuscript

- [x] 204 number macros, all defined and used; no unknown or uncited references
  (`results/paper_check.txt`).
- [x] All 187 numbers typed directly in the text reviewed and categorised in
  `tools/typed_numbers_reviewed.tsv`; `check_paper.py` fails on any unreviewed or stale entry.
- [x] All 40 references checked: the 34 journal articles and chapters against Crossref (Fraley &
  Raftery 2002 against the authors' published PDF); the 6 books, reports and datasets (Raworth 2012,
  2017; UN 2015; UNDP 2020; WDI; OWID) by title, publisher and identifier. Figures quoted from
  Millward-Hopkins et al. (2020), Vogel & Hickel (2023) and Fanning et al. (2022, 2025) checked
  against their abstracts or SI.
- [x] PDF compiled after the final run: 53 pages, no LaTeX or BibTeX warnings, no overfull or
  underfull boxes, no unresolved references; newer than every table, figure, number file and source.
- [ ] Author: review the AI-use statement in `paper/sections/conclusion.tex` against the target
  journal's policy.

## Source data checksums (SHA-256)

- `data_sources.xlsx`: `afa6abd5a5e4fb556c5fa5eeb51e8bebb318be49454f2b343b6c8d7ea5212dd6`
- `owid-co2-codebook.csv`: `33b4f5e00efd58c7b83863f736beba1af4df946b43642b0400c3ec38648e0e8e`
- `owid-co2-data.csv`: `7f78e2b218ce4bb8c538bbec04fdc9a7982e8d40bff972e650df603899edd5f6`
- `owid-energy-codebook.csv`: `3cc9b7db0d921496e2988568ce3aee5ed41f50431dd234a0663b5f0a4b2e32bb`
- `owid-energy-data.csv`: `266f2e2baad7975351bc9bb4aa061d22b1da9fe4c47d51d2ac6071e01e171f76`
- `sovereign_states.csv`: `561726e2ead2724ebfa6c434470ad0bc6ae51bd1b462bd57813fb2bd02f17a60`
- `thesis_dataset.xlsx`: `18bdfc0ad986a649d160f725c6161cc3a0cd7832cb4a54eb0cb8982c9005ec81`

## Final outputs

- `paper/main.pdf`: `a797970fc509e7fac014d055bb0c1ce7ea976d6d71b2f8401a2e89da0b4f86cf` (53 pages)
- `paper/numbers.tex`: `a1896218c12ce00d386a75f50c4b2f7d87c33839d1d0a5112b7d61851fe88587` (204 macros)
