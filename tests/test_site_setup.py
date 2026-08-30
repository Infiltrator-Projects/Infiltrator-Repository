#!/usr/bin/env python3
"""Regression test for copy/paste-safe repository setup commands."""
from pathlib import Path

site = Path("site/index.html").read_text(encoding="utf-8")
start = site.index("function setupCommand()")
end = site.index("function updateRepoInfo()", start)
block = site[start:end]

assert "\\\\n" not in block, "setupCommand() contains a double-escaped newline"
assert "infiltrator-alpha.list\\n" in block, "unsigned setup command must contain a real JS newline escape"
assert "infiltrator.list\\n" in block, "signed setup command must contain a real JS newline escape"
assert "sudo apt update" in block
assert 'var base="https://infiltrator-projects.github.io/Infiltrator-Repository";' in site
assert 'var legacyBase="https://the-first-infiltrator.github.io/Infiltrator-Repository";' in site
assert "grep -RIlF" in block, "setup command must search for the pre-move repository URL"
assert "sed -i" in block and "legacyBase" in block, "setup command must migrate legacy repository sources"
assert 'return migrate+"echo \'deb [trusted=yes arch=amd64]' in block, "unsigned alpha setup must run migration before writing the source"

print("Software Centre setup-command regression test passed")
