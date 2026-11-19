import json
import os
import time
import traceback
from pathlib import Path
import unreal as u

OUT = Path('E:/Construction_Demo/AI/camera_frames')
OUT.mkdir(parents=True, exist_ok=True)
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
game_world = editor.get_game_world()
actors_api = u.get_editor_subsystem(u.EditorActorSubsystem)
levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
world = game_world or editor.get_editor_world()
actors = (u.GameplayStatics.get_all_actors_of_class(world, u.Actor) if game_world
          else actors_api.get_all_level_actors())
cameras = [a for a in actors if a.get_class().get_name().startswith('BP_Camera_C')]
assert len(cameras) == 1, 'Expected exactly one BP_Camera in the current world'
camera = cameras[0]
cap = camera.get_component_by_class(u.SceneCaptureComponent2D)
assert cap and cap.texture_target, 'BP_Camera requires a scene capture and render target'
location, rotation = cap.get_world_location(), cap.get_world_rotation()
old_view_location, old_view_rotation = u.EditorLevelLibrary.get_level_viewport_camera_info()
old_pilot = levels.get_pilot_level_actor()
old_game_view = levels.editor_get_game_view()
performance = None
try:
    settings = u.get_default_object(u.load_class(None, '/Script/UnrealEd.EditorPerformanceSettings'))
    old_throttle = settings.get_editor_property('bThrottleCPUWhenNotForeground')
    settings.set_editor_property('bThrottleCPUWhenNotForeground', False)
    performance = settings
except Exception:
    u.log_warning('Background CPU override unavailable; keep the Unreal viewport visible while streaming')
controller = u.GameplayStatics.get_player_controller(world, 0) if game_world else None
old_target = controller.get_view_target() if controller else None
if game_world:
    transform = u.Transform(location=location, rotation=rotation, scale=u.Vector(1, 1, 1))
    gameplay = u.get_default_object(u.GameplayStatics)
    reference_camera = gameplay.call_method('BeginDeferredActorSpawnFromClass', args=(
        world, u.CameraActor.static_class(), transform,
        u.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN, None,
        u.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
    gameplay.call_method('FinishSpawningActor', args=(
        reference_camera, transform, u.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
else:
    reference_camera = actors_api.spawn_actor_from_class(u.CameraActor, location, rotation, transient=True)
reference = reference_camera.get_component_by_class(u.CameraComponent)
reference.field_of_view = cap.fov_angle
scale = max(1., 1280. / max(cap.texture_target.size_x, cap.texture_target.size_y))
width, height = round(cap.texture_target.size_x * scale), round(cap.texture_target.size_y * scale)
reference.aspect_ratio = width / height
reference.constrain_aspect_ratio = True
active_camera = old_target.get_component_by_class(u.CameraComponent) if old_target else None
reference.post_process_settings = (active_camera.post_process_settings if active_camera
                                   else cap.post_process_settings).copy()
reference.post_process_blend_weight = (active_camera.post_process_blend_weight if active_camera
                                     else cap.post_process_blend_weight)
if controller:
    controller.set_view_target_with_blend(reference_camera, 0.)
else:
    levels.pilot_level_actor(reference_camera)
levels.editor_set_game_view(True)

meta = {'camera': camera.get_path_name(), 'transport': 'main_rendered_viewport',
        'width': width, 'height': height, 'color_encoding': 'display_sRGB',
        'exposure': 'game camera overrides plus scene post-process volumes; no extra exposure/gamma',
        'is_playing': bool(game_world),
        'fov': cap.fov_angle, 'location': str(location), 'rotation': str(rotation), 'samples': []}
state = {'start': time.monotonic(), 'last': 0., 'index': 0, 'finished': False,
         'pending': False, 'requesting': False}
limit = int(os.environ.get('YOLO_CAPTURE_COUNT', '0'))
stop_file = OUT / 'stop_capture'
stop_file.unlink(missing_ok=True)
interval = float(os.environ.get('YOLO_CAPTURE_INTERVAL', '0.1'))
pending_file = OUT / 'viewport_pending.png'
pending_file.unlink(missing_ok=True)

def finish():
    if state['finished']:
        return
    state['finished'] = True
    u.unregister_slate_post_tick_callback(state['handle'])
    if performance is not None:
        performance.set_editor_property('bThrottleCPUWhenNotForeground', old_throttle)
    try:
        if controller and old_target:
            controller.set_view_target_with_blend(old_target, 0.)
        if old_pilot:
            levels.pilot_level_actor(old_pilot)
        else:
            levels.eject_pilot_level_actor()
            u.EditorLevelLibrary.set_level_viewport_camera_info(old_view_location, old_view_rotation)
        levels.editor_set_game_view(old_game_view)
        if game_world:
            reference_camera.destroy_actor()
            remaining_cameras = u.GameplayStatics.get_all_actors_of_class(world, u.CameraActor)
        else:
            actors_api.destroy_actor(reference_camera)
            remaining_cameras = actors_api.get_all_level_actors()
        restored_location, restored_rotation = u.EditorLevelLibrary.get_level_viewport_camera_info()
        meta['restoration'] = {'temporary_camera_destroyed': reference_camera not in remaining_cameras,
                               'previous_view_location': str(old_view_location),
                               'restored_view_location': str(restored_location),
                               'previous_view_rotation': str(old_view_rotation),
                               'restored_view_rotation': str(restored_rotation)}
    except Exception:
        u.log_warning(traceback.format_exc())
    (OUT / 'capture_metadata.json').write_text(json.dumps(meta, indent=2))
    u._ppe_capture_finish = None
    u.log('YOLO_VIEWPORT_CAPTURE_COMPLETE ' + str(state['index']))
    if os.environ.get('YOLO_CAPTURE_QUIT') == '1':
        u.SystemLibrary.quit_editor()

def tick(delta):
    try:


        if state['requesting'] or state['finished']:
            return
        now = time.monotonic()
        levels.editor_invalidate_viewports()
        if game_world and not editor.get_game_world():
            finish()
            return
        if stop_file.exists():
            finish()
            return
        if state['pending']:
            if pending_file.exists() and pending_file.stat().st_size > 0:
                filename = 'frame_%06d.png' % (state['index'] if limit else state['index'] % 2)
                pending_file.replace(OUT / filename)
                meta['samples'].append({'file': filename, 'unix_time': time.time(),
                                       'game_time': u.GameplayStatics.get_time_seconds(world),
                                       'frame_number': state['index'] + 1})
                meta['samples'] = meta['samples'][-30:]
                state['pending'] = False
                state['index'] += 1
                state['last'] = now
                (OUT / 'capture_metadata.json').write_text(json.dumps(meta, indent=2))
                if limit and state['index'] >= limit:
                    finish()
            elif now - state['requested'] > 10:
                state['pending'] = False
                state['last'] = now
                u.log_warning('PPE frame stalled; requesting a fresh viewport frame')
            return
        if now - state['start'] < 20 or now - state['last'] < interval:
            return
        state['pending'] = True
        state['requesting'] = True
        try:
            state['task'] = u.AutomationLibrary.take_high_res_screenshot(
                width, height, str(pending_file), camera=reference_camera)
        finally:
            state['requesting'] = False
        state['requested'] = time.monotonic()
    except Exception:
        u.log_error(traceback.format_exc())
        finish()

state['handle'] = u.register_slate_post_tick_callback(tick)
u._ppe_capture_finish = finish
u.log('YOLO_VIEWPORT_CAPTURE_STARTED ' + str(width) + 'x' + str(height))
