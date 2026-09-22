# Compounding conventions of the zero-curve sources

Inside the package a zero yield `z` at tenor `t` means `DF(t) = (1 + z)^(-t)`
— annual compounding (PLAN.md, Conventions). Each zero-curve loader reads
the source's stated convention from the source's own documentation, records
it here with the quote, and converts once, in `parse`. Par yields (US, JP,
FR) are quoted with the country's coupon frequency and are not converted.

| Country | Source | Stated convention | Conversion in the loader | Recorded in step |
|---|---|---|---|---|
| GB | Bank of England, nominal government spot curve (`glcnominalmonthedata.zip`) | **Continuously compounded, quoted on an annual basis** | `z = exp(r) − 1` | 1.2 |
| DE | Deutsche Bundesbank, Svensson parameters for listed Federal securities (`BBSIS`) | **Annually (discretely) compounded** spot rates | none | 1.3 |
| CA | Bank of Canada, zero-coupon yield curve (`lookup_yield_curve.php`, decimals) | **Continuously compounded** zero rates | `z = exp(r) − 1` | 1.5 (Session 1 fix, issue #8) |

## GB — Bank of England

Source: https://www.bankofengland.co.uk/statistics/yield-curves, read
2026-09-17, section "Yield curve methodology":

> **At which frequency are the yields compounded and how are they quoted?**
> The yields (spot and forward) are continuously compounded and quoted on
> an annual basis. We do not provide support in transforming these yields
> into other forms of compounding/quoting or how these should be used for
> specific applications.

The same page's "What is the difference between EIOPA risk free rate data
and the yield curves on this page?" is a two-column table; its
"Compounding" row reads *Yield curves: The curves are continuously
compounded and quoted on an annual basis. / Solvency II Technical
Information: The figures are annually compounded zero coupon spot rates.*
The annually-compounded line describes the PRA's Solvency II term
structures, not the curves in the archive we use.

Size of the conversion: at r = 5% continuous, `exp(0.05) − 1 = 5.127%`,
12.7 bp; at 1%, 0.5 bp; at 10%, 51.7 bp. Applied to the percent value
divided by 100, once, in `curvecarry.loaders.gb.parse_workbook`
(`test_compounding_conversion_applied_once`).

The `info` sheet in each archive file does not state the convention; it
points to the website.

## DE — Deutsche Bundesbank

Source: Schich, S. T., *Estimating the German term structure*, Deutsche
Bundesbank Discussion Paper 4/97 (linked from the Bundesbank's
term-structure statistics page; downloaded 2026-09-17), the method the
`BBSIS` Svensson series still use (Monthly Report, October 1997, "Estimating
the term structure of interest rates"):

> Discrete compounding has been chosen in these illustrations since it is
> used also in the estimations detailed in Section III. In the literature,
> recourse is often taken to the assumption of continuous compounding in
> order to facilitate the calculations. However, this assumption can
> substantially alter the results of the estimates. (footnote 3)

with the discount factor defined as `δ_{t,m} = (1 + z_{t,m})^{−m}` (eq. 6),
the Svensson function inserted into it (eq. 22), and
`z_{t,m} = δ_{t,m}^{−1/m} − 1` (eq. 23). The Bundesbank's `z` is therefore
the annually compounded spot rate, which is the package convention: **no
conversion**. The spot-rate function itself is the decay-time form
`z(m) = β0 + β1 (1−e^{−m/τ1})/(m/τ1) + β2[(1−e^{−m/τ1})/(m/τ1) − e^{−m/τ1}] + β3[(1−e^{−m/τ2})/(m/τ2) − e^{−m/τ2}]`
(Monthly Report October 1997, p. 64), implemented in
`curvecarry.svensson.svensson_yield`; reconstructing the published 10-year
series from the parameters matches within 0.55 bp on every one of 7,390
days (the published series is rounded to 2 decimals of a percent).

## CA — Bank of Canada

The data page (https://www.bankofcanada.ca/rates/interest-rates/bond-yield-curves/,
read 2026-09-17) states only the unit — "The data are expressed as decimals
(e.g. 0.0500 = 5.00% yield)" — and points to the methodology paper, which
this machine could not fetch (HTTP 202, empty body; issue #8). The owner
supplied the definition on 2026-09-22:

- Bolder, D. J., Johnson, G. and Metzler, A. (2004), *An Empirical Analysis
  of the Canadian Term Structure of Zero-Coupon Interest Rates*, Bank of
  Canada Working Paper 2004-48, https://doi.org/10.34989/swp-2004-48 —
  defines `z(t, T)` as the **continuously compounded** yield (pp. 25–26);
  as restated in the data appendix of *Riding the yield curve: a spanning
  analysis*, Review of Quantitative Finance and Accounting (2012),
  https://link.springer.com/article/10.1007/s11156-011-0267-7, which uses
  the same Bank of Canada download.
- Bolder, D. J. and Stréliski, D., *Yield Curve Modelling at the Bank of
  Canada*, Bank of Canada Technical Report 84,
  https://www.bankofcanada.ca/wp-content/uploads/2010/01/tr84.pdf — the
  zero curve is derived continuously compounded (eq. 6 and 7).

So the file's `z` is `−ln d(t) / t`, and the package's annually compounded
zero is `exp(z) − 1`, applied once in `curvecarry.loaders.ca.parse`
(`test_compounding_conversion_applied_once`, as for GB). Size of the
conversion in the data: 1986-01-02 1y `0.0900549` → `0.0942343` (41.8 bp);
1991-01-02 30y `0.1150026` → `0.1218763` (68.7 bp); 2005-06-30 10y
`0.0383818` → `0.0391278` (7.5 bp); 2026-08-26 10y `0.0368203` →
`0.0375066` (6.9 bp); 2020-03-31 0.25y `0.0025384` → `0.0025416` (0.03 bp).

### The empirical check, kept for the record

Before the definition was available, 5- and 10-year par yields were priced
off the zero curve under each convention (semi-annual coupons) and compared
with the Bank of Canada's own benchmark yields (Valet
`bond_yields_benchmark`) on the same day:

| date | T | benchmark % | par if annual | par if continuous | annual − bm (bp) | continuous − bm (bp) |
|---|---|---|---|---|---|---|
| 2005-06-30 | 10 | 3.74 | 3.739 | 3.808 | −0.1 | 6.8 |
| 2010-06-30 | 10 | 3.08 | 3.083 | 3.130 | 0.3 | 5.0 |
| 2015-06-30 | 10 | 1.68 | 1.739 | 1.754 | 5.9 | 7.4 |
| 2019-06-28 | 10 | 1.46 | 1.478 | 1.489 | 1.8 | 2.9 |
| 2023-06-30 | 10 | 3.26 | 3.236 | 3.290 | −2.4 | 3.0 |
| 2026-08-26 | 10 | 3.66 | 3.599 | 3.663 | −6.1 | 0.3 |
| mean over 12 rows (5y and 10y) | | | | | **0.2** | **4.2** |

**This check did not discriminate between the two conventions**: the
benchmarks are on-the-run coupon bonds, not par bonds, and the ±5–15 bp
scatter of either column is larger than the 4 bp that separates them. The
convention is taken from the stated definition above, not from this table.
