# Yield Curve Modelling and a G7 Carry Strategy — Build Plan v2

This file is the build specification. Work through it one step at a time.

## How to use this file

**Sessions, not steps** (working rule from 2026-09-17; renumbered
2026-09-22). **Session N is Phase N: all of that phase's steps, and nothing
else.** The groups are fixed:

| Session | Steps |
|---|---|
| 0 | 0.1, 0.2, 0.3 |
| 1 | 1.1 to 1.9 and the gate |
| 2 | 2.1, 2.2, 2.3, 2.4 |
| 3 | 3.1, 3.2, 3.3 |
| 4 | 4.1, 4.2, 4.3, 4.4 |
| 5 | 5.1, 5.2, 5.3, 5.4, 5.5 |
| 6 | 6.1, 6.2, 6.3, 6.4 |

Phase 1 was built in two parts under the old numbering (1.1-1.7, then 1.8,
1.9 and the gate) and its commits and issues keep their original titles;
`CLAUDE.md` → Validation status records both parts.

In Claude Code, from the repo root, say:

> Read PLAN.md and CLAUDE.md. Do Session N.

**Within a session.** Steps are built in order. Each step keeps its own
commit (`Step X.Y: <one line>`) and its own `review/X.Y.md` from
`review/TEMPLATE.md`, and its "Done when" must be met, with `make test` and
`make lint` passing, before the next step starts. No review issue per
step. If a step cannot meet its "Done when", the session stops there and
reports; the step is not skipped and nothing past it is started. If a step
needs a choice the plan does not make, the question is posted as an issue
(label `decision`) and the session continues only with steps that do not
depend on the answer; if every remaining step depends on it, the session
stops. Never guess. When a decision issue changes a step, the plan text is
amended in the same session, before the session review is posted.

**End of session.** Push, then post one issue titled `Session N review`
(label `review`) containing: the steps built with their test counts; every
deviation from the plan, stated in full; every open question; and for each
step the "Reviewer reads" list from its review file. Then stop.

**Every session ends by writing `instructions/session-N-status.md` and
pushing it** (rule of 2026-09-22, session 2). However the session ends —
finished, stopped on a question, or blocked — that file states what was
built, what was not, why it stopped, and the last commit. It is written and
pushed even when the session stopped early, and it is the last thing done
before the summary. The owner's own instruction for the session is saved
verbatim in `instructions/session-N.md` at the start of the session and
committed as `Session N: instructions`.

**Review loop.** The owner reviews the whole session from the repo and
replies with fixes. Each fix is one commit (`Session N fix: <one line>`);
after the fixes the full suite is re-run and a comment on the session issue
lists what changed; then stop. This repeats until the owner posts
`Session N approved`. Only then is `Session N approved <date> (<commit>)`
recorded in `CLAUDE.md` → Validation status, and only then does the next
session start. A session is never started without the previous one's
approval line in `CLAUDE.md`.

Every step has exactly three parts — **Build**, **Test**, **Done when** —
and "Done when" is always a test name or a file in `data/checks/` the owner
can open. One commit per step. No branches.

Written 2026-09-16 from the brief (`Project Outline/08_Yield_Curve_Carry.docx`),
the kickoff, the session-1 review corrections and the answers in issue #1:
base currency USD; France from the Banque de France TEC series; duration
neutrality across the book; the policy rate as funding rate with 3-month
interbank as a robustness column; Canada from the zero-coupon curve; par
curves bootstrapped to zero in step 1.9. Italy is not in the universe
(`decisions/euro_curves.md`).

**Session-2 amendments (2026-09-22, `instructions/session-2.md`)** — three,
amended into steps 2.1, 2.2 and 2.3 below in the same session:
(1) a repricing check in 2.1 (`data/checks/par_reprice.csv`);
(2) the Bundesbank `(tau1, tau2)` -> lambda mapping and its ordering swap in
2.3, with a 10% trigger on the share of DE months whose lambda lies outside
`config.nelson_siegel.ns_lambda_grid` — **the share is 69.9%, so the trigger
fired, issue #12 is open and step 2.4 is not built until it is answered**;
(3) a held-out fit test across 2.2 and 2.3 (`data/checks/fit_holdout.csv`).

