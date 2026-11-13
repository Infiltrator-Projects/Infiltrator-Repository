# Changelog

## 2026-11-13 — Require Common V2-only BOOT deployment

- Publish InfiltratorOS 1.0.86 with BOOT 0.1.46 as the minimum mandatory firmware component release.

## 2026-11-13 — Common V2 NTFS extent maps

- Publish NTFS 1.0.18 with per-file physical extent mapping through the installed `NTFS.so`. Mapping is read-only and uses the Common V2 partition host.

## 2026-11-13 — BOOT Common V2 filesystem loading

- Publish BOOT 0.1.46 and InfiltratorOS 1.0.85 after their OVMF qualification. BOOT loads filesystem extensions through Common V2 shared objects. The updater preserves existing deployments that may still depend on a separate EFI filesystem driver.

## 2026-11-13 — Common V2 NTFS formatting

- Publish NTFS 1.0.17 and Files 0.1.84. Files detects the selected removable volume and delegates NTFS creation to `NTFS.so` through Common V2. The NTFS native build does not install FUSE.
- Publish InfiltratorOS 1.0.84 with validation of the NTFS native installer release and its FUSE-free build prerequisites.

## 2026-11-13 — Defragmenter 1.8.0-300

- Publish the qualified Defragmenter package with Common V2 OFS Test Media formatting and verification.

## 2026-11-13 — OFS Common V2 file access

- Publish OFS 0.1.16 with the original drop-in file access exports removed. The package retains Common V2 for BOOT and file operations and preserves the qualified OFS relocation and recovery path.

## 2026-11-13 — Common V2 OFS firmware support

- Publish the qualified OFS 0.1.15 package and native installer. BOOT reads OFS volumes and their labels through Common V2.

## 2026-11-13 — Common V2 FAT firmware modules

- Publish FAT12 0.1.27, FAT16 0.1.19 and FAT32 0.1.15 after Common V2 firmware and package qualification. The FAT shared objects use the Common interface for BOOT and volume labels.

## 2026-11-13 — InfiltratorOS Common V2 provider validation

- Publish the qualified InfiltratorOS 1.0.83 package. Filesystem provisioning now requires the defined Common V2 export.

## 2026-11-12 — Common V2 BOOT and Files rollout

- Publish InfiltratorOS 1.0.82, BOOT 0.1.45, Files 0.1.83 and FAT16 0.1.18 from their verified release packages. The installer stages compatible Common V2 filesystem modules with BOOT after the filesystem workers finish. Files calls the selected installed module's format operation.

## 2026-11-12 — InfiltratorOS 1.0.81 BOOT upgrade fix

- Publish the verified update for existing firmware-registered BOOT installations, including installations created before the upgrader's marker.

## 2026-11-12 — InfiltratorOS 1.0.80 native BOOT fix

- Publish the verified InfiltratorOS update that builds BOOT from its independent source installer during provisioning, without a portable BOOT package prerequisite.

## 2026-11-12 — InfiltratorOS 1.0.79 and BOOT 0.1.42 APT refresh

- Publish the verified automatic BOOT upgrade and its independent BOOT package together. The upgrader adds an EFI option on eligible systems and preserves GRUB as the default.

## 2026-11-12 — InfiltratorOS 1.0.78 APT refresh

- Publish the refreshed GTK upgrader and the migration that keeps native Calendar builds selected on machines with the legacy priority-1001 rule.

## 2026-11-12 — InfiltratorOS 1.0.77 APT refresh

- Publish the InfiltratorOS upgrader window with the running package version in its title and a Debian-based systems description.

## 2026-11-12 — InfiltratorOS 1.0.76 APT refresh

- Refresh the alpha and beta APT indexes after the verified InfiltratorOS v1.0.76 GitHub release. This release adapts native build concurrency to available CPU and RAM, up to 16 selected components.

## 2026-11-08 — InfiltratorOS 1.0.70 native verification fix

- Refresh the beta APT catalogue after the fully verified InfiltratorOS v1.0.70 release. Correct false failures when installed applications omit an optional Defragmenter metadata field or do not ship a PDF. Continue to require version identity, package ownership, native-build evidence, SHA-256 attestation and dpkg verification. Preserve independently published application and filesystem packages.

