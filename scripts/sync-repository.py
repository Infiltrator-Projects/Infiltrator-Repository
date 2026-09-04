#!/usr/bin/env python3
"""Build the Infiltrator APT repository and software-centre catalogue."""
from __future__ import annotations

import base64
import datetime as dt
import functools
import gzip
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
POOL = PUBLIC / "pool" / "main"
CATALOGUE = PUBLIC / "catalogue"
OWNER = "Infiltrator-Projects"
PRIMARY_SUITE = "alpha"
LEGACY_SUITE = "stable"
HISTORY_LIMIT = 5


def github_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Infiltrator-Repository",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def request_json(url: str):
    request = urllib.request.Request(url, headers=github_headers())
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def download(url: str, destination: Path) -> str:
    request = urllib.request.Request(url, headers=github_headers())
    digest = hashlib.sha256()
    with urllib.request.urlopen(request, timeout=180) as response, destination.open("wb") as output:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            output.write(chunk)
    return digest.hexdigest()


def expected_sha256(asset: dict) -> str:
    value = asset.get("digest") or ""
    if not value.startswith("sha256:") or len(value) != 71:
        raise RuntimeError(f"{asset.get('name', '<asset>')}: GitHub release asset has no usable SHA-256 digest")
    return value.split(":", 1)[1].lower()


