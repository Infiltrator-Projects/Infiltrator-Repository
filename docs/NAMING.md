# Product and publication names

Use one human-facing product name in the application, README, GitHub repository,
release title and download names. Spaces become hyphens where a filename needs
them. Debian package identifiers are lowercase. Release tags remain `v<version>`.

| Product | Repository | Debian package |
| --- | --- | --- |
| Libraries | Libraries | Source library release |
| Calendar | Calendar | calendar |
| Slicer | Slicer | slicer |
| Calculator | Calculator | calculator |
| Software | Software | software |
| Defragmenter | Defragmenter | defragmenter |
| Files | Files | files |
| System Settings | System-Settings | system-settings |
| System Monitor | System-Monitor | system-monitor |
| RunnerScope | RunnerScope | runnerscope |
| Character Profiler | Character-Profiler | iPhone application |
| Link | Link | Shared automotive library |
| MBLink | MBLink | mblink |
| JAGLink | JAGLink | jaglink |
| BMWLink | BMWLink | bmwlink |
| AUDILink | AUDILink | audilink |
| FORDLink | FORDLink | fordlink |

Manufacturer abbreviations are uppercase and the suffix is always `Link`.
The shared product is `Link`. InfiltratorFS and InfiltratorOS retain their
established product names.

`catalogue/apps-source.json` declares each current package identity and its
legacy package names. Retained historical artifacts keep their original names
and bytes. Once a canonical package is published, empty versioned transition
packages upgrade installations from previous package names into that package.
Compatibility packages do not create additional catalogue cards or launchers.
The publisher never generates a transition back into an obsolete name.

Stable application IDs, bundle identifiers, saved-data paths, C/CMake APIs,
service names and compatibility executable names can retain historical
identifiers. They must not replace the human-facing product name or the current
published package identity. Published release tags and artifact bytes remain
immutable; naming changes ship in a new qualified release.
