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

One step per session. The owner says `Do step X.Y only`. The session does
that step as written in `PLAN.md`, runs `make test` and `make lint`, writes
`review/X.Y.md` from `review/TEMPLATE.md`, commits on `main` with message
`Step X.Y: <one line>`, pushes, shows the test output and the review file,
and stops. Never two steps. Never the next step because it "makes sense".
If a step cannot be done as written, stop and say why. If a step needs a
choice that neither `PLAN.md` nor `config.toml` makes, stop and ask.

---

## Invariants

Each has a test named next to it once the step that builds it lands. Until
then the cell says which step will add the test. `review` means there is no
test and the reviewer checks it from the review file. Do not weaken a test
to make a run pass.

| # | Invariant | Test |
|---|---|---|
| 1 | One step per session: `make test`, `make lint`, review, commit, push, stop. | review |
| 2 | Yields are **decimals** everywhere inside the package (0.0425, never 4.25). Conversion from percent happens once, in the loader, and nowhere else. Every loader test fails on a yield above 0.5 or below -0.05. | pending 1.1–1.7 (one `test_units_*` per loader) |
| 3 | `par` and `zero` are never mixed in one calculation. Any function that takes a curve asserts on `curve_type`. | pending 1.9 / 2.1 |
| 4 | Every number that affects a result comes from `config.toml`. Nothing in `src/` reads a knob that is not there. | review |
| 5 | Raw files are never overwritten; every fetch appends to `data/raw/manifest.json` (URL, sha256, bytes, fetched_at, source). A re-fetch gets a new filename with the fetch date. | pending 0.2 |
| 6 | Every strategy run is a row in `reports/specifications.csv` **before** it computes. A variant with no row did not happen. The file is append-only. N in the deflated Sharpe is that row count. | pending 0.1 |
| 7 | Anything a function uses at month *t* is dated on or before *t*. Expanding-window PCA scores at *t* do not change when later months are appended. | pending 5.4 |
| 8 | No number in `README.md` is typed by hand. The results table is pasted from `reports/results.md` and a test asserts equality. | pending 6.4 |
| 9 | Nothing is imported from the project 1 repo. The duration-budget engine is written here. | review |
| 10 | Do not add features, refactor other modules, or improve earlier steps unless the current step says so. | review |
| 11 | If a data source is unreachable, stop and say so. A substitution is written into `decisions/` before it is used. | review |
| 12 | Tests never use the network. Every `parse()` is tested on a fixture in `tests/fixtures/` (first 50 rows of the real download). | review (a test that needs the internet is a bug) |
| 13 | Interpolation in yield is linear in tenor, between observed tenors only. One interpolation function in the package; every module uses it. No extrapolation, ever: a tenor beyond the longest observed is missing. | pending 1.8 |
| 14 | `config.toml` is written in full in step 0.1 with every key the plan names. A later step may change a default only if the step says so, and that change is a commit on its own. | review |

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
uv run pytest -q                                       # make test
uv run ruff check . && uv run ruff format --check .    # make lint
uv run curvecarry fetch    # Phase 1 (placeholder until then)
uv run curvecarry build    # steps 1.8-1.9
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

### Data state on disk

Nothing fetched yet (session 1, 2026-09-16). `data/raw/`, `data/interim/`
and `data/processed/` are empty and git-ignored except `data/raw/manifest.json`
and everything in `data/checks/`, which are committed. Update this block
in the step that first writes to each.

Source facts learned in the probe that later steps depend on (full table in
`decisions/sources.md`):

- MOF's JGB file moved under `historical/`; the kickoff URL is 404.
- Bundesbank Svensson parameters start 1997-08-01 (the published Svensson
  yields go back further; the parameters do not).
- The Bank of Canada zero-coupon curve is a GET form, not a static file, and
  is published with a two-week lag; the Valet benchmark group is the fallback.
- Banque de France Webstat has TEC 1–30 daily but the records need a free API
  key; without it the response is 200 with zero rows, not an error.
- FRED's OECD 3-month series for Japan starts 2002-04; BIS policy rates are
  the long-history alternative.

---

## Validation status

Empty at the start. Each gate writes one dated line here when it passes.

| Gate | Date | Result |
|---|---|---|
| Phase 1 gate: `coverage.csv` and `par_zero_gap.csv` reviewed; `strategy_start` set | — | — |
