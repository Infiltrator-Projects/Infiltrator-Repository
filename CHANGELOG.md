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

This file records user-visible, compatibility, architecture and validation changes for Package Repository.

## Unreleased

- Standardise non-automotive Software Centre icons on the InfiltratorFS/canonical `#00ADEF` line-art blue instead of the lighter package-art cyan, while retaining product artwork for Automotive entries.
- Give non-automotive catalogue cards and dialogs the intended raster/terminal typography treatment; Automotive entries retain their polished Corpo presentation.
- Verified package icons remain published for package-manager integration even when the Software Centre deliberately renders the canonical generic glyph.
- Canonical documentation baseline aligned with the Infiltrator project family.

## Policy

Record behaviour/support changes and material fixes. Research or internal activity belongs in specialist notes until it changes the supported product.

## Historical identity

Git tags, immutable releases and repository history remain authoritative for exact historical source/artifact identity.
