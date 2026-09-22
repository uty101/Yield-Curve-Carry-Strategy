# Source reachability probe — session 1 (2026-09-16, re-run after the session-1 corrections)

Fetched with `requests` from this machine, one GET per URL, browser User-Agent. No data was written to `data/`.
Bytes are the response body. Span is the first and last date token seen in the body (blank for zips / html).

| Group | Source | Status | Bytes | Span | URL |
|---|---|---|---|---|---|
| US curve | FRED DGS1 | 200 | 268,333 | 1962-01-02 → 2026-09-14 | `https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS1` |
| US curve | FRED DGS10 | 200 | 268,711 | 1962-01-02 → 2026-09-14 | `https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10` |
| US curve | FRED DGS20 | 200 | 261,980 | 1962-01-02 → 2026-09-14 | `https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS20` |
| US curve | FRED DGS30 | 200 | 206,305 | 1977-02-15 → 2026-09-14 | `https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS30` |
| UK curve | BoE nominal month-end archive (zip, 3 xlsx) | 200 | 2,563,251 |  | `https://www.bankofengland.co.uk/-/media/boe/files/statistics/yield-curves/glcnominalmonthedata.zip` |
| UK curve | BoE latest (zip, current-month daily) — NOT USED | 200 | 323,736 |  | `https://www.bankofengland.co.uk/-/media/boe/files/statistics/yield-curves/latest-yield-curve-data.zip` |
| DE curve | Bundesbank Svensson B0 | 200 | 252,143 | 1997-08-01 → 2026-09-16 | `https://api.statistiken.bundesbank.de/rest/download/BBSIS/D.I.ZST.B0.EUR.S1311.B.A604._Z.R.A.A._Z._Z.A?format=csv&lang=en` |
| DE curve | Bundesbank Svensson B1 | 200 | 258,640 | 1997-08-01 → 2026-09-16 | `https://api.statistiken.bundesbank.de/rest/download/BBSIS/D.I.ZST.B1.EUR.S1311.B.A604._Z.R.A.A._Z._Z.A?format=csv&lang=en` |
| DE curve | Bundesbank Svensson B2 | 200 | 259,061 | 1997-08-01 → 2026-09-16 | `https://api.statistiken.bundesbank.de/rest/download/BBSIS/D.I.ZST.B2.EUR.S1311.B.A604._Z.R.A.A._Z._Z.A?format=csv&lang=en` |
| DE curve | Bundesbank Svensson B3 | 200 | 258,639 | 1997-08-01 → 2026-09-16 | `https://api.statistiken.bundesbank.de/rest/download/BBSIS/D.I.ZST.B3.EUR.S1311.B.A604._Z.R.A.A._Z._Z.A?format=csv&lang=en` |
| DE curve | Bundesbank Svensson T1 | 200 | 252,674 | 1997-08-01 → 2026-09-16 | `https://api.statistiken.bundesbank.de/rest/download/BBSIS/D.I.ZST.T1.EUR.S1311.B.A604._Z.R.A.A._Z._Z.A?format=csv&lang=en` |
| DE curve | Bundesbank Svensson T2 | 200 | 252,947 | 1997-08-01 → 2026-09-16 | `https://api.statistiken.bundesbank.de/rest/download/BBSIS/D.I.ZST.T2.EUR.S1311.B.A604._Z.R.A.A._Z._Z.A?format=csv&lang=en` |
| DE curve | Bundesbank published 10y (check series) | 200 | 230,812 | 1997-08-01 → 2026-09-16 | `https://api.statistiken.bundesbank.de/rest/download/BBSIS/D.I.ZST.ZI.EUR.S1311.B.A604.R10XX.R.A.A._Z._Z.A?format=csv&lang=en` |
| JP curve | MOF JGB historical (all) | 200 | 1,193,668 | 1974/9/24 → 2026/8/31 | `https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/historical/jgbcme_all.csv` |
| JP curve | MOF JGB current year | 200 | 1,332 | 2026/9/1 → 2026/9/15 | `https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/jgbcme.csv` |
| JP curve | MOF kickoff URL (moved) | 404 | 20,481 |  | `https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/jgbcme_all.csv` |
| CA curve | BoC zero-coupon curve (GET form -> csv) | 200 | 32,135 | 2026-07-31 → 2026-08-26 | `https://www.bankofcanada.ca/stats/results/csv?lookupPage=lookup_yield_curve.php&startRange=1986-01-01&searchRange=&dFrom=2026-08-01&dTo=2026-08-31&submit=Submit` |
| CA curve | BoC Valet benchmark yields (fallback) | 200 | 407,583 | 2001-01-02 → 2026-09-15 | `https://www.bankofcanada.ca/valet/observations/group/bond_yields_benchmark/csv` |
| FR curve | Banque de France Webstat TEC 10y daily (catalog) | 200 | 6,802 |  | `https://webstat.banque-france.fr/api/explore/v2.1/catalog/datasets/fm-d-fr-eur-fr2-bb-frmoytec10-hsta` |
| FR curve | Banque de France Webstat TEC 10y records (no key) | 200 | 33 |  | `https://webstat.banque-france.fr/api/explore/v2.1/catalog/datasets/fm-d-fr-eur-fr2-bb-frmoytec10-hsta/records?limit=3` |
| Euro composite | ECB euro AAA spot 10y — NOT USED | 200 | 3,159,845 | 2004-09-06 → 2026-09-15 | `https://data-api.ecb.europa.eu/service/data/YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y?format=csvdata` |
| FR check | ECB IRS France 10y (monthly, convergence rate) | 200 | 175,502 | 1986-01 → 2026-08 | `https://data-api.ecb.europa.eu/service/data/IRS/M.FR.L.L40.CI.0000.EUR.N.Z?format=csvdata` |
| Euro composite | ECB euro all-issuers spot 10y — NOT USED | 200 | 3,192,373 | 2004-09-06 → 2026-09-15 | `https://data-api.ecb.europa.eu/service/data/YC/B.U2.EUR.4F.G_N_C.SV_C_YM.SR_10Y?format=csvdata` |
| IT check (dropped) | ECB IRS Italy 10y (monthly, convergence rate) | 200 | 153,283 | 1991-03 → 2026-08 | `https://data-api.ecb.europa.eu/service/data/IRS/M.IT.L.L40.CI.0000.EUR.N.Z?format=csvdata` |
| IT curve (dropped) | Banca d'Italia BDS (national) | 200 | 121,343 |  | `https://infostat.bancaditalia.it/inquiry/home?spyglass/taxo:CUBESET=/PUBBL_00/PUBBL_00_02_00&ep:LC=EN` |
| Short robustness | FRED IR3TIB01USM156N (USD) | 200 | 12,040 | 1964-06-01 → 2026-08-01 | `https://fred.stlouisfed.org/graph/fredgraph.csv?id=IR3TIB01USM156N` |
| Short — NOT USED | FRED TB3MS (USD T-bill) | 200 | 17,849 | 1934-01-01 → 2026-08-01 | `https://fred.stlouisfed.org/graph/fredgraph.csv?id=TB3MS` |
| Short robustness | FRED IR3TIB01GBM156N (GBP) | 200 | 15,956 | 1957-01-01 → 2026-01-01 | `https://fred.stlouisfed.org/graph/fredgraph.csv?id=IR3TIB01GBM156N` |
| Short robustness | FRED IR3TIB01JPM156N (JPY) | 200 | 5,621 | 2002-04-01 → 2026-07-01 | `https://fred.stlouisfed.org/graph/fredgraph.csv?id=IR3TIB01JPM156N` |
| Short robustness | FRED IR3TIB01CAM156N (CAD) | 200 | 19,641 | 1956-01-01 → 2026-08-01 | `https://fred.stlouisfed.org/graph/fredgraph.csv?id=IR3TIB01CAM156N` |
| Short robustness | FRED IR3TIB01EZM156N (EUR) | 200 | 11,669 | 1994-01-01 → 2026-01-01 | `https://fred.stlouisfed.org/graph/fredgraph.csv?id=IR3TIB01EZM156N` |
| Funding (default) | BIS CBPOL US | 200 | 225,967 | 1954-07 → 2026-08 | `https://stats.bis.org/api/v2/data/dataflow/BIS/WS_CBPOL/1.0/M.US?format=csv` |
| Funding (default) | BIS CBPOL GB | 200 | 367,939 | 1946-01 → 2026-08 | `https://stats.bis.org/api/v2/data/dataflow/BIS/WS_CBPOL/1.0/M.GB?format=csv` |
| Funding (default) | BIS CBPOL JP | 200 | 1,979,669 | 1946-01 → 2026-08 | `https://stats.bis.org/api/v2/data/dataflow/BIS/WS_CBPOL/1.0/M.JP?format=csv` |
| Funding (default) | BIS CBPOL CA | 200 | 495,005 | 1960-07 → 2026-08 | `https://stats.bis.org/api/v2/data/dataflow/BIS/WS_CBPOL/1.0/M.CA?format=csv` |
| Funding (default) | BIS CBPOL XM (euro area) | 200 | 192,803 | 1999-01 → 2026-08 | `https://stats.bis.org/api/v2/data/dataflow/BIS/WS_CBPOL/1.0/M.XM?format=csv` |
| FX (default) | FRED DEXUSUK (USD per GBP, daily) | 200 | 258,181 | 1971-01-04 → 2026-09-11 | `https://fred.stlouisfed.org/graph/fredgraph.csv?id=DEXUSUK` |
| FX (default) | FRED DEXJPUS (JPY per USD, daily) | 200 | 256,631 | 1971-01-04 → 2026-09-11 | `https://fred.stlouisfed.org/graph/fredgraph.csv?id=DEXJPUS` |
| FX (default) | FRED DEXCAUS (CAD per USD, daily) | 200 | 258,217 | 1971-01-04 → 2026-09-11 | `https://fred.stlouisfed.org/graph/fredgraph.csv?id=DEXCAUS` |
| FX (default) | FRED DEXUSEU (USD per EUR, daily) | 200 | 128,395 | 1999-01-04 → 2026-09-11 | `https://fred.stlouisfed.org/graph/fredgraph.csv?id=DEXUSEU` |
| FX monthly avg — NOT USED | FRED EXUSUK | 200 | 12,048 | 1971-01-01 → 2026-08-01 | `https://fred.stlouisfed.org/graph/fredgraph.csv?id=EXUSUK` |
| FX monthly avg — NOT USED | FRED EXJPUS | 200 | 13,311 | 1971-01-01 → 2026-08-01 | `https://fred.stlouisfed.org/graph/fredgraph.csv?id=EXJPUS` |
| FX monthly avg — NOT USED | FRED EXCAUS | 200 | 12,048 | 1971-01-01 → 2026-08-01 | `https://fred.stlouisfed.org/graph/fredgraph.csv?id=EXCAUS` |
| FX monthly avg — NOT USED | FRED EXUSEU | 200 | 6,000 | 1999-01-01 → 2026-08-01 | `https://fred.stlouisfed.org/graph/fredgraph.csv?id=EXUSEU` |

