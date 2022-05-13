# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# <pep8 compliant>

# ----------------------------------------------------------------------------
import importlib
import bpy

from bpy.props import (
    BoolProperty,
    FloatProperty,
    StringProperty,
    EnumProperty,
)
from bpy_extras.io_utils import (
    ImportHelper,
    ExportHelper,
    orientation_helper,
    path_reference_mode,
    axis_conversion,
)


# ----------------------------------------------------------------------------
bl_info = {
    "name": "Cannibal Project (CPJ) format",
    "author": "patwork",
    "version": (0, 0, 1),
    "blender": (3, 1, 0),
    "location": "File > Import-Export",
    "description": "Import-Export CPJ",
    "warning": "",
    "doc_url": "",
    "support": "COMMUNITY",
    "category": "Import-Export",
}


# ----------------------------------------------------------------------------
@orientation_helper(axis_forward='-Z', axis_up='Y')
class ImportCPJ(bpy.types.Operator, ImportHelper):
    """Load a Cannibal Project (CPJ) File"""
    bl_idname = "import_model.cpj"
    bl_label = "Import CPJ"
    bl_options = {'UNDO'}

    filename_ext = ".cpj"
    filter_glob: StringProperty(default="*.cpj", options={'HIDDEN'})

    def execute(self, context):
        from . import import_cpj
        keywords = self.as_keywords(ignore=(
            "axis_forward",
            "axis_up",
            "filter_glob",
        ))
        return import_cpj.load(context, **keywords)


# ----------------------------------------------------------------------------
@orientation_helper(axis_forward='-Z', axis_up='Y')
class ExportCPJ(bpy.types.Operator, ExportHelper):
    """Save a Cannibal Project (CPJ) File"""
    bl_idname = "export_model.cpj"
    bl_label = "Export CPJ"

    filename_ext = ".cpj"
    filter_glob: StringProperty(default="*.cpj", options={'HIDDEN'})

    def execute(self, context):
        from . import export_cpj
        keywords = self.as_keywords(ignore=(
            "axis_forward",
            "axis_up",
            "check_existing",
            "filter_glob",
        ))
        return export_cpj.save(context, **keywords)


# ----------------------------------------------------------------------------
def menu_func_import(self, context):
    self.layout.operator(ImportCPJ.bl_idname, text="Cannibal Project (.cpj)")


# ----------------------------------------------------------------------------
def menu_func_export(self, context):
    self.layout.operator(ExportCPJ.bl_idname, text="Cannibal Project (.cpj)")


# ----------------------------------------------------------------------------
classes = {
    ImportCPJ,
    ExportCPJ,
}


# ----------------------------------------------------------------------------
def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)

    print("CPJ plugin loaded")  # FIXME debug


# ----------------------------------------------------------------------------
def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)

    for cls in classes:
        bpy.utils.unregister_class(cls)

    print("CPJ plugin unloaded")  # FIXME debug


# ----------------------------------------------------------------------------
if "import_cpj" in locals():
    importlib.reload(import_cpj)

if "export_cpj" in locals():
    importlib.reload(export_cpj)

if __name__ == "__main__":
    register()

# EoF
