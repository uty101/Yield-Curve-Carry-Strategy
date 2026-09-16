# Yield Curve Modelling and a G7 Carry Strategy — Build Plan v1

This file is the build specification. Work through it one step at a time.

## How to use this file

In Claude Code, from the repo root, say:

> Read PLAN.md and CLAUDE.md. Do step 0.1 only. Stop when its "Done when"
> condition is met, show me the test output and the review file.

Then `Do step 0.2 only`, and so on. Never a whole phase at once. Every step
has exactly three parts — **Build**, **Test**, **Done when** — and "Done
when" is always a test name or a file in `data/checks/` the owner can open.

At the end of every step the session runs `make test` and `make lint`,
writes `review/X.Y.md` from `review/TEMPLATE.md`, commits on `main` with
message `Step X.Y: <one line>`, pushes, posts the review as a GitHub issue
titled `Review X.Y: <one line>` (label `review`, via
`scripts/gh_issue.py`), shows the test output and the review file, and
stops. One commit per step. No branches.

Written 2026-09-16 from the brief (`Project Outline/08_Yield_Curve_Carry.docx`),
the kickoff, the session-1 review corrections and the answers in issue #1:
base currency USD; France from the Banque de France TEC series; duration
neutrality across the book; the policy rate as funding rate with 3-month
interbank as a robustness column; Canada from the zero-coupon curve; par
curves bootstrapped to zero in step 1.9. Italy is not in the universe
(`decisions/euro_curves.md`).

## Global rules (apply to every step)

1. One step per session. Run `make test` and `make lint`, write the review,
   commit, push, post the review issue, stop.
2. Yields are decimals everywhere inside the package (0.0425, never 4.25).
   Conversion from percent happens once, in the loader, and nowhere else.
3. Never mix `par` and `zero` in one calculation. Any function that takes a
   curve asserts on `curve_type`.
4. Every number that affects a result comes from `config.toml`.
5. Raw files are never overwritten; every fetch goes in the manifest.
6. Every strategy run is a row in `reports/specifications.csv` before it
   computes. A variant that has no row did not happen. The file is append
   only.
7. Anything a function uses at month *t* is dated on or before *t*.
8. No number in `README.md` is typed by hand.
9. Do not import from the project 1 repo. The duration-budget engine is
   written here; it is small, and a cross-repo import will break.
10. Do not add features, refactor other modules, or improve earlier steps
    unless the current step says so.
11. If a data source is unreachable, stop and say so. Do not substitute a
    source without writing the substitution into `decisions/`.
12. Tests never use the network. Fixtures in `tests/fixtures/`.
13. Interpolation in yield is linear in tenor, between observed tenors only.
    There is one interpolation function in the package and every module uses
    it. No extrapolation, ever; a tenor beyond the longest observed is
    missing.
14. `config.toml` is written in full in step 0.1 with every key the plan
    names, so that no later step "adds a knob". A later step may change a
    default only if the step says so, and the change is a commit on its own.

### Conventions every step uses

These are stated once here and referenced by name below.

**CurveFrame.** Every loader and every curve-level step returns or reads a
tidy `pandas.DataFrame` with exactly these columns, in this order:

| column | dtype | meaning |
|---|---|---|
| `date` | `datetime64[ns]` | calendar month end (`Timestamp + MonthEnd(0)`, midnight). The observation is the last available in that calendar month in the source's own calendar; the stamp is the calendar month end so countries align. |
| `country` | `str` | ISO2: `US`, `GB`, `DE`, `JP`, `CA`, `FR` |
| `tenor_years` | `float64` | years; `0.25` is the funding anchor (`decisions/short_anchor.md`) |
| `yield` | `float64` | decimal, annually compounded (see below) |
| `curve_type` | `str` | `zero` or `par` |
| `source` | `str` | the manifest `source` name of the raw file it came from |

`curvecarry.loaders.base.validate_curve(df: pd.DataFrame) -> pd.DataFrame`
asserts the schema, `yield` in `[-0.05, 0.5]`, `yield.max() > 0.001`
(catches a double division), monotone unique `date` per `(country, tenor_years)`,
no duplicate `(date, country, tenor_years)`, `curve_type ∈ {zero, par}`, and
returns the frame sorted by `(country, date, tenor_years)`. Every loader's
`load()` ends by calling it.

**Month-end sampling.** `curvecarry.loaders.base.month_end_sample(daily: pd.DataFrame) -> pd.DataFrame`
takes a long daily frame (`obs_date`, `tenor_years`, `yield`) and returns,
for each `(calendar month, tenor_years)`, the last non-null observation in
that month, stamped `date = month end`. Per tenor, not per day, so a tenor
that stops mid-month (DGS20 in 1986) is sampled at its own last print. Never
an average. Monthly sources (BoE, BIS, OECD) are stamped, not sampled.

**Compounding.** Inside the package a zero yield `z` at tenor `t` means
`DF(t) = (1 + z)^(-t)` (annual compounding). Each zero-curve loader (GB, DE,
CA) reads the source's stated convention from the source's own documentation,
records it in its module docstring and in `decisions/compounding.md`, and
converts continuously compounded rates with `z = exp(r) - 1`. If the
documentation does not state the convention, the step stops and asks. Par
yields are quoted with the country's coupon frequency and are not converted.

**Curve object.** `curvecarry.curves.Curve` is a frozen dataclass:
`tenors: np.ndarray`, `yields: np.ndarray`, `curve_type: str`, `country: str`,
`date: pd.Timestamp`, sorted by tenor, NaNs dropped.
`Curve.from_panel(panel: pd.DataFrame, country: str, date: pd.Timestamp, *, include_anchor: bool) -> Curve`.
`Curve.at(tenor: float) -> float` calls the one interpolation function
(rule 13) and returns NaN outside `[tenors.min(), tenors.max()]`.

**Units in names.** Columns ending `_bp` are basis points; everything else
is decimal. `carry` is per year; `rolldown` is per horizon month;
`duration` and `convexity` are in years and years²; `weight` is units of
capital; `wd` is `weight × duration` in years.

**Files.** `data/raw/<source>/<name>_<YYYYMMDD>.<ext>` and
`data/raw/manifest.json` (committed); `data/interim/*.parquet` one per
loader; `data/processed/*.parquet` panels and results;
`data/checks/*.csv` everything the reviewer reads (committed);
`reports/figures/*.png`; `reports/results.md`; `reports/specifications.csv`.

**Fixtures.** `scripts/make_fixture.py <source>` trims a raw file to its
header rows plus the first 50 data rows and writes it to
`tests/fixtures/<source>/` (same extension; xlsx written with openpyxl).
Every `parse()` test reads a fixture; every `fetch()` is a thin function that
is never called in a test.

**CLI.** `uv run curvecarry fetch --source <name>`,
`build --step <name>`, `run --variant <name> [--note "..."]`, `report`.
Sub-commands are added by the step that builds them; until then they print
"not built yet".

---

# Phase 0 — Foundation

## Step 0.1 — Config loader, spec log and run hash

**Build**
- `config.toml` is already written in full (session 1). This step does not
  add a key. It adds the loader:
- `src/curvecarry/config.py`:
  - `load(path: str | Path = "config.toml") -> dict`: `tomllib.load`, returns
    the nested dict unchanged, except `sample.strategy_end` parsed to
    `pd.Timestamp` and blank strings left as `""`. Raises `KeyError` naming
    the key if any of the keys this plan names is absent (the list of
    required dotted keys is a module constant `REQUIRED_KEYS`).
  - `config_hash(cfg: dict) -> str`: first 12 hex chars of sha256 of
    `json.dumps(cfg, sort_keys=True, default=str)`.
- `src/curvecarry/speclog.py`:
  - `log_run(cfg: dict, label: str, note: str, path: str | Path = "reports/specifications.csv") -> str`:
    appends one row `run_id, timestamp_utc, git_commit, config_hash, label, note`
    (`run_id` = `f"{timestamp_utc:%Y%m%dT%H%M%S}-{config_hash}"`, commit from
    `git rev-parse --short HEAD`, `"nogit"` on failure), creating the file
    with a header if absent. Opens in append mode only. Returns `run_id`.
  - `count_runs(path) -> int`: number of data rows. This is N for the
    deflated Sharpe in 5.5 and is never an argument.
  - `require_logged(run_id: str, path) -> None`: raises `RuntimeError` if
    no row has that `run_id`. Every function that computes a strategy
    result takes a `run_id` and calls this first.
- `reports/specifications.csv` created with the header only and committed.
- `.gitattributes` already marks `*.csv text eol=lf`.

**Test** `tests/test_config.py`, `tests/test_speclog.py`
- `test_config_loads_every_named_key`: `load()` returns every key in
  `REQUIRED_KEYS`; `strategy_start` and `sample_full_start` are `""`.
- `test_config_hash_stable_and_sensitive`: two loads give the same hash;
  changing `z_entry` changes it; the hash is 12 hex chars.
- `test_log_run_appends_row`: in a `tmp_path`, two `log_run` calls give a
  file with 2 data rows, distinct `run_id`s, header
  `run_id,timestamp_utc,git_commit,config_hash,label,note`.
- `test_run_without_row_fails`: `require_logged("nope", tmp)` raises
  `RuntimeError`; after `log_run` the returned id passes.
- `test_speclog_is_append_only`: `log_run` after an existing row leaves the
  first row byte-identical.

**Done when** the five tests pass and `reports/specifications.csv` exists
with a header and no rows.

## Step 0.2 — Raw data manifest

**Build**
- `src/curvecarry/manifest.py`:
  - `raw_path(source: str, name: str, ext: str, fetched: date, root: Path = Path("data/raw")) -> Path`
    → `root/source/f"{name}_{fetched:%Y%m%d}.{ext}"`.
  - `write_raw(content: bytes, path: Path, url: str, source: str, manifest: Path = Path("data/raw/manifest.json")) -> dict`:
    raises `FileExistsError` if `path` exists (never overwrite); writes the
    bytes; appends `{"source", "name", "path", "url", "sha256", "bytes", "fetched_at"}`
    to the manifest list (created if absent); returns the entry.
  - `fetch_bytes(url: str, *, params: dict | None = None, headers: dict | None = None, timeout: int = 180) -> bytes`:
    one `requests.get`, browser User-Agent, `raise_for_status`, and raises
    `RuntimeError("empty body")` if `len(content) == 0`. This is the only
    place `requests` is called in the package.
  - `latest_raw(source: str, name: str, root=...) -> Path`: the newest file
    matching `name_*.ext`; raises `FileNotFoundError` with the `fetch`
    command to run.
