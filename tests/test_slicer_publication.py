#!/usr/bin/env python3
"""Publish the corrected Slicer release without importing its inherited version."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import test_latest_release_deb_coverage as coverage

ROOT = Path(__file__).resolve().parents[1]
def validate_published(public, expected_version=None):
    apps = json.loads((public / "catalogue/apps.json").read_text())
    slicers = [app for app in apps if app["id"] == "slicer"]
    assert len(slicers) == 1, "The published catalogue must contain Slicer"
    app = slicers[0]
    assert app["package"] == "infiltrator-slicer" and app["architecture"] == "amd64", app
    assert app["version"] != "2.9.6", app
    if expected_version is not None:
        assert app["version"] == expected_version, app
    for suite in ("alpha", "beta"):
        index = (public / f"dists/{suite}/main/binary-amd64/Packages").read_text()
        versions = []
        for stanza in index.split("\n\n"):
            fields = dict(line.split(": ", 1) for line in stanza.splitlines()
                          if ": " in line and not line.startswith(" "))
            if fields.get("Package") == "infiltrator-slicer":
                assert fields["Architecture"] == "amd64", fields
                versions.append(fields["Version"])
        assert app["version"] in versions and "2.9.6" not in versions, versions
        assert set(versions) == {item["version"] for item in app["history"]}, versions
        for version in versions:
            assert subprocess.run(["dpkg", "--compare-versions", version, "le", app["version"]]).returncode == 0
        print(f"PASS: {suite} APT selects Slicer {app['version']}; indexed versions: {', '.join(versions)}")
    print(json.dumps({key: app[key] for key in ("id", "package", "version", "architecture", "asset", "sha256")}))


if sys.argv[1] == "--published":
    validate_published(Path(sys.argv[2]))
    raise SystemExit(0)

TOOL = Path(sys.argv[1]).resolve()
entries = json.loads((ROOT / "catalogue/apps-source.json").read_text())
matches = [entry for entry in entries if entry["id"] == "slicer"]
assert len(matches) == 1, "Slicer must remain an explicit catalogue application"
entry = matches[0]
assert entry["repo"] == "Slicer"
assert entry["expected_package_regex"] == "^infiltrator-slicer$"
assert entry["expected_architecture"] == "amd64"
assert not entry.get("optional_until_release"), "Published Slicer must not silently disappear"
active = re.compile(entry["deb_regex"])
for version in ("0.0.1", "0.0.2", "1.0.0"):
    assert active.fullmatch(f"infiltrator-slicer_{version}_amd64.deb")
old_asset = "infiltrator-slicer_2.9.6_amd64.deb"
assert not active.fullmatch(old_asset), "The inherited version must never outrank 0.0.1"
assert any(re.fullmatch(pattern, old_asset)
           for pattern in entry["retired_release_deb_regexes"])

with tempfile.TemporaryDirectory(prefix="slicer-publication-") as td:
    root = Path(td)
    (root / "site").mkdir()
    (root / "site/index.html").write_text("<!doctype html><title>fixture</title>\n")
    (root / "catalogue").mkdir()
    (root / "catalogue/apps-source.json").write_text(json.dumps([entry]))
    fixture = root / "fixture"
    fixture.mkdir()
    releases = []
    for release_id, version in enumerate(("0.0.1", "2.9.6"), 1):
        stage = fixture / f"stage-{version}"
        (stage / "DEBIAN").mkdir(parents=True)
        (stage / "DEBIAN/control").write_text(
            "Package: infiltrator-slicer\n"
            f"Version: {version}\n"
            "Architecture: amd64\n"
            "Maintainer: Test <test@example.invalid>\n"
            "Description: Slicer publication fixture\n"
        )
        asset = f"infiltrator-slicer_{version}_amd64.deb"
        deb = fixture / asset
        subprocess.run(["dpkg-deb", "--build", "--root-owner-group", str(stage), str(deb)],
                       check=True, stdout=subprocess.DEVNULL)
        releases.append({
            "id": release_id, "tag_name": f"v{version}", "draft": False,
            "prerelease": False, "published_at": (
                "2026-10-16T00:00:00Z" if version == "0.0.1" else "2026-10-15T14:34:35Z"),
            "html_url": f"https://github.com/Infiltrator-Projects/Slicer/releases/tag/v{version}",
            "assets_url": f"https://api.github.com/repos/Infiltrator-Projects/Slicer/releases/{release_id}/assets",
        })
        (fixture / f"assets-{release_id}.json").write_text(json.dumps([{
            "name": asset,
            "browser_download_url": f"https://github.com/Infiltrator-Projects/Slicer/releases/download/v{version}/{asset}",
            "digest": "sha256:" + hashlib.sha256(deb.read_bytes()).hexdigest(),
            "size": deb.stat().st_size,
        }]))
    # Reproduce the real API response: the inherited higher version appears first.
    releases.reverse()
    (fixture / "releases.json").write_text(json.dumps(releases))
    original_api = coverage.api_json
    try:
        coverage.api_json = lambda path: releases
        assert coverage.latest_release("Infiltrator-Projects", "Slicer")["tag_name"] == "v0.0.1"
    finally:
        coverage.api_json = original_api
    bin_dir = root / "bin"
    bin_dir.mkdir()
    curl = bin_dir / "curl"
    curl.write_text('''#!/usr/bin/env python3
import os
from pathlib import Path
import shutil
import sys
from urllib.parse import urlparse
args = sys.argv[1:]
url = next(arg for arg in args if arg.startswith("https://"))
output = Path(args[args.index("-o") + 1])
fixture = Path(os.environ["SLICER_RELEASE_FIXTURE"])
path = urlparse(url).path
if url.startswith("https://infiltrator-projects.github.io/"):
    raise SystemExit(22)  # Exercise the normal GitHub asset fallback.
if path.endswith("/releases"):
    source = fixture / "releases.json"
elif path.endswith("/assets"):
    source = fixture / ("assets-" + path.split("/")[-2] + ".json")
elif path.endswith(".deb"):
    source = fixture / path.split("/")[-1]
else:
    raise SystemExit("Unexpected HTTP request: " + url)
shutil.copyfile(source, output)
''')
    curl.chmod(0o755)
    env = dict(os.environ, REPOSITORY_ROOT=str(root), SLICER_RELEASE_FIXTURE=str(fixture),
               PATH=str(bin_dir) + os.pathsep + os.environ["PATH"])
    for key in ("APT_SIGNING_KEY_B64", "APT_SIGNING_KEY_FINGERPRINT", "APT_SIGNING_PASSPHRASE"):
        env.pop(key, None)
    subprocess.run([str(TOOL), "publish"], cwd=root, env=env, check=True)
    validate_published(root / "public", expected_version="0.0.1")
    apps = json.loads((root / "public/catalogue/apps.json").read_text())
    assert len(apps) == 1 and apps[0]["id"] == "slicer", apps
    assert apps[0]["version"] == "0.0.1", apps
    assert [item["version"] for item in apps[0]["history"]] == ["0.0.1"], apps
    assert not (root / "public/pool/main" / old_asset).exists()
    for suite in ("alpha", "beta"):
        index = (root / f"public/dists/{suite}/main/binary-amd64/Packages").read_text()
        assert "Package: infiltrator-slicer\n" in index, index
        assert "Version: 0.0.1\n" in index and "Version: 2.9.6\n" not in index, index

print("PASS: Slicer 0.0.1 is required in the catalogue and APT; inherited 2.9.6 stays retired")
