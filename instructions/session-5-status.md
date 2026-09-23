# Session 5 status — finished

Date: 2026-09-23. Instruction: `instructions/session-5.md` (saved verbatim,
commit `04af7a5`).

**Outcome: finished.** Phase 5 is complete — steps 5.1, 5.2, 5.3, 5.4 and
5.5, each with its own commit, its own `review/X.Y.md`, its "Done when"
met, `make test` and `make lint` green before the next started. The session
stopped once, on issue #19, and resumed when the owner answered it.

## What was built

| Step | Commit | Tests after | Outputs |
|---|---|---|---|
| Session 4 approval line | `6483d9c` | — | `CLAUDE.md` Validation status; issue #18 closed |
| Session 5 instruction | `04af7a5` | — | `instructions/session-5.md` |
| The five amendments into PLAN.md and CLAUDE.md | `c77be42` | — | the headline sentence in both |
| `min_eligible_buckets` 6 → 9 (rule 14, own commit) | `cf0e344` | — | `config.toml` |
| 5.1 Signal and the universe join | `99d4ee4` | 231 | `signal.parquet`, `universe_eligible.csv`, `universe_changes.csv`, `signal_exclusions.csv` |
| 5.2 Duration-neutral weights | `00fa75e` | 250 | `weights.parquet`, `weights_empty_months.csv` |
| 5.3 Carry-only backtest | `ff2e794` | 261 | `specifications.csv`, `backtest_*`, `metrics_*`, `positions_*`, `extreme_months_*` |
| Issue #19 ruling (own commit) | `c3ce589` | 261 | `pca.py` docstring corrected, `PLAN.md` 5.4 carries the ruling |
| 5.4 Slope overlay | `5474bed` | 271 | `pc2_expanding.parquet`, `overlay_positions.parquet`, `overlay_trades.csv` |
| 5.5 Combined, variants, deflated Sharpe | `015a919` | 280 | `metrics_table.csv`, `metrics_table.md`, the seven remaining runs |

`make test` **280 passed** (224 before this session), `make lint` clean.

## The headline, fixed before any result was seen

Written into `PLAN.md` 5.3 and `CLAUDE.md` in `c77be42`, before every
commit that computes anything: **carry-only, hedged, book-wide duration
neutrality, net of costs, 1997-08-31 to `strategy_end`, universe as
available each month** — `carry_hedged`, `full` window, `r_net`.

**0.591% a year, 2.233% vol, Sharpe 0.265, max drawdown −10.37%
(2019-12-31 to 2022-12-31), turnover 1.473, 2022 −4.41%.** Gross of costs,
0.767% and Sharpe 0.344. **Deflated Sharpe 0.568 with N = 11.** It is not
significant, and that is the result.

## The eleven logged runs

`reports/specifications.csv` has exactly the eleven rows amendment 2 fixed
in advance: `carry_hedged`, `carry_unhedged`, `overlay_hedged`,
`overlay_unhedged`, `combined_hedged`, `combined_unhedged`,
`carry_hedged_country_scope`, `carry_hedged_interbank_3m`,
`carry_hedged_cost0`, `carry_hedged_cost2x`, `carry_hedged_no_gb30`. All
are in `data/checks/metrics_table.md`, both windows, gross and net,
whether they help or not.

Two findings worth carrying into Phase 6: **nothing rests on the GB 30-year
bucket** (excluding it for the whole sample slightly improves the book,
0.626% against 0.591%), and **country-scope neutrality is the one variant
that changes the answer** (0.191% at Sharpe 0.120).

## Issue #19, the one stop

Posted at the start of the session, answered by the owner mid-session,
closed. `PLAN.md` 5.4 said the overlay's expanding PC2 was fitted on the
country's own rows; the `pca.py` docstring approved with session 3 said
5.4 took the pooled scope. The owner ruled **per country** — the overlay
trades a national 2s10s pair, and the pooled set is the 1-to-10
intersection, which would drop the long end out of the slope measure for
DE, JP, CA and FR — and asked for the conflict to be fixed rather than
left. It was, in its own commit (`c3ce589`): the docstring now states that
**5.4 takes the per-country expanding fit and 6.2 the pooled PC1**.

## Plan amendments made this session

1. The headline sentence — `PLAN.md` 5.3 and `CLAUDE.md`.
2. The five extra variants and what the review must show — `PLAN.md` 5.5.
3. The universe join, two new per-month check files,
   `min_eligible_buckets = 9` — `PLAN.md` 5.1 and 5.2, `config.toml`.
4. The real-panel invariant walk — `PLAN.md` 5.2,
   `tests/test_weights_panel.py`.
5. The two look-ahead tests — `PLAN.md` 5.3 and 5.4.
6. (in-session, 5.3) `extreme_months_<variant>.csv` moved from 5.5 to the
   5.3 engine, and every metric reported gross as well as net.
7. (in-session, 5.4) the issue #19 ruling written into `PLAN.md` 5.4.

## Fix round (2026-09-23, on the owner's three points)

| Fix | Commit | What it did |
|---|---|---|
| 1 Overlay anatomy | `2dc250b` | `overlay_trades.csv` is one row per trade (country, entry and exit date, direction, entry and exit z, months held, PnL in bp gross, its own cost, net), with `overlay_country_stats.csv` beside it; `build --step overlay_trades` writes both after the overlay run. `review/5.4.md` answers the two questions. |
| 2 Unhedged caveat | `079899e` | `unhedged_fx_exposure.csv`: net notional per currency per month for the three unhedged runs, then the regression of each book on its own currency-weighted FX return. `review/5.3.md` states that duration neutrality is not currency neutrality, with the numbers. |
| 3 DSR wording | `737faa7` | The DSR is stated as a probability against a threshold, in `review/5.5.md`, `PLAN.md` 6.4 and the foot of `metrics_table.md`; 6.4 recomputes it from the final row count and never with a smaller `N`. |

`make test` **288 passed** after the fix round (280 at step 5.5), `make lint`
clean, `ruff format --check` clean. No new rows in
`reports/specifications.csv`: the fixes read saved runs and compute no new
strategy, so `N` is still 11.

**What the fixes found.**

- **The overlay's loss is five trades, not a bleed.** 181 trades in the
  window, 99 winners to 82 losers, median trade **+1.86 bp**; the five worst
  cost **684 bp of the 912 bp total loss**. Strip them and the overlay is
  flat. No single country drives it — five of six lose (JP −342, FR −244,
  CA −213, DE −154, US −44, GB +83) and the concentration is in time:
  2022 −392, 2016 −379, 2008 −308. The per-trade sums tie out to the run to
  six decimals in bp.
- **The unhedged runs are currency books.** `carry_unhedged` regresses on
  its own currency-weighted FX term at **R² = 0.953**, beta 0.956, with an
  annualised intercept of **−0.56%**. The book carries a mean 1.86 units of
  foreign notional per unit of capital, to a maximum of 3.39. The hedged
  book's correlation with the same FX term is −0.195.
- **The DSR is 0.57 against a threshold of 0.067 over 11 trials**, and it
  is a probability, not a Sharpe.

## Last commit

`737faa7` — *Session 5 fix: the deflated Sharpe is reported as the
probability it is* — plus this status commit.

## Next

`Session 5 review` is issue #21, updated with the fix round. Nothing starts
on Phase 6 until `Session 5 approved` is recorded in `CLAUDE.md` →
Validation status.
