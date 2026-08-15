# Test fixtures

## combat_character.blend

A rigged, skinned, multi-action character used by `test_export_pipeline_animation.py`
to exercise export of a realistic animated asset (armature + skin + several
actions), as opposed to the plain static quad used by the rest of the export
pipeline tests.

- **Source**: [Universal Animation Library](https://quaternius.com/packs/universalanimationlibrary.html)
  by [Quaternius](https://quaternius.itch.io/universal-animation-library) (Standard tier).
- **License**: [CC0 1.0 Universal](https://creativecommons.org/publicdomain/zero/1.0/) —
  public domain, no attribution required.
- **Contents**: `CombatRig` armature (65 bones) + `CombatMesh` (6,994 verts,
  2 material slots, 52 vertex groups), with a curated subset of 14 of the
  pack's 43 shipped actions kept for size:
  `Idle_Loop, Walk_Loop, Sprint_Loop, Roll, Jump_Start, Jump_Loop, Jump_Land,
  Punch_Jab, Punch_Cross, Sword_Idle, Sword_Attack, Hit_Chest, Hit_Head, Death01`.
- **Rebuilding**: generated from `UAL1_Standard.fbx` (non-root-motion variant)
  via a one-off import + prune + save script; not checked in since it's only
  needed if the fixture needs regenerating from a fresh source download.
