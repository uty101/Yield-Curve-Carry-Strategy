# Yield Curve Modelling and a G7 Carry Strategy

Nelson-Siegel, Svensson and PCA on six sovereign curves (US, GB, DE, JP, CA,
FR) from free central-bank data, and a duration-neutral, FX-hedged
cross-country carry strategy with a PCA slope overlay. Italy is not in the
universe: no national curve is reachable from a free source and the ECB
euro-area composites are never labelled FR or IT
([decisions/euro_curves.md](decisions/euro_curves.md)).

Build plan: [PLAN.md](PLAN.md). Session invariants: [CLAUDE.md](CLAUDE.md).
Everything between the two markers below is pasted from
[reports/results.md](reports/results.md) by `uv run curvecarry report`, and
`tests/test_readme.py` asserts the two are equal character for character. No
number here is typed by hand.

## Results

<!-- results:begin -->
### The headline

The headline result of this project is the **carry-only, hedged, book-wide duration-neutral book, net of costs**, from 1997-08-31 to 2026-08-31, on the universe available each month: the `carry_hedged` variant, `full` window, `r_net`. It was fixed before any result was seen. Everything else in the tables below is a logged variant and is reported whether it helps or not.

It returned **0.59% a year** at **2.23%** annualised volatility, a Sharpe of **0.265**, a worst drawdown of **-10.37%** (2019-12-31 to 2022-12-31) and **-4.41%** in 2022, over 348 months.

**The decomposition is the deliverable, not the Sharpe.** The per-year table below splits every year into the carry it earned, the yield-change PnL it paid for, and its costs; the four pieces sum to the reported return to 1e-10 in every month.

### The headline book, year by year

| year | months | net return | carry earned | yield-change PnL | cost |
|---|---:|---:|---:|---:|---:|
| 1997 | 5 | -1.55% | 1.71% | -3.18% | -0.08% |
| 1998 | 12 | -1.70% | 3.74% | -5.27% | -0.16% |
| 1999 | 12 | 2.61% | 3.41% | -0.61% | -0.18% |
| 2000 | 12 | -2.24% | 3.44% | -5.54% | -0.15% |
| 2001 | 12 | 2.73% | 2.95% | -0.01% | -0.21% |
| 2002 | 12 | 4.32% | 4.12% | 0.35% | -0.15% |
| 2003 | 12 | 3.10% | 3.01% | 0.30% | -0.20% |
| 2004 | 12 | -0.55% | 3.31% | -3.72% | -0.15% |
| 2005 | 12 | -1.19% | 2.32% | -3.34% | -0.17% |
| 2006 | 12 | 1.44% | 2.56% | -1.01% | -0.10% |
| 2007 | 12 | -2.17% | 2.37% | -4.40% | -0.14% |
| 2008 | 12 | -0.48% | 2.98% | -3.16% | -0.29% |
| 2009 | 12 | 3.36% | 3.58% | -0.10% | -0.13% |
| 2010 | 12 | 3.39% | 3.19% | 0.31% | -0.11% |
| 2011 | 12 | 5.41% | 2.55% | 3.04% | -0.18% |
| 2012 | 12 | 2.33% | 1.63% | 0.91% | -0.20% |
| 2013 | 12 | -0.60% | 1.84% | -2.28% | -0.16% |
| 2014 | 12 | 1.37% | 2.04% | -0.56% | -0.10% |
| 2015 | 12 | 2.23% | 1.90% | 0.47% | -0.14% |
| 2016 | 12 | 0.93% | 1.39% | -0.24% | -0.21% |
| 2017 | 12 | -2.04% | 1.46% | -3.31% | -0.19% |
| 2018 | 12 | 0.69% | 1.80% | -0.95% | -0.16% |
| 2019 | 12 | 2.86% | 1.14% | 1.98% | -0.26% |
| 2020 | 12 | -3.30% | 0.69% | -3.69% | -0.30% |
| 2021 | 12 | -3.11% | 1.59% | -4.51% | -0.19% |
| 2022 | 12 | -4.41% | 3.69% | -7.84% | -0.26% |
| 2023 | 12 | 2.89% | 3.71% | -0.65% | -0.17% |
| 2024 | 12 | -0.23% | 4.50% | -4.66% | -0.08% |
| 2025 | 12 | -0.99% | 2.08% | -2.93% | -0.13% |
| 2026 | 7 | 2.05% | 0.98% | 1.19% | -0.13% |
| **all** | **348** | **17.13%** | **75.68%** | **-53.43%** | **-5.13%** |

