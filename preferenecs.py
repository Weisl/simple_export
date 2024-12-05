import bpy

from .keymap import remove_key

def add_key(self, km, idname, properties_name, simple_export_panel_type, simple_export_panel_ctrl,
            simple_export_panel_shift,
            simple_export_panel_alt, simple_export_panel_active):
    """
    Add a new keymap item to the specified keymap.

    Args:
        km (bpy.types.KeyMap): The keymap to which the new keymap item will be added.
        idname (str): The operator identifier.
        properties_name (str): The name property for the keymap item.
        simple_export_panel_type (str): The type of key (e.g., 'A', 'B', etc.).
        simple_export_panel_ctrl (bool): Whether the Ctrl key is pressed.
        simple_export_panel_shift (bool): Whether the Shift key is pressed.
        simple_export_panel_alt (bool): Whether the Alt key is pressed.
        simple_export_panel_active (bool): Whether the keymap item is active.

    Returns:
        None
    """
    kmi = km.keymap_items.new(idname=idname, type=simple_export_panel_type, value='PRESS',
                              ctrl=simple_export_panel_ctrl, shift=simple_export_panel_shift,
                              alt=simple_export_panel_alt)
    kmi.properties.name = properties_name
    kmi.active = simple_export_panel_active


# Scene properties to define original_path and replacement_path
def register_scene_properties():
    bpy.types.Scene.collection_index = bpy.props.IntProperty(name="Collection Index",
                                                             description="Index of the active collection in the list",
                                                             default=0)

    bpy.types.Scene.export_format = bpy.props.EnumProperty(name="Export Format",
                                                           description="Filter collections by export format.",
                                                           items=[('Universal Scene Description', "USD (.usd)",
                                                                   "Export to USD format"),
                                                                  ('Alembic', "Alembic (.abc)",
                                                                   "Export to Alembic format"),
                                                                  ('Wavefront OBJ', "OBJ (.obj)",
                                                                   "Export to OBJ format"),
                                                                  (
                                                                  'Stanford PLY', "PLY (.ply)", "Export to PLY format"),
                                                                  ('STL', "STL (.stl)", "Export to STL format"),
                                                                  ('FBX', "FBX (.fbx)", "Export to FBX format"), (
                                                                  'glTF 2.0', "glTF (.gltf)",
                                                                  "Export to glTF format"), ],
                                                           default=bpy.context.preferences.addons[
                                                               __package__].preferences.default_export_format)


def register_collection_properties():
    bpy.types.Collection.my_export_select = bpy.props.BoolProperty(name="Select for Export",
                                                                   description="Select this collection for export",
                                                                   default=False)

    bpy.types.Collection.offset_object = bpy.props.PointerProperty(name="Offset Object", type=bpy.types.Object,
                                                                   description="Object to be used for setting the collection offset")


def unregister_scene_properties():
    del bpy.types.Scene.collection_index
    del bpy.types.Scene.export_format


def unregister_collection_properties():
    del bpy.types.Collection.my_export_select
    del bpy.types.Collection.offset_object


