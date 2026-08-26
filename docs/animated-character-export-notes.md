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

## Godot pipeline validated end-to-end (follow-up session)

A later session ran the same validation for Godot: exported `combat_character.blend` via the real
`Godot-animation` addon preset (`export_animations: True` is the only difference from `Godot-gltf`/`Godot-default`,
confirmed by diffing the preset dicts for the running Blender version), imported into a real Godot 4.7.1 project,
and verified numerically rather than by eyeballing the viewport.

**Method** (Godot has no MCP equivalent of Unity's arbitrary-C#-execution tool, so verification code was written as
a GDScript run headlessly via `godot --headless --path <project> <verify_scene>.tscn`, with `mcp__godot__launch_editor`
used first so the *real* editor performed the asset import, matching what a user would get):

- Skeleton rest-pose bone positions: compared Blender's `bone.matrix_local` (world space) against Godot's
  `Skeleton3D.get_bone_global_pose()`, converting Blender's Z-up to glTF/Godot's Y-up via `(x,y,z) -> (x,z,-y)`.
  Matched to ~1e-6 m across all 65 bones — this also served as calibration proof that the axis-conversion formula
  and general method were correct before trusting anything less trivially checkable.
- Skin binding (does the mesh follow the right bone): initial attempt mapped each vertex's dominant `ARRAY_BONES`
  index through `Skin.get_bind_name()`/`get_bind_bone()` and got a spurious ~1.9 m left/right-mirrored gap on every
  symmetric limb bone. Cross-checked by parsing the exported `.gltf`+`.bin` directly in Python (bypassing Godot
  entirely) — the raw file was correct, proving the ~1.9 m gap was a bug in the verification script's assumption
  about how Godot's importer indexes `ARRAY_BONES` per surface, not a real pipeline bug. Switched to an
  index-assumption-free method (classify each vertex by nearest rest-pose bone, geometry only) and got a max gap of
  0.14 m, consistent with the raw-glTF cross-check. Lesson repeated from the Unity session: a measurement showing a
  large gap is exactly as likely to indicate a bug in the measurement as a bug in the pipeline — cross-check with an
  independent method before concluding either way.
- Animation playback: sampled 5 (action, frame) pairs across 15 bones each (75 comparisons), seeking Godot's
  `AnimationPlayer` to the equivalent time and reading `Skeleton3D.get_bone_global_pose()`, against Blender's
  depsgraph-evaluated pose at the matching frame. Max gap 0.072 m (one bone, one frame, likely time-quantization
  between Blender's frame-stepped evaluation and Godot's continuous interpolation), everything else sub-centimeter.

**Result: no addon bug found.** The existing `apply_triangulate_modifiers` fix (see above) protects the glTF/Godot
path exactly as expected, with no additional work needed.

**New data point on the still-open residual gap**: the same rig's `calf_l/r` and `thigh_l/r` showed <0.01 m gaps
via Godot/glTF (vs. ~0.4–0.44 m via FBX/Unity), and `upperarm_l/r` showed ~0.10 m (vs. ~0.29 m via FBX/Unity). This
is evidence the residual gap is FBX/Unity-specific rather than a general Blender-rig issue, consistent with the
Unity notes' suspicion.

**Godot-side import quirks worth documenting for users** (both real Godot importer behavior, not addon-controlled,
so nothing to fix — just to explain in user docs, see `exporter_guide_godot.md`):

- Unlike Unity's "Avatar Definition defaults to No Avatar" trap, Godot's glTF importer imports animations and wires
  up `Skeleton3D`/`MeshInstance3D`/`AnimationPlayer` automatically with no manual import-settings step required.
- Godot's importer treats an `_Loop`/`-loop` suffix on an animation name as a looping convention: `Idle_Loop`
  imports as `AnimationPlayer` entry `Idle` with `loop_mode` automatically set to `LOOP_LINEAR`; names without that
  suffix import unchanged with `loop_mode = LOOP_NONE`. Confirmed on all 4 of the fixture's `_Loop`-suffixed actions
  (`Idle_Loop`, `Walk_Loop`, `Sprint_Loop`, `Jump_Loop`) and no false positives on the other 10.

## Unreal pipeline validated end-to-end (follow-up session)

A later session ran the same validation for Unreal: exported `combat_character.blend` via the real `UE-animation`
addon preset (confirmed diff from `UE-fbx`: `bake_anim`/`bake_anim_use_nla_strips`/`bake_anim_use_all_actions`, the
same three-field pattern as Unity/Godot), imported into a real Unreal Engine 5.8.1 project, and verified numerically.

