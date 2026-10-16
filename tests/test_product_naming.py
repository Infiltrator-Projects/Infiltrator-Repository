#!/usr/bin/env python3
"""Verify canonical package selection and one-way upgrades from published names."""
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TOOL = Path(sys.argv[1]).resolve()
entries = [item for item in json.loads((ROOT / 'catalogue/apps-source.json').read_text())
           if item.get('canonical_package')]
assert len(entries) == 9
all_entries = json.loads((ROOT / 'catalogue/apps-source.json').read_text())
for identifier, name in {'mblink':'MBLink','jaglink':'JAGLink','bmwlink':'BMWLink','audilink':'AUDILink','fordlink':'FORDLink'}.items():
    entry = next(item for item in all_entries if item['id'] == identifier)
    assert entry['name'] == name and entry['repo'] == name, entry

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
        for package, version in [(item['canonical_package'], '9.0.1'), (item['legacy_packages'][0], '9.0.0')]:
            stage = root / 'stage'
            (stage / 'DEBIAN').mkdir(parents=True, exist_ok=True)
            (stage / 'DEBIAN/control').write_text(
                f'Package: {package}\nVersion: {version}\nArchitecture: amd64\n'
                'Maintainer: Test <test@example.invalid>\nDescription: naming fixture\n')
            subprocess.run(['dpkg-deb', '--build', '--root-owner-group', str(stage),
                            str(fixture / f'{package}_{version}_amd64.deb')],
                           check=True, stdout=subprocess.DEVNULL)
        fixtures.append(item)
    (root / 'catalogue/apps-source.json').write_text(json.dumps(fixtures))
    subprocess.run([str(TOOL), 'publish'], cwd=root, check=True, stdout=subprocess.DEVNULL)
    apps = json.loads((root / 'public/catalogue/apps.json').read_text())
    assert len(apps) == len(entries), 'Compatibility packages must not create application cards'
    for entry in entries:
        app = next(app for app in apps if app['id'] == entry['id'])
        canonical = entry['canonical_package']
        assert app['package'] == canonical and app['version'] == '9.0.1', app
        for legacy in entry['legacy_packages']:
            transition = root / f'public/pool/main/{legacy}_9.0.1_all.deb'
            assert transition.is_file(), transition
            dependency = subprocess.check_output(['dpkg-deb', '-f', str(transition), 'Depends'], text=True).strip()
            assert dependency == f'{canonical} (= 9.0.1)', dependency
            files = subprocess.check_output(['dpkg-deb', '-c', str(transition)], text=True)
            assert 'usr/share/applications' not in files, 'Transition packages must not add launchers'

    # Before a renamed release is available, keep the last qualified release
    # usable and never generate a reverse transition into the old name.
    for item in fixtures:
        for package in (root / 'fixtures' / item['id']).glob('*_9.0.1_amd64.deb'):
            package.unlink()
    subprocess.run([str(TOOL), 'publish'], cwd=root, check=True, stdout=subprocess.DEVNULL)
    for entry in entries:
        assert not (root / f"public/pool/main/{entry['canonical_package']}_9.0.0_all.deb").exists()

print('Canonical names, legacy upgrades and single application-card publication passed.')