- `data/raw/manifest.json` committed as `[]`.

**Test** `tests/test_manifest.py` (all in `tmp_path`, no network)
- `test_second_fetch_to_existing_path_raises`: `write_raw` twice to the same
  path → `FileExistsError`, file unchanged, manifest has one entry.
- `test_manifest_entry_has_sha256_and_bytes`: sha256 matches
  `hashlib.sha256(content).hexdigest()`, `bytes == len(content)`.
- `test_refetch_gets_dated_filename`: `raw_path` for two dates gives two
  different paths.
- `test_latest_raw_picks_newest`: two dated files → the later one.

**Done when** the four tests pass and `data/raw/manifest.json` is `[]`.

## Step 0.3 — Review template guard

**Build**
- `review/TEMPLATE.md` exists (session 1). Add
  `tests/test_reviews.py::test_reviews_follow_template`: every
  `review/*.md` except `TEMPLATE.md` has the headings
  `## What changed`, `## Findings`, `## Not verified`, `## Open`,
  `## Reviewer reads`, a first line matching `# Review — Step \d+\.\d+ — `,
  and a `Date: … Commit: … Tests: \d+/\d+` line. Every `> Claim:` block is
  followed by a `> Number:` line and at least 5 `> ` row lines.
- `scripts/make_fixture.py` (the trimmer named in Conventions):
  `python scripts/make_fixture.py <source> <raw_path> [--sheet NAME]`
  writes header + first 50 data rows to `tests/fixtures/<source>/` for csv
  and xlsx.

**Test** `tests/test_reviews.py`
- `test_reviews_follow_template` (above); passes vacuously with no reviews.
- `test_make_fixture_trims_to_50_rows`: on a generated 200-row csv and a
  200-row xlsx in `tmp_path`, the output has 50 data rows and the header.

**Done when** both tests pass.

---

# Phase 1 — Data

One step per source. Phases 2–6 are locked until 1.9 passes and the owner
has reviewed `coverage.csv` and `par_zero_gap.csv`. Each loader module has
`fetch(cfg) -> list[Path]` (downloads, writes via `manifest.write_raw`,
nothing else), `parse(paths: list[Path]) -> pd.DataFrame` (raw → daily or
monthly long frame in **decimal**), and `load(cfg) -> pd.DataFrame`
(`parse(latest raws)` → month-end sample → CurveFrame → `validate_curve` →
`data/interim/curves_<cc>.parquet`). Every loader test has, at minimum:
`test_units_<cc>` (all yields in `[-0.05, 0.5]` and `max > 0.001`),
`test_tenors_<cc>` (the exact tenor set), `test_dates_<cc>` (monotone
unique month ends), `test_no_duplicates_<cc>`.

Coverage is one file, `data/checks/coverage.csv`, written by
`curvecarry.checks.write_coverage(df: pd.DataFrame, stage: str) -> None`:
one row per `(country, tenor_years, curve_type, stage)` with `first_date`,
`last_date`, `months_present`, `months_missing` (months between first and
last with no observation), `gaps` (`;`-joined `YYYY-MM..YYYY-MM` runs of
≥ 2 missing months). Rows for the same `(country, stage)` are replaced, all
others kept. Loader steps write `stage = observed`; 1.8 writes
`stage = harmonised`.

## Step 1.1 — US: FRED constant-maturity par yields

**Build**
- `src/curvecarry/loaders/us.py`. Series `DGS1 DGS2 DGS3 DGS5 DGS7 DGS10 DGS20 DGS30`,
  URL `https://fred.stlouisfed.org/graph/fredgraph.csv?id=<series>`,
  raw `data/raw/fred/<series>_<date>.csv`, source `fred`.
  - `parse(paths)`: columns `observation_date, <series>`; `"."` → NaN;
    `yield = value / 100`; `tenor_years` from the series name; long frame
    `obs_date, tenor_years, yield`.
  - `load(cfg)`: `month_end_sample` → `country = "US"`, `curve_type = "par"`.
    Writes `data/interim/curves_us.parquet` and coverage rows
    (`stage = observed`). The DGS20 gap (1987-01 to 1993-09) and the DGS30
    gap (2002-03 to 2006-01) appear in the `gaps` column; nothing is
    interpolated across them.
- CLI: `fetch --source us`, `build --step us`.

**Test** `tests/test_loader_us.py` on `tests/fixtures/fred/DGS*.csv`
(8 fixtures, header + 50 rows each) plus a synthetic frame for the gap check.
- `test_units_us`, `test_tenors_us` (`{1,2,3,5,7,10,20,30}`), `test_dates_us`,
  `test_no_duplicates_us`.
- `test_month_end_is_last_observation_not_average`: a synthetic month with
  values 1, 2, 3 on three days gives 3 (× 1e-2), not 2.
- `test_gap_is_recorded_not_filled`: a synthetic DGS20 with 24 missing months
  produces one `gaps` entry and no yields in those months.

**Done when** the six tests pass and `data/checks/coverage.csv` has 8 US rows
with the two gaps in `gaps`.

## Step 1.2 — UK: Bank of England nominal spot curve, month-end archive

**Build**
- `src/curvecarry/loaders/gb.py`. One zip,
  `https://www.bankofengland.co.uk/-/media/boe/files/statistics/yield-curves/glcnominalmonthedata.zip`,
  raw `data/raw/boe/glcnominalmonthedata_<date>.zip`, source `boe`. The zip
  holds `GLC Nominal month end data_1970 to 2015.xlsx`,
  `..._2016 to 2024.xlsx`, `..._2025 to present.xlsx`; the loader must read
  every xlsx in the zip whatever their names, and the sheet whose name
  contains `spot curve` (the 4th sheet in the BoE layout). The
  `latest-yield-curve-data.zip` is not used (session-1 correction 4).
  - `parse(paths)`: header row of maturities in years (0.5 to 40 in 0.5
    steps in later files, shorter in early years), one row per month end;
    `yield = value / 100`; the BoE's compounding convention is read from
    the notes sheet / BoE documentation and recorded per Conventions, with
    the conversion applied if continuous.
  - `load(cfg)`: monthly already; stamp to calendar month end;
    `country = "GB"`, `curve_type = "zero"`. Keep every observed tenor
    (1.8 selects). Coverage rows.
- `decisions/compounding.md` created with the GB entry.

**Test** `tests/test_loader_gb.py` on `tests/fixtures/boe/*.xlsx`
(one trimmed xlsx per archive file, made with `make_fixture.py --sheet`).
- `test_units_gb`, `test_tenors_gb` (integer tenors 1–30 all present in the
  post-2016 fixture; at least `{1,2,3,5,7,10}` in the 1970s fixture),
  `test_dates_gb`, `test_no_duplicates_gb`.
- `test_all_archive_files_are_read`: dates span across the three fixtures.
- `test_compounding_conversion_applied_once`: with a synthetic sheet at
  exactly 5.000% and the recorded convention, `yield` equals the expected
  converted value to 1e-12 (or 0.05 if the source is annual).

**Done when** the six tests pass, coverage has GB rows, and
`decisions/compounding.md` states the BoE convention with its source.

## Step 1.3 — Germany: Bundesbank Svensson parameters

**Build**
- `src/curvecarry/loaders/de.py`. Six series from the Bundesbank API,
  `https://api.statistiken.bundesbank.de/rest/download/BBSIS/D.I.ZST.<P>.EUR.S1311.B.A604._Z.R.A.A._Z._Z.A?format=csv&lang=en`
  for `P ∈ {B0, B1, B2, B3, T1, T2}`, plus the published 10-year
  `D.I.ZST.ZI.EUR.S1311.B.A604.R10XX.R.A.A._Z._Z.A` as the check series.
  Raw `data/raw/bundesbank/<P>_<date>.csv`, source `bundesbank`.
  - `parse_params(paths) -> pd.DataFrame`: daily `obs_date, beta0, beta1, beta2, beta3, tau1, tau2`
    with betas `/ 100` (published in percent), taus in years, `"."` → NaN;
    header lines skipped by matching `^\d{4}-\d{2}-\d{2},`.
  - `svensson_yield(tau: np.ndarray, beta0, beta1, beta2, beta3, tau1, tau2) -> np.ndarray`
    in `src/curvecarry/svensson.py` (shared with 2.3), in the Bundesbank's
    decay-time form:
    `y = β0 + β1·(1−e^{−τ/τ1})/(τ/τ1) + β2·[(1−e^{−τ/τ1})/(τ/τ1) − e^{−τ/τ1}] + β3·[(1−e^{−τ/τ2})/(τ/τ2) − e^{−τ/τ2}]`.
  - `parse(paths)`: reconstructs the 8 standard tenors daily from the
    parameters, decimal, then applies the compounding conversion per
    Conventions (recorded in `decisions/compounding.md`).
  - `load(cfg)`: `month_end_sample` → `country = "DE"`, `curve_type = "zero"`,
    `data/interim/curves_de.parquet`; and the month-end sampled parameters
    to `data/interim/svensson_params_de.parquet` (the Phase 2 benchmark).
    Parameters start 1997-08; coverage rows record it.

**Test** `tests/test_loader_de.py` on `tests/fixtures/bundesbank/*.csv`
(7 fixtures).
- `test_units_de`, `test_tenors_de` (`{1,2,3,5,7,10,20,30}`), `test_dates_de`,
  `test_no_duplicates_de`.
- `test_reconstruct_published_10y_within_1bp`: on 20 dates drawn with
  `numpy.random.default_rng(0)` from the fixture dates where all seven
  series are present, `|svensson_yield(10, params) − published_10y| ≤ 1e-4`
  (before compounding conversion; the published series is in the same
  convention as the formula).
- `test_svensson_yield_limits`: as τ → ∞ the formula → β0; at τ = 1e-9 it
  → β0 + β1 (to 1e-8).

