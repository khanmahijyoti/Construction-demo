import json
import math
import re
import sys
from pathlib import Path
import unreal as u

ROOT = Path('E:/Construction_Demo')
sys.path.insert(0,str(ROOT/'Scripts'))
from worker_activity_plan import build_plan

MAP = '/Game/ConstructionSite/Maps/Showcase'
SEQ = '/Game/PPEWorker/Sequences/LS_HazardWorkerActivity'
FPS = 30
levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
actors = u.get_editor_subsystem(u.EditorActorSubsystem)
assets = u.EditorAssetLibrary


prop_specs = {}
mounts = json.loads((ROOT/'Saved/scenario-authoring-api.json').read_text())['demo_tools']
for mount in mounts:
    if mount['socket'] != 'ik_hand_gun':
        continue
    text = mount['relative']
    def values(field):
        return [float(v) for v in re.findall(r'[xyzw]: ([-+\d.eE]+)',re.search(field+r': \{([^}]+)\}',text).group(1))]
    q,p,s = values('rotation'),values('translation'),values('scale3d')
    name = mount['mesh'].rsplit('.',1)[-1]
    transform = u.Transform()
    transform.translation = u.Vector(*p)
    transform.rotation = u.Quat(*q)
    transform.scale3d = u.Vector(*s)
    prop_specs.setdefault(name,transform)

assert levels.load_level(MAP)
world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
all_actors = actors.get_all_level_actors()
workers = sorted([a for a in all_actors if 'HazardSiteWorker' in [str(t) for t in a.tags]],
                 key=lambda a:a.get_actor_label())
assert len(workers) == 10
inventory = {'actors': []}
for actor in all_actors:
    comp = actor.get_component_by_class(u.StaticMeshComponent)
    if not comp or not comp.static_mesh:
        continue
    origin, extent = actor.get_actor_bounds(False)
    inventory['actors'].append({'label':actor.get_actor_label(), 'mesh':comp.static_mesh.get_path_name(),
                                'origin':[origin.x,origin.y,origin.z], 'extent':[extent.x,extent.y,extent.z]})
placements = {'workers': []}
for actor in workers:
    p = actor.get_actor_location()
    placements['workers'].append({'label':actor.get_actor_label(),'location':[p.x,p.y,p.z],
                                  'yaw':actor.get_actor_rotation().yaw})

target_mesh = u.load_asset('/Game/PPEWorker/Parts/SK_Body')
source_mesh = u.load_asset('/Game/NPCsBundle/Demo/Characters/Mannequins/Meshes/SKM_Manny_Simple')
target_options, source_options = u.AnimPoseEvaluationOptions(), u.AnimPoseEvaluationOptions()
target_options.optional_skeletal_mesh = target_mesh
source_options.optional_skeletal_mesh = source_mesh
def pose(anim, options):
    return u.AnimPoseExtensions.get_anim_pose_at_time(anim,0.,options)
def bone(p, name):
    return u.AnimPoseExtensions.get_bone_pose(p,name,u.AnimPoseSpaces.WORLD)
def forward(p, foot, toe):
    a,b = bone(p,foot).translation,bone(p,toe).translation
    return math.degrees(math.atan2(b.y-a.y,b.x-a.x))
idle = u.load_asset('/Game/PPEWorker/Animations/A_Worker_Idle')
target_forward = forward(pose(idle,target_options),'LeftFoot','LeftToeBase')
source_idle = u.load_asset('/Game/NPCsBundle/Animations/ConstructionWorker/A_Idle')
source_forward = forward(pose(source_idle,source_options),'foot_l','ball_l')
plan = build_plan(inventory,placements,target_forward)

sequence = u.load_asset(SEQ)
if sequence:
    for binding in list(sequence.get_bindings()):
        binding.remove()
else:
    sequence = u.AssetToolsHelpers.get_asset_tools().create_asset('LS_HazardWorkerActivity',
                     '/Game/PPEWorker/Sequences',u.LevelSequence,u.LevelSequenceFactoryNew())
