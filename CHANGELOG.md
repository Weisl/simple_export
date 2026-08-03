# Changelog

All notable changes to Simple Export are documented here. Dates are set when
a version is actually tagged/released.

Each version below mirrors the structure used on the
[documentation site's release notes page](https://weisl.github.io/simple_export/exporter_release_notes/):
a short summary of the release, followed by "Features & Improvements" and
"Bug Fixes" lists whose entries link back to their GitHub issue. New releases
are added as a new section above the previous one — existing entries are
never overwritten, so this file (like the docs page) accumulates the full
release history over time.

## Simple Export v0.8.2 (Unreleased)

This release fixes the Godot-gltf export preset on Blender 4.2–4.4, adds
Blender 5.2 export preset support, and restructures the test suite.

### Features & Improvements

- Added a dedicated `blender_5_2` export preset folder alongside the
  existing 4.2/4.5 folders, ensuring correct defaults on Blender 5.2.

### Bug Fixes

- [#310](https://github.com/Weisl/simple_export/issues/310): Fixed the
  **Godot-gltf** export preset breaking Blender's native preset loader on
  Blender 4.2–4.4. Four glTF properties referenced by the preset don't exist
  yet on those point releases, and Blender's native, exec-based preset
  loader aborts on the first unrecognized property — silently dropping
  roughly 90 subsequent properties instead of just the unsupported one.
  Split the preset folder into version-gated `blender_4_2`/`blender_4_5`
  buckets and reordered the version-gated properties to the end of the
  4.2–4.4 preset so every other property still applies.

### Internal

- Restructured the test suite — Blender-dependent tests moved into
  `tests/blender/`, the magic-mock-based `bpy` stub was removed, and a
  dedicated preset-application test module was added.
