#!/usr/bin/env python3
"""Materialise private package mirrors from verified checked-in payloads."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIRROR = ROOT / "mirrored-packages"

PACKAGE = "intune-zabbix-bridge"
SEED_VERSION = "0.7.5"
SEED_SHA256 = "dfde41c90846e6c30daf605bc9def9ffba104d77dfe6707778db22e26ca8611b"
SEED_OUTPUT = MIRROR / f"{PACKAGE}_{SEED_VERSION}_all.deb"
SEED_PART_GLOB = f"{PACKAGE}_{SEED_VERSION}_all.deb.part-*"
PUBLIC_EXPORT_MANIFEST = "https://infiltrator-projects.github.io/Intune-Zabbix-Bridge/manifest.json"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ENCODED_NAME_RE = re.compile(
    rf"^{re.escape(PACKAGE)}_(?P<version>[0-9][0-9A-Za-z.+:~_-]*)_all\.deb\.b64\.part-00$"
)


def deb_field(package: Path, field: str) -> str:
    return subprocess.check_output(
        ["dpkg-deb", "--field", str(package), field], text=True
    ).strip()


def verify_deb(path: Path, expected_version: str) -> None:
    package = deb_field(path, "Package")
    version = deb_field(path, "Version")
    architecture = deb_field(path, "Architecture")
    if package != PACKAGE or version != expected_version or architecture != "all":
        raise SystemExit(
            "Refusing Intune mirror: "
            f"got {package} {version} {architecture}, expected {PACKAGE} {expected_version} all"
        )


def materialise_seed() -> None:
    parts = sorted(MIRROR.glob(SEED_PART_GLOB))
    if not parts:
        raise SystemExit(f"No private mirror parts found for {SEED_OUTPUT.name}")

    payload = b"".join(part.read_bytes() for part in parts)
    digest = hashlib.sha256(payload).hexdigest()
    if digest != SEED_SHA256:
        raise SystemExit(
            f"Refusing to materialise {SEED_OUTPUT.name}: SHA-256 {digest} != {SEED_SHA256}"
        )

    SEED_OUTPUT.write_bytes(payload)
    verify_deb(SEED_OUTPUT, SEED_VERSION)
    print(f"Materialised {SEED_OUTPUT.name} ({digest}) from {len(parts)} verified parts")


def materialise_encoded_mirrors() -> None:
    """Decode version-dynamic DEBs from text-safe checked-in base64 parts.

    Each mirror requires:
      intune-zabbix-bridge_VERSION_all.deb.b64.part-00 ...
      intune-zabbix-bridge_VERSION_all.deb.sha256

    The SHA file is authoritative and the decoded DEB metadata is checked before
    the file is made visible to repository generation.
    """
    for first_part in sorted(MIRROR.glob(f"{PACKAGE}_*_all.deb.b64.part-00")):
        match = ENCODED_NAME_RE.match(first_part.name)
        if match is None:
            raise SystemExit(f"Refusing malformed encoded mirror name: {first_part.name}")

        version = match.group("version")
        base = f"{PACKAGE}_{version}_all.deb"
        parts = sorted(MIRROR.glob(f"{base}.b64.part-*"))
        if not parts:
            raise SystemExit(f"No encoded mirror parts found for {base}")

        sha_path = MIRROR / f"{base}.sha256"
        if not sha_path.is_file():
            raise SystemExit(f"Missing SHA-256 file for encoded mirror {base}")
        expected_sha256 = sha_path.read_text(encoding="ascii").strip().lower()
        if not SHA256_RE.fullmatch(expected_sha256):
            raise SystemExit(f"Invalid SHA-256 file for encoded mirror {base}")

        encoded = "".join(part.read_text(encoding="ascii").strip() for part in parts)
        try:
            payload = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise SystemExit(f"Invalid base64 for encoded mirror {base}: {exc}") from exc

        actual_sha256 = hashlib.sha256(payload).hexdigest()
        if actual_sha256 != expected_sha256:
            raise SystemExit(
                f"Refusing encoded mirror {base}: SHA-256 {actual_sha256} != {expected_sha256}"
            )

        target = MIRROR / base
        temporary = MIRROR / f".{base}.decoded"
        temporary.write_bytes(payload)
        try:
            verify_deb(temporary, version)
            if target.exists():
                existing_sha256 = hashlib.sha256(target.read_bytes()).hexdigest()
                if existing_sha256 != expected_sha256:
                    # A historical placeholder may exist in git; only replace it
                    # after the encoded payload has passed every integrity check.
                    target.write_bytes(payload)
                else:
                    temporary.unlink(missing_ok=True)
            else:
                temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)

        print(
            f"Materialised encoded {base} ({expected_sha256}) "
            f"from {len(parts)} text-safe parts"
        )


def public_request(url: str) -> urllib.request.Request:
    return urllib.request.Request(
        url,
        headers={
            "Accept": "application/json,application/octet-stream;q=0.9,*/*;q=0.8",
            "Cache-Control": "no-cache",
            "User-Agent": "Infiltrator-Repository-Intune-Mirror",
        },
    )


def fetch_public_export() -> None:
    try:
        with urllib.request.urlopen(public_request(PUBLIC_EXPORT_MANIFEST), timeout=30) as response:
            manifest = json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            print("Intune public APT export is not available yet; retaining verified local history")
            return
        raise
    except urllib.error.URLError as exc:
        print(f"Intune public APT export is temporarily unavailable ({exc}); retaining verified local history")
        return

    if not isinstance(manifest, dict):
        raise SystemExit("Refusing Intune public export: manifest is not an object")

    package = str(manifest.get("package") or "")
    version = str(manifest.get("version") or "")
    filename = str(manifest.get("filename") or "")
    expected_sha256 = str(manifest.get("sha256") or "").lower()

    if package != PACKAGE:
        raise SystemExit(f"Refusing Intune public export: package is {package!r}")
    if not version or any(ch in version for ch in "/\\\x00\r\n"):
        raise SystemExit(f"Refusing Intune public export: invalid version {version!r}")

    expected_filename = f"{PACKAGE}_{version}_all.deb"
    if filename != expected_filename:
        raise SystemExit(
            f"Refusing Intune public export: filename {filename!r} != {expected_filename!r}"
        )
    if not SHA256_RE.fullmatch(expected_sha256):
        raise SystemExit("Refusing Intune public export: invalid SHA-256")

    parsed_manifest = urllib.parse.urlparse(PUBLIC_EXPORT_MANIFEST)
    if parsed_manifest.scheme != "https" or parsed_manifest.hostname != "infiltrator-projects.github.io":
        raise SystemExit("Refusing Intune public export: untrusted manifest origin")

    download_url = urllib.parse.urljoin(PUBLIC_EXPORT_MANIFEST, filename)
    parsed_download = urllib.parse.urlparse(download_url)
    if parsed_download.scheme != "https" or parsed_download.hostname != parsed_manifest.hostname:
        raise SystemExit("Refusing Intune public export: untrusted package origin")

    MIRROR.mkdir(parents=True, exist_ok=True)
    target = MIRROR / filename
    temporary = MIRROR / f".{filename}.download"
    digest = hashlib.sha256()

    try:
        with urllib.request.urlopen(public_request(download_url), timeout=90) as response, temporary.open("wb") as output:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
                output.write(chunk)

        actual_sha256 = digest.hexdigest()
        if actual_sha256 != expected_sha256:
            raise SystemExit(
                f"Refusing Intune public export: SHA-256 {actual_sha256} != {expected_sha256}"
            )

        verify_deb(temporary, version)

        if target.exists():
            existing_sha256 = hashlib.sha256(target.read_bytes()).hexdigest()
            if existing_sha256 != expected_sha256:
                raise SystemExit(
                    f"Refusing to replace immutable {filename}: existing SHA-256 {existing_sha256} "
                    f"!= public export {expected_sha256}"
                )
            temporary.unlink(missing_ok=True)
            print(f"Verified existing public Intune mirror {filename} ({expected_sha256})")
        else:
            temporary.replace(target)
            print(f"Fetched verified public Intune mirror {filename} ({expected_sha256})")
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    MIRROR.mkdir(parents=True, exist_ok=True)
    materialise_seed()
    materialise_encoded_mirrors()
    fetch_public_export()


if __name__ == "__main__":
    main()
