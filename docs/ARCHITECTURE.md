# Architecture

## Purpose

Package Repository is the distribution layer that turns approved independent GitHub releases into a normal APT source and static software catalogue.

## System decomposition

- release discovery and package selection
- APT metadata generation
- retention and mirroring policy
- signing path
- static catalogue/site generator
- Linux Mint lifecycle qualification
- scheduled publication workflows

## Ownership boundaries

Application repositories own their software and release artifacts. Package Repository owns which approved artifacts are mirrored, how repository metadata is generated, how retention/signing/publication work and how the catalogue represents that state.

Mechanisms supplied by GitHub, APT, an operating system, LINK/Common or a platform toolkit sit behind explicit project-owned policy. The external mechanism must not silently become the source of product meaning.

## Source of truth

Code, tests, pinned dependency/release identities and generated artifacts define executable/publication behaviour. Documentation defines ownership and support boundaries. Specialist files may refine a subsystem but must not contradict this model.

## Change discipline

Keep generic behaviour in its shared owner and local behaviour in this repository. Unknown, unavailable and unsupported states stay explicit. Changes to persistent/publication identity require an intentional version or migration decision.

## Specialist documentation

- No specialist architecture documents beyond the canonical baseline are currently required.
