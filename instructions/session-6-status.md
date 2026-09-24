# Session 6 status — Phase 6, steps 6.1 to 6.4

Date: 2026-09-23. Last commit of the session: see `git log` on `main`.
Outcome: **finished**. All four steps built, each with its own commit, its own
`review/X.Y.md` and its "Done when" met; `make test` and `make lint` pass.

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

Tests: 288 at the end of session 5, **340** now. `uv run ruff check .` and
`uv run ruff format --check .` clean.

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

The deflated Sharpe is recomputed at the final **N = 17** (11 from session 5,
6 from 6.2): **0.567** against a threshold SR0 = 0.067 monthly. It **does not
clear the usual bar** of about 0.95, and the README says so in its own
sentence.

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

## Open questions for the owner

- **6.2, the rates-vol filter.** A filter whose expanding window started at
  `strategy_start` rather than at the first available month would be a
  different, unregistered control. It was not run and not logged. If the owner
  wants one it needs a `decision` issue and a new config key.
- **6.2, overlapping drawdown breaches.** `carry_hedged_ddstop` flattens five
  months, not the three `dd_reentry_months` names, because each month the
  drawdown is still below the stop re-arms the window. That is the rule as
  written applied month by month; the plan does not say what happens when
  breaches overlap.
- **6.4, the report header commit.** `git_commit()` stamps the report with the
  parent commit, because the report is written and then committed.

## Where to look

`README.md` first, then `reports/results.md`,
`data/checks/decomposition_shares.csv`,
`data/checks/attribution_2022_carry_hedged.csv`,
`data/checks/risk_controls.csv` and
`reports/figures/chart5_decomposition_carry_hedged.png`.
