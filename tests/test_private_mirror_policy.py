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

tool = (ROOT / "scripts" / "repository-tool.cpp").read_text(encoding="utf-8")
assert '(.local_deb_glob // \\"\\")' in tool
assert 'dpkg --compare-versions' in tool
assert 'if (result.size() > 5) result.resize(5);' in tool
assert 'https://infiltrator-projects.github.io/Infiltrator-Repository/pool/main/' in tool
assert 'GITHUB_TOKEN' in tool
assert '#include <infiltratr/escape.h>' in tool
assert '#include <infiltratr/posix.h>' in tool
assert 'infiltratr_escape_json' in tool
assert 'infiltratr_escape_uri_component' in tool
assert 'infiltratr_atomic_file_write_bytes' in tool
assert 'std::uppercase' not in tool, "URI escaping must come from COMMON, not a private encoder"

print("Private mirror publication policy is version-dynamic and COMMON-backed.")
