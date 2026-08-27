#!/usr/bin/env python3
"""Build the Infiltrator alpha APT repository from current GitHub Releases."""
from __future__ import annotations
import gzip
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
POOL = PUBLIC / "pool" / "main"
DIST = PUBLIC / "dists" / "stable" / "main" / "binary-amd64"
CATALOGUE = PUBLIC / "catalogue"
OWNER = "The-First-Infiltrator"


def request_json(url: str) -> dict:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "Infiltrator-Repository-alpha"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as response:
        return json.load(response)


def download(url: str, destination: Path) -> None:
    headers = {"User-Agent": "Infiltrator-Repository-alpha"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=180) as response, destination.open("wb") as output:
        shutil.copyfileobj(response, output)


def deb_field(package: Path, field: str) -> str:
    result = subprocess.run(["dpkg-deb", "-f", str(package), field], check=True, text=True, capture_output=True)
    return result.stdout.strip()


def main() -> int:
    source = json.loads((ROOT / "catalogue" / "apps-source.json").read_text())
    if PUBLIC.exists():
        shutil.rmtree(PUBLIC)
    POOL.mkdir(parents=True)
    DIST.mkdir(parents=True)
    CATALOGUE.mkdir(parents=True)
    shutil.copy2(ROOT / "site" / "index.html", PUBLIC / "index.html")
    (PUBLIC / ".nojekyll").write_text("")

    generated = []
    for app in source:
        release = request_json(f"https://api.github.com/repos/{OWNER}/{app['repo']}/releases/latest")
        rx = re.compile(app["deb_regex"])
        matching = [asset for asset in release.get("assets", []) if rx.fullmatch(asset.get("name", ""))]
        if len(matching) != 1:
            raise RuntimeError(f"{app['repo']}: expected exactly one DEB matching {app['deb_regex']}, found {len(matching)}")
        asset = matching[0]
        target = POOL / asset["name"]
        print(f"Downloading {app['name']} {release['tag_name']} -> {target.name}")
        download(asset["browser_download_url"], target)

        item = dict(app)
        item.update({
            "package": deb_field(target, "Package"),
            "version": deb_field(target, "Version"),
            "architecture": deb_field(target, "Architecture"),
            "depends": deb_field(target, "Depends") if subprocess.run(["dpkg-deb", "-f", str(target), "Depends"], capture_output=True).returncode == 0 else "",
            "release_tag": release["tag_name"],
            "release_url": release["html_url"],
            "source_url": f"https://github.com/{OWNER}/{app['repo']}",
            "asset": asset["name"]
        })
        generated.append(item)

    (CATALOGUE / "apps.json").write_text(json.dumps(generated, indent=2) + "\n")

    packages = subprocess.run(
        ["dpkg-scanpackages", "--multiversion", "pool/main", "/dev/null"],
        cwd=PUBLIC, check=True, text=True, capture_output=True).stdout
    (DIST / "Packages").write_text(packages)
    with (DIST / "Packages.gz").open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0) as gz:
            gz.write(packages.encode())

    subprocess.run([
        "apt-ftparchive",
        "-o", "APT::FTPArchive::Release::Origin=Infiltrator",
        "-o", "APT::FTPArchive::Release::Label=Infiltrator Alpha",
        "-o", "APT::FTPArchive::Release::Suite=stable",
        "-o", "APT::FTPArchive::Release::Codename=stable",
        "-o", "APT::FTPArchive::Release::Architectures=amd64",
        "-o", "APT::FTPArchive::Release::Components=main",
        "-o", "APT::FTPArchive::Release::Description=Infiltrator Software Repository alpha",
        "release", "dists/stable"
    ], cwd=PUBLIC, check=True, stdout=(PUBLIC / "dists" / "stable" / "Release").open("w"))

    print(f"Built {len(generated)} packages in {PUBLIC}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
