import bpy


class ASSETBROWSER_PT_simple_export_metadata(bpy.types.Panel):
    bl_idname = "ASSETBROWSER_PT_simple_export_metadata"
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Asset Metadata"
    bl_category = "Simple Export"

    @classmethod
    def poll(cls, context):
        sd = context.space_data
        return sd and hasattr(sd, 'browse_mode') and sd.browse_mode == 'ASSETS'

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        scene = context.scene

        layout.prop(scene, "asset_meta_author")
        layout.prop(scene, "asset_meta_license")
        layout.prop(scene, "asset_meta_copyright")
        layout.prop(scene, "asset_meta_description")

        layout.separator()

        selected = context.selected_assets or []
        n = len(selected)

        row = layout.row()
        row.enabled = n > 0
        row.scale_y = 1.3
        row.operator(
            "simple_export.apply_asset_metadata",
            text=f"Apply to {n} Selected" if n != 1 else "Apply to 1 Selected",
        )

        row = layout.row()
        row.enabled = n > 0
        row.scale_y = 1.3
        row.operator(
            "simple_export.regenerate_asset_preview",
            text=f"Regenerate Preview ({n})" if n != 1 else "Regenerate Preview (1)",
            icon='FILE_REFRESH',
        )


classes = (ASSETBROWSER_PT_simple_export_metadata,)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        if 'bl_rna' in cls.__dict__:
            unregister_class(cls)
