#!/usr/bin/env python3
"""Ensure local mirror retention agrees with the actual APT package pool."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('publisher', ROOT / 'scripts/sync-repository.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
with tempfile.TemporaryDirectory() as td:
    m.ROOT = Path(td)
    m.POOL = m.ROOT / 'pool'
    m.POOL.mkdir()
    mirrors = m.ROOT / 'mirrors'
    mirrors.mkdir()
    for version in ['1.1', '1.2', '1.3', '1.4', '1.5', '1.9', '1.10']:
        tree = m.ROOT / ('build-' + version)
        (tree / 'DEBIAN').mkdir(parents=True)
        (tree / 'DEBIAN/control').write_text(f'Package: retention-test\nVersion: {version}\nArchitecture: all\nMaintainer: Test <test@example.invalid>\nDescription: retention fixture\n')
        subprocess.run(['dpkg-deb', '--build', '--root-owner-group', str(tree), str(mirrors / f'retention-test_{version}_all.deb')], check=True, stdout=subprocess.DEVNULL)
    result = m.collect_local_app(dict(name='Test', repo='Test', local_deb_glob='mirrors/*.deb'))
    assert result['version'] == '1.10', result
    assert [x['version'] for x in result['history']] == ['1.10','1.9','1.5','1.4','1.3']
    assert {p.name for p in m.POOL.glob('*.deb')} == {x['asset'] for x in result['history']}
    assert len(list(mirrors.glob('*.deb'))) == 7, 'source history must remain intact'
print('PASS: Debian version ordering and five-version APT pool retention')
