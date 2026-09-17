# France and Italy: national curves only; Italy dropped

Decided 2026-09-16 (session 1 review, owner). Recorded so the choice can be
reversed later with the facts that drove it in front of whoever reverses it.

## The rule

A country in `countries` is represented by **its own** government curve. The
ECB Data Portal's euro-area composite curves — the AAA-rated spot curve
(`YC.B.U2.EUR.4F.G_N_A.SV_C_YM.*`) and the all-issuers spot curve
(`YC.B.U2.EUR.4F.G_N_C.SV_C_YM.*`) — are **not labelled FR or IT anywhere in
this repo**. Neither is a national curve: the AAA curve is a changing-
composition aggregate of AAA sovereigns (Germany, the Netherlands and others
as their ratings move), the all-issuers curve a changing-composition aggregate
of every euro sovereign. Carry on such a composite is an average across
issuers with different funding markets, and a cross-country carry strategy
that ranks a composite against real national curves is ranking a portfolio
against its own components.

## France — Banque de France TEC, `par`

Source: Banque de France Webstat, "Taux de l'Echéance Constante" (TEC), the
CNO constant-maturity OAT yields, daily, at 1, 2, 3, 5, 7, 10, 15, 20, 25 and
30 years. Dataset ids `fm-d-fr-eur-fr2-bb-frmoytec{N}-hsta`, N in
{1,2,3,5,7,10,15,20,25,30}. `curve_type = par` (TEC is the yield of a
hypothetical par OAT of constant maturity, interpolated between the two
nearest OATs), coupon frequency 1, bootstrapped to zero in step 1.9 like the
other par curves.

The catalog is open but records need an API key. The owner supplies it as the
environment variable **`BDF_API_KEY`**. The loader reads it from the
environment and from nowhere else; it is never written to a file in this
repo, `.env` is git-ignored, and the France tests run on a committed fixture
(`tests/fixtures/`) so the suite never needs the key. Without a valid key the
API returns **HTTP 200 with zero records**, not an error, so the fetch
asserts on a non-empty body and refuses to write an empty file to
`data/raw/`.

**Found in step 1.6 (2026-09-17):** the per-tenor catalog datasets above are
empty shells (`has_records: false`); the observations live in the Webstat
catalog dataset `observations`, filtered by series key, e.g.
`GET https://webstat.banque-france.fr/api/explore/v2.1/catalog/datasets/observations/exports/csv?where=series_key="FM.D.FR.EUR.FR2.BB.FRMOYTEC10.HSTA"`
with the key in the `Authorization: Apikey` header (that dataset 404s without
a key). Export format: semicolon csv with `series_key, time_period, obs_value,
obs_status` (status `M` rows carry no value: non-trading days). **First
observation 2004-11-03 for TEC 1–20, 2006-10-24 for TEC 25 and 30**, daily to
the present; so `sample_full_start` is no earlier than 2004-11-30, recorded in
`data/checks/coverage.csv`.

## Italy — dropped

No national source reachable by a plain HTTP GET was located:

- Banca d'Italia's statistical database (`infostat.bancaditalia.it`) is a
  JavaScript application; no CSV endpoint was found in the probe.
- The MEF / Dipartimento del Tesoro pages are HTML tables, not a download.
- The only country-specific Italian yield series reachable is the ECB IRS
  10-year convergence rate (`IRS.M.IT.L.L40.CI.0000.EUR.N.Z`, monthly,
  1991-03 onward): a single tenor, so no curve, no carry-per-duration across
  buckets, no PCA.

`countries` in `config.toml` is therefore `["US","GB","DE","JP","CA","FR"]`.
The IT coupon frequency is left commented in `config.toml` for the day a
national source appears.

## What the all-issuers proxy would have done to the sample if Italy were kept

Recorded from the probe so this is a number, not a memory:

| Fact | Value | Where from |
|---|---|---|
| ECB all-issuers curve first date | 2004-09-06 | probe, `firstNObservations=1` |
| ECB all-issuers 10y, 2026-09-09 | 3.858% | probe |
| ECB IRS Italy 10y, 2026-08 (monthly) | 3.986% | probe |
| ECB AAA 10y, 2026-09-09 | 3.427% | probe |
| ECB IRS France 10y, 2026-08 (monthly) | 4.000% | probe |

So on the latest observations the all-issuers composite sits about **13 bp
below** Italy's own 10-year and about 43 bp above the AAA curve — an "Italy"
bucket built from it would have carried a euro-area-average yield, not an
Italian one, and the carry signal for that bucket would have been a blend of
Germany, France, Italy, Spain and the rest with Italy's own spread diluted.

Effect on the windows:

- **`strategy_start` (5 of N countries with all tenors to 10 years)** would
  have been unchanged. US, GB, JP and CA reach 10 years well before 1997, and
  Germany's Svensson parameters start 1997-08; the fifth country is Germany
  either way, so the composite's 2004-09 start does not bind.
- **`sample_full_start` (all countries present)** would have been
  `max(France TEC start, 2004-09-30)`; with Italy dropped it is the France
  TEC start alone (unknown until fetched). If the TEC series predate 2004, the
  6-country window is longer than the 7-country window would have been.
- **Cross-section**: 6 countries × 8 tenors = 48 buckets a month at full
  coverage, thirds of 16, instead of 56 and thirds of 18–19.

## To reverse

1. Find a national Italian curve (BTP benchmark yields at ≥ 6 tenors, daily
   or month-end), probe it, add it to `decisions/sources.md`.
2. Add `"IT"` back to `countries`, uncomment `IT = 1`, write `loaders/it.py`
   with its fixture and unit test, rerun 1.8 and 1.9.
3. Note the change here with the date, and log the first strategy run with
   Italy as its own row in `reports/specifications.csv`.
