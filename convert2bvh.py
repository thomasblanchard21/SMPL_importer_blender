import argparse
import math
import os
import pickle as pk

import bpy
import numpy as np

# from mathutils import Matrix

def rot2quat(rot):
    m00, m01, m02, m10, m11, m12, m20, m21, m22 = rot.reshape(9)
    q_abs = np.array([
                1.0 + m00 + m11 + m22,
                1.0 + m00 - m11 - m22,
                1.0 - m00 + m11 - m22,
                1.0 - m00 - m11 + m22,
            ])
    q_abs = np.sqrt(np.maximum(q_abs, 0))

    quat_by_rijk = np.vstack(
        [
            np.array([q_abs[0] ** 2, m21 - m12, m02 - m20, m10 - m01]),
            np.array([m21 - m12, q_abs[1] ** 2, m10 + m01, m02 + m20]),
            np.array([m02 - m20, m10 + m01, q_abs[2] ** 2, m12 + m21]),
            np.array([m10 - m01, m20 + m02, m21 + m12, q_abs[3] ** 2]),
        ]
    )
    flr = 0.1
    quat_candidates = quat_by_rijk / np.maximum(2.0 * q_abs[:, None], 0.1)

    idx = q_abs.argmax(axis=-1)

    quat = quat_candidates[idx]
    return quat


def deg2rad(angle):
    return -np.pi * (angle + 90) / 180.


part_match = {'root': 'root', 'bone_00': 'Pelvis', 'bone_01': 'L_Hip', 'bone_02': 'R_Hip',
              'bone_03': 'Spine1', 'bone_04': 'L_Knee', 'bone_05': 'R_Knee', 'bone_06': 'Spine2',
              'bone_07': 'L_Ankle', 'bone_08': 'R_Ankle', 'bone_09': 'Spine3', 'bone_10': 'L_Foot',
              'bone_11': 'R_Foot', 'bone_12': 'Neck', 'bone_13': 'L_Collar', 'bone_14': 'R_Collar',
              'bone_15': 'Head', 'bone_16': 'L_Shoulder', 'bone_17': 'R_Shoulder', 'bone_18': 'L_Elbow',
              'bone_19': 'R_Elbow', 'bone_20': 'L_Wrist', 'bone_21': 'R_Wrist', 'bone_22': 'L_Hand', 'bone_23': 'R_Hand'}


def init_scene(scene, root_path, gender='m', angle=0):
    # load fbx model
    bpy.ops.import_scene.fbx(filepath=os.path.join(root_path, 'data', f'basicModel_{gender}_lbs_10_207_0_v1.0.2.fbx'), axis_forward='-Y', axis_up='-Z', global_scale=100)
    print('success load')
    obname = '%s_avg' % gender[0]
    ob = bpy.data.objects[obname]
    
    # assign the existing spherical harmonics material
    ob.active_material = bpy.data.materials['Material']

    # delete the default cube (which held the material)
    # bpy.ops.object.select_all(action='DESELECT')
    # bpy.data.objects['Cube'].select = True
    # bpy.ops.object.delete(use_global=False)

    # set camera properties and initial position
    # bpy.ops.object.select_all(action='DESELECT')
    cam_ob = bpy.data.objects['Camera']
    cam_ob.location = [0, 0, 0]
    cam_ob.rotation_euler = [np.pi/2, 0, 0]
    # scn = bpy.context.scene
    # scn.objects.active = cam_ob

    # th = deg2rad(angle)
    # cam_ob = init_location(cam_ob, th, params['camera_distance'])

    '''
    cam_ob.matrix_world = Matrix(((0., 0., 1, params['camera_distance']+dis),
                                 (0., -1, 0., -1.0),
                                 (-1., 0., 0., 0.),
                                 (0.0, 0.0, 0.0, 1.0)))
    '''
    # cam_ob.data.angle = math.radians(60)
    # cam_ob.data.lens = 60
    # cam_ob.data.clip_start = 0.1
    # cam_ob.data.sensor_width = 32

    # # setup an empty object in the center which will be the parent of the Camera
    # # this allows to easily rotate an object around the origin
    # scn.cycles.film_transparent = True
    # scn.render.layers["RenderLayer"].use_pass_vector = True
    # scn.render.layers["RenderLayer"].use_pass_normal = True
    # scene.render.layers['RenderLayer'].use_pass_emit = True
    # scene.render.layers['RenderLayer'].use_pass_emit = True
    # scene.render.layers['RenderLayer'].use_pass_material_index = True

    # # set render size
    # # scn.render.resolution_x = params['resy']
    # # scn.render.resolution_y = params['resx']
    # scn.render.resolution_percentage = 100
    # scn.render.image_settings.file_format = 'PNG'

    # clear existing animation data
    # ob.data.shape_keys.animation_data_clear()
    arm_ob = bpy.data.objects['Armature']
    arm_ob.animation_data_clear()

    return (ob, obname, arm_ob)


