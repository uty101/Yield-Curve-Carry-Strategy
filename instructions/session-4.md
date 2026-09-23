Session 3 approved. Record "Session 3 approved 2026-09-23 (<commit>)" in CLAUDE.md Validation status, note against the Phase 1 carry-forward line that the pre-1997 US question is closed (the 30-year is not in the US PCA set and the borderline months move the 1980s loadings by at most 0.015), commit "Session 3 approved", push, close #16.

Then start Session 4: Phase 4, steps 4.1, 4.2, 4.3 and 4.4, under the session rule. Save this message verbatim to instructions/session-4.md first, and end with the status file.

Three amendments; amend PLAN.md in the same session before the review is posted.

1. Universe log (4.2). Write data/checks/universe_by_month.csv: for every month, per country, the tenors with a computable return (zeros present at t and at t+1 for the aged tenor), the count, and the total across countries. Report in the review: the first and last month each country-tenor bucket exists, every month where a bucket appears or disappears mid-sample, and the total bucket count by year. The GB 30-year entering in 2016 must be visible there.

2. Long-run identity (4.1 and 4.2). Write data/checks/return_identity.csv: per country and tenor, over the full available sample and over the strategy window, the annualised mean of r_local, the annualised mean of (carry + rolldown), the annualised mean price return, and the difference. Over a long sample the first two should be close for a constant-maturity bucket. Report the differences in bp and flag any country-tenor where the gap exceeds 50 bp a year, with your reading of why. This is a check, not a gate.

3. FX and funding coverage (4.3). Write data/checks/return_coverage.csv: per country and month, whether r_local, r_hedged and r_unhedged each exist, and the reason where one does not. Report the months where hedged exists but unhedged does not (DE and FR before the EUR FX series starts) and confirm no month uses a spliced funding rate outside the window decisions/short_anchor.md records.

The Session 4 review issue must also contain: the return approximation gap distribution from return_approx_gap.csv by tenor (median, p95, max) and whether the plan's 2 bp and 10 bp tolerances hold; the identity table above; and the carry-per-duration signal's range by country and decade, in bp per year of duration, so Chart 4's colour scale can be checked against numbers.
