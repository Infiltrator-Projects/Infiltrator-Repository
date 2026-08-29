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
assert "https://infiltrator-projects.github.io/Infiltrator-Repository" in site
assert "the-first-infiltrator.github.io/Infiltrator-Repository" not in site.lower()

print("Software Centre setup-command regression test passed")
