# Handoff brief: validate the Unreal animated-character pipeline

Starting-point notes for a fresh chat session to establish and validate the Blender → Unreal animated-character
export/import pipeline through the Simple Export addon, mirroring what was already done for Unity and Godot. Written
so that session doesn't have to rediscover the environment or repeat mistakes made in the earlier two.

## Goal

Same validation the Unity and Godot sessions did: export a rigged, animated character from Blender via Simple
Export's `UE-animation` preset, import it into Unreal, and confirm the skeleton, mesh, and animations all come
through correctly - then document the real, working workflow (not using MCP - MCP is for verification in the
session doing the validation; the resulting docs are for addon users who won't have it).

## What's already done and ready to use

- **`UE-animation` / `UE-animation-fbx` presets exist** in the repo (`presets_addon/preset_data_exporters.py`,
  `presets_export/blender_*/preset_data_fbx.py` for all 5 supported Blender versions) - built alongside the
  Unity/Godot animation work, **not yet tested end-to-end**. Confirmed diff from the static `UE-fbx` preset (checked
  against `blender_5_2/preset_data_fbx.py`): `bake_anim: False → True`, `bake_anim_use_nla_strips: True → False`,
  `bake_anim_use_all_actions: False → True` - the identical three-field pattern used for `Unity-animation`.
  Everything else (axis convention, `add_leaf_bones: False`, `use_armature_deform_only: False`) stays exactly as
  `UE-fbx` already had it, since those are Unreal-specific FBX conventions unrelated to animation.
- **The one confirmed, real bug fix from the Unity session already applies to Unreal with no extra work**:
  `functions/pre_export_ops.py`'s `apply_triangulate_modifiers` was double-deforming armature-skinned meshes when
  `triangulate_before_export` is on. Fixed by disabling Armature modifiers specifically during the triangulation
  bake. This runs before every exporter (FBX/glTF/USD/Alembic), so it's already protecting Unreal's FBX export too.
  Read the full root-cause writeup in `docs/animated-character-export-notes.md` before assuming any new symptom is a
  new bug - check whether it matches this pattern first.
- **A real, still-open, non-addon-specific issue, directly relevant here**: the Unity session found a ~0.4m
  bone-to-skin-vertex gap on some limbs (calves/thighs/upper-arms) that persisted even with the triangulate fix, and
  was reproduced by a *raw* FBX export bypassing the addon's pipeline entirely - so it isn't something
  `simple_export` introduces. The follow-up Godot session found the **same rig does not show this gap via glTF**
  (<0.14m on the same limbs), which is evidence the issue is FBX-format-specific rather than a general rig problem.
  Since Unreal also imports via FBX, this is the natural next data point: if Unreal shows the same ~0.4m-scale gap,
  that's strong evidence it's an FBX-format issue (Blender's FBX exporter, or a shared convention both engines'
  importers rely on) rather than something specific to Unity's importer. If Unreal does *not* show it, that would
  instead point at something Unity-importer-specific. Either result is valuable, useful information - don't skip
  this check.

## Environment - NOT yet set up (unlike the Godot session, which had this ready)

- **No Unreal MCP server is currently configured.** `claude mcp list` (as of this writing) shows only `unity-mcp`,
  `godot`, and `blender` - no Unreal entry. Setting up *some* form of Unreal Editor automation access is the first
  blocker to resolve, not an assumption to skip past. There are a few community Unreal MCP/remote-control projects
  (exposing Python remote execution or the Editor Utility/Remote Control API) - check what's actually installable
  and what surface it exposes before assuming it can replicate Unity's `Unity_RunCommand`-style arbitrary C#/Python
  execution. If nothing suitable is available, say so early and ask rather than guessing at a workflow that can't
  actually be driven programmatically.
- **No dedicated throwaway Unreal test project exists yet** alongside `Simple_Unity` and `simple-godot` under
  `/media/matthiasp/Projects/Projects/Simple_Engine/`. There *are* other real Unreal projects on this machine
  (`AlAndalus` at `/media/matthiasp/Projects/Projects/AlAndalus/...`, `Prop_UE` at
  `/media/matthiasp/Projects/Projects/2026_photogrammetry/Prop_UE/...`) - **those are the user's own work, not test
  scaffolding. Do not use them for this validation.** Create a fresh, minimal project under `Simple_Engine/` instead
  (matching the existing naming convention), e.g. a Blank or Third Person template. Multiple Unreal versions are
  installed locally (5.6.1, 5.7.3, 5.8.1 under `~/Applications/Linux_Unreal_Engine_*`) - check which version, if
  any, the addon's `UE-fbx`/`UE-animation-fbx` presets were built against before picking one, since FBX
  axis-convention details can be version-sensitive.
- **Blender MCP** (`mcp__blender__*`) should still be available (same as the Unity/Godot sessions) - verify it's in
  the tool list before assuming; availability is fixed at session start.

## Test fixture

Same fixture as the Unity and Godot sessions: `tests/blender/fixtures/combat_character.blend` - see
`tests/blender/fixtures/README.md` for provenance. **Read `docs/animated-character-export-notes.md` in full before
starting** - it covers the append-with-all-actions gotcha (a plain collection append only pulls in the one Action
currently assigned to the armature, not all 14 - explicitly include `data_to.actions = list(data_from.actions)`)
and the rule against opening/working in the fixture file live (start fresh, append, save the working copy to a
scratch path, never back to the fixture's own path).

## Methodology notes carried over from the Unity and Godot sessions - read `docs/animated-character-export-notes.md`
in full, don't skip this

- **Whole-mesh bounding-box checks are not sensitive enough.** Use per-bone measurement instead. The Godot session's
  first attempt at a skin-binding check produced a ~1.9m false-positive gap from a wrong assumption about how
  Godot's mesh API indexes bone/weight data internally - caught only by cross-checking against a second,
  index-assumption-free method (classify each vertex by nearest rest-pose bone) and against a raw parse of the
  exported file bypassing the engine entirely. Expect Unreal's Python API (`unreal.SkeletalMesh`, bone reference
  skeletons, render data access) to have its own indexing conventions with the same failure mode - **calibrate
  any new measurement against a case with a known-correct answer (e.g. rest-pose bone positions, which should match
  Blender to near-zero error) before trusting it on the less-trivially-checkable skin/animation questions.**
- **Don't build automated fixes before measuring that a hypothesis actually moves the numbers.** The Unity session
  built and fully reverted an "armature transform" pre-export fix based on a plausible, well-researched theory that
  turned out to be measurably wrong, and introduced a real regression along the way.
- **Watch for ambiguous name-based lookups.** Unity's `GameObject.Find` intermittently matched a nested object
  sharing the top-level object's name. Check whether Unreal's asset/actor lookup-by-name has a similar footgun
  before relying on it.
- **The FBX axis convention is already a solved problem here** - `UE-fbx` is an existing, presumably-already-correct
  preset (Primary/Secondary Bone Axis, Forward/Up Axis are already set for Unreal's conventions). Don't re-derive
  these via trial and error; if something looks axis-flipped, check whether it's a *measurement* bug (see above)
  before assuming the preset itself is wrong.

## Suggested first steps for the new session

1. Read `docs/animated-character-export-notes.md` in full, plus skim `docs/godot-animated-export-validation-brief.md`
   for how the equivalent Godot investigation was scoped and what it found - the process generalizes even though
   the engine specifics don't.
2. Check `claude mcp list` for Unreal automation options; if nothing suitable exists, surface that to the user
   before spending significant time on a workaround.
3. Locate or create a throwaway Unreal test project under `Simple_Engine/` (never `AlAndalus` or `Prop_UE`).
4. Do the Blender-side export exactly as the real addon UI would - `simple_export.create_export_collections` with
   the `UE-animation` preset, ideally by parsing the actual on-disk preset file Blender's preset system writes
   (`presets_addon/exporter_preset.py`'s `simple_export_presets_folder()`) rather than hand-copying preset values,
   against a fresh scene + freshly appended fixture, saved to a scratch `.blend` - not the fixture's own path.
5. Import into Unreal and figure out Unreal's equivalent import-settings gotchas: Skeleton asset creation/reuse
   across multiple imports of the same rig, whether "Import Animations" is on by default, Animation Blueprint /
   Anim Instance setup needed before anything can actually play at runtime - mirroring Unity's "Avatar Definition
   defaults to No Avatar" trap and Godot's (lack of an equivalent) trap.
6. Once genuinely confirmed working - numeric bone/skin verification against Blender ground truth, not just "it
   imported without erroring" - write the addon-user-facing docs in
   `documentation_source/docs/simple_export/exporter_guide_unreal.md`, following the structure already used in
   `exporter_guide_unity.md` and `exporter_guide_godot.md` (Export steps → Import steps → settings table diffing
   `UE-default` vs `UE-animation`). The file already exists with a static-mesh-only workflow - extend it, don't
   replace it.
7. Update `CHANGELOG.md`'s "Known limitations" note (currently scoped to "FBX exports (Unity, Unreal)" - update
   once Unreal is actually confirmed one way or the other on the residual-gap question) and add a matching entry to
   `documentation_source/docs/simple_export/exporter_release_notes.md`, following the pattern the Godot session's
   changelog updates already established.
