#!/usr/bin/env python3
"""Write the core technology versions of a project into the project Google Sheet.

Runs inside a project repo after a push (see templates/core-versions.yml):

1. Read the versions from the project's files (Dockerfile, .nvmrc, lockfiles, ...).
2. Find the project's rows in the sheet: column K contains the repo URL.
   A push to main/master updates the prod rows, a push to stage/develop the
   rows whose name (column C) contains "stage".
3. Write the versions that changed into the version columns (AH, AI, ...).

Run locally to see which versions are found (no Google token needed):
  python3 scripts/core_versions.py path/to/project

Environment (set by GitHub Actions / the reusable workflow):
  GITHUB_REPOSITORY    the project repo, e.g. dreipol/sib-website
  GITHUB_REF_NAME      the pushed branch: main, master, stage or develop
  GOOGLE_ACCESS_TOKEN  access token of the Google service account
  DRY_RUN              "false" writes to the sheet, anything else only prints
"""

import json
import os
import re
import sys
import tomllib
import urllib.parse
import urllib.request

SHEET_ID = "1i-WaIgdIGqbGjWAXFVemhwxd2D7pV_t8fQXykXtUIFM"
TAB = "Web / Server"
NAME_COLUMN = "C"
REPO_COLUMN = "K"
VERSION_COLUMNS = {"Python": "AH", "Django": "AI", "Next": "AK", "Node": "AL", "React": "AM", "djangoCMS": "AO"}

PYTHON_PACKAGES = {"django": "Django", "django-cms": "djangoCMS"}
NODE_PACKAGES = {"next": "Next", "react": "React"}
SKIP_FOLDERS = {".git", "node_modules", ".venv", "venv"}


# --- Reading the project files ----------------------------------------------
# Each reader gets the text of one file and returns the versions it contains,
# e.g. {"Python": "3.13", "Node": "22"}.

def read_dockerfile(text):
    """Python and Node from the FROM lines (python:3.13, uv:python3.13-bookworm, node:22-slim)
    or from ENV NODE_VERSION=10.14.1. The last FROM wins, as it is usually the image that runs."""
    versions = {}
    for image in re.findall(r"^FROM\s+(\S+)", text, re.MULTILINE | re.IGNORECASE):
        python = re.search(r"python:?(\d+(\.\d+)*)", image)
        if python:
            versions["Python"] = python.group(1)
        node = re.search(r"node:(\d+(\.\d+)*)", image)
        if node:
            versions["Node"] = node.group(1)
    node_env = re.search(r"NODE_VERSION[= ]v?(\d+(\.\d+)*)", text)
    if node_env and "Node" not in versions:
        versions["Node"] = node_env.group(1)
    return versions


def first_line(text):
    """The first line without a leading "v", e.g. "v22" -> "22"."""
    lines = text.strip().splitlines()
    return lines[0].strip().removeprefix("v") if lines else None


def read_python_version(text):
    return {"Python": first_line(text)}


def read_nvmrc(text):
    return {"Node": first_line(text)}


def read_pipfile_lock(text):
    packages = json.loads(text)["default"]
    versions = {}
    for name, tech in PYTHON_PACKAGES.items():
        if name in packages:
            versions[tech] = packages[name]["version"].removeprefix("==")
    return versions


def read_uv_lock(text):
    versions = {}
    for package in tomllib.loads(text)["package"]:
        if package["name"] in PYTHON_PACKAGES:
            versions[PYTHON_PACKAGES[package["name"]]] = package["version"]
    return versions


def read_package_lock(text):
    """New lockfiles list "node_modules/next" under "packages", old ones (npm 6) "next" under "dependencies"."""
    data = json.loads(text)
    versions = {}
    for name, tech in NODE_PACKAGES.items():
        if f"node_modules/{name}" in data.get("packages", {}):
            versions[tech] = data["packages"][f"node_modules/{name}"]["version"]
        elif name in data.get("dependencies", {}):
            versions[tech] = data["dependencies"][name]["version"]
    return versions


def read_yarn_lock(text):
    """Entries look like this; the first entry of a package wins:

    next@^16.2.0, next@^16.2.4:
      version "16.2.4"
    """
    versions = {}
    current = None
    for line in text.splitlines():
        if line.endswith(":") and not line.startswith(" "):
            current = None
            for name, tech in NODE_PACKAGES.items():
                if line.startswith((f"{name}@", f'"{name}@')):
                    current = tech
        elif current and line.strip().startswith("version "):
            versions.setdefault(current, line.split('"')[1])
            current = None
    return versions


# The files to look at, most reliable first: if two files contain a version
# of the same technology, the earlier one wins.
FILES = [
    ("Dockerfile", read_dockerfile),
    (".python-version", read_python_version),
    (".nvmrc", read_nvmrc),
    ("Pipfile.lock", read_pipfile_lock),
    ("uv.lock", read_uv_lock),
    ("package-lock.json", read_package_lock),
    ("yarn.lock", read_yarn_lock),
]


def read_folder(path):
    """The versions in one folder: {tech: (version, file name)}."""
    versions = {}
    for filename, reader in FILES:
        file_path = os.path.join(path, filename)
        if not os.path.isfile(file_path):
            continue
        try:
            with open(file_path, encoding="utf-8") as file:
                found = reader(file.read())
        except (ValueError, KeyError, tomllib.TOMLDecodeError) as error:
            print(f"WARN could not read {file_path}: {error!r}")
            continue
        for tech, version in found.items():
            if version and tech not in versions:
                versions[tech] = (version, filename)
    return versions