**Environment**: no Unreal MCP server existed at the start of the session; one was set up using Epic's own built-in
`ModelContextProtocol` plugin (UE 5.6+, experimental) plus the `AllToolsets` aggregator plugin for asset/editor
toolset coverage. The plugin's registered MCP toolsets (asset import, skeletal-mesh bone-hierarchy inspection,
screenshots, log reading) cover import + basic inspection, but expose no bone-*transform* query - so numeric
verification instead used Epic's officially-shipped Python remote-execution protocol
(`Engine/Plugins/Experimental/PythonScriptPlugin/Content/Python/remote_execution.py`), giving the same class of
arbitrary-code access the Unity session had via `Unity_RunCommand`. Getting that working surfaced one real,
environment-specific bug worth recording: on this machine, a UDP socket bound to a *specific* address (`127.0.0.1`,
the documented default for both Unreal's server and Epic's reference client) never receives multicast traffic,
even after successfully joining the multicast group - confirmed with an isolated, Unreal-independent send/receive
test. Binding to `0.0.0.0` (ANY) instead, on both the Unreal project's `RemoteExecutionMulticastBindAddress` setting
and the Python client's `multicast_bind_address` config, fixed it. Not an addon issue, but worth knowing if a future
session hits silent remote-execution discovery failures on Linux.

### Confirmed root cause: a ~100x scale-import bug, not a `simple_export` bug

The first real export/import round-trip produced a character importing at roughly 1/100th its intended size (a
~1.8m-tall character came in with a bounding-box half-extent of ~0.9 Unreal units, i.e. ~1.8cm tall). Isolated the
cause methodically rather than guessing:

1. Re-imported the exported FBX **back into Blender** (fresh scene, `bpy.ops.import_scene.fbx`) - it reproduced the
   original ~1.79m height exactly. This proved the FBX file itself is correctly scaled; the bug is entirely on
   Unreal's import side.
2. Confirmed via Unreal Engine 5.8 source (`Engine/Source/Editor/UnrealEd/Private/Fbx/FbxAssetImportData.cpp`) that
   `bConvertSceneUnit` defaults to `false` in the base `UFbxAssetImportData` constructor for a plain skeletal-mesh
   import (as opposed to `FbxSceneImportFactory`, the whole-scene importer, which explicitly forces it to `true`).
   This is a real, if easy-to-miss, Unreal import-dialog checkbox: **Convert Scene Unit**, under Miscellaneous.
