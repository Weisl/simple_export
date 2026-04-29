import bpy


class ASSET_OT_ApplyMetadata(bpy.types.Operator):
    """Write staged Author / License / Copyright / Description to all selected local assets."""
    bl_idname = "simple_export.apply_asset_metadata"
    bl_label = "Apply to Selected"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        sd = context.space_data
        if not (sd and hasattr(sd, 'browse_mode') and sd.browse_mode == 'ASSETS'):
            return False
        return bool(context.selected_assets)

    def execute(self, context):
        scene = context.scene
        author = scene.asset_meta_author.strip()
        license_val = scene.asset_meta_license.strip()
        copyright_val = scene.asset_meta_copyright.strip()
        description = scene.asset_meta_description.strip()

        updated = 0
        skipped = 0
        for asset in context.selected_assets:
            local_id = asset.local_id
            if local_id is None or local_id.asset_data is None:
                skipped += 1
                continue
            ad = local_id.asset_data
            if author:
                ad.author = author
            if license_val:
                ad.license = license_val
            if copyright_val:
                ad.copyright = copyright_val
            if description:
                ad.description = description
            updated += 1

        if skipped:
            self.report({'WARNING'}, f"Updated {updated} asset(s). {skipped} skipped (external library assets).")
        else:
            self.report({'INFO'}, f"Updated {updated} asset(s).")
        return {'FINISHED'}


class ASSET_OT_RegeneratePreview(bpy.types.Operator):
    """Regenerate the preview thumbnail for all selected local assets."""
    bl_idname = "simple_export.regenerate_asset_preview"
    bl_label = "Regenerate Preview"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        sd = context.space_data
        if not (sd and hasattr(sd, 'browse_mode') and sd.browse_mode == 'ASSETS'):
            return False
        return bool(context.selected_assets)

    def execute(self, context):
        updated = 0
        skipped = 0
        for asset in context.selected_assets:
            local_id = asset.local_id
            if local_id is None or local_id.asset_data is None:
                skipped += 1
                continue
            with context.temp_override(id=local_id):
                bpy.ops.ed.lib_id_generate_preview()
            updated += 1

        if skipped:
            self.report({'WARNING'}, f"Regenerated {updated} preview(s). {skipped} skipped (external library assets).")
        else:
            self.report({'INFO'}, f"Regenerated {updated} preview(s).")
        return {'FINISHED'}


classes = (ASSET_OT_ApplyMetadata, ASSET_OT_RegeneratePreview)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        if 'bl_rna' in cls.__dict__:
            unregister_class(cls)