**Session-3 amendments (2026-09-23, `instructions/session-3.md`)** — four,
amended into steps 3.1 and 3.2 below in the same session:
(1) the PCA tenor set is chosen per country rather than fixed at the 8
standard tenors, with a stop condition — the stop condition fired on the
instruction's own wording and **issue #15 answered it: "enters the panel"
means the first month the country has a 10-year zero (option C)**, which
also added a secondary pooled fit on the 20-year set, reported only;
(2) sign normalisation restated for a variable tenor set;
(3) the input is `curves_zero.parquet` in bp of monthly change, and a month
enters only if it and the previous month are both complete on the set;
(4) 3.2 reports the US decade loadings twice, with and without the
borderline pre-1997 months carried forward from the Phase 1 gate — a
robustness check, since 30y is not in the US tenor set (#15 answer 4).

**v2 (2026-09-16, after the review of v1 in issue #2)** — four amendments:
(A) every bucket return is an excess return over its own funding rate and
the hedge is the CIP identity `r_hedged = r_excess_local`; (B) the funding
rate is never on the curve — no anchor row, a flat short-end convention
below the shortest observed tenor, US and DE gain observed 0.25 and 0.5
tenors; (C) the risk controls use returns dated ≤ t−1; (D) euro funding
before 1999 is the national BIS policy rate, spliced at
`config.hedge.eur_splice`. Steps changed: 1.1, 1.3, 1.5, 1.7, 1.8, 1.9,
2.1, 3.1, 4.1, 4.2, 4.3, 5.3, 5.5, 6.1, 6.2.

## Global rules (apply to every step)

1. One session at a time; one commit and one review file per step; nothing
   starts until the previous session is approved in `CLAUDE.md`.
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
    missing. **One exception, by convention:** below the shortest
    *observed* zero tenor the zero yield is flat from that tenor
    (`config.short_end = "flat"`). It is not extrapolation, it lives in
    `Curve.at`, and only `bondmath`, `bootstrap` and the 1-year rolldown
    through `Curve.at` exercise it (`decisions/short_anchor.md`).
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
| `tenor_years` | `float64` | years; every observed tenor is kept, standard or not (US 0.25 and 0.5, JP 15, 25, 40, FR 15, 25, CA 0.25-year steps). The funding rate is never a row: it lives in `data/interim/funding.parquet` (`decisions/short_anchor.md`) |
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
`Curve.from_panel(panel: pd.DataFrame, country: str, date: pd.Timestamp) -> Curve`
(all observed tenors of that country-month, standard and non-standard).
`Curve.at(tenor: float) -> float` calls the one interpolation function
(rule 13) inside `[tenors.min(), tenors.max()]`, returns **`yields[0]`
below `tenors.min()`** (the flat short end, `config.short_end`), and NaN
above `tenors.max()`.

**Funding table.** `data/interim/funding.parquet` (step 1.7) has
`date, country, currency, rate, kind, source` — one row per
`(country, month end, kind)`, `kind ∈ {policy, interbank_3m}`. For a euro
country before `config.hedge.eur_splice` the policy rate is the national
BIS series named in `config.hedge.eur_legacy`; from the splice it is `XM`.
`r_short_local` for a bucket is this table at the bucket's country and
date; `r_short_base` is the row of the base currency's country. Every
bucket return the strategy sees is an excess return over its own
`r_short_local` (amendment A).

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
    (`run_id` = `f"{timestamp_utc:%Y%m%dT%H%M%S}-{config_hash}"`, with
    `-2`, `-3`, … appended when that id already exists in the file, so two
    runs of one config in the same second get distinct ids; commit from
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
    to the manifest list (created if absent); returns the entry. `name` is
    the path stem with its `_YYYYMMDD` suffix removed (the inverse of
    `raw_path`); a path without that suffix is refused with `ValueError`
    (issue #4).
  - `fetch_bytes(url: str, *, params: dict | None = None, headers: dict | None = None, timeout: int = 180) -> bytes`:
    one `requests.get`, browser User-Agent, `raise_for_status`, and raises
    `RuntimeError("empty body")` if `len(content) == 0`. This is the only
    place `requests` is called in the package.
  - `latest_raw(source: str, name: str, root=...) -> Path`: globs
    `name_*.*` under `root/source` (any extension), keeps only files whose
    stem is exactly `name_<YYYYMMDD>`, and returns the one with the newest
    `YYYYMMDD` in its filename — never by mtime; raises `ValueError` naming
    the extensions if the matches carry more than one extension; raises
    `FileNotFoundError` with the `fetch` command to run when there is none
    (issue #4).
- `data/raw/manifest.json` committed as `[]`.

**Test** `tests/test_manifest.py` (all in `tmp_path`, no network)
- `test_second_fetch_to_existing_path_raises`: `write_raw` twice to the same
  path → `FileExistsError`, file unchanged, manifest has one entry.
- `test_manifest_entry_has_sha256_and_bytes`: sha256 matches
  `hashlib.sha256(content).hexdigest()`, `bytes == len(content)`.
- `test_refetch_gets_dated_filename`: `raw_path` for two dates gives two
  different paths.
- `test_latest_raw_picks_newest`: two dated files → the later date, with
  the newer date written first so mtime would give the wrong answer.
- `test_latest_raw_refuses_mixed_extensions`: a `.csv` and a `.zip` for the
  same name → `ValueError` naming both extensions (issue #4).
- `test_manifest_name_round_trips_raw_path`: for several
  `(source, name, ext)`, `write_raw(raw_path(...))` records exactly `name`;
  an undated path is refused (issue #4).

**Done when** the six tests pass and `data/raw/manifest.json` is `[]`.

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

`data/checks/sample_day_mismatch.csv` (Session 1 part A review, 2026-09-22) is the
sampling rule's footprint: every curve loader writes, per `(country, month)`,
the latest `obs_date` any tenor was sampled on, the number of standard
tenors present, the number of those sampled on an earlier day and which
(`checks.write_sample_day`). It is a check only; the per-tenor sampling
rule in Conventions is unchanged unless the owner says so.

## Step 1.1 — US: FRED constant-maturity par yields

**Build**
- `src/curvecarry/loaders/us.py`. Series `DGS3MO DGS6MO DGS1 DGS2 DGS3 DGS5 DGS7 DGS10 DGS20 DGS30`
  (`DGS3MO` → 0.25, `DGS6MO` → 0.5, both from 1981-09, kept in the panel as
  non-standard tenors like JP's 15y; they give the US curve an observed
  short end — amendment B),
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
  - **DGS30 2002-02-19 .. 2006-02-08 is dropped in `parse`** (issue #7,
    2026-09-22): Treasury discontinued the 30-year constant maturity on
    2002-02-18 and reinstated it on 2006-02-09; FRED's DGS30 now carries
    Treasury's factor-based estimates from the 20-year for the interval.
    They are an extrapolation (rule 13), so the loader masks the closed
    span (`us.DGS30_EXTRAPOLATED`) and the gap is recorded, not filled.
- CLI: `fetch --source us`, `build --step us`.

**Test** `tests/test_loader_us.py` on `tests/fixtures/fred/DGS*.csv`
(10 fixtures, header + 50 rows each) plus a synthetic frame for the gap check.
- `test_units_us`, `test_tenors_us` (`{0.25,0.5,1,2,3,5,7,10,20,30}`), `test_dates_us`,
  `test_no_duplicates_us`.
- `test_month_end_is_last_observation_not_average`: a synthetic month with
  values 1, 2, 3 on three days gives 3 (× 1e-2), not 2.
- `test_gap_is_recorded_not_filled`: a synthetic DGS20 with 24 missing months
  produces one `gaps` entry and no yields in those months.
- `test_dgs30_extrapolated_span_is_dropped` (issue #7): a synthetic DGS30
  with values on every business day 2002-01..2006-03 has no yield inside
  the span, keeps 2002-02 and 2006-02, and coverage shows `2002-03..2006-01`.

**Done when** the seven tests pass and `data/checks/coverage.csv` has 10 US rows
with the two gaps in `gaps` and 1981-09 first dates for 0.25 and 0.5.

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
  - `parse(paths)`: reconstructs the 8 standard tenors **and 0.25 and 0.5**
    daily from the parameters (amendment B: the observed short end for
    Germany), decimal, then applies the compounding conversion per
    Conventions (recorded in `decisions/compounding.md`).
  - `load(cfg)`: `month_end_sample` → `country = "DE"`, `curve_type = "zero"`,
    `data/interim/curves_de.parquet`; and the month-end sampled parameters
    to `data/interim/svensson_params_de.parquet` (the Phase 2 benchmark).
    Parameters start 1997-08; coverage rows record it.

**Test** `tests/test_loader_de.py` on `tests/fixtures/bundesbank/*.csv`
(7 fixtures).
- `test_units_de`, `test_tenors_de` (`{0.25,0.5,1,2,3,5,7,10,20,30}`), `test_dates_de`,
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
    Every tenor from 0.25 to 30 is kept (non-standard ones as observed
    rows, like JP's 15y). The file is published with a
    two-week lag; if the latest calendar month has no observation, that
    month is missing and coverage shows it.

**Test** `tests/test_loader_ca.py` on `tests/fixtures/boc/zero_curve.csv`.
- `test_units_ca` — the decisive one: `yield.max() > 0.001` fails if the
  loader divides by 100.
- `test_tenors_ca` (`{0.25, 0.5, 0.75, 1.0, …, 30.0}`, 120 tenors), `test_dates_ca`,
  `test_no_duplicates_ca`.
- `test_na_is_missing`: `na` → NaN.
- `test_no_division_by_100`: a fixture cell `0.0226506` is returned as
  `0.0226506`, not `0.000226506`.

**Done when** the six tests pass and coverage has CA rows.

## Step 1.6 — France: Banque de France TEC constant-maturity yields

**Build**
- `src/curvecarry/loaders/fr.py`. Ten daily series on Webstat,
  `FM.D.FR.EUR.FR2.BB.FRMOYTEC<N>.HSTA` for `N ∈ {1,2,3,5,7,10,15,20,25,30}`,
  read from the Explore API catalog dataset **`observations`** filtered by
  series key (amended 2026-09-22 after step 1.6 found the per-tenor catalog
  datasets `fm-d-fr-eur-fr2-bb-frmoytec<N>-hsta` to be empty shells,
  `has_records: false`, with and without the key):
  `GET https://webstat.banque-france.fr/api/explore/v2.1/catalog/datasets/observations/exports/csv?where=series_key="FM.D.FR.EUR.FR2.BB.FRMOYTEC<N>.HSTA"`
  with the key sent as the `Authorization: Apikey <key>` header (never as a
  query parameter, so it is never in a URL, the manifest or a log; the
  `observations` dataset returns 404 without it). Raw
  `data/raw/bdf/tec<N>_<date>.csv`, source `bdf`; the manifest URL carries
  the `where` clause and nothing else.
  - `fetch(cfg)`: key from `os.environ["BDF_API_KEY"]` only — raises
    `RuntimeError("BDF_API_KEY not set")` otherwise; never reads a file for
    it; never logs it. **The API returns HTTP 200 with zero rows when the
    key is missing or invalid**, so `fetch` counts data rows in the body and
    raises `RuntimeError("empty export")` rather than writing an empty raw
    file.
  - `parse(paths)`: the export is a semicolon csv with `series_key,
    time_period, obs_value, obs_status` (status `M` rows carry no value:
    non-trading days, dropped); one series per file, its tenor read from
    the key; `/ 100`; long frame `obs_date, tenor_years, yield`.
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
    for `A ∈ {US, GB, JP, CA, XM, DE, FR}` (XM = euro area from 1999-01;
    `DE` and `FR` are the national series, both discontinued at 1998-12,
    probed 2026-09-16: DE 1948-07 → 1998-12, FR 1945-01 → 1998-12 —
    amendment D). Raw
    `data/raw/bis/CBPOL_<A>_<date>.csv`, source `bis`. SDMX-CSV:
    `TIME_PERIOD` (`YYYY-MM`), `OBS_VALUE` in percent → `/ 100`; stamped to
    calendar month end. The BIS monthly value is the end-of-month rate; the
    step confirms this from the BIS metadata and records it in the docstring.
  - 3-month interbank (robustness, `funding_rate_robustness = "interbank_3m"`):
    FRED `IR3TIB01USM156N, IR3TIB01GBM156N, IR3TIB01JPM156N, IR3TIB01CAM156N, IR3TIB01EZM156N`,
    raw `data/raw/fred/<series>_<date>.csv`, `/ 100`, first-of-month dates
    stamped to that month's end.
  - `load(cfg) -> pd.DataFrame` → `data/interim/short_rates.parquet` with
    columns `date, area, rate, kind, source`; `area ∈ {US,GB,JP,CA,XM,DE,FR,EZ}`
    (the BIS / OECD area code), `kind ∈ {policy, interbank_3m}`.
  - `build_funding(cfg) -> pd.DataFrame` → `data/interim/funding.parquet`
    (the Funding table in Conventions): one row per `(country, date, kind)`
    for every country in `config.countries` **and** the base currency's
    country. `currency = config.currency[country]`. For `policy`: a euro
    country takes `area = config.hedge.eur_legacy[country]` for dates
    `< config.hedge.eur_splice` and `area = XM` from the splice month end;
    every other country takes its own area. For `interbank_3m`: the OECD
    series of its currency (`EZ` for EUR; nothing before 1994-01 and
    nothing national — the robustness column is one series type).
    A missing `interbank_3m` rate is a missing row, never filled.
  - **Policy-rate gaps (Session 1 part A review, 2026-09-22):** the BIS JP series
    has no value for 116 months (1999-03..2000-07, 2001-04..2006-02,
    2013-05..2016-08). For `policy`, any month inside the BIS series' span
    with no BIS value is filled from the OECD immediate (overnight call)
    rate, FRED `IRSTCI01{US,GB,JP,CA,EZ}M156N` (raw
    `data/raw/fred/<series>_<date>.csv`, `/ 100`, month-end stamped), with
    `source = "fred_immediate"` on the filled row so the fill is visible in
    every row. A month with a BIS value is never overwritten. All five
    series are fetched so the rule is the same for every currency.
    `data/checks/funding_fill.csv` (`country, first, last, months_filled`)
    lists every filled run. `decisions/short_anchor.md` has the JP windows.
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
    with a row for the base currency at `spot = 1.0`. `DEXUSEU` starts
    1999-01: there is no EUR spot before it, so DE and FR **unhedged**
    returns are missing before 1999-01 (their hedged returns are not —
    under amendment A the hedged return needs no FX). Recorded in
    coverage, never filled (amendment D).
- `data/checks/coverage.csv` gets rows with `country = <cc>` and
  `curve_type = funding_policy` / `funding_interbank_3m` (one per country,
  showing the DE/FR splice as a continuous series) and
  `country = <currency>`, `curve_type = fx` (`stage = observed`).

**Test** `tests/test_loader_short_rates.py`, `tests/test_loader_fx.py` on
`tests/fixtures/bis/*.csv`, `tests/fixtures/fred/IR3TIB01*.csv`,
`tests/fixtures/fred/DEX*.csv`.
- `test_units_policy`, `test_units_interbank`: rates in `[-0.05, 0.5]`,
  `max > 0.001`.
- `test_funding_table_covers_every_country_and_kind`: `(country, kind)`
  is the full 6 × 2 (plus the base country if not in the universe).
- `test_eur_splice`: on a synthetic DE, FR and XM series, a DE row dated
  1998-12-31 equals the DE series, a DE row dated 1999-01-31 equals XM;
  the same for FR; a US row never reads the euro series.
- `test_month_end_stamp`: every `date` is a calendar month end.
- `test_fx_direction`: on the fixtures with USD base, GBP `spot` in
  `[1.0, 3.0]`, EUR in `[0.8, 1.7]`, JPY in `[0.002, 0.015]`, CAD in
  `[0.6, 1.1]`; base row is exactly 1.0.
- `test_fx_non_usd_base`: with `base_currency = "GBP"` on the same fixtures,
  `spot_USD × spot_GBP(USD base) == 1` to 1e-12 on matching dates.
- `test_fx_last_observation_of_month`: synthetic month → last value.
- `test_policy_gap_filled_from_immediate_and_labelled` (2026-09-22): a
  planted 3-month hole in a synthetic BIS series is filled from the
  immediate series with `source = fred_immediate` and appears as one run in
  `funding_fill_rows`; `test_bis_value_never_overwritten`: a month with a
  BIS value keeps it even when the immediate rate differs, and the fill
  never extends a series past its first or last BIS month.

**Done when** the ten tests pass and `data/interim/short_rates.parquet`,
`data/interim/funding.parquet`, `data/interim/fx.parquet` exist with the
coverage rows and `data/checks/funding_fill.csv`.

## Step 1.8 — Harmonise: one panel, the 8 standard tenors marked

**Build**
- `src/curvecarry/interp.py`:
  `interpolate_yield(tenors: np.ndarray, yields: np.ndarray, target: float | np.ndarray) -> float | np.ndarray`
  — the one interpolation function (rule 13). Linear in tenor between the
  two adjacent observed tenors; exact at an observed tenor; **NaN** for any
  target outside `[tenors.min(), tenors.max()]`; NaN inputs dropped first;
  raises `ValueError` if fewer than 2 finite points. `Curve.at` calls it
  inside the observed range and applies the flat short end below it
  (Conventions; the flat rule is in `Curve.at`, never here).
- `src/curvecarry/harmonise.py`:
  - `standard_tenors(cfg) -> list[float]` = `config.tenors`.
  - `to_standard(curve_df: pd.DataFrame, cfg) -> pd.DataFrame`: per
    `(country, date)`, keeps every observed tenor and adds the standard
    tenors that are not observed: `interpolate_yield` where the tenor lies
    between observed tenors, NaN (row absent) beyond the longest or before
    the shortest observed. Adds `interpolated: bool` and
    `standard: bool` (`tenor_years ∈ config.tenors`).
  - No funding row is added to any curve (amendment B; v1's `add_anchor`
    is withdrawn). The funding rate is joined by `(country, date)` from
    `funding.parquet` where it is needed (4.1, 4.2).
  - `build(cfg) -> pd.DataFrame` → `data/processed/curves.parquet`:
    CurveFrame columns + `interpolated`, `standard`. Countries from
    `config.countries`. Coverage `stage = harmonised` for the 8 standard
    tenors.
  - Dates: the panel index is the union of month ends across countries; a
    country-month absent in the source is absent here (no forward fill).
  - **Partial month (Session 1 part B amendment, 2026-09-22):** `build` keeps
    only months `<= config.sample.strategy_end` in
    `data/processed/curves.parquet` (and therefore in
    `curves_zero.parquet`). `data/interim/` is unchanged and still carries
    the partial current month. Coverage rows for `stage = harmonised`
    reflect the cut.
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
  all 8 standard, none interpolated; to 25 → no 30y row.
- `test_non_standard_tenors_kept`: US-like input with 0.25 and 0.5 keeps
  them with `standard == False`; JP-like input keeps 15, 25, 40.
- `test_no_funding_row_on_curve`: no row whose `source` is `bis` or whose
  `tenor_years` is not from the loader's own observed set or
  `config.tenors`.
- `test_one_curve_type_per_country_month`.
- `test_no_forward_fill`: a missing month stays missing.
- `test_panel_stops_at_strategy_end` (Session 1 part B amendment): a synthetic
  panel with months after `strategy_end` keeps none of them; the month
  equal to `strategy_end` is kept.

**Done when** the ten tests pass and `data/checks/coverage.csv` has
`harmonised` rows for 6 countries × 8 standard tenors.

## Step 1.9 — Par to zero, the two sample windows, the gate

**Build**
- **Par conventions first (Session 1 part B amendment, 2026-09-22).** Before the
  bootstrap is built, `decisions/compounding.md` gets a section "Par
  yields" quoting each source's own statement of how its par series is
  quoted: US FRED constant maturity (Treasury par yield curve,
  semi-annual bond-equivalent); Banque de France TEC (taux actuariel,
  annual); MOF JGB (compound or simple, and whether that differs before
  1986 or at any other date). It also records that TEC and MOF yields are
  yields to maturity on actual bonds treated as par yields, and what that
  approximation is. A convention not stated in a reachable source is a
  `decision` issue, and 1.9 is not built until it is answered; 1.8 does
  not depend on it.
- `src/curvecarry/bootstrap.py`:
  - `bootstrap_par_to_zero(par: Curve, freq: int) -> Curve`: asserts
    `par.curve_type == "par"`. Coupon dates `t_k = k / freq` for
    `k = 1 … freq × T_max` where `T_max` is the longest observed par tenor.
    Par yield at each `t_k` by `par.at(t_k)`: `interpolate_yield` over the
    observed par tenors, and **flat at the shortest observed par yield
    for `t_k` below it** (`config.short_end = "flat"`; JP and FR have no
    tenor below 1, US has 0.25 and 0.5 from 1981-09 — amendment B). For
    `t_k ≤ 1/freq` (single-cashflow bond) `z = c` with `c` the par yield
    at `t_k` (converted from the coupon-frequency convention to annual:
    `z = (1 + c/freq)^freq − 1`). For later `t_k`:
    `DF_k = (1 − (c_k/freq) · Σ_{j<k} DF_j) / (1 + c_k/freq)`, `z_k = DF_k^(−1/t_k) − 1`.
    Returns the zero curve **at every coupon-grid point `t_k` inside
    `[T_min, T_max]`** as `Curve(curve_type="zero")` (Session 1 part B fix 1,
    issue #10 A, answer a, 2026-09-22: the plan's earlier "observed par
    tenors plus the 8 standard tenors" cannot reprice a 20y or 30y bond
    within 0.005 — the zeros between 10, 20 and 30 would be re-interpolated
    linearly — while the full grid reprices every observed par bond to
    1e-10). Grid points below `T_min` are not returned: the par is flat
    there by convention, so their zeros all equal `z(T_min)` and `Curve.at`
    reproduces them. **An observed par tenor below the first coupon date**
    (the US 0.25 bill, `freq = 2`) gets the money-market identity
    `z = (1 + c·t)^(1/t) − 1` (#10 B, answer a: a bill's bond-equivalent
    yield `c` is defined by `P = 1/(1 + c·t)`), with its own test. Tenors
    beyond `T_max` are absent (rule 13). In `curves_zero.parquet` a
    bootstrapped month therefore carries 60 US / 80 JP / 30 FR rows;
    `standard` marks the 8 standard tenors and `interpolated` marks a grid
    point that was not an observed par tenor. Phase 2 fits use
    `standard == True` only; `Curve.from_panel` keeps every row of a
    bootstrapped month (its grid is the curve).
  - **No bootstrap across a wide node gap (Session 1 part B fix 2, 2026-09-22).**
    For a par country the bootstrap for a `(country, date)` runs only to
    the longest observed par tenor `T` such that no two consecutive
    observed par nodes up to `T` are more than
    `config.bootstrap_max_node_gap_years` (10) apart
    (`bootstrap.node_gap_cutoff`). Tenors beyond `T` are absent from
    `curves_zero.parquet` (rule 13), not interpolated. For the US this
    removes the 20y and 30y zeros for 1987-01..1993-09 (DGS20 unpublished;
    the 1.8 panel's interpolated 20y is not a node). Recorded in
    `decisions/sources.md` → "Bootstrap node-gap rule".
  - **Ill-conditioned long end (Session 1 part B fix 3, 2026-09-22; the rule was
    replaced in fix round 2, same date).** After bootstrapping each
    `(country, date)` (to the node-gap `T`), if
    `|zero(T) − par(T)| > config.bootstrap_zero_par_tolerance_bp` (100) at
    any standard tenor `T ≥ bootstrap.ZERO_PAR_MIN_TENOR` (10) that is
    **also an observed par node**, the zeros at `T` and beyond are dropped
    for that month (`bootstrap.bootstrap_month`). Comparing at observed
    nodes only means nothing the interpolator invented can trip the rule.
    **The withdrawn rule** compared the 1-year forward rates on the coupon
    grid with par and used `bootstrap_forward_tolerance_bp = 300`; it
    measured the step function that linear par interpolation makes of the
    forward curve and dropped 46 months after `strategy_start` that were
    ordinary steep curves. `decisions/sources.md` → "Bootstrap long-end
    rules" has the withdrawal, the 100 bp choice (made after seeing the
    data) and the threshold band.
    `data/checks/bootstrap_dropped.csv`: one row per country-month and
    reason that dropped tenors — `country, date, reason` (`node_gap` or
    `zero_par`), `first_tenor_dropped`, and for `zero_par` the `zero`,
    `par` and `gap_bp` at the breaching node. The fix comment reports
    months dropped by country, decade and reason, how many fall on or
    after `strategy_start`, and the threshold band that leaves them
    unaffected.
  - **US bootstrap check (Session 1 part B amendment, 2026-09-22).**
    `src/curvecarry/loaders/gsw.py` fetches the Federal Reserve's
    Gürkaynak–Sack–Wright zero curve,
    `https://www.federalreserve.gov/data/yield-curve-tables/feds200628.csv`,
    to `data/raw/gsw/feds200628_<date>.csv` (source `gsw`, in the manifest).
    Its `SVENYnn` zero yields are continuously compounded (the file's own
    header says so) and percent: `/ 100`, then `exp(z) − 1`; month-end
    sampled like the curves. `build` writes
    `data/checks/us_zero_vs_gsw.csv`: `date, tenor_years, zero_bootstrap,
    zero_gsw, diff_bp` at 2, 5, 10 and 30 years every month both exist.
    A check, not a test gate; its distribution is reported in the session
    review. `tests/fixtures/gsw/feds200628.csv` (header + 50 rows) and
    `test_gsw_units_and_compounding`.
  - **GSW diagnostics, reported only (Session 1 part B fix 4, 2026-09-22; no rule
    changes).** `gsw.parse_par` reads the GSW par yields `SVENPYnn`
    (coupon-equivalent — the CMT basis — so `/ 100` and nothing else) to
    `data/interim/gsw_us_par.parquet`; `test_gsw_par_units`. `build` also
    writes, to `strategy_end`: (a) `data/checks/us_par_vs_gsw.csv` —
    `date, tenor_years, par_cmt, par_gsw, diff_bp, interpolated` at 2, 5,
    10 and 30 years every month both exist (the input difference, apart
    from the bootstrap); (b) `data/checks/bootstrap_on_gsw.csv` — the GSW
    par curve at every integer tenor the fit reaches, `freq = 2`, through
    `bootstrap_grid` (no node-gap or forward rule) against the GSW zeros
    (`exp(z) − 1`) at the same four tenors: `date, tenor_years,
    zero_bootstrap_gsw, zero_gsw, diff_bp` (the bootstrap's own error on a
    smooth curve). `test_gsw_diagnostics_shapes`. The fix comment
    summarises (a) per tenor since 2000 and by decade (mean, sd, p5, p95)
    and (b) per tenor (mean, max absolute diff in bp).
- CLI `build --step zero`.

**Test** `tests/test_bootstrap.py` (synthetic).
- `test_flat_par_gives_flat_zero`: a flat 4% par curve (freq 1 and freq 2,
  tenors 1, 2, 3, 5, 7, 10, 20, 30 — no sub-1y tenor, so the stubs use
  the flat rule) gives zero yields equal to
  `(1 + 0.04/freq)^freq − 1` at every tenor to 1e-12 (exactly 0.04 for
  freq 1).
- `test_reprice_par_bonds_at_100`: an upward-sloping par curve
  (2% at 1 to 5% at 30, and again with 0.25 and 0.5 observed) bootstrapped,
  then each observed par bond priced
  off the returned zero curve (`bondmath` is 2.1; this test uses a local
  cashflow-sum helper in the test file) is within 1e-9 of 100 (Session 1
  part B fix 1: the returned curve is the coupon grid, so the bound is
  exact).
- `test_bill_zero_is_money_market_identity` (Session 1 part B fix 1, #10 B): with
  0.25 observed at yield `c`, the returned 0.25 zero is
  `(1 + c·0.25)^4 − 1`, not `(1 + c/2)^2 − 1`, and every other zero is
  unchanged from the curve without the 0.25 point.
- `test_zero_source_passes_through`: a `zero` input is returned identical.
- `test_par_assertion`: passing a `zero` curve raises `AssertionError`.
- `test_no_tenor_beyond_longest_par`: par curve to 10y gives no 20 or 30.
- `test_no_bootstrap_across_wide_node_gap` (Session 1 part B fix 2): nodes
  {1, 2, 3, 5, 7, 10, 30} give no zero beyond 10; nodes
  {1, 2, 3, 5, 7, 10, 20, 30} give all; a gap of exactly 10 years is
  allowed; the zeros to 10y are identical with and without the cut.
- `test_ill_conditioned_long_end_is_dropped` (Session 1 part B fix round 2): a
  flat 15% par curve keeps every tenor (the zero is 56 bp above par at
  every tenor, from semiannual compounding alone); the same curve with a
  10 bp kink down in the 20y par yield keeps the 20y (33 bp) and drops
  the 30y (138 bp); the surviving zeros equal the unrestricted
  bootstrap's; a steep par curve rising 1.5% over 29 years drops nothing
  (64 bp at 30y), while one rising 2.0% is 105.6 bp at 30y and does drop
  it (recorded, not tuned around); a tenor ≥ 10y that is not an observed
  par node is never checked.
- `test_node_gap_and_zero_par_rows` (Session 1 part B fix round 2): a node-gap
  cut writes one `node_gap` row naming the first grid tenor beyond the
  cutoff, with `zero`, `par` and `gap_bp` blank.
- `test_short_stub_is_flat_at_shortest_par`: with tenors from 1y and
  freq 2, the 0.5y discount factor equals the one implied by the 1y par
  yield; with 0.5 observed it equals the one implied by the 0.5 par yield;
  with 0.25 observed the returned zero curve has a 0.25 point.
- `test_sample_window_rule`: a synthetic coverage panel with a known first
  5-of-6 month and first 6-of-6 month gives those two dates.

**Done when** the fourteen tests pass, `data/checks/par_zero_gap.csv`,
`data/checks/us_zero_vs_gsw.csv` and `data/checks/sample_window.txt`
exist, and `config.toml` has both dates.

**Gate.** The owner reviews `data/checks/coverage.csv` and
`data/checks/par_zero_gap.csv` and the two dates before any Phase 2 step
is started. The pass is recorded in `CLAUDE.md` → Validation status.

**Session 1 part B review issue (amendment, 2026-09-22)** must contain, besides
the usual sections:
- `strategy_start` and `sample_full_start`, and for each country the
  first month it has all standard tenors ≤ 10y.
- A table per country and standard tenor: first and last harmonised
  month, months present, months missing, and whether any value is
  interpolated.
- `par_zero_gap.csv` summarised per country at 10y and 30y by decade:
  mean, 5th and 95th percentile, max absolute gap in bp.
- `us_zero_vs_gsw.csv` summarised per tenor: mean, standard deviation,
  5th and 95th percentile, max absolute diff in bp, and the 5 worst months.

---

# Phase 2 — Curve models

All fits use the **zero** panel `curves_zero.parquet` at the 8 standard
tenors (`standard == True`); non-standard observed tenors are not fitted.
A country-month with fewer than `config.nelson_siegel.min_tenors` (5)
non-null standard tenors is not fitted and is counted in
`data/checks/fit_skipped.csv`.

**Session-2 amendment 3 (2026-09-22), across 2.2 and 2.3.** Fits still use
the 8 standard tenors only. `data/checks/fit_holdout.csv`: for GB, CA and JP,
every month and every observed non-standard tenor between 1 and 30 years
(`interpolated == False`), the NS-free, NS-DL and Svensson fitted yield
against the observed zero, and the error in bp. For US and FR the
bootstrapped non-standard coupon-grid zeros are used instead and labelled
`bootstrapped` in the `zero_kind` column. (JP's own zeros are bootstrapped
too, so its rows carry `zero_kind = bootstrapped` although it is selected by
the `interpolated == False` rule; DE is in neither list, its whole curve
being reconstructed from the Bundesbank's parameters.) `holdout_summary`
reports, per country and model, the median and p95 of the monthly held-out
RMSE next to the in-sample RMSE. The file is written by 2.2 with the two NS
models in it and rewritten by 2.3 with all three.

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
    `curve.at(t_j)` is NaN (above the longest observed tenor; below the
    shortest `Curve.at` is flat by convention, so a seasoned bond's short
    stub always prices).
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

**Session-2 amendment 1 (2026-09-22).** `Curve.from_panel` for zero curves
keeps every coupon-grid point in `curves_zero.parquet`, not only the
standard tenors (already true since the Session 1 part B fix to issue #10 A;
restated here so it cannot be lost). `write_par_reprice(cfg)` →
`data/checks/par_reprice.csv`: for every US, JP and FR month and every
observed par node, the observed par yield, `par_yield_from_zero(Curve.from_panel(...))`
and `diff_bp`, with a `status` of `ok`, `money_market` (an observed node
below the first coupon date, whose zero came from the simple-interest
identity) or `dropped` (a node beyond that month's zero curve after the 1.9
node-gap and zero-vs-par rules). **Expected max |diff| below 0.01 bp; if it
is larger, stop and report before 2.2.** Measured: 3.4e-12 bp (US), 3.1e-12
(JP), 1.9e-12 (FR) — see `review/2.1.md`.

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
- `test_short_end_is_flat_not_nan`: a zero curve observed from 1y,
  `curve.at(0.5) == curve.at(1.0)` exactly and is finite; `curve.at(31)`
  with max tenor 30 is NaN; a curve observed from 0.25 interpolates at 0.5.

**Done when** the eight tests pass.

## Step 2.2 — Nelson-Siegel

**`config.nelson_siegel.ns_lambda_grid` may be changed in this step** (issue
#12, answered 2026-09-22; the one exception to rule 14 for this key, and only
here and in 2.3). It was widened from `[0.2, 1.5, 0.05]` to
`[0.05, 1.5, 0.05]` because the fits themselves said the lower bound was
binding: the Bundesbank's own lambda lay outside `[0.2, 1.5]` in 69.9% of DE
months (`data/checks/svensson_vs_bundesbank.csv`), 51.9% of those breaches at
the bottom, and our own NS-free lambda sat on a bound in 8.9% (DE) to 40.5%
(JP) of months with roughly nine in ten of those at 0.2. The upper bound is
unchanged: a published lambda above 1.5 is a month where tau collapses, not a
curve the fit needs to reach. The change is its own commit. Any further
widening needs a new decision issue, and **if lambda pins at the new lower
bound in more than 10% of months for any country the session stops and posts
one** rather than widening again.

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

**`ns_lambda_grid` may be changed in this step too** — see 2.2 for the reason
and the stop condition. 2.2 and 2.3 are always re-run together on a new grid.

**Session-2 amendment 2 (2026-09-22).** In `compare_bundesbank`, convert the
Bundesbank's `(tau1, tau2)` to the lambda form and, where `1/tau2 < 1/tau1`,
swap the labels (and `beta2` with `beta3`) so that both sides use
`lambda2 > lambda1` before the betas and lambdas are compared;
`swapped` records it per month. **The swap is a labelling convention, not an
identity** — `lambda1` carries the slope loading as well as the first
curvature, so it preserves the curve only when `beta1 = 0` — therefore
`rmse_bbk_bp` is scored from the *original, unswapped* parameters, which is
what makes it 0 by construction. Report the distribution of the
Bundesbank's `1/tau1` and `1/tau2` (p5, median, p95) and the share of DE
months where either lies outside `config.nelson_siegel.ns_lambda_grid`.
**If that share is above 10%, post a `decision` issue on whether to widen the
grid and do not build 2.4 until it is answered.** Measured: 69.9% (1/tau1
39.0%, 1/tau2 55.0%), so issue #12 is open and 2.4 is not built.
`test_de_fit_recovers_bundesbank_curve` uses a fixture row whose lambdas lie
inside the grid; `test_de_fit_for_a_row_outside_the_grid` documents what
happens for a row outside it.

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
    Dates: for each decade in `config.report.chart1_decades` the last December
    month end with a fit; where a decade has fitted months but no fitted
    December, its last fitted month. **Amended 2026-09-23 (session 2 fix
    round):** where a country has **no** fitted month in a decade, `chart1_dates`
    emits **no row** — the file holds only real dates — and the panel is drawn
    empty, captioned "no fitted months in this decade". The earlier rule fell
    back to the country's earliest fitted month, which put France's 2004-11-30
    curve under a panel headed by the 1990s. The chosen dates go to
    `data/checks/chart1_dates.csv` (`country, decade, date`; 23 rows, not 24).
  - `chart1_rmse(ns_params, sv_params, out) -> Path`:
    `reports/figures/chart1_rmse.png`, 6 panels, RMSE (bp) by month, NS-free
    vs NS-DL vs Svensson.
  - `chart3_betas(ns_params, out) -> Path`: `reports/figures/chart3_betas.png`,
    one line per country, 1995 to the last month. **Amended 2026-09-23, issue
    #14 option K** (the original said 3 panels of NS-free betas): **6 panels,
    two rows.** The top row is β0, β1, β2 from **`ns_dl`**, the fixed-λ model,
    and is the primary series — with a free λ the betas are coefficients on
    loadings whose shape changes month to month, so the same numeric value in
    two months is not the same quantity and the series is not comparable
    across time or countries; fixing λ is what makes it comparable, and is why
    Diebold-Li fix it. The bottom row is the same three betas from `ns_free`
    with every `ns_degenerate` month **left as a gap** — not clipped, not
    interpolated, not forward-filled — and the gap count per country in the
    caption. **`ns_degenerate`** (session 2 fix round, 2026-09-23) is
    `lam_at_bound` **or** `max(|β0|, |β1|, |β2|) > 0.5`, i.e. 50 percentage
    points of yield: a λ just inside the bound leaves the loadings nearly
    collinear, so a bound-only criterion let runaway betas through (GB
    2010-02-28, λ = 0.0539, β2 = +50.2%, RMSE 3.19 bp). It is a column on
    `ns_params.parquet` for every model, beside `lam_at_bound`, which is kept
    because `decisions/lambda_bound.md` refers to it.
    `data/checks/chart3_excluded.csv` lists every excluded country-month with
    its λ, its betas and a `reason` of `bound`, `beta` or `both`. **No percentile clipping
    anywhere.** Chart 1 and `chart1_rmse` are unchanged and keep NS-free:
    what they measure is fit quality, which is where a free λ earns its place.
    Reasoning in `decisions/lambda_bound.md`.
- CLI `report --charts 1,3` (partial report; the full `report` is 6.4).

**Test** `tests/test_charts.py` (synthetic frames, `tmp_path`).
- `test_chart1_dates_rule`: a synthetic fit table with gaps picks the last
  December per decade and the earliest month for a missing decade.
- `test_chart_functions_write_files`: each function writes a non-empty png.
- `test_chart3_excludes_degenerate_months_as_gaps` (issue #14, amended in the
  fix round): a bound-only, a beta-only and a both month are each absent from
  the NS-free series, none is interpolated across, and each is one row of
  `chart3_excluded.csv` with the right `reason`; the `ns_dl` series keeps every
  month.

**Done when** the three tests pass and the 8 pngs,
`data/checks/chart1_dates.csv` and `data/checks/chart3_excluded.csv` exist.

---

# Phase 3 — PCA

## Step 3.1 — PCA on monthly yield changes

**Session-3 amendment 1 (2026-09-23, as answered in issue #15): the tenor
set is chosen, not fixed.** PCA needs a fixed tenor set, so it is chosen
**per country**: the largest set of standard tenors (`config.tenors`)
present in at least `config.pca.tenor_presence_min` (0.95) of that country's
months, counted **from the first month the country has a 10-year zero**.
The **pooled** set is the intersection of the six country sets.

That last clause is the owner's ruling of 2026-09-23 (issue #15, option C)
and it is **a different rule from the one written in
`instructions/session-3.md`**, not a different window for it. The
instruction said "from the first month it enters the panel". Read that way
JP entered in 1974-09 with a curve that stopped at 7 years, its 10-year
point was present in only 77.2% of its months, its set came out
`1, 2, 3, 5, 7` and the pooled intersection came out 5 tenors — which
tripped the amendment's own stop condition and left amendment 2's "PC1
positive at 10 years" undefined. A country enters the panel, for the purpose
of this rule, when it enters it **with a curve rather than a stub**: the
first month it has a 10-year zero. JP's panel therefore starts 1986-07;
every other country's first 10-year month is its first panel month already.

**Stop condition (kept, for a re-run on changed data):** if any country's
set has fewer than 5 tenors, or the pooled set has fewer than 6, the step
stops and a `decision` issue is posted. On the data of 2026-09-23 it does
not fire: the sets are US and GB `1, 2, 3, 5, 7, 10`; JP, CA and FR
`1, 2, 3, 5, 7, 10, 20`; DE all 8; **pooled `1, 2, 3, 5, 7, 10`**, 6 tenors.

`data/checks/pca_tenor_sets.csv`
(`country, tenors_used, tenors_excluded, months_available, months_dropped_missing_tenor`)
records the choice and names the excluded tenors.

**Two pooled fits, and which one is load-bearing (issue #15 answer 5).**
- **`pooled`, the primary fit**, on the intersection `1, 2, 3, 5, 7, 10`
  over every month each country has complete on that set. **This is the
  pooled fit every later step reads** — the PC1 vol control of 6.2 and the
  PC2 z-score of 5.4 take their scores from `scope == "pooled"` and from
  nothing else.
- **`pooled_20y`, a secondary fit, reported only**, on
  `1, 2, 3, 5, 7, 10, 20` over the months in which **all six** countries
  have a 20-year zero. That window starts at the later of France's first
  month and the end of the US 20-year gap (`1993-09`), so it is France's
  start, `2004-11-30`, and runs to `strategy_end` with no gaps. Its
  explained variance, loadings and month count are reported beside the
  primary fit in the session review and in `pca_explained.csv`. **No step
  after 3.3 may read it.**

**Session-3 amendment 3 (2026-09-23): the input.** The input is the **zero**
curves of `data/processed/curves_zero.parquet` in basis points of monthly
change — never the fitted NS or Svensson yields of Phase 2. A month enters
only if **both it and the previous calendar month** carry every tenor in the
set, so a gap is never bridged into a multi-month change reported as a
one-month one.

**Build**
- `src/curvecarry/pca.py`:
  - `tenor_sets(zero_panel, cfg) -> dict[str, list[float]]` and
    `write_tenor_sets(...)` → `data/checks/pca_tenor_sets.csv` (amendment 1);
    raises `TenorSetTooSmall` naming the scope when the stop condition fires.
  - `monthly_changes_bp(zero_panel, cfg) -> dict[str, pd.DataFrame]`: wide per
    country, index `date`, columns that country's tenor set,
    `Δy_t = (y_t − y_{t−1}) × 1e4` where `t−1` is the previous calendar
    month end **and both months are present at every tenor in the set**;
    otherwise the row is dropped and counted in `data/checks/pca_dropped.csv`
    (`country, n_months_total, n_dropped, reason`). Non-standard tenors and
    standard tenors outside the set are excluded.
  - `pca(changes: np.ndarray, tenors) -> PCAResult`: demean by column;
    `S = np.cov(X, rowvar=False, ddof=1)`; `w, V = np.linalg.eigh(S)`;
    sort descending; sign rule per component (**amendment 2**, restated for a
    variable set): PC1 loading at **10 years** > 0; PC2 loading at
    **(longest tenor in the set) − 2 years** > 0; PC3 loading at the
    **middle tenor of the set** > 0; PC4+ first non-zero element positive.
    The middle tenor of a set of even size is the lower of the two middle
    entries. A set that does not contain the tenor a rule names is a stop,
    not a fallback; under amendment 1 as answered, 10 years is in every one
    of the seven scopes, so amendment 2 stands exactly as written.
    `PCAResult(loadings (n×n), eigenvalues, explained (= w / w.sum()), mean, scores)`.
  - `fit_country(cfg) -> None` and `fit_pooled(cfg, tenors, scope) -> None`:
    pooled = each country's changes **on the pooled set** demeaned by its own
    column means, stacked as rows, one PCA; scores per country-month = that
    country's demeaned row `@ V`. Called twice: `scope = "pooled"` on the
    intersection, and `scope = "pooled_20y"` on `1, 2, 3, 5, 7, 10, 20`
    restricted to months every country has complete (the secondary fit).
  - Outputs `data/processed/pca_loadings.parquet`
    (`scope ∈ {US,…,FR,pooled}, component, tenor_years, loading`),
    `data/checks/pca_explained.csv` (`scope, component, eigenvalue, explained_share, n_months`),
    `data/processed/pca_scores.parquet` (`scope, country, date, component, score`).
    `component` runs 1..n for a set of n tenors, so it is no longer 1–8 for
    every scope.
- CLI `build --step pca`.

**Test** `tests/test_pca.py` (synthetic).
- `test_explained_sums_to_one`: to 1e-12.
- `test_scores_reconstruct_changes`: `scores @ V.T + mean == changes` to
  1e-10 with all components.
- `test_sign_rules`: after normalisation the three inequalities hold, on a
  set whose longest tenor is not 30 and whose middle tenor is not 10.
- `test_three_factor_data_gives_three_components`: data generated from 3
  factors → explained shares 4+ sum < 1e-10.
- `test_missing_tenor_month_dropped_and_counted`.
- `test_gap_month_is_not_a_multi_month_change` (**amendment 3**): a panel with
  one month removed yields no change row spanning the gap; the month after
  the gap is dropped and counted.
- `test_tenor_set_is_the_95pct_set`: a synthetic country whose 30y is present
  in 94% of months excludes 30y and keeps the rest.
- `test_tenor_set_too_small_raises`: a pooled intersection of 5 tenors raises
  `TenorSetTooSmall`.
- `test_pooled_scores_are_per_country_month`: pooled score frame has one
  row per `(country, date, component)`.

- `test_secondary_pooled_is_a_separate_scope`: `pooled` and `pooled_20y`
  are both present, on different tenor sets, and `pooled` is the
  intersection.

**Done when** the tests pass and `pca_tenor_sets.csv`, `pca_dropped.csv`,
`pca_explained.csv`, `pca_loadings.parquet` and `pca_scores.parquet` exist
with six country scopes, `pooled` and `pooled_20y`.

## Step 3.2 — Loading stability by decade

**Build**
- `pca.stability(cfg) -> pd.DataFrame` → `data/checks/pca_stability.csv`:
  per country and decade (`1960s`…`2020s`, each `<yyyy>-01..<yyyy+9>-12`),
  PCA on that decade's changes alone (same sign rules, the country's own
  tenor set), and, for k = 1, 2, 3,
  **`abs_cosine = |v_k^decade . v_k^full|`** — the uncentred inner product of
  two unit eigenvectors — as the statistic of record, with
  `abs_corr = |corr(v_k^decade, v_k^full)|`, the Pearson version, kept
  beside it as a secondary column. Columns
  `country, decade, component, n_months, abs_cosine, abs_corr,
  explained_share_decade, us_borderline_excluded`.
  A decade with fewer than `config.pca.stability_min_months` (24) months of
  changes is written with both statistics NaN and its `n_months`.

  **Why the swap (session-3 fix round, 2026-09-23; the original wording of
  session-3 amendment 4 named `abs_corr` and the owner has withdrawn it).**
  Pearson removes each vector's mean, and for a level factor the mean is
  almost the whole vector, so `abs_corr` on PC1 measures the *tilt* of the
  level loading rather than whether it is the same factor: the US 1990s
  reads `abs_corr` 0.075 while its PC1 never differs from the full-sample
  PC1 by more than 0.137 element by element and `abs_cosine` is 0.984. The
  cosine is the right statistic for two unit eigenvectors; `abs_corr` stays
  in the file because the tilt is a real and sometimes interesting fact
  about a decade, not because it answers the stability question.

**Session-3 amendment 4 (2026-09-23, relabelled by issue #15): the US
twice, as a robustness check.** Under amendment 1 as answered, the US set is
`1, 2, 3, 5, 7, 10` — **the 30-year is not in it.** A pre-1997 month with a
bad 30-year zero therefore enters the US PCA only through its 1- to 10-year
yields, and the Phase 1 gate's concern does not reach a loading at all. The
row is still computed and reported, as a robustness check rather than a
correction; `review/3.2.md` says it is moot and why, and the carry-forward
line in `CLAUDE.md` → Validation status is answered there so the Phase 1
gate question is closed rather than left open. The item `CLAUDE.md`
carries forward from the Phase 1 gate is settled here. The US decade rows
are written **twice**: once on all months (`us_borderline_excluded = False`)
and once excluding the pre-1997 months whose 30-year zero-to-par gap in
`data/checks/par_zero_gap.csv` exceeds
`config.pca.us_borderline_gap_bp` (50) (`= True`). Every other country
has the flag `False` only. The review says whether the **1980s** loading
vector changes materially between the two.

**Test** `tests/test_pca_stability.py` (synthetic).
- `test_self_correlation_is_one`: full sample vs itself → 1.0 to 1e-12.
- `test_stable_factor_structure_scores_high`: two decades drawn from the
  same 3-factor model → `abs_corr > 0.99` for PC1–3.
- `test_short_decade_is_nan_with_count`.
- `test_us_written_twice_with_flag` (**amendment 4**): the US has both flag
  values for every decade that has any excluded month; no other country does.

**Done when** the four tests pass and `data/checks/pca_stability.csv`
exists.

**Two new `config.toml` keys (2026-09-23).** Amendments 1 and 4 each name a
number that global rule 4 requires to live in `config.toml`, and rule 14
says step 0.1 writes every key the plan names. The two are therefore added
to `[pca]` and to `config.REQUIRED_KEYS` as part of this amendment, in a
commit of their own: `tenor_presence_min = 0.95` and
`us_borderline_gap_bp = 50`. Named in issue #15 so the owner can object
before they land.

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

**Session-4 amendment 2 (2026-09-23), the side this step owns.** The
long-run identity check `data/checks/return_identity.csv` compares the
annualised mean of `r_local` with the annualised mean of the expected return
this step computes. It needs both `carry.parquet` (here) and
`returns.parquet` (4.2), so **the file is written in 4.2** and its columns
are listed there. It is a check, not a gate: nothing about it stops a step.

**Build**
- `src/curvecarry/carry.py`, on `curves_zero.parquet` and
  `funding.parquet`, horizon `Δt = 1/12`:
  - per `(country, date, tenor n ∈ standard tenors)` with
    `Curve.from_panel` (all observed tenors of that country-month):
    `r_short` = `funding.parquet` at `(country, date, kind = config.hedge.funding_rate)`
    — never read off the curve (amendment B);
    `carry = y_n − r_short` (per year);
    `(c, D, C) = par_bond_risk(curve, n, freq)`;
    `y_roll = curve.at(n − Δt)`: between observed tenors, and for n = 1
    under the flat rule where no sub-1y tenor is observed, so JP's and
    FR's 1-year rolldown is exactly 0 (`decisions/short_anchor.md`);
    `rolldown = (y_n − y_roll) × D` (per horizon month, decimal);
    `expected_return_1m = carry × Δt + rolldown`.
  - Output `data/processed/carry.parquet`:
    `date, country, tenor_years, yield, r_short, carry, rolldown, duration, convexity, par_yield, expected_return_1m`.
    Rows where any input is NaN are dropped and counted in
    `data/checks/carry_missing.csv` (`country, tenor_years, n_missing,
    n_flat_short_end` — the last is the number of 1-year bucket-months
    where `n − Δt` fell below the shortest observed tenor).
- CLI `build --step carry`.

**Test** `tests/test_carry.py` (synthetic curves).
- `test_flat_curve_rolldown_zero`: flat curve → `rolldown == 0` to 1e-15,
  `carry == y − r_short`.
- `test_linear_curve_rolldown`: `y(τ) = a + bτ` → `rolldown == b × Δt × D`
  to 1e-12 for every tenor.
- `test_one_year_rolldown_uses_observed_short_end_else_flat`: with 0.5
  observed, `y_roll(1)` is the interpolation between 0.5 and 1 and
  `rolldown ≠ 0`; with nothing below 1, `y_roll(1) == y(1)` and
  `rolldown == 0` exactly, and `n_flat_short_end` counts it.
- `test_r_short_from_funding_table_not_curve`: changing the curve leaves
  `r_short` unchanged; changing the funding row changes `carry` one for
  one.
- `test_duration_is_par_bond_risk`: `duration` equals
  `bondmath.par_bond_risk(...)[1]` exactly.
- `test_missing_input_is_counted_not_filled`.

**Done when** the six tests pass and `data/processed/carry.parquet` exists.

## Step 4.2 — Return engine

**Session-4 amendment 1 (2026-09-23): the universe log.**
`data/checks/universe_by_month.csv`, one row per `(date, country)` over
every month of the panel that has a next month:
`date, country, n_tenors, tenors, n_total_all_countries`. A tenor is in
`tenors` when it has a **computable return** — a standard zero at
`(country, t, n)` and a curve at `t + 1` that reaches the aged tenor
`n − 1/12`, which is exactly the rows of `returns.parquet` with
`closed == False`. `n_total_all_countries` is that month's total across the
six countries and repeats on each of the month's rows. The review reports
the first and last month of every country-tenor bucket, every mid-sample
appearance or disappearance, and the bucket count by year.

**Issue #17, answered 2026-09-23: what `Δy` is, and what the tolerance is.**

1. **`Δy` is the change in the bond's own yield to maturity**,
   `yield_from_price(P, n − 1/12, c, freq) − c`. It is *not* the par yield at
   the aged tenor, which this step first specified. That quantity is not
   comparable to the par yield at `n`: the aged bond's first coupon is a
   five-month stub while it still pays a full half-coupon, so its par rate is
   tens of bp lower **on a curve that has not moved at all**, and the
   approximation came out biased by 28 to 35 bp a month at every tenor.
   "From curve yields only" was the owner's wording and is not a constraint;
   the rejected alternative — the curve move at the same tenor plus the 4.1
   rolldown — was declined because its decomposition argument does not hold
   (6.1 cannot put a Taylor term inside an exact identity; see the ruling at
   the head of step 6.1).

2. **The tolerance is 5 bp for tenors ≤ 10 and 10 bp at 20 and 30**, and
   `(D, C)` stay at `t` on the un-aged bond. Averaging them over the month
   would close most of the residual but would change the `duration` column
   that 5.2's duration budget reads, and a diagnostic does not justify moving
   a live definition.

   **The 5 bp is a known floor, not slack.** With `(D, C)` measured at `t`,
   one month of ageing shortens the duration by about `1/12` of a year, so
   the approximation keeps roughly `Δy/12` too much price sensitivity — about
   **4 bp for a 50 bp move**, at every tenor, whatever `Δy` is. That term,
   not Taylor truncation, is what sets the number: on the 200 draws the worst
   gap is 4.80 bp at 1 year and falls to 2.67 bp at 30, the opposite of the
   ordering a truncation error would have. `test_ageing_term_is_the_tolerance_floor`
   measures it.

**Session-4 amendment 2 (2026-09-23): the long-run identity.**
`data/checks/return_identity.csv`, one row per `(country, tenor_years,
window)` with `window ∈ {full, strategy}` (`full` = every month the bucket
has a return; `strategy` = from `config.sample.strategy_start`):
`country, tenor_years, window, n_months, r_local_ann, yield_rolldown_ann,
carry_rolldown_ann, price_return_ann, r_short_ann, diff_bp,
diff_carry_bp, flagged, mean_duration, mean_dy_ann, trend_bp,
trend_residual_bp, trend_linearisation_bp, coupon_vs_zero_bp,
linear_exact_bp, convexity_bp, accounting_sum_bp, accounting_gap_bp,
r_local_sd_monthly, half_var_ann_bp, annualisation`.

Annualisation is `12 × mean(monthly)`, in decimals; `diff_bp` is
`(r_local_ann − yield_rolldown_ann) × 1e4`.

- `yield_rolldown_ann` = `12 × mean(yield/12 + rolldown)` — the bucket's
  expected **total** return from carrying and rolling down the curve.
- `carry_rolldown_ann` = `12 × mean(expected_return_1m)` =
  `12 × mean(carry/12 + rolldown)` — the same quantity net of funding,
  using this project's `carry = y_n − r_short` (`decisions/short_anchor.md`).
  It differs from the first by `r_short_ann` by construction.

The amendment's own words are "the annualised mean of (carry + rolldown)"
and "over a long sample the first two should be close": those two clauses
cannot both hold of `carry = y_n − r_short`, because a total return and a
return over funding differ by the funding rate, which is 200 to 400 bp a
year. Both columns are therefore written, nothing is lost either way, and
**`flagged` is set on
`|diff_bp| > config.checks.identity_gap_flag_bp_per_year` (50), the
funding-free reading**, because that is the one the amendment's stated
expectation describes. `diff_carry_bp` carries the other reading.

**The trend columns** (session-4 fix round): `mean_duration`,
`mean_dy_ann` (`12 × mean` of the constant-maturity monthly change in that
tenor's zero yield), `trend_bp = −mean_duration × mean_dy_ann × 1e4` and
`trend_residual_bp = diff_bp − trend_bp`. If `diff_bp` is the sample's yield
trend and nothing else, `trend_bp` should be close to it. A first-order
comparison: a residual of a few bp on a long bucket is the convexity and the
duration/yield cross term, not a discrepancy.

**The accounting columns** (second fix round, 2026-09-23), which turn that
sentence into numbers. `diff_bp` is split into three terms computed month by
month and then annualised, so nothing is linearised away:

- `coupon_vs_zero_bp = 12 × mean(coupon − yield)`;
- `linear_exact_bp = 12 × mean(−duration × dy − rolldown)`, the yield-change
  term at its own month's duration, net of the rolldown that
  `yield_rolldown_ann` already contains;
- `convexity_bp = 12 × mean(C·dy²/2)`, **always positive**.

`accounting_sum_bp` is their sum and `accounting_gap_bp = diff_bp −
accounting_sum_bp` is the third-order Taylor remainder — the step-4.2 `gap_bp`
averaged over the window, and it is under 14 bp on every one of the 96 rows.
`trend_linearisation_bp = linear_exact_bp − trend_bp` is the linearisation the
trend comparison itself makes (mean duration × mean yield change rather than
the mean of the product, and `dy_cm` rather than the bond's own `dy`); **it is
the one term that carries either sign**, and with it the residual splits
exactly:

```
trend_residual_bp = coupon_vs_zero_bp + trend_linearisation_bp
                  + convexity_bp + accounting_gap_bp
```

**Annualisation is arithmetic throughout — `mean × 12`, never compounded** —
on both sides of `diff_bp`, which is the basis the identity needs because
carry and rolldown are summed rather than compounded. The `annualisation`
column states it on every row. There is therefore **no geometric-versus-
arithmetic wedge and no `σ²/2` term to remove**; `r_local_sd_monthly` and
`half_var_ann_bp` are written so a reader can check that rather than take it
on trust. What they show is that `half_var_ann_bp` tracks `convexity_bp`
(correlation 0.998 over the 96 rows, ratio 1.13 to 1.37) — the variance term
is real, it grows with duration, and it is already one of the three accounted
terms rather than a missing correction.

Two things the identity does not claim. It is a *mean* identity, not a
per-month one: within a month `r_local` also contains the price effect of
the actual yield change, which averages towards zero over a long sample and
does not vanish in a short one. And a bucket whose sample is one direction
of rates (JP, or any bucket that starts in the 2010s) has no reason to
satisfy it; the review says so rather than calling it a fault.

**Build**
- `src/curvecarry/returns.py`, for each `(country, tenor n, month t)` with
  a curve at `t` and at `t+1` (the next calendar month end):
  - Full recomputation: buy at `t` the par bond at tenor `n` off the zero
    curve: `c = par_yield_from_zero(curve_t, n, freq)`, price 100. At
    `t+1` its tenor is `n − 1/12`; dirty price
    `P = price_from_zero(curve_{t+1}, n − 1/12, c, freq)` (no coupon is
    paid within one month for freq ≤ 2; the accrued coupon is inside the
    dirty price). `r_local_full = P / 100 − 1`.
  - Approximation (brief 6.3):
    **`Δy = yield_from_price(P, n − 1/12, c, freq) − c`** — the change in the
    **bond's own yield to maturity** (issue #17 answer 1, 2026-09-23);
    `r_local_approx = c/12 − D·Δy + ½·C·Δy²` with `(D, C)` from
    `par_bond_risk(curve_t, n, freq)`.
  - `gap_bp = (r_local_full − r_local_approx) × 1e4`.
  - **`r_local = r_local_full`**; the approximation is diagnostic.
  - `r_short_local` = `funding.parquet` at `(country, t, kind = config.hedge.funding_rate)`
    (dated `t`, the country's own currency);
    **`r_excess_local = r_local − r_short_local / 12`** — the bucket's
    return over its own financing, the quantity every later step uses
    (amendment A). A `robustness` copy, `r_short_local_interbank_3m`,
    `r_excess_local_interbank_3m`, with `kind = funding_rate_robustness`.
  - A bucket present at `t` whose price at `t+1` cannot be computed
    (`price_from_zero` raises: the aged tenor needs an unobserved tenor)
    gets `r_local = 0.0`, `closed = True`, and a row in
    `data/checks/closed_buckets.csv` (`date, country, tenor_years, reason`)
    — "closed at its last available price".
  - Output `data/processed/returns.parquet`:
    `date (= t), country, tenor_years, coupon, duration, convexity, dy, r_local_full, r_local_approx, gap_bp, r_local, r_short_local, r_excess_local, r_short_local_interbank_3m, r_excess_local_interbank_3m, closed`.
    This is the whole schema: the `*_ytm` and `*_curve` candidate columns of
    the session-4 fix round were dropped when issue #17 was answered.
  - `data/checks/return_approx_gap.csv`: the full distribution — per
    `tenor_years`: `n, mean_bp, std_bp, p01, p05, p50, p95, p99, max_abs_bp`,
    and the 20 largest `|gap_bp|` rows with their dates.
- CLI `build --step returns`.

**Test** `tests/test_returns.py` (synthetic zero curves: NS curves with
`rng = default_rng(0)`, β0 ∈ [0.01, 0.08], β1 ∈ [−0.04, 0.02],
β2 ∈ [−0.03, 0.03], λ ∈ [0.3, 1.2], month-to-month shocks: parallel
±50 bp, slope ±25 bp uniform).
- `test_approx_within_tolerance_on_200_draws`: 200 random
  `(curve_t, curve_{t+1}, tenor)` draws → **`|gap_bp| ≤ 5` for tenors ≤ 10
  and `≤ 10` at 20 and 30** (issue #17 answer 2; the test file lists the
  numbers).
- `test_ageing_term_is_the_tolerance_floor`: the residual is the **ageing of
  `(D, C)`**, not Taylor truncation, and the 5 bp is that floor rather than
  slack. See the amendment block above.
- `test_unchanged_curve_return_equals_carry_plus_rolldown`: `curve_{t+1} == curve_t`
  → `r_local_full` equals `c/12 + rolldown-like term` within 1 bp, and
  `r_local_approx` equals it **inside the step tolerance, and in fact inside
  1 bp**. Not the 0.1 bp this line said before issue #17: on a static curve
  the residual is a constant ≈ 0.26 bp from the annual-versus-`freq`
  compounding convention plus the `Δy/12` ageing term, which is −0.41 bp at
  1 year and vanishes by 10.
- `test_parallel_shift_sign`: +100 bp shift → negative return for every
  tenor; −100 bp → positive.
- `test_closed_bucket_is_zero_and_logged`: curve at `t+1` missing 30y →
  `r_local == 0`, `closed`, one log row.
- `test_full_repricing_uses_dirty_price`: the price at `t+1` includes
  accrued (equals cashflow sum with first stub `1/freq − 1/12`).
- `test_excess_return_subtracts_own_funding`: `r_local 0.01`,
  `r_short_local 0.048` → `r_excess_local == 0.01 − 0.004` to 1e-15; the
  funding row is the bucket's country and date `t`, not `t+1`.

**Done when** the six tests pass and `data/checks/return_approx_gap.csv`
exists.

## Step 4.3 — Hedged and unhedged excess returns

**Session-4 amendment 3 (2026-09-23): the coverage log.**
`data/checks/return_coverage.csv`, one row per `(date, country)` over every
month with returns:
`date, country, n_buckets, has_r_local, has_r_hedged, has_r_unhedged,
reason, funding_kind, funding_source, funding_area, fx_currency`.
`has_*` is true when **at least one** bucket that month has a finite value
of that column; `reason` is empty when all three exist and otherwise names
the binding one (`no_fx` — no spot for the currency that month or the next;
`no_funding_local`; `no_funding_base`; `no_bucket`). `funding_source` is the
`source` of the row used from `funding.parquet` (`bis`, or `fred_immediate`
for a filled month), `funding_area` is `XM` or the legacy `DE`/`FR` code for
the euro countries and the country itself otherwise, so the splice window
of `decisions/short_anchor.md` can be read straight off the file.

The review reports the months with a hedged return but no unhedged one and
confirms that every `fred_immediate` month and every legacy euro area code
falls inside the windows `decisions/short_anchor.md` records.

**Build**
- `returns.add_fx(returns, funding, fx, cfg) -> pd.DataFrame` adds to
  `returns.parquet` (amendment A):
  - `r_short_base` = `funding.parquet` at the base currency's country,
    dated `t`, `kind = config.hedge.funding_rate`;
  - **`r_hedged = r_excess_local`** — under covered interest parity the
    FX-hedged excess return in the base currency equals the local excess
    return. No FX series enters it;
  - `fx_return = ln(S_{t+1}) − ln(S_t)` with `S` = base per foreign from
    `fx.parquet` (foreign appreciation is a gain);
  - **`r_unhedged = r_local + fx_return − r_short_base / 12`** — the local
    return converted at spot, financed in the base currency;
  - `hedge_carry = (r_short_base − r_short_local) / 12` kept as a
    **diagnostic** column only; by construction
    `r_local + hedge_carry − r_short_base/12 == r_hedged`.
  - For the base country's currency `r_hedged == r_unhedged == r_excess_local`
    and `fx_return == hedge_carry == 0`.
  - Robustness columns with `kind = funding_rate_robustness` and the same
    definitions: `r_hedged_interbank_3m = r_excess_local_interbank_3m`,
    `r_unhedged_interbank_3m`, `hedge_carry_interbank_3m` (NaN where the
    interbank series is missing).
  - `r_unhedged` is NaN where no `S` exists (EUR before 1999-01); such a
    bucket is not held in an unhedged variant (5.3) and is counted in
    `data/checks/closed_buckets.csv` with `reason = no_fx`.
- `decisions/basis.md`: first the two-line derivation —
  a bond bought with `1` unit of foreign currency borrowed at
  `r_short_local` and the proceeds sold forward: forward premium under CIP
  is `(r_short_base − r_short_local)/12`, so the base-currency excess
  return is `r_local + (r_short_base − r_short_local)/12 − r_short_base/12 = r_local − r_short_local/12 = r_excess_local`;
  then what that omits (the cross-currency basis). The step probes, and records the status of, the free candidates
  it can find (at minimum: FRED search for "cross-currency basis", BIS
  Statistics Explorer, the ECB Data Portal); if none yields a series, it
  states that the basis is **not measured** and quotes the brief's 20 to
  50 bp in stress periods. If one is found, the size of the CIP error by
  year for each currency pair is tabulated there and in
  `data/checks/xccy_basis.csv`.
- CLI `build --step fx_hedge`. **Not `fx`**, as first written here: `fx` is
  already the name of the step-1.7 FX *loader* in `cli.LOADERS`, and a
  build step of the same name shadows it, so `build --all` would silently
  stop rebuilding `data/interim/fx.parquet`. Renamed in session 4.

**Test** `tests/test_fx_hedge.py` (synthetic).
- `test_hedged_is_local_excess_return`: `r_hedged == r_local − r_short_local/12`
  to 1e-15 and does not change when the FX series changes.
- `test_cip_identity`: `r_local + hedge_carry − r_short_base/12 == r_hedged`
  to 1e-14 on 1,000 random rows.
- `test_base_country_columns_equal`: `r_hedged == r_unhedged == r_excess_local`,
  `fx_return == hedge_carry == 0`.
- `test_hedge_carry_sign_and_size`: base 5%, foreign 1% → `+0.04/12`.
- `test_unhedged_uses_log_change_and_base_funding`: `S` 1.00 → 1.02,
  `r_local 0`, `r_short_base 0.048` → `r_unhedged == ln(1.02) − 0.004`; a
  foreign appreciation raises `r_unhedged`.
- `test_rates_dated_t_not_t_plus_1`.
- `test_robustness_columns_present_and_nan_where_missing`.
- `test_no_fx_means_unhedged_nan_and_logged`.

**Done when** the eight tests pass, `returns.parquet` has the new columns,
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

**Session-5 amendment 3 - universe discipline.** The signal frame is
**joined to `data/checks/universe_by_month.csv`** (4.2): a bucket is a
candidate at `t` only if that file lists its tenor for its country at `t`,
so the strategy universe is the universe the return engine can actually
price, and a bucket that exists on the curve but has no computable return
is `eligible = False` with `excluded_reason = not_in_universe`. Three
things are reported per month, not per sample:

- `data/checks/universe_eligible.csv`: `date, n_universe, n_eligible,
  n_below_floor, n_missing_input, n_not_in_universe, eligible_buckets`
  - one row per month, the last column `;`-joined `CC:tenor`.
- `data/checks/universe_changes.csv`: `date, country, tenor_years, change in
  {enters, leaves}` - every month a bucket enters or leaves the **eligible**
  set, against the month before. The first month of the panel is all
  `enters`.
- `data/checks/signal_exclusions.csv` keeps its per-month floor counts as
  above; the per-country table is unchanged.

**Done when** the four tests pass and `data/checks/signal_exclusions.csv`,
`universe_eligible.csv` and `universe_changes.csv` exist.

## Step 5.2 — Weights

**Build**
- `src/curvecarry/weights.py`:
  - `duration_neutral_weights(signal: pd.DataFrame, cfg) -> pd.DataFrame`
    per month on eligible rows:
    - `scope = "book"` (default): rank all eligible buckets by `signal`
      descending; `n` eligible; `k = n // 3`; if `n < config.weights.min_eligible_buckets`
      the month holds nothing and is logged to
      `data/checks/weights_empty_months.csv`. **Session-5 amendment 3
      changes that default from 6 to 9**, pre-registered before any result
      is seen: below 9 eligible buckets `k = n // 3` is 2 a side, which is
      a pair trade and not a book, so the book is flat that month and the
      month is logged. The change is a commit on its own (global rule 14). Long leg = top `k`, short
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
- `test_min_eligible_buckets_is_nine`: the default read from `config.toml`
  is 9 (amendment 3 is pre-registered, so a silent revert fails a test).

**Session-5 amendment 4 - the invariants are tested on the real panel, not
only on synthetic frames.** `tests/test_weights_panel.py` builds the weights
from the real `signal.parquet` once (module-scoped fixture) and walks
**every month of the backtest sample**, asserting on each:

- `|sum_j wd_j| < 1e-10` (book scope) and `|sum_j wd_j| < 1e-10` within each
  country (country scope);
- no `(country, tenor_years)` appears in both legs;
- `sum_{j in long} wd_j == config.weights.long_duration_budget` to 1e-10,
  and `k_long == k_short`;
- `weight_j * duration_j == wd_j` to 1e-12 **with `duration_j` taken from
  `returns.parquet`** - the same `bondmath.par_bond_risk` output 4.1 and 4.2
  use - so the weights cannot be sized off a second duration.

A month the rule leaves flat asserts that it holds nothing and appears in
`weights_empty_months.csv`. The test skips with a clear message if
`data/processed/signal.parquet` is absent (a fresh clone before
`build --step signal`), and is not skipped in this repo.

**Done when** the eight synthetic tests and the real-panel walk pass.

## Step 5.3 — Carry-only backtest

**The headline, fixed 2026-09-23 before any result was seen (session-5
amendment 1).** *The headline result of this project is the **carry-only,
hedged, book-wide duration-neutral book, net of costs, from `strategy_start`
(1997-08-31) to `strategy_end`, on the universe available each month** - the
`carry_hedged` variant, `full` window, `r_net`.* Everything else is a logged
variant and is never the headline, whatever the numbers say.

**Build**
- `src/curvecarry/backtest.py`:
  - `run(cfg, variant: str, note: str = "") -> BacktestResult`:
    **first** `run_id = speclog.log_run(cfg, label=variant, note=note)`,
    then computes; every computing function takes `run_id` and calls
    `speclog.require_logged`. Variants in this step:
    `carry_hedged`, `carry_unhedged`.
  - Timing: weights `w_t` from `signal` at month end `t`; held `t → t+1`;
    bucket return `r_{j,t}` from `returns.parquet` row dated `t`
    (`r_hedged` or `r_unhedged` as defined in 4.3 — both excess returns,
    so a net long notional is charged its financing). A bucket missing at
    `t`, or with NaN `r_unhedged` in an unhedged variant, is not held; a
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
    `sharpe = annualised_return / annualised_vol` (no risk-free subtraction,
    because every bucket return is an excess return over its funding
    rate); `max_drawdown` on the wealth index `Π(1 + r)` with
    `peak_date`, `trough_date`; `turnover_mean`; `n_months`;
    `year_2022 = {return, vol, sharpe, max_drawdown}` on the 12 months
    of 2022 alone.
  - Outputs: `data/processed/backtest_<variant>.parquet`
    (`date, r_gross, cost, r_net, turnover, n_long, n_short, n_closed, run_id`);
    `data/checks/metrics_<variant>.csv` (`run_id, variant, window, metric, value`),
    `data/checks/positions_<variant>.parquet` (the weights actually held), and
    `data/checks/extreme_months_<variant>.csv` (**session-5 amendment 2**:
    `rank, sign, date, r_net, country, tenor_years, leg, wd, r_bucket,
    contribution` - the 10 largest monthly gains and the 10 largest losses,
    each with the 5 largest positive and 5 largest negative bucket
    contributions, `contribution = weight x r`). It is written by the engine
    for **every** variant rather than once in 5.5, because the headline is a
    5.3 variant and a headline number nobody can trace to a curve move is a
    number taken on trust.
  - Every metric this step reports is reported **twice, gross and net of
    costs**: the metrics frame carries `<metric>` on `r_net` and
    `<metric>_gross` on `r_gross`, in both windows.
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
- `test_net_notional_is_financed`: two buckets with weights summing to
  `+3` units of notional, zero price change (`r_local = 0`), `r_short 4%`
  → `r_gross = −3 × 0.04/12` to 1e-15.
- `test_metrics_closed_forms`: constant monthly return `r` →
  `annualised_return = 12r`, `vol = 0`, drawdown 0; a `−10%` then `+5%`
  series → `max_drawdown = −0.10`, dates right.
- `test_two_windows_reported`: metrics frame has `window ∈ {full, six}`.
- `test_extreme_months_names_the_legs`: the biggest month of a synthetic
  panel is the month that moved, and the largest contribution in it is
  `weight x r` of the bucket that moved.
- **Session-5 amendment 5, timing:** `test_appending_months_does_not_change_weights_at_t`
  - weights built on the signal panel truncated at `T0` are identical, to
  1e-12 on `wd` and exactly on the held set, to the weights at the same
  dates built on the panel truncated at `T0 + 24`. The signal at `t` is the
  curve at `t` and the return it earns is the `returns.parquet` row dated
  `t`, which spans `t -> t+1`; the test makes the first half of that
  sentence enforceable.

**Done when** the ten tests pass, `reports/specifications.csv` has two new
rows, and `data/checks/metrics_carry_hedged.csv`,
`data/checks/metrics_carry_unhedged.csv` exist.

## Step 5.4 — Slope overlay

**Ruling of 2026-09-23 (issue #19), carried here so nothing is built on the
other reading.** The overlay's expanding PC2 is fitted **per country, on that
country's own change rows**, not on the pooled panel. Two reasons, the
owner's: the overlay trades a **national 2s10s pair**, so `v2` must be the
vector describing that country's slope rather than the average country's;
and the pooled set is the intersection of the six country sets, `1` to `10`
years, which would drop the long end out of the slope measure for DE, JP, CA
and FR. Each country's expanding fit uses **that country's own tenor set**
from `data/checks/pca_tenor_sets.csv`, the **3.1 sign convention**, and
**`config.pca.pca_min_months` = 60**. **6.2 keeps the pooled PC1**, which is
the right object for a book-wide volatility gauge. The contradicting
sentence in the `pca.py` module docstring is corrected in the same session,
in its own commit.

**Build**
- `src/curvecarry/overlay.py`:
  - `expanding_pc2_scores(changes_by_country, cfg) -> pd.DataFrame`: for
    country `c` and month `t`, if the number of complete change rows
    dated ≤ `t` is ≥ `config.pca.pca_min_months` (60): PCA (3.1 rules) on
    **country `c`'s own** rows ≤ `t`,
    `score_t = (Δy_t − mean_{≤t}) @ v2^{(≤t)}`; otherwise NaN.
    Never full-sample loadings, and never a pooled loading vector. Output
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
- **Session-5 amendment 5, timing:** `test_zscore_at_t_unchanged_when_future_appended`
  - the z-score at every `t <= T0`, not only the PC2 score, is unchanged to
  1e-12 when 24 later months are appended. The score test above covers the
  loadings; this covers the rolling mean and standard deviation on top of
  them.

**Done when** the six tests pass, the two overlay variants are logged, and
`data/checks/overlay_trades.csv` exists.

## Step 5.5 — Combined and the metrics table

**Build**
- `backtest.run(cfg, "combined_hedged")`, `"combined_unhedged"`:
  positions = carry weights + overlay weights summed per `(country, tenor)`
  (both books duration-neutral, so the sum is); turnover and cost on the
  summed `wd`.
- Robustness variants, each its own logged row:
  `carry_hedged_country_scope` (`duration_neutral_scope = "country"`),
  `carry_hedged_interbank_3m` (`funding_rate = interbank_3m` for `r_short`
  in carry, `r_excess_local` and `r_short_base`; sample limited to where the series exist, stated in the
  table), and the three **session-5 amendment 2** variants, fixed before any
  result was seen and all reported whether they help or not:
  `carry_hedged_cost0` (`costs.cost_bp_per_duration_year = 0.0`, the book
  priced as if trading were free), `carry_hedged_cost2x` (`= 1.0`, twice the
  default) and `carry_hedged_no_gb30` (`GB` at 30 years excluded from the
  universe for the **whole** sample, not only from 2016 when it enters, so
  the comparison is a like-for-like book and not a book with a regime break
  in it). The last exists because the GB 30-year bucket enters in 2016 and
  the owner asked whether anything rests on it. With `carry_hedged`,
  `carry_unhedged`, the two overlay and the two combined variants that is
  **eleven logged runs in this session**.
  A variant config override is recorded in its spec-log `note` as the JSON of the
  overridden keys; the base `config.toml` is not edited. A variant's config override is recorded in its spec-log `note` as the JSON of the
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
  rows = variants (carry, overlay, combined × hedged, unhedged; the five
  robustness rows - country scope, interbank funding, cost 0, cost 2x and no
  GB 30y), columns = window (`full`, `six`) × metric
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
all eleven variants in both windows.

**Session-5 amendment 2, what the review must show.** The `Session 5 review`
issue carries: the headline metrics table (annualised return, vol, Sharpe,
max drawdown with its peak and trough dates, turnover, 2022 in isolation,
gross **and** net of costs); the same table for every variant; the deflated
Sharpe with its `N` and the `specifications.csv` row count; the eligible
bucket count by year; and the **10 largest monthly gains and the 10 largest
monthly losses**, each with the country-tenor legs that drove them, from
`data/checks/extreme_months_<variant>.csv`, which step 5.3 writes for every
variant.

---

# Phase 6 — Analysis and write-up

## Step 6.1 — Decomposition

**Ruling of 2026-09-23 (issue #17, carried here so nothing is built on the
other reading).** The yield-change PnL of this step is **the residual of the
full repricing**, `r_local − carry − rolldown`, and nothing else. The
duration-convexity approximation is **reported beside the identity, never
inside it**: a Taylor term cannot appear in an identity that has to hold to
1e-10, which is the whole reason step 4.2's approximation is diagnostic.

Two consequences for the text below:

- `yield_change_pnl_t` is already written as the exact remainder. That is
  the definition, not a convenience, and it is what the identity uses.
- `yield_change_taylor_t` takes **the same `Δy` as step 4.2** — the change in
  each bond's own yield to maturity, `yield_from_price(P_j, n_j − 1/12, c_j,
  freq) − c_j` — and **not** the curve move at the aged tenor that this step
  first specified. Only then is `taylor_residual_t` the weighted sum of the
  4.2 `gap_bp`, which is what `test_taylor_residual_equals_weighted_gap`
  asserts. With the old `Δy` the two were different quantities and that test
  could not have passed.

**Build**
- `src/curvecarry/decomposition.py`, per variant and month `t`, on the
  held positions:
  - **hedged variants:** `carry_earned_t = Σ_j w_j (c_j/12 − r_short_j/12 + rolldown_j)`
    (`c_j` the par yield the bond was bought at, `r_short_j` its own
    funding rate, `rolldown_j` from 4.1); `funding_t = 0` and `fx_t = 0`
    (financing is inside carry earned, and there is no FX term).
    **unhedged variants:** `carry_earned_t = Σ_j w_j (c_j/12 + rolldown_j)`,
    `funding_t = −Σ_j w_j r_short_base/12`, `fx_t = Σ_j w_j fx_return_j`
    (amendment A);
  - `yield_change_pnl_t = Σ_j w_j (r_local_full,j − c_j/12 − rolldown_j)` —
    the exact remainder, so the identity holds to machine precision. Its
    Taylor form `Σ_j w_j (−D_j Δy_j + ½ C_j Δy_j²)` with **`Δy_j` the step-4.2
    `dy`** (the change in the bond's own yield to maturity; the ruling above
    replaces the curve move at the aged tenor first written here) is stored as
    `yield_change_taylor_t` and the difference as `taylor_residual_t`, which is
    then exactly the 4.2 `gap_bp` aggregated by the weights;
  - `cost_t = −cost_t` from the backtest.
  - Identity: `carry_earned + yield_change_pnl + funding + fx + cost == r_net`
    to 1e-10 every month (for hedged variants `funding` and `fx` are zero
    columns, so it is the four-piece identity).
  - Outputs `data/processed/decomposition_<variant>.parquet`
    (`date, carry_earned, yield_change_pnl, yield_change_taylor, taylor_residual, funding, fx, cost, r_net, identity_gap`),
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
- `test_carry_earned_hand_computed`: hedged, one bucket `w 2`, `c 0.03`,
  `r_short 0.012`, `rolldown 0.0005` → `2 × (0.0025 − 0.001 + 0.0005)`;
  unhedged, the same bucket → `2 × (0.0025 + 0.0005)` and
  `funding == −2 × r_short_base/12`.
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
  - (a) `vol_target`: `scale_t = min(target_vol / vol_{t−12..t−1}, max_leverage)`
    with `vol` the annualised std (ddof 1) of the base's `r_net` over the
    12 returns **dated `t−12 … t−1`** (a return dated `t` is earned over
    `t → t+1` and is not known at `t` — amendment C); NaN until 12 months →
    scale 1; positions at `t` multiplied by `scale_t`. Variant
    `<base>_voltarget`.
  - (b) `dd_stop`: drawdown of the base's wealth index **through `r_{t−1}`**
    (`Π_{s ≤ t−1} (1 + r_s)`, amendment C); if
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
- `test_vol_target_uses_only_past_returns`: changing `r_t` (the return
  dated `t`) does not change `scale_t`; changing `r_{t−1}` does.
- `test_dd_stop_goes_flat_next_month_for_exactly_reentry_months`.
- `test_dd_stop_uses_wealth_through_t_minus_1`: a drawdown breach that
  first appears in `r_t` does not flatten positions at `t`; it flattens
  them at `t+1`.
- `test_rates_filter_expanding_percentile_no_lookahead`: appending months
  after `t` leaves the flag at `t` unchanged.
- `test_attribution_2022_rows_sum_to_total`.

**Done when** the six tests pass, six risk-control rows are in
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

**How the deflated Sharpe is reported (session-5 fix 3).** The deflated Sharpe is **a probability that the true Sharpe exceeds the
multiple-testing threshold, not a Sharpe** — here **0.57 against a threshold
of 0.067 over 11 trials, which does not clear the usual bar**. It is written that way
in `reports/results.md` and in `README.md`, in words as well as in the
table, so that no reader can mistake it for a risk-adjusted return.

**6.4 recomputes the DSR from the final `reports/specifications.csv` row
count and never with a smaller `N`.** `metrics.deflated_sharpe` takes `N`
from `speclog.count_runs()` at the moment the report is written, so every
run logged by Phase 6 — the three risk controls of 6.2 above all — is in
it. A DSR quoted from an earlier session's smaller `N` is a number that
flatters the result, and quoting one is a reporting error, not a rounding
difference. `tests/test_report.py` asserts that the `N` printed in
`reports/results.md` equals `speclog.count_runs()` and is at least the
count Phase 5 left behind.

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
the README block is the pasted table, and the DSR line in the report states
the probability, its threshold and its `N` in the words above.

---

## Appendix — where each number lives

| Quantity | Config key | Used in |
|---|---|---|
| countries, tenors, flat short end | `countries`, `tenors`, `short_end` | 1.8, 1.9, 2.1, 4.1 |
| bootstrap node gap | `bootstrap_max_node_gap_years` | 1.9 (Session 1 part B fix 2) |
| bootstrap zero-vs-par tolerance | `bootstrap_zero_par_tolerance_bp` | 1.9 (Session 1 part B fix round 2; replaced `bootstrap_forward_tolerance_bp`) |
| coupon frequency | `coupon_frequency.<cc>` | 1.9, 2.1, 4.x |
| windows | `sample.*` | 1.9, 5.3 |
| NS/Svensson grid and fixed λ, min tenors | `nelson_siegel.*` | 2.2, 2.3 |
| PCA windows | `pca.*` | 3.x, 5.4, 6.2 |
| yield floor | `signal.yield_floor` | 5.1 |
| duration budget, scope, minimum buckets | `weights.*` | 5.2 |
| overlay entry/exit, budget, tenors | `overlay.*` | 5.4 |
| funding rate kinds, EUR splice and legacy areas | `hedge.*` | 1.7, 4.1, 4.2, 4.3, 5.5 |
| cost | `costs.cost_bp_per_duration_year` | 5.3 |
| risk controls | `risk.*` | 6.2 |
| chart decades | `report.chart1_decades` | 2.4 |
