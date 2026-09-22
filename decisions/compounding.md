# Compounding conventions of the zero-curve sources

Inside the package a zero yield `z` at tenor `t` means `DF(t) = (1 + z)^(-t)`
— annual compounding (PLAN.md, Conventions). Each zero-curve loader reads
the source's stated convention from the source's own documentation, records
it here with the quote, and converts once, in `parse`. Par yields (US, JP,
FR) are quoted with the country's coupon frequency and are not converted
(their sources' statements are in "Par yields" below, Session 1 part B).

| Country | Source | Stated convention | Conversion in the loader | Recorded in step |
|---|---|---|---|---|
| GB | Bank of England, nominal government spot curve (`glcnominalmonthedata.zip`) | **Continuously compounded, quoted on an annual basis** | `z = exp(r) − 1` | 1.2 |
| DE | Deutsche Bundesbank, Svensson parameters for listed Federal securities (`BBSIS`) | **Annually (discretely) compounded** spot rates | none | 1.3 |
| CA | Bank of Canada, zero-coupon yield curve (`lookup_yield_curve.php`, decimals) | **Continuously compounded** zero rates | `z = exp(r) − 1` | 1.5 (Session 1 part A fix, issue #8) |

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

## Par yields

Written 2026-09-22 (Session 1 part B, amendment 2) before the bootstrap in step
1.9 was built. Each par source's own statement of how its series is quoted,
and the conversion the bootstrap makes from it. Inside the package a par
yield stays as quoted (decimal, the country's coupon frequency
`config.coupon_frequency`); the bootstrap turns it into an annually
compounded zero via the discount factors (`DF_k = (1 − (c/f) Σ DF_j) /
(1 + c/f)`, `z = DF^(−1/t) − 1`), so at the first coupon date
`z = (1 + c/f)^f − 1`.

| Country | Series | Stated quotation | Coupon frequency used | What the series is |
|---|---|---|---|---|
| US | FRED `DGS*` = Treasury par yield curve rates (H.15) | **Bond-equivalent yield, semiannual coupon, par yield curve** | 2 | a par curve by construction (fitted to on-the-run bid quotes) |
| FR | Banque de France `FM.D.FR.EUR.FR2.BB.FRMOYTEC<n>.HSTA` (CNO-TEC n) | **Taux de rendement actuariel annuel** of a fictitious n-year OAT, linear interpolation between the annual actuarial yields of the two bracketing OATs | 1 | yields to maturity of two actual bonds, interpolated; treated as a par yield |
| JP | MOF "Interest Rate" (JGB constant-maturity yields) | **Semiannual compound interest rate on a constant maturity basis**, from a cubic-spline yield curve through yields to maturity of selected JGBs | 2 | yields to maturity of actual bonds on a spline; treated as a par yield |

### US — Treasury par yield curve (FRED DGS series)

FRED's series notes point to the H.15 release and Treasury's yield-curve
methodology. Treasury, *Interest Rates — Frequently Asked Questions*
(https://home.treasury.gov/policy-issues/financing-the-government/interest-rate-statistics/interest-rates-frequently-asked-questions,
read 2026-09-22):

> CMT yields are read directly from the Treasury's daily par yield curve
> and represent "bond equivalent yields" for securities that pay semiannual
> interest, which are expressed on a simple annualized basis.

> The par yield curve is based on securities that pay interest on a
> semiannual basis and the yields are "bond-equivalent" yields.

> All yields on the par yield curve are on a bond-equivalent basis.
> Therefore, the yields at any point on the par yield curve are consistent
> with a semiannual coupon security with that amount of time remaining to
> maturity.

Treasury, *Treasury Yield Curve Methodology* (revised 2025-02-18): "The
Treasury's official yield curve is a par yield curve derived using a
monotone convex method. Our inputs are indicative, bid-side market price
quotations … for the most recently auctioned securities". The bills'
inputs are "bid discount rates corresponding to their bond equivalent
yields". So `DGS<n>` is the semiannual bond-equivalent par yield;
`coupon_frequency.US = 2`, no conversion before the bootstrap. The
0.25-year point is a bill's bond-equivalent yield, not a coupon bond; it
is off the semiannual coupon grid (Session 1 part B decision issue).

### FR — Banque de France CNO-TEC (Taux de l'Échéance Constante)

Banque de France, *Note technique sur les indices CNO-TEC*, revised
2020-05-07 (https://www.banque-france.fr/system/files/2024-07/TEC%20Note%20Technique%20-%20Version%20r%C3%A9vis%C3%A9e%20FR%2020200507.pdf,
downloaded 2026-09-22), §1.1 Définition:

> L'indice quotidien CNO-TEC n, Taux de l'Échéance Constante n ans, pour n
> variant de 1 à 30, est le taux de rendement actuariel d'une valeur du
> Trésor fictive dont la durée de vie serait à chaque instant égale à n
> années. Ce taux est obtenu par interpolation linéaire entre les taux de
> rendement actuariels annuels des 2 valeurs du Trésor qui encadrent au
> plus proche la maturité n années théorique.

§1.2: the reference securities are "OAT à taux fixe, in fine et à intérêts
annuels" (TEC 1 may use a BTF, for which "il est retenu le taux actuariel
équivalent"); the Banque de France "extrait un taux actuariel de la
cotation milieu de fourchette … par la méthode … décrite dans la notice
'Normes applicables au marché domestique obligataire français' en date de
Juin 1992" — the CNO actuarial yield, annual compounding on actual days
(`Dj − Di` "correspond au nombre de jours réels"). So TEC n is an
**annually compounded yield to maturity**; `coupon_frequency.FR = 1`,
no conversion before the bootstrap. (The Webstat metadata for the series
gives only "Constant maturity rate", unit PC, source EUXT/Euronext, first
observation 2004-11-03; the definition is in the note above.)

### JP — MOF JGB constant-maturity interest rates

MOF, *Interest Rate (Q & A)*
(https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/qa.htm,
read 2026-09-22):

> What kind of interest rate is released by the Ministry of Finance? — The
> semiannual compound interest rate on a constant maturity basis calculated
> on prevailing prices of fixed income JGBs in the secondary market at the
> market closing time (3pm) is released.

> What is the yield curve? — It is a curve which is plotted by connecting
> the points which represent the relationship between yields to maturity
> and remaining maturity of JGBs.

> How are the prevailing market yields of each JGB calculated? — They are
> calculated by using the average price of "Reference Statistical Prices
> (Yields) for OTC Bond Transactions" provided by Japan Securities Dealers
> Association (JSDA). Note that the prevailing market yields of before
> July, 2002 are calculated by using the following data. Sep 24, 1974 ~
> Nov 30, 1998: Tokyo Stock Exchange, Close Price or Special Quotation;
> Dec 1, 1998 ~ Jul 31, 2002: JSDA, The price of "Standard Quotation".

MOF, *Calculation method of interest rate (Outline)* (`outline-e.pdf`,
linked from the Q & A): grids at one-year intervals from 1 to 40 years;
for each grid the on-the-run issue of the class (2-, 5-, 10-, 20-, 30-,
40-year JGBs) plus the issues whose remaining maturity is nearest to the
grid on either side; "The yield curve is formed by interpolating through a
cubic spline function, utilizing the prevailing market yields of securities
selected … as contact points"; the constant-maturity rates are read off it.

**Compound or simple, and whether it changes by date.** The source states
*semiannual compound* with no date qualification, and the yields are
computed by MOF from *prices*, so the JSDA convention of quoting OTC
reference yields as simple yields does not enter. The only dated changes
the source states are the price providers (TSE to 1998-11-30, JSDA
standard quotation to 2002-07-31, JSDA reference statistical prices
after). Nothing in the source says the pre-1986 (or any other) portion of
the historical file is on a different basis; review 1.4's open question
is answered by that statement, and by nothing else — there is no separate
document for the 1974–1985 data. `coupon_frequency.JP = 2`, no
conversion before the bootstrap.

### TEC and MOF yields are yields to maturity treated as par yields

A par yield is the coupon at which a bond of that maturity prices at 100.
TEC n and the MOF constant-maturity rates are **yields to maturity of
actual bonds** (interpolated or splined to the grid maturity). A bond's
yield to maturity equals the par yield of its maturity only when its
coupon equals that par yield; otherwise the yield to maturity is a
coupon-weighted average of the zero rates along its cash flows (the
"coupon effect"): a high-coupon bond has more weight on the shorter,
lower zeros in an upward-sloping curve and so a yield to maturity *below*
the par yield, and the reverse for a low coupon. The bootstrap treats the
quoted yield as the par yield, i.e. it prices a bond with coupon equal to
the quote at exactly 100.

Size of the approximation, measured on the bootstrapped curves of this
repo (a 10-year bond priced off the zero curve with a coupon that differs
from the 10-year par yield, then its yield to maturity compared with the
par yield; bp):

| Country | Date | 10y par | 2s10s slope | coupon = par − 200 bp | − 100 bp | + 100 bp | + 200 bp |
|---|---|---|---|---|---|---|---|
| FR | 2010-06-30 | 3.085% | 230 bp | +8.1 | +3.8 | −3.4 | −6.6 |
| FR | 2021-12-31 | 0.100% | 80 bp | +3.8 | +1.8 | −1.6 | −3.0 |
| FR | 2026-08-31 | 4.114% | 104 bp | +4.2 | +2.0 | −1.8 | −3.4 |
| JP | 2010-06-30 | 1.095% | 95 bp | +5.4 | +2.6 | −2.3 | −4.4 |
| JP | 2021-12-31 | 0.089% | 18 bp | +1.4 | +0.7 | −0.6 | −1.1 |
| JP | 2026-08-31 | 2.943% | 120 bp | +5.0 | +2.4 | −2.2 | −4.1 |
| US | 2010-06-30 | 2.970% | 236 bp | +8.3 | +3.9 | −3.6 | −6.8 |

So the error is of order **2–4 bp per 100 bp of coupon–par difference at
10 years** in a curve with a 100–230 bp 2s10s slope, and proportional to
both. The TEC uses the two OATs nearest the maturity, whose coupons are
close to current yields when the curve has not moved far since issue
(2004–2021: coupons above yields in a falling-rate period, so the TEC
reads slightly below the true par yield); the MOF grid uses on-the-run
and nearest-maturity issues, same argument. The approximation is of the
same nature for both, is not corrected anywhere in the package, and is
the reason `data/checks/par_zero_gap.csv` should be read as par-to-zero
*of the quoted series*, not of a true par curve. The US series has no such
approximation: Treasury publishes a par curve.

### GSW check curve (Session 1 part B, amendment 3)

The Federal Reserve's `feds200628.csv` header states, for the series
used: "Zero-coupon yield, Continuously Compounded, SVENYXX". The loader
`loaders/gsw.py` asserts that line is present and converts with
`exp(z) − 1` once. Used only for `data/checks/us_zero_vs_gsw.csv`.