def collect_versions(project_dir):
    """The versions of every folder of the project: {folder: {tech: (version, file name)}}.

    "" is the project root; a monorepo also has e.g. "backend" and "frontend".
    """
    result = {}
    for path, subfolders, _ in os.walk(project_dir):
        subfolders[:] = sorted(folder for folder in subfolders if folder not in SKIP_FOLDERS)
        versions = read_folder(path)
        if versions:
            folder = os.path.relpath(path, project_dir)
            result["" if folder == "." else folder] = versions
    return result


# --- Matching versions to sheet rows ---------------------------------------

def repo_name(cell):
    """The GitHub repo in a cell, e.g. "https://github.com/dreipol/Sib-Website" -> "dreipol/sib-website"."""
    match = re.search(r"github\.com/([\w.-]+)/([\w.-]+)", cell, re.IGNORECASE)
    if not match:
        return None
    owner, repo = match.groups()
    return f"{owner}/{repo.removesuffix('.git')}".lower()


def pick_folders(folders, part):
    """The project folders that belong to a "frontend" or "backend" row.

    Without a part: all of them. Otherwise the folders whose name contains the
    part (e.g. frontend/), or, if there are none, all except the other part's
    (a backend row of a repo with only a frontend/ folder gets the root).
    """
    if part is None:
        return folders
    matching = [folder for folder in folders if part in folder]
    if matching:
        return matching
    other = "backend" if part == "frontend" else "frontend"
    return [folder for folder in folders if other not in folder]


def plan_updates(rows, repo, branch, folders):
    """The cells to change: [{"tech", "cell", "old", "new", "project", "source"}]."""
    stage = branch in ("stage", "develop")
    updates = []
    for row in rows:
        name = row["name"].lower()
        if row["repo"] != repo or ("stage" in name) != stage:
            continue
        part = "frontend" if "frontend" in name else "backend" if "backend" in name else None

        # The versions for this row; if several folders have one, the first folder wins
        versions = {}
        for folder in pick_folders(list(folders), part):
            for tech, (version, filename) in folders[folder].items():
                versions.setdefault(tech, (version, os.path.join(folder, filename)))

        for tech, (new, source) in versions.items():
            old = row["versions"][tech]
            # Skip unchanged values, and keep the sheet's value if it is more precise (3.13.1 vs. 3.13)
            if old == new or old.startswith(new + "."):
                continue
            updates.append({
                "tech": tech, "cell": f"{VERSION_COLUMNS[tech]}{row['number']}", "old": old, "new": new,
                "project": row["name"], "source": source,
            })
    return updates


def describe_update(update):
    """E.g. "Update Django from 5.2.10 to 5.2.17 in AI12 for project 'SIB prod' (from Pipfile.lock)"."""
    if update["old"]:
        change = f"Update {update['tech']} from {update['old']} to {update['new']}"
    else:
        change = f"Set {update['tech']} to {update['new']} (was empty)"
    return f"{change} in {update['cell']} for project '{update['project']}' (from {update['source']})"


# --- Google Sheets ------------------------------------------------------------

def column_index(letters):
    """Column letters to a list index: "A" -> 0, "K" -> 10, "AH" -> 33."""
    index = 0
    for letter in letters:
        index = index * 26 + ord(letter) - ord("A") + 1
    return index - 1


def sheet_url(cells):
    cell_range = urllib.parse.quote(f"'{TAB}'!{cells}", safe="")
    return f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{cell_range}"


def google_request(method, url, token, body=None):
    data = json.dumps(body).encode() if body else None
    request = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def parse_rows(values):
    """The sheet rows with a GitHub URL: [{"number", "name", "repo", "versions"}]."""
    rows = []
    for number, cells in enumerate(values, start=1):
        cells = cells + [""] * 50  # the API leaves out empty cells at the end of a row
        repo = repo_name(cells[column_index(REPO_COLUMN)])
        if repo:
            rows.append({
                "number": number,
                "name": cells[column_index(NAME_COLUMN)],
                "repo": repo,
                "versions": {tech: cells[column_index(column)].strip() for tech, column in VERSION_COLUMNS.items()},
            })
    return rows


def read_rows(token):
    return parse_rows(google_request("GET", sheet_url("A:AO"), token).get("values", []))


def write_cell(token, cell, value):
    # RAW keeps "3.10" as text instead of turning it into the number 3.1
    google_request("PUT", sheet_url(cell) + "?valueInputOption=RAW", token, {"values": [[value]]})


def main():
    project_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    folders = collect_versions(project_dir)
    if not folders:
        print("No versions found")
    for folder, versions in folders.items():
        found = ", ".join(f"{tech} {version} ({filename})" for tech, (version, filename) in versions.items())
        print(f"{folder or '(root)'}: {found}")

    token = os.environ.get("GOOGLE_ACCESS_TOKEN")
    if not token:
        print("No GOOGLE_ACCESS_TOKEN, so the sheet is not read")
        return

    repo = os.environ["GITHUB_REPOSITORY"].lower()
    branch = os.environ["GITHUB_REF_NAME"]
    if branch not in ("main", "master", "stage", "develop"):
        sys.exit(f"Branch {branch} is not main, master, stage or develop")
    dry_run = os.environ.get("DRY_RUN") != "false"

    updates = plan_updates(read_rows(token), repo, branch, folders)
    if not updates:
        print(f"Nothing to update for {repo} on {branch} (no matching row, or the sheet is up to date)")
        return
    for update in updates:
        print(describe_update(update))
        if not dry_run:
            write_cell(token, update["cell"], update["new"])
    if dry_run:
        print(f"Dry run: nothing written. Set CORE_VERSIONS_DRY_RUN to false to write the {len(updates)} changes.")
    else:
        print(f"Updated {len(updates)} cells")


if __name__ == "__main__":
    main()
