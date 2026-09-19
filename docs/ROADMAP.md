# Roadmap

## Current foundation

- C++17 first-party repository materialisation and catalogue generation.
- Public GitHub release discovery for normal application packages.
- Debian metadata/version validation and SHA-256 checks.
- Retention and mirrored-package policy with automated tests.
- Repository signing self-test path.
- Static software centre generated from repository state.
- Linux Mint userspace lifecycle qualification for representative install/upgrade/remove flows.

## Near-term priorities

- keep signing and repository-key handling explicit and reproducible;
- extend lifecycle coverage as additional applications enter the repository;
- keep catalogue metadata derived from resolved package state rather than duplicated configuration;
- strengthen failure cleanup so interrupted publication cannot leave ambiguous output;
- keep Common reuse limited to genuinely generic primitives.

## Longer-term direction

- additional channels only if promotion and retention semantics remain explicit;
- broader distribution testing without turning the repository into an application build system;
- stronger reproducibility evidence for complete generated repository trees.

## Completion rule

A roadmap item is complete when publication code, automated tests, generated metadata and user-facing catalogue behaviour agree. Merely downloading an artifact or rendering it on the site is not publication evidence.
