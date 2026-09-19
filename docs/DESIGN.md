# Design

## First-principles position

The repository is designed around one question: what is required to turn independently released software into a normal, inspectable APT source without making an opaque hosted service the source of publication policy?

The answer is deliberately small: first-party policy code, standard Debian package semantics, deterministic static output and replaceable external mechanisms.

## Design goals

- deterministic repository materialisation from immutable upstream release identities;
- normal APT behaviour rather than a custom updater protocol;
- explicit retention rather than accidental "latest only" state;
- package metadata and checksum verification before publication;
- publication that can be inspected and reproduced on an ordinary Debian-family system;
- one resolved package state feeding both APT metadata and the software catalogue.

## Dependency philosophy

The project does not reimplement HTTP, Debian package parsing or OpenPGP simply to avoid all external commands. It uses mature system tools where their contract is stronger and more authoritative than a private implementation.

That does not surrender policy ownership. `curl` may retrieve bytes, but it does not decide which release is acceptable. `dpkg-deb` may read fields, but it does not decide retention. GitHub may host a release, but it does not decide whether that release enters the repository.

## Failure model

Publication fails closed on mismatched package/version/architecture metadata, missing required assets, checksum failure, malformed catalogue input or signing failure.

Temporary command output is not repository state. Durable publication occurs only after validation and generation succeed.

## Security and trust

Release asset identity, package metadata and signatures form separate trust layers. A package being downloadable does not mean it is acceptable; a package having the expected filename does not mean its internal metadata matches; an unsigned repository is not represented as signed.

## Static-site rule

The software centre is presentation over resolved repository state. It must not contain a second version-selection algorithm that can disagree with the APT repository.

## Quality rule

A change is acceptable when it improves correctness, resilience, inspectability, security or maintainability. Replacing a stable Debian mechanism with a fashionable framework is not an improvement by itself.
