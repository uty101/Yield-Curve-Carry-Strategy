Session 4 approved. Record "Session 4 approved 2026-09-23 (<commit>)" in CLAUDE.md Validation status, commit "Session 4 approved", push, close #18.

Then start Session 5: Phase 5, steps 5.1 to 5.5, under the session rule. Save this message verbatim to instructions/session-5.md first, and end with the status file. Five amendments; amend PLAN.md in the same session before the review is posted.

1. The headline is fixed now, before any result is seen: carry-only, hedged, book-wide duration neutrality, net of costs, 1997-08-31 to strategy_end, universe as available each month. Write that sentence into PLAN.md 5.3 and into CLAUDE.md. Everything else is a logged variant, never the headline, whatever the numbers say.

2. Variants, each a row in specifications.csv with its own run label, all run and all reported whether they help or not: duration_neutral_scope = country; unhedged; funding_rate = interbank_3m; costs at 0 and at 2x; GB 30y excluded from the universe for the whole sample. The last one exists because that bucket enters in 2016 and I want to see whether anything rests on it.

3. Universe discipline (5.1 and 5.2). Join weights to universe_by_month.csv. Report the eligible bucket count per month, every month a bucket enters or leaves, and the yield-floor exclusions per month. Pre-register a minimum: if fewer than 9 buckets are eligible in a month, the book is flat that month and the month is logged. State it in config as min_eligible_buckets = 9.

4. Real-panel invariants (5.2), tested every month of the backtest, not only on synthetic cases: sum of w times D is zero to 1e-10; no bucket in both legs; the long leg's duration equals long_duration_budget; weights use the duration from the same function as 4.1 and 4.2. A test that walks the real panel.

5. Timing (5.3 and 5.4). Signal from the curve at t, return from t to t+1, and a test that appending months after t changes neither the weights at t nor the overlay z-score at t. The overlay's PCA loadings are expanding-window as already specified.

The Session 5 review issue must contain: the headline metrics table (annualised return, vol, Sharpe, max drawdown with dates, turnover, 2022 in isolation, gross and net of costs); the same table for every variant; the deflated Sharpe with N and the specifications.csv row count; the eligible bucket count by year; and the 10 largest monthly gains and losses with the country-tenor legs that drove them, so the biggest months can be checked against the curve moves rather than taken on trust.
