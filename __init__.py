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
from .panels import SCENE_PT_CollectionExportPanel
from .uilist import SCENE_UL_CollectionList
from .properties import CustomExporterPreferences, register_scene_properties, unregister_scene_properties

classes = (
    SCENE_OT_CreateExportDirectory,
    SCENE_OT_SetExporterPath,
    SCENE_OT_ExportCollection,
    SCENE_OT_ExportSelectedCollections,
    SCENE_OT_OpenExportDirectory,
    SCENE_UL_CollectionList,
    SCENE_PT_CollectionExportPanel,
    SCENE_OT_SelectAllCollections,
    SCENE_OT_UnselectAllCollections,
    CustomExporterPreferences,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    register_scene_properties()

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    unregister_scene_properties()

if __name__ == "__main__":
    register()
