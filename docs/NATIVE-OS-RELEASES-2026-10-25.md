# Native InfiltratorOS application integration — 2026-10-25

This release-coordination record identifies the exact independently published
application packages that accompany the InfiltratorOS native namespace migration.
It is not a claim of physical Mint/Debian host qualification.

| Project | Released tag | Expected package |
| --- | --- | --- |
| InfiltratorOS | [v1.0.27](https://github.com/Infiltrator-Projects/InfiltratorOS/releases/tag/v1.0.27) | `infiltratoros_1.0.27_amd64.deb` |
| Files | [v0.1.71](https://github.com/Infiltrator-Projects/Files/releases/tag/v0.1.71) | `files_0.1.71_amd64.deb` |
| Calculator | [v0.2.60](https://github.com/Infiltrator-Projects/Calculator/releases/tag/v0.2.60) | `calculator_0.2.60_amd64.deb` |
| Defragmenter | [v1.8.0-274](https://github.com/Infiltrator-Projects/Defragmenter/releases/tag/v1.8.0-274) | `Defragmenter-1.8.0-274-amd64.deb` |

InfiltratorOS 1.0.27 also depends on separately published Calendar 1.0.125
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
upgrade cannot complete; the local retry requires only the Files worker.
