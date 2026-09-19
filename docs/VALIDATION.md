# Validation

## Evidence model

Build, unit, integration, lifecycle and physical-hardware evidence prove different things and are recorded separately.

## Automated gates

- .github/workflows/publish.yml
- .github/workflows/sync-private-intune.yml

tests/ covers retention, signing, private-mirror policy and site setup. Publication additionally performs repository generation and selected Linux Mint lifecycle checks.

## Manual/environment evidence

A chroot/userspace lifecycle run cannot prove every kernel-loaded package path; kernel/DKMS products still require their owning project to validate runtime loading on a matching booted kernel.

Do not promote fixture/simulator/chroot evidence into a broader claim than the environment actually exercised.

## Release/publication criterion

The exact source revision and pinned dependencies/releases intended for publication must pass required gates. Artifacts must be traceable to that identity and documentation must not advertise known-failing or merely planned behaviour.

## Regression rule

Reproducible defects gain permanent automated coverage where practical, at the narrowest layer that captures the failure.
