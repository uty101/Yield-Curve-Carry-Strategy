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

## Gaps in the BIS policy rate: filled from the OECD immediate rate, labelled

Owner's rule, Session 1 part A review, 2026-09-22. The BIS `WS_CBPOL` series for
Japan has no value for **116 months**, in three windows — the periods with
no stated target (zero interest rate policy, quantitative easing, QQE):

| window | months | first filled value | last filled value | BIS on either side |
|---|---|---|---|---|
| 1999-03 .. 2000-07 | 17 | 0.041% (1999-03) | 0.021% (2000-07) | 0.25% (1999-02), 0.25% (2000-08) |
| 2001-04 .. 2006-02 | 59 | 0.020% (2001-04) | 0.001% (2006-02) | 0.15% (2001-03), 0.00% (2006-03) |
| 2013-05 .. 2016-08 | 40 | 0.070% (2013-05) | −0.043% (2016-08) | 0.05% (2013-04), −0.10% (2016-09) |

For `kind = policy`, any month **inside the BIS series' span** (between its
first and last month) with no BIS value is filled from the OECD *immediate
rate* — the monthly average of the overnight call-money rate, FRED
`IRSTCI01{US,GB,JP,CA,EZ}M156N`, percent, `/ 100`, stamped to the month end
like the other FRED monthly series. The filled row carries
`source = "fred_immediate"` in `funding.parquet`, so every consumer can see
which months are fills; a month with a BIS value is never overwritten, and
the fill never extends a series before its first or after its last BIS
month. The rule runs for every currency (the five series are fetched and in
the manifest) even though only Japan has gaps today, so a gap that appears
in a re-fetch is treated the same way. `data/checks/funding_fill.csv` lists
every filled run per country (`country, first, last, months_filled`; a
country with no fill has one row with 0).

What the fill is and is not: it is a traded overnight average, not a
target. Where both exist, the immediate rate differs from the BIS policy
rate by −2 bp (US), −6 bp (GB), −2 bp (CA) and +42 bp (JP; the BIS series is
the discount rate before 1995, above which the call rate traded) on
average, with single months hundreds of bp apart in the 1970s–80s. Inside
the three JP windows the immediate rate sits within 1 bp of the BIS value
on the month either side, which is what a zero-target regime looks like.
The `EZ` immediate series stops at 2026-01, so a euro gap after that could
not be filled; there is none.

`decisions/short_anchor.md` is the record; `loaders/short_rates.py`
(`fill_policy_gaps`, `funding_fill_rows`) is the code;
`test_policy_gap_filled_from_immediate_and_labelled` and
`test_bis_value_never_overwritten` are the tests.

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

**Correction, 2026-09-23, step 4.1.** The table above reads as though each
country's shortest observed tenor is the same in every month. It is not, and
`data/checks/carry_missing.csv` is what showed it:

| Country | months with no observed tenor below 1 − 1/12 | when |
|---|---|---|
| FR | 262 of 262 (all) | always: TEC 1 is the shortest |
| JP | 598 of 598 at the 1-year bucket, and 12 months at 2 and 3 years | always at 1y; the 12 are months whose curve starts at 2, 3 or 4 years |
| US | 236 of 776 | 1962-01 .. 1981-08, before DGS3MO and DGS6MO start |
| GB | 128 of 680 (126 starting at 1.0, 2 at 1.5) | scattered across the whole sample in 46 runs, 1970-01 .. 2025-12, longest 8 months |
| CA, DE | 0 | 0.25 observed in every month |

The GB row is the one the table got wrong: the BoE nominal spot curve does
not always publish a point below 1 year, so GB's 1-year rolldown is exactly
0 in 128 months of 680 (18.8%) rather than never. The US row is right about
the mechanism and wrong about the period — before 1981-09 the US short end
is the 1-year too. Nothing about the rule changes: the flat short end is
still the convention, still the only exception to rule 13, and every one of
these months is counted in `n_flat_short_end` rather than filled.

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
