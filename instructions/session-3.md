Session 2 approved. Record "Session 2 approved 2026-09-23 (<commit>)" in CLAUDE.md Validation status, commit "Session 2 approved", push, close #13.

Then start Session 3: Phase 3, steps 3.1, 3.2 and 3.3, under the session rule. Save this message verbatim to instructions/session-3.md first, and end with the status file as usual. Four amendments; amend PLAN.md in the same session before the review is posted.

1. Tenor sets. PCA runs on a fixed tenor set, so choose it per country: the largest set of standard tenors present in at least 95% of that country's months from the first month it enters the panel, and name the excluded tenors. The pooled set is the intersection of the six country sets. Write data/checks/pca_tenor_sets.csv: country, tenors used, tenors excluded, months available, months dropped for a missing tenor. If any country's set has fewer than 5 tenors, or the pooled set has fewer than 6, stop and post a decision issue.

2. Sign normalisation with a variable tenor set: PC1 loading positive at 10 years; PC2 positive at (longest tenor in the set) minus (2 years); PC3 positive at the middle tenor of the set. State the convention in the review.

3. Inputs are the zero curves from curves_zero.parquet, in basis points of monthly change, never the fitted NS or Svensson yields. A month enters only if both it and the previous month have every tenor in the set, so a gap never becomes a fake 12-month change. Test that.

4. 3.2 stability, plus the item CLAUDE.md carries forward from Phase 1: report US decade loadings twice, once on all months and once excluding the pre-1997 months whose 30-year zero-to-par gap exceeds 50 bp, and say whether the 1980s loading vector changes materially. Write both into the decade table with a flag column.

The Session 3 review issue must contain, besides the usual sections:
- pca_tenor_sets.csv in full.
- Explained variance of PC1, PC2, PC3 per country and pooled, and the cumulative share of the first three.
- The loading vectors per country, and the absolute correlation of each decade's PC1, PC2 and PC3 loadings against the full-sample ones.
- The US with and without the borderline 1980s months.
- Months dropped per country and why.