def Rodrigues(rotvec):
    theta = np.linalg.norm(rotvec)
    r = (rotvec / theta).reshape(3, 1) if theta > 0. else rotvec
    cost = np.cos(theta)
    mat = np.asarray([[0, -r[2], r[1]],
                      [r[2], 0, -r[0]],
                      [-r[1], r[0], 0]])
    return (cost * np.eye(3) + (1 - cost) * r.dot(r.T) + np.sin(theta) * mat)


def rotate180(rot):
    xyz_convert = np.array([
        [1, 0, 0],
        [0, -1, 0],
        [0, 0, -1]
    ], dtype=np.float32)
    return np.dot(xyz_convert.T, rot)


def convert_transl(transl):
    xyz_convert = np.array([
        [1, 0, 0],
        [0, -1, 0],
        [0, 0, -1]
    ], dtype=np.float32)
    return transl.dot(xyz_convert)


def rodrigues2bshapes(pose):
    if pose.size == 24 * 9:
        rod_rots = np.asarray(pose).reshape(24, 3, 3)
        mat_rots = [rod_rot for rod_rot in rod_rots]
    else:
        rod_rots = np.asarray(pose).reshape(24, 3)
        mat_rots = [Rodrigues(rod_rot) for rod_rot in rod_rots]
    bshapes = np.concatenate([(mat_rot - np.eye(3)).ravel()
                              for mat_rot in mat_rots[1:]])
    return (mat_rots, bshapes)


def setState0():
    for ob in bpy.data.objects.values():
        ob.select = False
    bpy.context.scene.objects.active = None


# apply trans pose and shape to character
def apply_trans_pose_shape(trans, pose, shape, ob, arm_ob, obname, scene, frame=None):
    # transform pose into rotation matrices (for pose) and pose blendshapes
    mrots, bsh = rodrigues2bshapes(pose)
    mrots[0] = rotate180(mrots[0])
    trans = convert_transl(trans)

    # set the location of the first bone to the translation parameter
    # arm_ob.pose.bones[obname + '_Pelvis'].location = trans
    arm_ob.pose.bones[obname + '_root'].location = trans
    arm_ob.pose.bones[obname + '_root'].keyframe_insert('location', frame=frame)
    # set the pose of each bone to the quaternion specified by pose
    for ibone, mrot in enumerate(mrots):
        bone = arm_ob.pose.bones[obname + '_' + part_match['bone_%02d' % ibone]]
        bone.rotation_quaternion = rot2quat(mrot)
        if frame is not None:
            bone.keyframe_insert('rotation_quaternion', frame=frame)
            bone.keyframe_insert('location', frame=frame)

    # apply pose blendshapes
    for ibshape, bshape in enumerate(bsh):
        ob.data.shape_keys.key_blocks['Pose%03d' % ibshape].value = bshape
        if frame is not None:
            ob.data.shape_keys.key_blocks['Pose%03d' % ibshape].keyframe_insert(
                'value', index=-1, frame=frame)

    # apply shape blendshapes
    for ibshape, shape_elem in enumerate(shape):
        ob.data.shape_keys.key_blocks['Shape%03d' % ibshape].value = shape_elem
        if frame is not None:
            ob.data.shape_keys.key_blocks['Shape%03d' % ibshape].keyframe_insert(
                'value', index=-1, frame=frame)


def load_bvh(res_db, root_path, gender, pid=0):
    scene = bpy.data.scenes['Scene']

    gender = {
        'male': 'm',
        'female': 'f'
    }[gender]
    ob, obname, arm_ob = init_scene(scene, root_path, gender)
    # try:
    #     setState0()
    # except AttributeError:
    #     pass

    # ob.select = True
    # bpy.context.scene.objects.active = ob

    # unblocking both the pose and the blendshape limits
    for k in ob.data.shape_keys.key_blocks.keys():
        bpy.data.shape_keys["Key"].key_blocks[k].slider_min = -10
        bpy.data.shape_keys["Key"].key_blocks[k].slider_max = 10

    # scene.objects.active = arm_ob

    # animation
    arm_ob.animation_data_clear()
    # cam_ob.animation_data_clear()
    # load smpl params:
    nFrames = len(res_db['pred_thetas'])

    all_betas = res_db['pred_betas']
    avg_beta = np.mean(all_betas, axis=0)

    for frame in range(nFrames):
        print(frame)
        scene.frame_set(frame)
        # apply
        trans = res_db['transl_camsys'][frame]
        shape = avg_beta
        pose = res_db['pred_thetas'][frame]
        apply_trans_pose_shape(
            trans, pose, shape, ob,
            arm_ob, obname, scene, frame=frame)
        # scene.update()
