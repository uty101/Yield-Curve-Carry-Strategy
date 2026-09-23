# Session 2 status — fix round done; awaiting the owner's approval

Date: 2026-09-23
Last commit: the commit that adds this update; `03335fc` before it, on `main`.
Tests at the finish: **162 passed**, `ruff check` clean, `ruff format --check` clean.

**Phase 2 is complete.** All four steps built, each with its own commit and its
own review file. Both decision issues (#12, #14) were raised, answered and
implemented; #14 is closed. `Session 2 review` is issue #13 and carries four
comments: the original review, the #12 fix report, the completion report, and
the fix-round report.

## What was built

| step | commit | review | tests |
|---|---|---|---|
| 2.1 Bond maths | `6d29fb8` | `review/2.1.md` | 11 (`tests/test_bondmath.py`) |
| 2.2 Nelson-Siegel | `f7b0fa5` | `review/2.2.md` | 9 (`tests/test_nelson_siegel.py`) |
| 2.3 Svensson | `9f97223` | `review/2.3.md` | 10 (`tests/test_svensson.py`) |
| 2.4 Chart 1 and Chart 3 | `ae51982` | `review/2.4.md` | 5 (`tests/test_charts.py`) |

Supporting commits:

| commit | what |
|---|---|
| `29394cf` | `Session 2: instructions` — the owner's message saved verbatim to `instructions/session-2.md` |
| `03aa2d7` | the three session-2 amendments into PLAN.md; the status-file rule into PLAN.md and CLAUDE.md as invariant 15 |
| `580b8ce` | #12 Q1 option C: `ns_lambda_grid` `[0.2, 1.5, 0.05]` → `[0.05, 1.5, 0.05]`. Config default change, so its own commit under rule 14 |
| `e814dce` | #12 Q2 option D: `svensson.fit` requires `λ2 ≥ λ1 + step` in the Nelder-Mead polish as well as the grid, via `_project`. `beta_diff_max` computed unswapped |
| `0f71cae` | 2.2 and 2.3 re-run on the new grid |
| `d46397e` | #14 option K: `lam_at_bound` on `ns_params.parquet` + test; `decisions/lambda_bound.md` |
| `07cdd96` | **fix round 1**: Chart 3 gaps on `ns_degenerate` (= `lam_at_bound` **or** max \|β\| > 0.5), not `lam_at_bound` alone; `chart3_excluded.csv` gains `reason` |
| `03335fc` | **fix round 2**: Chart 1 draws an empty panel for a decade with no fitted month; `chart1_dates.csv` holds only real dates |

## Artefacts

- `src/curvecarry/bondmath.py`, `nelson_siegel.py`, `charts.py`; the λ form and
  fitter added to `svensson.py`
- `data/processed/ns_params.parquet` (6,306 rows, with `lam_at_bound` and `ns_degenerate`),
  `ns_fitted.parquet` (70,776), `sv_params.parquet` (3,153)
- `data/checks/par_reprice.csv` (17,064), `fit_skipped.csv` (26),
  `fit_holdout.csv` (361,491), `svensson_vs_bundesbank.csv` (349),
  `chart1_dates.csv` (23), `chart3_excluded.csv` (285, with `reason`)
- `reports/figures/` — 8 pngs, committed
- `decisions/lambda_bound.md`
- CLI `build --step ns`, `build --step svensson`, `report --charts 1,3`

## What was not built

Nothing. Every step of Phase 2 met its "Done when".

## How it ended

Finished, then one fix round on the owner's review (below). Two stops happened along the way and both were resolved:

1. **Amendment 2's 10% trigger** fired at 69.9% (the Bundesbank's λ outside the
   grid), so 2.4 was held and #12 was posted. The owner answered: option C on the
   grid, option D on the collapsed λ pair with a pre-registered `rcond` fallback,
   and `beta_diff_max` unswapped. All three implemented.
2. **The pre-registered stop condition** on that answer fired: NS-free λ still
   pinned at 0.05 in four of six countries, so 2.4 was held again and #14 was
   posted. The owner answered option K: keep the grid, record `lam_at_bound`,
   and change Chart 3 rather than clip it. Implemented, #14 closed, 2.4 built.

