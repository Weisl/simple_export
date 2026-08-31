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

This release adds a "Create Instance Collection" tool for grouping objects
for instancing, fixes an export-preset regression on Blender 4.2–4.4, adds
Blender 5.2 export preset support, restructures the test suite, and
hardens the pre-export transform-baking pipeline against mesh corruption.

### Features & Improvements

- [#309](https://github.com/Weisl/simple_export/issues/309): **Create
  Instance Collection** — new operator (also available from the 3D viewport
  object context menu) that groups the current selection into a new
  collection with a root empty, ready to be used as a Collection Instance.
- New animated-character presets for all three engines, alongside their
  existing static-mesh-only presets: `Unity-animation` / `Unity-animation-fbx`,
  `UE-animation` / `UE-animation-fbx`, and `Godot-animation` /
  `Godot-animation-gltf`. Each bakes every Action as its own take/clip
  instead of exporting a static pose (FBX: `bake_anim: True`,
  `bake_anim_use_all_actions: True`, `bake_anim_use_nla_strips: False`;
  glTF: `export_animations: True` with the already-correct
  `export_animation_mode: 'ACTIONS'`). All three presets were validated
  end-to-end (export → import → numeric skeleton/skin/animation checks
  against a real Unity/Godot/Unreal project, not just "it imported without
  erroring").
- Added a dedicated `blender_5_2` export preset folder alongside the
  existing 4.2/4.5 folders, ensuring correct defaults on Blender 5.2.

### Bug Fixes

- [#318](https://github.com/Weisl/simple_export/issues/318): Export collections
  that keep their geometry in **sub-collections** (only a
  root empty, or nothing, linked directly) are now handled correctly
  everywhere. Previously several code paths looked only at objects linked
  *directly* to the collection (`collection.objects`) instead of the whole
  hierarchy (`collection.all_objects`), so such a collection got a bogus
  "No mesh objects (types present: EMPTY)" warning, had its nested meshes
  skipped by every per-object validation check and by the triangle-count
  budget, and had the "Apply Scale/Rotation/Transform", "Pre-Rotate Objects"
  and "Collection Offset" pre-export operations silently do nothing to the
  nested meshes. Validation, warnings, and all pre-export operations now walk
  the full collection hierarchy.
- [#319](https://github.com/Weisl/simple_export/issues/319): A collection that is
  **excluded from the view layer** (its Outliner checkbox
  unticked — which also stops it rendering) no longer fails to export.
  Blender's collection exporters only see view-layer collections, so the
  export silently wrote nothing (or, worse, fell through to whichever
  collection happened to be active and exported *that* one to the excluded
  collection's path). The collection (and any excluded ancestor) is now
  temporarily re-included for the duration of the export, restored afterwards,
  and the export succeeds with a warning. A guard also now aborts loudly if
  the target collection can't be made active, instead of exporting the wrong
  one.
- "All objects are excluded from render" is now a **warning**, not an error:
  the FBX/glTF/USD exporters still write render-hidden objects, so the export
  proceeds and produces a valid file. It was already non-blocking at export
  time; this just stops it showing as a red error in the Validate panel.
- Fixed `apply_triangulate_modifiers` (pre-export triangulation) baking an
  armature-deformed mesh at its *currently posed* shape instead of its rest
  pose, then getting deformed a second time by the FBX exporter's own
  skin-cluster handling — which ignores the modifier-visibility suppression
  this step relies on for every other modifier. Visible as body parts
  (fingers worst, since they're typically posed far from rest) rendering up
  to ~0.9m from their own skeleton once imported into a game engine.
  Armature modifiers are now disabled specifically during the triangulation
  bake so only triangulation gets baked. See
  `docs/animated-character-export-notes.md` for the full investigation,
  including a residual, not-yet-root-caused ~0.4m gap on some limbs that
  predates this fix and isn't introduced by the addon.
- [#310](https://github.com/Weisl/simple_export/issues/310): Fixed the
  **Godot-gltf** export preset breaking Blender's native preset loader on
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

### Internal

- Restructured the test suite — Blender-dependent tests moved into
  `tests/blender/`, the magic-mock-based `bpy` stub was removed, and a
  dedicated preset-application test module was added.

### Known limitations

- FBX exports via Unity specifically can still show a real, unexplained
  skin-binding gap (bone-to-vertex offset up to ~0.4m) on some limbs,
  independent of any `simple_export` setting — reproduced even by a raw FBX
  export bypassing the addon entirely. Not yet root-caused, but now believed
  to be Unity-importer/Avatar-system-specific rather than a general FBX or
  rig issue: both the equivalent glTF/Godot path (<0.14m) and a follow-up
  Unreal/FBX validation (<0.05m, same file format as the Unity case) show
  the same rig without the large gap. See
  `docs/animated-character-export-notes.md`.
- Unreal's plain FBX skeletal-mesh importer defaults **Convert Scene Unit**
  to off, which imports a Blender-exported animated character at 1/100th
  its intended scale unless enabled manually during import. Confirmed to be
  an Unreal import-default issue, not a `simple_export` export bug (the
  exported FBX re-imports into Blender at the correct scale) — see the
  Import steps in `exporter_guide_unreal.md` and
  `docs/animated-character-export-notes.md` for the full investigation,
  including why baking the scale on the Blender export side
  (`bake_space_transform`) was tried and rejected (it drops all but one
  Action from the export).
- [#311](https://github.com/Weisl/simple_export/issues/311): `Lowpoly-fbx`
  and `Highpoly-fbx` still embed Blender-calculated tangent space
  (`use_tspace: True`), which can produce incorrect baked normal maps when
  the high-poly source has ngons. Not yet fixed.

