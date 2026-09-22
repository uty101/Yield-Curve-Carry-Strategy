Start Session 2: Phase 2, steps 2.1, 2.2, 2.3 and 2.4, under the session rule in PLAN.md.

First, save this message verbatim to instructions/session-2.md and commit it ("Session 2: instructions"). From now on every session ends, however it ends (finished, stopped on a question, or blocked), by writing instructions/session-N-status.md (what was built, what was not, why it stopped, the last commit) and pushing it. Add this to PLAN.md and CLAUDE.md with the amendments below.

Three amendments; amend PLAN.md in the same session before the review is posted.

1. Repricing check (2.1). Curve.from_panel for zero curves keeps every coupon-grid point in curves_zero.parquet, not only standard tenors. Write data/checks/par_reprice.csv: for every US, JP and FR month and every observed par node, observed par yield, par_yield_from_zero(Curve.from_panel(...)), diff_bp. Expected max |diff| below 0.01 bp; if it is larger, stop and report before 2.2.

2. Bundesbank parameter mapping (2.3). In compare_bundesbank, convert the Bundesbank's (tau1, tau2) to our lambda form and, where 1/tau2 < 1/tau1, swap the labels (and beta2 with beta3) so both sides use lambda2 > lambda1 before comparing betas and lambdas. Record in the csv whether a swap was made. Report the distribution of the Bundesbank's 1/tau1 and 1/tau2 (p5, median, p95) and the share of DE months where either lies outside config's lambda grid. If that share is above 10%, post a decision issue on whether to widen the grid and do not build 2.4 until answered. test_de_fit_recovers_bundesbank_curve uses a fixture row whose lambdas lie inside the grid, and a second test documents what happens for a row outside it.

3. Held-out fit test (2.2 and 2.3). Fits still use the 8 standard tenors only. Write data/checks/fit_holdout.csv: for GB, CA and JP, every month and every observed non-standard tenor between 1 and 30 years (interpolated == False), the NS-free, NS-DL and Svensson fitted yield against the observed zero, error in bp. For US and FR use the bootstrapped non-standard coupon-grid zeros and label them bootstrapped. Summarise per country and model: median and p95 of monthly held-out RMSE, next to the in-sample RMSE.

The Session 2 review issue must contain, besides the usual sections:
- par_reprice.csv: max |diff| per country.
- In-sample RMSE (bp) per country, model and decade: median and p95; months skipped per country from fit_skipped.csv.
- Held-out RMSE per country and model: median and p95, and the in-sample to held-out ratio.
- NS-free lambda per country: p5, median, p95, and the share of months at a grid bound.
- Svensson: share of months with lam_gap below 2 grid steps (weak identification), per country.
- svensson_vs_bundesbank.csv: our RMSE, the swap count, the lambda-outside-grid share, and median beta_diff_max.

Stop after posting the "Session 2 review" issue and pushing the status file.