3. Confirmed the fix empirically: re-imported the same FBX via a raw `unreal.AssetImportTask` +
   `unreal.FbxImportUI` with `skeletal_mesh_import_data.convert_scene_unit = True` (not exposed by the MCP
   toolset's `import_file` tool, which uses whichever import defaults Unreal already has - only reachable via
   Python/the Editor's own import dialog) - the character imported at exactly 178.6cm, matching Blender's own
   re-import to within rounding.
4. Root-caused *why* the default is wrong for this specific pipeline (not just "Unreal is being difficult"): with
   `Use Space Transform` disabled (the addon's setting, matching Blender's own default, `simple_export`'s FBX
   presets never turn it on), Blender's `apply_unit_scale` writes the correct x100 conversion as the FBX Armature
   node's `Lcl Scaling`, not baked into the vertex/bone local coordinates. Unreal's importer has a documented
   behavior (Unreal Engine Community Wiki, multiple Epic forum threads - see `exporter_guide_unreal.md`'s further
   references) of collapsing/stripping that node, losing the scale factor with it. `Convert Scene Unit` compensates
   for the lost factor rather than being a "real" double-conversion - which is also why enabling it does *not*
   produce a 100x-too-*big* character, contrary to what reading the Unreal source in isolation would suggest.

**Tried and rejected as a Blender-side alternative**: enabling `bake_space_transform` (Blender's "Apply Transform"
export option) *does* fix the scale with zero Unreal-side setting changes, and gives near-perfect bone accuracy (see
below) - but it silently drops 13 of the fixture's 14 Actions from the export, keeping only one, even with
`bake_anim_use_all_actions` correctly enabled on the exporter. This is a real, confirmed regression, not a
theoretical risk: Blender's own tooltip already flags this option as "known to be broken with armatures/animations",
and this investigation reproduces exactly that failure mode. **Do not enable `bake_space_transform` on the animated
presets** - the `Convert Scene Unit` Unreal-side fix, while less convenient (it requires user action outside
Blender), is the only one of the two that doesn't lose animation data. Left `UE-fbx`/`UE-animation` unchanged;
documented `Convert Scene Unit` as a required manual import step in `exporter_guide_unreal.md`, the same treatment
Unity's Avatar-setup trap already gets.

### Numeric verification

Skeleton/skin binding: captured Blender's *posed* world-space bone positions (`arm_obj.matrix_world @
pose_bone.matrix`, at the scene's current frame/action - **not** `bone.matrix_local`/edit-bone rest pose, which
turned out to read something different from what the FBX exporter embeds as the mesh's default pose; see the
methodology note below) for all 65 bones, and Unreal's equivalent (`SkeletalMeshComponent.get_bone_transform(name,
RTS_WORLD)` on a freshly spawned `SkeletalMeshActor` with no animation assigned). Least-squares-fit the axis/scale
mapping across all 65 bones rather than assuming the standard Blender-to-Unreal formula, confirming
`(x, y, z)_Blender -> (-y, -x, z)_Unreal * 100`:

- With the `Convert Scene Unit` fix: max gap 4.83cm (`calf_r`), mean 0.94cm, median 0.78cm, out of a 178cm-tall
  character.
- With `bake_space_transform` (rejected for the animation-count regression above, but recorded since the number is
  informative): max gap 0.00005cm - i.e. exact, floating-point-noise-level agreement.

**New data point on the still-open residual gap** (see the Unity section above): the same rig's worst-case limb gap
via Unreal/FBX (`calf_r`, 4.83cm with the `Convert Scene Unit` fix, effectively 0cm with `bake_space_transform`) is
far below Unity's ~40-44cm `calf_l/r`/`thigh_l/r` gaps on the same bones, and much closer to Godot/glTF's <1cm-to-14cm
range than to Unity's. This is evidence the residual gap first found in the Unity session is **Unity-importer/Avatar-
system-specific**, not a general FBX-format issue as originally hypothesized - two independent FBX consumers (raw
Blender re-import, and now Unreal) both read the same exported file back correctly; only Unity's own import/Avatar
pipeline showed the large gap.

### Methodology note: rest pose vs. posed - a real trap, not just a Unity/Godot indexing footgun

The two prior sessions' "watch for measurement bugs, not pipeline bugs" lesson (Unity's finger-gap false alarm,
Godot's 1.9m `ARRAY_BONES`-indexing false alarm) repeated here in a new form: an initial comparison against Blender's
`bone.matrix_local` (true edit-bone rest pose) showed enormous, hierarchy-depth-correlated gaps (up to ~140cm on
finger-tip bones) that a naive read would call a broken skin bind. Cross-checking against Blender's own **posed**
bone transforms (`pose_bone.matrix`, at the fixture's default `Idle_Loop` frame 1 - the frame the scratch file
happened to be sitting on at export time, curled fist and all) instead of the edit-bone rest pose closed the gap to
sub-5cm immediately. In other words: Unreal's SkeletalMeshComponent shows whatever pose the Blender scene was
actually posed to when the animation-baking FBX export ran as its no-animation-assigned default appearance, **not**
the true T-pose/bind pose - this is expected FBX/Blender-exporter behavior (animation-baking exports never claimed
to reset the scene to rest pose first), not a defect, but it is exactly the kind of assumption a first attempt at
ground-truth capture gets wrong. Playing any of the 14 real AnimSequences overrides this default appearance
immediately, so it has no user-visible impact beyond "what does the mesh look like in the content browser thumbnail
before you press play."

### Character Blueprint setup quirk (found interactively, with live user testing)

Building a minimal walkable demo (`BP_CombatCharacter`, duplicated from the Third Person template's character
Blueprint with the mesh/Anim Blueprint swapped to the imported assets) surfaced a rig-specific gotcha worth carrying
into user docs: the duplicated SkeletalMeshComponent inherited a `Relative Rotation` yaw tuned for the *Unreal
Mannequin's* forward-axis convention (-90°). For this fixture's rig, that value is wrong on two different rigs' worth
of evidence gathered live (0° still faced backward relative to travel, -90°/270° and 0° were both confirmed wrong
by interactive testing) - 180° was the correct value, confirmed by the user actually walking the character around
in Play mode. There is no single constant that works for every rig; each new character's mesh-relative yaw has to be
checked against its own source rig's forward convention. See `exporter_guide_unreal.md`.

### Clean-room reconfirmation (same session, after documentation was written)

Once the guide above was written, re-ran the whole export → import path from scratch to confirm the *documented*
steps actually reproduce success independent of all the trial-and-error state accumulated while diagnosing the scale
bug: fresh Blender scene (`read_homefile(use_empty=True)`), fresh append from the fixture's own path (never the
scratch working copy), `UE-animation` preset applied via the real `create_export_collections` operator, exported,
then imported into a previously-untouched `/Game/CleanReconfirmTest` content folder with `Convert Scene Unit`
enabled exactly as documented.

Result: identical to the original validation - 18 assets (2 materials, 1 Skeleton, 1 SkeletalMesh, all 14
AnimSequences), height 178.61cm (matches the original run to 5 decimal places), 66 bones. Confirms the documented
workflow is real and reproducible, not an artifact of the specific sequence of fixes applied while debugging it.

One warning surfaced on this clean run that hadn't been called out before: `Imported skeleton has some invalid bind
poses. Skeletal mesh skinning has been rebind using the time zero pose.` Reproduced consistently across every import
of this rig in this session (not just this one), always alongside the already-documented smoothing-groups warning.
Since the 65-bone posed-position verification (see above) already confirms the resulting skin binding is
numerically correct, this looks like Unreal's importer self-correcting a real-but-harmless FBX bind-pose quirk
rather than a defect - added to `exporter_guide_unreal.md` as a second "expected warning" alongside the smoothing
groups one, so a user doesn't mistake it for a broken import.
