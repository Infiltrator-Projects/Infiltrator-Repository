#!/usr/bin/env python3
"""Exercise the repository signing path with a disposable CI-only OpenPGP key."""
from __future__ import annotations

import base64
import importlib.util
import os
import pathlib
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "sync-repository.py"


def run(args, *, env=None, input_data=None, capture=False):
    return subprocess.run(
        args,
        env=env,
        input=input_data,
        text=isinstance(input_data, str),
        check=True,
        capture_output=capture,
    )


def main() -> int:
    spec = importlib.util.spec_from_file_location("sync_repository", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    with tempfile.TemporaryDirectory(prefix="infiltrator-signing-test-") as td:
        temp = pathlib.Path(td)
        gen_home = temp / "generator"
        verify_home = temp / "verifier"
        public = temp / "public"
        gen_home.mkdir(mode=0o700)
        verify_home.mkdir(mode=0o700)

        for suite in ("alpha", "stable"):
            directory = public / "dists" / suite
            directory.mkdir(parents=True)
            (directory / "Release").write_text(
                "Origin: Infiltrator\n"
                f"Suite: {suite}\n"
                f"Codename: {suite}\n"
                "Architectures: amd64\n"
                "Components: main\n"
            )

        gen_env = dict(os.environ)
        gen_env["GNUPGHOME"] = str(gen_home)
        params = """Key-Type: RSA
Key-Length: 3072
Key-Usage: sign
Name-Real: Infiltrator CI Signing Self-Test
Name-Email: ci-signing-test@example.invalid
Expire-Date: 1d
%no-protection
%commit
"""
        run(["gpg", "--batch", "--generate-key"], env=gen_env, input_data=params)
        listed = run(
            ["gpg", "--batch", "--with-colons", "--list-secret-keys"],
            env=gen_env,
            capture=True,
        ).stdout.splitlines()
        fingerprint = next(line.split(":")[9] for line in listed if line.startswith("fpr:"))

        secret = subprocess.check_output(
            ["gpg", "--batch", "--export-secret-keys", fingerprint],
            env=gen_env,
        )

        old_public = module.PUBLIC
        module.PUBLIC = public
        try:
            os.environ["APT_SIGNING_KEY_B64"] = base64.b64encode(secret).decode("ascii")
            os.environ["APT_SIGNING_KEY_FINGERPRINT"] = fingerprint
            os.environ.pop("APT_SIGNING_PASSPHRASE", None)
            assert module.sign_repository(["alpha", "stable"]) is True
        finally:
            module.PUBLIC = old_public
            os.environ.pop("APT_SIGNING_KEY_B64", None)
            os.environ.pop("APT_SIGNING_KEY_FINGERPRINT", None)

        assert (public / "repository-key.gpg").stat().st_size > 0
        verify_env = dict(os.environ)
        verify_env["GNUPGHOME"] = str(verify_home)
        run(["gpg", "--batch", "--import", str(public / "repository-key.gpg")], env=verify_env)

        for suite in ("alpha", "stable"):
            directory = public / "dists" / suite
            run(["gpg", "--batch", "--verify", str(directory / "InRelease")], env=verify_env)
            run(
                [
                    "gpg",
                    "--batch",
                    "--verify",
                    str(directory / "Release.gpg"),
                    str(directory / "Release"),
                ],
                env=verify_env,
            )

    print("Repository signing self-test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
