# Results

Written at commit `b6c16ea`, config hash `a9a8ad073abb`.

Every number below is produced by `uv run curvecarry report`. The block between the two markers is pasted into `README.md` verbatim and a test asserts the two are equal.

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

## The decomposition

`data/checks/decomposition_shares.csv`, headline book. `cumulative` is the sum of the monthly piece over the window; `share` is its fraction of the summed `r_net`.

| variant | window | piece | cumulative | share |
|---|---|---|---|---|
| carry_hedged | full | carry_earned | 0.756831 | 4.417974 |
| carry_hedged | full | yield_change_pnl | -0.534258 | -3.118715 |
| carry_hedged | full | funding | 0.000000 | 0.000000 |
| carry_hedged | full | fx | 0.000000 | 0.000000 |
| carry_hedged | full | cost | -0.051265 | -0.299259 |
| carry_hedged | full | r_net | 0.171307 | 1.000000 |
| carry_hedged | six | carry_earned | 0.504336 | 4.838925 |
| carry_hedged | six | yield_change_pnl | -0.361392 | -3.467431 |
| carry_hedged | six | funding | 0.000000 | 0.000000 |
| carry_hedged | six | fx | 0.000000 | 0.000000 |
| carry_hedged | six | cost | -0.038719 | -0.371495 |
| carry_hedged | six | r_net | 0.104225 | 1.000000 |
| carry_hedged | 1990s | carry_earned | 0.088532 | -13.899972 |
| carry_hedged | 1990s | yield_change_pnl | -0.090652 | 14.232704 |
| carry_hedged | 1990s | funding | 0.000000 | -0.000000 |
| carry_hedged | 1990s | fx | 0.000000 | -0.000000 |
| carry_hedged | 1990s | cost | -0.004250 | 0.667269 |
| carry_hedged | 1990s | r_net | -0.006369 | 1.000000 |
| carry_hedged | 2000s | carry_earned | 0.306524 | 3.685108 |
| carry_hedged | 2000s | yield_change_pnl | -0.206270 | -2.479829 |
| carry_hedged | 2000s | funding | 0.000000 | 0.000000 |
| carry_hedged | 2000s | fx | 0.000000 | 0.000000 |
| carry_hedged | 2000s | cost | -0.017075 | -0.205278 |
| carry_hedged | 2000s | r_net | 0.083179 | 1.000000 |
| carry_hedged | 2010s | carry_earned | 0.189414 | 1.143345 |
| carry_hedged | 2010s | yield_change_pnl | -0.006446 | -0.038910 |
| carry_hedged | 2010s | funding | 0.000000 | 0.000000 |
| carry_hedged | 2010s | fx | 0.000000 | 0.000000 |
| carry_hedged | 2010s | cost | -0.017301 | -0.104435 |
| carry_hedged | 2010s | r_net | 0.165666 | 1.000000 |
| carry_hedged | 2020s | carry_earned | 0.172360 | -2.421847 |
| carry_hedged | 2020s | yield_change_pnl | -0.230890 | 3.244255 |
| carry_hedged | 2020s | funding | 0.000000 | -0.000000 |
| carry_hedged | 2020s | fx | 0.000000 | -0.000000 |
| carry_hedged | 2020s | cost | -0.012639 | 0.177592 |
| carry_hedged | 2020s | r_net | -0.071169 | 1.000000 |

## 2022, month by month

`data/checks/attribution_2022_carry_hedged.csv`, the `ALL` rows; the per-country and per-leg rows are in the file.