**Done when** the six tests pass and `data/interim/svensson_params_de.parquet`
exists.

## Step 1.4 — Japan: MOF JGB benchmark yields

**Build**
- `src/curvecarry/loaders/jp.py`. Two files:
  `https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/historical/jgbcme_all.csv`
  and `https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/jgbcme.csv`
  (current year), raw `data/raw/mof/jgbcme_all_<date>.csv`,
  `jgbcme_<date>.csv`, source `mof`. The kickoff URL without `historical/`
  is 404 (`decisions/sources.md`).
  - `parse(paths)`: first line `Interest Rate,,,(Unit : %)`, second line
    `Date,1Y,2Y,…,10Y,15Y,20Y,25Y,30Y,40Y`, dates `YYYY/M/D`, `"-"` → NaN,
    `/ 100`. Concatenate both files and drop duplicate `obs_date`
    (historical wins). Keep every tenor (1–10, 15, 20, 25, 30, 40).
  - `load(cfg)`: `month_end_sample` → `country = "JP"`, `curve_type = "par"`.
    The 20, 25, 30 and 40-year series start later than the rest; coverage
    rows record the first dates.

**Test** `tests/test_loader_jp.py` on `tests/fixtures/mof/*.csv` (2 fixtures).
- `test_units_jp`, `test_tenors_jp` (`{1,…,10,15,20,25,30,40}` present as
  columns; the standard 8 are a subset), `test_dates_jp`,
  `test_no_duplicates_jp`.
- `test_dash_is_missing_not_zero`: a `"-"` cell gives NaN, not 0.
- `test_historical_wins_on_overlap`: a synthetic overlap day with different
  values keeps the historical file's value.

**Done when** the six tests pass and coverage has JP rows with later first
dates for 20, 25, 30, 40.

## Step 1.5 — Canada: Bank of Canada zero-coupon curve

**Build**
- `src/curvecarry/loaders/ca.py`. The zero-coupon curve is a GET form:
  `https://www.bankofcanada.ca/stats/results/csv` with params
  `lookupPage=lookup_yield_curve.php, startRange=1986-01-01, searchRange=all, submit=Submit`
  (whole history in one file). Raw `data/raw/boc/zero_curve_<date>.csv`,
  source `boc`. The Valet benchmark group
  (`https://www.bankofcanada.ca/valet/observations/group/bond_yields_benchmark/csv`)
  is fetched to `data/raw/boc/benchmark_<date>.csv` as the recorded
  fallback but is not loaded (issue #1 answer 5).
  - `parse(paths)`: columns `Date, ZC025YR, ZC050YR, …, ZC3000YR`
    (tenor = int(col[2:-2]) / 100), `"na"` → NaN. **Values are already
    decimals: no division.** Compounding per Conventions.
  - `load(cfg)`: `month_end_sample` → `country = "CA"`, `curve_type = "zero"`.
    `ZC025YR` is dropped: the 0.25 anchor is the policy rate for every
    country (`decisions/short_anchor.md`). The file is published with a
    two-week lag; if the latest calendar month has no observation, that
    month is missing and coverage shows it.

**Test** `tests/test_loader_ca.py` on `tests/fixtures/boc/zero_curve.csv`.
- `test_units_ca` — the decisive one: `yield.max() > 0.001` fails if the
  loader divides by 100.
- `test_tenors_ca` (`{0.5, 0.75, 1.0, …, 30.0}` minus 0.25), `test_dates_ca`,
  `test_no_duplicates_ca`.
- `test_na_is_missing`: `na` → NaN.
- `test_anchor_tenor_dropped`: no `tenor_years == 0.25` row.

**Done when** the six tests pass and coverage has CA rows.

## Step 1.6 — France: Banque de France TEC constant-maturity yields

**Build**
- `src/curvecarry/loaders/fr.py`. Ten datasets on Webstat,
  `fm-d-fr-eur-fr2-bb-frmoytec<N>-hsta` for `N ∈ {1,2,3,5,7,10,15,20,25,30}`,
  CSV export
  `https://webstat.banque-france.fr/api/explore/v2.1/catalog/datasets/<id>/exports/csv`
  with the key sent as the `apikey` query parameter (or the header the API
  documents; the step records which). Raw `data/raw/bdf/tec<N>_<date>.csv`,
  source `bdf`.
  - `fetch(cfg)`: key from `os.environ["BDF_API_KEY"]` only — raises
    `RuntimeError("BDF_API_KEY not set")` otherwise; never reads a file for
    it; never logs it. **The API returns HTTP 200 with zero rows when the
    key is missing or invalid**, so `fetch` counts data rows in the body and
    raises `RuntimeError("empty export")` rather than writing an empty raw
    file.
  - `parse(paths)`: the export's date and value columns (names fixed by the
    step from the real file and written into the module), `/ 100`, long
    frame `obs_date, tenor_years, yield`.
  - `load(cfg)`: `month_end_sample` → `country = "FR"`, `curve_type = "par"`
    (TEC is the yield of a hypothetical par OAT of constant maturity;
    coupon frequency 1 from `config.toml`). Keep all ten tenors. Coverage
    rows; the first TEC date is what sets `sample_full_start` in 1.9.
- `decisions/euro_curves.md` updated with the first available date and the
  export format.

**Test** `tests/test_loader_fr.py` on `tests/fixtures/bdf/tec*.csv`
(10 fixtures made from real exports with the key; the key is not in the
fixture).
- `test_units_fr`, `test_tenors_fr` (`{1,2,3,5,7,10,15,20,25,30}`),
  `test_dates_fr`, `test_no_duplicates_fr`.
- `test_fetch_without_key_raises`: with `BDF_API_KEY` removed from the
  environment (`monkeypatch.delenv`), `fetch` raises before any request
  (assert `manifest.fetch_bytes` is not called, via monkeypatch).
- `test_empty_export_is_refused`: `fetch_bytes` monkeypatched to return a
  header-only body → `RuntimeError`, nothing written.

**Done when** the six tests pass and coverage has FR rows with the TEC
first date.

## Step 1.7 — Funding rates and FX

**Build**
- `src/curvecarry/loaders/short_rates.py`:
  - Policy rates (default, `config.hedge.funding_rate = "policy"`): BIS
    `https://stats.bis.org/api/v2/data/dataflow/BIS/WS_CBPOL/1.0/M.<A>?format=csv`
    for `A ∈ {US, GB, JP, CA, XM}` (XM = euro area, used for EUR). Raw
    `data/raw/bis/CBPOL_<A>_<date>.csv`, source `bis`. SDMX-CSV:
    `TIME_PERIOD` (`YYYY-MM`), `OBS_VALUE` in percent → `/ 100`; stamped to
    calendar month end. The BIS monthly value is the end-of-month rate; the
    step confirms this from the BIS metadata and records it in the docstring.
  - 3-month interbank (robustness, `funding_rate_robustness = "interbank_3m"`):
    FRED `IR3TIB01USM156N, IR3TIB01GBM156N, IR3TIB01JPM156N, IR3TIB01CAM156N, IR3TIB01EZM156N`,
    raw `data/raw/fred/<series>_<date>.csv`, `/ 100`, first-of-month dates
    stamped to that month's end.
  - `load(cfg) -> pd.DataFrame` → `data/interim/short_rates.parquet` with
    columns `date, currency, rate, kind, source`; `currency ∈ {USD,GBP,JPY,CAD,EUR}`,
    `kind ∈ {policy, interbank_3m}`. The country→currency map is
    `config.currency`.
- `src/curvecarry/loaders/fx.py`:
  - FRED daily `DEXUSUK` (USD per GBP), `DEXJPUS` (JPY per USD), `DEXCAUS`
    (CAD per USD), `DEXUSEU` (USD per EUR); raw `data/raw/fred/<series>_<date>.csv`.
    A module constant `QUOTES = {"GBP": ("DEXUSUK", "usd_per_foreign"), "JPY": ("DEXJPUS", "foreign_per_usd"), "CAD": ("DEXCAUS", "foreign_per_usd"), "EUR": ("DEXUSEU", "usd_per_foreign")}`.
  - `parse(paths)`: `"."` → NaN; `usd_per_foreign = value` or `1 / value`
    by the quote direction; then
    `spot = usd_per_foreign / usd_per_base` where `usd_per_base` is 1 for
    USD base and the base currency's own series otherwise, so `spot` is
    always **units of base currency per unit of foreign currency**.
    `month_end_sample` (last observation of the month).
  - `load(cfg)` → `data/interim/fx.parquet`: `date, currency, spot, source`,
    with a row for the base currency at `spot = 1.0`.
- `data/checks/coverage.csv` gets rows with `country = <currency>` and
  `curve_type = funding` / `fx` (`stage = observed`).

**Test** `tests/test_loader_short_rates.py`, `tests/test_loader_fx.py` on
`tests/fixtures/bis/*.csv`, `tests/fixtures/fred/IR3TIB01*.csv`,
`tests/fixtures/fred/DEX*.csv`.
- `test_units_policy`, `test_units_interbank`: rates in `[-0.05, 0.5]`,
  `max > 0.001`.
- `test_five_currencies_two_kinds`: the set of `(currency, kind)` is the
  full 5 × 2.
- `test_month_end_stamp`: every `date` is a calendar month end.
- `test_fx_direction`: on the fixtures with USD base, GBP `spot` in
  `[1.0, 3.0]`, EUR in `[0.8, 1.7]`, JPY in `[0.002, 0.015]`, CAD in
  `[0.6, 1.1]`; base row is exactly 1.0.
- `test_fx_non_usd_base`: with `base_currency = "GBP"` on the same fixtures,
  `spot_USD × spot_GBP(USD base) == 1` to 1e-12 on matching dates.
- `test_fx_last_observation_of_month`: synthetic month → last value.

**Done when** the seven tests pass and `data/interim/short_rates.parquet`,
`data/interim/fx.parquet` exist with the coverage rows.

## Step 1.8 — Harmonise: one panel at the 8 tenors plus the anchor

