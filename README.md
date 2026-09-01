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
deb [trusted=yes arch=amd64] https://infiltrator-projects.github.io/Infiltrator-Repository alpha main
```

For the current unsigned alpha, the setup command also repairs installations that still reference the pre-organisation GitHub Pages URL:

```bash
OLD='https://the-first-infiltrator.github.io/Infiltrator-Repository'
NEW='https://infiltrator-projects.github.io/Infiltrator-Repository'
sudo grep -RIlF "$OLD" /etc/apt/sources.list /etc/apt/sources.list.d 2>/dev/null \
  | while IFS= read -r f; do sudo sed -i "s#$OLD#$NEW#g" "$f"; done
echo 'deb [trusted=yes arch=amd64] https://infiltrator-projects.github.io/Infiltrator-Repository alpha main' \
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

A local helper is provided at `scripts/create-signing-key.sh`. It creates a dedicated two-year APT signing key outside the repository and writes the two values that must be added as GitHub Actions secrets. The private key output must never be committed to Git.

## Validation

Every non-scheduled publish also runs two independent validation jobs.

The signing self-test creates a disposable CI-only OpenPGP key, signs both suites through the real repository signing code, imports the generated public key into a fresh keyring and verifies both `InRelease` and `Release.gpg`.

The Mint lifecycle test downloads the Linux Mint 22.3 Cinnamon ISO from the kernel.org Linux Mint mirror, verifies the ISO against its published SHA-256 list, extracts the genuine Mint `filesystem.squashfs`, and performs APT testing inside that clean Mint userspace. It checks repository discovery for all seven packages, installs an older System Monitor and upgrades it to the current version, installs and removes the standard desktop applications, and runs `apt-get check` throughout. InfiltratorFS is dependency-resolved but not kernel-loaded in the chroot because DKMS runtime validation requires a booted Mint kernel. WHERE'S WALLY is retrieved and Debian-metadata validated because complete installation also requires the external Zabbix frontend repository.

## Publication

GitHub Actions publishes on pushes to `main`, on `application-release` dispatches, on manual request and every five minutes as a permission-independent safety net. Source release workflows attempt an immediate dispatch; the five-minute poll ensures a migrated or temporarily mis-scoped cross-repository token cannot leave APT stale. Scheduled runs refresh packages without re-downloading the multi-gigabyte Mint ISO; the heavier Mint lifecycle and signing self-tests run on code changes and manual runs.

Live software centre:

`https://infiltrator-projects.github.io/Infiltrator-Repository/`

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
