import json
import unreal as u

assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Game/ConstructionSite/Maps/Showcase')
actors = u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
director = next(a for a in actors if a.get_actor_label()=='Hazard Worker Activity - Auto Play')
sequence = director.get_sequence()
forward, old = 0, 0
for binding in sequence.get_bindings():
    for track in binding.get_tracks():
        if isinstance(track,u.MovieSceneSkeletalAnimationTrack):
            for section in track.get_sections():
                anim = section.get_editor_property('params').animation
                if anim:
                    forward += anim.get_name()=='A_Worker_Walk_Fwd'
                    old += anim.get_name()=='A_Worker_Walk'
assert forward == 107 and old == 0, (forward,old)
assert director.playback_settings.auto_play
report = {'level':'/Game/ConstructionSite/Maps/Showcase','sequence':sequence.get_path_name(),
          'walking_animation':'/Game/PPEWorker/Animations/A_Worker_Walk_Fwd',
          'forward_walk_sections':forward,'old_walk_sections':old,'autoplay':True,'reload_verified':True}
with open('E:/Construction_Demo/Saved/showcase-forward-walk.json','w') as handle:
    json.dump(report,handle,indent=2)
u.log('SHOWCASE_FORWARD_WALK_RELOAD_VERIFIED')
