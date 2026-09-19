#!/usr/bin/env python3
"""Exercise five-version retention through the compiled C++ publisher."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "build" / "repository-tool").resolve()
assert BINARY.is_file(), BINARY

with tempfile.TemporaryDirectory(prefix="infiltrator-retention-") as td:
    root = Path(td)
    (root / "site").mkdir()
    (root / "site" / "index.html").write_text("<!doctype html><title>fixture</title>\n")
    (root / "catalogue").mkdir()
    mirrors = root / "mirrors"
    mirrors.mkdir()

    for version in ["1.1", "1.2", "1.3", "1.4", "1.5", "1.9", "1.10"]:
        tree = root / f"build-{version}"
        (tree / "DEBIAN").mkdir(parents=True)
        (tree / "DEBIAN" / "control").write_text(
            "Package: retention-test\n"
            f"Version: {version}\n"
            "Architecture: amd64\n"
            "Maintainer: Test <test@example.invalid>\n"
            "Description: retention fixture\n"
        )
        subprocess.run(
            ["dpkg-deb", "--build", "--root-owner-group", str(tree),
             str(mirrors / f"retention-test_{version}_amd64.deb")],
            check=True,
            stdout=subprocess.DEVNULL,
        )

    (root / "catalogue" / "apps-source.json").write_text(json.dumps([{
        "id": "retention-test",
        "name": "Retention Test",
        "repo": "retention-test",
        "category": "Test",
        "description": "C++ retention fixture.",
        "local_deb_glob": "mirrors/*.deb",
        "icon": "test",
    }]))

    env = dict(os.environ)
    env["REPOSITORY_ROOT"] = str(root)
    for name in ("APT_SIGNING_KEY_B64", "APT_SIGNING_KEY_FINGERPRINT", "APT_SIGNING_PASSPHRASE"):
        env.pop(name, None)
    subprocess.run([str(BINARY), "publish"], cwd=root, env=env, check=True)

    apps = json.loads((root / "public" / "catalogue" / "apps.json").read_text())
    app = apps[0]
    expected = ["1.10", "1.9", "1.5", "1.4", "1.3"]
    assert app["version"] == "1.10", app
    assert [item["version"] for item in app["history"]] == expected, app["history"]

    pool = root / "public" / "pool" / "main"
    pool_versions = sorted(
        subprocess.check_output(["dpkg-deb", "-f", str(path), "Version"], text=True).strip()
        for path in pool.glob("retention-test_*.deb")
    )
    assert len(pool_versions) == 5, pool_versions
    assert set(pool_versions) == set(expected), pool_versions
    assert len(list(mirrors.glob("*.deb"))) == 7, "source history must remain intact"

    packages = (root / "public" / "dists" / "beta" / "main" / "binary-amd64" / "Packages").read_text()
    assert packages.count("Package: retention-test\n") == 5, packages

    beta_release = (root / "public" / "dists" / "beta" / "Release").read_text()
    alpha_release = (root / "public" / "dists" / "alpha" / "Release").read_text()
    assert "Label: Infiltrator Beta\n" in beta_release, beta_release
    assert "Label: Infiltrator Alpha\n" in alpha_release, alpha_release
    assert not (root / "public" / "dists" / "stable").exists(), "stable is reserved, not an alias"

print("PASS: compiled C++ publisher retains five versions and publishes beta with alpha compatibility and reserves stable")
