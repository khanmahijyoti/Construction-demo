import json
import math
import unreal as u

SOURCE = '/Game/NPCsBundle/Demo/Characters/Mannequins/Animations/Manny/MM_Walk_Fwd'
OUTPUT = '/Game/PPEWorker/Animations/A_Worker_Walk_Fwd'
SEQUENCE = '/Game/PPEWorker/Sequences/LS_HazardWorkerActivity'
assets = u.EditorAssetLibrary
source_anim = u.load_asset(SOURCE)
source_mesh = u.load_asset('/Game/NPCsBundle/Demo/Characters/Mannequins/Meshes/SKM_Manny_Simple')
target_mesh = u.load_asset('/Game/PPEWorker/Parts/SK_Body')
retargeter = u.load_asset('/Game/PPEWorker/Rigs/RTG_Manny_PPEWorker')
assert source_anim and source_mesh and target_mesh and retargeter
assert source_anim.get_editor_property('skeleton') == source_mesh.get_editor_property('skeleton')
anim = u.load_asset(OUTPUT)
if not anim:
    inputs = u.IKRetargetBatchOperationInputs()
    inputs.assets_to_retarget = [assets.find_asset_data(SOURCE)]
    inputs.source_mesh = source_mesh
    inputs.target_mesh = target_mesh
    inputs.ik_retarget_asset = retargeter
    inputs.target_path = '/Game/PPEWorker/Animations'
    inputs.use_source_path = False
    inputs.search = 'MM_Walk_Fwd'
    inputs.replace = 'A_Worker_Walk_Fwd'
    inputs.include_referenced_assets = False
    inputs.overwrite_existing_files = False
    results = u.IKRetargetBatchOperation.run_batch_retarget(inputs)
    assert len(results)==1
    anim = results[0].get_asset()
assert anim.get_path_name().split('.')[0] == OUTPUT
assert anim.get_editor_property('skeleton') == target_mesh.get_editor_property('skeleton')
assert abs(anim.get_play_length()-source_anim.get_play_length()) < .04


options = u.AnimPoseEvaluationOptions()
options.optional_skeletal_mesh = target_mesh
options.should_retarget = False
model = anim.get_editor_property('data_model_interface')
count = model.get_number_of_keys()
poses = [u.AnimPoseExtensions.get_anim_pose_at_time(anim,anim.get_play_length()*i/(count-1),options)
         for i in range(count)]
root = u.AnimPoseExtensions.get_bone_names(poses[0])[0]
transforms = [u.AnimPoseExtensions.get_bone_pose(p,root,u.AnimPoseSpaces.LOCAL) for p in poses]
a,b = transforms[0].translation,transforms[-1].translation
drift = (b.x-a.x,b.y-a.y,b.z-a.z)
positions = [u.Vector(t.translation.x-drift[0]*i/(count-1),
                      t.translation.y-drift[1]*i/(count-1),
                      t.translation.z-drift[2]*i/(count-1)) for i,t in enumerate(transforms)]
controller = anim.get_editor_property('controller')
if not controller:
    controller = u.new_object(u.AnimDataController,outer=anim)
    controller.set_model(model)
assert controller.set_bone_track_keys(root,positions,[t.rotation for t in transforms],
                                     [t.scale3d for t in transforms],False)
anim.set_editor_property('enable_root_motion',False)
assert assets.save_loaded_asset(anim)

sequence = u.load_asset(SEQUENCE)
assert sequence
sequence.modify()
changed = 0
for binding in sequence.get_bindings():
    for track in binding.get_tracks():
        if not isinstance(track,u.MovieSceneSkeletalAnimationTrack):
            continue
        for section in track.get_sections():
            params = section.get_editor_property('params')
            if params.animation and params.animation.get_name() in ('A_Worker_Walk','A_Worker_Walk_Fwd'):
                section.modify()
                params.animation = anim
                section.set_editor_property('params',params)
                changed += 1
assert changed > 0, 'No walking sections found'
assert assets.save_loaded_asset(sequence,only_if_is_dirty=False)

hips = []
for fraction in (0,.125,.25,.375,.5,.625,.75,.875,1):
    p = u.AnimPoseExtensions.get_anim_pose_at_time(anim,anim.get_play_length()*fraction,options)
    for name in u.AnimPoseExtensions.get_bone_names(p):
        t = u.AnimPoseExtensions.get_bone_pose(p,name,u.AnimPoseSpaces.WORLD).translation
        assert all(math.isfinite(v) for v in (t.x,t.y,t.z))
    t = u.AnimPoseExtensions.get_bone_pose(p,'Hips',u.AnimPoseSpaces.WORLD).translation
    hips.append((t.x,t.y,t.z))
span = [max(p[i] for p in hips)-min(p[i] for p in hips) for i in range(3)]
assert max(span[:2]) < 25, 'Walk still has world travel'
report = {'source':SOURCE,'asset':anim.get_path_name(),'duration':anim.get_play_length(),
          'removed_root_travel_cm':drift,'hips_span_cm':span,'sequence':SEQUENCE,
          'walking_sections_updated':changed,'skeleton_matches':True,'passed':True}
with open('E:/Construction_Demo/Saved/worker-forward-walk-update.json','w') as handle:
    json.dump(report,handle,indent=2)
u.log('WORKER_FORWARD_WALK_UPDATED '+str(changed))