| date | country | leg | carry_earned | yield_change_pnl | hedge | cost | total |
|---|---|---|---|---|---|---|---|
| 2022-01-31 | ALL | both | 0.003153 | 0.000212 | 0.000000 | -0.000100 | 0.003265 |
| 2022-02-28 | ALL | both | 0.003385 | -0.020309 | 0.000000 | -0.000100 | -0.017024 |
| 2022-03-31 | ALL | both | 0.004117 | -0.005374 | 0.000000 | -0.000167 | -0.001424 |
| 2022-04-30 | ALL | both | 0.004079 | 0.007968 | 0.000000 | -0.000115 | 0.011932 |
| 2022-05-31 | ALL | both | 0.003581 | -0.006842 | 0.000000 | -0.000077 | -0.003338 |
| 2022-06-30 | ALL | both | 0.003318 | -0.003970 | 0.000000 | -0.000214 | -0.000866 |
| 2022-07-31 | ALL | both | 0.001380 | -0.010927 | 0.000000 | -0.000571 | -0.010119 |
| 2022-08-31 | ALL | both | 0.003259 | -0.019780 | 0.000000 | -0.000464 | -0.016986 |
| 2022-09-30 | ALL | both | 0.003651 | 0.009112 | 0.000000 | -0.000143 | 0.012620 |
| 2022-10-31 | ALL | both | 0.003276 | -0.014075 | 0.000000 | -0.000036 | -0.010835 |
| 2022-11-30 | ALL | both | 0.001868 | -0.001656 | 0.000000 | -0.000429 | -0.000216 |
| 2022-12-31 | ALL | both | 0.001800 | -0.012741 | 0.000000 | -0.000200 | -0.011142 |

## The three pre-registered risk controls

Each is its own logged run, applied to the base book named in `config.risk.risk_control_base_variants`, and each is reported whether it helps or not. None of them is the headline.

| base | variant | control | window | ann_return | ann_vol | sharpe | max_dd | ret_2022 | turnover | months_flat |
|---|---|---|---|---|---|---|---|---|---|---|
| carry_hedged | carry_hedged | (base) | full | 0.005907 | 0.022329 | 0.264548 | -0.103653 | -0.044131 | 1.473139 | 0 |
| carry_hedged | carry_hedged | (base) | six | 0.004792 | 0.020053 | 0.238965 | -0.103653 | -0.044131 | 1.483483 | 0 |
| carry_hedged | carry_hedged_voltarget | vol_target | full | 0.009352 | 0.040379 | 0.231615 | -0.187888 | -0.075256 | 2.812239 | 0 |
| carry_hedged | carry_hedged_voltarget | vol_target | six | 0.009183 | 0.038365 | 0.239352 | -0.187888 | -0.075256 | 2.916938 | 0 |
| carry_hedged | carry_hedged_ddstop | dd_stop | full | 0.005370 | 0.022058 | 0.243442 | -0.104106 | -0.044131 | 1.476287 | 5 |
| carry_hedged | carry_hedged_ddstop | dd_stop | six | 0.004076 | 0.019645 | 0.207464 | -0.104106 | -0.044131 | 1.487680 | 5 |
| carry_hedged | carry_hedged_ratesvol | rates_vol_filter | full | 0.005907 | 0.022329 | 0.264548 | -0.103653 | -0.044131 | 1.473139 | 0 |
| carry_hedged | carry_hedged_ratesvol | rates_vol_filter | six | 0.004792 | 0.020053 | 0.238965 | -0.103653 | -0.044131 | 1.483483 | 0 |
| carry_hedged | carry_hedged_ratesvol_rolling | rates_vol_filter_rolling | full | 0.005790 | 0.020328 | 0.284814 | -0.086347 | -0.014258 | 1.328314 | 31 |
| carry_hedged | carry_hedged_ratesvol_rolling | rates_vol_filter_rolling | six | 0.004635 | 0.016975 | 0.273065 | -0.086347 | -0.014258 | 1.290383 | 31 |
| combined_hedged | combined_hedged | (base) | full | 0.002886 | 0.030875 | 0.093485 | -0.140841 | -0.081304 | 3.445734 | 0 |
| combined_hedged | combined_hedged | (base) | six | -0.000635 | 0.030555 | -0.020795 | -0.140841 | -0.081304 | 3.593211 | 0 |
| combined_hedged | combined_hedged_voltarget | vol_target | full | 0.001453 | 0.049388 | 0.029427 | -0.255856 | -0.137451 | 5.987877 | 0 |
| combined_hedged | combined_hedged_voltarget | vol_target | six | -0.003479 | 0.049077 | -0.070886 | -0.255856 | -0.137451 | 6.359997 | 0 |
| combined_hedged | combined_hedged_ddstop | dd_stop | full | 0.002685 | 0.029258 | 0.091778 | -0.125306 | -0.058976 | 3.038500 | 45 |
| combined_hedged | combined_hedged_ddstop | dd_stop | six | -0.000904 | 0.028348 | -0.031875 | -0.125306 | -0.058976 | 3.050233 | 45 |
| combined_hedged | combined_hedged_ratesvol | rates_vol_filter | full | 0.002886 | 0.030875 | 0.093485 | -0.140841 | -0.081304 | 3.445734 | 0 |
| combined_hedged | combined_hedged_ratesvol | rates_vol_filter | six | -0.000635 | 0.030555 | -0.020795 | -0.140841 | -0.081304 | 3.593211 | 0 |
| combined_hedged | combined_hedged_ratesvol_rolling | rates_vol_filter_rolling | full | 0.005375 | 0.024744 | 0.217243 | -0.097857 | -0.014258 | 2.940250 | 31 |
| combined_hedged | combined_hedged_ratesvol_rolling | rates_vol_filter_rolling | six | 0.002683 | 0.021913 | 0.122453 | -0.097857 | -0.014258 | 2.919232 | 31 |

