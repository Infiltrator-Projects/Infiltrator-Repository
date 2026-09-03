#!/usr/bin/env python3
"""Materialise exact private-package mirrors from Git-safe binary parts."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIRROR = ROOT / "mirrored-packages"

PACKAGE = "intune-zabbix-bridge"
VERSION = "0.7.5"
EXPECTED_SHA256 = "dfde41c90846e6c30daf605bc9def9ffba104d77dfe6707778db22e26ca8611b"
OUTPUT = MIRROR / f"{PACKAGE}_{VERSION}_all.deb"
PART_GLOB = f"{PACKAGE}_{VERSION}_all.deb.part-*"


def main() -> None:
    parts = sorted(MIRROR.glob(PART_GLOB))
    if not parts:
        raise SystemExit(f"No private mirror parts found for {OUTPUT.name}")

    payload = b"".join(part.read_bytes() for part in parts)
    digest = hashlib.sha256(payload).hexdigest()
    if digest != EXPECTED_SHA256:
        raise SystemExit(
            f"Refusing to materialise {OUTPUT.name}: SHA-256 {digest} != {EXPECTED_SHA256}"
        )

    OUTPUT.write_bytes(payload)

    package = subprocess.check_output(
        ["dpkg-deb", "--field", str(OUTPUT), "Package"], text=True
    ).strip()
    version = subprocess.check_output(
        ["dpkg-deb", "--field", str(OUTPUT), "Version"], text=True
    ).strip()

    if package != PACKAGE or version != VERSION:
        raise SystemExit(
            f"Refusing private mirror: got {package} {version}, expected {PACKAGE} {VERSION}"
        )

    print(f"Materialised {OUTPUT.name} ({digest}) from {len(parts)} verified parts")


if __name__ == "__main__":
    main()
