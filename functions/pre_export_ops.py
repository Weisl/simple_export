from mathutils import Matrix, Euler
import bpy

TRIANGULATE_MOD_NAME = "_SimpleExport_Triangulate"


# --- Triangulate ---

def apply_triangulate_modifiers(collection):
    """Bake triangulation into mesh data before export (non-destructive).

    Returns a backup dict {obj.name: (original_mesh, suppressed)} so the caller
    can restore with remove_triangulate_modifiers.
    """
    backup = {}
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for obj in collection.all_objects:
        if obj.type != 'MESH':
            continue
        mod = obj.modifiers.new(name=TRIANGULATE_MOD_NAME, type='TRIANGULATE')
        mod.keep_custom_normals = True
        depsgraph.update()
        eval_obj = obj.evaluated_get(depsgraph)
        triangulated_mesh = bpy.data.meshes.new_from_object(eval_obj)
        obj.modifiers.remove(mod)
        # All modifiers are now baked into triangulated_mesh. Suppress them so
        # the exporter doesn't apply them a second time on the already-evaluated mesh.
        # Both flags are disabled to cover exporters that use either depsgraph type.
        suppressed = {m.name: (m.show_render, m.show_viewport) for m in obj.modifiers}
        for m in obj.modifiers:
            m.show_render = False
            m.show_viewport = False
        backup[obj.name] = (obj.data, suppressed)
        obj.data = triangulated_mesh
    return backup


def remove_triangulate_modifiers(collection, backup):
    """Restore original mesh data and modifier visibility after a triangulated export."""
    for obj in collection.all_objects:
        if obj is None or obj.name not in backup:
            continue
        original_mesh, suppressed = backup[obj.name]
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
    Returns a backup dict: {obj.name: (original_mesh, scale)}.
    """
    backup = {}
    for obj in collection.objects:
        if obj.parent is not None or obj.type != 'MESH':
            continue
        original_mesh = obj.data
        scale = obj.scale.copy()
        obj.data = obj.data.copy()
        obj.data.transform(Matrix.Diagonal((*scale, 1.0)))
        obj.scale = (1.0, 1.0, 1.0)
        backup[obj.name] = (original_mesh, scale)
    return backup


def restore_scale_after_export(collection, backup):
    """Restore original mesh data and scale from backup."""
    for obj in collection.objects:
        if obj.name not in backup:
            continue
        original_mesh, scale = backup[obj.name]
        temp_mesh = obj.data
        obj.data = original_mesh
        obj.scale = scale
        bpy.data.meshes.remove(temp_mesh)


# --- Apply Rotation ---

def apply_rotation_for_export(collection):
    """
    Bake object rotation into mesh data before export.
    Makes a single-user copy of the mesh to avoid affecting shared data blocks.
    Returns a backup dict: {obj.name: (original_mesh, rotation_euler)}.
    """
    backup = {}
    for obj in collection.objects:
        if obj.parent is not None or obj.type != 'MESH':
            continue
        original_mesh = obj.data
        rotation = obj.rotation_euler.copy()
        obj.data = obj.data.copy()
        obj.data.transform(rotation.to_matrix().to_4x4())
        obj.rotation_euler = (0.0, 0.0, 0.0)
        backup[obj.name] = (original_mesh, rotation)
    return backup


def restore_rotation_after_export(collection, backup):
    """Restore original mesh data and rotation from backup."""
    for obj in collection.objects:
        if obj.name not in backup:
            continue
        original_mesh, rotation = backup[obj.name]
        temp_mesh = obj.data
        obj.data = original_mesh
        obj.rotation_euler = rotation
        bpy.data.meshes.remove(temp_mesh)


# --- Apply Full Transformation ---

def apply_transform_for_export(collection):
    """
    Bake the full matrix_world (location, rotation, scale) into mesh data before export.
    Makes a single-user copy of the mesh to avoid affecting shared data blocks.
    Returns a backup dict: {obj.name: (original_mesh, matrix_world)}.
    """
    backup = {}
    for obj in collection.objects:
        if obj.parent is not None or obj.type != 'MESH':
            continue
        original_mesh = obj.data
        matrix = obj.matrix_world.copy()
        obj.data = obj.data.copy()
        obj.data.transform(matrix)
        obj.matrix_world = Matrix.Identity(4)
        backup[obj.name] = (original_mesh, matrix)
    return backup


def restore_transform_after_export(collection, backup):
    """Restore original mesh data and matrix_world from backup."""
    for obj in collection.objects:
        if obj.name not in backup:
            continue
        original_mesh, matrix = backup[obj.name]
        temp_mesh = obj.data
        obj.data = original_mesh
        obj.matrix_world = matrix
        bpy.data.meshes.remove(temp_mesh)


# --- Pre-Rotate Objects ---

def apply_pre_rotation(collection, euler_offset):
    """
    Apply a rotation offset (Euler XYZ) to all top-level objects before export.
    Returns a backup dict: {obj.name: original_rotation_euler}.
    Applies to all object types (not just meshes) since rotation is object-level.
    """
    backup = {}
    rot = Euler(euler_offset, 'XYZ')
    for obj in collection.objects:
        if obj.parent is not None:
            continue
        backup[obj.name] = obj.rotation_euler.copy()
        obj.rotation_euler.rotate(rot)
    return backup


def restore_pre_rotation(collection, backup):
    """Restore original rotation from backup."""
    for obj in collection.objects:
        if obj.name not in backup:
            continue
        obj.rotation_euler = backup[obj.name]
