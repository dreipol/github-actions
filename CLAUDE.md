# CLAUDE.md

## Core technology versions

Writes the Python, Django, djangoCMS, Node, Next and React versions of a project into the tab "Web / Server" of the Google Sheet "39H Serverliste und SLA". User-facing docs: the "Core technology versions" section in `README.md`.

### Files

- `templates/core-versions.yml`: copied by hand into each project repo as `.github/workflows/core-versions.yml`. Triggers on push to `main`/`master`/`stage`/`develop` and `workflow_dispatch`, then calls the reusable workflow with `secrets: inherit`.
- `.github/workflows/reusable-core-versions.yml`: checks out the project (`project/`) and this repo at `master` (`tools/`), gets a Google access token from the org secret `CORE_VERSIONS_GOOGLE_CREDENTIALS`, runs the script. Skips Dependabot runs.
- `scripts/core_versions.py`: the whole logic, one file.

### How the script works

1. `collect_versions()` walks the project folders (skipping `SKIP_FOLDERS`) and runs the readers in `FILES` on each folder. Order in `FILES` is priority: the first file with a version of a technology wins.
2. `read_rows()` reads `A:AO` of the tab once; `parse_rows()` keeps rows with a GitHub URL in column K.
3. `plan_updates()` combines the versions of all folders (root first, then alphabetical; first wins), picks the rows of this repo and environment (`main`/`master` → rows without "stage" in column C, `stage`/`develop` → rows with "stage") and lists the cells that changed.
4. `main()` prints one line per change (`describe_update()`) and writes each cell with `write_cell()`, unless `DRY_RUN` is `"true"`.

### Rules to keep

- **Standard library only** (`tomllib` needs Python ≥ 3.11). No `pip install`, no PyYAML; pnpm and yarn lockfiles are read line by line on purpose.
- **Only support file formats projects actually use.** Before adding or dropping one, check the real repos (e.g. `gh search code --owner dreipol --filename <file>`). The old npm 6 `package-lock.json` (`"dependencies"`) is still used by several projects.
- **Never touch other cells.** Only the columns in `VERSION_COLUMNS` are written, one cell at a time, with `valueInputOption=RAW` (so `3.10` stays text). Cells are never emptied; a value is not replaced by a less precise one (`3.13.1` stays when the Dockerfile says `3.13`).
- **One repo per row.** Column K holds exactly one repo URL; the same repo can be in several rows. There is deliberately no frontend/backend split: a monorepo's folders are combined and every row of the repo gets all versions (reviewer decision).
- **No GitHub App, no GitHub API.** Each project reads its own checkout. Don't reintroduce a central cron or org-wide token.
- **Changes go live immediately.** Projects use the workflow and script from `master`, so a mistake on `master` breaks every project at once.

### Testing

There are no unit tests (removed on purpose). Check changes by running the script on real projects:

```sh
# Versions only, no Google access needed
python3 scripts/core_versions.py path/to/project

# Planned sheet changes (dry run), with a token of the service account
GITHUB_REPOSITORY=dreipol/<repo> GITHUB_REF_NAME=master DRY_RUN=true \
GOOGLE_ACCESS_TOKEN=$(gcloud auth print-access-token --scopes=https://www.googleapis.com/auth/spreadsheets) \
python3 scripts/core_versions.py path/to/project
```

Without `DRY_RUN=true` the script writes to the real sheet. The system Python on macOS is 3.9 (no `tomllib`); use Homebrew's `python3.13`.
