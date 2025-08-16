import os

from ..presets_export.preset_format_functions import get_preset_format_folder

ADDON_NAME = "Simple Export"

# Map color_tag to icons
COLOR_TAG_ICONS = {
    'NONE': 'OUTLINER_COLLECTION',
    'COLOR_01': 'COLLECTION_COLOR_01',
    'COLOR_02': 'COLLECTION_COLOR_02',
    'COLOR_03': 'COLLECTION_COLOR_03',
    'COLOR_04': 'COLLECTION_COLOR_04',
    'COLOR_05': 'COLLECTION_COLOR_05',
    'COLOR_06': 'COLLECTION_COLOR_06',
    'COLOR_07': 'COLLECTION_COLOR_07',
    'COLOR_08': 'COLLECTION_COLOR_08',
}

EXPORT_FORMATS = {
    "FBX": {
        "op_name": "IO_FH_fbx",
        "label": "FBX",
        "description": "FBX Export",
        "preset_folder": os.path.join(get_preset_format_folder(), "export_scene.fbx"),
        "op_type": "<class 'bpy.types.EXPORT_SCENE_OT_fbx'>",
        "file_extension": "fbx",
    },
    "OBJ": {
        "op_name": "IO_FH_obj",
        "label": "OBJ",
        "description": "Wavefront OBJ Export",
        "preset_folder": os.path.join(get_preset_format_folder(), "wm.obj_export"),
        "op_type": "<class 'bpy.types.WM_OT_obj_export'>",
        "file_extension": "obj",
    },
    "GLTF": {
        "op_name": "IO_FH_gltf2",
        "label": "glTF",
        "description": "glTF 2.0 Export",
        "preset_folder": os.path.join(get_preset_format_folder(), "export_scene.gltf"),
        "op_type": "<class 'bpy.types.EXPORT_SCENE_OT_gltf'>",
        "file_extension": "glb",
    },
    "USD": {
        "op_name": "IO_FH_usd",
        "label": "USD",
        "description": "Universal Scene Description Export",
        "preset_folder": os.path.join(get_preset_format_folder(), "wm.usd_export"),
        "op_type": "<class 'bpy.types.WM_OT_usd_export'>",
        "file_extension": "usd",
    },
    "ABC": {
        "op_name": "IO_FH_alembic",
        "label": "Alembic",
        "description": "Alembic Export",
        "preset_folder": os.path.join(get_preset_format_folder(), "wm.alembic_export"),
        "op_type": "<class 'bpy.types.WM_OT_alembic_export'>",
        "file_extension": "abc",
    },
    "PLY": {
        "op_name": "IO_FH_ply",
        "label": "PLY",
        "description": "Stanford PLY Export",
        "preset_folder": os.path.join(get_preset_format_folder(), "wm.ply_export"),
        "op_type": "<class 'bpy.types.WM_OT_ply_export'>",
        "file_extension": "ply",
    },
    "STL": {
        "op_name": "IO_FH_stl",
        "label": "STL",
        "description": "STL Export",
        "preset_folder": os.path.join(get_preset_format_folder(), "wm.stl_export"),
        "op_type": "<class 'bpy.types.WM_OT_stl_export'>",
        "file_extension": "stl",
    },
}