### Every logged variant, both windows

Windows: `full` from 1997-08-31, `six` from 2004-11-30 (the first month all six countries are present).

| variant | window | ann return | ann vol | Sharpe | max DD | DD peak | DD trough | turnover | 2022 | DD 2022 | n | gross return | gross Sharpe | DSR |
|---|---|---:|---:|---:|---:|---|---|---:|---:|---:|---:|---:|---:|---:|
| carry_hedged | full | 0.59% | 2.23% | 0.265 | -10.37% | 2019-12-31 | 2022-12-31 | 1.473 | -4.41% | -4.69% | 348 | 0.77% | 0.344 | 0.573 |
| carry_hedged | six | 0.48% | 2.01% | 0.239 | -10.37% | 2019-12-31 | 2022-12-31 | 1.483 | -4.41% | -4.69% | 261 | 0.66% | 0.328 | 0.517 |
| carry_hedged_cost0 | full | 0.77% | 2.23% | 0.344 | -9.69% | 2019-12-31 | 2022-12-31 | 1.473 | -4.15% | -4.45% | 348 | 0.77% | 0.344 | 0.727 |
| carry_hedged_cost0 | six | 0.66% | 2.00% | 0.328 | -9.69% | 2019-12-31 | 2022-12-31 | 1.483 | -4.15% | -4.45% | 261 | 0.66% | 0.328 | 0.673 |
| carry_hedged_cost2x | full | 0.41% | 2.24% | 0.185 | -11.04% | 2019-12-31 | 2022-12-31 | 1.473 | -4.67% | -4.93% | 348 | 0.77% | 0.344 | 0.406 |
| carry_hedged_cost2x | six | 0.30% | 2.01% | 0.150 | -11.04% | 2019-12-31 | 2022-12-31 | 1.483 | -4.67% | -4.93% | 261 | 0.66% | 0.328 | 0.356 |
| carry_hedged_country_scope | full | 0.19% | 1.60% | 0.120 | -8.94% | 2019-12-31 | 2022-10-31 | 1.963 | -2.18% | -3.06% | 348 | 0.43% | 0.268 | 0.278 |
| carry_hedged_country_scope | six | 0.36% | 1.55% | 0.230 | -8.94% | 2019-12-31 | 2022-10-31 | 1.967 | -2.18% | -3.06% | 261 | 0.59% | 0.383 | 0.500 |
| carry_hedged_ddstop | full | 0.54% | 2.21% | 0.243 | -10.41% | 2019-12-31 | 2025-11-30 | 1.476 | -4.41% | -4.69% | 348 | 0.71% | 0.324 | 0.529 |
| carry_hedged_ddstop | six | 0.41% | 1.96% | 0.207 | -10.41% | 2019-12-31 | 2025-11-30 | 1.488 | -4.41% | -4.69% | 261 | 0.59% | 0.299 | 0.459 |
| carry_hedged_interbank_3m | full | 0.64% | 2.27% | 0.284 | -9.55% | 2019-12-31 | 2022-12-31 | 1.489 | -4.68% | -4.91% | 348 | 0.82% | 0.363 | 0.612 |
| carry_hedged_interbank_3m | six | 0.50% | 2.10% | 0.236 | -9.55% | 2019-12-31 | 2022-12-31 | 1.503 | -4.68% | -4.91% | 261 | 0.68% | 0.322 | 0.510 |
| carry_hedged_no_gb30 | full | 0.63% | 2.24% | 0.280 | -10.35% | 2019-12-31 | 2022-12-31 | 1.486 | -4.49% | -4.75% | 348 | 0.80% | 0.360 | 0.604 |
| carry_hedged_no_gb30 | six | 0.53% | 2.01% | 0.262 | -10.35% | 2019-12-31 | 2022-12-31 | 1.500 | -4.49% | -4.75% | 261 | 0.71% | 0.352 | 0.558 |
| carry_hedged_ratesvol | full | 0.59% | 2.23% | 0.265 | -10.37% | 2019-12-31 | 2022-12-31 | 1.473 | -4.41% | -4.69% | 348 | 0.77% | 0.344 | 0.573 |
| carry_hedged_ratesvol | six | 0.48% | 2.01% | 0.239 | -10.37% | 2019-12-31 | 2022-12-31 | 1.483 | -4.41% | -4.69% | 261 | 0.66% | 0.328 | 0.517 |
| carry_hedged_ratesvol_rolling | full | 0.58% | 2.03% | 0.285 | -8.63% | 2019-12-31 | 2025-11-30 | 1.328 | -1.43% | -1.75% | 348 | 0.74% | 0.364 | 0.614 |
| carry_hedged_ratesvol_rolling | six | 0.46% | 1.70% | 0.273 | -8.63% | 2019-12-31 | 2025-11-30 | 1.290 | -1.43% | -1.75% | 261 | 0.62% | 0.365 | 0.578 |
| carry_hedged_voltarget | full | 0.94% | 4.04% | 0.232 | -18.79% | 2019-12-31 | 2022-12-31 | 2.812 | -7.53% | -8.04% | 348 | 1.27% | 0.316 | 0.504 |
| carry_hedged_voltarget | six | 0.92% | 3.84% | 0.239 | -18.79% | 2019-12-31 | 2022-12-31 | 2.917 | -7.53% | -8.04% | 261 | 1.27% | 0.331 | 0.517 |
| carry_unhedged | full | 2.80% | 11.07% | 0.253 | -32.25% | 1999-06-30 | 2001-08-31 | 1.473 | -6.53% | -20.95% | 348 | 2.98% | 0.269 | 0.551 |
| carry_unhedged | six | 3.03% | 10.29% | 0.294 | -31.08% | 2017-07-31 | 2022-08-31 | 1.483 | -6.53% | -20.95% | 261 | 3.20% | 0.311 | 0.618 |
| combined_hedged | full | 0.29% | 3.09% | 0.093 | -14.08% | 2019-12-31 | 2023-02-28 | 3.446 | -8.13% | -8.21% | 348 | 0.70% | 0.229 | 0.238 |
| combined_hedged | six | -0.06% | 3.06% | -0.021 | -14.08% | 2019-12-31 | 2023-02-28 | 3.593 | -8.13% | -8.21% | 261 | 0.37% | 0.121 | 0.120 |
| combined_hedged_ddstop | full | 0.27% | 2.93% | 0.092 | -12.53% | 2019-12-31 | 2024-07-31 | 3.039 | -5.90% | -6.10% | 348 | 0.63% | 0.218 | 0.236 |
| combined_hedged_ddstop | six | -0.09% | 2.83% | -0.032 | -12.53% | 2019-12-31 | 2024-07-31 | 3.050 | -5.90% | -6.10% | 261 | 0.28% | 0.098 | 0.108 |
| combined_hedged_ratesvol | full | 0.29% | 3.09% | 0.093 | -14.08% | 2019-12-31 | 2023-02-28 | 3.446 | -8.13% | -8.21% | 348 | 0.70% | 0.229 | 0.238 |
| combined_hedged_ratesvol | six | -0.06% | 3.06% | -0.021 | -14.08% | 2019-12-31 | 2023-02-28 | 3.593 | -8.13% | -8.21% | 261 | 0.37% | 0.121 | 0.120 |
| combined_hedged_ratesvol_rolling | full | 0.54% | 2.47% | 0.217 | -9.79% | 2019-12-31 | 2025-11-30 | 2.940 | -1.43% | -1.75% | 348 | 0.89% | 0.362 | 0.473 |
| combined_hedged_ratesvol_rolling | six | 0.27% | 2.19% | 0.122 | -9.79% | 2019-12-31 | 2025-11-30 | 2.919 | -1.43% | -1.75% | 261 | 0.62% | 0.285 | 0.311 |
| combined_hedged_voltarget | full | 0.15% | 4.94% | 0.029 | -25.59% | 2015-12-31 | 2025-11-30 | 5.988 | -13.75% | -13.69% | 348 | 0.86% | 0.176 | 0.142 |
| combined_hedged_voltarget | six | -0.35% | 4.91% | -0.071 | -25.59% | 2015-12-31 | 2025-11-30 | 6.360 | -13.75% | -13.69% | 261 | 0.42% | 0.085 | 0.078 |
| combined_unhedged | full | 4.60% | 15.45% | 0.298 | -40.85% | 2017-07-31 | 2026-05-31 | 3.445 | -11.12% | -31.83% | 348 | 5.02% | 0.325 | 0.653 |
| combined_unhedged | six | 4.85% | 14.97% | 0.324 | -40.85% | 2017-07-31 | 2026-05-31 | 3.593 | -11.12% | -31.83% | 261 | 5.28% | 0.353 | 0.677 |
| overlay_hedged | full | -0.31% | 1.86% | -0.169 | -13.70% | 2008-05-31 | 2026-05-31 | 2.075 | -3.75% | -4.41% | 348 | -0.07% | -0.035 | 0.009 |
| overlay_hedged | six | -0.56% | 2.04% | -0.272 | -13.70% | 2008-05-31 | 2026-05-31 | 2.215 | -3.75% | -4.41% | 261 | -0.29% | -0.143 | 0.003 |
| overlay_unhedged | full | 1.79% | 9.10% | 0.197 | -28.01% | 1998-10-31 | 2008-04-30 | 2.075 | -4.62% | -15.02% | 348 | 2.04% | 0.224 | 0.427 |
| overlay_unhedged | six | 1.82% | 9.73% | 0.187 | -24.91% | 2005-12-31 | 2008-04-30 | 2.215 | -4.62% | -15.02% | 261 | 2.08% | 0.214 | 0.418 |