## PCA: explained variance

| scope | n months | PC1 | PC2 | PC3 | PC1-3 |
|---|---:|---:|---:|---:|---:|
| US | 775 | 90.9 | 7.2 | 1.1 | 99.2 |
| GB | 676 | 88.3 | 9.2 | 2.0 | 99.5 |
| DE | 348 | 81.6 | 14.6 | 2.6 | 98.8 |
| JP | 476 | 82.1 | 9.5 | 4.8 | 96.4 |
| CA | 487 | 87.5 | 9.6 | 1.5 | 98.6 |
| FR | 261 | 84.6 | 11.9 | 2.2 | 98.7 |
| pooled | 3023 | 89.1 | 8.6 | 1.6 | 99.3 |
| pooled_20y | 1566 | 85.1 | 11.7 | 2.2 | 99.0 |

## PCA: loading stability by decade

| country | decade | component | n_months | abs_cosine | abs_corr | explained_share_decade | us_borderline_excluded |
|---|---|---|---|---|---|---|---|
| CA | 1980s | 1 | 47 | 0.998767 | 0.970862 | 0.915954 | False |
| CA | 1980s | 2 | 47 | 0.968689 | 0.968045 | 0.057248 | False |
| CA | 1980s | 3 | 47 | 0.616551 | 0.620908 | 0.011845 | False |
| CA | 1990s | 1 | 120 | 0.996700 | 0.972332 | 0.878413 | False |
| CA | 1990s | 2 | 120 | 0.991783 | 0.993869 | 0.091845 | False |
| CA | 1990s | 3 | 120 | 0.989778 | 0.989721 | 0.015625 | False |
| CA | 2000s | 1 | 120 | 0.998401 | 0.984649 | 0.849454 | False |
| CA | 2000s | 2 | 120 | 0.997202 | 0.997269 | 0.130987 | False |
| CA | 2000s | 3 | 120 | 0.962760 | 0.963151 | 0.013052 | False |
| CA | 2010s | 1 | 120 | 0.957579 | 0.063942 | 0.894844 | False |
| CA | 2010s | 2 | 120 | 0.918266 | 0.946899 | 0.083816 | False |
| CA | 2010s | 3 | 120 | 0.910168 | 0.910526 | 0.013793 | False |
| CA | 2020s | 1 | 80 | 0.989815 | 0.663291 | 0.882105 | False |
| CA | 2020s | 2 | 80 | 0.988281 | 0.997975 | 0.093534 | False |
| CA | 2020s | 3 | 80 | 0.960005 | 0.959488 | 0.016763 | False |
| DE | 1990s | 1 | 28 | 0.998726 | 0.980944 | 0.827146 | False |
| DE | 1990s | 2 | 28 | 0.992780 | 0.992781 | 0.134553 | False |
| DE | 1990s | 3 | 28 | 0.933632 | 0.933024 | 0.026478 | False |
| DE | 2000s | 1 | 120 | 0.975009 | 0.488741 | 0.791042 | False |
| DE | 2000s | 2 | 120 | 0.966545 | 0.986958 | 0.166504 | False |
| DE | 2000s | 3 | 120 | 0.971936 | 0.972057 | 0.028184 | False |
| DE | 2010s | 1 | 120 | 0.967896 | 0.307044 | 0.835019 | False |
| DE | 2010s | 2 | 120 | 0.949988 | 0.976036 | 0.128580 | False |
| DE | 2010s | 3 | 120 | 0.974532 | 0.974375 | 0.027357 | False |
| DE | 2020s | 1 | 80 | 0.999739 | 0.989046 | 0.895291 | False |
| DE | 2020s | 2 | 80 | 0.997671 | 0.997713 | 0.078174 | False |
| DE | 2020s | 3 | 80 | 0.915684 | 0.915028 | 0.019702 | False |
| FR | 2000s | 1 | 61 | 0.966639 | 0.228689 | 0.797947 | False |
| FR | 2000s | 2 | 61 | 0.959909 | 0.990381 | 0.167667 | False |
| FR | 2000s | 3 | 61 | 0.975120 | 0.974900 | 0.021737 | False |
| FR | 2010s | 1 | 120 | 0.983104 | 0.849958 | 0.856070 | False |
| FR | 2010s | 2 | 120 | 0.965786 | 0.977888 | 0.104026 | False |
| FR | 2010s | 3 | 120 | 0.908510 | 0.907849 | 0.026575 | False |
| FR | 2020s | 1 | 80 | 0.999360 | 0.957532 | 0.905432 | False |
| FR | 2020s | 2 | 80 | 0.988305 | 0.988353 | 0.067369 | False |
| FR | 2020s | 3 | 80 | 0.947522 | 0.947028 | 0.020965 | False |
| GB | 1970s | 1 | 116 | 0.999706 | 0.973445 | 0.849833 | False |
| GB | 1970s | 2 | 116 | 0.998300 | 0.998319 | 0.120553 | False |
| GB | 1970s | 3 | 116 | 0.997832 | 0.998178 | 0.023924 | False |
| GB | 1980s | 1 | 120 | 0.998702 | 0.983296 | 0.933490 | False |
| GB | 1980s | 2 | 120 | 0.994363 | 0.995216 | 0.042897 | False |
| GB | 1980s | 3 | 120 | 0.992855 | 0.992859 | 0.018931 | False |
| GB | 1990s | 1 | 120 | 0.999067 | 0.907769 | 0.881349 | False |
| GB | 1990s | 2 | 120 | 0.994743 | 0.995103 | 0.109520 | False |
| GB | 1990s | 3 | 120 | 0.983967 | 0.984825 | 0.007924 | False |
| GB | 2000s | 1 | 120 | 0.999260 | 0.930840 | 0.868950 | False |
| GB | 2000s | 2 | 120 | 0.998923 | 0.998955 | 0.107894 | False |
| GB | 2000s | 3 | 120 | 0.975945 | 0.976290 | 0.021057 | False |
| GB | 2010s | 1 | 120 | 0.906149 | 0.866822 | 0.934559 | False |
| GB | 2010s | 2 | 120 | 0.873632 | 0.947386 | 0.053529 | False |
| GB | 2010s | 3 | 120 | 0.952866 | 0.962881 | 0.010559 | False |
| GB | 2020s | 1 | 80 | 0.994724 | 0.426920 | 0.954548 | False |
| GB | 2020s | 2 | 80 | 0.996491 | 0.999932 | 0.038700 | False |
| GB | 2020s | 3 | 80 | 0.994418 | 0.996268 | 0.005815 | False |
| JP | 1980s | 1 | 36 | 0.992907 | 0.803237 | 0.785517 | False |
| JP | 1980s | 2 | 36 | 0.428585 | 0.434450 | 0.109403 | False |
| JP | 1980s | 3 | 36 | 0.414002 | 0.409334 | 0.060286 | False |
| JP | 1990s | 1 | 120 | 0.998085 | 0.854598 | 0.862665 | False |
| JP | 1990s | 2 | 120 | 0.995524 | 0.996831 | 0.084082 | False |
| JP | 1990s | 3 | 120 | 0.956256 | 0.956038 | 0.026893 | False |
| JP | 2000s | 1 | 120 | 0.949445 | 0.523252 | 0.787016 | False |
| JP | 2000s | 2 | 120 | 0.920607 | 0.945469 | 0.144430 | False |
| JP | 2000s | 3 | 120 | 0.709411 | 0.713656 | 0.050873 | False |
| JP | 2010s | 1 | 120 | 0.910262 | 0.106921 | 0.797963 | False |
| JP | 2010s | 2 | 120 | 0.721646 | 0.754202 | 0.123953 | False |
| JP | 2010s | 3 | 120 | 0.792601 | 0.800613 | 0.057660 | False |
| JP | 2020s | 1 | 80 | 0.970384 | 0.336497 | 0.836401 | False |
| JP | 2020s | 2 | 80 | 0.898386 | 0.914895 | 0.113773 | False |
| JP | 2020s | 3 | 80 | 0.827095 | 0.826576 | 0.031755 | False |
| US | 1960s | 1 | 95 | 0.998387 | 0.928598 | 0.898642 | False |
| US | 1960s | 2 | 95 | 0.994131 | 0.995026 | 0.072540 | False |
| US | 1960s | 3 | 95 | 0.961889 | 0.962296 | 0.017049 | False |
| US | 1970s | 1 | 120 | 0.992750 | 0.994742 | 0.922476 | False |
| US | 1970s | 2 | 120 | 0.986517 | 0.992233 | 0.051255 | False |
| US | 1970s | 3 | 120 | 0.926842 | 0.927072 | 0.017551 | False |
| US | 1980s | 1 | 120 | 0.997721 | 0.977790 | 0.940188 | False |
| US | 1980s | 2 | 120 | 0.995832 | 0.997633 | 0.048434 | False |
| US | 1980s | 3 | 120 | 0.994950 | 0.995036 | 0.006071 | False |
| US | 1990s | 1 | 120 | 0.983621 | 0.074824 | 0.938424 | False |
| US | 1990s | 2 | 120 | 0.969377 | 0.982673 | 0.048419 | False |
| US | 1990s | 3 | 120 | 0.968967 | 0.969148 | 0.007010 | False |
| US | 2000s | 1 | 120 | 0.971774 | 0.401468 | 0.877139 | False |
| US | 2000s | 2 | 120 | 0.961446 | 0.985248 | 0.096659 | False |
| US | 2000s | 3 | 120 | 0.937816 | 0.938514 | 0.019063 | False |
| US | 2010s | 1 | 120 | 0.874336 | 0.880517 | 0.907201 | False |
| US | 2010s | 2 | 120 | 0.758562 | 0.845481 | 0.068443 | False |
| US | 2010s | 3 | 120 | 0.861572 | 0.869456 | 0.017830 | False |
| US | 2020s | 1 | 80 | 0.981056 | 0.119550 | 0.909789 | False |
| US | 2020s | 2 | 80 | 0.980809 | 0.998048 | 0.070355 | False |
| US | 2020s | 3 | 80 | 0.945077 | 0.945459 | 0.017300 | False |
| US | 1960s | 1 | 95 | 0.998603 | 0.936104 | 0.898642 | True |
| US | 1960s | 2 | 95 | 0.994119 | 0.994896 | 0.072540 | True |
| US | 1960s | 3 | 95 | 0.960725 | 0.961098 | 0.017049 | True |
| US | 1970s | 1 | 117 | 0.990770 | 0.992737 | 0.910854 | True |
| US | 1970s | 2 | 117 | 0.984403 | 0.991910 | 0.058687 | True |
| US | 1970s | 3 | 117 | 0.929461 | 0.929684 | 0.020395 | True |
| US | 1980s | 1 | 111 | 0.997020 | 0.973336 | 0.938597 | True |
| US | 1980s | 2 | 111 | 0.995659 | 0.998197 | 0.050086 | True |
| US | 1980s | 3 | 111 | 0.996526 | 0.996648 | 0.006310 | True |
| US | 1990s | 1 | 120 | 0.984255 | 0.056710 | 0.938424 | True |
| US | 1990s | 2 | 120 | 0.970232 | 0.983086 | 0.048419 | True |
| US | 1990s | 3 | 120 | 0.968909 | 0.969069 | 0.007010 | True |
| US | 2000s | 1 | 120 | 0.972561 | 0.387477 | 0.877139 | True |
| US | 2000s | 2 | 120 | 0.962300 | 0.985507 | 0.096659 | True |
| US | 2000s | 3 | 120 | 0.936061 | 0.936709 | 0.019063 | True |
| US | 2010s | 1 | 120 | 0.875630 | 0.877858 | 0.907201 | True |
| US | 2010s | 2 | 120 | 0.760406 | 0.846237 | 0.068443 | True |
| US | 2010s | 3 | 120 | 0.863494 | 0.871305 | 0.017830 | True |
| US | 2020s | 1 | 80 | 0.981726 | 0.103018 | 0.909789 | True |
| US | 2020s | 2 | 80 | 0.981266 | 0.997993 | 0.070355 | True |
| US | 2020s | 3 | 80 | 0.942597 | 0.942934 | 0.017300 | True |

