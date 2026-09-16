# The funding rate is never on the curve

Rewritten 2026-09-16 for plan v2 (amendment B). The v1 rule — the BIS
policy rate placed on every curve at `tenor_years = 0.25` — is withdrawn.
Nothing is appended to any curve.

## The funding rate: what it is and what it does

The funding rate is the **BIS central bank policy rate** (`WS_CBPOL`,
monthly), an overnight rate: Fed funds target (US), Bank Rate (GB), the BoJ
policy rate (JP), the BoC overnight target (CA), the ECB rate as BIS defines
it (`XM`, euro area). It is joined to carry and returns **by country and
date** from `data/interim/funding.parquet`, never read off a curve.

It is used for exactly two things:

1. **Carry.** `carry_n = y_n − r_short` for every tenor (brief 6.4).
2. **Financing and the hedge.** Every bucket return is an excess return
   over its own funding rate: `r_excess_local = r_local − r_short_local/12`.
   Under covered interest parity the FX-hedged excess return in the base
   currency equals the local excess return, so `r_hedged = r_excess_local`;
   the unhedged return is `r_local + Δ ln S − r_short_base/12`
   (`decisions/basis.md`, step 4.3).

The euro countries before 1999-01: Germany's and France's national BIS
policy rates (`M.DE`, `M.FR`, both discontinued at 1998-12: the Bundesbank
repo rate from 1985, the Banque de France repo rate from 1982) are used
before `config.hedge.eur_splice = 1999-01-31`, and `M.XM` from that month
end (amendment D; the probe on 2026-09-16 found both series, 1948-07 → 1998-12
and 1945-01 → 1998-12). The splice is a step in the level of the series and
is visible in `data/checks/coverage.csv`.

The OECD 3-month interbank series (`IR3TIB01*`) are the robustness funding
rate (`funding_rate_robustness = "interbank_3m"`), used in a logged run in
5.5 with the same definitions. Their sample is shorter (JPY from 2002-04)
and stops at 2026-01 for GBP and EUR.

## The short end of each curve

Below the shortest observed zero tenor the zero yield is **flat** from that
tenor (`config.short_end = "flat"`). This is a convention, not
extrapolation, and the only exception to rule 13. `Curve.at(t)` returns
`yields[0]` for `t < tenors.min()`; above `tenors.max()` it is still NaN.
It is exercised by `bondmath` (discounting a seasoned bond's short stub),
by `bootstrap` (coupon dates below the shortest par tenor take that tenor's
par yield) and by the 1-year rolldown through `Curve.at(1 − 1/12)`.

Where each country's observed short end starts, and what that does to the
1-year rolldown (`y_roll = y(1 − 1/12) = y(0.9167)`):

| Country | Shortest observed tenor | Source of it | 1-year rolldown |
|---|---|---|---|
| US | 0.25 (DGS3MO, from 1981-09), 0.5 (DGS6MO, from 1981-09) | FRED, added in 1.1 | interpolated between 0.5 and 1 (from 1981-09; flat before) |
| GB | 0.5 | BoE spot curve | interpolated between 0.5 and 1 |
| DE | 0.25, 0.5 | reconstructed from the Svensson parameters in 1.3 | interpolated between 0.5 and 1 |
| JP | 1 | MOF benchmark yields start at 1Y | **flat: rolldown = 0** |
| CA | 0.25 | BoC zero curve (0.25-year steps) | interpolated between 0.75 and 1 |
| FR | 1 | TEC 1 is the shortest | **flat: rolldown = 0** |

So JP's and FR's 1-year buckets carry no rolldown; their carry is
unaffected. `data/checks/carry_missing.csv` reports `n_flat_short_end` per
country — the number of 1-year bucket-months where `y_roll` fell in the
flat region — so the size of this is a number in the review. The 2-year
and longer buckets roll between observed tenors in every country and are
untouched.

## What v1 got wrong, for the record

Putting an overnight rate on the curve at 0.25 years (i) made the 1-year
rolldown depend on a rate that is not a bond yield, (ii) let the bootstrap's
sub-1-year stubs discount at a policy rate, and (iii) put the funding rate
inside the curve object where `par` and `zero` functions could read it as a
yield. All three are removed by keeping the funding rate in its own table.
