# Animated character export: findings and open issues

Notes from an end-to-end validation of the Blender → Unity animation export
pipeline, using the `combat_character.blend` fixture (armature + skinned
mesh + 14 baked actions). Captured here so the root causes and the ones that
turned out to be dead ends aren't re-discovered from scratch.

## Symptom

A character exported with `bake_anim: True` and imported into Unity showed
specific body parts (initially reported as "floating fingers") rendering far
from their own skeleton — a `SkinnedMeshRenderer` vertex strongly weighted to
a given bone could sit up to ~0.9m away from that bone's actual position,
even though the bone transforms themselves were always correct. Whole-mesh
bounding-box checks alone did not surface this: the corruption is confined to
a fraction of the vertices, so the overall silhouette still looked roughly
human-sized.

Diagnostic method that worked reliably: bake the live `SkinnedMeshRenderer`
via `SkinnedMeshRenderer.BakeMesh()`, cross-reference each vertex's dominant
`BoneWeight` against that bone's actual `Transform.position`, and take the
max per-bone gap. This is far more sensitive than bounding-box or
silhouette checks, which can look "fine" even with a badly broken rig.

## Confirmed root cause: `apply_triangulate_modifiers` double-deforms armature-skinned meshes

**File:** `functions/pre_export_ops.py`

The pre-export triangulation step bakes a new mesh via
`bpy.data.meshes.new_from_object(eval_obj)`, evaluating the object's full
modifier stack — including its Armature modifier — at whatever pose the
scene happened to be at when export ran. That bakes the *currently posed*
shape into static vertex data. The code then hid every modifier
(`show_viewport = show_render = False`) so the exporter wouldn't apply them
again — but Blender's FBX exporter detects an Armature modifier and its
matching vertex groups directly, independent of `show_viewport`/`show_render`,
and still builds skin-cluster/bind-pose data from it. Net effect: the
already-posed mesh gets deformed a **second time** during export.

The error is proportional to how far each bone sits from rest at the moment
export runs — small for bones close to rest (torso/spine), large for bones
posed far from rest (fingers, which are typically curled in a fist at rest
in this fixture's `Idle_Loop` frame 1).

**Fix:** temporarily disable Armature modifiers specifically *during* the
triangulation bake (not just after), so only triangulation gets baked and
the mesh stays in true bind pose with valid vertex groups for the exporter
to deform exactly once.

Confirmed with the real preset defaults (`triangulate_before_export: True`):
finger gaps dropped from ~0.90–0.94m to ~0.03m, matching a raw
`bpy.ops.export_scene.fbx()` call that bypasses triangulation entirely.

## Ruled out: armature object-level transform

Initial hypothesis was that the armature's non-identity `matrix_world` (a
leftover axis-conversion rotation from Blender's FBX importer, common when a
rig is sourced from a marketplace asset — this fixture's is a 180° Z
rotation) corrupts bind-pose baking once animation is exported, based on
research into `bake_space_transform` being documented as broken for
armatures+animation.

This was **empirically disproven**: exporting with the armature transform
explicitly baked (via a duplicated-datablock `transform_apply()`, non-
destructive to the source file) vs. left untouched produced **identical**
per-bone gap measurements. An implementation of this as an automatic
pre-export step was built, tested, and then fully reverted once it was clear
it fixed nothing — worse, it introduced a real regression: `transform_apply`
silently rewrites a non-selected child object's own `matrix_basis` in some
contexts rather than compensating `matrix_parent_inverse`, and the
restore logic only backed up/restored the latter, so it left the live scene
with the skinned mesh permanently misrotated after every export.

Lesson for next time: verify a fix moves the actual measured numbers before
building automation around it. "Sounds like a known Blender/FBX gotcha, and
the docs support it" is not the same as "measured before/after and the gap
changed."

## Still open: residual ~0.4m gap on some limbs, cause unknown

