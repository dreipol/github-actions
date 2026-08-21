#!/usr/bin/env python3
"""Slack reminders for PRs carrying the UNREVIEWED label.

Searches all open or merged PRs in the org labeled UNREVIEWED (merged PRs
still nag — e.g. a hotfix reviewed after the fact), and DMs the assignees if
any, else the requested reviewers, else the author, on Slack.

Cadence: weekly, Monday mornings, no cap — this is a "don't forget it
entirely" nudge, not an urgency escalation. Stateless — reminder text shows
how many weekdays the PR has been unreviewed, derived from the timestamp of
the (latest) UNREVIEWED "labeled" event on the PR. Removing the label (done
manually by the reviewer) stops the reminders.

Environment:
  GH_TOKEN          GitHub token with org-wide PR read access (PAT or App token)
  SLACK_BOT_TOKEN   Slack bot token (scopes: chat:write, im:write)
  GH_SLACK_MAP      JSON object {"github_login": "U_SLACK_MEMBER_ID", ...}
  DRY_RUN           "false" enables real Slack sends; anything else = dry run
  ALLOWLIST         optional JSON array of GitHub logins; if non-empty, only
                    these users receive DMs (pilot phase)
  GH_ORG            organization to search (default: dreipol)
"""

import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

GITHUB_API = "https://api.github.com"
SLACK_API = "https://slack.com/api/chat.postMessage"
LABEL = "UNREVIEWED"
LOCAL_TZ = ZoneInfo("Europe/Zurich")
REQUEST_TIMEOUT = 15  # seconds; a hung connection must not stall the whole run


def github_request(path, token, params=None):
    url = f"{GITHUB_API}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
        return json.load(response)


def github_paginate(path, token, params=None, items_key=None):
    page = 1
    while True:
        page_params = dict(params or {}, per_page=100, page=page)
        data = github_request(path, token, page_params)
        items = data[items_key] if items_key else data
        yield from items
        if len(items) < 100:
            return
        page += 1


def search_unreviewed_prs(org, token):
    query = f"org:{org} is:pr (is:merged OR is:open) label:{LABEL}"
    return list(github_paginate("/search/issues", token, {"q": query}, items_key="items"))


def label_anchor(repo, number, token):
    """Timestamp of the latest UNREVIEWED 'labeled' event, or None."""
    latest = None
    for event in github_paginate(f"/repos/{repo}/issues/{number}/timeline", token):
        if event.get("event") == "labeled" and event.get("label", {}).get("name") == LABEL:
            created = event.get("created_at")
            if created and (latest is None or created > latest):
                latest = created
    if latest is None:
        return None
    return datetime.fromisoformat(latest.replace("Z", "+00:00"))


def nag_number(anchor_date, today):
    """Count of weekdays d with anchor_date < d <= today.

    Labeled Monday -> Tuesday run = 1; labeled Friday -> Monday run = 1
    (weekends don't count). Used as the "N weekdays unreviewed" display age.
    """
    count = 0
    day = anchor_date
    while day < today:
        day = date.fromordinal(day.toordinal() + 1)
        if day.weekday() < 5:
            count += 1
    return count


def pr_targets(repo, number, author, token):
    """(logins, is_author_fallback) — assignees, else requested reviewers, else the author.

    Assignees win first: reassigning a PR to someone (e.g. a reviewer handing
    it back to the author after requesting changes) signals who the ball is
    with now, and requested_reviewers isn't cleared by submitting a review.
    """
    pull = github_request(f"/repos/{repo}/pulls/{number}", token)
    for team in pull.get("requested_teams", []):
        print(f"SKIP team reviewer '{team['slug']}' on {repo}#{number} (teams unsupported)")
    assignees = [user["login"] for user in pull.get("assignees", [])]
    if assignees:
        return assignees, False
    reviewers = [user["login"] for user in pull.get("requested_reviewers", [])]
    if reviewers:
        return reviewers, False
    return [author], True


def format_dm(entries):
    lines = [
        "👋 You have pull requests waiting for review:",
        "",
    ]
    for entry in entries:
        nag = entry["nag"]
        age = f"{nag} weekday{'s' if nag != 1 else ''} unreviewed"
        lines.append(f"<{entry['url']}|{entry['title']}> ({entry['repo']}, {age})")
        if entry["author_fallback"]:
            lines.append("        ↳ your PR has *no reviewer assigned* — please request one")
    lines += [
        "",
        "_Review the PR, then remove the `UNREVIEWED` label to stop these reminders._",
    ]
    return "\n".join(lines)


def send_dm(slack_id, text, token):
    payload = json.dumps({"channel": slack_id, "text": text}).encode()
    request = urllib.request.Request(SLACK_API, data=payload, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    })
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
        result = json.load(response)
    if not result.get("ok"):
        raise RuntimeError(f"Slack error for {slack_id}: {result.get('error')}")


def main():
    gh_token = os.environ["GH_TOKEN"]
    org = os.environ.get("GH_ORG", "dreipol")
    dry_run = os.environ.get("DRY_RUN", "true").lower() != "false"
    slack_map = json.loads(os.environ.get("GH_SLACK_MAP") or "{}")
    allowlist = json.loads(os.environ.get("ALLOWLIST") or "[]")

    today = datetime.now(LOCAL_TZ).date()
    prs = search_unreviewed_prs(org, gh_token)
    print(f"Found {len(prs)} open/merged PRs with label {LABEL} (dry_run={dry_run})")

    queue = {}  # github login -> list of PR entries
    for pr in prs:
        repo = pr["repository_url"].removeprefix(f"{GITHUB_API}/repos/")
        number = pr["number"]
        anchor = label_anchor(repo, number, gh_token)
        if anchor is None:
            print(f"SKIP {repo}#{number}: no {LABEL} labeled event found")
            continue
        nag = nag_number(anchor.astimezone(LOCAL_TZ).date(), today)
        if nag == 0:
            print(f"SKIP {repo}#{number}: labeled today, first nag next Monday")
            continue
        targets, author_fallback = pr_targets(repo, number, pr["user"]["login"], gh_token)
        for login in targets:
            queue.setdefault(login, []).append({
                "repo": repo, "url": pr["html_url"], "title": pr["title"],
                "nag": nag, "author_fallback": author_fallback,
            })

    failures = 0
    for login, entries in sorted(queue.items()):
        summary = ", ".join(f"{e['repo']}#{e['url'].rsplit('/', 1)[1]} (nag {e['nag']})" for e in entries)
        if allowlist and login not in allowlist:
            print(f"SKIP {login}: not on allowlist — {summary}")
            continue
        slack_id = slack_map.get(login)
        if not slack_id:
            print(f"SKIP {login}: no Slack mapping in GH_SLACK_MAP — {summary}")
            continue
        if dry_run:
            print(f"DRY-RUN would DM {login} ({slack_id}): {summary}")
            continue
        try:
            send_dm(slack_id, format_dm(entries), os.environ["SLACK_BOT_TOKEN"])
            print(f"SENT DM to {login} ({slack_id}): {summary}")
            time.sleep(1)  # chat.postMessage: ~1 msg/sec
        except Exception as error:
            print(f"ERROR DMing {login}: {error}")
            failures += 1

    if failures:
        sys.exit(f"{failures} Slack DM(s) failed")


if __name__ == "__main__":
    main()
