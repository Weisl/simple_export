# Changelog

All notable changes to Simple Export are documented here. Dates are set when
a version is actually tagged/released.

Each new release is added as a new section above the previous one — existing
entries are never overwritten, so this file accumulates the full release
history over time.

## Simple Export v0.8.2 (Unreleased)

This release adds a "Create Instance Collection" tool for grouping objects
for instancing, fixes an export-preset regression on Blender 4.2–4.4, and
hardens the pre-export transform-baking pipeline against mesh corruption.

### Features & Improvements

- [#309](https://github.com/Weisl/simple_export/issues/309): **Create
  Instance Collection** — new operator (also available from the 3D viewport
  object context menu) that groups the current selection into a new
  collection with a root empty, ready to be used as a Collection Instance.

### Bug Fixes

- [#310](https://github.com/Weisl/simple_export/issues/310): Fixed the
  `Godot-gltf` export preset breaking Blender's native preset loader on
  Blender 4.2–4.4 — four version-gated glTF properties aborted the loader's
  `exec()` partway through, silently dropping ~90 subsequent properties.
  Export presets are now split per Blender line (`blender_4_2`,
  `blender_4_5`, and a new `blender_5_2` tier) with version-gated properties
  ordered last so unrelated properties still apply.
- [#306](https://github.com/Weisl/simple_export/issues/306): Fixed mesh data
  corruption and thread-safety issues in the pre-export pipeline: a failure
  mid-bake during scale/rotation/transform baking could orphan a mesh
  datablock or leave the object partially transformed; backups were keyed by
  the object's (mutable) name, so a rename between apply and restore could
  restore the wrong object; and the background "update available" check
  could keep writing its result after the addon had been unregistered.

### Known limitations

- [#311](https://github.com/Weisl/simple_export/issues/311): `Lowpoly-fbx`
  and `Highpoly-fbx` still embed Blender-calculated tangent space
  (`use_tspace: True`), which can produce incorrect baked normal maps when
  the high-poly source has ngons. Not yet fixed.