Even with the triangulate fix applied and the armature-transform code fully
reverted, a real gap remains on `calf_l/r` (~0.44m), `thigh_l/r` (~0.41m),
and `upperarm_l/r` (~0.29m) — present under the addon's default preset
settings, **and** reproduced by a raw `bpy.ops.export_scene.fbx()` call that
bypasses the addon's entire pre-export pipeline. This means the remaining
gap is not something `simple_export` introduces — it's inherent to how
Blender's FBX exporter (or Unity's importer) handles this rig/pose/setting
combination.

Ruled out so far: `use_deform` is `True` on every bone in the affected
chains (not an excluded-bone issue); `move_by_collection_offset` (offset was
zero, and toggling it made no difference); `use_active_collection` vs plain
selection-based export (toggling made results *worse*, not better,
suggesting it changed export scope rather than isolating a variable
cleanly).

Not yet tried: bisecting `primary_bone_axis`/`secondary_bone_axis`,
`bake_anim_use_all_bones`, `use_armature_deform_only`, and `add_leaf_bones`
individually against the raw-export baseline; comparing against a
Humanoid-rig avatar instead of Generic; testing whether the gap is specific
to this fixture's particular rest-pose vs. a plain T-pose rig.

## Unity-side setup gap (unrelated to the above, also confirmed)

Unity's `ModelImporter` defaults to `avatarSetup: NoAvatar` even when
`animationType: Generic`, so a freshly imported animated FBX gets **no**
`Animator` or `Avatar` component attached automatically — the clips exist
but nothing can play them until you manually set the FBX's Rig import tab to
`Avatar Definition: Create From This Model` and reimport. This is a Unity
importer default that no Blender-side export setting can reach; there is no
`simple_export` fix for it, only documentation. Unity also never
auto-generates an `AnimatorController` — one has to be created and clips
assigned to it before anything will play at runtime (as opposed to
edit-time `AnimationMode` preview).

## What shipped as a result

- `functions/pre_export_ops.py`: `apply_triangulate_modifiers` fix described
  above (the one confirmed, verified change). It's format-agnostic — this
  step runs before *any* exporter (FBX/glTF/USD/Alembic), so it fixes the
  same double-deformation for Godot and Unreal exports too, automatically,
  with no format-specific work needed.
- New `Unity-animation` / `Unity-animation-fbx` presets (addon + FBX-format
  level) alongside the existing static-mesh-only `Unity-default` /
  `Unity-fbx`: `bake_anim: True`, `bake_anim_use_nla_strips: False`,
  `bake_anim_use_all_actions: True` — every Action exports as its own take
  instead of being silently dropped.
- The same pattern applied to the other two engines, each using its format's
  own equivalent of "bake every Action as a separate take":
  - `UE-animation` / `UE-animation-fbx` (FBX) — same three `bake_anim*`
    fields as Unity's; everything else (axis convention, `add_leaf_bones:
    False`, `use_armature_deform_only: False`) stays exactly as `UE-fbx`
    already had it, since those are format/engine conventions unrelated to
    animation.
  - `Godot-animation` / `Godot-animation-gltf` (glTF) — glTF's animation
    toggle is `export_animations` (equivalent to FBX's `bake_anim`), and
    `export_animation_mode: 'ACTIONS'` was already correctly set on the
    static preset (exports each Action as its own glTF animation, the glTF
    equivalent of `bake_anim_use_all_actions: True` +
    `bake_anim_use_nla_strips: False`) — so the only change needed was
    flipping `export_animations` to `True`. Each of the 5 per-Blender-version
    files has its own slightly different property set (older exporter
    versions lack some fields — see the version-gated-properties comment
    already in `blender_4_2/preset_data_gltf.py` from a past bug, #310); the
    new preset was built by duplicating each file's own existing block
    rather than templating from one version, so that per-file property set
    is preserved exactly.
- None of the above touches the still-open residual gap or the Unity avatar-
  setup gap described above — those aren't addon bugs, so there's nothing in
  the presets that can fix them. The Unity avatar-setup step and the
  `AnimatorController`-creation step have direct equivalents worth checking
  for Godot (Import dock → skeleton/animation settings) and Unreal (Skeleton
  asset creation, Animation Blueprint setup) — not yet investigated for
  either engine.