sequence.set_display_rate(u.FrameRate(FPS,1))
sequence.set_tick_resolution(u.FrameRate(FPS,1))
sequence.set_playback_start(0)
sequence.set_playback_end(round(plan['duration']*FPS))
clips = {s['clip']:u.load_asset('/Game/PPEWorker/Animations/A_Worker_'+('Walk_Fwd' if s['clip']=='Walk' else s['clip']))
         for w in plan['workers'] for s in w['sections']}
assert all(clips.values())

def frame(t):
    return round(t*FPS)
def transform_track(binding, keys):
    track = binding.add_track(u.MovieScene3DTransformTrack)
    section = track.add_section()
    section.set_range(0,frame(plan['duration'])+1)
    section.set_completion_mode(u.MovieSceneCompletionMode.RESTORE_STATE)
    channels = section.get_channels_by_type(u.MovieSceneScriptingDoubleChannel)
    assert len(channels) == 9
    for i, value in enumerate((0.,0.,0.,0.,0.,0.,1.,1.,1.)):
        channels[i].set_default(value)
    for t,x,y,z,yaw in keys:
        for channel,value in zip(channels,(x,y,z,0.,0.,yaw,1.,1.,1.)):
            channel.add_key(u.FrameNumber(frame(t)),value,interpolation=u.MovieSceneKeyInterpolation.LINEAR)

tools_by_clip = {'Shoveling':'P_Shovel','DrillingFloor':'P_Drill','PickaxeMining':'P_Pickaxe',
                 'SawFloorVar1':'P_Saw','Jackhammer':'P_Jackhammer'}
known = {a.get_actor_label():a for a in all_actors}
report = {'sequence':SEQ,'duration':plan['duration'],'workers':[],'tool_count':0,
          'minimum_worker_separation_cm':plan['minimum_worker_separation_cm'],
          'model_forward_yaw':target_forward,'source_forward_yaw':source_forward}
