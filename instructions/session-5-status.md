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
| 5.1 Signal and the universe join | `99d4ee4` | 230 | `signal.parquet`, `universe_eligible.csv`, `universe_changes.csv`, `signal_exclusions.csv` |
| 5.2 Duration-neutral weights | `00fa75e` | 249 | `weights.parquet`, `weights_empty_months.csv` |
| 5.3 Carry-only backtest | `ff2e794` | 260 | `specifications.csv`, `backtest_*`, `metrics_*`, `positions_*`, `extreme_months_*` |
| Issue #19 ruling (own commit) | `c3ce589` | 261 | `pca.py` docstring corrected, `PLAN.md` 5.4 carries the ruling |
| 5.4 Slope overlay | `5474bed` | 270 | `pc2_expanding.parquet`, `overlay_positions.parquet`, `overlay_trades.csv` |
| 5.5 Combined, variants, deflated Sharpe | `015a919` | 279 | `metrics_table.csv`, `metrics_table.md`, the seven remaining runs |

`make test` **279 passed** (224 before this session), `make lint` clean.

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

## Last commit

`015a919` — *Step 5.5: the combined book, the eleven variants and the
deflated Sharpe* — plus this status commit.

## Next

`Session 5 review` is posted. Nothing starts on Phase 6 until
`Session 5 approved` is recorded in `CLAUDE.md` → Validation status.
