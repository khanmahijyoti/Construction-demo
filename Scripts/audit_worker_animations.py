import json
import unreal as u

registry = u.AssetRegistryHelpers.get_asset_registry()
registry.search_all_assets(True)
report = {"animations": [], "animation_blueprints": [], "blend_spaces": [], "errors": []}
for data in registry.get_assets_by_path('/Game', recursive=True):
    kind = str(data.asset_class_path.asset_name)
    if kind not in ('AnimSequence', 'AnimBlueprint', 'BlendSpace', 'BlendSpace1D', 'AnimMontage'):
        continue
    asset = data.get_asset()
    entry = {'path': asset.get_path_name(), 'class': kind}
    try:
        skeleton = asset.get_editor_property('target_skeleton' if kind == 'AnimBlueprint' else 'skeleton')
        entry['skeleton'] = skeleton.get_path_name() if skeleton else None
        if kind == 'AnimSequence':
            entry['duration'] = asset.get_play_length()
            for prop in ('number_of_sampled_keys', 'enable_root_motion', 'rate_scale'):
                try:
                    entry[prop] = str(asset.get_editor_property(prop))
                except Exception:
                    pass
        key = 'animation_blueprints' if kind == 'AnimBlueprint' else 'blend_spaces' if kind.startswith('BlendSpace') else 'animations'
        report[key].append(entry)
    except Exception as exc:
        report['errors'].append({'path': entry['path'], 'error': str(exc)})
body = u.load_asset('/Game/PPEWorker/Parts/SK_Body')
report['ppe_skeleton'] = body.get_editor_property('skeleton').get_path_name()
bp = u.load_asset('/Game/PPEWorker/Blueprints/BP_ConstructionWorker')
default = u.get_default_object(bp.generated_class())
report['ppe_default_clip'] = default.animation_clip.get_path_name() if default.animation_clip else None
report['ppe_animation_mode'] = str(default.mesh.get_editor_property('animation_mode'))
report['ppe_anim_class'] = str(default.mesh.get_editor_property('anim_class'))
with open('E:/Construction_Demo/Saved/worker-animation-audit.json', 'w') as handle:
    json.dump(report, handle, indent=2)
u.log('WORKER_ANIMATION_AUDIT_COMPLETE ' + str(len(report['animations'])))
