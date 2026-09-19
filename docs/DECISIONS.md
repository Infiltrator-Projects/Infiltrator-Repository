# Decisions

## ADR-001 — Publish normal APT, not a private updater protocol

**Decision.** Applications are distributed through standard Debian/APT repository semantics.

**Rationale.** Linux already has dependency, upgrade, signature and lifecycle machinery. Replacing it would create unnecessary product-specific infrastructure.

**Consequence.** Repository correctness is tested with genuine APT/package metadata and Linux Mint lifecycle checks.

## ADR-002 — Upstream releases remain the application source of truth

**Decision.** Package Repository consumes approved immutable application release assets; it does not rebuild them into new application releases.

**Rationale.** Rebuilding would create a second release authority and break traceability.

**Consequence.** Published repository packages retain upstream release/version identity.

## ADR-003 — Repository semantics live in first-party C++

**Decision.** Selection, retention, validation and materialisation policy are implemented in `repository-tool.cpp`.

**Rationale.** Policy must remain inspectable and controlled even when external mechanisms change.

**Consequence.** Shell/system tools are narrow mechanisms, not scattered policy scripts.

## ADR-004 — Use authoritative Debian tools where they are stronger

**Decision.** Use `dpkg`/`dpkg-deb` for Debian version/package semantics rather than duplicating them.

**Rationale.** Debian's own tools are the reference behaviour APT users will encounter.

**Consequence.** The repository remains dependent on a normal Debian-family publication environment, which is intentional.

## ADR-005 — Catalogue and APT indexes share one resolved state

**Decision.** The browsable software centre is generated from the same selected package set as repository metadata.

**Rationale.** Independent selection logic would allow the website and APT source to disagree.

**Consequence.** Presentation code cannot silently publish a version the repository did not resolve.

## ADR-006 — Private/mirrored packages are an explicit boundary

**Decision.** Packages that cannot use ordinary public release discovery are handled through explicit mirror policy and tests.

**Rationale.** Hidden exceptions inside generic release discovery make provenance difficult to reason about.

**Consequence.** Private/mirror logic remains separately named and regression-tested.

## ADR-007 — Validate release identity against independent expectations

**Decision.** Every catalogue entry declares expected Debian package identity and architecture, while a canonical `v<version>` GitHub release tag supplies the expected version.

**Rationale.** Reading Package, Version and Architecture from a DEB and comparing those fields with themselves proves only that the file is parseable. Publication must establish agreement between independently maintained release/catalogue intent and package internals.

**Consequence.** A package with the right filename and digest but the wrong internal package name, version or architecture fails before publication.

## ADR-008 — Share website identity through an immutable family snapshot

**Decision.** Package Repository consumes the `ssmithnet.net` website-family assets and acceptance test from an exact commit, while Common remains the neutral primitive layer.

**Rationale.** Copying font-family names or approximate colours independently allows the two public sites to drift while appearing superficially related.

**Consequence.** Family changes are explicit, byte-addressable updates. Both sites stay self-contained at runtime and catalogue-specific presentation remains local.