## What carry does not tell you

Nine things this book's numbers do not say, each with the figure from this
repo that bounds it.

**1. The return is carry net of a losing yield bet, and the yield bet is the
larger number.** Over the full window the headline book earned
75.68% of carry, gave back 53.43% to yield changes
and 5.13% to costs, and kept 17.13%. A reader who sees
only the net figure will under-estimate both the gross carry and the size of
the directional risk that offset it. The losing decades are
1990s, 2020s: decades where the yield move was larger than the carry,
not decades where the carry stopped.

**2. 2022 is what that looks like in one year.** The book lost
4.41% over 12 months, of which carry earned
3.69% and yield changes cost 7.84%. Carry was
positive in 12 of those months, including the worst
one (2022-02-28, a loss of 1.70%). Duration
neutrality did not protect the book, because the long leg sat where the curve
moved most;
a book neutral in duration is not neutral in *where on the curve* the duration
sits.

**3. The slope overlay is flat gross and loses its costs.** Over
29 years and 181 in-sample trades it made
-190 bp gross, paid 722 bp in costs and returned
-912 bp. The 5 worst trades alone cost
684 bp: GB 2008-09 flattener -176 bp; FR 2022-08 steepener -150 bp; CA 2008-09 flattener -134 bp; CA 2021-01 flattener -114 bp; JP 1998-11 flattener -110 bp. They share a shape — a
mean-reversion slope signal is short the trend, so it fades a curve move that
keeps going, and it does that hardest in the months the move is largest. An
overlay that is flat before costs is not a diversifier; it is a fee.

