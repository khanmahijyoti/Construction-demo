import json
import unreal as u

report = {'api': {}, 'props': {}, 'demo_tools': []}
for cls, names in [(u.LevelSequence, ['add_possessable', 'set_display_rate', 'set_tick_resolution', 'get_bindings']),
                   (u.MovieSceneScriptingDoubleChannel, ['add_key', 'set_default']),
                   (u.MovieSceneSkeletalAnimationSection, ['set_range', 'get_all_channels', 'set_completion_mode']),
                   (u.LevelSequencePlayer, ['create_level_sequence_player', 'set_playback_position'])]:
    for name in names:
        report['api'][cls.__name__+'.'+name] = getattr(cls, name).__doc__
for name in ['P_Shovel', 'P_Drill', 'P_Jackhammer', 'P_Pickaxe', 'P_Saw']:
    mesh = u.load_asset('/Game/NPCsBundle/Demo/Props/' + name)
    report['props'][name] = str(mesh.get_bounding_box())
levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
assert levels.load_level('/Game/NPCsBundle/Map/ConstructionWorkers')
for actor in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
    for comp in actor.get_components_by_class(u.StaticMeshComponent):
        if comp.static_mesh and '/Props/' in comp.static_mesh.get_path_name():
            report['demo_tools'].append({'actor': actor.get_actor_label(), 'mesh': comp.static_mesh.get_path_name(),
                                         'relative': str(comp.get_relative_transform()),
                                         'socket': str(comp.get_attach_socket_name()),
                                         'parent': comp.get_attach_parent().get_name() if comp.get_attach_parent() else None})
with open('E:/Construction_Demo/Saved/scenario-authoring-api.json', 'w') as handle:
    json.dump(report, handle, indent=2)
u.log('SCENARIO_API_INSPECTED')
