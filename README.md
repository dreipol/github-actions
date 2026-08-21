# github-actions

Repository with github actions for the CI workflow

## PR hygiene

Automation so PRs don't sit unreviewed ([templates/pr-label.yml](templates/pr-label.yml), [.github/workflows](/.github/workflows), [scripts/pr_reminder.py](scripts/pr_reminder.py)).

**How it works**

1. **Label** — every new PR automatically gets the `UNREVIEWED` label (workflow in each repo, see below). Drafts and bot PRs included.
2. **Review, then remove the label manually** — removing `UNREVIEWED` is the "I reviewed this" acknowledgment. Automation never removes or re-adds it.
3. **Reminders** — a Monday-morning cron in this repo searches all open or merged PRs in the org that still carry the label (merged PRs still nag — e.g. a hotfix reviewed after the fact) and DMs the assignees on Slack, else the requested reviewers, else the author if no reviewer was requested. Weekly, no cap — this is a "don't forget it entirely" nudge, not an urgency escalation.

**Adding the label workflow to a repo**

Copy [templates/pr-label.yml](templates/pr-label.yml) to `.github/workflows/pr-label.yml`. That's all — no secrets needed. `scripts/rollout_pr_label.sh` opens these PRs org-wide (dry run by default, `--execute` to run).

**Reminder configuration** (org/repo Actions variables + secrets on this repo)

| Name | Kind | Purpose |
| --- | --- | --- |
| `GH_SLACK_MAP` | variable | JSON `{"github_login": "U_SLACK_MEMBER_ID"}`; unmapped users are skipped and logged |
| `PR_HYGIENE_DRY_RUN` | variable | anything but `false` = log instead of DM (safe default) |
| `PR_HYGIENE_ALLOWLIST` | variable | optional JSON array of GitHub logins; if non-empty only these get DMs (pilot) |
| `PR_BOT_PAT` | secret | GitHub token with org-wide PR read (test phase; swap for a GitHub App later, only the `GH_TOKEN` line in `pr-reminder.yml` changes) |
| `SLACK_BOT_TOKEN` | secret | bot token of the Slack app from [docs/slack-app-manifest.yml](docs/slack-app-manifest.yml) (scopes `chat:write`, `im:write`) |
| `SLACK_WEBHOOK` | secret | existing webhook, used only to report failed reminder runs |

Find a Slack member ID: profile → ⋯ → "Copy member ID".

**Launch phases:** 1) `PR_HYGIENE_DRY_RUN=true` — inspect run logs. 2) `false` + allowlist — pilot users get real DMs. 3) empty allowlist — org-wide.

**GitHub App swap (production):** org owner creates an App (permissions: Pull requests read, Members read), installs it org-wide; add `APP_ID` var + `APP_PRIVATE_KEY` secret; in `pr-reminder.yml` mint the token with `actions/create-github-app-token@v2` and point `GH_TOKEN` at its output.

Tests: `cd scripts && python3 -m unittest`


## build
```
dreipol/github-actions/build@master
```
Builds a docker image with the commit sha as tag.
If an image with the same tag already exists in the registry, it will use that image instead of building
another one. Tries to use the docker cache from master, stage, branch to speed up the build.

Required env variables:
* GCP_SERVICEACCOUNT_KEY
* GCR_IMAGE
* GITHUB_REF_SLUG
* GITHUB_SHA   
* PROJECT_NAME

## cleanup
```
dreipol/github-actions/cleanup@master
```
Deletes images from the google cloud registry older than 30 days that have 1 or less tags.
This is intended to remove all images that only have their git hash as tag.
Images that are tagged with the git hash and another tag (for example master) won't be deleted.

Required env variables:
* GCP_SERVICEACCOUNT_KEY
* GCR_IMAGE

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
* CC_TEST_REPORTER_ID (only for codeclimate-coverage)

## deploy
```
dreipol/github-actions/deploy@master
```
Pulls an image with the commit hash from the registry and pushes it to the openshift cluster.

Required env variables:
* ASPECTRA_REGISTRY
* ASPECTRA_TAG
* DEPLOY_IMAGE
* GCP_SERVICEACCOUNT_KEY
* GCR_IMAGE
* GITHUB_SHA   
* OPENSHIFT_TOKEN
* OPENSHIFT_USER


## deployment-status
```
dreipol/github-actions/deployment-status@master
```
Monitors the rollout of a deployment configuration. This is usually used after running the deploy action
to monitor if the deployment from an imagestream succeeded.

Required env variables:
* OPENSHIFT_HOST
* OPENSHIFT_TOKEN
* OPENSHIFT_USER
* OPENSHIFT_PROJECT
* DEPLOYMENT_CONFIG

## deployment-status-reverse proxy
```
dreipol/github-actions/deployment-status@master
```
This one is specific to the reverse proxy, since it deplyos almost all projects, we want to make sure all the
projects deploy ok before the job succeeds.

Required env variables:
* OPENSHIFT_HOST
* OPENSHIFT_TOKEN
* OPENSHIFT_USER
* OPENSHIFT_PROJECT

## push
```
dreipol/github-actions/push@master
```
Pushes an image with the commit sha as tag to the google registry. 
Also tags it with the current branch name.

Required env variables:
* GCP_SERVICEACCOUNT_KEY
* GCR_IMAGE
* GITHUB_REF_SLUG
* GITHUB_SHA   

## set-logs-url
```
dreipol/github-actions/set-logs-url@master
```
Injects the url to the raw logs into the environment variables

Required env variables:
* GITHUB_TOKEN
* JOB_NAME  


## slack
```
dreipol/github-actions/slack@master
```
Sends a slack message with your defined text.
**Info:** You can use slack@silent to log the messages instead of sending them to slack

Required env variables:
* ENVIRONMENT
* SLACK_WEBHOOK
* TEXT

## slugify
```
dreipol/github-actions/slugify@master
```
Creates slug names for branches so that we can use them as docker tags

Required env variables:
* GITHUB_HEAD_REF
* GITHUB_BASE_REF
* GITHUB_REF
* GITHUB_SHA