## What the two answers bought

- Svensson against the Bundesbank: median RMSE **0.10085 → 0.00639 bp**, p95
  2.606 → 0.499, max 4.311 → 1.452; λ outside the grid **69.9% → 25.8%**.
- Max |β2| **3.7e11 → 66.1**; `lam_gap` never below `step` (minimum 0.05
  exactly), share at exactly 0 now **0.0% in every country**. The `rcond`
  fallback did **not** trigger and was not applied; no `rcond` key was added.
- Held-out median RMSE improved in 9 of the 10 free-λ country-model pairs.
- `fit_skipped.csv` byte-identical throughout: the same 26 JP months.

## The fix round (2026-09-23)

The owner asked for two fixes before approval; both are in and reported on #13.

**1. The Chart 3 gap criterion keyed on the wrong thing.** `ns_degenerate` =
`lam_at_bound` **or** `max(|β0|, |β1|, |β2|) > 0.5` (50 percentage points of
yield) is now a column on `ns_params.parquet` for every model, beside
`lam_at_bound`, which is kept because `decisions/lambda_bound.md` refers to it.
Chart 3's lower panel gaps on it and `chart3_excluded.csv` gained a `reason`
column (`bound`, `beta`, `both`). `ns_free` degenerate months: CA 169 (34.6%),
US 174 (22.4%), GB 150 (22.1%), JP 106 (17.7%), DE 24 (6.9%), FR 12 (4.6%).
The beta criterion adds 2 GB months the bound missed and agrees on 60 more.
**`ns_dl` is 0 in every country** — largest max |β| 0.3365 (GB) — so the
fixed-λ panel has no degenerate month. Largest max |β| still kept: GB 0.4452,
JP 0.4206, US 0.3991, CA 0.2466, DE 0.1977, FR 0.1574.

**2. Chart 1 no longer falls back to a country's earliest month.** A decade
with no fitted month gets an empty panel captioned "no fitted months in this
decade", and `chart1_dates` emits no row for it: `chart1_dates.csv` is 23 rows,
not 24, FR 1990 gone, every row a real 31 December. Where a decade has months
but no fitted December, its last fitted month is still used. The legend moved
to the first panel that has data (FR's panel 0 is now the empty one), and a
country with no fitted month in any configured decade gets no figure at all.

## Carried forward — neither blocking, both on #13

- **Svensson `lam1` sits at the lower bound** in CA 60.9%, US 60.4%, GB 36.2%,
  JP 34.8%, FR 25.6%, DE 8.3% of months. `sv_params.parquet` carries no
  `lam_at_bound`: #14 specified `ns_params.parquet`, and nothing in the plan
  plots or reads Svensson betas (Chart 3 is Nelson-Siegel, Phase 3 is PCA on
  yields). A later step that reads them needs the flag first.
- **Held-out p95 rose** for five country-model pairs after the widening even as
  every median improved. A wider λ range fits the easy months better and lets the
  hard months reach further. Worth watching in Phase 3.
- **The 0.5 beta threshold is a line through a continuum, not a natural break.**
  It now gaps GB 2010-02-28 (β2 = +50.2%), which is what fix 1 was for, but the
  largest kept |β| is 0.4452 (GB 1976-06-30, outside the chart window) and
  nothing distinguishes it in kind. The rule is stated in `PLAN.md` 2.4 and
  `review/2.4.md`; it is not a discovered boundary.

## Issues

- **#12** — answered and fully implemented. Left open until Session 2 is approved.
- **#13** — `Session 2 review`, four comments: the review, the #12 fix report,
  the completion report, and the fix-round report.
- **#14** — answered, implemented, **closed**.

## To resume

1. The owner said one fix round then approval. Both fixes are in, the suite is
   re-run, and #13 carries the comment listing what changed.
2. On `Session 2 approved`, record `Session 2 approved <date> (<commit>)` under
   `CLAUDE.md` → Validation status. **Only then** does Session 3 (Phase 3:
   steps 3.1, 3.2, 3.3) start.
3. Phase 3's gate note in `CLAUDE.md` asks for the pre-1997 bootstrap threshold
   to be revisited in the Session 3 PCA stability review.
