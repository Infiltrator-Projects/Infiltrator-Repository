#!/usr/bin/env python3
"""Exercise signing through the compiled C++ publisher."""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "build" / "repository-tool").resolve()
assert BINARY.is_file(), BINARY

def run(args, *, env=None, input_data=None, capture=False, cwd=None):
    return subprocess.run(
        args, env=env, input=input_data, text=True, check=True,
        capture_output=capture, cwd=cwd
    )

with tempfile.TemporaryDirectory(prefix="infiltrator-signing-") as td:
    root = Path(td)
    (root / "site").mkdir()
    (root / "site" / "index.html").write_text("<!doctype html><title>fixture</title>\n")
    (root / "catalogue").mkdir()
    mirrors = root / "mirrors"
    mirrors.mkdir()

    tree = root / "package"
    (tree / "DEBIAN").mkdir(parents=True)
    (tree / "DEBIAN" / "control").write_text(
        "Package: signing-test\n"
        "Version: 1.0\n"
        "Architecture: amd64\n"
        "Maintainer: Test <test@example.invalid>\n"
        "Description: signing fixture\n"
    )
    package = mirrors / "signing-test_1.0_amd64.deb"
    run(["dpkg-deb", "--build", "--root-owner-group", str(tree), str(package)])

    (root / "catalogue" / "apps-source.json").write_text(json.dumps([{
        "id": "signing-test",
        "name": "Signing Test",
        "repo": "signing-test",
        "category": "Test",
        "description": "C++ signing fixture.",
        "local_deb_glob": "mirrors/*.deb",
        "icon": "test",
        "expected_package_regex": "^signing-test$",
        "expected_architecture": "amd64",
    }]))

    gen_home = root / "generator"
    verify_home = root / "verifier"
    gen_home.mkdir(mode=0o700)
    verify_home.mkdir(mode=0o700)
    gen_env = dict(os.environ)
    gen_env["GNUPGHOME"] = str(gen_home)

    params = """Key-Type: RSA
Key-Length: 3072
Key-Usage: sign
Name-Real: Infiltrator C++ Signing Self-Test
Name-Email: ci-signing-test@example.invalid
Expire-Date: 1d
%no-protection
%commit
"""
    run(["gpg", "--batch", "--generate-key"], env=gen_env, input_data=params)
    listed = run(
        ["gpg", "--batch", "--with-colons", "--list-secret-keys"],
        env=gen_env, capture=True
    ).stdout.splitlines()
    fingerprint = next(line.split(":")[9] for line in listed if line.startswith("fpr:"))
    secret = subprocess.check_output(
        ["gpg", "--batch", "--export-secret-keys", fingerprint],
        env=gen_env,
    )

    env = dict(os.environ)
    env["REPOSITORY_ROOT"] = str(root)
    env["APT_SIGNING_KEY_B64"] = base64.b64encode(secret).decode("ascii")
    env["APT_SIGNING_KEY_FINGERPRINT"] = fingerprint
    env.pop("APT_SIGNING_PASSPHRASE", None)
    run([str(BINARY), "publish"], env=env, cwd=root)

    repository = json.loads((root / "public" / "catalogue" / "repository.json").read_text())
    assert repository["signed"] is True, repository
    assert repository["suite"] == "beta", repository
    assert repository["compatibility_suite"] == "alpha", repository
    assert repository["stable_reserved"] is True, repository
    assert repository.get("generated_at"), repository
    public_key = root / "public" / "repository-key.gpg"
    assert public_key.stat().st_size > 0

    verify_env = dict(os.environ)
    verify_env["GNUPGHOME"] = str(verify_home)
    run(["gpg", "--batch", "--import", str(public_key)], env=verify_env)
    for suite in ("beta", "alpha"):
        directory = root / "public" / "dists" / suite
        run(["gpg", "--batch", "--verify", str(directory / "InRelease")], env=verify_env)
        run(["gpg", "--batch", "--verify", str(directory / "Release.gpg"), str(directory / "Release")], env=verify_env)

print("PASS: compiled C++ publisher signs and verifies beta plus alpha compatibility suites")