**4. Duration neutrality is not currency neutrality.** The book is neutral in
duration and not in notional, and notional is what carries currency risk. The
unhedged book's monthly return regresses on its own currency-weighted FX term
with an R-squared of 95.3% and a beta of 0.96: almost all of
what the unhedged run earned or lost is the exchange rate, not the curve. Its
mean absolute net foreign notional is 1.86 units of capital
and its maximum 3.39. Every unhedged number in this report
is a currency bet with a carry book attached.

**5. The funding rate is a policy rate used as a three-month anchor.** The
financing leg of every excess return is the central bank's policy rate, not a
rate anyone can borrow at for three months. Where the policy series has gaps
they are filled from the OECD immediate rate: 116 months in
total, all in JP (JP 1999-03-31 to 2000-07-31 (17 months); JP 2001-04-30 to 2006-02-28 (59 months); JP 2013-05-31 to 2016-08-31 (40 months)). The logged
robustness run on the OECD three-month interbank rate returns
0.64% a year at a Sharpe of 0.284 against
the headline's 0.59% and 0.265 — close
enough that the choice does not carry the result, but the interbank series
prices bank credit, and in 2008 that credit spread would read here as carry.

**6. The cross-currency basis is not measured.** The hedged return is
the local excess return by covered interest parity, and covered interest
parity has not held since 2008. No free basis series was found
(`decisions/basis.md` records the probe), so the error is not estimated; from
the brief it runs 20 to 50 bp in stress periods for the major pairs,
one-directional rather than noise, and wider at quarter and year ends. Every
hedged number here is a CIP-implied hedged number.

