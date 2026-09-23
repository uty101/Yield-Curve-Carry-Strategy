# Why the Nelson-Siegel lambda sits on the grid bound, and why that is left alone

Decided 2026-09-23, issue #14 (option K), after issue #12 widened
`config.nelson_siegel.ns_lambda_grid` from `[0.2, 1.5, 0.05]` to
`[0.05, 1.5, 0.05]`. **The grid is not widened again.** Any further change
needs a new `decision` issue.

## What happens

`ns_params.parquet` carries `lam_at_bound`: true where the fitted `lam` is
within 1e-12 of either end of the grid. On `ns_free` rows it is true in

| country | either bound | at 0.05 | at 1.50 | months |
|---|---|---|---|---|
| CA | 34.6% | 31.6% | 3.1% | 488 |
| US | 22.4% | 18.6% | 3.9% | 776 |
| GB | 21.8% | 19.4% | 2.4% | 680 |
| JP | 17.7% | 13.4% | 4.3% | 598 |
| DE | 6.9% | 6.3% | 0.6% | 349 |
| FR | 4.6% | 4.6% | 0.0% | 262 |

On `ns_dl` rows it is false in every month, by construction: that model fixes
`lam` at `config.nelson_siegel.ns_lambda_fixed` (0.7), an interior point. That
is the control which says the flag is reading `lam` and nothing else.

A bound hit means the RMSE was still falling when the search ran out of grid.
The reported `lam` is then a constraint, not an estimate, and the betas that
go with it are coefficients on a loading matrix that is nearly singular.

## Why it happens: lambda -> 0 is a degeneracy of the model

The three Nelson-Siegel loadings at maturity `tau` are

    level      1
    slope      (1 - e^{-lam tau}) / (lam tau)
    curvature  (1 - e^{-lam tau}) / (lam tau) - e^{-lam tau}

As `lam -> 0` the slope loading tends to 1 — which **is** the level loading —
and the curvature loading tends to 0. The design matrix becomes collinear:

| loading at tau = 1, 10, 30 | lam = 0.30 | lam = 0.05 | lam = 0.01 |
|---|---|---|---|
| slope | 0.864, 0.317, 0.111 | 0.975, 0.787, 0.518 | 0.995, 0.952, 0.864 |
| curvature | 0.123, 0.267, 0.111 | 0.024, 0.180, 0.295 | 0.005, 0.047, 0.123 |

so the betas run away and cancel. Median |beta| on bound-hit months against
the rest: beta0 0.054 vs 0.043, beta1 **0.077 vs 0.022**, beta2
**0.145 vs 0.029**. The extreme:

| country | date | lam | beta0 | beta1 | beta2 | RMSE bp |
|---|---|---|---|---|---|---|
| JP | 1981-06-30 | 0.05 | 2.409 | -2.314 | -2.595 | 26.94 |
| JP | 1981-05-31 | 0.05 | 2.158 | -2.063 | -2.316 | 27.53 |
| JP | 1980-11-30 | 0.05 | 1.986 | -1.877 | -2.202 | 15.11 |

A beta0 of 2.409 is a 241% level yield cancelled by a -231% slope. The fitted
*curve* is fine — that JP month's RMSE is 26.9 bp, poor but not absurd — and
the three numbers are individually meaningless.

The months that hit the bound are the flat and humpless ones, where there is
no slope decay to estimate. They are also the hard ones: median `ns_free`
RMSE 6.7-9.5 bp on bound-hit months against 2.4-4.9 bp on the rest.

## Why widening again does not help

All 544 months that were pinned at 0.05 were refit offline on
`[0.01, 1.5, 0.01]` — a 25x wider range at a fifth of the step. Nothing was
committed and `config.toml` was untouched.

| country | pinned | median RMSE at lo = 0.05 | at lo = 0.01 | median gain | max gain | **still at the new bound** |
|---|---|---|---|---|---|---|
| CA | 154 | 6.68 bp | 5.32 bp | 1.00 bp | 10.84 bp | **76.6%** |
| GB | 132 | 7.35 | 6.52 | 0.71 | 3.56 | **76.5%** |
| US | 144 | 9.48 | 8.23 | 0.50 | 6.27 | **66.0%** |
| JP | 80 | 8.48 | 8.36 | 0.27 | 1.55 | **88.8%** |
| DE | 22 | 5.02 | 3.99 | 0.60 | 3.23 | 40.9% |
| FR | 12 | 2.87 | 2.22 | 0.28 | 1.29 | 50.0% |

Two thirds to nine tenths of them still pin. Widening moves the bound; it does
not find an interior optimum, because for these months there is none. It also
costs: 30 -> 150 NS grid points and 435 -> 11,175 Svensson pairs, which takes
the Svensson panel from about 90 seconds to about 40 minutes.

## What the bound is for

**It is the regulariser, not a search boundary.** It is the only thing
stopping the betas from running to the collinear limit, and it does the same
job as the `lam2 >= lam1 + step` separation that issue #12 (option D) put into
the Svensson polish — which took the largest |beta2| from 3.7e11 to 66.1.
Loosening it further would loosen the brake.

The widening that #12 authorised was still right, and was kept: every measured
quantity improved. Svensson against the Bundesbank went from a median 0.10085
bp to 0.00639 bp, the share of Bundesbank lambdas outside the grid fell from
69.9% to 25.8%, and held-out RMSE improved in 9 of the 10 free-lambda
country-model pairs. The residual pinning is a property of Nelson-Siegel on a
flat curve, not of the grid.

## What is done about it instead

- **`lam_at_bound` is recorded** on every `ns_params.parquet` row and is tested
  (`test_lam_at_bound_flags_either_end_only`).
- **Chart 3 changes rather than clips** (step 2.4). Its primary panel plots the
  **NS-DL** betas, at fixed lambda: with a free lambda, beta1 and beta2 are
  coefficients on loadings whose shape changes every month, so the same numeric
  value in two months is not the same quantity and the series is not comparable
  across time or countries. Fixing lambda is what makes it comparable, and is
  why Diebold-Li fix it. A second panel plots the NS-free betas with the
  `lam_at_bound` months **left as gaps** — not clipped, not interpolated, not
  forward-filled — and the gap count per country is in the caption.
  `data/checks/chart3_excluded.csv` lists every excluded country-month with its
  lambda and its betas. **No percentile clipping anywhere.**
- **Chart 1 and the RMSE comparison are unchanged**, NS-free included in both:
  what they measure is fit quality, which is where a free lambda earns its
  place.

`sv_params.parquet` has two lambdas and carries no such flag — issue #14
specified `ns_params.parquet`. Svensson's `lam1` sits at the lower bound in
CA 60.9%, US 60.4%, GB 36.2%, JP 34.8%, FR 25.6% and DE 8.3% of months.
Nothing in the plan plots or reads Svensson betas (Chart 3 is Nelson-Siegel,
Phase 3 runs PCA on yields), so it changes no reported number today. If a
later step reads them, it needs the same flag first.