**Build**
- `src/curvecarry/interp.py`:
  `interpolate_yield(tenors: np.ndarray, yields: np.ndarray, target: float | np.ndarray) -> float | np.ndarray`
  — the one interpolation function (rule 13). Linear in tenor between the
  two adjacent observed tenors; exact at an observed tenor; **NaN** for any
  target outside `[tenors.min(), tenors.max()]`; NaN inputs dropped first;
  raises `ValueError` if fewer than 2 finite points. `Curve.at` calls it.
- `src/curvecarry/harmonise.py`:
  - `standard_tenors(cfg) -> list[float]` = `config.tenors`.
  - `to_standard(curve_df: pd.DataFrame, cfg) -> pd.DataFrame`: per
    `(country, date)`, yields at the 8 standard tenors: the observed value
    where the tenor is observed, `interpolate_yield` where it lies between
    observed tenors, NaN beyond the longest (or before the shortest)
    observed. Adds `interpolated: bool`.
  - `add_anchor(panel, short_rates, cfg) -> pd.DataFrame`: one row per
    `(country, date)` at `tenor_years = config.short_tenor` with the
    policy rate of `config.currency[country]` (`kind = funding_rate`),
    `curve_type` = that country's curve type (so a `(country, date)` has one
    curve type), `source = bis`, `anchor = True`. Missing rate → no anchor
    row and a line in `data/checks/anchor_missing.csv`.
  - `build(cfg) -> pd.DataFrame` → `data/processed/curves.parquet`:
    CurveFrame columns + `interpolated`, `anchor`. Countries from
    `config.countries`. Coverage `stage = harmonised` for the 8 tenors.
  - Dates: the panel index is the union of month ends across countries; a
    country-month absent in the source is absent here (no forward fill).
- CLI `build --step harmonise`.

**Test** `tests/test_interp.py`, `tests/test_harmonise.py` (synthetic).
- `test_interp_exact_at_observed`, `test_interp_midpoint`: yields 0.02 at
  2y and 0.04 at 4y → 0.03 at 3y to 1e-15.
- `test_interp_never_extrapolates`: target 31 with max tenor 30 → NaN;
  target 0.1 with min 0.25 → NaN.
- `test_interp_needs_two_points`: one point → `ValueError`.
- `test_standard_tenors_from_jp_like_input`: tenors `{1..10,15,20,25,30}`
  give all 8 standard tenors with `interpolated == False` everywhere.
- `test_standard_tenors_from_boc_like_input`: tenors in 0.25 steps to 30 →
  all 8, none interpolated; to 25 → 30y NaN.
- `test_anchor_is_policy_rate_of_currency`: DE and FR anchors both equal the
  EUR policy rate; anchor `curve_type` equals the country's.
- `test_one_curve_type_per_country_month`.
- `test_no_forward_fill`: a missing month stays missing.

**Done when** the eight tests pass and `data/checks/coverage.csv` has
`harmonised` rows for 6 countries × 8 tenors.

## Step 1.9 — Par to zero, the two sample windows, the gate

**Build**
- `src/curvecarry/bootstrap.py`:
  - `bootstrap_par_to_zero(par: Curve, freq: int) -> Curve`: asserts
    `par.curve_type == "par"`. Coupon dates `t_k = k / freq` for
    `k = 1 … freq × T_max` where `T_max` is the longest observed par tenor.
    Par yield at each `t_k` by `interpolate_yield` over the observed par
    tenors **including the 0.25 anchor**; `t_k` below the shortest observed
    tenor is not reached because the anchor is at 0.25 ≤ 1/freq. For
    `t_k ≤ 1/freq` (single-cashflow bond) `z = c` with `c` the par yield
    at `t_k` (converted from the coupon-frequency convention to annual:
    `z = (1 + c/freq)^freq − 1`). For later `t_k`:
    `DF_k = (1 − (c_k/freq) · Σ_{j<k} DF_j) / (1 + c_k/freq)`, `z_k = DF_k^(−1/t_k) − 1`.
    Returns the zero curve at the 8 standard tenors (those ≤ `T_max`) as
    `Curve(curve_type="zero")`; tenors beyond `T_max` are absent (rule 13).
  - `build(cfg) -> pd.DataFrame` → `data/processed/curves_zero.parquet`:
    same schema as `curves.parquet` plus `bootstrapped: bool`. Countries
    whose source is `zero` (GB, DE, CA) pass through unchanged; `par`
    countries (US, JP, FR) are bootstrapped per `(country, date)` with
    `freq = config.coupon_frequency[country]`. The anchor row is carried
    through unchanged (it is a rate, not a bond yield). The par panel
    `curves.parquet` is kept as is (both stored).
  - `data/checks/par_zero_gap.csv`: `country, date, tenor_years, par_yield, zero_yield, gap_bp`
    at 10 and 30 years for US, JP, FR, every month.
  - `data/checks/sample_window.txt`: two lines,
    `strategy_start=YYYY-MM-DD` — the first month end where at least
    `config.sample.sample_min_countries` (5) of `config.countries` have a
    non-null zero yield at every standard tenor ≤ `sample_max_tenor` (10);
    `sample_full_start=YYYY-MM-DD` — the first month end where **all**
    countries in `config.countries` do. `config.toml` gets both values
    written into `[sample]` in this step's commit (the only step that edits
    `config.toml` besides 0.1).
- CLI `build --step zero`.

**Test** `tests/test_bootstrap.py` (synthetic).
- `test_flat_par_gives_flat_zero`: a flat 4% par curve (freq 1 and freq 2,
  tenors 0.25, 1, 2, 3, 5, 7, 10, 20, 30) gives zero yields equal to
  `(1 + 0.04/freq)^freq − 1` at every tenor to 1e-12 (exactly 0.04 for
  freq 1).
- `test_reprice_par_bonds_at_100`: an upward-sloping par curve
  (2% at 0.25 to 5% at 30) bootstrapped, then each observed par bond priced
  off the zero curve (`bondmath` is 2.1; this test uses a local
  cashflow-sum helper in the test file) is within 0.005 of 100.
- `test_zero_source_passes_through`: a `zero` input is returned identical.
- `test_par_assertion`: passing a `zero` curve raises `AssertionError`.
- `test_no_tenor_beyond_longest_par`: par curve to 10y gives no 20 or 30.
- `test_sample_window_rule`: a synthetic coverage panel with a known first
  5-of-6 month and first 6-of-6 month gives those two dates.

**Done when** the six tests pass, `data/checks/par_zero_gap.csv` and
`data/checks/sample_window.txt` exist, and `config.toml` has both dates.

**Gate.** The owner reviews `data/checks/coverage.csv` and
`data/checks/par_zero_gap.csv` and the two dates before any Phase 2 step
is started. The pass is recorded in `CLAUDE.md` → Validation status.

---

# Phase 2 — Curve models

All fits use the **zero** panel `curves_zero.parquet` at the 8 standard
tenors; the 0.25 anchor is excluded from fitting (it is a policy rate).
A country-month with fewer than `config.nelson_siegel.min_tenors` (5)
non-null standard tenors is not fitted and is counted in
`data/checks/fit_skipped.csv`.

## Step 2.1 — Bond maths

**Build**
- `src/curvecarry/bondmath.py`, every function asserts
  `curve.curve_type == "zero"` where it takes a curve:
  - `discount_factor(z: float | np.ndarray, t: float | np.ndarray) -> ...` = `(1 + z) ** (-t)`.
  - `cashflow_times(tenor: float, freq: int) -> np.ndarray`: `tenor − k/freq`
    for `k = n−1 … 0` where `n = ceil(tenor × freq − 1e-9)`; all > 0. For a
    seasoned bond (tenor not a multiple of 1/freq) the first coupon is the
    short stub.
  - `price_from_zero(curve: Curve, tenor: float, coupon: float, freq: int) -> float`:
    dirty price per 100 = `Σ (100·coupon/freq)·DF(t_j) + 100·DF(T)` with
    `DF(t) = discount_factor(curve.at(t), t)`; raises `ValueError` if any
    `curve.at(t_j)` is NaN (no extrapolation).
  - `par_yield_from_zero(curve, tenor, freq) -> float` = `freq · (1 − DF(T)) / Σ DF(t_j)`.
  - `yield_from_price(price: float, tenor: float, coupon: float, freq: int) -> float`:
    ytm `y` (coupon-frequency compounding) by `scipy.optimize.brentq` on
    `Σ (100c/f)/(1+y/f)^(f t_j) + 100/(1+y/f)^(f T) − price`, bracket
    `[-0.05, 1.0]`, `xtol=1e-12`.
  - `modified_duration(ytm: float, tenor: float, coupon: float, freq: int) -> float`:
    `Mac = Σ t_j CF_j v_j / P`, `v_j = (1+y/f)^(−f t_j)`; `D = Mac / (1 + y/f)`.
  - `convexity(ytm, tenor, coupon, freq) -> float` = `Σ t_j (t_j + 1/f) CF_j v_j / (P (1+y/f)²)`.
  - `par_bond_risk(curve: Curve, tenor: float, freq: int) -> tuple[float, float, float]`:
    `(c, D, C)` for the par bond at `tenor` off the zero curve: `c` from
    `par_yield_from_zero`, then `D`, `C` at `ytm = c`. **This is the one
    duration function**; 4.1, 4.2, 5.1, 5.2 and 6.1 call it and nothing
    else computes a duration.

**Test** `tests/test_bondmath.py` (closed forms).
- `test_zero_coupon_bond_price`: coupon 0, tenor T, flat curve z →
  `100 (1+z)^(−T)` to 1e-12.
- `test_flat_curve_par_yield`: flat z, freq f → `c = f((1+z)^(1/f) − 1)` to
  1e-12; for f = 1, `c = z`.
- `test_par_bond_prices_at_100`: `price_from_zero(curve, T, par_yield, f) == 100`
  to 1e-9 on a sloped curve for T in {1, 2, 5, 10, 30}.
- `test_yield_from_price_round_trip`: `yield_from_price(price_from_zero(...))`
  equals the par yield to 1e-10.
- `test_zero_coupon_duration_and_convexity`: coupon 0 → `D = T/(1+y/f)`,
  `C = T(T + 1/f)/(1+y/f)²` to 1e-10.
- `test_duration_matches_finite_difference`: `−(P(y+h) − P(y−h)) / (2hP)`
  with `h = 1e-6` matches `D` to 1e-6.