**7. The Nelson-Siegel lambda is unidentified on flat curves.** As lambda goes
to zero the slope loading becomes the level loading and the design matrix goes
collinear, so the fit runs to the edge of the grid and stops there. On the
free-lambda fits that happens in 34.6% of
CA months (31.6% of them at the lower
bound) and as little as 4.6% of FR
months. Where lambda is on a bound the reported betas are coefficients on a
nearly singular basis and should not be read as level, slope and curvature.
Nothing in the strategy reads them — the signal is built from zero yields —
but the fitted-curve charts inherit the problem.

**8. The US curve is built from on-the-run yields, which are rich.** Against
the Fed's own GSW fitted curve the CMT par yield at 10 years
differs by -7.9 bp on average and -7.2 bp at the median over
661 months — the CMT yield is the lower, which is the on-the-run
bond being the dearer. That is the on-the-run premium, and it is a level
shift on one country's curve that no other country in this book carries. It
enters the carry signal as a small standing tilt away from the US, not as
noise.

**9. Buckets enter and leave mid-sample, and the universe is not the same book
throughout.** Inside the strategy window 131 bucket-months
enter and 169 leave, across CA, DE, FR, GB, JP, US. A
cross-sectional rank is taken over whatever is available that month, so the
same signal value means a different thing in a month with four countries and a
month with six. The two sample windows exist for exactly this reason and every
result is reported on both.

