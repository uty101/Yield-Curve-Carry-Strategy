# Compounding conventions of the zero-curve sources

Inside the package a zero yield `z` at tenor `t` means `DF(t) = (1 + z)^(-t)`
— annual compounding (PLAN.md, Conventions). Each zero-curve loader reads
the source's stated convention from the source's own documentation, records
it here with the quote, and converts once, in `parse`. Par yields (US, JP,
FR) are quoted with the country's coupon frequency and are not converted.

| Country | Source | Stated convention | Conversion in the loader | Recorded in step |
|---|---|---|---|---|
| GB | Bank of England, nominal government spot curve (`glcnominalmonthedata.zip`) | **Continuously compounded, quoted on an annual basis** | `z = exp(r) − 1` | 1.2 |

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
