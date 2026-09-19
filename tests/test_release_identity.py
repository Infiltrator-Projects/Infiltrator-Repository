#!/usr/bin/env python3
"""Exercise the same DEB identity validator used by remote release ingestion."""
from pathlib import Path
import subprocess
import sys
import tempfile

tool = Path(sys.argv[1]).resolve()
with tempfile.TemporaryDirectory() as td:
    root = Path(td)

    def build(name, version, arch):
        stage = root / f"{name}-{version}-{arch}"
        (stage / "DEBIAN").mkdir(parents=True)
        (stage / "DEBIAN" / "control").write_text(
            f"Package: {name}\nVersion: {version}\nArchitecture: {arch}\n"
            "Maintainer: CI <ci@example.invalid>\n"
            "Description: identity fixture\n",
            encoding="utf-8",
        )
        out = root / f"{name}_{version}_{arch}.deb"
        subprocess.run(
            ["dpkg-deb", "--build", "--root-owner-group", str(stage), str(out)],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        return out

    good = build("expected-app", "1.0", "amd64")
    wrong_name = build("wrong-app", "1.0", "amd64")
    wrong_version = build("expected-app", "9.9", "amd64")
    wrong_arch = build("expected-app", "1.0", "all")

    def validate(path):
        return subprocess.run(
            [str(tool), "validate-deb", str(path), "v1.0", "^expected-app$", "amd64"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode

    assert validate(good) == 0
    assert validate(wrong_name) != 0
    assert validate(wrong_version) != 0
    assert validate(wrong_arch) != 0

print("Independent release/package identity validation passed")
