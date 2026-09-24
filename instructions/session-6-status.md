# Session 6 status — Phase 6, steps 6.1 to 6.4

Date: 2026-09-23, fix round 2026-09-24. Last commit of the session: see
`git log` on `main`. Outcome: **finished, one fix round done, awaiting the
owner's approval line**. All four steps built, each with its own commit, its
own `review/X.Y.md` and its "Done when" met; `make test` and `make lint` pass.

## What was built

| step | commit | what it is |
|---|---|---|
| 6.1 | `7f9faf0` | the decomposition and the identity it has to satisfy |
| 6.2 | `aaf57aa` | the 2022 attribution, and three risk controls that do not help |
| 6.3 | `7e6ebee` | what carry does not tell you, with a figure on every claim |
| 6.4 | `60fde73` | the report, and a README with no number typed by hand |

Before them: `d8ac521` recorded the Session 5 approval in `CLAUDE.md` and
issue #21 was closed; `186c83d` saved the owner's instruction verbatim to
`instructions/session-6.md`.

Fix rounds (2026-09-24), six commits:

| commit | what it is |
|---|---|
| `0ad6bf6` | the rates-vol null is diagnosed, not asserted |
| `406a876` | config key `rates_vol_window_months`, pre-registered at 120 (its own commit, rule 14) |
| `f5a4868` | the rolling rates-vol filter, the live test of a dead threshold |
| `080dd09` | the rolling filter carries its selection caveat everywhere; the expanding-fit fact and its guard tests |
| `e62b539` | the documented pipeline sequence double-logged eight runs |
| `98ba198` | two defects the determinism check found (CRLF writers, `overlay_trades` in `build --all`) |
| `5309db9` | `unhedged_fx_exposure.csv` written LF, as the writer now says |
| `f1353f3` | N counts distinct labels; the two rebuild checks named; the stale status text; the wrong `fetch --source` hint |
| `af771ef` | `decomposition_shares.csv` covers all 19 variants |

Tests: 288 at the end of session 5, **354** after the fix rounds.
`uv run ruff check .` and `uv run ruff format --check .` clean.
`reports/specifications.csv` has **19** rows — the two rolling runs of
amendment 9 — and every deflated Sharpe in the report is recomputed at
**N = 19**. The headline's is 0.573 and still does not clear the bar.

## The headline answer to the brief

Over the full window (1997-08-31 to 2026-08-31, 348 months) the headline
`carry_hedged` book **earned 75.68 points of carry, gave back 53.43 to yield
changes and 5.13 to costs, and kept 17.13** — 0.59% a year at 2.23%
annualised volatility, Sharpe 0.265, worst drawdown -10.37%.

The failure mode the brief names did not happen: the return is carry **net of
a losing yield bet**, not a long-duration bet dressed as carry. The
yield-change PnL is negative in every decade.

The four pieces sum to the reported net return to **5.20e-18** on every month
of every logged variant, against a tolerance of 1e-10.

## What did not help, and is reported anyway

All three pre-registered risk controls were logged before they computed and
none improves the headline: vol targeting is a leverage rule here and nearly
doubles vol, turnover and drawdown for a lower Sharpe; the drawdown stop sells
the 2023 bottom for five months; the pooled PC1 volatility filter **never
fires inside the sample at all**, because its expanding threshold is
calibrated on a history beginning in 1962 and all 67 of its flags are
pre-1983. That last one is reported, not repaired — re-calibrating a
pre-registered parameter after seeing it do nothing is what rule 6 exists to
prevent.

The deflated Sharpe is recomputed at the final **N = 19** (11 from session 5,
6 from 6.2, 2 from amendment 9): **0.573** against a threshold SR0 = 0.066
monthly. It **does not clear the usual bar** of about 0.95, and the README
says so in its own sentence. (This paragraph read N = 17 and 0.567 until
2026-09-24; those were the figures before amendment 9 added the two rolling
runs. `reports/results.md` and `README.md` were always correct.)

## The one control that helps

`<base>_ratesvol_rolling` (amendment 9, pre-registered 2026-09-24) is the only
one of the four that improves the headline. It does it by cutting risk, not by
adding return: on `carry_hedged` the return falls from 0.591% to 0.579% a year
while vol falls from 2.233% to 2.033%, the worst drawdown from -10.37% to
-8.63%, 2022 from -4.41% to -1.43% and turnover from 1.473 to 1.328, for a
Sharpe of 0.285 against 0.265. On `combined_hedged` it is larger: Sharpe 0.093
to 0.217. **It is still a logged variant and not the headline**, which is the
carry-only hedged book as fixed before any result was seen.

## Deviations from PLAN.md, all eight amended in the plan this session

1. **6.1** — the Taylor form subtracts the rolldown inside its bracket. The
   plan wrote the bare price term and in the same paragraph required the
   residual to equal the weighted 4.2 `gap_bp`; those cannot both hold and the
   step's own test could not pass.
2. **6.1** — `decomposition_shares.csv` also carries a row block per decade,
   which the session instruction asks the review to report.
3. **6.2** — the pooled PC1 score is the cross-country mean of each country's
   own score; a pooled fit has one score per country-month and the plan did
   not say how they collapse.
4. **6.2** — `pca_min_months` counts months of history, not rows of the
   stacked matrix.
5. **6.3** — the section is its own module (`caveats.py`);
   `report.section_what_carry_does_not_tell_you` is kept as the plan's entry
   point and a test asserts the two return the same string.