## 2026-11-08 — InfiltratorOS 1.0.68 APT refresh

- Refresh the beta APT index after the verified InfiltratorOS v1.0.68 GitHub release. This carries bounded retries for transient HTTP 504 failures when retrieving the four application-native RUN installers. Preserve independent application, calendar, clock, filesystem and Intune publication rules; retain existing package history and validation.

## Retire Common’s combined temporal producer

- Remove the legacy combined resource package from current APT catalogue/index generation; preserve historical GitHub release assets.
- Require provider-owned translations from the 14 localized calendars’ 1.0.1 releases.
- Qualify independent ownership and consumer-removal survival using all 54 individual packages in the Mint lifecycle test.

## Independent temporal providers

Publish the generic Debian packages from all 31 calendar and 23 clock repositories, alongside their product-owned native RUN and complete source ZIP releases. Preserve locally compiled +native1 versions and accept the narrowly scoped legacy module ownership transfer.

## 2026-10-18 — Files 0.1.43 menu repair

- Refresh the beta APT index for verified Files 0.1.43 after its published GitHub release. The hamburger menu now has a bounded, scrollable File actions list with clipboard commands still accessible, plus a GTK directory-monitoring safeguard during own clipboard mutations. Preserve the canonical `files` package name, validated metadata, checksums and retention rules.


## 2026-10-18 — Files 0.1.42 APT publication

- Refresh the verified beta index for released Files v0.1.42. This release adds bounded filename filtering, Open With associations, private recent locations, safely journalled empty-file creation and MIME-aware Linux clipboard interoperability. Its final GTK lifetime fix passed standard and aggressive-native qualification. Keep the existing package name `files`, signatures/metadata validation and retention policy unchanged.


## 2026-10-18 — Files 0.1.41 APT publication

- Refresh the beta APT catalogue after the successful Files v0.1.41 release, preserving the existing package name `files`, verified package metadata, SHA checks and retention policy. This revision corrects measured GTK Details-row density, restores neutral Day view controls and unifies the navigation header and tab strip without changes to file-operation engines.


## 2026-10-18 — Files 0.1.38 APT refresh

- Republish the verified Files 0.1.38 package after its source release, including the filesystem-root startup correction and consistent Day/Night GTK contrast. Keep the existing five-version APT retention policy and package name `files` unchanged.


## 2026-10-16 — Publication robustness

- Refresh the pinned website family for balanced typography, the original locked MB fonts, palette and wordmark (including #00ADEF) and readable supporting text; keep the Software Centre introduction on the same heading and label scale.

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

- Register the released Slicer Debian package in the catalogue, restoring release coverage so application updates including RunnerScope 1.3.10 can reach APT clients.

- Publish Files 0.1.2 to the central APT repository so Mint Update Manager receives the released Files package.
- Refresh the central APT catalogue for Filesystem Support 0.5.13.
- Refresh the central APT catalogue for InfiltratorFS 0.18.97 and its repaired Ubuntu/Mint desktop integration package.
- Refresh the central APT catalogue for Filesystem Support 0.5.11 and verify Update Manager can see the released package.
- Republish after the Filesystem Support 0.5.3 release so APT clients receive the complete five-entry Amiga catalogue and desktop media-detection package.
- Advance all Package Repository Common consumers, including publication, Pages deployment and private-mirror synchronisation, to released Libraries 1.19.10 at `33e69c0a462b56d388881d89c4eb49f72fa0b0fe`.
- Correct the documented website-family pin to the immutable commit actually consumed by publication.

- Standardise non-automotive Software Centre icons on the InfiltratorFS/canonical `#00ADEF` line-art blue instead of the lighter package-art cyan, while retaining product artwork for Automotive entries.
- Give non-automotive catalogue cards and dialogs the intended raster/terminal typography treatment; Automotive entries retain their polished Corpo presentation.
- Verified package icons remain published for package-manager integration even when the Software Centre deliberately renders the canonical generic glyph.
- Canonical documentation baseline aligned with the Infiltrator project family.

## Policy

Record behaviour/support changes and material fixes. Research or internal activity belongs in specialist notes until it changes the supported product.

## Historical identity

Git tags, immutable releases and repository history remain authoritative for exact historical source/artifact identity.
