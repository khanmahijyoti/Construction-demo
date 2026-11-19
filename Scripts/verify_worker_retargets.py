import json
import math
import unreal as u

with open('E:/Construction_Demo/Saved/worker-retarget-report.json') as handle:
    manifest = json.load(handle)
assert manifest.get('complete'), 'Retarget batch did not finish'
mesh = u.load_asset(manifest['target_mesh'])
skeleton = mesh.get_editor_property('skeleton')
options = u.AnimPoseEvaluationOptions()
options.optional_skeletal_mesh = mesh
root = u.IKRigController.get_controller(u.load_asset('/Game/PPEWorker/Rigs/IK_PPE_Worker')).get_retarget_root()
report = {'clips': [], 'errors': [], 'root_bone': str(root)}
for entry in manifest['clips']:
    anim = u.load_asset(entry['asset'])
    source = u.load_asset(entry['source'])
    assert anim and anim.get_editor_property('skeleton') == skeleton, entry['asset']
    assert abs(anim.get_play_length() - source.get_play_length()) < 0.04, entry['asset']
    samples = []
    for fraction in (0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875, 1):
        pose = u.AnimPoseExtensions.get_anim_pose_at_time(anim, fraction * anim.get_play_length(), options)
        bones = u.AnimPoseExtensions.get_bone_names(pose)
        assert len(bones) >= 60, entry['asset']
        for bone in bones:
            transform = u.AnimPoseExtensions.get_bone_pose(pose, bone, u.AnimPoseSpaces.WORLD)
            location = transform.translation
            assert all(math.isfinite(v) for v in (location.x, location.y, location.z)), entry['asset']
        transform = u.AnimPoseExtensions.get_bone_pose(pose, root, u.AnimPoseSpaces.WORLD)
        samples.append([transform.translation.x, transform.translation.y, transform.translation.z])
    span = [max(p[axis] for p in samples) - min(p[axis] for p in samples) for axis in range(3)]
    if entry['name'] in ('Walk', 'Jog', 'CarryLoad', 'Cartwheel'):
        assert max(span[:2]) < 25, 'Locomotion trajectory remains: ' + entry['asset']
    report['clips'].append({'asset': entry['asset'], 'duration': anim.get_play_length(),
                            'bones': len(bones), 'pose_samples': len(samples),
                            'root_span_cm': span, 'skeleton_matches': True})
assert len(report['clips']) == 20
report['passed'] = True
with open('E:/Construction_Demo/Saved/worker-retarget-validation.json', 'w') as handle:
    json.dump(report, handle, indent=2)
u.log('PPE_RETARGET_VALIDATION_PASSED ' + str(len(report['clips'])))
