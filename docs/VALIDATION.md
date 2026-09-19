# Validation

## Automated tests

The repository maintains direct tests for:

- retention/version-selection behaviour;
- signing and signature-generation paths;
- private mirror policy;
- software-centre/site setup.

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

A publication is valid only when the exact workflow source completes package discovery/validation, repository generation and the required policy tests. The site and APT metadata must describe the same resolved package set.

## Regression rule

Any failure that allowed wrong version selection, bad metadata, incorrect retention or inconsistent site/repository state should gain a permanent regression test.
