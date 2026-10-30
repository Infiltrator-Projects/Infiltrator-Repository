#!/usr/bin/env python3
"""Regression checks for complete DEB coverage and a bounded OS installer set."""
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


coverage = load("deb_coverage", ROOT / "tests/test_latest_release_deb_coverage.py")
publisher = load("native_publisher", ROOT / "scripts/publish-native-installers.py")


def entry(number):
    return {"owner": {"login": coverage.ORG}, "name": f"Repository-{number:03d}"}


class CatalogueCoverage(unittest.TestCase):
    def test_inventory_fetches_next_page_when_first_is_full(self):
        calls = []
        def fake_api(path):
            calls.append(path)
            return [entry(i) for i in range(100)] if "page=1" in path else [entry(100), entry(101)]
        with patch.object(coverage, "api_json", side_effect=fake_api):
            repos = coverage.org_repositories()
        self.assertEqual(len(repos), 102)
        self.assertEqual(len(calls), 2)
        self.assertIn("page=2", calls[1])

    def test_exactly_100_still_fetches_terminal_empty_page(self):
        with patch.object(coverage, "api_json", side_effect=[[entry(i) for i in range(100)], []]) as api:
            self.assertEqual(len(coverage.org_repositories()), 100)
        self.assertEqual(api.call_count, 2)

    def test_repeating_page_is_not_accepted_as_complete(self):
        pages = [[entry(i) for i in range(100)]] * 2
        with patch.object(coverage, "api_json", side_effect=pages):
            with self.assertRaisesRegex(ValueError, "duplicate"):
                coverage.org_repositories()

    def test_exfat_has_exactly_one_deb_rule_but_is_not_an_os_installer(self):
        entries = json.loads((ROOT / "catalogue/apps-source.json").read_text())
        exfat = [x for x in entries if x["repo"] == "Filesystem-exFAT"]
        self.assertEqual(len(exfat), 1)
        item = exfat[0]
        self.assertEqual(item["id"], "infiltrator-filesystem-exfat")
        self.assertEqual(item["minimum_version"], "0.1.0")
        errors = []
        regex = coverage.compile_regex(item["deb_regex"], "exFAT", errors)
        coverage.validate_assets(coverage.ORG, item["repo"],
            ["infiltrator-filesystem-exfat_0.1.0_amd64.deb"], [(item["id"], regex)], errors)
        self.assertEqual(errors, [])
        os_entries = publisher.discover(ROOT / "catalogue/apps-source.json")
        self.assertEqual(len(os_entries), 62)
        self.assertNotIn("Filesystem-exFAT", os_entries)
        self.assertIn("Filesystem-OFS", os_entries)


if __name__ == "__main__":
    unittest.main()