def deb_field(package: Path, field: str, optional: bool = False) -> str:
    result = subprocess.run(
        ["dpkg-deb", "-f", str(package), field],
        check=False,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        if optional:
            return ""
        raise RuntimeError(f"{package.name}: unable to read required DEB field {field}")
    return result.stdout.strip()


def verify_package(package: Path, asset: dict) -> str:
    expected = expected_sha256(asset)
    actual = hashlib.sha256(package.read_bytes()).hexdigest()
    if actual != expected:
        package.unlink(missing_ok=True)
        raise RuntimeError(
            f"{asset['name']}: SHA-256 mismatch; expected {expected}, downloaded {actual}"
        )
    return actual


def human_description(value: str) -> str:
    lines = value.splitlines()
    return lines[0].strip() if lines else ""


def compare_debian_versions(left: dict, right: dict) -> int:
    """Sort release dictionaries newest-first using dpkg's version semantics."""
    a = left["version"]
    b = right["version"]
    if a == b:
        return 0
    if subprocess.run(["dpkg", "--compare-versions", a, "gt", b], check=False).returncode == 0:
        return -1
    if subprocess.run(["dpkg", "--compare-versions", a, "lt", b], check=False).returncode == 0:
        return 1
    raise RuntimeError(f"Unable to order Debian versions {a!r} and {b!r}")


def collect_local_app(app: dict) -> dict:
    if app.get("local_deb_glob"):
        sources = [path for path in ROOT.glob(app["local_deb_glob"]) if path.is_file()]
    else:
        source = ROOT / app["local_deb"]
        sources = [source] if source.is_file() else []

    if not sources:
        selector = app.get("local_deb_glob") or app.get("local_deb") or "<unspecified>"
        raise RuntimeError(f"{app['name']}: no mirrored DEB matches {selector}")

    releases = []
    seen_versions: set[str] = set()
    for source in sources:
        version = deb_field(source, "Version")
        if version in seen_versions:
            raise RuntimeError(f"{app['name']}: duplicate mirrored Debian version {version}")
        seen_versions.add(version)

        target = POOL / source.name
        shutil.copy2(source, target)
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        releases.append(
            {
                "package": deb_field(target, "Package"),
                "version": version,
                "architecture": deb_field(target, "Architecture"),
                "depends": deb_field(target, "Depends", optional=True),
                "homepage": deb_field(target, "Homepage", optional=True),
                "section": deb_field(target, "Section", optional=True),
                "maintainer": deb_field(target, "Maintainer", optional=True),
                "package_description": human_description(deb_field(target, "Description", optional=True)),
                "installed_size_kib": deb_field(target, "Installed-Size", optional=True),
                "asset": source.name,
                "download_size": target.stat().st_size,
                "sha256": digest,
                "release_tag": f"v{version}",
                "release_url": f"https://github.com/{OWNER}/{app['repo']}/releases/tag/v{version}",
                "published_at": "",
            }
        )

    releases.sort(key=functools.cmp_to_key(compare_debian_versions))
    releases = releases[:HISTORY_LIMIT]
    latest = releases[0]

    item = dict(app)
    item.update(latest)
    item["source_url"] = f"https://github.com/{OWNER}/{app['repo']}"
    item["history"] = releases
    for key in ("local_deb", "local_deb_glob", "deb_regex", "release_tag", "release_url", "published_at"):
        item.pop(key, None)
    return item


def collect_app(app: dict) -> dict:
    if app.get("local_deb") or app.get("local_deb_glob"):
        return collect_local_app(app)

    releases = request_json(
        f"https://api.github.com/repos/{OWNER}/{app['repo']}/releases?per_page={HISTORY_LIMIT}"
    )
    eligible = [release for release in releases if not release.get("draft") and not release.get("prerelease")]
    if not eligible:
        raise RuntimeError(f"{app['repo']}: no eligible releases found")

    rx = re.compile(app["deb_regex"])
    versions = []
    for release_index, release in enumerate(eligible[:HISTORY_LIMIT]):
        matching = [asset for asset in release.get("assets", []) if rx.fullmatch(asset.get("name", ""))]
        if not matching:
            if release_index == 0:
                raise RuntimeError(
                    f"{app['repo']}: latest release {release['tag_name']} has no DEB matching {app['deb_regex']}"
                )
            continue
        if len(matching) != 1:
            raise RuntimeError(
                f"{app['repo']} {release['tag_name']}: expected one DEB matching "
                f"{app['deb_regex']}, found {len(matching)}"
            )

        asset = matching[0]
        target = POOL / asset["name"]
        print(f"Downloading {app['name']} {release['tag_name']} -> {target.name}")
        streamed_hash = download(asset["browser_download_url"], target)
        verified_hash = verify_package(target, asset)
        if streamed_hash != verified_hash:
            raise RuntimeError(f"{target.name}: internal SHA-256 verification disagreement")

        versions.append(
            {
                "package": deb_field(target, "Package"),
                "version": deb_field(target, "Version"),
                "architecture": deb_field(target, "Architecture"),
                "depends": deb_field(target, "Depends", optional=True),
                "homepage": deb_field(target, "Homepage", optional=True),
                "section": deb_field(target, "Section", optional=True),
                "maintainer": deb_field(target, "Maintainer", optional=True),
                "package_description": human_description(deb_field(target, "Description", optional=True)),
                "installed_size_kib": deb_field(target, "Installed-Size", optional=True),
                "asset": asset["name"],
                "download_size": int(asset.get("size") or target.stat().st_size),
                "sha256": verified_hash,
                "release_tag": release["tag_name"],
                "release_url": release["html_url"],
                "published_at": release.get("published_at") or release.get("created_at") or "",
            }
        )

    if not versions:
        raise RuntimeError(f"{app['repo']}: no usable packages found")

    latest = versions[0]
    item = dict(app)
    item.update(latest)
    item["source_url"] = f"https://github.com/{OWNER}/{app['repo']}"
    item["history"] = versions
    item.pop("deb_regex", None)
    return item


def write_packages_index(suite: str) -> None:
    binary = PUBLIC / "dists" / suite / "main" / "binary-amd64"
    binary.mkdir(parents=True, exist_ok=True)

    packages = subprocess.run(
        ["dpkg-scanpackages", "--multiversion", "pool/main", "/dev/null"],
        cwd=PUBLIC,
        check=True,
        text=True,
        capture_output=True,
    ).stdout
    packages_path = binary / "Packages"
    packages_gz = binary / "Packages.gz"
    packages_path.write_text(packages)

    with packages_gz.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0) as gz:
            gz.write(packages.encode())

    release_path = PUBLIC / "dists" / suite / "Release"
    release_tmp = PUBLIC / f".Release-{suite}.tmp"
    with release_tmp.open("w") as output:
        subprocess.run(
            [
                "apt-ftparchive",
                "-o", "APT::FTPArchive::Release::Origin=Infiltrator",
                "-o", f"APT::FTPArchive::Release::Label=Infiltrator {suite.title()}",
                "-o", f"APT::FTPArchive::Release::Suite={suite}",
                "-o", f"APT::FTPArchive::Release::Codename={suite}",
                "-o", "APT::FTPArchive::Release::Architectures=amd64",
                "-o", "APT::FTPArchive::Release::Components=main",
                "-o", f"APT::FTPArchive::Release::Description=Infiltrator Software Repository {suite}",
                "release",
                f"dists/{suite}",
            ],
            cwd=PUBLIC,
            check=True,
            stdout=output,
        )
    release_tmp.replace(release_path)

    release_text = release_path.read_text()
    marker = f"Codename: {suite}\n"
    if marker in release_text:
        release_text = release_text.replace(marker, marker + "Acquire-By-Hash: yes\n", 1)
    else:
        release_text = "Acquire-By-Hash: yes\n" + release_text
    release_path.write_text(release_text)

    by_hash = binary / "by-hash" / "SHA256"
    by_hash.mkdir(parents=True, exist_ok=True)
    for metadata in (packages_path, packages_gz):
        digest = hashlib.sha256(metadata.read_bytes()).hexdigest()
        shutil.copy2(metadata, by_hash / digest)


