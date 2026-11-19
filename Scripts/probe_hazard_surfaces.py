import json
import unreal as u

levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
if world.get_name() != 'Showcase':
    assert levels.load_level('/Game/ConstructionSite/Maps/Showcase')
    world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
report = {'map': world.get_path_name(), 'points': []}
camera = u.EditorLevelLibrary.get_level_viewport_camera_info()
report['viewport_camera'] = str(camera)
for x in (0, 300, 450, 550, 650, 1000, 1500, 2000, 2500, 2900, 3200):
    for y in (2550, 2750, 3050, 3150, 3450, 3550, 3700, 3950, 4200):
        result = u.SystemLibrary.line_trace_single(world, u.Vector(x, y, 200), u.Vector(x, y, -1200),
                         u.TraceTypeQuery.TRACE_TYPE_QUERY1, True, [], u.DrawDebugTrace.NONE, True)
        if result:
            parts = result.to_tuple()
            if not parts[0]:
                continue
            point = parts[5]
            actor = parts[9]
            report['points'].append({'x': x, 'y': y, 'z': point.z,
                                     'actor': actor.get_actor_label() if actor else None})
with open('E:/Construction_Demo/Saved/hazard-surface-probes.json', 'w') as handle:
    json.dump(report, handle, indent=2)
u.log('HAZARD_PROBE_COMPLETE')
