import json
import unreal as u

ROOT = '/Game/PPEWorker'
RIGS = ROOT + '/Rigs'
DEST = ROOT + '/Animations'
REPORT = 'E:/Construction_Demo/Saved/worker-retarget-report.json'
tools = u.AssetToolsHelpers.get_asset_tools()
assets = u.EditorAssetLibrary
registry = u.AssetRegistryHelpers.get_asset_registry()
registry.search_all_assets(True)
source = u.load_asset('/Game/NPCsBundle/Demo/Characters/Mannequins/Meshes/SKM_Manny_Simple')
target = u.load_asset(ROOT + '/Parts/SK_Body')
assert source and target
target_skeleton = target.get_editor_property('skeleton')

def rig(name, mesh):
    result = u.load_asset(RIGS + '/' + name)
    if not result:
        result = tools.create_asset(name, RIGS, u.IKRigDefinition, u.IKRigDefinitionFactory())
        controller = u.IKRigController.get_controller(result)
        controller.set_skeletal_mesh(mesh)
        assert controller.apply_auto_generated_retarget_definition(), 'Rig characterization failed: ' + name
        controller.apply_auto_fbik()
    assert assets.save_loaded_asset(result)
    return result

source_rig = rig('IK_Manny_Source', source)
target_rig = rig('IK_PPE_Worker', target)
retargeter = u.load_asset(RIGS + '/RTG_Manny_PPEWorker')
if not retargeter:
    retargeter = tools.create_asset('RTG_Manny_PPEWorker', RIGS, u.IKRetargeter, u.IKRetargetFactory())
    controller = u.IKRetargeterController.get_controller(retargeter)
    controller.set_ik_rig(u.RetargetSourceOrTarget.SOURCE, source_rig)
    controller.set_ik_rig(u.RetargetSourceOrTarget.TARGET, target_rig)
    controller.set_preview_mesh(u.RetargetSourceOrTarget.SOURCE, source)
    controller.set_preview_mesh(u.RetargetSourceOrTarget.TARGET, target)
    controller.add_default_ops()
    controller.auto_map_chains(u.AutoMapChainType.EXACT, True)
    controller.auto_align_all_bones(u.RetargetSourceOrTarget.TARGET)
assert assets.save_loaded_asset(retargeter)

work_names = ['Idle', 'Idle1H', 'Idle2H', 'IdleBreak1', 'IdleBreak2',
              'CarryLoad', 'Cartwheel', 'Equip1H', 'Equip2H', 'Unequip1H', 'Unequip2H',
              'HammeringFloor', 'HammeringWall', 'DrillingFloor', 'DrillWall',
              'Jackhammer', 'PickaxeMining', 'SawFloorVar1']
clips = [(name, '/Game/NPCsBundle/Animations/ConstructionWorker/A_' + name) for name in work_names]
clips += [('Walk', '/Game/NPCsBundle/Demo/Characters/Mannequins/Animations/Manny/MM_Walk_InPlace'),
          ('Jog', '/Game/NPCsBundle/Demo/Characters/Mannequins/Animations/Manny/MM_Run_Fwd')]
report = {'target_mesh': target.get_path_name(), 'target_skeleton': target_skeleton.get_path_name(),
          'retargeter': retargeter.get_path_name(), 'clips': [], 'errors': [],
          'visual_review': 'Pending user preview; props and runtime animation transitions are not included.'}
for name, path in clips:
    source_anim = u.load_asset(path)
    assert source_anim, path
    assert source_anim.get_editor_property('skeleton') == source.get_editor_property('skeleton'), path
    output = DEST + '/A_Worker_' + name
    baked = u.load_asset(output)
    if not baked:
        inputs = u.IKRetargetBatchOperationInputs()
        inputs.assets_to_retarget = [assets.find_asset_data(path)]
        inputs.source_mesh = source
        inputs.target_mesh = target
        inputs.ik_retarget_asset = retargeter
        inputs.target_path = DEST
        inputs.use_source_path = False
        inputs.search = source_anim.get_name()
        inputs.replace = 'A_Worker_' + name
        inputs.include_referenced_assets = False
        inputs.overwrite_existing_files = False
        results = u.IKRetargetBatchOperation.run_batch_retarget(inputs)
        assert len(results) == 1, 'Unexpected output: ' + name
        baked = results[0].get_asset()
        assert baked.get_path_name().split('.')[0] == output, baked.get_path_name()

    baked.set_editor_property('enable_root_motion', False)
    assert baked.get_editor_property('skeleton') == target_skeleton, output
    assert abs(baked.get_play_length() - source_anim.get_play_length()) < 0.04, output
    assert assets.save_loaded_asset(baked), output
    report['clips'].append({'name': name, 'source': path, 'asset': baked.get_path_name(),
                            'duration': baked.get_play_length(), 'skeleton_matches': True})
    with open(REPORT, 'w') as handle:
        json.dump(report, handle, indent=2)
    u.log('PPE_RETARGET_CLIP_COMPLETE ' + name)
existing = u.load_asset(DEST + '/A_Worker_Shoveling')
assert existing.get_editor_property('skeleton') == target_skeleton
report['existing_shoveling_preserved'] = existing.get_path_name()
report['complete'] = True
with open(REPORT, 'w') as handle:
    json.dump(report, handle, indent=2)
u.log('PPE_RETARGET_COMPLETE ' + str(len(report['clips'])))