- `test_curve_type_asserted`: a `par` Curve → `AssertionError`.

**Done when** the seven tests pass.

## Step 2.2 — Nelson-Siegel

**Build**
- `src/curvecarry/nelson_siegel.py`:
  - `ns_loadings(tau: np.ndarray, lam: float) -> np.ndarray` (n × 3):
    `[1, (1−e^{−λτ})/(λτ), (1−e^{−λτ})/(λτ) − e^{−λτ}]` — the brief's
    6.1 form, λ per year.
  - `fit_fixed_lambda(tau, y, lam) -> tuple[np.ndarray, float]`: OLS
    `β = lstsq(X, y)`, RMSE in decimal.
  - `fit(tau: np.ndarray, y: np.ndarray, grid: tuple[float, float, float]) -> NSFit`:
    λ over `np.arange(lo, hi + step/2, step)`, pick min RMSE, then
    `scipy.optimize.minimize_scalar(bounded, bracket = [λ* − step, λ* + step] ∩ [lo, hi], xatol=1e-10)`
    on RMSE(λ); `NSFit(beta0, beta1, beta2, lam, rmse_bp, n_tenors)`.
  - `fit_panel(zero_panel: pd.DataFrame, cfg) -> pd.DataFrame` →
    `data/processed/ns_params.parquet`: `date, country, model, beta0, beta1, beta2, lam, rmse_bp, n_tenors`
    with `model ∈ {ns_free, ns_dl}` (`ns_dl` = fixed `config.ns_lambda_fixed`).
    Fitted yields at the 8 tenors to `data/processed/ns_fitted.parquet`
    (`date, country, model, tenor_years, fitted`).
- CLI `build --step ns`.

**Test** `tests/test_nelson_siegel.py` (synthetic).
- `test_recover_known_parameters`: β = (0.05, −0.02, 0.01), λ = 0.6 at the
  8 tenors, no noise → `|β̂ − β| < 1e-4` each and `|λ̂ − λ| < 1e-4`,
  `rmse_bp < 1e-6`.
- `test_fixed_lambda_recovers_beta_when_lambda_true`: λ_true = 0.7 → β to
  1e-10.
- `test_loadings_limits`: at τ → 0 loadings → `[1, 1, 0]`; at τ = 1e3 →
  `[1, ~0, ~0]`.
- `test_grid_refinement_not_worse_than_grid`: refined RMSE ≤ best grid RMSE.
- `test_skips_below_min_tenors`: 4 tenors → not fitted, counted.

**Done when** the five tests pass and `data/processed/ns_params.parquet`
has both models for every fitted country-month.

## Step 2.3 — Svensson

**Build**
- `src/curvecarry/svensson.py` (module created in 1.3 with `svensson_yield`):
  - `sv_loadings(tau, lam1, lam2) -> np.ndarray` (n × 4), λ-form:
    columns 1–3 as NS with λ1, column 4 `(1−e^{−λ2τ})/(λ2τ) − e^{−λ2τ}`.
    Relation to the Bundesbank form: `λ = 1/τ_decay`.
  - `fit(tau, y, grid) -> SVFit`: grid over `(λ1, λ2)` pairs from the same
    grid with `λ2 > λ1 + step` (ordering removes the label swap), OLS per
    pair, then `scipy.optimize.minimize(Nelder-Mead, xatol=1e-8, fatol=1e-14)`
    on `(λ1, λ2)` from the best pair, clipped to `[lo, hi]`.
    `SVFit(beta0..beta3, lam1, lam2, lam_gap = |λ1 − λ2|, rmse_bp, n_tenors)`.
  - `fit_panel(...)` → `data/processed/sv_params.parquet` and fitted yields
    appended to `ns_fitted.parquet` with `model = "sv"`.
  - Germany benchmark: `compare_bundesbank(cfg) -> pd.DataFrame` →
    `data/checks/svensson_vs_bundesbank.csv`: per DE month,
    `rmse_ours_bp` (our fit vs the panel), `rmse_bbk_bp` (yields from the
    Bundesbank's own month-end parameters vs the panel — ~0 by
    construction, after the same compounding conversion as 1.3),
    `lam1_ours, lam2_ours, lam1_bbk = 1/tau1, lam2_bbk = 1/tau2, lam_gap_ours, lam_gap_bbk`,
    and `beta_diff_max` (max abs difference of the four betas).
- CLI `build --step svensson`.

**Test** `tests/test_svensson.py` (synthetic).
- `test_recover_known_curve`: from β = (0.05, −0.02, 0.01, 0.015),
  λ1 = 0.5, λ2 = 1.2 → fitted yields within 1e-7 at every tenor (the curve
  is identified even where the parameters are weakly so).
- `test_nested_ns_case`: β3 = 0 data → `rmse_bp < 1e-6`.
- `test_lambda_gap_recorded_and_positive`.
- `test_bundesbank_form_equals_lambda_form`: `svensson_yield(τ, …, tau1, tau2)`
  equals `sv_loadings(τ, 1/tau1, 1/tau2) @ β` to 1e-14.
- `test_de_fit_recovers_bundesbank_curve`: yields generated from a real
  Bundesbank parameter row in the fixture → our `fit` RMSE < 0.1 bp.

**Done when** the five tests pass and
`data/checks/svensson_vs_bundesbank.csv` exists.

## Step 2.4 — Chart 1 and Chart 3

**Build**
- `src/curvecarry/charts.py` (matplotlib, `Agg`, every function takes
  frames and an output path and returns the path):
  - `chart1_fit(zero_panel, fitted, dates: dict[str, list[pd.Timestamp]], out_dir) -> list[Path]`:
    per country one figure `reports/figures/chart1_fit_<cc>.png` with 4
    panels: observed points, NS-free line, Svensson line, on the 4 dates.
    Dates: for each decade in `config.report.chart1_decades` the last
    December month end with a fit; if a country lacks that decade, the
    earliest fitted month. The chosen dates go to
    `data/checks/chart1_dates.csv` (`country, decade, date`).
  - `chart1_rmse(ns_params, sv_params, out) -> Path`:
    `reports/figures/chart1_rmse.png`, 6 panels, RMSE (bp) by month, NS-free
    vs NS-DL vs Svensson.
  - `chart3_betas(ns_params, out) -> Path`: `reports/figures/chart3_betas.png`,
    3 panels (β0, β1, β2), one line per country, 1995 to the last month
    (NS-free).
- CLI `report --charts 1,3` (partial report; the full `report` is 6.4).

**Test** `tests/test_charts.py` (synthetic frames, `tmp_path`).
- `test_chart1_dates_rule`: a synthetic fit table with gaps picks the last
  December per decade and the earliest month for a missing decade.
- `test_chart_functions_write_files`: each function writes a non-empty png.

**Done when** both tests pass and the 8 pngs and
`data/checks/chart1_dates.csv` exist.

---

# Phase 3 — PCA

## Step 3.1 — PCA on monthly yield changes

**Build**
- `src/curvecarry/pca.py`:
  - `monthly_changes_bp(zero_panel, cfg) -> pd.DataFrame`: wide per
    country, index `date`, columns the 8 standard tenors,
    `Δy_t = (y_t − y_{t−1}) × 1e4` where `t−1` is the previous calendar
    month end **and both months are present at all 8 tenors**; otherwise
    the row is dropped and counted in `data/checks/pca_dropped.csv`
    (`country, n_months_total, n_dropped, reason`). The anchor is excluded.
  - `pca(changes: np.ndarray) -> PCAResult`: demean by column;
    `S = np.cov(X, rowvar=False, ddof=1)`; `w, V = np.linalg.eigh(S)`;
    sort descending; sign rule per component:
    PC1 loading at 10y > 0; PC2 `loading(30) − loading(2) > 0`;
    PC3 `loading(10) − ½(loading(2) + loading(30)) > 0` (belly positive;
    the kickoff fixes PC1 and PC2, PC3 is fixed here so the sign is
    reproducible); PC4+ first non-zero element positive.
    `PCAResult(loadings (8×8), eigenvalues, explained (= w / w.sum()), mean, scores)`.
  - `fit_country(cfg) -> None` and `fit_pooled(cfg) -> None`: pooled =
    each country's changes demeaned by its own column means, stacked as
    rows, one PCA; scores per country-month = that country's demeaned row
    `@ V`.
  - Outputs `data/processed/pca_loadings.parquet`
    (`scope ∈ {US,…,FR,pooled}, component (1–8), tenor_years, loading`),
    `data/checks/pca_explained.csv` (`scope, component, eigenvalue, explained_share, n_months`),
    `data/processed/pca_scores.parquet` (`scope, country, date, component, score`).
- CLI `build --step pca`.

**Test** `tests/test_pca.py` (synthetic).
- `test_explained_sums_to_one`: to 1e-12.
- `test_scores_reconstruct_changes`: `scores @ V.T + mean == changes` to
  1e-10 with all 8 components.
- `test_sign_rules`: after normalisation the three inequalities hold.
- `test_three_factor_data_gives_three_components`: data generated from 3
  factors → explained shares 4–8 sum < 1e-10.
- `test_missing_tenor_month_dropped_and_counted`.
- `test_pooled_scores_are_per_country_month`: pooled score frame has one
  row per `(country, date, component)`.

**Done when** the six tests pass and the three outputs exist with
`pooled` and six country scopes.

## Step 3.2 — Loading stability by decade

**Build**
- `pca.stability(cfg) -> pd.DataFrame` → `data/checks/pca_stability.csv`:
  per country and decade (`1990s` = 1990-01..1999-12, `2000s`, `2010s`,
  `2020s`), PCA on that decade's changes alone (same sign rules), and
  `abs_corr = |corr(v_k^decade, v_k^full)|` for k = 1, 2, 3; columns
  `country, decade, component, n_months, abs_corr, explained_share_decade`.
  A decade with fewer than `config.pca.stability_min_months` (24) months of
  changes is written with `abs_corr = NaN` and its `n_months`.

**Test** `tests/test_pca_stability.py` (synthetic).
- `test_self_correlation_is_one`: full sample vs itself → 1.0 to 1e-12.
- `test_stable_factor_structure_scores_high`: two decades drawn from the
  same 3-factor model → `abs_corr > 0.99` for PC1–3.