class SIMPLE_EXPORT_preferemces(bpy.types.AddonPreferences):
    bl_idname = __package__

    def update_simple_export_panel_key(self, context):
        """
        Update the hotkey assignment for the collision pie menu.

        This function is called when the hotkey assignment is updated in the preferences.

        Args:
            context (bpy.types.Context): The current context.

        Returns:
            None
        """
        # This functions gets called when the hotkey assignment is updated in the preferences
        wm = bpy.context.window_manager
        km = wm.keyconfigs.addon.keymaps["Window"]
        simple_export_panel_type = self.simple_export_panel_type.upper()

        # Remove previous key assignment
        remove_key(context, 'wm.call_panel', "SIMPLE_EXPORT_PT_simple_export")
        add_key(self, km, 'wm.call_panel', "SIMPLE_EXPORT_PT_simple_export", simple_export_panel_type,
                self.simple_export_panel_ctrl,
                self.simple_export_panel_shift, self.simple_export_panel_alt, self.simple_export_panel_active)
        self.simple_export_panel_type = simple_export_panel_type

        return

    prefs_tabs: bpy.props.EnumProperty(
        name='Export Preferences',
        items=(('SETTINGS', "Settings", "General addon settings"),
               ('KEYMAP', "Keymap", "Change the hotkeys for tools associated with this addon.")),
        default='SETTINGS',
        description='Settings category:')

    use_blender_file_location: bpy.props.BoolProperty(name="Use Blender File Location",
                                                      description="If checked, the export path will be set to the Blender file location. If unchecked, a custom path will be used.",
                                                      default=True)

    use_instance_offset: bpy.props.BoolProperty(name="Move to Collection Offset",
                                                description="Use the collection offset for the exported collection",
                                                default=True)

    custom_export_path: bpy.props.StringProperty(name="Custom Export Path",
                                                 description="Custom directory to export files to.", subtype='DIR_PATH')

    use_blend_file_name_as_prefix: bpy.props.BoolProperty(name="Use Blend File Name as Prefix",
                                                          description="If checked, the Blender file name will be used as a prefix for the export file name.",
                                                          default=False)

    custom_prefix: bpy.props.StringProperty(name="Custom Prefix",
                                            description="Custom prefix to add to the export file name.")

    custom_suffix: bpy.props.StringProperty(name="Custom Suffix",
                                            description="Custom suffix to add to the export file name.")

    default_export_format: bpy.props.EnumProperty(name="Default Export Format",
                                                  description="Default format for exporting collections.",
                                                  items=[('Universal Scene Description', "USD (.usd)",
                                                          "Export to USD format"),
                                                         ('Alembic', "Alembic (.abc)", "Export to Alembic format"),
                                                         ('Wavefront OBJ', "OBJ (.obj)", "Export to OBJ format"),
                                                         ('Stanford PLY', "PLY (.ply)", "Export to PLY format"),
                                                         ('STL', "STL (.stl)", "Export to STL format"),
                                                         ('FBX', "FBX (.fbx)", "Export to FBX format"),
                                                         ('glTF 2.0', "glTF (.gltf)", "Export to glTF format"), ],
                                                  default='FBX'  # Default value set to FBX
                                                  )

    original_path: bpy.props.StringProperty(name="Original Path", description="The path to be replaced.",
                                            default="workdata")
    replacement_path: bpy.props.StringProperty(name="Replacement Path", description="The path to replace with.",
                                               default="sourcedata")

    ###################################################################
    # KEYMAP

    simple_export_panel_type: bpy.props.StringProperty(name="Export Popup Menu", default="E",
                                                       update=update_simple_export_panel_key)

    simple_export_panel_ctrl: bpy.props.BoolProperty(name="Ctrl", default=False, update=update_simple_export_panel_key)

    simple_export_panel_shift: bpy.props.BoolProperty(name="Shift", default=True, update=update_simple_export_panel_key)
    simple_export_panel_alt: bpy.props.BoolProperty(name="Alt", default=True, update=update_simple_export_panel_key)

    simple_export_panel_active: bpy.props.BoolProperty(name="Active", default=True,
                                                       update=update_simple_export_panel_key)

    def keymap_ui(self, layout, title, property_prefix, id_name, properties_name):
        box = layout.box()
        split = box.split(align=True, factor=0.5)
        col = split.column()

        # Is hotkey active checkbox
        row = col.row(align=True)
        row.prop(self, f'{property_prefix}_active', text="")
        row.label(text=title)

        # Button to assign the key assignments
        col = split.column()
        row = col.row(align=True)
        key_type = getattr(self, f'{property_prefix}_type')
        text = (
            bpy.types.Event.bl_rna.properties['type'].enum_items[key_type].name
            if key_type != 'NONE'
            else 'Press a key'
        )

        op = row.operator("simple_export.key_selection_button", text=text)
        op.property_prefix = property_prefix

        # row.prop(self, f'{property_prefix}_type', text="")
        op = row.operator("simple_export.remove_hotkey", text="", icon="X")
        op.idname = id_name
        op.properties_name = properties_name
        op.property_prefix = property_prefix

        row = col.row(align=True)
        row.prop(self, f'{property_prefix}_ctrl')
        row.prop(self, f'{property_prefix}_shift')
        row.prop(self, f'{property_prefix}_alt')

    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.prop(self, "prefs_tabs", expand=True)

        if self.prefs_tabs == 'SETTINGS':
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
            layout.prop(self, "use_blender_file_location")

        elif self.prefs_tabs == 'KEYMAP':
            self.keymap_ui(layout, 'Export Popup', 'simple_export_panel', 'wm.call_panel',
                           "SIMPLE_EXPORT_PT_simple_export")


classes = (
    SIMPLE_EXPORT_preferemces,
)


def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)

    from .keymap import add_keymap
    add_keymap()
    register_scene_properties()
    register_collection_properties()


def unregister():
    from .keymap import remove_keymap
    remove_keymap()

    unregister_collection_properties()
    unregister_scene_properties()

    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)