**DSR is a probability, not a Sharpe**: the probability that the true Sharpe exceeds the multiple-testing threshold, here SR0 = 0.066 monthly over N = 19 trials. N is the row count of `reports/specifications.csv`, V[SR] = 0.001249 across the logged runs, monthly basis. A DSR below about 0.95 does not clear the usual bar.

Annualisation of every return and vol column: arithmetic, mean x 12.

### The deflated Sharpe

The headline's annualised Sharpe is 0.265. Its **deflated Sharpe is 0.573**, and that number is **a probability, not a Sharpe ratio**: it is the probability that the true Sharpe exceeds the multiple-testing threshold SR0 = 0.066 on a monthly basis, which is the Sharpe that 19 trials would be expected to produce by selection alone. N = 19 is the row count of `reports/specifications.csv` at the moment this report was written, and every run this project logged is in it.

**That does not clear the usual bar.** A deflated Sharpe is conventionally read as clearing it at about 0.95, and 0.573 is below that: after 19 trials, the evidence that this book's true Sharpe is above the selection threshold is weak.

### The one control that helped, and why it is not a result

`carry_hedged_ratesvol_rolling` is the only one of the four pre-registered risk controls that improves the headline book: Sharpe 0.285 against 0.265, volatility 2.03% against 2.23%, worst drawdown -8.63% against -10.37%. Four things have to be said next to that.

