#!/usr/bin/env python3
"""Produce one verifiable native release snapshot for InfiltratorOS provisioning.

Only the publisher calls the GitHub REST API; installed systems consume the
result from Pages with a detached OpenPGP signature.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import json
import os
from pathlib import Path
import re
import time
import urllib.error
import urllib.request

OWNER = "Infiltrator-Projects"
APPLICATIONS = {"System-Monitor", "Calculator", "Files", "Defragmenter"}
VERSION = re.compile(r"v[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?$")
HEX = re.compile(r"sha256:[a-f0-9]{64}$")


def discover(source: Path) -> dict[str, dict]:
    entries = json.loads(source.read_text(encoding="utf-8"))
    selected = {item["repo"]: item for item in entries
                if item["repo"] in APPLICATIONS or item["repo"].startswith(("Calendar-", "Clock-", "Filesystem-"))}
    if len(selected) != 60 or len([x for x in selected if x.startswith("Calendar-")]) != 31 or len([x for x in selected if x.startswith("Clock-")]) != 23 or len([x for x in selected if x.startswith("Filesystem-")]) != 2:
        raise ValueError("Expected precisely four applications, 31 calendars, 23 clocks and two FAT filesystems")
    return selected


def fetch(repository: str) -> dict:
    url = f"https://api.github.com/repos/{OWNER}/{repository}/releases/latest"
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "Infiltrator-Repository-release-publisher"}
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is required for authenticated publication")
    headers["Authorization"] = "Bearer " + token
    last_error = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as response:
                data = response.read(2 * 1024 * 1024 + 1)
            if len(data) > 2 * 1024 * 1024:
                raise ValueError(repository + ": release metadata exceeds size limit")
            return json.loads(data)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            if isinstance(exc, urllib.error.HTTPError) and exc.code not in (429, 500, 502, 503, 504):
                break
            if attempt < 3:
                time.sleep(min(15, 2 ** attempt))
    raise RuntimeError(f"{repository}: release API unavailable: {last_error}")


def verify(repository: str, item: dict, raw: dict) -> dict:
    if not isinstance(raw, dict) or raw.get("draft") or raw.get("prerelease"):
        raise ValueError(repository + ": latest release is not stable")
    tag = raw.get("tag_name")
    if not isinstance(tag, str) or not VERSION.fullmatch(tag):
        raise ValueError(repository + ": invalid release version")
    version = tag[1:]
    prefix = f"https://github.com/{OWNER}/{repository}/releases/download/{tag}/"
    original = raw.get("assets")
    if not isinstance(original, list) or not original:
        raise ValueError(repository + ": release has no assets")
    assets = []
    for source in original:
        if not isinstance(source, dict):
            raise ValueError(repository + ": malformed asset")
        name, url, digest, size = (source.get(k) for k in ("name", "browser_download_url", "digest", "size"))
        if (not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_.+-]+", name)
                or url != prefix + name or not isinstance(digest, str) or not HEX.fullmatch(digest)
                or not isinstance(size, int) or not 0 < size <= 512 * 1024 * 1024):
            raise ValueError(repository + ": invalid asset identity, checksum or size")
        assets.append({"name": name, "browser_download_url": url, "digest": digest, "size": size})
    names = {asset["name"] for asset in assets}
    if len(names) != len(assets):
        raise ValueError(repository + ": duplicate assets")
    run = (repository.lower() + "-" + version + "-native-installer.run"
           if repository != "Defragmenter" else "Defragmenter-" + version + "-local-folder.run")
    if run not in names:
        raise ValueError(repository + ": missing native RUN installer")
    if repository.startswith(("Calendar-", "Clock-")):
        expected = {run, repository.lower() + "-" + version + "-source.zip",
                    "infiltrator-" + repository.lower() + "_" + version + "_amd64.deb"}
        if names != expected:
            raise ValueError(repository + ": incomplete independent temporal release")
    if repository.startswith("Filesystem-"):
        expected = {run, "infiltrator-" + repository.lower() + "_" + version + "_amd64.deb"}
        if names != expected:
            raise ValueError(repository + ": incomplete independent filesystem release")
    return {"tag_name": tag, "draft": False, "prerelease": False, "assets": assets}


def build(source: Path) -> dict:
    entries = discover(source)
    releases = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fetch, repo): repo for repo in entries}
        for future in as_completed(futures):
            repo = futures[future]
            releases[repo] = verify(repo, entries[repo], future.result())
            print(f"Verified {repo} {releases[repo]['tag_name']}", flush=True)
    return {"schema": 1, "releases": {key: releases[key] for key in sorted(releases)}}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalogue", type=Path, default=Path("catalogue/apps-source.json"))
    parser.add_argument("--output", type=Path, default=Path("public/catalogue/native-installers.json"))
    args = parser.parse_args()
    snapshot = build(args.catalogue)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Sign the exact deterministic bytes written here. Never sign a partial snapshot.
    pending = args.output.with_suffix(".json.tmp")
    pending.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    pending.replace(args.output)
    print("Verified 60 independent native installers; release snapshot complete", flush=True)


if __name__ == "__main__":
    main()
