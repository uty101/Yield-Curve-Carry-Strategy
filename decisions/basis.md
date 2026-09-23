# Why the hedged return needs no FX series, and what that leaves out

Written 2026-09-23, step 4.3.

## The derivation, in two lines

Buy the foreign bond with one unit of foreign currency borrowed at
`r_short_local`, and sell the proceeds forward into the base currency. Under
covered interest parity the one-month forward premium on the foreign currency
is `(r_short_base − r_short_local)/12`. So the position returns, in base
currency,

```
r_local + (r_short_base − r_short_local)/12          (bond, plus the forward premium)
       − r_short_base/12                              (financing in the base currency)
=  r_local − r_short_local/12
=  r_excess_local
```

**The FX-hedged excess return in the base currency is the local excess
return.** `r_hedged = r_excess_local` exactly, and no exchange-rate series
enters it. That is why `test_hedged_is_local_excess_return` asserts that
`r_hedged` does not move when the FX series is changed.

`hedge_carry = (r_short_base − r_short_local)/12` is kept in
`returns.parquet` as a **diagnostic only**. It is the forward premium, the
size of what the hedge is paying or earning, and by construction
`r_local + hedge_carry − r_short_base/12 == r_hedged`
(`test_cip_identity`, to 1e-14 on 1,000 rows). Nothing reads it.

The unhedged return keeps the FX exposure and finances in the base currency:

```
r_unhedged = r_local + (ln S_{t+1} − ln S_t) − r_short_base/12
```

with `S` in units of base currency per unit of foreign currency, so a foreign
appreciation is a gain. For the base country itself
`r_hedged == r_unhedged == r_excess_local` and `fx_return == hedge_carry == 0`.

## What the derivation omits: the cross-currency basis

Covered interest parity has not held since 2008. The forward premium is not
exactly `(r_short_base − r_short_local)/12`; it differs by the **cross-currency
basis**, the price of borrowing dollars through the FX swap market rather than
directly. Where the basis is negative — as it has been for JPY and EUR through
most of the post-crisis period — a dollar investor hedging a foreign bond
**earns** it and a foreign investor hedging a dollar bond **pays** it.

So `r_hedged = r_excess_local` is right to the basis and no further. The error
is a level shift on each currency's hedged return, of one sign, concentrated
in stress periods and at quarter and year ends.

## The probe: the basis is not measured here

The plan requires this step to try the free candidates and record what it
found. Probed 2026-09-23:

| source | what was checked | result |
|---|---|---|
| FRED | tag search `currency` + `swaps` (6 series), tag `swaps` (75 series), category 32299 "Interest Rate Swaps" (32 series) | **no basis series.** Everything under those tags is Fed swap-line balance-sheet data (`ROWSLAQ027S`, `BOGZ1FL713090003Q` and the like) or domestic interest-rate swaps |
| BIS Data Portal / Statistics Explorer | the full topic list at `data.bis.org/topics` | **no basis topic.** The portal has OTC derivatives *outstandings* and the Triennial Survey *turnover*, neither of which is a price series; `WS_CBPOL` and `XRU` are already used here |
| ECB Data Portal | dataset list and search | **inconclusive, treated as no.** `data.ecb.europa.eu` returned HTTP 503 on both the dataset list and the search endpoint on the day of the probe, and the public dataset catalogue reached indirectly names no basis dataset. The EXR dataset it does publish is spot and reference rates |

Published basis series (Bloomberg `EURUSDBS`, `USDJPYBS` and the like, or the
CIP-deviation datasets behind the BIS working papers) are commercial. **The
cross-currency basis is therefore not measured in this project**, and
`data/checks/xccy_basis.csv` is not written.

What that costs, from the brief: the basis runs **20 to 50 bp in stress
periods** for the major pairs, wider at quarter ends. Against a duration-
neutral book whose carry signal is measured in tens of bp per year of
duration, that is not negligible, and it is one-directional rather than
noise. The honest statement for the report is that the hedged returns here
are CIP-implied hedged returns, that they overstate the cost of hedging
foreign bonds back into dollars over 2008–2020 for JPY and EUR, and that the
size of the overstatement is of the order of the basis and is not estimated.

If a series is ever obtained, the step that adds it writes the CIP error by
year and currency pair into `data/checks/xccy_basis.csv` and a table here, and
nothing else in the pipeline needs to change: the basis enters as an additive
adjustment to `hedge_carry` and hence to `r_hedged`.

## Related

- `decisions/short_anchor.md` — what `r_short_local` and `r_short_base` are,
  the EUR splice, and the JP policy-rate gap fill.
- `PLAN.md` → Step 4.3 and its session-4 amendment 3.
- `data/checks/return_coverage.csv` — per country and month, which of
  `r_local`, `r_hedged` and `r_unhedged` exist and why one does not.
