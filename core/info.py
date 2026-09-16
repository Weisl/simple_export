import os
import sys

from ..presets_export.preset_format_functions import get_preset_format_folder

ADDON_NAME = "Simple Export"

if sys.platform == "win32":
    DEFAULT_ABSOLUTE_PATH = "C:\\tmp\\"
elif sys.platform == "darwin":
    DEFAULT_ABSOLUTE_PATH = os.path.expanduser("~/Desktop/")
else:
    DEFAULT_ABSOLUTE_PATH = "/tmp/"

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

# Severity -> icon convention shared by the validation popup (validation/operators.py)
# and the export-results popup (ui/result_popups.py). CANCEL = hard failure,
# ERROR = warning (yellow triangle), INFO = informational.
SEVERITY_ICONS = {'ERROR': 'CANCEL', 'WARNING': 'ERROR', 'INFO': 'INFO'}

# Display order and label for obj.type values, used by the optional per-collection
# export statistics breakdown (functions/vallidate_func.get_collection_export_statistics,
# ui/result_popups.py). Only types actually present in a collection are shown; any
# type not listed here still shows up, labelled with its raw Blender type string.
OBJECT_TYPE_LABELS = {
    'MESH': 'Meshes',
    'LIGHT': 'Lights',
    'CAMERA': 'Cameras',
    'EMPTY': 'Empties',
    'ARMATURE': 'Armatures',
    'CURVE': 'Curves',
    'SURFACE': 'Surfaces',
    'META': 'Metaballs',
    'FONT': 'Text',
    'LATTICE': 'Lattices',
    'GPENCIL': 'Grease Pencil',
    'GREASEPENCIL': 'Grease Pencil',
    'VOLUME': 'Volumes',
    'SPEAKER': 'Speakers',
    'LIGHT_PROBE': 'Light Probes',
}
OBJECT_TYPE_ORDER = list(OBJECT_TYPE_LABELS.keys())