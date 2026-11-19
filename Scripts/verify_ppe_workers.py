import unreal as u,json,math
levels=u.get_editor_subsystem(u.LevelEditorSubsystem)
levels.load_level('/Game/PPEWorker/Maps/L_WorkerShowcase')
workers=[a for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors() if isinstance(a,u.PPEConstructionWorker)]
report={'worker_count':len(workers),'errors':[],'workers':[]}
for a in workers:
    parts=[a.shirt,a.pants,a.boots,a.safety_vest,a.casual_vest,a.helmet,a.beard,a.eyelashes,a.scalp,a.hair]
    rotation=a.get_actor_rotation()
    entry={'actor':a.get_actor_label(),'rotation':{'pitch':rotation.pitch,'yaw':rotation.yaw,'roll':rotation.roll},'helmet':a.wear_helmet,'safety_vest':a.wear_safety_vest,'beard':a.has_beard,'body_materials_before_refresh':[m.get_name() if m else None for m in a.mesh.get_materials()]}
    if abs(rotation.roll)>0.1 or abs(rotation.pitch)>0.1:report['errors'].append(a.get_actor_label()+': inverted actor orientation')
    a.apply_appearance()
    for part in parts:
        if not part.get_skinned_asset():report['errors'].append(a.get_actor_label()+': missing '+part.get_name())
        if part.get_editor_property('leader_pose_component')!=a.mesh:report['errors'].append(a.get_actor_label()+': leader mismatch '+part.get_name())
    if a.helmet.is_visible()!=a.wear_helmet:report['errors'].append(a.get_actor_label()+': helmet state')
    if a.safety_vest.is_visible()!=a.wear_safety_vest:report['errors'].append(a.get_actor_label()+': vest state')
    if a.beard.is_visible()!=a.has_beard:report['errors'].append(a.get_actor_label()+': beard state')
    if not all(m for m in a.mesh.get_materials()):report['errors'].append(a.get_actor_label()+': missing body material')
    report['workers'].append(entry)
hero=next(a for a in workers if a.get_actor_label()=='Animated Shoveling Preview')
before=(hero.wear_helmet,hero.wear_safety_vest,hero.has_beard)
hero.wear_helmet=False;hero.wear_safety_vest=False;hero.has_beard=False;hero.apply_appearance()
report['toggle_test']={'helmet_hidden':not hero.helmet.is_visible(),'safety_vest_hidden':not hero.safety_vest.is_visible(),'casual_vest_visible':hero.casual_vest.is_visible(),'beard_hidden':not hero.beard.is_visible(),'hair_visible':hero.hair.is_visible()}
hero.wear_helmet,hero.wear_safety_vest,hero.has_beard=before;hero.apply_appearance()
report['animation_skeleton_matches']=hero.animation_clip.get_editor_property('skeleton')==hero.get_editor_property('body_asset').get_editor_property('skeleton')
with open('E:/Odyssey/output/ppe-demo/unreal-validation.json','w') as f:json.dump(report,f,indent=2)
if report['errors'] or not all(report['toggle_test'].values()) or not report['animation_skeleton_matches']:raise RuntimeError(str(report))
u.log('PPE_VALIDATION_PASSED '+str(len(workers)))
