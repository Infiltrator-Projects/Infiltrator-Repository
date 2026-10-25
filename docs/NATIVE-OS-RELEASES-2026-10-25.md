# Native InfiltratorOS application integration — 2026-10-25

This release-coordination record identifies the exact independently published
application packages that accompany the InfiltratorOS native namespace migration.
It is not a claim of physical Mint/Debian host qualification.

| Project | Released tag | Expected package |
| --- | --- | --- |
| InfiltratorOS | [v1.0.31](https://github.com/Infiltrator-Projects/InfiltratorOS/releases/tag/v1.0.31) | `infiltratoros_1.0.31_amd64.deb` |
| Files | [v0.1.71](https://github.com/Infiltrator-Projects/Files/releases/tag/v0.1.71) | `files_0.1.71_amd64.deb` |
| Calculator | [v0.2.60](https://github.com/Infiltrator-Projects/Calculator/releases/tag/v0.2.60) | `calculator_0.2.60_amd64.deb` |
| Defragmenter | [v1.8.0-274](https://github.com/Infiltrator-Projects/Defragmenter/releases/tag/v1.8.0-274) | `Defragmenter-1.8.0-274-amd64.deb` |

InfiltratorOS 1.0.31 also depends on separately published Calendar 1.0.125
and `infiltrator-calendar-resources` 1.19.75.

The InfiltratorOS Debian payload constructs `/System`, `/Programs`,
`/Users`, `/Volumes`, and `/Temporary` during package unpack,
before its post-installation workers run. Files, Calculator and Defragmenter
are independently versioned, installed, and validated under the native layout.
Files remains an additional file manager until it is feature-complete:
Nemo/default handlers and MIME associations must not be changed or purged.
Calendar's Cinnamon panel applet replacement is per-user, reversible and
preserves the original desktop calendar package.

Each linked release has public GitHub assets and qualified source/build
artifacts; the source repositories' individual release tests govern them.
The central signed beta APT index must be republished and independently checked
for each exact Debian version and SHA-256 before treating repository delivery
as complete. Physical reinstall and boot qualification on the target Mint
machine remain separate from CI and repository publication.

## Mint native installer prerequisite correction

The first physical InfiltratorOS 1.0.27 install exposed a Files 0.1.70
native-build dependency probe omission: LibArchive headers and the linker
library were missing, despite GTK 4 prerequisites being available. Files
0.1.71 fixes the `libarchive-dev` probe before CMake and includes a CI
regression test that hides LibArchive while keeping GTK discoverable.
The previously installed Files package and Nemo remain intact if its native
upgrade cannot complete. Reinstalling InfiltratorOS from its published GitHub
release now retries the native installation through the canonical OS setup
process; no permanent per-product installer launchers are retained.

## One installation entry point; no leftover application installers

InfiltratorOS 1.0.29 corrects the prior 1.0.27 package architecture that
left twelve per-product installation launchers, workers and progress windows
under `/System/Commands/InfiltratorOS` after installation. The latest
InfiltratorOS release packages those internal processes in one checksum-verified
Debian post-install script, stages them temporarily under `/run/infiltratoros`
and deletes the staged executables when the four application builds reach
terminal status. All intentional native resources and integration helpers are
unchanged. Debian's package upgrade removes the twelve obsolete package-owned
`/System` executable files without manual deletion. The full package data
payload contains 34 regular files instead of 46. Source/runtime validation is
green, but physical installation on the target Mint host remains to be proven.

## Mint /run noexec native installer fix

The initial physical Mint attempt to install InfiltratorOS 1.0.29 failed verifying its native installer executables because executable workers had been staged under `/run` on a host where `/run` may be mounted `noexec`. Published InfiltratorOS 1.0.30 keeps status under `/run` but stages executable binaries under the host's executable `/var/lib` filesystem in a transient `infiltratoros-native-worker.*` directory, which is cleaned up after installations terminate. This patch does not change the permanent file layout, `/Volumes`, application replacement policy or shared resource contents. A physical retest on the Latitude Mint host is still required. When the host's `/System` hierarchy was manually cleared, `calendar` and `infiltrator-calendar-resources` remained installed in dpkg and need package reinstallation to restore package-owned native calendar/clock resources.

## 1.0.31 — Restore canonical native temporary layout

The revised package routes all **InfiltratorOS-owned temporary installation state** (verified temporary worker binaries, worker downloads, statuses, diagnostic logs and lockfiles) through `/Temporary/InfiltratorOS`. This temporary native directory is created **before** fonts/icons and the four app workers are started; `TMPDIR` is exported for setup and worker processes. No InfiltratorOS-owned files are staged under `/run`, `/run/lock`, `/var/lib`, `/var/log`, or `/tmp` (Linux's own dpkg/XDG interoperability is unchanged). The prior 1.0.30 Linux-path workaround is superseded and is **not recommended for the user's native-layout reinstall**. The published 1.0.31 package SHA-256 is `8b64b741062f7bcdb6927af8f9fa2e2bfead4a67c477b179ce61ee265d8cdd55`. `/Volumes` is preserved, and the 34 permanent InfiltratorOS package files, app distribution policies and Nemo coexistence do not change. Physical installation on the Dell Latitude Mint system remains to be proven.
