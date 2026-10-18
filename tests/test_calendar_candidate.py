#!/usr/bin/env python3
"""Exercise APT's real resolver against the Mint calendar name collision."""
import hashlib
from pathlib import Path
import pwd
import shutil
import subprocess
import tempfile

SOURCE = Path(__file__).resolve().parents[1]
APT_GET = "/usr/bin/apt-get"
APT_CACHE = "/usr/bin/apt-cache"


def archive(root, name, origin, version):
    base = root / name
    binary = base / "dists/beta/main/binary-amd64"
    binary.mkdir(parents=True)
    packages = (
        "Package: calendar\nArchitecture: amd64\n"
        f"Version: {version}\nMaintainer: Fixture <test@example.invalid>\n"
        f"Filename: pool/calendar_{version}_amd64.deb\nSize: 1\n"
        "Description: resolver fixture\n\n"
    ).encode()
    (binary / "Packages").write_bytes(packages)
    digest = hashlib.sha256(packages).hexdigest()
    (base / "dists/beta/Release").write_text(
        f"Origin: {origin}\nLabel: {origin}\nSuite: beta\nCodename: beta\n"
        "Architectures: amd64\nComponents: main\nSHA256:\n"
        f" {digest} {len(packages)} main/binary-amd64/Packages\n"
    )
    return f"deb [trusted=yes arch=amd64] {base.as_uri()} beta main\n"


with tempfile.TemporaryDirectory(prefix="calendar-candidate-") as temporary:
    root = Path(temporary)
    apt = root / "apt"
    for directory in (
        "etc/apt/preferences.d", "var/lib/dpkg", "var/lib/apt/lists/partial",
        "var/cache/apt/archives/partial",
    ):
        (apt / directory).mkdir(parents=True, exist_ok=True)
    status = apt / "var/lib/dpkg/status"
    status.write_text("")
    sources = apt / "etc/apt/sources.list"
    sources.write_text(
        archive(root, "mint", "Ubuntu", "12.1.8")
        + archive(root, "infiltrator", "Infiltrator", "1.0.116")
    )
    options = [
        "-o", f"Dir={apt}",
        "-o", f"Dir::Etc::sourcelist={sources}",
        "-o", "Dir::Etc::sourceparts=-",
        "-o", f"Dir::Etc::preferences={apt / 'etc/apt/preferences'}",
        "-o", f"Dir::Etc::preferencesparts={apt / 'etc/apt/preferences.d'}",
        "-o", f"Dir::State::status={status}",
        "-o", "Dir::Cache::pkgcache=",
        "-o", "Dir::Cache::srcpkgcache=",
        "-o", "Debug::NoLocking=true",
        "-o", f"APT::Sandbox::User={pwd.getpwuid(root.stat().st_uid).pw_name}",
        "-o", "Acquire::Languages=none",
    ]
    subprocess.run([APT_GET, *options, "update"], check=True,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    def candidate():
        output = subprocess.check_output(
            [APT_CACHE, *options, "policy", "calendar"], text=True)
        return next(line.split(":", 1)[1].strip() for line in output.splitlines()
                    if line.strip().startswith("Candidate:"))

    assert candidate() == "12.1.8", "fixture must reproduce the stock Mint collision"
    shutil.copyfile(SOURCE / "site/infiltrator-calendar.pref",
                    apt / "etc/apt/preferences.d/infiltrator-calendar")
    assert candidate() == "1.0.116", "repository preference must select Infiltrator Calendar"
    for installed in ("12.1.8", "1.0.116+nativepgo1"):
        status.write_text(
            "Package: calendar\nStatus: install ok installed\nArchitecture: amd64\n"
            f"Version: {installed}\nMaintainer: Fixture <test@example.invalid>\n"
            "Description: installed calendar\n\n"
        )
        assert candidate() == installed, ("preference must preserve an installed newer/native build", installed, candidate())


print("APT selects Infiltrator Calendar despite Mint's higher-version namesake")
