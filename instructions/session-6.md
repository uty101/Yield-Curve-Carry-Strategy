Session 5 approved. Record "Session 5 approved 2026-09-23 (<commit>)" in CLAUDE.md Validation status, commit "Session 5 approved", push, close the Session 5 review issue.

Then start Session 6: Phase 6, steps 6.1 to 6.4, under the session rule. Save this message verbatim to instructions/session-6.md first, and end with the status file. Five amendments; amend PLAN.md in the same session before the review is posted.

1. 6.1's identity uses the residual definition ruled on in #17: yield-change PnL is r_local minus carry minus rolldown, and the duration-convexity approximation is reported beside it, never inside the identity. The four pieces still sum to the reported return to 1e-10.

2. 6.2 runs all three pre-registered risk controls from config (vol target, drawdown stop, pooled PC1 vol filter), each as its own logged run, each reported whether it helps or not. None of them may change the headline definition, whatever the numbers say. Report each against the headline on return, vol, Sharpe, max drawdown, 2022, and turnover.

3. The deflated Sharpe in 6.4 is recomputed with the final specifications.csv row count, never a smaller N, and reported as a probability with its threshold. If the headline stays below the usual bar, the README says so in its own sentence rather than in a footnote.

4. 6.3 is written from the numbers already in the repo, not from general caveats. It must cover, each with its figure: the overlay is flat gross (-190 bp over 29 years) and loses 722 bp to costs, with the five worst trades (2008-09 GB and CA flatteners, 2022-08 FR steepener, 2021-01 CA) costing 684 bp because a mean-reversion slope signal is short the trend; duration neutrality is not currency neutrality, with the 95% variance figure; the funding rate is a policy rate used as a 3-month anchor, with the Japanese fill windows; the cross-currency basis is not measured; the Nelson-Siegel lambda is unidentified on flat curves; the US on-the-run richness of about 10 bp at 10 years; and the buckets that enter or leave mid-sample.

5. 6.4: every number in README.md comes from reports/results.md, with a test asserting they match. Include the per-year return table for the headline, the full variant table, and the eleven-plus logged runs with their labels.

The Session 6 review issue must contain: the decomposition shares (carry earned against yield-change PnL, cumulative and by decade); the 2022 attribution by country and leg; the three risk-control runs against the headline; the final deflated Sharpe with N; and confirmation that the README and results.md numbers tie.