## First 3 lines of each response

### US curve — FRED DGS1
_par, daily; same pattern DGS2 DGS3 DGS5 DGS7 DGS10 DGS20 DGS30_
```
observation_date,DGS1
1962-01-02,3.22
1962-01-03,3.24
```

### US curve — FRED DGS10
```
observation_date,DGS10
1962-01-02,4.06
1962-01-03,4.03
```

### US curve — FRED DGS20
_gap 1987-1993_
```
observation_date,DGS20
1962-01-02,4.07
1962-01-03,4.07
```

### US curve — FRED DGS30
_gap 2002-2006 — **enforced by the loader, not present in the file** (issue #7, decided 2026-09-22): Treasury discontinued the 30-year constant maturity on 2002-02-18 and reinstated it on 2006-02-09, and for the interval FRED's DGS30 carries Treasury's factor-based estimates from the 20-year (0 missing days in 2002–2006 in the file fetched 2026-09-17). `loaders/us.py` masks 2002-02-19..2006-02-08 (`DGS30_EXTRAPOLATED`) as extrapolation under rule 13; coverage shows `2002-03..2006-01`, 47 months._
```
observation_date,DGS30
1977-02-15,7.70
1977-02-16,7.67
```

### UK curve — BoE nominal month-end archive (zip, 3 xlsx)
_zero (spot); 1970-2015, 2016-2024, 2025-present_
```
[zip] GLC Nominal month end data_1970 to 2015.xlsx (2746456 B)
[zip] GLC Nominal month end data_2016 to 2024.xlsx (1778223 B)
[zip] GLC Nominal month end data_2025 to present.xlsx (98509 B)
```

### UK curve — BoE latest (zip, current-month daily) — NOT USED
_session-1 correction 4: the month-end archive covers everything up to strategy_end_
```
[zip] GLC Inflation daily data current month.xlsx (324005 B)
[zip] GLC Nominal daily data current month.xlsx (213419 B)
[zip] GLC Real daily data current month.xlsx (322107 B)
```

### DE curve — Bundesbank Svensson B0
_daily, 1997-08 onward; B1 B2 B3 T1 T2 same pattern_
```
"",BBSIS.D.I.ZST.B0.EUR.S1311.B.A604._Z.R.A.A._Z._Z.A,BBSIS.D.I.ZST.B0.EUR.S1311.B.A604._Z.R.A.A._Z._Z.A_FLAGS
"",Term structure of interest rates on listed Federalsecurities (method by Svensson) / Parameter Beta0 /daily 
Comment (in english),,
```

### DE curve — Bundesbank Svensson B1
```
"",BBSIS.D.I.ZST.B1.EUR.S1311.B.A604._Z.R.A.A._Z._Z.A,BBSIS.D.I.ZST.B1.EUR.S1311.B.A604._Z.R.A.A._Z._Z.A_FLAGS
"",Term structure of interest rates on listed Federalsecurities (method by Svensson) / Parameter Beta1 /daily 
Comment (in english),,
```

### DE curve — Bundesbank Svensson B2
```
"",BBSIS.D.I.ZST.B2.EUR.S1311.B.A604._Z.R.A.A._Z._Z.A,BBSIS.D.I.ZST.B2.EUR.S1311.B.A604._Z.R.A.A._Z._Z.A_FLAGS
"",Term structure of interest rates on listed Federalsecurities (method by Svensson) / Parameter Beta2 /daily 
Comment (in english),,
```

### DE curve — Bundesbank Svensson B3
```
"",BBSIS.D.I.ZST.B3.EUR.S1311.B.A604._Z.R.A.A._Z._Z.A,BBSIS.D.I.ZST.B3.EUR.S1311.B.A604._Z.R.A.A._Z._Z.A_FLAGS
"",Term structure of interest rates on listed Federalsecurities (method by Svensson) / Parameter Beta3 /daily 
Comment (in english),,
```

### DE curve — Bundesbank Svensson T1
```
"",BBSIS.D.I.ZST.T1.EUR.S1311.B.A604._Z.R.A.A._Z._Z.A,BBSIS.D.I.ZST.T1.EUR.S1311.B.A604._Z.R.A.A._Z._Z.A_FLAGS
"",Term structure of interest rates on listed Federalsecurities (method by Svensson) / Parameter Tau1 /daily d
Comment (in english),,
```

### DE curve — Bundesbank Svensson T2
```
"",BBSIS.D.I.ZST.T2.EUR.S1311.B.A604._Z.R.A.A._Z._Z.A,BBSIS.D.I.ZST.T2.EUR.S1311.B.A604._Z.R.A.A._Z._Z.A_FLAGS
"",Term structure of interest rates on listed Federalsecurities (method by Svensson) / Parameter Tau2 /daily d
Comment (in english),,
```

### DE curve — Bundesbank published 10y (check series)
_for the 1 bp reconstruction test in 1.3_
```
"",BBSIS.D.I.ZST.ZI.EUR.S1311.B.A604.R10XX.R.A.A._Z._Z.A,BBSIS.D.I.ZST.ZI.EUR.S1311.B.A604.R10XX.R.A.A._Z._Z.A
"",Term structure of interest rates on listed Federal securities (method by Svensson) / residual maturity of 1
Comment (in english),,
```

### JP curve — MOF JGB historical (all)
_par (benchmark), daily 1974-09 onward; kickoff URL without /historical/ is 404_
```
Interest Rate,,,,,,,,,,,,,,,(Unit : %)
Date,1Y,2Y,3Y,4Y,5Y,6Y,7Y,8Y,9Y,10Y,15Y,20Y,25Y,30Y,40Y
1974/9/24,10.327,9.362,8.83,8.515,8.348,8.29,8.24,8.121,8.127,-,-,-,-,-,-
```

### JP curve — MOF JGB current year
```
Interest Rate (September 2026),,,,,,,,,,,,,,,(Unit : %)
Date,1Y,2Y,3Y,4Y,5Y,6Y,7Y,8Y,9Y,10Y,15Y,20Y,25Y,30Y,40Y
2026/9/1,1.527,1.802,1.952,2.14,2.28,2.411,2.559,2.718,2.848,2.987,3.544,3.859,4.143,4.131,4.145
```

### JP curve — MOF kickoff URL (moved)
_expected 404_
```
<!DOCTYPE html>
<html lang="ja">
<head prefix="og: http://ogp.me/ns# fb: http://ogp.me/ns/fb# article: http://ogp.me/ns/article#">
```

### CA curve — BoC zero-coupon curve (GET form -> csv)
_zero; 0.25..30y in 0.25 steps, DECIMALS already; full file: searchRange=all_
```
Date, ZC025YR, ZC050YR, ZC075YR, ZC100YR, ZC125YR, ZC150YR, ZC175YR, ZC200YR, ZC225YR, ZC250YR, ZC275YR, ZC300
2026-07-31, 0.0226506000, 0.0239074000, 0.0250856000, 0.0262629000, 0.0274360000, 0.0280733000, 0.0286429000, 
2026-08-03, na, na, na, na, na, na, na, na, na, na, na, na, na, na, na, na, na, na, na, na, na, na, na, na, na
```

### CA curve — BoC Valet benchmark yields (fallback)
_par; 2 3 5 7 10 long_
```
"TERMS AND CONDITIONS"
"https://www.bankofcanada.ca/terms/"
"NAME"
```

### FR curve — Banque de France Webstat TEC 10y daily (catalog)
_DEFAULT for FR (par): TEC 1 2 3 5 7 10 15 20 25 30 daily; records need the key in env BDF_API_KEY_
```
{"visibility": "domain", "fields": [], "dataset_id": "fm-d-fr-eur-fr2-bb-frmoytec10-hsta", "dataset_uid": "da_
```

### FR curve — Banque de France Webstat TEC 10y records (no key)
_returns 0 rows without apikey_
```
{"total_count": 0, "results": []}
```

### Euro composite — ECB euro AAA spot 10y — NOT USED
_zero; 2004-09 onward; not a national curve, see decisions/euro_curves.md_
```
KEY,FREQ,REF_AREA,CURRENCY,PROVIDER_FM,INSTRUMENT_FM,PROVIDER_FM_ID,DATA_TYPE_FM,TIME_PERIOD,OBS_VALUE,OBS_STA
YC.B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y,B,U2,EUR,4F,G_N_A,SV_C_YM,SR_10Y,2004-09-06,4.20921992630835,A,F,,,P1D,,E,
YC.B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y,B,U2,EUR,4F,G_N_A,SV_C_YM,SR_10Y,2004-09-07,4.209625926710301,A,F,,,P1D,,E
```

### FR check — ECB IRS France 10y (monthly, convergence rate)
_single tenor, check series only_
```
KEY,FREQ,REF_AREA,IR_TYPE,TR_TYPE,MATURITY_CAT,BS_COUNT_SECTOR,CURRENCY_TRANS,IR_BUS_COV,IR_FV_TYPE,TIME_PERIO
IRS.M.FR.L.L40.CI.0000.EUR.N.Z,M,FR,L,L40,CI,0000,EUR,N,Z,1986-01,10.05,A,F,,,P1M,,A,,,,,,,,,2,,,Long-term int
IRS.M.FR.L.L40.CI.0000.EUR.N.Z,M,FR,L,L40,CI,0000,EUR,N,Z,1986-02,9.81,A,F,,,P1M,,A,,,,,,,,,2,,,Long-term inte
```

### Euro composite — ECB euro all-issuers spot 10y — NOT USED
_zero; 2004-09 onward; not a national curve, Italy dropped, see decisions/euro_curves.md_
```
KEY,FREQ,REF_AREA,CURRENCY,PROVIDER_FM,INSTRUMENT_FM,PROVIDER_FM_ID,DATA_TYPE_FM,TIME_PERIOD,OBS_VALUE,OBS_STA
YC.B.U2.EUR.4F.G_N_C.SV_C_YM.SR_10Y,B,U2,EUR,4F,G_N_C,SV_C_YM,SR_10Y,2004-09-06,4.262767322619997,A,F,,,P1D,,E
YC.B.U2.EUR.4F.G_N_C.SV_C_YM.SR_10Y,B,U2,EUR,4F,G_N_C,SV_C_YM,SR_10Y,2004-09-07,4.26066676103177,A,F,,,P1D,,E,
```

### IT check (dropped) — ECB IRS Italy 10y (monthly, convergence rate)
_single tenor, check series only_
```
KEY,FREQ,REF_AREA,IR_TYPE,TR_TYPE,MATURITY_CAT,BS_COUNT_SECTOR,CURRENCY_TRANS,IR_BUS_COV,IR_FV_TYPE,TIME_PERIO
IRS.M.IT.L.L40.CI.0000.EUR.N.Z,M,IT,L,L40,CI,0000,EUR,N,Z,1991-03,13.767,A,F,,,P1M,,A,,,,,,,,,2,,,Long-term in
IRS.M.IT.L.L40.CI.0000.EUR.N.Z,M,IT,L,L40,CI,0000,EUR,N,Z,1991-04,13.433,A,F,,,P1M,,A,,,,,,,,,2,,,Long-term in
```

### IT curve (dropped) — Banca d'Italia BDS (national)
_JS application, no CSV endpoint located_
```
{"INQUIRYSCOPE":{"environmentId":"LIVE","communityId":"BANKITALIA","defaultCommunityId":"BANKITALIA","contextI
```

### Short robustness — FRED IR3TIB01USM156N (USD)
_robustness column only; OECD 3m interbank, one series type for all 5 currencies_
```
observation_date,IR3TIB01USM156N
1964-06-01,3.86
1964-07-01,3.87
```

### Short — NOT USED — FRED TB3MS (USD T-bill)
_replaced by IR3TIB01USM156N so the robustness column is one series type_
```
observation_date,TB3MS
1934-01-01,0.72
1934-02-01,0.62
```

### Short robustness — FRED IR3TIB01GBM156N (GBP)
_robustness column only; OECD 3m interbank, stops 2026-01_
```
observation_date,IR3TIB01GBM156N
1957-01-01,4.84000
1957-02-01,4.44000
```

### Short robustness — FRED IR3TIB01JPM156N (JPY)
_robustness column only; 2002-04 onward_
```
observation_date,IR3TIB01JPM156N
2002-04-01,0.10000
2002-05-01,0.08000
```

### Short robustness — FRED IR3TIB01CAM156N (CAD)
_robustness column only_
```
observation_date,IR3TIB01CAM156N
1956-01-01,2.940000000
1956-02-01,2.940000000
```

### Short robustness — FRED IR3TIB01EZM156N (EUR)
_robustness column only; stops 2026-01_
```
observation_date,IR3TIB01EZM156N
1994-01-01,6.9100000000000001
1994-02-01,6.8600000000000003
```

### Funding (default) — BIS CBPOL US
_policy rate, monthly; DEFAULT funding rate for all five currencies_
```
FREQ,REF_AREA,UNIT_MEASURE,UNIT_MULT,TIME_FORMAT,COMPILATION,DECIMALS,SOURCE_REF,SUPP_INFO_BREAKS,TITLE,TIME_P
M,US,368,0,,From 19 Dec 1985 onwards: mid-point of the Federal Reserve target rate; from 1 Jul 1954 to 18 Dec 
M,US,368,0,,From 19 Dec 1985 onwards: mid-point of the Federal Reserve target rate; from 1 Jul 1954 to 18 Dec 
```

### Funding (default) — BIS CBPOL GB
```
FREQ,REF_AREA,UNIT_MEASURE,UNIT_MULT,TIME_FORMAT,COMPILATION,DECIMALS,SOURCE_REF,SUPP_INFO_BREAKS,TITLE,TIME_P
M,GB,368,0,,From 3 Aug 2006 onwards: official bank rate; from 6 May 1997 to 2 Aug 2006: repo rate; from 20 Aug
M,GB,368,0,,From 3 Aug 2006 onwards: official bank rate; from 6 May 1997 to 2 Aug 2006: repo rate; from 20 Aug
```

### Funding (default) — BIS CBPOL JP
```
FREQ,REF_AREA,UNIT_MEASURE,UNIT_MULT,TIME_FORMAT,COMPILATION,DECIMALS,SOURCE_REF,SUPP_INFO_BREAKS,TITLE,TIME_P
M,JP,368,0,,"From 17 Jun 2026 onwards: the BOJ encourages the uncollateralized overnight call rate to remain a
M,JP,368,0,,"From 17 Jun 2026 onwards: the BOJ encourages the uncollateralized overnight call rate to remain a
```

### Funding (default) — BIS CBPOL CA
```
FREQ,REF_AREA,UNIT_MEASURE,UNIT_MULT,TIME_FORMAT,COMPILATION,DECIMALS,SOURCE_REF,SUPP_INFO_BREAKS,TITLE,TIME_P
M,CA,368,0,,"From 1 Jun 1994 onwards: Central Bank target, overnight rate; from 27 Jul 1960 to 31 May 1994: of
M,CA,368,0,,"From 1 Jun 1994 onwards: Central Bank target, overnight rate; from 27 Jul 1960 to 31 May 1994: of
```

### Funding (default) — BIS CBPOL XM (euro area)
```
FREQ,REF_AREA,UNIT_MEASURE,UNIT_MULT,TIME_FORMAT,COMPILATION,DECIMALS,SOURCE_REF,SUPP_INFO_BREAKS,TITLE,TIME_P
M,XM,368,0,,"From 18 Sep 2024 onwards: official central bank steering rate is the deposit facility rate, fixed
M,XM,368,0,,"From 18 Sep 2024 onwards: official central bank steering rate is the deposit facility rate, fixed
```

### FX (default) — FRED DEXUSUK (USD per GBP, daily)
_sampled at the last observation of the month, same rule as the curves_
```
observation_date,DEXUSUK
1971-01-04,2.3938
1971-01-05,2.3949
```

### FX (default) — FRED DEXJPUS (JPY per USD, daily)
_inverted in the loader to base per foreign_
```
observation_date,DEXJPUS
1971-01-04,357.73
1971-01-05,357.81
```

### FX (default) — FRED DEXCAUS (CAD per USD, daily)
_inverted in the loader_
```
observation_date,DEXCAUS
1971-01-04,1.0109
1971-01-05,1.0102
```

### FX (default) — FRED DEXUSEU (USD per EUR, daily)
_1999-_
```
observation_date,DEXUSEU
1999-01-04,1.1812
1999-01-05,1.1760
```

### FX monthly avg — NOT USED — FRED EXUSUK
_monthly average: misaligned with month-end yields (correction 1)_
```
observation_date,EXUSUK
1971-01-01,2.4058
1971-02-01,2.4178
```

### FX monthly avg — NOT USED — FRED EXJPUS
```
observation_date,EXJPUS
1971-01-01,358.0200
1971-02-01,357.5450
```

### FX monthly avg — NOT USED — FRED EXCAUS
```
observation_date,EXCAUS
1971-01-01,1.0118
1971-02-01,1.0075
```

### FX monthly avg — NOT USED — FRED EXUSEU
```
observation_date,EXUSEU
1999-01-01,1.1591
1999-02-01,1.1203
```