- `test_short_decade_is_nan_with_count`.

**Done when** the three tests pass and `data/checks/pca_stability.csv`
exists.

## Step 3.3 — Chart 2 and the explained-variance table

**Build**
- `charts.chart2_loadings(loadings, out) -> Path`:
  `reports/figures/chart2_loadings.png`, 3 panels (PC1, PC2, PC3), x =
  tenor, one line per country, pooled dashed black.
- `report.explained_table(explained: pd.DataFrame) -> str`: markdown table
  `scope | PC1 | PC2 | PC3 | PC1–3` in percent to 1 dp, written to
  `data/checks/pca_explained_table.md`.

**Test** `tests/test_charts.py::test_chart2_writes_file`,
`tests/test_report_tables.py::test_explained_table_rows_sum` (PC1–3 column
equals the sum of the three to 0.05 pp; one row per scope).

**Done when** both tests pass and the png and md exist.

---

# Phase 4 — Carry, rolldown, returns

## Step 4.1 — Carry and rolldown

**Build**
- `src/curvecarry/carry.py`, on `curves_zero.parquet`, horizon `Δt = 1/12`:
  - per `(country, date, tenor n ∈ standard tenors)` with `Curve` built
    `include_anchor=True`:
    `r_short = curve.at(0.25)` (the anchor);
    `carry = y_n − r_short` (per year);
    `(c, D, C) = par_bond_risk(curve, n, freq)`;
    `y_roll = curve.at(n − Δt)` (between observed tenors; for n = 1 this
    lies between 0.25 and 1 — `decisions/short_anchor.md`);
    `rolldown = (y_n − y_roll) × D` (per horizon month, decimal);
    `expected_return_1m = carry × Δt + rolldown`.
  - Output `data/processed/carry.parquet`:
    `date, country, tenor_years, yield, r_short, carry, rolldown, duration, convexity, par_yield, expected_return_1m`.
    Rows where any input is NaN are dropped and counted in
    `data/checks/carry_missing.csv` (`country, tenor_years, n_missing`).
- CLI `build --step carry`.

**Test** `tests/test_carry.py` (synthetic curves).
- `test_flat_curve_rolldown_zero`: flat curve → `rolldown == 0` to 1e-15,
  `carry == y − r_short`.
- `test_linear_curve_rolldown`: `y(τ) = a + bτ` → `rolldown == b × Δt × D`
  to 1e-12 for every tenor.
- `test_one_year_bucket_rolls_toward_anchor`: with an anchor at 0.25 and
  no other tenor below 1, `y_roll(1)` is the interpolation between the
  anchor and the 1y point.
- `test_duration_is_par_bond_risk`: `duration` equals
  `bondmath.par_bond_risk(...)[1]` exactly.
- `test_missing_input_is_counted_not_filled`.

**Done when** the five tests pass and `data/processed/carry.parquet` exists.

## Step 4.2 — Return engine

**Build**
- `src/curvecarry/returns.py`, for each `(country, tenor n, month t)` with
  a curve at `t` and at `t+1` (the next calendar month end):
  - Full recomputation: buy at `t` the par bond at tenor `n` off the zero
    curve: `c = par_yield_from_zero(curve_t, n, freq)`, price 100. At
    `t+1` its tenor is `n − 1/12`; dirty price
    `P = price_from_zero(curve_{t+1}, n − 1/12, c, freq)` (no coupon is
    paid within one month for freq ≤ 2; the accrued coupon is inside the
    dirty price). `r_local_full = P / 100 − 1`.
  - Approximation (brief 6.3) from curve yields only:
    `Δy = par_yield_from_zero(curve_{t+1}, n − 1/12, freq) − c`;
    `r_local_approx = c/12 − D·Δy + ½·C·Δy²` with `(D, C)` from
    `par_bond_risk(curve_t, n, freq)`.
  - `gap_bp = (r_local_full − r_local_approx) × 1e4`.
  - **`r_local = r_local_full`** is the return the strategy uses; the
    approximation is diagnostic.
  - A bucket present at `t` whose price at `t+1` cannot be computed
    (`price_from_zero` raises: the aged tenor needs an unobserved tenor)
    gets `r_local = 0.0`, `closed = True`, and a row in
    `data/checks/closed_buckets.csv` (`date, country, tenor_years, reason`)
    — "closed at its last available price".
  - Output `data/processed/returns.parquet`:
    `date (= t), country, tenor_years, coupon, duration, convexity, dy, r_local_full, r_local_approx, gap_bp, r_local, closed`.
  - `data/checks/return_approx_gap.csv`: the full distribution — per
    `tenor_years`: `n, mean_bp, std_bp, p01, p05, p50, p95, p99, max_abs_bp`,
    and the 20 largest `|gap_bp|` rows with their dates.
- CLI `build --step returns`.

**Test** `tests/test_returns.py` (synthetic zero curves: NS curves with
`rng = default_rng(0)`, β0 ∈ [0.01, 0.08], β1 ∈ [−0.04, 0.02],
β2 ∈ [−0.03, 0.03], λ ∈ [0.3, 1.2], month-to-month shocks: parallel
±50 bp, slope ±25 bp uniform).
- `test_approx_within_tolerance_on_200_draws`: 200 random
  `(curve_t, curve_{t+1}, tenor)` draws → `|gap_bp| ≤ 2` for tenors ≤ 10
  and `≤ 10` at 20 and 30 (the plan's tolerance; the test file lists the
  numbers).
- `test_unchanged_curve_return_equals_carry_plus_rolldown`: `curve_{t+1} == curve_t`
  → `r_local_full` equals `c/12 + rolldown-like term` within 1 bp, and
  `r_local_approx` equals it within 0.1 bp.
- `test_parallel_shift_sign`: +100 bp shift → negative return for every
  tenor; −100 bp → positive.
- `test_closed_bucket_is_zero_and_logged`: curve at `t+1` missing 30y →
  `r_local == 0`, `closed`, one log row.
- `test_full_repricing_uses_dirty_price`: the price at `t+1` includes
  accrued (equals cashflow sum with first stub `1/freq − 1/12`).

**Done when** the five tests pass and `data/checks/return_approx_gap.csv`
exists.

## Step 4.3 — FX hedge column

**Build**
- `returns.add_fx(returns, short_rates, fx, cfg) -> pd.DataFrame` adds to
  `returns.parquet`:
  - `hedge_carry = (r_short_base − r_short_foreign) / 12` with both from
    `short_rates.parquet`, `kind = config.hedge.funding_rate`, dated `t`;
  - `fx_return = ln(S_{t+1}) − ln(S_t)` with `S` = base per foreign from
    `fx.parquet` (foreign appreciation is a gain);
  - `r_hedged = r_local + hedge_carry`; `r_unhedged = r_local + fx_return`.
  - For the base country's currency all of `r_local, r_hedged, r_unhedged`
    are equal (`hedge_carry = fx_return = 0`).
  - A robustness copy with `kind = funding_rate_robustness`:
    `hedge_carry_interbank_3m`, `r_hedged_interbank_3m` (NaN where the
    interbank series is missing).
- `decisions/basis.md`: what the hedged return omits (the cross-currency
  basis). The step probes, and records the status of, the free candidates
  it can find (at minimum: FRED search for "cross-currency basis", BIS
  Statistics Explorer, the ECB Data Portal); if none yields a series, it
  states that the basis is **not measured** and quotes the brief's 20 to
  50 bp in stress periods. If one is found, the size of the CIP error by
  year for each currency pair is tabulated there and in
  `data/checks/xccy_basis.csv`.
- CLI `build --step fx`.

**Test** `tests/test_fx_hedge.py` (synthetic).
- `test_base_country_columns_equal`.
- `test_hedge_carry_sign_and_size`: base 5%, foreign 1% → `+0.04/12`.
- `test_unhedged_uses_log_change_of_base_per_foreign`: `S` 1.00 → 1.02 →
  `fx_return == ln(1.02)`; a foreign appreciation raises `r_unhedged`.
- `test_hedge_uses_rates_dated_t_not_t_plus_1`.
- `test_robustness_column_present_and_nan_where_missing`.

**Done when** the five tests pass, `returns.parquet` has the new columns,
and `decisions/basis.md` exists.

## Step 4.4 — Chart 4

**Build**
- `charts.chart4_carry_heatmap(carry, out) -> Path`:
  `reports/figures/chart4_carry_per_duration.png`: rows = `country-tenor`
  (48, grouped by country), columns = months, colour = `carry / duration`
  (bp per year per year of duration), diverging colormap centred at 0,
  NaN shown grey. Plus one small-multiple figure per country,
  `chart4_<cc>.png`.

**Test** `tests/test_charts.py::test_chart4_writes_files`.

**Done when** the test passes and the 7 pngs exist.

---

# Phase 5 — Strategy

## Step 5.1 — Signal

**Build**
- `src/curvecarry/signal.py`:
  - `signal = (carry + 12 × rolldown) / duration` — carry per year and
    rolldown annualised (× 12) so both are per year before dividing by
    `D`; units: return per year per year of duration. Ranking is invariant
    to this scaling, so the brief's `(Carry + Rolldown)/D` with mixed
    units gives the same portfolio; the annualised form is used so the
    number is readable.
  - Eligibility per `(country, tenor, month)`: `yield ≥ config.signal.yield_floor`
    (zero yield at the tenor) and `carry, rolldown, duration` all finite.
    Ineligible rows keep their signal but `eligible = False`, with
    `excluded_reason ∈ {below_floor, missing_input}`.
  - `data/checks/signal_exclusions.csv`: `date, n_below_floor, n_missing_input, n_eligible`
    per month, and a second table `country, n_below_floor` (Japan will
    dominate).
  - Output `data/processed/signal.parquet`:
    `date, country, tenor_years, signal, duration, yield, eligible, excluded_reason`.
- CLI `build --step signal`.

**Test** `tests/test_signal.py` (synthetic).
- `test_signal_hand_computed`: carry 0.02, rolldown 0.001, D 4 →
  `(0.02 + 0.012)/4 = 0.008`.
- `test_below_floor_is_ineligible`: yield 0.0019 with floor 0.002 →
  `eligible False`, reason `below_floor`.
