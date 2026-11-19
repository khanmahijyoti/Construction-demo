import json
import unreal as u

MAP = '/Game/ConstructionSite/Maps/Showcase'
levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
if not world or world.get_name() != 'Showcase':
    assert levels.load_level(MAP)
actors = u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
director = next(a for a in actors if a.get_actor_label()=='Hazard Worker Activity - Auto Play')
sequence = director.get_sequence()
anim = u.load_asset('/Game/PPEWorker/Animations/A_Worker_Walk_Fwd')
assert sequence and anim
sequence.modify()
count = 0
for binding in sequence.get_bindings():
    for track in binding.get_tracks():
        if isinstance(track,u.MovieSceneSkeletalAnimationTrack):
            for section in track.get_sections():
                params = section.get_editor_property('params')
                if params.animation and params.animation.get_name() in ('A_Worker_Walk','A_Worker_Walk_Fwd'):
                    section.modify()
                    params.animation = anim
                    section.set_editor_property('params',params)
                    count += 1
assert count > 0
assert u.EditorAssetLibrary.save_loaded_asset(sequence,only_if_is_dirty=False)
report = {'level':MAP,'level_sequence_actor':director.get_actor_label(),'sequence':sequence.get_path_name(),
          'animation':anim.get_path_name(),'walking_sections':count,'saved':True}
with open('E:/Construction_Demo/Saved/showcase-forward-walk.json','w') as handle:
    json.dump(report,handle,indent=2)
u.log('SHOWCASE_FORWARD_WALK_SAVED '+str(count))
