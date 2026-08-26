# Handoff brief: validate the Godot animated-character pipeline

Starting-point notes for a fresh chat session to establish and validate the Blender → Godot animated-character
export/import pipeline through the Simple Export addon, mirroring what was already done for Unity. Written so that
session doesn't have to rediscover the environment or repeat mistakes made getting here.

## Goal

Same validation the Unity session did: export a rigged, animated character from Blender via Simple Export's
`Godot-animation` preset, import it into Godot, and confirm the skeleton, mesh, and animations all come through
correctly - then document the real, working workflow (not using MCP - MCP is for verification in the session doing
the validation; the resulting docs are for addon users who won't have it).

## What's already done and ready to use

- **`Godot-animation` / `Godot-animation-gltf` presets exist** in the repo (`presets_addon/preset_data_exporters.py`,
  `presets_export/blender_*/preset_data_gltf.py` for all 5 supported Blender versions) - built by mirroring the
  Unity work, **not yet tested end-to-end**. See `docs/animated-character-export-notes.md`, section "What shipped as
  a result", for exactly what was changed and why (`export_animations: True`; `export_animation_mode: 'ACTIONS'`
  was already correct on the static preset).
- **The one confirmed, real bug fix from the Unity session already applies to Godot with no extra work**:
  `functions/pre_export_ops.py`'s `apply_triangulate_modifiers` was double-deforming armature-skinned meshes when
  `triangulate_before_export` is on, because it baked the mesh at its currently-posed shape instead of rest pose.
  Fixed by disabling Armature modifiers specifically during the triangulation bake. This runs before every exporter
  (FBX/glTF/USD/Alembic), so it's already protecting Godot's glTF export too. Read the full root-cause writeup in
  `docs/animated-character-export-notes.md` before assuming any new symptom is a new bug - check whether it matches
  this pattern first.
- **A real, still-open, non-addon-specific issue** from the Unity session: a ~0.4m bone-to-skin-vertex gap on some
  limbs (calves/thighs/upper-arms) that persisted even with the triangulate fix, and was reproduced by a *raw* FBX
  export bypassing the addon's pipeline entirely - so it isn't something `simple_export` introduces. It's unknown
  whether this is FBX/Unity-specific or would also show up via glTF/Godot. Worth checking early: if the same rig
  shows the same kind of limb-offset in Godot, that's evidence it's a Blender-side or rig-side issue, not
  format-specific - valuable information either way.

## Environment already available in this session

- **Godot version**: 4.7.1 (`stable.official.a13da4feb`)
- **Existing Godot project**: `/media/matthiasp/Projects/Projects/Simple_Engine/simple-godot` - found via
  `mcp__godot__list_projects`, not yet inspected further (no scenes/nodes checked, don't know what's already in it)
- **Godot MCP tools available in this environment**: `add_node`, `create_scene`, `export_mesh_library`,
  `get_debug_output`, `get_project_info`, `get_uid`, `launch_editor`, `list_projects`, `load_sprite`, `run_project`,
  `save_scene`, `stop_project`, `update_project_uids`. These are schema-deferred - use `ToolSearch` with
  `select:<name>` before calling any of them, they won't be directly callable otherwise.
- No Godot-side C# equivalent of Unity's `Unity_RunCommand` (arbitrary code execution) was seen in the tool list -
  check what's actually possible for driving the Godot editor headlessly/programmatically before assuming you can
  replicate the Unity session's approach of writing throwaway C#-equivalent verification scripts inline. GDScript
  run via `add_node`/scene manipulation may be the available surface instead.
- **Blender MCP** (`mcp__blender__*`) was used throughout the Unity session and is registered for this project
  (added via `claude mcp add blender ...`, local scope) - should still be available, but tool availability is fixed
  at session start, so if it's not in the fresh session's tool list, check `claude mcp list` and reload.

## Test fixture

