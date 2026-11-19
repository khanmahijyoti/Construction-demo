import json
import unreal as u

mesh = u.load_asset('/Game/PPEWorker/Parts/SK_Body')
options = u.AnimPoseEvaluationOptions()
options.optional_skeletal_mesh = mesh
options.should_retarget = False
report = []
for name in ('Jog', 'CarryLoad', 'Cartwheel'):
    anim = u.load_asset('/Game/PPEWorker/Animations/A_Worker_' + name)
    model = anim.get_editor_property('data_model_interface')
    count = model.get_number_of_keys()
    poses = [u.AnimPoseExtensions.get_anim_pose_at_time(anim, anim.get_play_length() * index / (count - 1), options)
             for index in range(count)]
    root = u.AnimPoseExtensions.get_bone_names(poses[0])[0]
    transforms = [u.AnimPoseExtensions.get_bone_pose(pose, root, u.AnimPoseSpaces.LOCAL) for pose in poses]
    start = transforms[0].translation
    end = transforms[-1].translation
    drift = [end.x - start.x, end.y - start.y, end.z - start.z]

    positions = [u.Vector(t.translation.x - drift[0] * index / (count - 1),
                          t.translation.y - drift[1] * index / (count - 1),
                          t.translation.z - drift[2] * index / (count - 1))
                 for index, t in enumerate(transforms)]
    controller = anim.get_editor_property('controller')
    if not controller:
        controller = u.new_object(u.AnimDataController, outer=anim)
        controller.set_model(model)
    assert controller.set_bone_track_keys(root, positions, [t.rotation for t in transforms],
                                         [t.scale3d for t in transforms], False)
    assert u.EditorAssetLibrary.save_loaded_asset(anim)
    report.append({'asset': anim.get_path_name(), 'bone': str(root), 'keys': count, 'removed_local_trajectory_cm': drift})
with open('E:/Construction_Demo/Saved/worker-in-place-report.json', 'w') as handle:
    json.dump(report, handle, indent=2)
u.log('PPE_IN_PLACE_COMPLETE')
exec(compile(open('E:/Construction_Demo/Scripts/verify_worker_retargets.py').read(), 'verify_worker_retargets.py', 'exec'))