- `test_exclusion_counts_match_rows`.
- `test_floor_read_from_config_not_hardcoded`: changing the floor in a
  modified cfg changes eligibility.

**Done when** the four tests pass and `data/checks/signal_exclusions.csv`
exists.

## Step 5.2 — Weights

**Build**
- `src/curvecarry/weights.py`:
  - `duration_neutral_weights(signal: pd.DataFrame, cfg) -> pd.DataFrame`
    per month on eligible rows:
    - `scope = "book"` (default): rank all eligible buckets by `signal`
      descending; `n` eligible; `k = n // 3`; if `n < config.weights.min_eligible_buckets`
      (6) the month holds nothing and is logged to
      `data/checks/weights_empty_months.csv`. Long leg = top `k`, short
      leg = bottom `k`; ties broken by `(country, tenor_years)` order so the
      result is deterministic.
      `wd_j = +B/k` (long), `−B/k` (short), `B = config.weights.long_duration_budget`;
      `weight_j = wd_j / duration_j`.
    - `scope = "country"`: the same rule within each country's eligible
      tenors with `k_c = n_c // 3` and `B_c = B / n_countries_that_month`;
      each country's `Σ wd = 0`.
  - Output `data/processed/weights.parquet`:
    `date, country, tenor_years, leg ∈ {long, short}, signal, duration, weight, wd`.
    Unheld buckets are absent (weight 0 by construction downstream).

**Test** `tests/test_weights.py` (synthetic signal frames).
- `test_duration_neutral_every_month`: `|Σ wd| < 1e-10` for every month.
- `test_long_leg_hits_budget`: `Σ wd_long == B` to 1e-12.
- `test_equal_duration_contribution_within_leg`.
- `test_legs_never_overlap`: no `(country, tenor)` in both legs.
- `test_third_rule`: 48 eligible → 16 long, 16 short; 7 → 2 and 2.
- `test_country_scope_neutral_per_country`.
- `test_empty_month_below_minimum_is_logged`.

**Done when** the seven tests pass.

## Step 5.3 — Carry-only backtest

**Build**
- `src/curvecarry/backtest.py`:
  - `run(cfg, variant: str, note: str = "") -> BacktestResult`:
    **first** `run_id = speclog.log_run(cfg, label=variant, note=note)`,
    then computes; every computing function takes `run_id` and calls
    `speclog.require_logged`. Variants in this step:
    `carry_hedged`, `carry_unhedged`.
  - Timing: weights `w_t` from `signal` at month end `t`; held `t → t+1`;
    bucket return `r_{j,t}` from `returns.parquet` row dated `t`
    (`r_hedged` or `r_unhedged`). A bucket missing at `t` is not held; a
    bucket with `closed = True` contributes `r = 0` and is counted in
    `n_closed_t`.
    `r_gross_t = Σ_j w_{j,t} r_{j,t}`.
  - Turnover `turnover_t = ½ Σ_j |wd_{j,t} − wd_{j,t−1}|` over the union of
    buckets (absent = 0); the first month counts the full entry.
    `cost_t = config.costs.cost_bp_per_duration_year × 1e-4 × Σ_j |wd_{j,t} − wd_{j,t−1}|`
    (= `2 × cost_bp × 1e-4 × turnover_t`). `r_net_t = r_gross_t − cost_t`.
  - Sample: `t` from `config.sample.strategy_start` to the last `t` with a
    `t+1` return ≤ `strategy_end`. Every metric is computed for **two
    windows**: `full` from `strategy_start` and `six` from
    `sample_full_start` (session-1 correction 5).
  - `src/curvecarry/metrics.py`:
    `annualised_return = mean(r) × 12`; `annualised_vol = std(r, ddof=1) × √12`;
    `sharpe = annualised_return / annualised_vol` (no risk-free subtraction:
    the book is duration-neutral long/short and hedged, so it is an excess
    return already); `max_drawdown` on the wealth index `Π(1 + r)` with
    `peak_date`, `trough_date`; `turnover_mean`; `n_months`;
    `year_2022 = {return, vol, sharpe, max_drawdown}` on the 12 months
    of 2022 alone.
  - Outputs: `data/processed/backtest_<variant>.parquet`
    (`date, r_gross, cost, r_net, turnover, n_long, n_short, n_closed, run_id`);
    `data/checks/metrics_<variant>.csv` (`run_id, variant, window, metric, value`),
    `data/checks/positions_<variant>.parquet` (the weights actually held).
- CLI `run --variant carry_hedged [--note]`; `run --all` runs the variants
  the step names, each as its own logged row.

**Test** `tests/test_backtest.py` (synthetic weights and returns in
`tmp_path`; the spec log path is injected).
- `test_run_logs_specification_before_computing`: after `run`, the log has
  one new row and its `run_id` is in the result; a computing function
  called with an unlogged `run_id` raises.
- `test_timing_signal_t_return_t_to_t_plus_1`: a return that occurs in the
  month after a weight change is captured by the new weights, not the old.
- `test_portfolio_return_hand_computed`: two buckets, known weights and
  returns → `r_gross` exactly.
- `test_turnover_and_cost`: `wd` from `{A: +2, B: −2}` to `{A: +2, C: −2}`
  → `turnover = 2`, `cost = 0.5e-4 × 4`.
- `test_missing_bucket_not_held_and_closed_is_zero`.
- `test_metrics_closed_forms`: constant monthly return `r` →
  `annualised_return = 12r`, `vol = 0`, drawdown 0; a `−10%` then `+5%`
  series → `max_drawdown = −0.10`, dates right.
- `test_two_windows_reported`: metrics frame has `window ∈ {full, six}`.

**Done when** the seven tests pass, `reports/specifications.csv` has two new
rows, and `data/checks/metrics_carry_hedged.csv`,
`data/checks/metrics_carry_unhedged.csv` exist.

## Step 5.4 — Slope overlay

**Build**
- `src/curvecarry/overlay.py`:
  - `expanding_pc2_scores(changes_by_country, cfg) -> pd.DataFrame`: for
    country `c` and month `t`, if the number of complete change rows
    dated ≤ `t` is ≥ `config.pca.pca_min_months` (60): PCA (3.1 rules) on
    rows ≤ `t`, `score_t = (Δy_t − mean_{≤t}) @ v2^{(≤t)}`; otherwise NaN.
    Never full-sample loadings. Output
    `data/processed/pc2_expanding.parquet` (`country, date, score, n_months`).
  - `zscore(scores, window = config.pca.pca_z_window) -> pd.Series`:
    `(s_t − mean_{t−35..t}) / std_{t−35..t}` (ddof 1), NaN until 36 scores.
  - `states(z: pd.Series, cfg) -> pd.Series` with values
    `{flat, steepener, flattener}` and per-country flags
    `armed_steep, armed_flat` (both start True):
    - `flat → steepener` when `z < −z_entry` and `armed_steep`;
      `flat → flattener` when `z > +z_entry` and `armed_flat`; entering
      clears that side's flag.
    - `steepener → flat` when `z ≥ z_exit`; `flattener → flat` when
      `z ≤ z_exit`.
    - A flag is re-armed when `z` crosses `z_exit` (sign change between
      consecutive months). NaN `z` → `flat` and both flags cleared until
      the next crossing.
  - Positions: per country in `steepener`: long `overlay_tenors[0]` (2y),
    short `overlay_tenors[1]` (10y) with `wd_2 = +B_o`, `wd_10 = −B_o`,
    `B_o = config.overlay.overlay_duration_budget`; `flattener` the
    reverse; weights `w = wd / D` with `D` from `par_bond_risk` at `t`.
    Book `Σ wd = 0` by construction.
  - `backtest.run(cfg, "overlay_hedged")` and `"overlay_unhedged"` using
    these positions through the same engine (5.3). Outputs as in 5.3 plus
    `data/processed/overlay_positions.parquet`
    (`date, country, state, z, tenor_years, weight, wd`) and
    `data/checks/overlay_trades.csv` (entries and exits with dates and z).
- CLI `run --variant overlay_hedged`.

**Test** `tests/test_overlay.py` (synthetic).
- `test_score_at_t_unchanged_when_future_appended`: scores for `t ≤ T0`
  computed on data to `T0` equal those computed on data to `T0 + 24`
  to 1e-12.
- `test_no_score_before_min_months`: month 59 NaN, month 60 finite.
- `test_state_machine_sequences`:
  `z = [−1.6, −0.5, 0.1, −1.6]` → `[steepener, steepener, flat, steepener]`;
  `[−1.6, −1.0, −1.7]` → all `steepener` (no double entry);
  `[1.6, 0.5, −0.2, 1.6]` → `[flattener, flattener, flat, flattener]`;
  `[−1.6, NaN, −1.6]` → `[steepener, flat, flat]` (disarmed until a
  crossing).
- `test_pair_is_duration_neutral_and_sized`: `Σ wd == 0`, long `wd == B_o`.
- `test_zscore_window_and_ddof`.

**Done when** the five tests pass, the two overlay variants are logged, and
`data/checks/overlay_trades.csv` exists.

## Step 5.5 — Combined and the metrics table

**Build**
- `backtest.run(cfg, "combined_hedged")`, `"combined_unhedged"`:
  positions = carry weights + overlay weights summed per `(country, tenor)`
  (both books duration-neutral, so the sum is); turnover and cost on the
  summed `wd`.
- Robustness variants, each its own logged row:
  `carry_hedged_country_scope` (`duration_neutral_scope = "country"`),
  `carry_hedged_interbank_3m` (`funding_rate = interbank_3m` for the anchor,
  carry, hedge; sample limited to where the series exist, stated in the
  table). A variant's config override is recorded in its spec-log `note` as the JSON of the
  overridden keys; the base `config.toml` is not edited.
