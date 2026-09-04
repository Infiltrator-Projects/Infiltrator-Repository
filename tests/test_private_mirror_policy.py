#!/usr/bin/env python3
"""Regression guard for token-free public Intune package publication."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

apps = json.loads((ROOT / "catalogue" / "apps-source.json").read_text(encoding="utf-8"))
intune = next(app for app in apps if app.get("id") == "intune-zabbix-bridge")

assert intune.get("repo") == "Intune-Zabbix-Bridge", intune
assert intune.get("deb_regex") == r"^intune-zabbix-bridge_.*_all\.deb$", intune
assert "local_deb" not in intune, "Public Intune releases must not use a pinned local mirror"
assert "local_deb_glob" not in intune, "Public Intune releases must not use the old private mirror"

sync = (ROOT / "scripts" / "sync-repository.py").read_text(encoding="utf-8")
assert "browser_download_url" in sync
assert "expected_sha256(asset)" in sync
assert 'f"https://api.github.com/repos/{OWNER}/{app[\'repo\']}/releases?per_page={HISTORY_LIMIT}"' in sync

print("Intune publication uses the normal public GitHub release path without a cross-repository token.")
