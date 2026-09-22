# Yield Curve Modelling and a G7 Carry Strategy

Read this first. The brief is
[Project Outline/08_Yield_Curve_Carry.docx](Project%20Outline/08_Yield_Curve_Carry.docx),
the build order and every module contract are in [PLAN.md](PLAN.md), and the
source URLs that were actually reachable from this machine are in
[decisions/sources.md](decisions/sources.md). This file holds what every
session must not violate, and how to run things on this machine.

**The decomposition is the deliverable, not the Sharpe.** The question the
brief asks is how much of a duration-neutral carry book's return was carry
earned and how much was paid for a directional yield bet. A carry strategy
that "works" because it was long duration into a bull market is the failure
mode; the decomposition in step 6.1 has to sum to the reported return to
1e-10 or the report is not written.

---

## How a session runs

**Sessions, not steps** (rule from 2026-09-17; the full text is in
`PLAN.md` → "How to use this file"). A session is a fixed group of steps
built in one go: 0 = {0.2, 0.3}; 1 = {1.1–1.7}; 2 = {1.8, 1.9, gate};
3 = {2.1–2.4}; 4 = {3.1–3.3}; 5 = {4.1–4.4}; 6 = {5.1–5.3}; 7 = {5.4, 5.5};
8 = {6.1, 6.2}; 9 = {6.3, 6.4}. The owner says `Do Session N`.

Within a session the steps are built in order; each keeps its own commit
`Step X.Y: <one line>` and its own `review/X.Y.md`, and its "Done when",
`make test` and `make lint` must pass before the next step starts. No
review issue per step. A step that cannot meet its "Done when" stops the
session there; it is not skipped. A step that needs a choice the plan does
not make gets a `decision` issue, and the session continues only with steps
that do not depend on the answer. Never guess. When a decision issue changes
a step, the plan text is amended in the same session, before the session
review is posted.

At the end: push, post one issue `Session N review` (label `review`) with
the steps built and their test counts, every deviation from the plan in
full, every open question, and each step's "Reviewer reads" list; stop. The
owner replies with fixes; each fix is one commit `Session N fix: <one line>`,
then the full suite is re-run and a comment on the session issue lists what
changed; stop. Repeat until the owner posts `Session N approved`; only then
record `Session N approved <date> (<commit>)` under Validation status below
and start the next session. **A session is never started without the
previous one's approval line in this file.**

**Everything the owner must read or answer goes on GitHub as an issue**, not
only in the terminal — the owner reviews and replies from the Claude app,
which reads GitHub. Use `scripts/gh_issue.py` (token from the git credential
store or `GITHUB_TOKEN`; never printed, never in a file):

```bash
uv run python scripts/gh_issue.py post --title "Session N review" --body-file s.md --label review
uv run python scripts/gh_issue.py post --title "Question X.Y: <one line>" --body-file q.md --label decision
uv run python scripts/gh_issue.py read <n>     # the owner's answers arrive as comments
uv run python scripts/gh_issue.py list
```

At the end of every session: post the `Session N review` issue after the
push and put its URL in the terminal summary. When a step needs a decision:
post it as a `decision` issue with the recommendation and one reason per
option. At the start of every session: `list`, and `read` any issue with new
comments before doing anything — an answer on GitHub counts as the owner's
answer.

---

## Invariants

Each has a test named next to it once the step that builds it lands. Until
then the cell says which step will add the test. `review` means there is no
test and the reviewer checks it from the review file. Do not weaken a test
to make a run pass.

