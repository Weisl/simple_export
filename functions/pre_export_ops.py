from mathutils import Matrix, Euler
import bpy

TRIANGULATE_MOD_NAME = "_SimpleExport_Triangulate"


# --- Triangulate ---

def apply_triangulate_modifiers(collection):
    """Bake triangulation into mesh data before export (non-destructive).

    Armature-deformed meshes are triangulated in their rest/bind pose, not
    their currently-posed shape: evaluating with an Armature modifier active
    would bake the CURRENT pose into static vertex data, and Blender's FBX
    exporter still builds skin-cluster/bind-pose data from an Armature
    modifier regardless of its show_viewport/show_render suppression below -
    it detects the modifier and the matching vertex groups directly, not via
    the depsgraph-evaluated mesh. Without this, the already-posed baked mesh
    gets deformed a second time by the exporter, with error proportional to
    how far each bone sits from rest at export time - most visible on
    extremities (fingers) that are typically posed far from rest, while
    barely noticeable on bones close to rest (torso/spine).

    Returns a backup dict {obj.as_pointer(): (original_mesh, suppressed)} so the
    caller can restore with remove_triangulate_modifiers. Keyed by pointer (not
    obj.name) because names are mutable and can change between apply and restore.
    """
    backup = {}
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for obj in collection.all_objects:
        if obj.type != 'MESH':
            continue

        # Temporarily hide armature modifiers for the bake only, so
        # triangulation is the only thing baked into the evaluated mesh.
        armature_mod_states = {}
        for armature_mod in obj.modifiers:
            if armature_mod.type == 'ARMATURE':
                armature_mod_states[armature_mod.name] = (armature_mod.show_viewport, armature_mod.show_render)
                armature_mod.show_viewport = False
                armature_mod.show_render = False

        mod = obj.modifiers.new(name=TRIANGULATE_MOD_NAME, type='TRIANGULATE')
        mod.keep_custom_normals = True
        try:
            depsgraph.update()
            eval_obj = obj.evaluated_get(depsgraph)
            triangulated_mesh = bpy.data.meshes.new_from_object(eval_obj)
        finally:
            obj.modifiers.remove(mod)
            for mod_name, (show_viewport, show_render) in armature_mod_states.items():
                armature_mod = obj.modifiers.get(mod_name)
                if armature_mod is not None:
                    armature_mod.show_viewport = show_viewport
                    armature_mod.show_render = show_render

        # All modifiers are now baked into triangulated_mesh. Suppress them so
        # the exporter doesn't apply them a second time on the already-evaluated mesh.
        # Both flags are disabled to cover exporters that use either depsgraph type.
        suppressed = {m.name: (m.show_render, m.show_viewport) for m in obj.modifiers}
        for m in obj.modifiers:
            m.show_render = False
            m.show_viewport = False
        backup[obj.as_pointer()] = (obj.data, suppressed)
        obj.data = triangulated_mesh
    return backup


def remove_triangulate_modifiers(collection, backup):
    """Restore original mesh data and modifier visibility after a triangulated export."""
    for obj in collection.all_objects:
        if obj is None or obj.as_pointer() not in backup:
            continue
        original_mesh, suppressed = backup[obj.as_pointer()]
        temp_mesh = obj.data
        obj.data = original_mesh
        for mod in obj.modifiers:
            if mod.name in suppressed:
                mod.show_render, mod.show_viewport = suppressed[mod.name]
        bpy.data.meshes.remove(temp_mesh)


# --- Apply Scale ---

def apply_scale_for_export(collection):
    """
    Bake object scale into mesh data before export.
    Makes a single-user copy of the mesh to avoid affecting shared data blocks.
    Returns a backup dict: {obj.as_pointer(): (original_mesh, scale)}. Keyed by
    pointer (not obj.name) because names are mutable and can change between
    apply and restore.
    """
    backup = {}
    for obj in collection.objects:
        if obj.parent is not None or obj.type != 'MESH':
            continue
        original_mesh = obj.data
        scale = obj.scale.copy()
        new_mesh = original_mesh.copy()
        try:
            new_mesh.transform(Matrix.Diagonal((*scale, 1.0)))
        except Exception:
            bpy.data.meshes.remove(new_mesh)
            raise
        # Backup is recorded only after the copy is fully transformed, and
        # obj.data is only reassigned afterwards, so a failure above leaves
        # obj untouched instead of orphaning original_mesh mid-mutation.
        backup[obj.as_pointer()] = (original_mesh, scale)
        obj.data = new_mesh
        obj.scale = (1.0, 1.0, 1.0)
    return backup


