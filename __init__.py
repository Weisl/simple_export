import bpy

from .operators import (
    SCENE_OT_CreateExportDirectory,
    SCENE_OT_SetExporterPath,
    SCENE_OT_ExportCollection,
    SCENE_OT_ExportSelectedCollections,
    SCENE_OT_OpenExportDirectory,
    SCENE_OT_SelectAllCollections,
    SCENE_OT_UnselectAllCollections,
)
from .panels import SCENE_PT_CollectionExportPanel, EXPORT_PT_CollectionExportPanel, draw_custom_collection_ui, \
    EXPOTR_MT_context_menu
from .properties import CustomExporterPreferences, register_scene_properties, unregister_scene_properties, \
    register_collection_properties, unregister_collection_properties
from .uilist import SCENE_UL_CollectionList
from .collection_offset import update_collection_offset

classes = (
    SCENE_OT_CreateExportDirectory,
    SCENE_OT_SetExporterPath,
    SCENE_OT_ExportCollection,
    SCENE_OT_ExportSelectedCollections,
    SCENE_OT_OpenExportDirectory,
    SCENE_UL_CollectionList,
    SCENE_OT_SelectAllCollections,
    SCENE_OT_UnselectAllCollections,
    SCENE_PT_CollectionExportPanel,
    EXPORT_PT_CollectionExportPanel,
    EXPOTR_MT_context_menu,
    CustomExporterPreferences,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    register_scene_properties()
    register_collection_properties()

    if update_collection_offset not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(update_collection_offset)

    # Append the custom UI to the COLLECTION_PT_instancing_offset panel
    # bpy.types.COLLECTION_PT_instancing.append(draw_custom_collection_ui)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    unregister_scene_properties()
    unregister_collection_properties()

    if update_collection_offset in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(update_collection_offset)

    # Remove the custom UI from the COLLECTION_PT_instancing_offset panel
    bpy.types.COLLECTION_PT_instancing.remove(draw_custom_collection_ui)


if __name__ == "__main__":
    register()