| # | Invariant | Test |
|---|---|---|
| 1 | One session at a time; one commit and one review file per step; nothing starts until the previous session is approved in `CLAUDE.md` → Validation status. | review (the approval line) |
| 2 | Yields are **decimals** everywhere inside the package (0.0425, never 4.25). Conversion from percent happens once, in the loader, and nowhere else. Every loader test fails on a yield above 0.5 or below -0.05. | `test_units_us`, `test_units_gb`, `test_units_de`, `test_units_jp`, `test_units_fr`; one `test_units_<cc>` per loader as each lands; `validate_curve` asserts both bounds |
| 3 | `par` and `zero` are never mixed in one calculation. Any function that takes a curve asserts on `curve_type`. | pending 1.9 / 2.1 |
| 4 | Every number that affects a result comes from `config.toml`. Nothing in `src/` reads a knob that is not there. | review |
| 5 | Raw files are never overwritten; every fetch appends to `data/raw/manifest.json` (URL, sha256, bytes, fetched_at, source). A re-fetch gets a new filename with the fetch date. | `test_second_fetch_to_existing_path_raises`, `test_refetch_gets_dated_filename` |
| 6 | Every strategy run is a row in `reports/specifications.csv` **before** it computes. A variant with no row did not happen. The file is append-only. N in the deflated Sharpe is that row count. | `test_run_without_row_fails`, `test_speclog_is_append_only` |
| 7 | Anything a function uses at month *t* is dated on or before *t*. Expanding-window PCA scores at *t* do not change when later months are appended. | pending 5.4 |
| 8 | No number in `README.md` is typed by hand. The results table is pasted from `reports/results.md` and a test asserts equality. | pending 6.4 |
| 9 | Nothing is imported from the project 1 repo. The duration-budget engine is written here. | review |
| 10 | Do not add features, refactor other modules, or improve earlier steps unless the current step says so. | review |
| 11 | If a data source is unreachable, stop and say so. A substitution is written into `decisions/` before it is used. | review |
| 12 | Tests never use the network. Every `parse()` is tested on a fixture in `tests/fixtures/` (first 50 rows of the real download, made by `scripts/make_fixture.py`). Every review follows `review/TEMPLATE.md`. | `test_reviews_follow_template` (reviews); network side is review (a test that needs the internet is a bug) |
| 13 | Interpolation in yield is linear in tenor, between observed tenors only. One interpolation function in the package; every module uses it. No extrapolation, ever: a tenor beyond the longest observed is missing. | pending 1.8 |
| 14 | `config.toml` is written in full in step 0.1 with every key the plan names. A later step may change a default only if the step says so, and that change is a commit on its own. | `test_config_loads_every_named_key`; the default-change rule is review |

Two consequences worth spelling out:

- **The percent-versus-decimal bug is the most likely bug in the project.**
  Every source but one publishes percent; the Bank of Canada zero-coupon file
  is already in decimals (0.0226 = 2.26%). A loader that divides by 100
  unconditionally will pass the "below 0.5" check on Canada with yields of
  0.0002 and poison every downstream number. The unit test bounds both sides.
- **A tweak that is not in `specifications.csv` did not happen.** The three
  risk controls in 6.2 are logged as runs before their results are seen, and
  all three are reported whether or not they help.

---

## Running it

Everything goes through `uv`; the lockfile is the environment. Python 3.12.

```bash
uv sync                                                # once, and after pyproject changes
uv run pytest -q                                       # make test (117 tests after Session 2)
uv run ruff check . && uv run ruff format --check .    # make lint
uv run curvecarry fetch    # Phase 1 (placeholder until then)
uv run curvecarry build --step harmonise   # 1.8: data/processed/curves.parquet
uv run curvecarry build --step zero        # 1.9: curves_zero.parquet, sample window, checks
uv run curvecarry run      # step 5.3
uv run curvecarry report   # step 6.4
```

### This machine

- Windows 11, Git Bash for the shell. The repo path has spaces, `&` and `)`
  in it: always quote it.
- `make` is GNU Make 4.4.1 from `winget install ezwinports.make --scope user`
  (installed 2026-09-16). It lives at
  `C:\Users\astha\AppData\Local\Microsoft\WinGet\Packages\ezwinports.make_Microsoft.Winget.Source_8wekyb3d8bbwe\bin\make.exe`
  and is on `PATH` for new shells; an old shell needs that directory prepended.
- **Set `PYTHONIOENCODING=utf-8` before any Python that prints non-ASCII**
  (β, λ, τ, em-dashes). Without it Python encodes stdout as cp1252 and
  crashes or writes mojibake. `uv run` inherits it from the environment.
- The credential helper is `manager` (global); `git push` to
  `https://github.com/uty101/Yield-Curve-Carry-Strategy.git` authenticates
  through it.
- `gh` is not installed and `gh auth login` needs a browser; `scripts/gh_issue.py`
  talks to the REST API with the same stored credential instead.

### Data state on disk