def signing_environment() -> tuple[str, str, str] | None:
    key = os.environ.get("APT_SIGNING_KEY_B64", "").strip()
    fingerprint = os.environ.get("APT_SIGNING_KEY_FINGERPRINT", "").strip()
    passphrase = os.environ.get("APT_SIGNING_PASSPHRASE", "")
    if not key and not fingerprint:
        return None
    if not key or not fingerprint:
        raise RuntimeError("APT signing requires both APT_SIGNING_KEY_B64 and APT_SIGNING_KEY_FINGERPRINT")
    return key, fingerprint, passphrase


def sign_repository(suites: list[str]) -> bool:
    signing = signing_environment()
    if signing is None:
        print("Repository signing is not configured; publishing unsigned alpha metadata")
        return False

    encoded_key, fingerprint, passphrase = signing
    key_bytes = base64.b64decode(encoded_key, validate=True)

    with tempfile.TemporaryDirectory(prefix="infiltrator-gnupg-") as gnupg_home:
        env = dict(os.environ)
        env["GNUPGHOME"] = gnupg_home
        import_result = subprocess.run(
            ["gpg", "--batch", "--import"],
            input=key_bytes,
            env=env,
            capture_output=True,
        )
        if import_result.returncode != 0:
            raise RuntimeError("Unable to import APT signing key")

        key_check = subprocess.run(
            ["gpg", "--batch", "--list-secret-keys", fingerprint],
            env=env,
            capture_output=True,
        )
        if key_check.returncode != 0:
            raise RuntimeError("Configured APT signing fingerprint was not found in the imported secret key")

        common = ["gpg", "--batch", "--yes", "--pinentry-mode", "loopback"]
        if passphrase:
            common.extend(["--passphrase", passphrase])

        for suite in suites:
            directory = PUBLIC / "dists" / suite
            release = directory / "Release"
            subprocess.run(
                common + ["--local-user", fingerprint, "--clearsign", "--output", str(directory / "InRelease"), str(release)],
                env=env,
                check=True,
            )
            subprocess.run(
                common + ["--local-user", fingerprint, "--detach-sign", "--output", str(directory / "Release.gpg"), str(release)],
                env=env,
                check=True,
            )

        with (PUBLIC / "repository-key.gpg").open("wb") as public_key:
            subprocess.run(
                ["gpg", "--batch", "--export", fingerprint],
                env=env,
                check=True,
                stdout=public_key,
            )
    return True


def main() -> int:
    source = json.loads((ROOT / "catalogue" / "apps-source.json").read_text())
    if PUBLIC.exists():
        shutil.rmtree(PUBLIC)

    POOL.mkdir(parents=True)
    CATALOGUE.mkdir(parents=True)
    shutil.copy2(ROOT / "site" / "index.html", PUBLIC / "index.html")
    (PUBLIC / ".nojekyll").write_text("")

    generated = [collect_app(app) for app in source]
    (CATALOGUE / "apps.json").write_text(json.dumps(generated, indent=2) + "\n")

    suites = [PRIMARY_SUITE, LEGACY_SUITE]
    for suite in suites:
        write_packages_index(suite)

    signed = sign_repository(suites)
    version_count = sum(len(item["history"]) for item in generated)
    repository = {
        "name": "Infiltrator Software",
        "suite": PRIMARY_SUITE,
        "legacy_suite": LEGACY_SUITE,
        "legacy_suite_deprecated": True,
        "signed": signed,
        "history_limit": HISTORY_LIMIT,
        "app_count": len(generated),
        "package_version_count": version_count,
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
    }
    (CATALOGUE / "repository.json").write_text(json.dumps(repository, indent=2) + "\n")

    print(
        f"Built {len(generated)} applications / {version_count} package versions "
        f"for {', '.join(suites)} in {PUBLIC}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