6. **6.3** — the tenor at which the on-the-run gap is quoted comes from
   `config.sample.sample_max_tenor`, not a literal (global rule 4).
7. **6.4** — the report lives in `results.py`, not `report.py`.
8. **6.4** — `build --all` stops before the three steps that read a completed
   backtest; the full sequence is written out in the `Makefile`.

No `decision` issue was opened. Every deviation above is a plan text that was
internally inconsistent or silent on a detail with one self-consistent
reading, and each is recorded in full in its step's review file, in the
commit message and in the amended PLAN.md.

## Wrap-up checks (2026-09-24)

**README and results.md tie — PASS.**
`tests/test_readme.py::test_readme_results_equal_results_md`. The shared block
is 13,484 characters and is written into both files from one string, so drift
is impossible rather than merely absent.

**`specifications.csv` — PASS.** 19 rows, 19 unique `run_id`, 0 duplicates, 19
unique labels, timestamps monotonic; `speclog.count_runs()` returns 19 and the
report prints `N = 19`.

**Fresh clone with a refetch — this is the availability check, not a
reproduction test** (owner's ruling, 2026-09-24). All ten sources answered and
every loader parsed; the BdF refetch moved 10 of 2,584 FR rows, all at the
incomplete 2026-09-30, none on or before `strategy_end`. See
`decisions/sources.md`. My earlier report that three BdF retries failed was
wrong: they were typed `fetch --source bdf` and never ran, because the CLI
takes the loader name `fr`.

**Reproduction from fixed raw inputs — every number reproduces.** A full
rebuild (`build --all`, `run --all`, the post-run steps, `report`) leaves
`N = 19` and the headline DSR at 0.573 even though the spec log goes from 19
rows to 38, which is the point of the label-based `N`. Of 83 committed
`data/checks` files, 63 are byte-identical, 19 differ only in the per-execution
`run_id` column, and 1 differs in the audit-trail row count in its footnote.
The remaining question for the owner is whether execution metadata — `run_id`,
the row count `M`, the runs listing — counts as an allowed difference alongside
the commit stamp.

**Determinism from fixed raw inputs — PASS**, and it is the check worth
keeping. Clone the tracked tree, copy the existing `data/raw/` in, wipe
interim and processed, `build --all`: all six core parquets reproduce bit for
bit and every committed `data/checks` file byte for byte.

Two incidental findings, both recorded rather than worked around: a partial
fetch is **not resumable the same day** (the dated filename collides, which is
invariant 5 working as intended), and a scratch path of ~200 characters breaks
`scipy` on this machine through Windows MAX_PATH.

## Open questions for the owner

- **6.2, the rates-vol filter.** Closed. Diagnosed as a null in fix 1 and then
  retested live in fix 2 (amendment 9).
  The rule fires at 9.5% of its 705 armed months, which is the ~10% an
  expanding 90th percentile implies, but all 67 triggers are pre-1983: the
  threshold is set by 1962-1982, when pooled PC1 vol ran two to three times
  its post-1997 level. Inside the sample the largest trailing vol is 0.679 of
  the threshold in force. `data/checks/ratesvol_filter.csv` has the month-by-
  month evidence and three tests keep a null distinguishable from a no-op.
  The idea was then retested on a live threshold:
  `<base>_ratesvol_rolling` takes the same 90th percentile over a rolling
  `rates_vol_window_months = 120` window, was pre-registered in its own commit
  before the run existed, and fires **31** of the same 349 armed months (8.9%)
  in two episodes — 2008-04 to 2009-04 and 2022-03 to 2023-08. It is the only
  one of the four controls that improves the headline, and it does so by
  cutting risk rather than adding return (Sharpe 0.265 to 0.285, vol 2.233% to
  2.033%, max DD -10.37% to -8.63%, 2022 -4.41% to -1.43%, turnover 1.473 to
  1.328, return 0.591% to 0.579%). The expanding runs stay logged and reported.
- **6.2, overlapping drawdown breaches.** `carry_hedged_ddstop` flattens five
  months, not the three `dd_reentry_months` names, because each month the
  drawdown is still below the stop re-arms the window. That is the rule as
  written applied month by month; the plan does not say what happens when
  breaches overlap.
- **6.4, the report header commit.** `git_commit()` stamps the report with the
  parent commit, because the report is written and then committed.
- ~~**What "reproducible" should mean here.**~~ **Closed by the owner's ruling
  of 2026-09-24**, implemented in `f1353f3`. There are **two** checks and they
  answer different questions, both now written into `CLAUDE.md` → "The two
  rebuild checks, and which is which":
  **(a) reproduction** — fixed raw inputs, the whole pipeline, derived data and
  `reports/results.md` identical, with the git commit stamp the only permitted
  difference; and **(b) source availability** — a refetch, which is expected to
  differ and reports what moved, never a reproduction test.
  What made (a) possible was the companion ruling that **`N` counts distinct
  labels, not rows** (invariant 6): a rebuild re-runs every variant, and under
  a row-count `N` that alone would have moved every deflated Sharpe. Neither an
  `--as-of` pin nor a fixed-`N` rebuild flag was needed, so no config key and
  no `decision` issue were added.

## Where to look

`README.md` first, then `reports/results.md`,
`data/checks/decomposition_shares.csv`,
`data/checks/attribution_2022_carry_hedged.csv`,
`data/checks/risk_controls.csv`, `data/checks/ratesvol_filter.csv` and
`reports/figures/chart5_decomposition_carry_hedged.png`.
