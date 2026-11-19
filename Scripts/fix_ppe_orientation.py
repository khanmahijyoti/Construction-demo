import unreal as u,json
levels=u.get_editor_subsystem(u.LevelEditorSubsystem);levels.load_level('/Game/PPEWorker/Maps/L_WorkerShowcase')
actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
before=[]
test=u.Rotator(pitch=0,yaw=180,roll=0)
u.log('PPE_ROTATOR_TEST '+str(test))
for a in actors:
    a.modify()
    if a.root_component:a.root_component.modify()
    if isinstance(a,u.PPEConstructionWorker) or isinstance(a,u.TextRenderActor):
        before.append({'name':a.get_actor_label(),'rotation':str(a.get_actor_rotation())})
        a.set_actor_rotation(u.Rotator(pitch=0,yaw=180,roll=0),False)
        u.log('PPE_AFTER_ROTATION '+a.get_actor_label()+' '+str(a.get_actor_rotation()))
        if isinstance(a,u.PPEConstructionWorker):a.apply_appearance()
    elif isinstance(a,u.DirectionalLight):a.set_actor_rotation(u.Rotator(pitch=-45,yaw=-35,roll=0),False)
    elif isinstance(a,u.PlayerStart):a.set_actor_rotation(u.Rotator(pitch=-8,yaw=0,roll=0),False)
    elif isinstance(a,u.CameraActor):
        rot=u.MathLibrary.find_look_at_rotation(a.get_actor_location(),u.Vector(250,345,80))
        a.set_actor_rotation(u.Rotator(pitch=rot.pitch,yaw=rot.yaw,roll=0),False)
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
if not u.EditorLoadingAndSavingUtils.save_map(world,'/Game/PPEWorker/Maps/L_WorkerShowcase'):
    raise RuntimeError('Could not save corrected showcase map')
with open('E:/Odyssey/output/ppe-demo/orientation-fix.json','w') as f:json.dump(before,f,indent=2)
u.log('PPE_ORIENTATION_FIXED '+str(before[:2]))