- `metrics.deflated_sharpe(sr_monthly: float, sr_var_trials: float, n_trials: int, T: int, skew: float, kurt: float) -> tuple[float, float]`
  — Bailey & López de Prado (2014), per period (monthly), exactly project
  1's formula written here (rule 9):
  `SR0 = sqrt(V[SR]) × [(1−γ) Φ⁻¹(1 − 1/N) + γ Φ⁻¹(1 − 1/(N e))]`,
  `DSR = Φ((SR − SR0) √(T−1) / sqrt(1 − γ3 SR + (γ4 − 1)/4 SR²))`,
  `kurt` raw (normal = 3), `SR0 = 0` when `N ≤ 1` or `V = 0`.
  **N = `speclog.count_runs()`** — the row count of `specifications.csv`,
  never an argument. `V[SR]` = variance of the monthly Sharpes across all
  runs that have a `metrics_<variant>.csv` (joined on `run_id`).
- `report.metrics_table(cfg) -> pd.DataFrame` →
  `data/checks/metrics_table.csv` and `data/checks/metrics_table.md`:
  rows = variants (carry, overlay, combined × hedged, unhedged; the two
  robustness rows), columns = window (`full`, `six`) × metric
  (`ann_return, ann_vol, sharpe, max_dd, dd_peak, dd_trough, turnover, ret_2022, dd_2022, n_months`)
  plus `dsr` and `N`.

**Test** `tests/test_combined.py`, `tests/test_metrics.py`.
- `test_combined_weights_are_sum_and_neutral`.
- `test_deflated_sharpe_known_values`: `N = 1` → `SR0 = 0` and
  `DSR = Φ(SR √(T−1)/…)`; `N = 100, V = 0.01, SR = 0.3, T = 121, skew 0, kurt 3`
  → the value written in the test from a hand calculation to 1e-6.
- `test_n_is_read_from_speclog`: `metrics_table` with a spec log of 7 rows
  reports `N = 7`.
- `test_variant_override_is_in_note_and_hash`: the robustness run's
  `config_hash` differs from the base and its `note` contains the key.

**Done when** the four tests pass and `data/checks/metrics_table.csv` has
all eight variants in both windows.

---

# Phase 6 — Analysis and write-up

## Step 6.1 — Decomposition

**Build**
- `src/curvecarry/decomposition.py`, per variant and month `t`, on the
  held positions:
  - `carry_earned_t = Σ_j w_j (c_j/12 + rolldown_j)` (`c_j` the par yield
    the bond was bought at, `rolldown_j` from 4.1);
  - `yield_change_pnl_t = Σ_j w_j (r_local_full,j − c_j/12 − rolldown_j)` —
    the exact remainder, so the identity holds to machine precision. Its
    Taylor form `Σ_j w_j (−D_j Δy_j + ½ C_j Δy_j²)` with
    `Δy_j = y_{t+1}(n − 1/12) − y_t(n − 1/12)` (the pure curve move at the
    aged tenor, zero curve) is stored as `yield_change_taylor_t` and the
    difference as `taylor_residual_t` (this is the 4.2 gap aggregated by
    the weights);
  - `hedge_t = Σ_j w_j hedge_carry_j` (or `fx_return_j` for unhedged);
  - `cost_t = −cost_t` from the backtest.
  - Identity: `carry_earned + yield_change_pnl + hedge + cost == r_net`
    to 1e-10 every month.
  - Outputs `data/processed/decomposition_<variant>.parquet`
    (`date, carry_earned, yield_change_pnl, yield_change_taylor, taylor_residual, hedge, cost, r_net, identity_gap`),
    `data/checks/decomposition_shares.csv` (`variant, window, piece, cumulative, share`
    where `cumulative` is the sum of the monthly piece and `share` its
    fraction of the summed `r_net`).
  - `charts.chart5_decomposition(...)` →
    `reports/figures/chart5_decomposition_<variant>.png`: cumulative sum of
    each piece and of `r_net`, for `carry_hedged` and `combined_hedged`.
- CLI `build --step decomposition`.

**Test** `tests/test_decomposition.py` (synthetic backtest in `tmp_path`).
- `test_four_pieces_sum_to_reported_return`: `|identity_gap| < 1e-10`
  every month.
- `test_carry_earned_hand_computed`.
- `test_taylor_residual_equals_weighted_gap`: equals `Σ w_j gap_j` from 4.2
  to 1e-12.
- `test_shares_sum_to_one`.

**Done when** the four tests pass and `data/checks/decomposition_shares.csv`
and the two chart-5 pngs exist.

## Step 6.2 — 2022 and the three risk controls

**Build**
- `decomposition.attribution_2022(cfg, variant) -> pd.DataFrame` →
  `data/checks/attribution_2022_<variant>.csv`:
  `date (12 months of 2022), country, leg, carry_earned, yield_change_pnl, hedge, cost, total`
  and a `country = ALL` row per month; for `carry_hedged` and
  `combined_hedged`.
- `src/curvecarry/risk_controls.py`, each a transform of a base variant's
  held positions into a new logged variant, applied to every base in
  `config.risk.risk_control_base_variants`:
  - (a) `vol_target`: `scale_t = min(target_vol / vol_{t−11..t}, max_leverage)`
    with `vol` the annualised std (ddof 1) of the base's `r_net` over the
    12 months ending at `t` (known at `t`); NaN until 12 months → scale 1;
    positions at `t` multiplied by `scale_t`. Variant `<base>_voltarget`.
  - (b) `dd_stop`: drawdown of the base's wealth index at `t`; if
    `< −dd_stop` the book is flat for months `t+1 … t+dd_reentry_months`
    (positions zero, turnover from closing counted), then re-enters at the
    base's positions. Variant `<base>_ddstop`.
  - (c) `rates_vol_filter`: pooled PC1 score by the **expanding** method
    of 5.4 (scope pooled, component 1, min 60 months); `v_t` = std of the
    12 scores ending at `t`; flat for `t → t+1` when
    `v_t > quantile_{≤t}(v, rates_vol_pct)` (expanding 90th percentile of
    `v` up to and including `t`). Variant `<base>_ratesvol`.
  - Every control's parameters are read from `config.toml [risk]` and were
    fixed there in session 1; **all six variants are logged before any
    result is looked at** (the `run` function logs first, as always) and
    all are reported in the metrics table whether or not they help, with
    their 2022 rows.
- CLI `run --risk-controls`.

**Test** `tests/test_risk_controls.py` (synthetic).
- `test_vol_target_scale_formula_and_cap`.
- `test_vol_target_uses_only_past_returns`: changing `r_{t+1}` does not
  change `scale_t`.
- `test_dd_stop_goes_flat_next_month_for_exactly_reentry_months`.
- `test_rates_filter_expanding_percentile_no_lookahead`: appending months
  after `t` leaves the flag at `t` unchanged.
- `test_attribution_2022_rows_sum_to_total`.

**Done when** the five tests pass, six risk-control rows are in
`specifications.csv`, and `data/checks/attribution_2022_carry_hedged.csv`
exists.

## Step 6.3 — What carry does not tell you

**Build**
- `report.section_what_carry_does_not_tell_you(cfg) -> str`: a section
  of `reports/results.md` written entirely from numbers read from
  `data/checks/decomposition_shares.csv`, `data/checks/attribution_2022_*.csv`,
  `data/checks/return_approx_gap.csv`, `data/checks/metrics_table.csv` and
  the status in `decisions/basis.md` (measured with its table, or "not
  measured; the brief's 20–50 bp"). Every figure in the prose is a
  formatted value from one of those files; the function has no numeric
  literals other than formatting widths. Paragraphs: the carry-earned share
  versus yield-change share; 2022 month by month; the size of the return
  approximation gap by tenor; the hedge and the basis; what the robustness
  rows changed.
- Written to `data/checks/section_6_3.md` for review before 6.4 assembles
  the report.

**Test** `tests/test_report_sections.py`
- `test_section_6_3_has_no_hardcoded_numbers`: the function's source (via
  `inspect.getsource`) contains no numeric literal other than in format
  specs (regex on the AST: `ast.Constant` of type int/float outside
  `FormattedValue` nodes → fail).
- `test_section_6_3_renders_from_synthetic_inputs`: with synthetic checks
  files in `tmp_path`, the returned string contains each input value
  formatted.

**Done when** both tests pass and `data/checks/section_6_3.md` exists.

## Step 6.4 — Report

**Build**
- `src/curvecarry/report.py::write(cfg) -> Path` → `reports/results.md`:
  header with `git commit`, `config_hash`, `N` runs, both sample windows;
  the metrics table (5.5) for both windows; the explained-variance table
  (3.3); the stability table (3.2); the decomposition shares (6.1); the
  2022 attribution summary (6.2) and the risk-control rows; the 6.3
  section; the DSR line; the list of charts. Also regenerates the 5
  charts (1, 2, 3, 4, 5) by calling the chart functions.
- `README.md`: the block between `<!-- results:begin -->` and
  `<!-- results:end -->` is pasted from the metrics table in
  `reports/results.md` by the session, verbatim.
- CLI `report`. `Makefile` targets `fetch`, `build`, `run`, `report` now
  call the CLI (`uv run curvecarry fetch --all`, `build --all`,
  `run --all`, `report`).

**Test** `tests/test_readme.py::test_readme_results_equal_results_md`:
the README block equals the metrics table section of `reports/results.md`
character for character (whitespace-normalised at line ends only).
`tests/test_report.py::test_report_writes_from_synthetic_checks`.

**Done when** both tests pass, `reports/results.md` and the 5 charts exist,
and the README block is the pasted table.

---

## Appendix — where each number lives

| Quantity | Config key | Used in |
|---|---|---|
| countries, tenors, anchor tenor | `countries`, `tenors`, `short_tenor` | 1.8 onwards |
| coupon frequency | `coupon_frequency.<cc>` | 1.9, 2.1, 4.x |
| windows | `sample.*` | 1.9, 5.3 |
| NS/Svensson grid and fixed λ, min tenors | `nelson_siegel.*` | 2.2, 2.3 |
| PCA windows | `pca.*` | 3.x, 5.4, 6.2 |
| yield floor | `signal.yield_floor` | 5.1 |
| duration budget, scope, minimum buckets | `weights.*` | 5.2 |
| overlay entry/exit, budget, tenors | `overlay.*` | 5.4 |
| funding rate kinds | `hedge.*` | 1.7, 1.8, 4.3, 5.5 |
| cost | `costs.cost_bp_per_duration_year` | 5.3 |
| risk controls | `risk.*` | 6.2 |
| chart decades | `report.chart1_decades` | 2.4 |
