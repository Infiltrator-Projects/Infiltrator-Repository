#!/usr/bin/env python3
"""Mirror the latest private Intune Debian release into Git-safe text parts.

The central public repository owns this pull so the private source repository does
not need a cross-repository write token. The release asset digest and Debian
metadata are verified before any mirror files are changed.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import subprocess
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIRROR = ROOT / "mirrored-packages"
PACKAGE = "intune-zabbix-bridge"
REPOSITORY = "Infiltrator-Projects/Intune-Zabbix-Bridge"
LATEST_RELEASE_API = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
PART_CHARS = 8000


def request(url: str, token: str, accept: str) -> urllib.request.Request:
    return urllib.request.Request(
        url,
        headers={
            "Accept": accept,
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "Infiltrator-Repository-Private-Intune-Sync",
        },
    )


def read_json(url: str, token: str) -> dict:
    with urllib.request.urlopen(
        request(url, token, "application/vnd.github+json"), timeout=60
    ) as response:
        value = json.load(response)
    if not isinstance(value, dict):
        raise SystemExit("Private Intune release API did not return an object")
    return value


def deb_field(path: Path, field: str) -> str:
    return subprocess.check_output(
        ["dpkg-deb", "--field", str(path), field], text=True
    ).strip()


def verify_deb(path: Path, version: str) -> None:
    package = deb_field(path, "Package")
    actual_version = deb_field(path, "Version")
    architecture = deb_field(path, "Architecture")
    if package != PACKAGE or actual_version != version or architecture != "all":
        raise SystemExit(
            f"Refusing private release: got {package} {actual_version} {architecture}; "
            f"expected {PACKAGE} {version} all"
        )


def main() -> int:
    token = os.environ.get("INTUNE_PRIVATE_TOKEN", "").strip()
    if not token:
        raise SystemExit(
            "INTUNE_PRIVATE_TOKEN is unavailable in the central repository; "
            "cannot read the private Intune release"
        )

    try:
        release = read_json(LATEST_RELEASE_API, token)
    except urllib.error.HTTPError as exc:
        raise SystemExit(
            f"Unable to read private Intune release (HTTP {exc.code})"
        ) from exc

    if release.get("draft") or release.get("prerelease"):
        raise SystemExit("Latest private Intune release is not an eligible stable release")

    tag = str(release.get("tag_name") or "")
    if not tag.startswith("v") or len(tag) < 2:
        raise SystemExit(f"Invalid private Intune release tag: {tag!r}")
    version = tag[1:]
    if any(ch in version for ch in "/\\\x00\r\n"):
        raise SystemExit(f"Invalid private Intune release version: {version!r}")

    filename = f"{PACKAGE}_{version}_all.deb"
    assets = [asset for asset in release.get("assets", []) if asset.get("name") == filename]
    if len(assets) != 1:
        raise SystemExit(
            f"Private Intune release {tag} must contain exactly one {filename}; found {len(assets)}"
        )

    asset = assets[0]
    digest_value = str(asset.get("digest") or "")
    if not digest_value.startswith("sha256:"):
        raise SystemExit(f"Private Intune release asset {filename} has no SHA-256 digest")
    expected_sha256 = digest_value.split(":", 1)[1].lower()
    if not SHA256_RE.fullmatch(expected_sha256):
        raise SystemExit(f"Private Intune release asset {filename} has an invalid SHA-256 digest")

    asset_url = str(asset.get("url") or "")
    expected_prefix = f"https://api.github.com/repos/{REPOSITORY}/releases/assets/"
    if not asset_url.startswith(expected_prefix):
        raise SystemExit(f"Refusing unexpected private Intune asset URL: {asset_url!r}")

    with tempfile.TemporaryDirectory(prefix="intune-private-sync-") as tmpdir:
        package_path = Path(tmpdir) / filename
        digest = hashlib.sha256()
        try:
            with urllib.request.urlopen(
                request(asset_url, token, "application/octet-stream"), timeout=120
            ) as response, package_path.open("wb") as output:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    digest.update(chunk)
                    output.write(chunk)
        except urllib.error.HTTPError as exc:
            raise SystemExit(
                f"Unable to download private Intune release asset (HTTP {exc.code})"
            ) from exc

        actual_sha256 = digest.hexdigest()
        if actual_sha256 != expected_sha256:
            raise SystemExit(
                f"Refusing private Intune release {filename}: SHA-256 {actual_sha256} "
                f"!= GitHub digest {expected_sha256}"
            )
        verify_deb(package_path, version)
        payload = package_path.read_bytes()

    encoded = base64.b64encode(payload).decode("ascii")
    parts = [encoded[offset : offset + PART_CHARS] for offset in range(0, len(encoded), PART_CHARS)]
    if not parts:
        raise SystemExit("Private Intune release asset is empty")

    MIRROR.mkdir(parents=True, exist_ok=True)
    prefix = f"{filename}.b64.part-"
    expected_names = {f"{prefix}{index:02d}" for index in range(len(parts))}

    for old in MIRROR.glob(f"{filename}.b64.part-*"):
        if old.name not in expected_names:
            old.unlink()

    for index, part in enumerate(parts):
        path = MIRROR / f"{prefix}{index:02d}"
        text = part + "\n"
        if not path.exists() or path.read_text(encoding="ascii") != text:
            path.write_text(text, encoding="ascii")

    sha_path = MIRROR / f"{filename}.sha256"
    sha_text = expected_sha256 + "\n"
    if not sha_path.exists() or sha_path.read_text(encoding="ascii") != sha_text:
        sha_path.write_text(sha_text, encoding="ascii")

    print(
        f"Prepared verified private Intune mirror {filename} ({expected_sha256}) "
        f"as {len(parts)} text-safe parts"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
