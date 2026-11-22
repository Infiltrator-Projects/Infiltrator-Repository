#!/usr/bin/env python3
"""Validate OFS/exFAT release admission and three backward-compatible snapshot views."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("publisher", ROOT / "scripts/publish-native-installers.py")
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)


class NativeInstallers(unittest.TestCase):
    """Qualify the real published artifact contract without weakening integrity."""

    def release(self, repository="Filesystem-OFS", version="0.1.18", extras=()):
        name = repository.lower()
        names = [
            f"{name}-{version}-native-installer.run",
            f"infiltrator-{name}_{version}_amd64.deb",
            *extras,
        ]
        prefix = f"https://github.com/Infiltrator-Projects/{repository}/releases/download/v{version}/"
        return {
            "tag_name": "v" + version,
            "draft": False,
            "prerelease": False,
            "target_commitish": "a" * 40,
            "assets": [
                {"name": asset, "browser_download_url": prefix + asset,
                 "digest": "sha256:" + "c" * 64, "size": 100}
                for asset in names
            ],
        }

    def test_all_five_filesystems_accept_current_two_asset_release_contract(self):
        versions = {
            "Filesystem-FAT12": "0.1.30",
            "Filesystem-FAT16": "0.1.22",
            "Filesystem-FAT32": "0.1.18",
            "Filesystem-OFS": "0.1.18",
            "Filesystem-exFAT": "0.1.17",
        }
        for repository, version in versions.items():
            with self.subTest(repository=repository):
                release = self.release(repository, version)
                result = publisher.verify(repository, {}, release)
                self.assertEqual(result["tag_name"], "v" + version)
                self.assertEqual(result["target_commitish"], "a" * 40)
                self.assertEqual(
                    {asset["name"] for asset in result["assets"]},
                    {asset["name"] for asset in release["assets"]},
                )
                for manifest in ("SHA256SUMS", "SHA256SUMS.txt"):
                    with self.subTest(repository=repository, manifest=manifest):
                        with_manifest = self.release(repository, version, (manifest,))
                        publisher.verify(repository, {}, with_manifest)

    def test_filesystem_release_rejects_missing_or_unexpected_assets(self):
        release = self.release("Filesystem-FAT16", "0.1.22")
        for missing in release["assets"]:
            bad = copy.deepcopy(release)
            bad["assets"].remove(missing)
            with self.subTest(missing=missing["name"]), self.assertRaises(ValueError):
                publisher.verify("Filesystem-FAT16", {}, bad)

        for unexpected in ("FAT16.efi", "fat16-linux-6.12.107.ko",
                           "FAT16.so", "unrelated-package.deb"):
            bad = self.release("Filesystem-FAT16", "0.1.22", (unexpected,))
            with self.subTest(extra=unexpected), self.assertRaisesRegex(ValueError, "expected one native RUN"):
                publisher.verify("Filesystem-FAT16", {}, bad)

        bad = self.release("Filesystem-exFAT", "0.1.17",
                           ("SHA256SUMS", "SHA256SUMS.txt"))
        with self.assertRaises(ValueError):
            publisher.verify("Filesystem-exFAT", {}, bad)

    def test_filesystem_release_verifies_checksum_origin_size_and_revision(self):
        release = self.release()
        publisher.verify("Filesystem-OFS", {}, release)
        for revision in (None, "main", "a" * 12):
            with self.subTest(revision=revision), self.assertRaisesRegex(ValueError, "not pinned"):
                publisher.verify("Filesystem-OFS", {}, dict(release, target_commitish=revision))
        for field, value in (
            ("digest", None),
            ("digest", "sha256:" + "0" * 63),
            ("size", 0),
            ("browser_download_url", "https://example.invalid/replaced"),
        ):
            bad = copy.deepcopy(release)
            bad["assets"][0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                publisher.verify("Filesystem-OFS", {}, bad)
        duplicate = copy.deepcopy(release)
        duplicate["assets"].append(copy.deepcopy(duplicate["assets"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            publisher.verify("Filesystem-OFS", {}, duplicate)

    def test_temporal_release_still_requires_source_archive(self):
        repository, version = "Calendar-Gregorian", "1.0.7"
        base = self.release(repository, version)
        base["assets"].append({
            "name": f"calendar-gregorian-{version}-source.zip",
            "browser_download_url": (
                f"https://github.com/Infiltrator-Projects/{repository}/releases/"
                f"download/v{version}/calendar-gregorian-{version}-source.zip"
            ),
            "digest": "sha256:" + "c" * 64,
            "size": 100,
        })
        self.assertEqual(publisher.verify(repository, {}, base)["tag_name"], "v" + version)
        base["assets"].pop()
        with self.assertRaisesRegex(ValueError, "incomplete independent temporal"):
            publisher.verify(repository, {}, base)

    def test_new_and_legacy_snapshots_share_exact_release_records(self):
        entries = publisher.discover(ROOT / "catalogue/apps-source.json")
        self.assertEqual(len(entries), 63)
        snapshot = {"schema": 1, "releases": {name: self.release() for name in entries}}
        with tempfile.TemporaryDirectory() as tmp:
            new, middle, old = [Path(tmp) / f"v{n}.json" for n in (3, 2, 1)]
            with patch.object(publisher, "build", return_value=snapshot), patch(
                    "sys.argv", ["publisher", "--output", str(new),
                                 "--v2-output", str(middle), "--legacy-output", str(old)]):
                publisher.main()
            modern, v2, legacy = [json.loads(p.read_text()) for p in (new, middle, old)]
            self.assertEqual(len(modern["releases"]), 63)
            self.assertEqual(len(v2["releases"]), 62)
            self.assertEqual(len(legacy["releases"]), 61)
            self.assertEqual(modern, snapshot)
            self.assertNotIn("Filesystem-exFAT", v2["releases"])
            self.assertNotIn("Filesystem-OFS", legacy["releases"])
            for name, release in v2["releases"].items():
                self.assertEqual(release, modern["releases"][name])
            for name, release in legacy["releases"].items():
                self.assertEqual(release, v2["releases"][name])


if __name__ == "__main__":
    unittest.main()
