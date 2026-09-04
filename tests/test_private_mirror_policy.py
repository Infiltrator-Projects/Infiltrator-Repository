#!/usr/bin/env python3
"""Regression guard for version-dynamic private package publication."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

apps = json.loads((ROOT / "catalogue" / "apps-source.json").read_text(encoding="utf-8"))
intune = next(app for app in apps if app.get("id") == "intune-zabbix-bridge")

pattern = intune.get("local_deb_glob")
assert pattern == "mirrored-packages/intune-zabbix-bridge_*_all.deb", intune
assert "local_deb" not in intune, "Intune catalogue must not pin one mirrored release"
assert "release_tag" not in intune, "Intune catalogue must derive the release tag from the DEB version"
assert "published_at" not in intune, "Intune catalogue must not pin release metadata to one version"

sync = (ROOT / "scripts" / "sync-repository.py").read_text(encoding="utf-8")
assert 'app.get("local_deb_glob")' in sync
assert '"dpkg", "--compare-versions"' in sync
assert 'releases = releases[:HISTORY_LIMIT]' in sync

print("Private mirror publication policy is version-dynamic.")
