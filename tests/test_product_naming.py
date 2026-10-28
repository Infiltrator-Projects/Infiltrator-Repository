#!/usr/bin/env python3
"""Verify canonical alpha packages without aliases or transition packages."""
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
all_entries = json.loads((ROOT / 'catalogue/apps-source.json').read_text())
entries = [item for item in all_entries if item.get('minimum_version')]

def validate_published(public):
    patterns = []
    for app in all_entries:
        for package in [app, *app.get('supplemental_packages', [])]:
            patterns.append(re.compile(package['expected_package_regex']))
    pool = list((public / 'pool/main').glob('*.deb'))
    assert pool, 'Publication must contain application packages'
    clean_names = {item['id'] for item in entries}
    for deb in pool:
        name = subprocess.check_output(['dpkg-deb', '-f', str(deb), 'Package'], text=True).strip()
        assert sum(bool(pattern.fullmatch(name)) for pattern in patterns) == 1, (deb, name)
        if name in clean_names:
            minimum = next(item['minimum_version'] for item in entries if item['id'] == name)
            version = subprocess.check_output(['dpkg-deb', '-f', str(deb), 'Version'], text=True).strip()
            assert subprocess.run(['dpkg', '--compare-versions', version, 'ge', minimum]).returncode == 0, (deb, version, minimum)
            for field in ('Provides', 'Breaks', 'Replaces', 'Conflicts'):
                value = subprocess.check_output(['dpkg-deb', '-f', str(deb), field], text=True).strip()
                if name == "calendar" and field in ("Breaks", "Replaces"):
                    assert value == "infiltrator-calendar-resources (<< 1.19.65)", (deb, field, value)
                elif name.startswith(("infiltrator-calendar-", "infiltrator-clock-")) and name != "infiltrator-calendar-resources" and field == "Replaces":
                    assert value == "infiltrator-calendar-resources", (deb, field, value)
                else:
                    assert not value, (deb, field, value)
    for suite in ('alpha', 'beta'):
        index = (public / f'dists/{suite}/main/binary-amd64/Packages').read_text()
        names = re.findall(r'^Package: (.+)$', index, re.MULTILINE)
        assert names and all(sum(bool(pattern.fullmatch(name)) for pattern in patterns) == 1 for name in names)
    print(f'Published canonical identities verified for {len(pool)} package versions; no migration aliases')

if sys.argv[1] == '--published':
    validate_published(Path(sys.argv[2]))
    raise SystemExit(0)

TOOL = Path(sys.argv[1]).resolve()
assert entries, 'At least one canonical package is required'
assert len({item['id'] for item in all_entries}) == len(all_entries), 'Duplicate application identifiers'
assert all(item['id'] and item['expected_package_regex'] for item in entries)
assert not any(a["id"] == "infiltrator-calendar-resources" or a["repo"] == "Libraries" for a in all_entries)
assert sum(a["repo"].startswith("Calendar-") for a in entries) == 31
assert sum(a["repo"].startswith("Clock-") for a in entries) == 23
# Two independent FAT packages must have exactly one canonical catalogue
# mapping each. They are .so releases, not qualified kernel/EFI drivers.
for fat in ("12", "16"):
    identifier = f"infiltrator-filesystem-fat{fat}"
    matched = [item for item in all_entries if item["id"] == identifier]
    assert len(matched) == 1, (identifier, len(matched))
    item = matched[0]
    assert item["repo"] == f"Filesystem-FAT{fat}", item
    assert item["category"] == "Filesystems", item
    assert item["expected_package_regex"] == '^' + re.escape(identifier) + '$', item
    expected_asset = f"{identifier}_0.1.1_amd64.deb"
    assert re.fullmatch(item["deb_regex"], expected_asset), (identifier, expected_asset)
    assert item["minimum_version"] == "0.1.1", item

for identifier, name in {'mblink':'MBLink','jaglink':'JAGLink','bmwlink':'BMWLink','audilink':'AUDILink','fordlink':'FORDLink'}.items():
    entry = next(item for item in all_entries if item['id'] == identifier)
    assert entry['name'] == name and entry['repo'] == name, entry
for entry in entries:
    assert entry['expected_package_regex'] == '^' + re.escape(entry['id']) + '$'

with tempfile.TemporaryDirectory(prefix='product-naming-') as temporary:
    root = Path(temporary)
    (root / 'site').mkdir()
    (root / 'site/index.html').write_text('<!doctype html><title>naming fixture</title>\n')
    (root / 'catalogue').mkdir()
    fixtures = []
    for entry in entries:
        item = dict(entry)
        item.pop('deb_regex', None)
        item['local_deb_glob'] = f"fixtures/{item['id']}/*.deb"
        fixture = root / 'fixtures' / item['id']
        fixture.mkdir(parents=True)
        for version in ['9.0.0', '9.0.1']:
            stage = root / 'stage'
            (stage / 'DEBIAN').mkdir(parents=True, exist_ok=True)
            (stage / 'DEBIAN/control').write_text(
                f"Package: {item['id']}\nVersion: {version}\nArchitecture: amd64\n"
                'Maintainer: Test <test@example.invalid>\nDescription: naming fixture\n')
            subprocess.run(['dpkg-deb', '--build', '--root-owner-group', str(stage),
                            str(fixture / f"{item['id']}_{version}_amd64.deb")],
                           check=True, stdout=subprocess.DEVNULL)
        fixtures.append(item)
    (root / 'catalogue/apps-source.json').write_text(json.dumps(fixtures))
    subprocess.run([str(TOOL), 'publish'], cwd=root, check=True, stdout=subprocess.DEVNULL)
    apps = json.loads((root / 'public/catalogue/apps.json').read_text())
    assert len(apps) == len(entries), 'Each canonical application has one catalogue card'
    pool = list((root / 'public/pool/main').glob('*.deb'))
    package_names = [
        subprocess.check_output(['dpkg-deb', '-f', str(deb), 'Package'], text=True).strip()
        for deb in pool
    ]
    for entry in entries:
        assert package_names.count(entry['id']) == 2, (
            entry['id'], package_names.count(entry['id'])
        )
    supplemental_patterns = [
        re.compile(package['expected_package_regex'])
        for entry in entries
        for package in entry.get('supplemental_packages', [])
    ]
    supplemental_total = 0
    for pattern in supplemental_patterns:
        count = sum(bool(pattern.fullmatch(name)) for name in package_names)
        assert 1 <= count <= 5, (
            f'Each supplemental package must publish one to five retained versions; '
            f'{pattern.pattern} published {count}'
        )
        supplemental_total += count
    assert len(pool) == (2 * len(entries)) + supplemental_total, (
        'Publication must contain exactly two fixture versions per application plus '
        'the retained supplemental-package history'
    )
    for entry in entries:
        app = next(app for app in apps if app['id'] == entry['id'])
        assert app['package'] == entry['id'] and app['version'] == '9.0.1', app
        assert all(item['package'] == entry['id'] for item in app['history'])
    assert all(subprocess.check_output(['dpkg-deb', '-f', str(deb), 'Architecture'],
                                      text=True).strip() == 'amd64' for deb in pool)

print('Canonical product names and direct package publication passed.')