**And one measurement note.** The duration-convexity approximation of the
monthly return, which the brief asks for, is diagnostic here and never inside
any identity. Its mean error runs -0.69 bp to -0.41 bp by
tenor, with a worst single bucket-month of 42 bp at
20 years. Every return in this report is a full
repricing.

**And the one risk control that helped is not a result.** Of the four
pre-registered controls, only the rolling rates-vol filter improves the
headline: Sharpe 0.285 against 0.265, worst
drawdown -8.63% against -10.37%. Four things belong beside
that. It is **one of 19 logged runs**, and its own deflated Sharpe
is 0.614 against the headline's 0.573 — higher, and
still far short of any sensible bar. **The improvement is largely one event**:
2022 goes from -4.41% to -1.43% while the annual
return *falls*, 0.59% to 0.58%, so the gain is
risk reduction concentrated in a single episode rather than a better book.
**Half of its specification was chosen after a result was seen**: the
120-month window was pre-registered in its own commit before the run existed,
but the decision to try a rolling percentile at all came after the
pre-registered expanding one turned out never to fire (its Sharpe is
0.265, the headline's to three places, because it never
trades differently). `N` does not price that degree of freedom. It **stays a
logged variant and is never the headline**.

**What the robustness rows changed.** Country-scope neutrality instead of
book-wide takes the headline to 0.19% a year at
0.120; excluding the GB 30-year, 0.63% at
0.280; zero costs, 0.77% at 0.344;
double costs, 0.41% at 0.185. Costs move the
result more than any modelling choice in the list, and the country-scope run
moves it most of all — which is the honest reading that book-wide neutrality
is doing real work and is a choice, not a detail.

## Charts

- `reports/figures/chart1_fit_ca.png`
- `reports/figures/chart1_fit_de.png`
- `reports/figures/chart1_fit_fr.png`
- `reports/figures/chart1_fit_gb.png`
- `reports/figures/chart1_fit_jp.png`
- `reports/figures/chart1_fit_us.png`
- `reports/figures/chart1_rmse.png`
- `reports/figures/chart2_loadings.png`
- `reports/figures/chart3_betas.png`
- `reports/figures/chart4_ca.png`
- `reports/figures/chart4_carry_per_duration.png`
- `reports/figures/chart4_de.png`
- `reports/figures/chart4_fr.png`
- `reports/figures/chart4_gb.png`
- `reports/figures/chart4_jp.png`
- `reports/figures/chart4_us.png`
- `reports/figures/chart5_decomposition_carry_hedged.png`
- `reports/figures/chart5_decomposition_combined_hedged.png`
