import json
import math
import sys
from pathlib import Path
import unreal as u

ROOT = Path('E:/Construction_Demo')
sys.path.insert(0,str(ROOT/'Scripts'))
from worker_activity_plan import sample, build_plan
levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
assert levels.load_level('/Game/ConstructionSite/Maps/Showcase')
world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
actors = u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
workers = {a.get_actor_label():a for a in actors if 'HazardSiteWorker' in [str(t) for t in a.tags]}
director = next(a for a in actors if a.get_actor_label()=='Hazard Worker Activity - Auto Play')
sequence = director.get_sequence()
assert sequence and director.playback_settings.auto_play
assert director.playback_settings.loop_count.value == -1
options = u.AnimPoseEvaluationOptions()
options.optional_skeletal_mesh = u.load_asset('/Game/PPEWorker/Parts/SK_Body')
idle = u.load_asset('/Game/PPEWorker/Animations/A_Worker_Idle')
pose = u.AnimPoseExtensions.get_anim_pose_at_time(idle,0.,options)
foot = u.AnimPoseExtensions.get_bone_pose(pose,'LeftFoot',u.AnimPoseSpaces.WORLD).translation
toe = u.AnimPoseExtensions.get_bone_pose(pose,'LeftToeBase',u.AnimPoseSpaces.WORLD).translation
forward_yaw = math.degrees(math.atan2(toe.y-foot.y,toe.x-foot.x))
plan = build_plan(json.loads((ROOT/'Saved/hazard-site-inventory.json').read_text()),
                  json.loads((ROOT/'Saved/hazard-workers-placement.json').read_text()),forward_yaw)
(ROOT/'Saved/worker-activity-plan.json').write_text(json.dumps(plan,indent=2))
tools = [a for a in actors if 'HazardWorkerTool' in [str(t) for t in a.tags]]
assert len(tools)==7
(ROOT/'Saved/worker-activity-build.json').write_text(json.dumps({
    'sequence':sequence.get_path_name(),'duration':180,'worker_count':len(workers),
    'tool_count':len(tools),'model_forward_yaw':forward_yaw,'saved':True,
    'minimum_worker_separation_cm':plan['minimum_worker_separation_cm']},indent=2))
settings = u.MovieSceneSequencePlaybackSettings()
player, temp = u.LevelSequencePlayer.create_level_sequence_player(world,sequence,settings)
assert player
report = {'samples':[],'errors':[],'sequence':sequence.get_path_name()}
for time in (0,10,15,20,35,55,65,75,88,110,140,150,165,179,0):
    params = u.MovieSceneSequencePlaybackParams(time=float(time),position_type=u.MovieScenePositionType.TIME,
                                               update_method=u.UpdatePositionMethod.JUMP)
    player.set_playback_position(params)
    entry = {'time':time,'workers':[]}
    for schedule in plan['workers']:
        actor = workers[schedule['label']]
        p = actor.get_actor_location()
        expected = sample(schedule['keys'],time)
        error = math.sqrt(sum((a-b)**2 for a,b in zip((p.x,p.y,p.z),expected[:3])))
        assert error < 2, 'Sequence transform did not evaluate: '+actor.get_actor_label()+' t='+str(time)+' error='+str(error)
        assert actor.shirt.get_editor_property('leader_pose_component') == actor.mesh
        assert actor.pants.get_editor_property('leader_pose_component') == actor.mesh
        entry['workers'].append({'label':actor.get_actor_label(),'location_error_cm':error,
                                 'animation_mode':str(actor.mesh.get_editor_property('animation_mode'))})
    report['samples'].append(entry)
player.stop()
temp.destroy_actor()
report['passed'] = True
(ROOT/'Saved/worker-activity-validation.json').write_text(json.dumps(report,indent=2))
u.log('WORKER_ACTIVITY_VALIDATED')