for actor, schedule in zip(workers,plan['workers']):
    actor.modify()
    actor.animation_clip = idle
    actor.animation_offset = 0.
    actor.apply_appearance()
    home = schedule['keys'][0]
    actor.set_actor_location(u.Vector(*home[1:4]),False,True)
    actor.set_actor_rotation(u.Rotator(pitch=0,yaw=home[4],roll=0),False)
    actor.character_movement.disable_movement()
    actor_binding = sequence.add_possessable(actor)
    actor_binding.set_display_name(actor.get_actor_label())
    transform_track(actor_binding,schedule['keys'])
    body_binding = sequence.add_possessable(actor.mesh)
    body_binding.set_parent(actor_binding)
    body_binding.set_display_name('Body animation (clothes follow)')
    animation_track = body_binding.add_track(u.MovieSceneSkeletalAnimationTrack)
    for index, segment in enumerate(schedule['sections']):
        section = animation_track.add_section()

        blend = .16
        section.set_range(max(0,frame(segment['start']-blend)),
                          min(frame(plan['duration']),frame(segment['end']+blend)))
        params = section.get_editor_property('params')
        params.animation = clips[segment['clip']]
        params.force_custom_mode = True
        params.skip_anim_notifiers = True
        section.set_editor_property('params',params)
        weight = section.get_channels_by_type(u.MovieSceneScriptingFloatChannel)[0]
        start = max(0,frame(segment['start']-blend))
        end = min(frame(plan['duration']),frame(segment['end']+blend))
        fade = min(frame(blend*2),max(1,(end-start)//3))
        weight.set_default(1.)
        for at,value in ((start,1. if start==0 else 0.),(start+fade,1.),
                         (end-fade,1.),(end,1. if end==frame(plan['duration']) else 0.)):
            weight.add_key(u.FrameNumber(at),value,interpolation=u.MovieSceneKeyInterpolation.LINEAR)
        section.set_completion_mode(u.MovieSceneCompletionMode.RESTORE_STATE)
    work_clip = schedule['work_clip']
    tool_name = tools_by_clip.get(work_clip)
    if tool_name:

        source_anim = u.load_asset('/Game/NPCsBundle/Animations/ConstructionWorker/A_'+work_clip)
        source_pose = pose(source_anim,source_options)
        target_pose = pose(clips[work_clip],target_options)
        source_hand = bone(source_pose,'hand_r')
        target_hand = bone(target_pose,'RightHand')
        source_tool = u.MathLibrary.compose_transforms(prop_specs[tool_name],bone(source_pose,'ik_hand_gun'))
        source_hand_local = u.MathLibrary.make_relative_transform(source_tool,source_hand)
        rotation_align = u.Transform(rotation=u.Rotator(pitch=0,yaw=target_forward-source_forward,roll=0))
        aligned_hand = u.MathLibrary.compose_transforms(source_hand,rotation_align)
        aligned_hand.translation = target_hand.translation
        aligned_hand.scale3d = u.Vector(1,1,1)
        correction = u.MathLibrary.make_relative_transform(aligned_hand,target_hand)
        relative = u.MathLibrary.compose_transforms(source_hand_local,correction)
        label = actor.get_actor_label().split(' - ')[0]+' - '+tool_name
        tool = known.get(label) or actors.spawn_actor_from_class(u.StaticMeshActor,actor.get_actor_location())
        tool.modify()
        tool.set_actor_label(label)
        tool.set_folder_path('Hazard Site Workers/Work Tools')
        tool.tags = [u.Name('HazardWorkerTool')]
        tool.static_mesh_component.set_mobility(u.ComponentMobility.MOVABLE)
        tool.static_mesh_component.set_static_mesh(u.load_asset('/Game/NPCsBundle/Demo/Props/'+tool_name))
        tool.static_mesh_component.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
        assert tool.attach_to_component(actor.mesh,'RightHand',u.AttachmentRule.SNAP_TO_TARGET,
                           u.AttachmentRule.SNAP_TO_TARGET,u.AttachmentRule.KEEP_RELATIVE,False)
        tool.root_component.set_relative_transform(relative,False,True)
        tool.set_actor_hidden_in_game(True)
        binding = sequence.add_possessable(tool)
        binding.set_display_name(label+' (work only)')
        track = binding.add_track(u.MovieSceneVisibilityTrack)
        track.set_property_name_and_path('bHidden','bHidden')
        section = track.add_section()
        section.set_range(0,frame(plan['duration']))
        section.set_completion_mode(u.MovieSceneCompletionMode.RESTORE_STATE)
        channel = section.get_channels_by_type(u.MovieSceneScriptingBoolChannel)[0]
        channel.set_default(False)
        visibility = {0:False,frame(plan['duration']):False}
        for segment in schedule['sections']:
            if segment['state']=='work' and segment['clip']==work_clip:
                visibility[frame(segment['start'])] = True
                visibility[frame(segment['end'])] = False
        for time,value in sorted(visibility.items()):
            channel.add_key(u.FrameNumber(time),value)
        report['tool_count'] += 1
    report['workers'].append({'label':actor.get_actor_label(),'animation_sections':len(schedule['sections']),
                              'work_clip':work_clip,'tool':tool_name,'group_position':schedule['meeting']})

director = known.get('Hazard Worker Activity - Auto Play')
if not director:
    director = actors.spawn_actor_from_class(u.LevelSequenceActor,u.Vector(1500,3075,0))
director.set_actor_label('Hazard Worker Activity - Auto Play')
director.set_folder_path('Hazard Site Workers')
director.set_sequence(sequence)
settings = director.get_editor_property('playback_settings')
settings.auto_play = True
settings.loop_count = u.MovieSceneSequenceLoopCount(value=-1)
settings.disable_camera_cuts = True
settings.disable_movement_input = False
settings.disable_look_at_input = False
settings.hide_player = False
settings.hide_hud = False
director.set_editor_property('playback_settings',settings)
assert assets.save_loaded_asset(sequence)
assert levels.save_current_level()
report['saved'] = True
(ROOT/'Saved/worker-activity-plan.json').write_text(json.dumps(plan,indent=2))
(ROOT/'Saved/worker-activity-build.json').write_text(json.dumps(report,indent=2))
u.log('WORKER_ACTIVITY_BUILT '+str(len(workers)))
