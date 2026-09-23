# Session 4 status — Phase 4 complete, one decision issue open

Date: 2026-09-23. Written under the rule of 2026-09-22 (CLAUDE.md invariant 15).

## What was built

All four steps of Phase 4, in order, each with its own commit and its own
`review/X.Y.md`, each passing `make test` and `make lint` before the next
started.

| Step | Commit | What |
|---|---|---|
| — | `dd74c6b` | Session 3 approved; the Phase 1 carry-forward note closed |
| — | `f09a5ed` | Session 4 instructions, verbatim |
| — | `5258a2f` | PLAN.md amended for the three session-4 amendments |
| — | `7734ac8` | `config.checks.identity_gap_flag_bp_per_year` |
| 4.1 | `93f0277` | Carry and rolldown → `carry.parquet`, `carry_missing.csv` |
| 4.2 | `76c0fe0` | Return engine → `returns.parquet` + 4 check files |
| 4.3 | `e75781d` | Hedged/unhedged returns, `decisions/basis.md`, coverage log |
| 4.4 | `3ab33bd` | Chart 4, 7 pngs |
| — | `883187e` | CLAUDE.md running notes and data state |

Tests went 196 → **223 passed + 1 xfailed**; ruff check and ruff format clean.

## The three amendments

1. **Universe log (4.2)** — `data/checks/universe_by_month.csv`, 3,173 rows.
   The GB 30-year entering in 2016-01 is visible as the six-country total
   going from 47 to 48. Seven buckets appear and disappear mid-sample; all of
   those runs are pre-1997 except the US 30-year's 2002–2005 absence.
2. **Long-run identity (4.2)** — `data/checks/return_identity.csv`, 96 rows.
   Holds inside 50 bp a year at 1 to 7 years in every country over the
   strategy window; 12 of 48 country-tenors flagged, every one of them at
   10 years or longer, in the direction the sample's yield trend predicts.
   **The amendment's own wording is internally inconsistent** — see below.
3. **FX and funding coverage (4.3)** — `data/checks/return_coverage.csv`,
   3,173 rows. 29 country-months have a hedged return and no unhedged one:
   DE 1997-08 to 1998-12 (17, before the EUR spot) and **GB 1970 (12, before
   `DEXUSUK` starts)**, which the amendment did not anticipate. FR has none.
   Every `fred_immediate` funding month is Japanese and inside the three
   windows `decisions/short_anchor.md` records; no month uses a spliced euro
   rate outside its window.

## What did not go to plan

**One decision issue, #17, and the session continued past it** under the
CLAUDE.md rule (a step needing a choice the plan does not make gets a
`decision` issue; the session continues with steps that do not depend on the
answer). 4.3 and 4.4 do not depend on it.

- **The plan's `Δy` for the 4.2 return approximation cannot be what the plan
  meant.** It compares the par yield at `n − 1/12` with the par yield at `n`;
  those differ by tens of bp on a curve that has not moved, because the aged
  bond's first coupon is a stub. Median `gap_bp` is −28 to −35 bp at every
  tenor. The plan's own 0.1 bp unchanged-curve test cannot pass with it.
- **The 2 bp tolerance is separately unreachable**, by about 4 bp, because
  `(D, C)` are taken at `t` on the un-aged bond.
- What is in the repo: `r_local_approx` and `gap_bp` hold **the plan's
  formula unchanged**; two candidate repairs sit beside them in extra
  columns and in the three labelled blocks of `return_approx_gap.csv`;
  `test_approx_within_tolerance_on_200_draws` is `xfail(strict=True)` with
  the reason pointing at #17. Nothing was substituted and nothing downstream
  reads these columns — `r_local` is the full repricing.
- **So step 4.2's "Done when" is met only in that sense.** Said plainly here
  and in `review/4.2.md` → Open.

**Three deviations, all in the review files in full:**

- 4.3's CLI step is `fx_hedge`, not the plan's `fx`: `fx` is already the 1.7
  FX *loader*, and a build step of that name shadows it, so `build --all`
  would have stopped rebuilding `data/interim/fx.parquet`. PLAN.md amended.
- `decisions/short_anchor.md`'s per-country short-end table was wrong about
  GB: the BoE spot curve has no point below 1 year in 128 months of 680, so
  GB's 1-year rolldown is exactly 0 in those, not never. Corrected in 4.1's
  commit with a dated note.
- The cross-currency basis is **not measured**. All three free sources the
  plan names were probed on 2026-09-23; FRED and the BIS Data Portal publish
  no basis series, and the ECB Data Portal returned HTTP 503 and is recorded
  as not reached and treated as a negative. `decisions/basis.md` says so and
  quotes the brief's 20 to 50 bp. `data/checks/xccy_basis.csv` is not written.

## Where it stopped

Finished. All of Phase 4 is built, committed and pushed.

- `Session 4 review` — issue **#18**.
- `Question 4.2: the return approximation's dy, and the 2 bp tolerance` —
  issue **#17**, open.
- Session 3's review issue **#16** is closed.

Last commit before this line was written: `9b20626`.

Nothing starts on Session 5 until `Session 4 approved` is posted and the
approval line is in `CLAUDE.md` → Validation status.
