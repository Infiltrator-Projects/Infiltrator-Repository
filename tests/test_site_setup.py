#!/usr/bin/env python3
"""Regression tests for safe, state-aware Software Centre setup commands."""
from pathlib import Path

site = Path("site/index.html").read_text(encoding="utf-8")
start = site.index("function setupCommand()")
end = site.index("function updateRepoInfo()", start)
block = site[start:end]

assert "\\\\n" not in block, "setupCommand() contains a double-escaped newline"
assert "infiltrator-beta.list\\n" in block
assert "infiltrator.list\\n" in block
assert "sudo apt update" in block
assert "infiltrator-app-install-data" not in block
assert 'var base="https://infiltrator-projects.github.io/Infiltrator-Repository";' in site
assert 'var legacyBase="https://the-first-infiltrator.github.io/Infiltrator-Repository";' in site
assert "assets/infiltrator-web-v1.css?v=common-1.19.3" in site
assert "assets/site.css?v=family-20260919" in site
assert "assets/site-overrides.css?v=family-20260919" in site
assert "if(!repoReady||!repoInfo)return" in block
assert 'id="copyRepo" disabled' in site
assert "\\#\"+legacyBase+\"#d" in block
assert "\\#\"+base+\"#d" in block
assert "s# alpha main# beta main#g" not in block
assert "s# stable main# beta main#g" not in block
assert 'aria-labelledby="modalName"' in site
assert 'setAttribute("aria-pressed"' in site
assert "activeCategory=cat;buildFilters()" not in site
assert "Repository configuration could not be verified. Setup copying is disabled." in site
assert "function appIcon(a)" in site and "a.icon_url" in site
assert 'function isAutomotive(a){return a.category==="Automotive";}' in site
assert 'return isAutomotive(a)&&a.icon_url?' in site, "automotive packages retain their product artwork"
assert ':iconSvg(a.icon);}' in site, "non-automotive catalogue artwork must use the canonical accent-coloured line glyph"
assert 'software:' in site, "Software needs its own canonical generic glyph"
assert '"raster-card"' in site and '"raster-dialog"' in site, "non-automotive catalogue typography must retain the raster treatment"
assert ':appIcon(a);}' not in site, "appIcon must not recursively call itself"
assert "calculator:" in site

print("Software Centre setup, accessibility and family-source regression tests passed")