`data/raw/` is git-ignored except `manifest.json`; `data/interim/` and
`data/processed/` are git-ignored; everything in `data/checks/` is committed.
Fetched so far (2026-09-17): `data/raw/fred/` — the 10 US DGS series (1.1);
`data/raw/boe/` — the nominal month-end archive zip (1.2);
`data/raw/bundesbank/` — 6 Svensson parameter series + the 10y check (1.3);
`data/raw/mof/` — the JGB historical and current-month files (1.4);
`data/raw/boc/` — the zero-coupon curve and Valet benchmarks (1.5);
`data/raw/bdf/` — the 10 TEC exports (1.6; needs `BDF_API_KEY`);
`data/raw/bis/` — 7 policy-rate series; `data/raw/fred/` also holds the 5
OECD interbank, the 5 OECD immediate-rate (`IRSTCI01*`, 2026-09-22, the
policy-gap fill) and 4 daily FX series (1.7); `data/raw/gsw/` — the Fed's
GSW zero curve `feds200628` (1.9 check, 2026-09-22).
`data/interim/curves_{us,gb,de,jp,ca,fr}.parquet`, `svensson_params_de.parquet`,
`short_rates.parquet`, `funding.parquet`, `fx.parquet`, `gsw_us.parquet` are built;
`data/processed/curves.parquet` (1.8) and `curves_zero.parquet` (1.9) too. Re-create
with `uv run curvecarry fetch --all && uv run curvecarry build --all`.

Source facts learned in the probe and the session-1 review that later steps
depend on (full table in `decisions/sources.md`, the FR/IT ruling in
`decisions/euro_curves.md`):

- **Six countries, not seven.** Italy is dropped: no national curve is
  reachable, and the ECB euro-area composite curves are never labelled FR or
  IT. France is the Banque de France TEC constant-maturity series (par, 1 to
  30 years, daily); the records need the key in the environment variable
  `BDF_API_KEY`, read from the environment only. Without a valid key the API
  returns 200 with zero rows — the fetch must assert on a non-empty body.
- **Funding rate is the BIS policy rate** (`WS_CBPOL`, monthly) for USD, GBP,
  JPY, CAD and the euro area (`XM`; the national BIS series `DE` and `FR`
  before `hedge.eur_splice = 1999-01-31`). **It is never placed on a
  curve**: it lives in `data/interim/funding.parquet`, joined by country and
  date, and every bucket return is an excess return over it
  (`r_excess_local = r_local − r_short_local/12`; the hedged return is that
  excess return by covered interest parity, the unhedged one is
  `r_local + Δln S − r_short_base/12`). Below the shortest observed zero
  tenor the curve is flat (`short_end = "flat"`, the one exception to rule
  13). `decisions/short_anchor.md` has the per-country short end and what
  it does to the 1-year rolldown. The OECD 3-month interbank series on FRED
  (`IR3TIB01*`, one series type for all five currencies, USD included) are a
  robustness column only: JPY starts 2002, GBP and EUR stop at 2026-01, and
  the interbank credit spread in 2008 would read as carry. **Gaps in the
  BIS policy series are filled from the OECD immediate rate** (FRED
  `IRSTCI01*`, rule of 2026-09-22) with `source = "fred_immediate"` on the
  row; only JP has any (116 months, three windows, listed in
  `data/checks/funding_fill.csv` and `decisions/short_anchor.md`).
- **FX is the FRED daily series** `DEXUSUK`, `DEXJPUS`, `DEXCAUS`, `DEXUSEU`,
  sampled at the last observation of the month like the curves, and
  normalised in the loader to units of base currency per unit of foreign
  currency. The monthly-average `EX*` series are not used.
- MOF's JGB file moved under `historical/`; the kickoff URL is 404.
- Bundesbank Svensson parameters start 1997-08-01 (the published Svensson
  yields go back further; the parameters do not).
- The Bank of Canada zero-coupon curve is a GET form, not a static file, and
  is published with a two-week lag; the Valet benchmark group is the fallback.
- The BoE `latest-yield-curve-data.zip` is not used; the month-end archive
  (`glcnominalmonthedata.zip`) covers everything up to `strategy_end`.
- **Two sample windows everywhere a result appears**: the 5-country window
  from `strategy_start = 1997-08-31` (Germany is the fifth country) and the
  6-country window from `sample_full_start = 2004-11-30` (France). Set in
  step 1.9 from `data/checks/sample_window.txt`.

---

## Validation status

Empty at the start. Each gate writes one dated line here when it passes.

| Gate | Date | Result |
|---|---|---|
| PLAN.md v2 approved by owner | 2026-09-16 | PLAN.md v2 approved by owner 2026-09-16 (commit 2c6040b), issue #2 |
| Session 0 (0.2, 0.3) | 2026-09-17 | Session 0 approved 2026-09-17 (142a14e), issue #6 |
| Session 1 (1.1–1.7, all loaders) | 2026-09-22 | Session 1 approved 2026-09-22 (ccd656f), issue #9 |
| Phase 1 gate: `coverage.csv` and `par_zero_gap.csv` reviewed; `strategy_start` set | — | — |
