# Package Repository — Beta

**Project copyright:** © 1993-2026 Shannon Smith

Package Repository is the distribution layer for the Linux applications published by Shannon Smith. Each application remains independently developed and released in its own repository; this project turns approved GitHub Release packages into a normal APT source and a browsable software centre.

## Engineering ethos

What does it take to build a normal, inspectable APT source from first principles without making publication depend on opaque repository services? Package Repository owns the rules that discover, verify, retain and publish approved release artifacts.

APT, Debian metadata and GitHub releases define external interfaces the repository must interoperate with; they do not own this project's publication policy. Repository state, package selection, retention, catalogue generation, verification and release materialisation remain first-party behaviour. Small external command-line tools may provide replaceable mechanisms, while the semantics that decide what is published stay in this source tree and are regression-tested.

The project values deterministic, explainable publication over novelty. A new dependency or workflow is adopted only when it improves correctness, resilience, security or maintainability without surrendering the repository's source of truth.

## Current applications

- System Monitor
- System Settings
- Software
- Calendar
- Defragmenter
- InfiltratorFS
- Calculator
- MBLINK
- JAGLINK
- FORDLINK
- AUDILINK
- BMWLINK
- Egypt
- WHERE'S WALLY
- Intune Zabbix Bridge
- Runner Monitor
- Backyard Racer

InfiltratorFS also publishes three separately versioned support packages through the same repository: Desktop Integration, GNOME Disks Integration and libblockdev Integration.

The allow-list lives in `catalogue/apps-source.json`. A catalogue application is published only when a release contains exactly the expected primary `.deb` asset. Product-owned supplemental `.deb` packages may also be declared for APT-only publication; they are independently verified and indexed without creating duplicate Software Centre cards. Entries marked pending remain hidden until their first eligible release appears. Multi-package releases can declare an asset-version extraction rule so every Debian package is validated against its own package version rather than being assumed to share the parent release tag.

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

The primary beta suite is:

```text
deb [trusted=yes arch=amd64] https://infiltrator-projects.github.io/Infiltrator-Repository beta main
```

The Software Centre setup command normalises earlier repository entries without editing unrelated APT sources. It removes only lines that reference either the pre-organisation or current Infiltrator repository URL, then writes exactly one current beta entry. This makes repeated setup safe and prevents unsigned-to-signed transitions from leaving conflicting APT options:

```bash
OLD='https://the-first-infiltrator.github.io/Infiltrator-Repository'
NEW='https://infiltrator-projects.github.io/Infiltrator-Repository'
for f in /etc/apt/sources.list /etc/apt/sources.list.d/*.list; do
  [ -f "$f" ] || continue
  sudo sed -i -e "\\#$OLD#d" -e "\\#$NEW#d" "$f"
done
echo 'deb [trusted=yes arch=amd64] https://infiltrator-projects.github.io/Infiltrator-Repository beta main' \
  | sudo tee /etc/apt/sources.list.d/infiltrator-beta.list
sudo apt update
sudo rm -f /var/cache/mintinstall/pkginfo.json
rm -f "$HOME/.cache/mintinstall/pkginfo.json"
```

Linux Mint Software Manager keeps its own package cache. The setup command invalidates both the system and invoking user's Mint Software Manager caches after refreshing APT so newly added or renamed repository applications are rebuilt from the current APT package set. No repository metadata package is installed.

The repository publishes only the `beta` suite. The former `alpha` suite is not published or aliased. The `stable` suite is deliberately reserved for a future stable channel and is not published as a beta alias.

## Signing readiness

No private signing key is stored in this repository.

The publisher supports optional GitHub Actions secrets:

- `APT_SIGNING_KEY_B64` — base64-encoded private OpenPGP signing key;
- `APT_SIGNING_KEY_FINGERPRINT` — exact fingerprint to use;
- `APT_SIGNING_PASSPHRASE` — optional key passphrase.

When configured, the build creates `InRelease`, `Release.gpg` and `repository-key.gpg`. The web software centre automatically changes its installation instructions from `trusted=yes` to a dedicated `signed-by=` keyring.

Until those secrets are deliberately configured, the site clearly identifies the repository as an unsigned beta.

A local helper is provided at `scripts/create-signing-key.sh`. It creates a dedicated two-year APT signing key outside the repository and writes the two values that must be added as GitHub Actions secrets. The private key output must never be committed to Git.

## Validation

