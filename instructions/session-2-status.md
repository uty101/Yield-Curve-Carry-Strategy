# Session 2 status — stopped on a question (second time)

Date: 2026-09-22
Last commit: the commit that adds this update; `0f71cae` before it, on `main`.
Tests at the stop: **154 passed**, `ruff check` clean, `ruff format --check` clean.

## What was built

| step | commit | review | tests added |
|---|---|---|---|
| 2.1 Bond maths | `6d29fb8` | `review/2.1.md` | 11 (`tests/test_bondmath.py`) |
| 2.2 Nelson-Siegel | `f7b0fa5` | `review/2.2.md` | 7 (`tests/test_nelson_siegel.py`) |
| 2.3 Svensson | `9f97223` | `review/2.3.md` | 8 (`tests/test_svensson.py`) |

Plus `29394cf` (`Session 2: instructions`, the owner's message saved verbatim to
`instructions/session-2.md`) and `03aa2d7` (the three amendments written into
PLAN.md, and the status-file rule into PLAN.md and CLAUDE.md as invariant 15).

**Fixes after the owner answered issue #12 (2026-09-22):**

| commit | what |
|---|---|
| `580b8ce` | `ns_lambda_grid` `[0.2, 1.5, 0.05]` → `[0.05, 1.5, 0.05]` (#12 Q1, option C). Config default change, so its own commit under rule 14; PLAN.md 2.2 and 2.3 amended to say the grid may be changed there, why, and the stop condition |
| `e814dce` | #12 Q2 option D: `svensson.fit` requires `λ2 ≥ λ1 + step` in the Nelder-Mead polish as well as the grid, through `_project`. `beta_diff_max` now computed from the original, unswapped Bundesbank betas; `swapped` kept and used for the λ comparison only. Two new tests |
| `0f71cae` | 2.2 and 2.3 re-run on the new grid; `review/2.2.md` and `review/2.3.md` extended with a "Session 2 fixes" section |

Artefacts (after the re-run):

- `src/curvecarry/bondmath.py`, `src/curvecarry/nelson_siegel.py`, the λ form and
  fitter in `src/curvecarry/svensson.py`
- `data/processed/ns_params.parquet` (6,306), `ns_fitted.parquet` (70,776),
  `sv_params.parquet` (3,153)
- `data/checks/par_reprice.csv` (17,064), `fit_skipped.csv` (26, unchanged by the
  re-run), `fit_holdout.csv` (361,491), `svensson_vs_bundesbank.csv` (349)
- CLI `build --step ns` and `build --step svensson`

## What was not built

**Step 2.4 — Chart 1 and Chart 3.** Not started, either time.

## Why it stopped

**First stop (issue #12, answered).** Amendment 2 of `instructions/session-2.md`
set a 10% trigger on the share of DE months whose λ lies outside
`ns_lambda_grid`. The share was 69.9%, so 2.4 was not built and #12 was posted.
The owner answered: option C on the grid, option D on the collapsed λ pair with a
pre-registered `rcond` fallback, and `beta_diff_max` unswapped. All three are done.

**Second stop (issue #14, open).** The owner's answer on #12 carried a
pre-registered stop condition:

> If lambda still pins at 0.05 in more than 10% of months for any country, stop
> and post a decision issue rather than widening again.

It does, in **four of six countries**: CA 31.6%, GB 19.4%, US 18.6%, JP 13.4%
(DE 6.3%, FR 4.6%). So the session stopped again and 2.4 was not built.

**issue #14** — <https://github.com/uty101/Yield-Curve-Carry-Strategy/issues/14>

The evidence in #14: an offline refit of all 544 pinned months on
`[0.01, 1.5, 0.01]` (nothing committed) shows 66% to 89% of them would still pin
at 0.01, for a median gain of 0.27 to 1.00 bp. λ → 0 is a degeneracy of
Nelson-Siegel on a flat curve — the slope loading tends to the level loading and
the betas run away to cancel (JP 1981-06-30: β0 = 2.409, β1 = −2.314, β2 = −2.595)
— so no grid width removes it. Recommendation there is to keep
`[0.05, 1.5, 0.05]`, record a `lam_at_bound` flag, and clip Chart 3 with the
clipped months written to `data/checks/chart3_clipped.csv`. #14 also asks for the
Chart 3 clipping rule, because 60 pinned months have a |β| above 0.5 and would
otherwise set the y-axis at ±240%.

## What the fixes bought (full tables in the #13 comment)

- Svensson against the Bundesbank: median RMSE **0.10085 → 0.00639 bp**, p95
  2.606 → 0.499, max 4.311 → 1.452; λ outside the grid **69.9% → 25.8%**.
- Max |β2| **3.7e11 → 66.1**, max |β3| 3.7e11 → 13.5. No country exceeds 1e6, so
  the pre-registered `rcond` fallback did **not** trigger and option E was not
  applied; no `rcond` key was added to `config.toml`.
- `lam_gap` is never below `step` now (minimum 0.05 exactly); the share at
  exactly 0 is 0.0% in every country, against 0.3%–3.2%.
- Held-out median RMSE improved in 9 of the 10 free-λ country-model pairs
  (exception JP `sv`, 4.380 → 4.432). `ns_dl` unchanged to every digit — the
  control, its λ being fixed at 0.7.
- `fit_skipped.csv` byte-identical: the same 26 JP months.

## Issues

- **#12** — answered, all three answers implemented; closes once #14 is settled.
- **#13** — `Session 2 review`, with the fix report as a comment.
- **#14** — open, blocking 2.4.

## To resume

1. Read the owner's answer on #14, including the Chart 3 clipping rule.
2. If the grid changes again, that is a commit of its own (global rule 14), and
   2.2 and 2.3 are re-run before 2.4 starts.
3. Build 2.4 (`charts.py`, 8 pngs, `data/checks/chart1_dates.csv`), commit it,
   write `review/2.4.md`, and comment the result on #13.
