# Validation

## Automated tests

The repository maintains direct tests for:

- retention/version-selection behaviour;
- signing and signature-generation paths;
- private mirror policy;
- software-centre/site setup;
- required Slicer catalogue membership and exclusion of the mistaken inherited `2.9.6` package when publishing `0.0.1`.

The publication workflow also exercises the real C++ repository tool and Debian utilities used by production.

## Package evidence

Every accepted Debian package is checked at the package-metadata layer. Version, package name and architecture are compared with the expected catalogue/release identity rather than trusted from the filename.

SHA-256 digests are part of the materialised package identity.

## Signing evidence

The signing self-test creates a disposable CI key and drives the real signing code, then verifies generated signed metadata through an independent keyring. A successful unsigned generation is not represented as signing proof.

## Linux Mint lifecycle evidence

The Mint qualification uses a genuine Linux Mint userspace extracted from a verified ISO and exercises repository discovery plus representative install, upgrade, remove and `apt-get check` flows.

That environment cannot prove runtime behaviour requiring a booted matching kernel. DKMS/kernel products therefore retain runtime qualification responsibility in their owning repositories.

## Publication criterion

A publication is valid only when the exact workflow source completes package discovery/validation, repository generation and the required policy tests. The site and APT metadata must describe the same resolved package set. Before deployment, `tests/test_slicer_publication.py --published public` requires Slicer in the generated catalogue, compares its retained versions with both APT indexes, and rejects the inherited `2.9.6` package or any indexed version newer than the catalogue selection.

## Regression rule

Any failure that allowed wrong version selection, bad metadata, incorrect retention or inconsistent site/repository state should gain a permanent regression test. Slicer discovery also tests a GitHub release list with the inherited higher version first; publication dates determine the latest eligible release, independently of API ordering.

## Forensic consistency regressions

Publication now exercises the defects reproduced in the 19 September 2026 joint review:

- `tests/test_release_identity.py` builds disposable Debian fixtures and proves that the production validator accepts the intended Package/Version/Architecture tuple while rejecting independently wrong package name, release version and architecture.
- `tests/test_site_setup.py` requires setup copying to remain disabled until repository metadata is verified, requires line-scoped cleanup of Infiltrator APT entries rather than whole-file suite rewriting, checks signed/unsigned canonical paths, keyboard-selection semantics and the package-icon path.
- the pinned `ssmithnet.net/tests/check_web_family.py` runs against the completed Pages tree and requires canonical/Open Graph metadata, the shared navigation/landmarks and three real local Corpo WOFF2 assets.
- package publication extracts an application icon from the verified current DEB when available; the catalogue references that published file and falls back to a built-in symbol only for packages without one.

## Concurrent capture and signing failure

The source workflow compiles a fixture against the actual publisher implementation. Eight workers capture distinct command outputs concurrently, a failed child command must report failure, and a private temporary directory must remain inaccessible to other users and disappear during exception unwinding. The existing compiled-publisher signing fixture verifies both signed suites and now also exercises a wrong-fingerprint failure with private scratch cleanup.

## APT index transitions

tests/apt_index_history_test.cpp exercises the production history owner with disposable publication generations. It checks both hash algorithms, unchanged canonical indexes, preservation of previous bytes, recovery from legacy SHA256-only by-hash hosting, migration without a manifest, first publication, expiry after a long publication gap, and rejection of corrupt, missing or malformed unexpired state. Failed candidates never acquire a complete history manifest.

After deployment, compare each catalogue application's version and SHA-256 with its primary GitHub Release DEB and the matching Package/Version/SHA256 records in both published APT suites. Resolve the hashes in each Release file against the canonical indexes and their SHA256/SHA512 by-hash URLs. A successful HTTP response alone does not prove that these identities agree. catalogue/repository.json records the observed signing state; disposable signing fixtures establish signing-code behavior separately from production key configuration.

The [Debian repository format](https://wiki.debian.org/DebianRepository/Format#indices_acquisition_via_hashsums_.28by-hash.29) defines content-addressed acquisition and retention of previous metadata. The live Pages response advertised a 600-second cache lifetime during this review; the publisher retains index history for 24 hours.