Release automation is built as a portable C++17 command-line tool
(`scripts/repository-tool.cpp`). GitHub Actions compiles it with the system
compiler and uses it for verified Intune mirroring and private-payload
materialisation. The tool consumes generic primitives from Common where the contract is product-neutral: output escaping and durable file publication belong to Common, while Debian/APT metadata, GitHub release discovery, retention, signing, mirroring and catalogue semantics remain local to this repository. The static Software Centre consumes Common's neutral web design adapter but keeps repository-specific status and package presentation locally. Pages artifact deployment is delegated to Common's reusable deployment action. It uses `curl`, `jq`, `sha256sum`, `base64`, and `dpkg-deb`
from the runner rather than embedding protocol or Debian implementations.
The production release path is C++17. The former Python publisher, mirror
materialiser and Intune synchroniser have been removed rather than retained as
a second implementation. Regression tests invoke the compiled C++ executable,
so a green workflow validates the code that actually publishes the repository.

The `publish` command performs release discovery, authenticated GitHub API
access when `GITHUB_TOKEN` is available, published-mirror reuse, asset/hash
validation, five-version retention, catalogue generation, package indexing,
by-hash metadata, generated timestamps, and optional OpenPGP signing.
`dpkg-scanpackages`, `apt-ftparchive`, `curl`, `jq`, and GnuPG remain
distribution tools invoked by the C++ executable.

`site/index.html` remains a static GitHub Pages application. It is copied into
the generated Pages artifact; converting it into a server-side C++ page would
break offline/static hosting and is neither necessary nor supported.

Every non-scheduled publish runs the signing self-test. The heavier Mint lifecycle test runs on manual workflow dispatch, or on an explicitly tagged promotion push containing `[mint-e2e]`, after publication succeeds.

The signing self-test creates a disposable CI-only OpenPGP key, signs the `beta` suite through the real repository signing code, imports the generated public key into a fresh keyring and verifies both `InRelease` and `Release.gpg`.

The Mint lifecycle test downloads the Linux Mint 22.3 Cinnamon ISO from the kernel.org Linux Mint mirror, verifies the ISO against its published SHA-256 list, extracts the genuine Mint `filesystem.squashfs`, and performs APT testing inside that clean Mint userspace. It checks repository discovery for the published package set, installs an older System Monitor and upgrades it to the current version, installs and removes the standard desktop applications, and runs `apt-get check` throughout. InfiltratorFS is dependency-resolved but not kernel-loaded in the chroot because DKMS runtime validation requires a booted Mint kernel. WHERE'S WALLY and Intune Zabbix Bridge are retrieved and Debian-metadata validated because complete installation also requires external Zabbix packages.

## Runner placement

Repository publication, signing checks and the Mint chroot test use GitHub-hosted `ubuntu-latest` runners. They do not occupy the organisation’s self-hosted Linux desktop runners. An idle desktop runner monitor does not mean repository publication has stopped; check this repository’s Actions runs.

## Publication

GitHub Actions publishes on pushes to this repository's `main`, on manual request and from its own five-minute pull schedule using GitHub's canonical `*/5` cron form. A central `main` push also acts as an immediate pull refresh when a newly released application must be indexed without waiting for GitHub's scheduled-run queue; this is the supported forced-refresh path when scheduled publication is delayed. Application repositories do not push or dispatch publication into this repository. Intune Zabbix Bridge is public and its release mirror is pulled and SHA-256/package-metadata verified without a PAT or cross-repository secret before publication. Scheduled runs refresh packages without re-downloading the multi-gigabyte Mint ISO; the signing self-test runs on non-scheduled publication, while the Mint lifecycle test runs only on manual dispatch.

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

## Website family contract

The Software Centre is the distribution surface of the same website family as `ssmithnet.net`. Publication pins the family source at `ssmithnet.net` commit `7cd6a749f1e2dff23300c3bcf071e733bffc0475` and copies its self-contained typography, graphics and interaction layer into the Pages artifact. The shared acceptance test from that same immutable commit checks canonical metadata, landmarks, navigation, local assets and the three real Corpo font files.

Infiltratr Common 1.19.35 (`7cc5de3de0e94ed2cfcff0840bbb5346eb5c9c9f`) remains the lower-level neutral design/infrastructure dependency. Package Repository owns catalogue behaviour, APT setup and package presentation. Application icons are extracted from the verified current DEB when the package contains a standard application icon, so a released icon update follows the package rather than a separate website illustration map; the compact built-in symbols are only a fallback for packages without a GUI icon.
