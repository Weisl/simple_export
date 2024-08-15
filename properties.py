import bpy


# Scene properties to define original_path and replacement_path
def register_scene_properties():
    bpy.types.Scene.collection_index = bpy.props.IntProperty(
        name="Collection Index",
        description="Index of the active collection in the list",
        default=0
    )

    bpy.types.Collection.my_export_select = bpy.props.BoolProperty(
        name="Select for Export",
        description="Select this collection for export",
        default=False
    )

    bpy.types.Scene.export_format = bpy.props.EnumProperty(
        name="Export Format",
        description="Filter collections by export format.",
        items=[
            ('Universal Scene Description', "USD (.usd)", "Export to USD format"),
            ('Alembic', "Alembic (.abc)", "Export to Alembic format"),
            ('Wavefront OBJ', "OBJ (.obj)", "Export to OBJ format"),
            ('Stanford PLY', "PLY (.ply)", "Export to PLY format"),
            ('STL', "STL (.stl)", "Export to STL format"),
            ('FBX', "FBX (.fbx)", "Export to FBX format"),
            ('glTF 2.0', "glTF (.gltf)", "Export to glTF format"),
        ],
        default=bpy.context.preferences.addons[__package__].preferences.default_export_format
    )


def unregister_scene_properties():
    del bpy.types.Scene.original_path
    del bpy.types.Scene.replacement_path
    del bpy.types.Scene.collection_index
    del bpy.types.Scene.use_blender_file_location
    del bpy.types.Scene.custom_export_path
    del bpy.types.Collection.my_export_select


class CustomExporterPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    show_lock_icons: bpy.props.BoolProperty(
        name="Show Lock Icons",
        description="Show or hide the LOCKED/UNLOCKED icons in the UIList.",
        default=True
    )

    show_edit_icons: bpy.props.BoolProperty(
        name="Show Edit Icons",
        description="Show or hide the EDIT/New icons in the UIList.",
        default=True
    )

    use_blender_file_location: bpy.props.BoolProperty(
        name="Use Blender File Location",
        description="If checked, the export path will be set to the Blender file location. If unchecked, a custom path will be used.",
        default=True
    )

    use_instance_offset: bpy.props.BoolProperty(
        name="Move to Collection Offset",
        description="Use the collection offset for the exported collection",
        default=True
    )

    custom_export_path: bpy.props.StringProperty(
        name="Custom Export Path",
        description="Custom directory to export files to.",
        subtype='DIR_PATH'
    )

    use_blend_file_name_as_prefix: bpy.props.BoolProperty(
        name="Use Blend File Name as Prefix",
        description="If checked, the Blender file name will be used as a prefix for the export file name.",
        default=False
    )

    custom_prefix: bpy.props.StringProperty(
        name="Custom Prefix",
        description="Custom prefix to add to the export file name."
    )

    custom_suffix: bpy.props.StringProperty(
        name="Custom Suffix",
        description="Custom suffix to add to the export file name."
    )

    default_export_format: bpy.props.EnumProperty(
        name="Default Export Format",
        description="Default format for exporting collections.",
        items=[
            ('Universal Scene Description', "USD (.usd)", "Export to USD format"),
            ('Alembic', "Alembic (.abc)", "Export to Alembic format"),
            ('Wavefront OBJ', "OBJ (.obj)", "Export to OBJ format"),
            ('Stanford PLY', "PLY (.ply)", "Export to PLY format"),
            ('STL', "STL (.stl)", "Export to STL format"),
            ('FBX', "FBX (.fbx)", "Export to FBX format"),
            ('glTF 2.0', "glTF (.gltf)", "Export to glTF format"),
        ],
        default='FBX'  # Default value set to FBX
    )

    original_path: bpy.props.StringProperty(
        name="Original Path",
        description="The path to be replaced.",
        default="workdata"
    )
    replacement_path: bpy.props.StringProperty(
        name="Replacement Path",
        description="The path to replace with.",
        default="sourcedata"
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "use_blender_file_location")
        if not self.use_blender_file_location:
            layout.prop(self, "custom_export_path")
        layout.prop(self, "use_blend_file_name_as_prefix")
        layout.prop(self, "use_instance_offset")
        layout.prop(self, "custom_prefix")
        layout.prop(self, "custom_suffix")
        layout.prop(self, "original_path")
        layout.prop(self, "replacement_path")
        layout.prop(self, "default_export_format")
        layout.prop(self, "show_edit_icons")
        layout.prop(self, "show_lock_icons")
