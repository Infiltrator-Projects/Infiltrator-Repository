#!/usr/bin/env python3
"""Validate OFS release admission and the backward-compatible snapshot views."""
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
                 "infiltrator-filesystem-ofs_0.1.1_amd64.deb", "OFS.so", "SHA256SUMS"]
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

    def test_new_and_legacy_snapshots_share_exact_release_records(self):
        entries = publisher.discover(ROOT / "catalogue/apps-source.json")
        self.assertEqual(len(entries), 62)
        snapshot = {"schema": 1, "releases": {name: self.release() for name in entries}}
        with tempfile.TemporaryDirectory() as tmp:
            new, old = Path(tmp) / "v2.json", Path(tmp) / "v1.json"
            with patch.object(publisher, "build", return_value=snapshot), patch(
                    "sys.argv", ["publisher", "--output", str(new), "--legacy-output", str(old)]):
                publisher.main()
            modern, legacy = json.loads(new.read_text()), json.loads(old.read_text())
            self.assertEqual(len(legacy["releases"]), 61)
            self.assertEqual(modern, snapshot)
            self.assertNotIn("Filesystem-OFS", legacy["releases"])
            for name, release in legacy["releases"].items():
                self.assertEqual(release, modern["releases"][name])


if __name__ == "__main__":
    unittest.main()
