import unreal as u,time,os,json,traceback
levels=u.get_editor_subsystem(u.LevelEditorSubsystem)
levels.load_level('/Game/PPEWorker/Maps/L_WorkerShowcase')
actors=u.get_editor_subsystem(u.EditorActorSubsystem)
workers=[a for a in actors.get_all_level_actors() if isinstance(a,u.PPEConstructionWorker)]
for actor in workers:actor.apply_appearance()
camera=next(a for a in actors.get_all_level_actors() if a.get_actor_label()=='Worker Showcase Camera')
u.EditorLevelLibrary.set_level_viewport_camera_info(camera.get_actor_location(),camera.get_actor_rotation())
start=time.monotonic();state={'shot':False}
def tick(delta):
    elapsed=time.monotonic()-start
    if elapsed>10 and not state['shot']:
        state['shot']=True
        u.AutomationLibrary.take_high_res_screenshot(1600,1000,'E:/Odyssey/output/ppe-demo/unreal-showcase.png',camera=camera)
        u.log('PPE_PREVIEW_CAPTURE_REQUESTED')
    if elapsed>20:
        u.unregister_slate_post_tick_callback(state['handle'])
        u.SystemLibrary.quit_editor()
state['handle']=u.register_slate_post_tick_callback(tick)
