# Contributing

## Ownership first

Before changing Package Repository, identify which repository/layer owns the behaviour. Do not solve a shared problem by creating another private copy.

## Required practice

1. Read README.md and the canonical architecture/design documents.
2. Preserve exact dependency/release identity where reproducibility depends on it.
3. Add tests for changed behaviour and failure boundaries.
4. Keep uncertain or unsupported behaviour explicit.
5. Update roadmap/validation documentation when support changes.

## Verification

Run the normal build/test path and ensure relevant CI remains green. Manual or hardware claims require corresponding evidence.

## Repository policy

main is the working branch. Published tags/releases are immutable identities.
