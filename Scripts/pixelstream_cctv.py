import time
import traceback
import unreal as u

ASPECT_FROM_TARGET = True
state = {'start': time.monotonic(), 'ready_since': None, 'done': False, 'camera': None}


def attach_view_camera(camera, blueprint, capture):
    camera.set_owner(blueprint)
    attached = camera.attach_to_component(capture, '', u.AttachmentRule.SNAP_TO_TARGET,
                                          u.AttachmentRule.SNAP_TO_TARGET,
                                          u.AttachmentRule.KEEP_WORLD, False)
    if not attached:
        raise RuntimeError('Could not attach the CCTV view camera to BP_Camera scene capture')
    return camera


def game_world():
    for w in u.ObjectIterator(u.World):
        try:
            if w.get_name() != 'Untitled' and u.GameplayStatics.get_player_controller(w, 0):
                return w
        except Exception:
            pass
    return None


def apply_cctv(world):
    actors = u.GameplayStatics.get_all_actors_of_class(world, u.Actor)
    cams = [a for a in actors if a.get_class().get_name().startswith('BP_Camera_C')]
    if len(cams) != 1:
        raise RuntimeError(f'Expected exactly one BP_Camera, found {len(cams)}')
    cap = cams[0].get_component_by_class(u.SceneCaptureComponent2D)
    if not cap:
        raise RuntimeError('BP_Camera has no SceneCaptureComponent2D')
    transform = u.Transform(location=cap.get_world_location(), rotation=cap.get_world_rotation(),
                            scale=u.Vector(1, 1, 1))
    gameplay = u.get_default_object(u.GameplayStatics)
    actor = gameplay.call_method('BeginDeferredActorSpawnFromClass', args=(
        world, u.CameraActor.static_class(), transform,
        u.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN, None,
        u.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
    gameplay.call_method('FinishSpawningActor', args=(
        actor, transform, u.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
    attach_view_camera(actor, cams[0], cap)
    cam = actor.get_component_by_class(u.CameraComponent)
    cam.field_of_view = cap.fov_angle
    target = cap.texture_target
    if ASPECT_FROM_TARGET and target:
        cam.aspect_ratio = target.size_x / target.size_y
        cam.constrain_aspect_ratio = True
    controller = u.GameplayStatics.get_player_controller(world, 0)
    old = controller.get_view_target()
    active = old.get_component_by_class(u.CameraComponent) if old else None
    src = active if active else cap
    cam.post_process_settings = src.post_process_settings.copy()
    cam.post_process_blend_weight = src.post_process_blend_weight
    controller.set_view_target_with_blend(actor, 0.)
    state['camera'] = actor
    u.log(f'PPE_STREAM_CCTV_READY fov={cap.fov_angle:.1f} camera={cams[0].get_name()} attached_to={cap.get_name()}')


def tick(_delta):
    if state['done']:
        return
    try:
        world = game_world()
        if world is None:
            if time.monotonic() - state['start'] > 180:
                state['done'] = True
                u.log_error('PPE stream: no game world with a player controller after 180 s')
            return
        if state['ready_since'] is None:
            state['ready_since'] = time.monotonic()
        if time.monotonic() - state['ready_since'] < 1.0:
            return
        cam = state['camera']
        controller = u.GameplayStatics.get_player_controller(world, 0)
        if cam is None:
            apply_cctv(world)
        elif controller.get_view_target() != cam:

            controller.set_view_target_with_blend(cam, 0.)
    except Exception:
        state['done'] = True
        u.log_error('PPE stream CCTV setup failed:\n' + traceback.format_exc())


u._ppe_stream_tick = u.register_slate_post_tick_callback(tick)
u.log('PPE stream: waiting for the game world to set the BP_Camera view...')
