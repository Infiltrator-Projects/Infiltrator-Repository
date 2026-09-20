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

    component = build("infiltratorfs-libblockdev-fs3", "3.1.1-1ubuntu0.1+infiltratorfs1", "amd64")

    def validate_component(asset_name):
        return subprocess.run(
            [
                str(tool), "validate-deb", str(component), "v0.18.65",
                "^infiltratorfs-libblockdev-fs3$", "amd64",
                asset_name,
                r"^infiltratorfs-libblockdev-fs3_([^_]+)_amd64\.deb$",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode

    assert validate_component(
        "infiltratorfs-libblockdev-fs3_3.1.1-1ubuntu0.1+infiltratorfs1_amd64.deb"
    ) == 0
    assert validate_component(
        "infiltratorfs-libblockdev-fs3_wrong_amd64.deb"
    ) != 0

print("Independent release/package and bundled-asset identity validation passed")
