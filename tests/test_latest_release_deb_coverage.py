#!/usr/bin/env python3
"""Fail closed when a release DEB is neither a catalogue app nor an APT-only supplemental package."""

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "catalogue" / "apps-source.json"
ORG = "Infiltrator-Projects"
API = "https://api.github.com"


def api_json(path):
    request = urllib.request.Request(
        API + path,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "Infiltrator-Repository-coverage-test",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"GitHub API {path} failed with HTTP {exc.code}") from exc


def latest_release(owner, repo):
    releases = api_json(f"/repos/{owner}/{repo}/releases?per_page=10")
    return next(
        (release for release in releases
         if not release.get("draft") and not release.get("prerelease")),
        None,
    )


def deb_assets(release):
    if not release:
        return []
    return [
        asset.get("name", "")
        for asset in release.get("assets", [])
        if str(asset.get("name", "")).lower().endswith(".deb")
    ]


def main():
    entries = json.loads(SOURCE.read_text())
    rules = {}
    errors = []

    for entry in entries:
        regex = entry.get("deb_regex")
        if not regex:
            continue
        owner = entry.get("owner", ORG)
        repo = entry["repo"]
        try:
            compiled = re.compile(regex)
        except re.error as exc:
            errors.append(f"{owner}/{repo} ({entry['id']}): invalid deb_regex: {exc}")
            continue
        rules.setdefault((owner, repo), []).append((entry["id"], compiled))

        for index, supplemental in enumerate(entry.get("supplemental_packages", []), start=1):
            supplemental_regex = supplemental.get("deb_regex")
            if not supplemental_regex:
                errors.append(
                    f"{owner}/{repo} ({entry['id']} supplemental #{index}): missing deb_regex"
                )
                continue
            try:
                supplemental_compiled = re.compile(supplemental_regex)
            except re.error as exc:
                errors.append(
                    f"{owner}/{repo} ({entry['id']} supplemental #{index}): "
                    f"invalid deb_regex: {exc}"
                )
                continue
            rules.setdefault((owner, repo), []).append(
                (f"{entry['id']}:supplemental:{index}", supplemental_compiled)
            )

    repos = api_json(f"/orgs/{ORG}/repos?per_page=100&type=all")
    if len(repos) >= 100:
        errors.append("organisation repository inventory reached the 100-repository page limit")

    checked = set()
    for repository in repos:
        if repository.get("archived"):
            continue
        owner = repository["owner"]["login"]
        repo = repository["name"]
        release = latest_release(owner, repo)
        assets = deb_assets(release)
        if not assets:
            continue
        key = (owner, repo)
        checked.add(key)
        repo_rules = rules.get(key, [])
        if not repo_rules:
            errors.append(
                f"{owner}/{repo} publishes DEB assets but has no catalogue rule: "
                + ", ".join(assets)
            )
            continue
        for asset in assets:
            matches = [app_id for app_id, regex in repo_rules if regex.fullmatch(asset)]
            if len(matches) != 1:
                errors.append(
                    f"{owner}/{repo} latest DEB {asset!r} matches {len(matches)} catalogue rules"
                    + (f": {', '.join(matches)}" if matches else "")
                )

    # Configured external release-backed repositories are checked too. Local
    # mirrors are deliberately excluded because they have no GitHub release DEB.
    for key, repo_rules in rules.items():
        if key in checked or key[0] == ORG:
            continue
        owner, repo = key
        release = latest_release(owner, repo)
        assets = deb_assets(release)
        for asset in assets:
            matches = [app_id for app_id, regex in repo_rules if regex.fullmatch(asset)]
            if len(matches) != 1:
                errors.append(
                    f"{owner}/{repo} latest DEB {asset!r} matches {len(matches)} catalogue rules"
                    + (f": {', '.join(matches)}" if matches else "")
                )

    if errors:
        print("DEB catalogue coverage failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print("Latest-release DEB catalogue coverage is complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
