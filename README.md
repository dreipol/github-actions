# github-actions

Repository with github actions for the CI workflow

## PR hygiene

Automation so PRs don't sit unreviewed ([templates/pr-label.yml](templates/pr-label.yml), [.github/workflows](/.github/workflows), [scripts/pr_reminder.py](scripts/pr_reminder.py)).

**How it works**

1. **Label** — every new PR automatically gets the `UNREVIEWED` label (workflow in each repo, see below). Drafts included; Dependabot PRs are skipped (their workflow token is read-only).
2. **Approve → label removed** — an approving review removes `UNREVIEWED` automatically, also on already merged PRs (GitHub allows approving after merge). Reviewed without approving? Remove the label manually. The label is only re-added when a PR is reopened.
3. **Reminders** — a Monday-morning cron in this repo searches all open PRs and PRs merged within the last year in the org that still carry the label (merged PRs still nag — e.g. a hotfix reviewed after the fact) and DMs the assignees on Slack, else the requested reviewers, else the author if no reviewer was requested. Weekly, no cap — this is a "don't forget it entirely" nudge, not an urgency escalation.

**Adding the label workflow to a repo**

Copy [templates/pr-label.yml](templates/pr-label.yml) to `.github/workflows/pr-label.yml`. That's all — no secrets needed. `scripts/rollout_pr_label.sh` opens these PRs org-wide (dry run by default, `--execute` to run).

**Reminder configuration** (org/repo Actions variables + secrets on this repo)

| Name                     | Kind     | Purpose                                                                                                                      |
| ------------------------ | -------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `GH_SLACK_MAP`           | variable | JSON `{"github_login": "U_SLACK_MEMBER_ID"}`; unmapped users are skipped and logged                                          |
| `PR_HYGIENE_DRY_RUN`     | variable | anything but `false` = log instead of DM (safe default)                                                                      |
| `PR_HYGIENE_ALLOWLIST`   | variable | optional JSON array of GitHub logins; if non-empty only these get DMs (pilot)                                                |
| `PR_BOT_APP_ID`          | variable | App ID of the PR reminder GitHub App (see below)                                                                             |
| `PR_BOT_APP_PRIVATE_KEY` | secret   | private key (`.pem` contents) of that GitHub App                                                                             |
| `SLACK_BOT_TOKEN`        | secret   | bot token of the Slack app from [docs/slack-app-manifest.yml](docs/slack-app-manifest.yml) (scopes `chat:write`, `im:write`) |
| `SLACK_WEBHOOK`          | secret   | existing webhook, used only to report failed reminder runs                                                                   |

Find a Slack member ID: profile → ⋯ → "Copy member ID".

**Launch phases:** 1) `PR_HYGIENE_DRY_RUN=true` — inspect run logs. 2) `false` + allowlist — pilot users get real DMs. 3) empty allowlist — org-wide.

**GitHub App:** the reminder reads PRs org-wide (incl. private repos) with a token minted per run by `actions/create-github-app-token`. Setup (org owner): dreipol → Settings → Developer settings → GitHub Apps → New GitHub App; webhook off; repository permissions _Pull requests: Read_ and _Issues: Read_; installable only on this account. Install it on **All repositories**, then store its App ID as `PR_BOT_APP_ID` and a generated private key as `PR_BOT_APP_PRIVATE_KEY`.

Tests: `cd scripts && python3 -m unittest`

## Core technology versions

Keeps the versions of Python, Django, djangoCMS, Node, Next and React up to date in the tab **Web / Server** of the project Google Sheet, for update planning ([templates/core-versions.yml](templates/core-versions.yml), [.github/workflows/reusable-core-versions.yml](.github/workflows/reusable-core-versions.yml), [scripts/core_versions.py](scripts/core_versions.py)).

**How it works**

