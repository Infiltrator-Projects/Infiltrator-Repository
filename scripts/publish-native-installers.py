#!/usr/bin/env python3
"""Produce one verifiable native release snapshot for InfiltratorOS provisioning.

Only the publisher calls the GitHub REST API; installed systems consume the
validated metadata over HTTPS from GitHub Pages.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import time
import urllib.error
import urllib.request

OWNER = "Infiltrator-Projects"
APPLICATIONS = {"System-Monitor", "Calculator", "Files", "Defragmenter"}
# These five filesystem jobs use the central OS snapshot.
# InfiltratorOS discovers additional filesystem releases independently.
OS_FILESYSTEMS = {"Filesystem-FAT12", "Filesystem-FAT16", "Filesystem-FAT32", "Filesystem-OFS", "Filesystem-exFAT"}
VERSION = re.compile(r"v[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?$")
HEX = re.compile(r"sha256:[a-f0-9]{64}$")


def discover(source: Path) -> dict[str, dict]:
    entries = json.loads(source.read_text(encoding="utf-8"))
    selected = {item["repo"]: item for item in entries
                if item["repo"] in APPLICATIONS or item["repo"] in OS_FILESYSTEMS
                or item["repo"].startswith(("Calendar-", "Clock-"))}
    if len(selected) != 63 or len([x for x in selected if x.startswith("Calendar-")]) != 31 or len([x for x in selected if x.startswith("Clock-")]) != 23 or len([x for x in selected if x.startswith("Filesystem-")]) != 5:
        raise ValueError("Expected precisely four applications, 31 calendars, 23 clocks and five independent filesystems")
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
    # Source-only manual releases use the same artifact names as runtime packages.
    # Apply the catalogue's Debian version floor here as well as in the APT
    # publisher so those historical pairs cannot enter the native OS snapshot.
    minimum = item.get("minimum_version")
    if minimum:
        comparison = subprocess.run(["dpkg", "--compare-versions", version, "ge", minimum])
        if comparison.returncode:
            raise ValueError(f"{repository}: {version} is below the catalogue minimum {minimum}")
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
           if repository not in {"Defragmenter", "Calendar"} else
           ("Defragmenter" if repository == "Defragmenter" else "calendar") + "-" + version + "-local-folder.run")
    if run not in names:
        raise ValueError(repository + ": missing native RUN installer")
    if repository.startswith(("Calendar-", "Clock-")):
        # The native RUN already carries the exact source and pinned Common.
        # GitHub generates the tag source archive; it is not an uploaded asset.
        required = {run, "infiltrator-" + repository.lower() + "_" + version + "_amd64.deb"}
        legacy_zip = repository.lower() + "-" + version + "-source.zip"
        # Keep immutable, previously published three-asset releases usable
        # during migration. Reject all other extras and validate every digest.
        if names not in (required, required | {legacy_zip}):
            raise ValueError(repository + ": incomplete independent temporal release")
    if repository.startswith("Filesystem-"):
        # A current filesystem release provides one native source-building
        # installer and one portable Debian package. Freestanding EFI drivers,
        # Linux kernel adapters and hosted shared objects are implementation
        # outputs; they are not separately required GitHub release artifacts.
        # An optional checksum manifest may accompany the two required assets.
        # Every advertised asset has already passed the identity, SHA-256,
        # download-origin and size checks above.
        required = {
            run,
            "infiltrator-" + repository.lower() + "_" + version + "_amd64.deb",
        }
        if repository in OS_FILESYSTEMS and names not in (
            required,
            required | {"SHA256SUMS"},
            required | {"SHA256SUMS.txt"},
        ):
            raise ValueError(
                repository + ": expected one native RUN, one generic DEB, "
                "and at most one checksum manifest; got " + ", ".join(sorted(names))
            )
        if not required <= names:
            raise ValueError(repository + ": missing native RUN or generic DEB")
    if repository == "Boot" and "infiltrator-boot_" + version + "_amd64.deb" not in names:
        raise ValueError("BOOT missing generic DEB")
    result = {"tag_name": tag, "draft": False, "prerelease": False, "assets": assets}
    if repository == "Calendar" or repository.startswith(("Filesystem-", "Calendar-", "Clock-")):
        # The native-build cache must compare its recorded source revision to
        # the exact published commit, not merely the human-readable version.
        revision = raw.get("target_commitish")
        if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision):
            raise ValueError(repository + ": provider release is not pinned to a commit")
        result["target_commitish"] = revision
    return result


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


def build_full(source: Path) -> dict:
    """Publish a single complete OS catalogue, independently of APT builds.

    Required components fail closed; optional filesystems with no qualified
    release are explicitly recorded as pending, never silently substituted.
    """
    required = set(discover(source)) | {"Boot", "Calendar"}
    # Optional filesystem providers are catalogue-driven. Adding a new
    # independently published provider must not require changing a compiled
    # consumer or a hard-coded total. Keep the legacy required baseline strict.
    selected = [item for item in json.loads(source.read_text(encoding="utf-8"))
                if item["repo"] in required or item["repo"].startswith("Filesystem-")]
    entries = {item["repo"]: item for item in selected}
    if len(required) != 65 or len(entries) != len(selected) or not required <= entries.keys():
        raise ValueError("Missing mandatory OS component or duplicate catalogue repository")
    releases, pending = {}, {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fetch, repo): repo for repo in entries}
        for future in as_completed(futures):
            repo = futures[future]
            try:
                releases[repo] = verify(repo, entries[repo], future.result())
                print(f"Verified {repo} {releases[repo]['tag_name']}", flush=True)
            except (ValueError, RuntimeError) as exc:
                if repo in required:
                    raise
                pending[repo] = str(exc)
                print(f"Pending {repo}: {exc}", flush=True)
    return {"schema": 1, "releases": dict(sorted(releases.items())),
            "pending": dict(sorted(pending.items()))}


def write_snapshot(path: Path, snapshot: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(".json.tmp")
    pending.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    pending.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalogue", type=Path, default=Path("catalogue/apps-source.json"))
    parser.add_argument("--output", type=Path, default=Path("public/catalogue/native-installers-v3.json"))
    parser.add_argument("--legacy-output", type=Path)
    parser.add_argument("--v2-output", type=Path)
    parser.add_argument("--full-output", type=Path)
    args = parser.parse_args()
    if args.full_output:
        write_snapshot(args.full_output, build_full(args.catalogue))
        return
    snapshot = build(args.catalogue)
    write_snapshot(args.output, snapshot)
    # Keep both published legacy views immutable in scope: 61 and 62 jobs.
    # New exFAT support is advertised only in native-installers-v3.json.
    v2 = {"schema": 1, "releases": {key: value for key, value in snapshot["releases"].items()
                                     if key != "Filesystem-exFAT"}}
    if args.v2_output:
        write_snapshot(args.v2_output, v2)
    if args.legacy_output:
        legacy = {"schema": 1, "releases": {key: value for key, value in v2["releases"].items()
                                              if key != "Filesystem-OFS"}}
        write_snapshot(args.legacy_output, legacy)
    print("Verified 63 native installers; 62/61 legacy views preserved", flush=True)


if __name__ == "__main__":
    main()
