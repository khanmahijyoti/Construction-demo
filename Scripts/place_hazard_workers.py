import json
import math
import unreal as u

MAP = '/Game/ConstructionSite/Maps/Showcase'
levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
actors = u.get_editor_subsystem(u.EditorActorSubsystem)
assert levels.load_level(MAP)
world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
before = actors.get_all_level_actors()
existing = {a.get_actor_label(): a for a in before}
report = {'map': MAP, 'actors_before': len(before), 'workers': [], 'errors': []}

placements = [
    ('01', '01_Helmet_And_Vest', 655, 3132, 145, 'Idle', 0.6, 'Plywood7'),
    ('02', '05_Medium_Clean_Both', 270, 3068, -55, 'IdleBreak1', 1.3, 'Plywood10'),
    ('03', '09_Deep_Beard_Both', 369, 3528, 20, 'IdleBreak2', 2.1, 'Plywood9'),
    ('04', '15_YellowVest_Charcoal_Shirt', 644, 3724, 195, 'Idle', 3.1, 'Plywood5'),
    ('05', '02_Helmet_Only', 980, 3078, 210, 'IdleBreak1', 2.8, 'ConcreteColumn1868'),
    ('06', '03_Vest_Only', 1500, 3608, 75, 'Idle', 1.8, 'ConcreteColumn1870'),
    ('07', '13_YellowVest_Olive_Shirt', 2000, 3078, 235, 'IdleBreak2', 0.9, 'ConcreteColumn1831'),
    ('08', '14_Helmet_Burgundy_Shirt', 2510, 3108, 120, 'Idle', 2.7, 'ConcreteColumn1871'),
    ('09', '16_NoPPE_Sand_Shirt', 2500, 4200, 180, 'IdleBreak1', 3.5, None),
    ('10', '11_Deep_Beard_Vest_Only', 3200, 3700, -70, 'Idle', 0.2, None),
]
tag = 'HazardSiteWorker'
with u.ScopedEditorTransaction('Place hazard site workers'):
    for number, preset, x, y, yaw, clip, offset, support_label in placements:
        label = 'Hazard Worker ' + number + ' - ' + preset.split('_', 1)[1]
        if support_label:


            support = existing[support_label]
            origin, extent = support.get_actor_bounds(False)
            assert abs(x-origin.x) < extent.x and abs(y-origin.y) < extent.y
            assert extent.z < 5, 'Expected a thin horizontal deck: ' + support_label
            point = u.Vector(x, y, origin.z + extent.z)
        else:
            result = u.SystemLibrary.line_trace_single(world, u.Vector(x, y, 150), u.Vector(x, y, -1200),
                              u.TraceTypeQuery.TRACE_TYPE_QUERY1, True, [], u.DrawDebugTrace.NONE, True)
            assert result, 'No surface at ' + label
            hit = result.to_tuple()
            assert hit[0], 'No blocking surface at ' + label
            point, normal, support = hit[5], hit[7], hit[9]
            assert normal.z > 0.7, 'Sloping/vertical support at ' + label

        assert point.z > -420 and point.z < 80, 'Unexpected support height at ' + label + ': ' + str(point.z)
        bp = u.load_asset('/Game/PPEWorker/Presets/BP_Worker_' + preset)
        assert bp, preset
        worker = existing.get(label)
        if worker:
            assert tag in [str(t) for t in worker.tags], 'Unmanaged actor label collision'
        else:
            worker = actors.spawn_actor_from_class(bp.generated_class(), u.Vector(x, y, point.z + 89),
                                                      u.Rotator(pitch=0, yaw=yaw, roll=0))
        worker.modify()
        worker.set_actor_label(label)
        worker.set_folder_path('Hazard Site Workers')
        worker.tags = [u.Name(tag)]
        worker.set_actor_location(u.Vector(x, y, point.z + 89), False, True)
        worker.set_actor_rotation(u.Rotator(pitch=0, yaw=yaw, roll=0), False)
        worker.animation_clip = u.load_asset('/Game/PPEWorker/Animations/A_Worker_' + clip)
        worker.animate = True
        worker.animation_offset = offset
        worker.animation_rate = 0.90 + (int(number) % 4) * 0.06
        worker.apply_appearance()
        worker.mesh.set_update_animation_in_editor(True)


        worker.character_movement.set_editor_property('default_land_movement_mode', u.MovementMode.MOVE_NONE)
        worker.character_movement.disable_movement()
        assert worker.animation_clip.get_editor_property('skeleton') == worker.get_editor_property('body_asset').get_editor_property('skeleton')
        for part in (worker.shirt, worker.pants, worker.boots, worker.safety_vest,
                     worker.casual_vest, worker.helmet, worker.beard, worker.eyelashes, worker.scalp, worker.hair):
            assert part.get_skinned_asset(), label + ': missing part'
            assert part.get_editor_property('leader_pose_component') == worker.mesh, label + ': leader mismatch'
        report['workers'].append({'label': label, 'preset': preset,
                                  'location': [x, y, point.z + 89], 'yaw': yaw,
                                  'support': support.get_actor_label(), 'surface_z': point.z,
                                  'animation': worker.animation_clip.get_path_name(),
                                  'helmet': worker.wear_helmet, 'vest': worker.wear_safety_vest})
    assert len(report['workers']) == 10
    assert len(actors.get_all_level_actors()) == len(before) + sum(p['label'] not in existing for p in report['workers'])
    assert levels.save_current_level()
report['saved'] = True
report['actors_after'] = len(actors.get_all_level_actors())
assert levels.load_level('/Game/ConstructionSite/Maps/Overview')
assert levels.load_level(MAP)
reloaded = actors.get_all_level_actors()
workers = [a for a in reloaded if tag in [str(t) for t in a.tags]]
assert len(workers) == 10, 'Saved worker count mismatch'
for worker in workers:
    entry = next(e for e in report['workers'] if e['label'] == worker.get_actor_label())
    location = worker.get_actor_location()
    assert abs(location.z - entry['location'][2]) < 0.1
    assert worker.animation_clip and worker.get_editor_property('body_asset')
    assert worker.shirt.get_skinned_asset() and worker.pants.get_skinned_asset()
    assert worker.helmet.is_visible() == worker.wear_helmet
    assert worker.safety_vest.is_visible() == worker.wear_safety_vest
    assert str(worker.character_movement.get_editor_property('default_land_movement_mode')) == str(u.MovementMode.MOVE_NONE)
report['reload_verified'] = True
with open('E:/Construction_Demo/Saved/hazard-workers-placement.json', 'w') as handle:
    json.dump(report, handle, indent=2)
u.log('HAZARD_WORKERS_PLACED ' + str(len(report['workers'])))
