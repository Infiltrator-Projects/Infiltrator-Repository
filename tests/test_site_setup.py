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
assert "/infiltrator-calendar.pref" in block
assert "return clean+preference+" in block
assert 'var cmd="sudo apt install "+a.package+"="+a.version;' in site
assert "sudo rm -f /var/cache/mintinstall/pkginfo.json" in block
assert "mintinstall/pkginfo.json" in block
assert 'var base="https://infiltrator-projects.github.io/Infiltrator-Repository";' in site
assert "assets/infiltrator-web-v1.css?v=common-1.19.42" in site
assert "assets/site.css?v=family-20261016-refined" in site
assert "assets/site-overrides.css?v=family-20261016-refined" in site
assert "if(!repoReady||!repoInfo)return" in block
assert 'id="copyRepo" disabled' in site
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
assert '"raster-card"' not in site and '"raster-dialog"' not in site, "catalogue typography must not bypass the canonical MB Corpo website family"
assert '"Cascadia Mono"' not in site and '"DejaVu Sans Mono"' not in site and '"Liberation Mono"' not in site, "catalogue cards must inherit the canonical MB Corpo family instead of a private monospace stack"
assert 'font:400 30px/1.15 var(--display)' in site, "application titles must use the canonical MB Corpo A display role"
assert ':appIcon(a);}' not in site, "appIcon must not recursively call itself"
assert "calculator:" in site

# Catalogue cards are sorted by name, independent of input/release ordering.
assert 'var visible=apps.filter(matches).sort(compareApps);' in site
assert 'function compareApps(a,b){return compareLabels(a.name,b.name)' in site
assert 'var categoryOrder=["System","Productivity","Filesystems","Development","Automotive","Infrastructure","Games"];' in site
assert '.sort(compareCategories)' in site
assert 'if(ai<0)ai=categoryOrder.length;' in site and 'if(bi<0)bi=categoryOrder.length;' in site

print("Software Centre setup, accessibility and family-source regression tests passed")

preference = Path("site/infiltrator-calendar.pref").read_text()
assert "Package: calendar\n" in preference
assert "Pin: release o=Infiltrator\n" in preference
assert "Pin-Priority: 1001\n" in preference