`tests/blender/fixtures/combat_character.blend` - `CombatCharacter` collection containing `CombatRig` (65-bone
armature) + `CombatMesh` (6994 verts, 52 vertex groups, 2 materials), 14 baked Actions (`Idle_Loop`, `Walk_Loop`,
`Sprint_Loop`, `Roll`, `Jump_Start/Loop/Land`, `Punch_Jab/Cross`, `Sword_Idle/Attack`, `Hit_Chest/Head`, `Death01`).
Sourced from Quaternius's Universal Animation Library (CC0), see `tests/blender/fixtures/README.md`.

**Do not open this file directly and work in it live** - that's what caused problems last time (accidental resaves,
a crash from aggressive live pose manipulation). Instead: start a fresh/empty Blender scene and append the
`CombatCharacter` collection via `bpy.data.libraries.load(path, link=False)`, explicitly including
`data_to.actions = list(data_from.actions)` (a plain collection append only pulls in the one Action currently
assigned to the armature, not all 14 - this tripped up the Unity session too). Save your working copy to a scratch
path, never back to the fixture's own path.

## Methodology notes - what worked, what didn't

- **Whole-mesh bounding-box checks are not sensitive enough.** A corruption confined to a fraction of the vertices
  (e.g. just the fingers) doesn't move the overall silhouette size enough to notice. What worked reliably in Unity:
  bake the live skinned mesh, cross-reference each vertex's dominant bone weight against that bone's actual
  transform position, take the max per-bone gap. Figure out the Godot equivalent (likely: bake the
  `MeshInstance3D`'s skin at runtime via `ArrayMesh`/`SkeletonModifier3D` APIs or similar, compare against
  `Skeleton3D` bone global transforms) rather than eyeballing the viewport or trusting aggregate stats.
- **Don't build automated "fixes" before confirming a hypothesis moves the actual measured numbers.** The Unity
  session built and then fully reverted an "armature transform" pre-export fix based on a plausible-sounding,
  well-researched theory that turned out to be measurably wrong (identical results with/without it) - and it
  introduced a real regression along the way. Measure before/after on every hypothesis before writing code around it.
- **Object name lookups can be ambiguous.** In Unity, `GameObject.Find("CombatRig")` intermittently matched a
  *nested* object sharing the same name as the top-level one, causing confusing intermittent failures. If Godot's
  node-lookup-by-name has a similar footgun (e.g. `get_node()` with an ambiguous relative path, or multiple nodes
  named identically in an imported skeleton hierarchy), prefer an unambiguous lookup (root/scene-tree-anchored path,
  or filtering by node type) from the start.
- **Watch for stale state after scene reloads/domain reloads.** Godot's editor likely has its own equivalent of
  Unity's "lost MCP connection during a domain reload" - expect tool calls to transiently fail after anything that
  reloads scripts or re-imports assets, and retry rather than assuming a crash.
- **This chat session hit a hard per-conversation image-display cap partway through** (every subsequent screenshot,
  even tiny ones, got rejected) - don't rely on being able to view many screenshots over a long session; prefer
  numeric/data verification (see bake-and-compare method above) over visual inspection where possible, and don't
  burn turns re-attempting rejected image reads.

## Suggested first steps for the new session

1. Read `docs/animated-character-export-notes.md` in full for the detailed Unity findings.
2. Check `mcp__godot__get_project_info` on the existing `simple-godot` project to see what's already in it.
3. Do the Blender-side export exactly as the real addon UI would (via `simple_export.create_export_collections`
   with the `Godot-animation` preset, not by hand-setting collection properties) against a fresh scene + appended
   fixture, to a scratch `.blend` - matches how the Unity validation was eventually done cleanly.
4. Import into Godot and figure out Godot's equivalent gotchas to Unity's "Avatar Definition defaults to No Avatar"
   surprise - Godot's glTF importer has its own set of import settings/defaults for skeletons and animation players
   that are worth checking don't have an equivalent trap.
5. Once a real, working pipeline is confirmed (not just "it imported without erroring" - actually verify bone
   positions against skin data numerically), write the addon-user-facing docs in
   `documentation_source/docs/simple_export/exporter_guide_godot.md`, following the structure just added to
   `exporter_guide_unity.md` as a template (Export steps → Import steps → settings table diffing `Godot-default` vs
   `Godot-animation`).
