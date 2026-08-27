# Infiltrator Repository — Alpha

Infiltrator Repository is the distribution layer for the Linux applications published by **The-First-Infiltrator**. Each application remains independently developed and released in its own repository; this project turns approved GitHub Release packages into a normal APT source and a browsable software centre.

## Current applications

- Linux System Monitor
- Calendar Plus
- Linux Defragger
- InfiltratorFS
- MBLINK
- JAGLINK
- WHERE'S WALLY

The allow-list lives in `catalogue/apps-source.json`. A package is published only when a release contains exactly the expected `.deb` asset.

## Repository behaviour

Every publish run:

1. reads recent non-draft, non-prerelease GitHub Releases for each approved project;
2. retains up to five recent package versions per application;
3. downloads the matching `.deb` files;
4. requires and verifies each GitHub release asset SHA-256 digest;
5. reads package metadata from the `.deb` itself with `dpkg-deb`;
6. generates multiversion APT `Packages`, `Packages.gz` and `Release` metadata;
7. publishes APT `by-hash` paths to avoid inconsistent metadata during CDN/cache transitions;
8. generates the software-centre catalogue from the same verified packages; and
9. deploys the result to GitHub Pages.

A missing latest package, ambiguous release asset or SHA-256 mismatch fails the publication rather than silently publishing questionable content.

## Add to Linux Mint

The primary alpha suite is:

```text
deb [trusted=yes arch=amd64] https://the-first-infiltrator.github.io/Infiltrator-Repository alpha main
```

For the current unsigned alpha:

```bash
echo 'deb [trusted=yes arch=amd64] https://the-first-infiltrator.github.io/Infiltrator-Repository alpha main' \
  | sudo tee /etc/apt/sources.list.d/infiltrator-alpha.list
sudo apt update
```

The old `stable` path is currently published as a temporary compatibility alias so early alpha testers do not break immediately. New installations should use `alpha`. The compatibility alias can be removed once alpha clients have migrated.

## Signing readiness

No private signing key is stored in this repository.

The publisher supports optional GitHub Actions secrets:

- `APT_SIGNING_KEY_B64` — base64-encoded private OpenPGP signing key;
- `APT_SIGNING_KEY_FINGERPRINT` — exact fingerprint to use;
- `APT_SIGNING_PASSPHRASE` — optional key passphrase.

When configured, the build creates `InRelease`, `Release.gpg` and `repository-key.gpg`. The web software centre automatically changes its installation instructions from `trusted=yes` to a dedicated `signed-by=` keyring.

Until those secrets are deliberately configured, the site clearly identifies the repository as an unsigned alpha.

## Publication

GitHub Actions publishes on pushes to `main`, on manual request and every six hours. A scheduled run therefore picks up new approved application releases without requiring changes to this repository.

Live software centre:

`https://the-first-infiltrator.github.io/Infiltrator-Repository/`

## Architecture

```text
Approved application repositories
            ↓
      GitHub Releases
            ↓
  verified SHA-256 .deb files
            ↓
 Infiltrator-Repository build
       ↙              ↘
APT multiversion       catalogue JSON
metadata + by-hash          ↓
       ↘              ↙
          GitHub Pages
                ↓
        Linux Mint / APT
```
