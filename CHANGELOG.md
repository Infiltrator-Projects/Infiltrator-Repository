# Changelog

## 2026-10-16 — Publication robustness

- Refresh the pinned website family for balanced typography, restrained silver-blue accents and readable supporting text; keep the Software Centre introduction on the same heading and label scale.

- Isolate concurrent command capture and private signing state, including exception cleanup.
- Qualify the real production concurrency, signing and failure paths.
- Generate SHA256 and SHA512 by-hash indexes and retain verified previous index bytes for 24 hours across Pages deployments.
- Separate bounded immutable metadata leases from eligible package selection; reject missing or corrupt retained indexes before publication.
- Qualify transitions, expiry, migration and malformed-state rejection against the production index owner.

## 2026-09-19 — Joint forensic consistency completion

- aligned the Software Centre with the pinned ssmithnet.net website family and Common 1.19.3;
- made APT setup state-aware, line-scoped and safe across unsigned/signed transitions;
- added independent Package/Version/Architecture release validation with executable regression fixtures;
- preserved category-button focus with explicit pressed-state semantics and named the details dialog;
- disabled trust/setup output when repository metadata has not been verified;
- publish application icons from verified DEBs where available, with built-in symbols only as fallback;
- corrected the Calculator fallback symbol and System Monitor naming;
- added cross-site family acceptance validation to publication.
# Changelog

## Unreleased

- Publish the InfiltratorOS and Filesystems names and their renamed source repository links.
- Publish only the current filesystems and infiltratoros APT identities; classify their previous package assets as retired.

This file records user-visible, compatibility, architecture and validation changes for Package Repository.

## Unreleased

- Register the released Slicer Debian package in the catalogue, restoring release coverage so application updates including Runner Monitor 1.3.10 can reach APT clients.

- Publish Infiltrator File Manager 0.1.2 to the central APT repository so Mint Update Manager receives the released Files package.
- Refresh the central APT catalogue for Filesystem Support 0.5.13.
- Refresh the central APT catalogue for InfiltratorFS 0.18.97 and its repaired Ubuntu/Mint desktop integration package.
- Refresh the central APT catalogue for Filesystem Support 0.5.11 and verify Update Manager can see the released package.
- Republish after the Filesystem Support 0.5.3 release so APT clients receive the complete five-entry Amiga catalogue and desktop media-detection package.
- Advance all Package Repository Common consumers, including publication, Pages deployment and private-mirror synchronisation, to released Infiltratr Common 1.19.10 at `33e69c0a462b56d388881d89c4eb49f72fa0b0fe`.
- Correct the documented website-family pin to the immutable commit actually consumed by publication.

- Standardise non-automotive Software Centre icons on the InfiltratorFS/canonical `#00ADEF` line-art blue instead of the lighter package-art cyan, while retaining product artwork for Automotive entries.
- Give non-automotive catalogue cards and dialogs the intended raster/terminal typography treatment; Automotive entries retain their polished Corpo presentation.
- Verified package icons remain published for package-manager integration even when the Software Centre deliberately renders the canonical generic glyph.
- Canonical documentation baseline aligned with the Infiltrator project family.

## Policy

Record behaviour/support changes and material fixes. Research or internal activity belongs in specialist notes until it changes the supported product.

## Historical identity

Git tags, immutable releases and repository history remain authoritative for exact historical source/artifact identity.