- **It is one of 19 logged runs.** Its own deflated Sharpe is 0.614 against a threshold of SR0 = 0.066 monthly over those 19 trials — higher than the headline's 0.573, and still far short of any sensible bar.
- **The improvement is largely one event.** 2022 goes from -4.41% to -1.43%, and the annual return *falls*, 0.59% to 0.58%. The gain is risk reduction concentrated in a single episode, not a better book.
- **Half of its specification was chosen after seeing a result.** The 120-month window was pre-registered in `config.toml`, in its own commit, before the run existed. The decision to try a *rolling* percentile at all was taken after seeing that the pre-registered *expanding* one never fires in the sample. That is one degree of freedom this project did not pay for in advance, and `N` does not price it.
- **It stays a logged variant and is never the headline**, which is the carry-only hedged book fixed before any result was seen.

### Every logged run

19 runs, each logged in `reports/specifications.csv` **before** it computed. A variant with no row did not happen.

| # | label | logged at (UTC) | config hash | what it overrides |
|---|---|---|---|---|
| 1 | `carry_hedged` | 2026-09-23T16:57:37 | `68b55883b46e` | (the base definition) |
| 2 | `carry_unhedged` | 2026-09-23T16:57:38 | `68b55883b46e` | (the base definition) |
| 3 | `overlay_hedged` | 2026-09-23T17:12:51 | `68b55883b46e` | (the base definition) |
| 4 | `overlay_unhedged` | 2026-09-23T17:12:52 | `68b55883b46e` | (the base definition) |
| 5 | `combined_hedged` | 2026-09-23T17:15:19 | `68b55883b46e` | (the base definition) |
| 6 | `combined_unhedged` | 2026-09-23T17:15:21 | `68b55883b46e` | (the base definition) |
| 7 | `carry_hedged_country_scope` | 2026-09-23T17:15:23 | `73a0ac4ee762` | {"overrides": {"weights": {"duration_neutral_scope": "country"}}} |
| 8 | `carry_hedged_interbank_3m` | 2026-09-23T17:15:27 | `056d2a51be66` | {"overrides": {"hedge": {"funding_rate": "interbank_3m"}}} |
| 9 | `carry_hedged_cost0` | 2026-09-23T17:15:34 | `726f4ec078e6` | {"overrides": {"costs": {"cost_bp_per_duration_year": 0.0}}} |
| 10 | `carry_hedged_cost2x` | 2026-09-23T17:15:37 | `f6d4b330dd2f` | {"overrides": {"costs": {"cost_bp_per_duration_year": 1.0}}} |
| 11 | `carry_hedged_no_gb30` | 2026-09-23T17:15:39 | `68b55883b46e` | {"exclude_buckets": [["GB", 30.0]]} |
| 12 | `carry_hedged_voltarget` | 2026-09-23T18:13:03 | `68b55883b46e` | {"base_variant": "carry_hedged", "risk_control": "vol_target"} |
| 13 | `carry_hedged_ddstop` | 2026-09-23T18:13:05 | `68b55883b46e` | {"base_variant": "carry_hedged", "risk_control": "dd_stop"} |
| 14 | `carry_hedged_ratesvol` | 2026-09-23T18:13:07 | `68b55883b46e` | {"base_variant": "carry_hedged", "risk_control": "rates_vol_filter"} |
| 15 | `combined_hedged_voltarget` | 2026-09-23T18:13:09 | `68b55883b46e` | {"base_variant": "combined_hedged", "risk_control": "vol_target"} |
| 16 | `combined_hedged_ddstop` | 2026-09-23T18:13:11 | `68b55883b46e` | {"base_variant": "combined_hedged", "risk_control": "dd_stop"} |
| 17 | `combined_hedged_ratesvol` | 2026-09-23T18:13:12 | `68b55883b46e` | {"base_variant": "combined_hedged", "risk_control": "rates_vol_filter"} |
| 18 | `carry_hedged_ratesvol_rolling` | 2026-09-24T14:44:54 | `a9a8ad073abb` | {"base_variant": "carry_hedged", "risk_control": "rates_vol_filter_rolling"} |
| 19 | `combined_hedged_ratesvol_rolling` | 2026-09-24T14:45:01 | `a9a8ad073abb` | {"base_variant": "combined_hedged", "risk_control": "rates_vol_filter_rolling"} |
<!-- results:end -->
