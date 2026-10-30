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
    def release(self):
        names = ["filesystem-ofs-0.1.1-native-installer.run",
                 "infiltrator-filesystem-ofs_0.1.1_amd64.deb", "OFS.so", "SHA256SUMS",
                 "ofs-linux-6.12.107.ko"]
        prefix = "https://github.com/Infiltrator-Projects/Filesystem-OFS/releases/download/v0.1.1/"
        return {"tag_name": "v0.1.1", "assets": [
            {"name": name, "browser_download_url": prefix + name,
             "digest": "sha256:" + "c" * 64, "size": 100} for name in names]}

    def test_ofs_requires_complete_checksummed_release(self):
        release = self.release()
        self.assertEqual(publisher.verify("Filesystem-OFS", {}, release)["tag_name"], "v0.1.1")
        for missing in release["assets"]:
            bad = copy.deepcopy(release)
            bad["assets"].remove(missing)
            with self.assertRaises(ValueError):
                publisher.verify("Filesystem-OFS", {}, bad)
        for field, value in (("digest", None), ("size", 0), ("browser_download_url", "https://example.invalid/")):
            bad = copy.deepcopy(release)
            bad["assets"][0][field] = value
            with self.assertRaises(ValueError):
                publisher.verify("Filesystem-OFS", {}, bad)

    def test_exfat_must_publish_aggressive_native_run_and_exact_assets(self):
        version = "0.1.2"
        names = ["filesystem-exfat-0.1.2-native-installer.run",
                 "infiltrator-filesystem-exfat_0.1.2_amd64.deb",
                 "exFAT.so", "exfat-linux-6.12.107.ko", "SHA256SUMS"]
        prefix = "https://github.com/Infiltrator-Projects/Filesystem-exFAT/releases/download/v0.1.2/"
        release = {"tag_name": "v" + version, "assets": [
            {"name": name, "browser_download_url": prefix + name,
             "digest": "sha256:" + "a" * 64, "size": 101} for name in names]}
        self.assertEqual(publisher.verify("Filesystem-exFAT", {}, release)["tag_name"], "v0.1.2")
        for item in names:
            bad = copy.deepcopy(release)
            bad["assets"] = [x for x in bad["assets"] if x["name"] != item]
            with self.assertRaises(ValueError):
                publisher.verify("Filesystem-exFAT", {}, bad)

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
