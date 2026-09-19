# Architecture

## Purpose

Package Repository is the distribution layer for independently released Infiltrator applications. It does not build application source into new releases; it discovers approved immutable release artifacts, validates their identity, constructs APT metadata, retains selected historical packages, generates the static software catalogue and publishes the resulting repository.

## Components

### Catalogue source

`catalogue/apps-source.json` is the maintained input describing applications the repository knows how to discover and present. It is configuration, not a substitute for upstream release metadata.

### Repository tool

`scripts/repository-tool.cpp` is the first-party C++17 publication engine. It owns repository semantics such as release discovery, version comparison, package metadata validation, retention, catalogue generation and durable publication.

The executable deliberately uses narrow system tools for mechanisms that are already authoritative on Debian-family systems:

- `curl` for HTTP transfer;
- `jq` for selected JSON extraction;
- `dpkg`/`dpkg-deb` for Debian version and package metadata semantics;
- `sha256sum` for digest calculation;
- OpenPGP tooling in the signing path.

Those commands are mechanisms behind project-owned policy. Their output is validated before it affects repository state.

### Common

Pinned Infiltratr Common provides generic output escaping and durable atomic file publication. Repository-specific package selection, APT metadata, retention, signing and catalogue semantics remain local.

### Mirrored packages

`mirrored-packages/` holds packages that cannot be rediscovered solely through the ordinary public release path or that are deliberately retained for lifecycle testing/private-mirror policy. Checksums and package metadata are verified before use.

### Static site

The generated software centre is a static catalogue. It presents repository state but does not independently decide what versions are valid or publishable.

### Workflows

`.github/workflows/publish.yml` is the normal publication path. `sync-private-intune.yml` handles the explicitly separate private/mirrored package boundary.

## Data flow

1. Read maintained catalogue configuration.
2. Discover candidate immutable upstream release assets.
3. Validate release/package version and Debian metadata.
4. Verify or compute cryptographic digests.
5. Apply retention and mirror policy.
6. Materialise the APT pool and package indexes.
7. Sign repository metadata when signing is enabled.
8. Generate the static catalogue from the same resolved package state.
9. Publish the completed static repository/site artifact.

A failure before completed materialisation must not leave a partially authoritative repository state.

## Ownership boundaries

Application repositories own application source, versioning and release artifacts. Package Repository owns distribution policy after those releases exist. GitHub supplies release hosting and Pages/Actions execution; Debian tooling supplies package/version semantics; neither owns the repository's selection or retention rules.

## Source of truth

The C++ tool plus catalogue configuration and tests define publication behaviour. Generated repository/site output is an artifact, not hand-maintained policy.

## Independent release identity

Each catalogue entry declares an expected Debian package-name regular expression and architecture independently of the downloaded package. For GitHub releases, the canonical `v<version>` release tag supplies the expected Debian version. The publisher validates Package, Version and Architecture against those independent values after SHA-256 verification and before the package enters resolved repository state.

## Website family boundary

The Software Centre consumes an immutable snapshot of the `ssmithnet.net` website family during publication. The pinned snapshot supplies the three Corpo font assets, shared site CSS, graphics and the cross-site output acceptance test. Package Repository retains its own catalogue layout and behaviour. Common 1.19.3 remains the product-neutral layer beneath both sites.