1. **Trigger** — every push (e.g. a merged PR) to `main`/`master` or `stage`/`develop` of a project repo runs the workflow in that repo. To fill the sheet right away, start it by hand: Actions → "Core versions" → Run workflow, pick the branch.
2. **Versions** — the script reads the project's own files, in this order (the first file with a version wins): `Dockerfile` (`FROM python:…` / `node:…`, `ENV NODE_VERSION`), `.python-version`, `.nvmrc`, `Pipfile.lock`, `uv.lock`, `package-lock.json`, `yarn.lock`. In a monorepo each folder (e.g. `backend/`, `frontend/`) is read separately.
3. **Rows** — the sheet stays hand-maintained: one row per project environment, name in column **C**, GitHub repo URL in column **K**. `main`/`master` updates the rows whose name does not contain `stage`, `stage`/`develop` the rows whose name contains `stage`.
4. **Cells** — only the version columns are written: **AH** Python, **AI** Django, **AK** Next, **AL** Node, **AM** React, **AO** djangoCMS. A cell is only written when the value changed, never emptied, and not replaced by a less precise form of itself (the sheet's `3.13.1` stays when the Dockerfile only says `python:3.13`). The run log lists every change, e.g. `Update Django from 5.2.10 to 5.2.17 in AI12 for project '…' (from Pipfile.lock)`.

Each row has one repo URL in column K; the same repo can appear in several rows (e.g. prod and stage). Rows whose name contains `frontend` or `backend` only get the versions of the matching monorepo folder (e.g. `frontend/`).

**Adding the workflow to a repo**

Copy [templates/core-versions.yml](templates/core-versions.yml) to `.github/workflows/core-versions.yml` and make sure the project has a row with the repo URL in column K. No repo secrets needed.

**Configuration** (org-level, visible to private repos)

| Name                               | Kind     | Purpose                                                                                 |
| ---------------------------------- | -------- | --------------------------------------------------------------------------------------- |
| `CORE_VERSIONS_GOOGLE_CREDENTIALS` | secret   | JSON key of the Google service account; the sheet is shared with its e-mail as _Editor_ |
| `CORE_VERSIONS_DRY_RUN`            | variable | anything but `false` = log the planned changes instead of writing them (safe default)   |

The sheet ID, tab and columns are constants at the top of [scripts/core_versions.py](scripts/core_versions.py).

Try locally (Python ≥ 3.11): `python3 scripts/core_versions.py path/to/project` prints the versions found. To also see the planned sheet changes (dry run), add `GITHUB_REPOSITORY=dreipol/<repo> GITHUB_REF_NAME=main GOOGLE_ACCESS_TOKEN=…` (a token with the spreadsheets scope, e.g. from the service account via `gcloud auth print-access-token --scopes=https://www.googleapis.com/auth/spreadsheets`).

## build

```
dreipol/github-actions/build@master
```

Builds a docker image with the commit sha as tag.
If an image with the same tag already exists in the registry, it will use that image instead of building
another one. Tries to use the docker cache from master, stage, branch to speed up the build.

Required env variables:

- GCP_SERVICEACCOUNT_KEY
- GCR_IMAGE
- GITHUB_REF_SLUG
- GITHUB_SHA
- PROJECT_NAME

## cleanup

```
dreipol/github-actions/cleanup@master
```

Deletes images from the google cloud registry older than 30 days that have 1 or less tags.
This is intended to remove all images that only have their git hash as tag.
Images that are tagged with the git hash and another tag (for example master) won't be deleted.

Required env variables:

- GCP_SERVICEACCOUNT_KEY
- GCR_IMAGE

## codeclimate

```
dreipol/github-actions/codeclimate-env@master
dreipol/github-actions/codeclimate-coverage@master
```

Provides the codeclimate coverage tool. First you need to use codeclimate-env to inject the necessary
environment variables for the codeclimate coverage tool.
Then you can use the codeclimate-coverage action.
You can find an example on how to use it [here](https://github.com/dreipol/bertschi-driver-server/blob/38fc56a50d8ce1d27a2e9814c845859658d77a32/.github/workflows/ci.yml#L49).

Required env variables:

- CC_TEST_REPORTER_ID (only for codeclimate-coverage)

## deploy

```
dreipol/github-actions/deploy@master
```

Pulls an image with the commit hash from the registry and pushes it to the openshift cluster.

Required env variables:

- ASPECTRA_REGISTRY
- ASPECTRA_TAG
- DEPLOY_IMAGE
- GCP_SERVICEACCOUNT_KEY
- GCR_IMAGE
- GITHUB_SHA
- OPENSHIFT_TOKEN
- OPENSHIFT_USER

## deployment-status

```
dreipol/github-actions/deployment-status@master
```

Monitors the rollout of a deployment configuration. This is usually used after running the deploy action
to monitor if the deployment from an imagestream succeeded.

Required env variables:

- OPENSHIFT_HOST
- OPENSHIFT_TOKEN
- OPENSHIFT_USER
- OPENSHIFT_PROJECT
- DEPLOYMENT_CONFIG

## deployment-status-reverse proxy

```
dreipol/github-actions/deployment-status@master
```

This one is specific to the reverse proxy, since it deplyos almost all projects, we want to make sure all the
projects deploy ok before the job succeeds.

Required env variables:

- OPENSHIFT_HOST
- OPENSHIFT_TOKEN
- OPENSHIFT_USER
- OPENSHIFT_PROJECT

## push

```
dreipol/github-actions/push@master
```

Pushes an image with the commit sha as tag to the google registry.
Also tags it with the current branch name.

Required env variables:

- GCP_SERVICEACCOUNT_KEY
- GCR_IMAGE
- GITHUB_REF_SLUG
- GITHUB_SHA

## set-logs-url

```
dreipol/github-actions/set-logs-url@master
```

Injects the url to the raw logs into the environment variables

Required env variables:

- GITHUB_TOKEN
- JOB_NAME

## slack

```
dreipol/github-actions/slack@master
```

Sends a slack message with your defined text.
**Info:** You can use slack@silent to log the messages instead of sending them to slack

Required env variables:

- ENVIRONMENT
- SLACK_WEBHOOK
- TEXT

## slugify

```
dreipol/github-actions/slugify@master
```

Creates slug names for branches so that we can use them as docker tags

Required env variables:

- GITHUB_HEAD_REF
- GITHUB_BASE_REF
- GITHUB_REF
- GITHUB_SHA
