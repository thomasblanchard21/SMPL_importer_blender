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

bl_info = {
    "name": "HybrIK for Blender",
    "author": "Jiefeng Li, Shanghai Jiao Tong University",
    "version": (2024, 12, 2),
    "blender": (3, 4, 0),
    "location": "Viewport > Right panel",
    "description": "HybrIK for Blender",
    "wiki_url": "https://github.com/Jeff-sjtu/HybrIK",
    "category": "HybrIK"}

import os
import pickle
import joblib


import bpy
from bpy.props import EnumProperty, PointerProperty, StringProperty
from bpy.types import PropertyGroup
from bpy_extras.io_utils import ImportHelper

from .convert2bvh import load_bvh


# Property groups for UI
class PG_SMPLProperties(PropertyGroup):

    smpl_gender: EnumProperty(
        name = "Model",
        description = "SMPL model",
        items = [ ("female", "Female", ""), ("male", "Male", ""), ("neutral", "Neutral", "") ],
    )

    pickle_format: EnumProperty(
        name = "Pickle Format",
        description = "Pickle format used to save the results",
        items = [ ("joblib", "Joblib", ""), ("pickle", "Pickle", "") ],
    )

    pose_key: StringProperty(
        name = "Pose Key",
        description = "Pose key name in the pickle file",
        default = "pose",
    )

    shape_key: StringProperty(
        name = "Shape Key",
        description = "Shape key name in the pickle file",
        default = "betas",
    )

    trans_key: StringProperty(
        name = "Trans Key",
        description = "Translation key name in the pickle file",
        default = "trans",
    )



class ImportHybrIKPK(bpy.types.Operator, ImportHelper):
    bl_idname = "object.hybrik_import_pk"
    bl_label = "Import Pickle Results"
    bl_description = ("Import HybrIK result from pk files")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        fdir = self.properties.filepath
        gender = context.window_manager.hybrik_tool.smpl_gender
        print('gender:', gender)

        with open(fdir, 'rb') as fid:
            if context.window_manager.hybrik_tool.pickle_format == 'joblib':
                res_db = joblib.load(fid)
            elif context.window_manager.hybrik_tool.pickle_format == 'pickle':
                res_db = pickle.load(fid)

        root_path = os.path.dirname(os.path.realpath(__file__))
        load_bvh(res_db, root_path, gender)
        # do something with fdir here  (fullpath)

        return{'FINISHED'}

class ResetLocation(bpy.types.Operator):
    bl_idname = "object.hybrik_reset_loc"
    bl_label = "Reset locations"
    bl_description = ("Reset locations")
    bl_options = {'REGISTER', 'UNDO'}


    def execute(self, context):
        frame_end = bpy.context.scene.frame_end
        arm_ob = bpy.data.objects['Armature']
        obname = 'm_avg'

        for fid in range(frame_end):
            arm_ob.pose.bones[obname + '_root'].location = [0, 0, 0]
            arm_ob.pose.bones[obname + '_root'].keyframe_insert('location', frame=fid)

        return{'FINISHED'}

class HybrIK_Result_Import(bpy.types.Panel):
    bl_label = "Import HybrIK Results"
    bl_category = "HybrIK"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)

        col.prop(context.window_manager.hybrik_tool, "smpl_gender")
        col.separator()

        col.operator("object.hybrik_import_pk")
        col.separator()

        col.operator("object.hybrik_reset_loc")
        col.separator()

        # export_button = col.operator("export_scene.obj", text="Export OBJ [m]", icon='EXPORT')
        # export_button.global_scale = 1.0
        # export_button.use_selection = True
        # col.separator()

        row = col.row(align=True)
        row.operator("ed.undo", icon='LOOP_BACK')
        row.operator("ed.redo", icon='LOOP_FORWARDS')
        col.separator()

        (year, month, day) = bl_info["version"]
        col.label(text="Version: %s-%s-%s" % (year, month, day))


classes = [
    PG_SMPLProperties,
    ImportHybrIKPK,
    ResetLocation,
    HybrIK_Result_Import
]

def register():
    from bpy.utils import register_class
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.WindowManager.hybrik_tool = PointerProperty(type=PG_SMPLProperties)

def unregister():
    from bpy.utils import unregister_class
    for cls in classes:
        bpy.utils.unregister_class(cls)

    del bpy.types.WindowManager.hybrik_tool

if __name__ == "__main__":
    register()
