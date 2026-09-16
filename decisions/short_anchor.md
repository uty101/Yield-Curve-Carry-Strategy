# The short anchor at `short_tenor = 0.25` is the policy rate, not a 3-month rate

Decided 2026-09-16 (session 1, owner, issue #1 follow-up).

## What it is

Every country's curve gets one extra point at `tenor_years = 0.25` in step
1.8. The rate placed there is the **BIS central bank policy rate**
(`WS_CBPOL`, monthly, series `M.US`, `M.GB`, `M.JP`, `M.CA`, `M.XM` for the
euro area). It is an **overnight** rate — the Fed funds target, Bank Rate, the
BoJ policy rate, the BoC target for the overnight rate, the ECB deposit or
main refinancing rate as BIS defines it — sitting on the curve at the 3-month
tenor. It is not a 3-month rate.

It is kept there because it is the only funding series with a consistent
definition and full history for all five currencies: US from 1954, GB and JP
from 1946, CA from 1960, euro area from 1999. The alternative, OECD 3-month
interbank (`IR3TIB01*` on FRED), starts in 2002 for JPY and stops at 2026-01
for GBP and EUR, and carries a bank credit spread that spikes in 2008 and
would read as carry.

## What it is used for

1. **The 1-year bucket's rolldown.** Rolldown at tenor n needs the yield at
   n − 1/12. For n = 1 that is 0.9167 years, interpolated linearly between the
   0.25 point and the 1-year point (rule 13: between observed tenors only).
   The anchor is therefore in the 1-year rolldown of every country and in
   nothing else on the curve side: the 2-year bucket rolls to 1.9167, between
   1 and 2, and never touches the anchor.
2. **The funding rate.** Carry_n = y_n − r_short and the hedge term
   (r_short,base − r_short,foreign)/12 both read `r_short` from the same
   series. `config.toml` names it: `funding_rate = "policy"`.

## The size of the gap

An overnight rate sits below a 3-month rate by a term premium plus, for
interbank rates, a bank credit spread. In normal years that is 10 to 30 bp;
in 2008 the interbank gap reached 200+ bp for USD and GBP. Putting an
overnight rate at 0.25 years therefore (i) overstates the 1-year rolldown by
a few bp per year in normal times and (ii) overstates carry by the same term
premium for every bucket equally — which cancels in a cross-sectional rank
within a currency but not across currencies whose term premia differ.

## The robustness run

A variant with the OECD 3-month interbank series placed at 0.25 and used as
`r_short` is one of the logged robustness runs in step 5.5
(`funding_rate_robustness = "interbank_3m"` in `config.toml`; series
`IR3TIB01USM156N`, `IR3TIB01GBM156N`, `IR3TIB01JPM156N`, `IR3TIB01CAM156N`,
`IR3TIB01EZM156N`). It is logged in `specifications.csv` before its result is
seen and reported next to the default whether or not it helps. Its sample is
shorter (JPY from 2002-04) and stops at 2026-01 for GBP and EUR; the report
states both.
