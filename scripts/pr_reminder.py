#!/usr/bin/env python3
"""Slack reminders for PRs carrying the UNREVIEWED label.

Searches all open PRs and PRs merged within the last year in the org labeled
UNREVIEWED (merged PRs still nag — e.g. a hotfix reviewed after the fact), and DMs the assignees if
any, else the requested reviewers, else the author, on Slack.

Cadence: weekly, Monday mornings, no cap — this is a "don't forget it
entirely" nudge, not an urgency escalation. Stateless — reminder text shows
how many weekdays the PR has been unreviewed, derived from the timestamp of
the (latest) UNREVIEWED "labeled" event on the PR. Approving the PR removes
the label automatically (see reusable-pr-label.yml); removing it manually
works too. Either stops the reminders.

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
import random
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

GITHUB_API = "https://api.github.com"
SLACK_API = "https://slack.com/api/chat.postMessage"
LABEL = "UNREVIEWED"
LOCAL_TZ = ZoneInfo("Europe/Zurich")
MERGED_MAX_AGE = timedelta(days=365)  # older merged PRs stop nagging; also keeps search < 1000-hit cap
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


def search_unreviewed_prs(org, token, today):
    cutoff = (today - MERGED_MAX_AGE).isoformat()
    query = f"org:{org} is:pr label:{LABEL} (is:open OR (is:merged merged:>={cutoff}))"
    # advanced_search: legacy search silently ignores OR/parentheses (0 hits)
    params = {"q": query, "advanced_search": "true"}
    return list(github_paginate("/search/issues", token, params, items_key="items"))


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
    with now. GitHub drops a reviewer from requested_reviewers once they
    submit any review, so a comment-only review falls back to the author.
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


INTROS = [
    "👋 You have pull requests waiting for review:",
    "🛋️ Knock knock knock, reviewer. Knock knock knock, reviewer. Knock knock knock, reviewer:",
    "😼 Bazinga! These pull requests are still waiting for you:",
    "🚩 Welcome to Fun with Flags. Today's flag: `UNREVIEWED`, on these PRs:",
    "📜 Per section 37(b) of the Roommate Agreement, these PRs require your review:",
    "🐈 Until someone looks, these PRs are both reviewed and unreviewed. Please collapse the wave function:",
    "🎵 Soft PR, warm PR, little ball of code… I WILL KEEP SINGING UNTIL YOU REVIEW. I KNOW ALL THE VERSES:",
    "🧠 I'm not saying you forgot these PRs. I'm saying my mother had me tested, and I'd remember:",
    "🐙 Random fact: octopuses have three hearts. You have one, and these unreviewed PRs are breaking it:",
    "🖖 I have invoked the Roommate Agreement's emergency clause. You are now legally my reviewer. Bazinga is NOT applicable:",
    "🧪 I have run 4,000 simulations. In 3,999 of them you review these PRs. In the other one, Leonard does it and it goes horribly:",
    "🕯️ I have lit a candle for each of these PRs. The candles are running low. REVIEW THEM:",
    "🦆 I asked the rubber duck to review these. It refused. It's on you now:",
    "👁️ The PRs have started whispering your name at night. Please make them stop:",
    "📬 You've got PRs! These are waiting for your review:",
    "🔥 This is fine. Everything is fine. These PRs are fine. (They are not fine. Review them.):",
    "🦝 A raccoon got into the repo and labeled these UNREVIEWED. Honestly, the raccoon has a point:",
    "🤓 Fun fact: unreviewed PRs are 100% more likely to be forgotten. Here are yours:",
    "📠 This message was faxed from the year 3000. Humanity fell because nobody reviewed these PRs:",
    "🚀 These pull requests are ready for liftoff, they just need your review:",
    "🟫 Random fact: wombats poop cubes. Nobody knows why you haven't reviewed these PRs either:",
    "🦄 Random fact: Scotland's national animal is the unicorn. Equally mythical: a review on these PRs:",
    "🦦 Random fact: sea otters hold hands while sleeping so they don't drift apart. Hold hands with these PRs:",
    "🍌 Random fact: bananas are berries, strawberries are not. Nothing is real. Except these PRs. Review them:",
    "🪐 Random fact: a day on Venus is longer than its year. These PRs have been waiting about one Venus day:",
    "🦩 Random fact: a group of flamingos is called a flamboyance. A group of unreviewed PRs is called this message:",
    "⚔️ Random fact: the shortest war in history lasted about 38 minutes. These PRs have been waiting longer:",
    "🏺 Random fact: Cleopatra lived closer in time to the Moon landing than to the building of the Great Pyramid. These PRs feel about that old:",
    # Useless science (all true)
    "🍯 Science fact: archaeologists found still-edible honey in ancient Egyptian tombs. It has aged better than these PRs:",
    "⭐ Science fact: a teaspoon of neutron star weighs about a billion tonnes. Still lighter than your review backlog:",
    "☀️ Science fact: sunlight needs about 8 minutes 20 seconds to reach Earth. These PRs have been waiting a few more:",
    "🦈 Science fact: sharks are older than trees. These PRs are trying to beat that record:",
    "♟️ Science fact: there are more possible chess games than atoms in the observable universe. There are fewer PRs below. You can do this:",
    "🗼 Science fact: the Eiffel Tower grows about 15 cm in summer from thermal expansion. Your review queue grows all year:",
    "🧊 Science fact: at its triple point, water boils and freezes at the same time. These PRs are both merged and unreviewed at the same time:",
    # Unhinged comedy
    "🦖 A T. rex couldn't review PRs with those tiny arms. What's your excuse?",
    "\U0001fabf A goose has entered the office and refuses to leave until these PRs are reviewed. I cannot help you. Nobody can:",
    "🧟 Day 47. The PRs have formed a society. They have elected a leader. It's the oldest one:",
    "🥔 A potato has eyes and still looks away. Don't be the potato. Review these:",
    # Full scientific language
    "🔬 Abstract: we report n ≥ 1 pull requests exhibiting persistent UNREVIEWED status (p < 0.05). The proposed intervention is listed below:",
    "⚛️ By the second law of thermodynamics, entropy in your review queue increases unless external work is applied. Please apply work:",
    "🧬 Observation: the PRs below show no measurable reviewer interaction during the observation period. Hypothesis: you. Method: review:",
    "📐 Let R be the set of PRs awaiting your review. We prove R ≠ ∅ by construction:",
    "🌡️ At standard temperature and pressure, an unreviewed PR has a half-life of exactly forever:",
    # Other languages
    "🥐 Bonjour ! Ces pull requests attendent ta review depuis plus longtemps qu'un TGV en retard :",
    "🍝 Mamma mia! Queste pull request aspettano la tua review:",
    "🏔️ Bun di! Quests pull requests spetgan sin tia review:",
    "🌮 ¡Ay, caramba! Estas pull requests esperan tu revisión:",
    "🍣 レビューをお願いします！これらのプルリクエストがあなたを待っています：",
    "🏛️ Ave! Hae petitiones recensionem tuam exspectant:",
    "🖖 Qapla'! A true Klingon warrior reviews these PRs today. Glory awaits:",
    # Swiss German, Sheldon style
    "🚪 Chlopf chlopf chlopf, Reviewer. Chlopf chlopf chlopf, Reviewer. Chlopf chlopf chlopf, Reviewer:",
    "😼 Bazinga! Du hesch gmeint, du chönntsch die PRs vergässe? Ich vergiss nüt:",
    "🛋️ Das isch min Platz uf em Sofa. Und das da sind dini PRs:",
    "🧠 Ich bi nöd verruckt, mini Mueter het mi teste lah. Und sie seit, du söttsch die PRs reviewe:",
    "🐈 Weichs Chätzli, warms Chätzli, chlises Pull-Request-Bölleli … bitte reviewe:",
    "🧪 Ich ha 4000 Simulatione gmacht. I allne bisch du am Kafi trinke statt am Reviewe. Bewis mer s Gägeteil:",
    # Genre parodies
    "🦁 Here, in the wild repository, the unreviewed PR waits patiently. Its natural predator, the reviewer, is nowhere to be seen:",
    "🕵️ It was a dark and stormy sprint. The PRs walked into my office. They had that look. Unreviewed:",
    "📯 Hear ye, hear ye! By order of the Crown, the following PRs shall be reviewed forthwith:",
    "🏟️ AND THE PRs ARE STILL UNREVIEWED! UNBELIEVABLE SCENES HERE AT THE REPO! Can anyone step up?!",
    "🔮 Today's horoscope: Mercury is in retrograde, and so is your review queue. Lucky numbers below:",
    "🌦️ Today's forecast: cloudy, with a 100% chance of pull requests:",
    "✈️ This is your captain speaking. We are holding over the review queue. Please return to the upright and reviewing position:",
    "🎬 In a world… where PRs go unreviewed… one developer… must rise:",
    # Own ideas / dev humor
    "🧘 Code waits silently / the merge happened long ago / still no review comes:",
    "🫖 HTTP 418: I'm a teapot. You, however, are a reviewer:",
    "🎰 Congratulations! You have been randomly selected (you were requested) to review:",
    "📈 Unreviewed PRs are up this week. Short them by reviewing:",
    "⚖️ By reading this message you agree to review the PRs below. Terms and conditions apply. There are no terms and conditions:",
    "🧩 Someone centered a div today. Anything is possible. Even reviewing these PRs:",
    "🤖 I am a bot. I have no feelings. If I did, they would be about these PRs:",
    # Dark, bleak, existential
    "🪦 Nobody on their deathbed says 'I wish I'd reviewed more PRs.' But nobody says they're glad they didn't either. Anyway:",
    "🛒 You're a grown adult. You pay taxes. You have a dentist. And you still can't click 'Approve'. That's the life you built:",
    "🕳️ Every PR below was written by someone who believed, for one brief moment, that their work mattered. You took that from them:",
    "🧓 One day your grandkids will ask what you did with your life. You'll say 'I let PRs rot in a queue.' They'll stop visiting. Rightly:",
    "🌌 The universe will end in heat death. Nothing matters. So you might as well review these, it's not like you had plans:",
    "🪞 Look in a mirror. No, really look. That's the person who's been ignoring these PRs. Gross. Anyway, here they are:",
    "😮‍💨 I'm a bot. I don't sleep. I don't eat. I just watch these PRs not get reviewed, week after week. This is my whole life. Help me:",
    "🦴 These PRs have waited so long they now count as historical artifacts. Somewhere an intern is crying. Probably about this:",
]


def format_dm(entries):
    lines = [
        random.choice(INTROS),
        "",
    ]
    for entry in entries:
        nag = entry["nag"]
        age = f"{nag} weekday{'s' if nag != 1 else ''} unreviewed" if nag else "labeled today"
        lines.append(f"<{entry['url']}|{entry['title']}> ({entry['repo']}, {age})")
        if entry["author_fallback"]:
            lines.append("        ↳ your PR has *no pending reviewer* — please (re-)request a review")
    lines += [
        "",
        "_Approve the PR (or remove the `UNREVIEWED` label) to stop these reminders._",
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
    prs = search_unreviewed_prs(org, gh_token, today)
    print(f"Found {len(prs)} open/merged PRs with label {LABEL} (dry_run={dry_run})")

    failures = 0
    queue = {}  # github login -> list of PR entries
    for pr in prs:
        repo = pr["repository_url"].removeprefix(f"{GITHUB_API}/repos/")
        number = pr["number"]
        try:
            anchor = label_anchor(repo, number, gh_token)
            if anchor is None:
                print(f"SKIP {repo}#{number}: no {LABEL} labeled event found")
                continue
            nag = nag_number(anchor.astimezone(LOCAL_TZ).date(), today)
            targets, author_fallback = pr_targets(repo, number, pr["user"]["login"], gh_token)
        except Exception as error:  # one broken PR must not block everyone's DMs
            print(f"ERROR reading {repo}#{number}: {error}")
            failures += 1
            continue
        for login in targets:
            queue.setdefault(login, []).append({
                "repo": repo, "url": pr["html_url"], "title": pr["title"],
                "nag": nag, "author_fallback": author_fallback,
            })

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
        sys.exit(f"{failures} PR lookup(s) / Slack DM(s) failed")


if __name__ == "__main__":
    main()