def restore_scale_after_export(collection, backup):
    """Restore original mesh data and scale from backup."""
    for obj in collection.objects:
        if obj.as_pointer() not in backup:
            continue
        original_mesh, scale = backup[obj.as_pointer()]
        temp_mesh = obj.data
        obj.data = original_mesh
        obj.scale = scale
        bpy.data.meshes.remove(temp_mesh)


# --- Apply Rotation ---

def apply_rotation_for_export(collection):
    """
    Bake object rotation into mesh data before export.
    Makes a single-user copy of the mesh to avoid affecting shared data blocks.
    Returns a backup dict: {obj.as_pointer(): (original_mesh, rotation_euler)}.
    Keyed by pointer (not obj.name) because names are mutable and can change
    between apply and restore.
    """
    backup = {}
    for obj in collection.objects:
        if obj.parent is not None or obj.type != 'MESH':
            continue
        original_mesh = obj.data
        rotation = obj.rotation_euler.copy()
        new_mesh = original_mesh.copy()
        try:
            new_mesh.transform(rotation.to_matrix().to_4x4())
        except Exception:
            bpy.data.meshes.remove(new_mesh)
            raise
        backup[obj.as_pointer()] = (original_mesh, rotation)
        obj.data = new_mesh
        obj.rotation_euler = (0.0, 0.0, 0.0)
    return backup


def restore_rotation_after_export(collection, backup):
    """Restore original mesh data and rotation from backup."""
    for obj in collection.objects:
        if obj.as_pointer() not in backup:
            continue
        original_mesh, rotation = backup[obj.as_pointer()]
        temp_mesh = obj.data
        obj.data = original_mesh
        obj.rotation_euler = rotation
        bpy.data.meshes.remove(temp_mesh)


# --- Apply Full Transformation ---

def apply_transform_for_export(collection):
    """
    Bake the full matrix_world (location, rotation, scale) into mesh data before export.
    Makes a single-user copy of the mesh to avoid affecting shared data blocks.
    Returns a backup dict: {obj.as_pointer(): (original_mesh, matrix_world)}.
    Keyed by pointer (not obj.name) because names are mutable and can change
    between apply and restore.
    """
    backup = {}
    for obj in collection.objects:
        if obj.parent is not None or obj.type != 'MESH':
            continue
        original_mesh = obj.data
        matrix = obj.matrix_world.copy()
        new_mesh = original_mesh.copy()
        try:
            new_mesh.transform(matrix)
        except Exception:
            bpy.data.meshes.remove(new_mesh)
            raise
        backup[obj.as_pointer()] = (original_mesh, matrix)
        obj.data = new_mesh
        obj.matrix_world = Matrix.Identity(4)
    return backup


def restore_transform_after_export(collection, backup):
    """Restore original mesh data and matrix_world from backup."""
    for obj in collection.objects:
        if obj.as_pointer() not in backup:
            continue
        original_mesh, matrix = backup[obj.as_pointer()]
        temp_mesh = obj.data
        obj.data = original_mesh
        obj.matrix_world = matrix
        bpy.data.meshes.remove(temp_mesh)


# --- Pre-Rotate Objects ---

def apply_pre_rotation(collection, euler_offset):
    """
    Apply a rotation offset (Euler XYZ) to all top-level objects before export.
    Returns a backup dict: {obj.as_pointer(): original_rotation_euler}. Keyed by
    pointer (not obj.name) because names are mutable and can change between
    apply and restore.
    Applies to all object types (not just meshes) since rotation is object-level.
    """
    backup = {}
    rot = Euler(euler_offset, 'XYZ')
    for obj in collection.objects:
        if obj.parent is not None:
            continue
        backup[obj.as_pointer()] = obj.rotation_euler.copy()
        obj.rotation_euler.rotate(rot)
    return backup


def restore_pre_rotation(collection, backup):
    """Restore original rotation from backup."""
    for obj in collection.objects:
        if obj.as_pointer() not in backup:
            continue
        obj.rotation_euler = backup[obj.as_pointer()]
