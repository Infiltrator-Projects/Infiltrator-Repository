# Infiltrator Repository — Alpha

This repository is an alpha distribution layer for the Linux applications already published by **The-First-Infiltrator**. It does not replace, rewrite, or mirror the source repositories.

The GitHub Pages workflow discovers the latest GitHub Release for each configured project, downloads its current `.deb`, inspects the actual package metadata with `dpkg-deb`, generates Debian `Packages`, `Packages.gz` and `Release` metadata, and deploys the package pool plus a small software-centre-style catalogue.

## Alpha applications

- Linux System Monitor
- Calendar Plus
- Linux Defragger
- InfiltratorFS
- MBLINK
- JAGLINK
- WHERE'S WALLY

Edit `catalogue/apps-source.json` to add or remove applications. Each entry identifies the owning GitHub repository and the regular expression for the release `.deb` asset.

## Publish

GitHub Actions runs on pushes to `main`, on manual request and every six hours so new upstream releases can appear without modifying the application repositories.

The intended Pages address is:

`https://the-first-infiltrator.github.io/Infiltrator-Repository/`

The alpha APT source is:

`deb [trusted=yes arch=amd64] https://the-first-infiltrator.github.io/Infiltrator-Repository stable main`

Then:

```bash
sudo apt update
apt search infiltrator
```

Individual package names come from the `.deb` metadata itself and are displayed by the web catalogue.

## Security status

This is deliberately an **alpha**. The repository is not yet GPG-signed; the test source therefore uses `trusted=yes`. A production version should generate a dedicated repository signing key, publish the public key, produce `InRelease`/`Release.gpg`, and remove `trusted=yes` from installation instructions.

## Architecture

```text
Existing application repositories
          ↓ GitHub Releases
Infiltrator-Repository workflow
          ↓
  latest .deb packages
          ↓
   dpkg-scanpackages
          ↓
GitHub Pages
 ├── website/catalogue
 ├── pool/main/*.deb
 └── dists/stable/...
          ↓
 Linux Mint / APT
```
