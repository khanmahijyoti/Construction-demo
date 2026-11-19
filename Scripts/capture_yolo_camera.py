import json
import os
import time
import traceback
from pathlib import Path
import unreal as u

OUT = Path('E:/Construction_Demo/AI/camera_frames')
OUT.mkdir(parents=True, exist_ok=True)
levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
if os.environ.get('YOLO_CAPTURE_QUIT') == '1' and '/Game/ConstructionSite/Maps/Showcase' not in u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world().get_path_name():
    assert levels.load_level('/Game/ConstructionSite/Maps/Showcase')
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
game_world = editor.get_game_world()
actors = (u.GameplayStatics.get_all_actors_of_class(game_world, u.Actor) if game_world
          else u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors())
candidates = [a for a in actors if a.get_class().get_name().startswith('BP_Camera_C')]
assert len(candidates) == 1, 'Expected exactly one BP_Camera; found ' + str(len(candidates))
camera = candidates[0]
capture = camera.get_component_by_class(u.SceneCaptureComponent2D)
assert capture, 'BP_Camera has no SceneCaptureComponent2D'
original = {'target': capture.texture_target, 'source': capture.capture_source,
            'every': capture.capture_every_frame, 'movement': capture.capture_on_movement,
            'visible': capture.is_visible(), 'persist': capture.always_persist_rendering_state,
            'flags': [f.copy() for f in capture.show_flag_settings],
            'post_blend': capture.post_process_blend_weight,
            'main_family': capture.main_view_family,
            'inherit_post': capture.inherit_main_view_camera_post_process_settings,
            'ray_tracing': capture.use_ray_tracing_if_enabled}
capture.set_visibility(True)
original_width, original_height = int(original['target'].size_x), int(original['target'].size_y)
scale = max(1.0, 1280.0 / max(original_width, original_height))
width, height = round(original_width * scale), round(original_height * scale)
target = u.RenderingLibrary.create_render_target2d(camera, width, height, u.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
capture.texture_target = target
capture.capture_source = u.SceneCaptureSource.SCS_FINAL_COLOR_LDR
capture.capture_every_frame = bool(game_world)
capture.capture_on_movement = not bool(game_world)
capture.always_persist_rendering_state = True
capture.main_view_family = True
capture.inherit_main_view_camera_post_process_settings = True
capture.set_component_tick_enabled(True)
capture.use_ray_tracing_if_enabled = True
original_post = capture.post_process_settings.copy()
post = original_post.copy()


post.override_dynamic_global_illumination_method = True
post.dynamic_global_illumination_method = u.DynamicGlobalIlluminationMethod.LUMEN
post.override_reflection_method = True
post.reflection_method = u.ReflectionMethod.LUMEN
post.override_lumen_surface_cache_resolution = True
post.lumen_surface_cache_resolution = 1.0


capture.post_process_settings = post
flag_overrides = {f.show_flag_name: f.enabled for f in original['flags']}
for flag in ['AntiAliasing', 'TemporalAA', 'EyeAdaptation', 'Tonemapper',
             'PostProcessing', 'Lighting', 'GlobalIllumination', 'LumenGlobalIllumination',
             'LumenReflections', 'ReflectionEnvironment']:
    flag_overrides[flag] = True
matched_flags = [u.EngineShowFlagsSetting(show_flag_name=name, enabled=enabled)
                 for name, enabled in flag_overrides.items()]


capture.call_method('SetShowFlagSettings', args=(matched_flags,))
meta = {'camera': camera.get_path_name(), 'width': width, 'height': height,
        'fov': capture.fov_angle, 'location': str(capture.get_world_location()),
        'rotation': str(capture.get_world_rotation()), 'original_source': str(original['source']),
        'export_source': str(capture.capture_source), 'color_encoding': 'sRGB', 'original_visible': original['visible'], 'original_size': [original_width, original_height],
        'exposure': 'original camera and scene post-process volumes; no brightness override',
        'temporal_aa': True, 'lumen_surface_cache_resolution': 1.0,
        'samples': [], 'worker_count': sum(isinstance(a, u.PPEConstructionWorker) for a in actors)}
state = {'start': time.monotonic(), 'last': 0, 'index': 0, 'finished': False}
limit = int(os.environ.get('YOLO_CAPTURE_COUNT', '0'))
stop_file = OUT / 'stop_capture'
stop_file.unlink(missing_ok=True)

def finish():
    if state['finished']:
        return
    state['finished'] = True
    capture.texture_target = original['target']
    capture.capture_source = original['source']
    capture.capture_every_frame = original['every']
    capture.capture_on_movement = original['movement']
    capture.set_visibility(original['visible'])
    capture.always_persist_rendering_state = original['persist']
    capture.post_process_settings = original_post
    capture.post_process_blend_weight = original['post_blend']
    capture.call_method('SetShowFlagSettings', args=(original['flags'],))
    capture.main_view_family = original['main_family']
    capture.inherit_main_view_camera_post_process_settings = original['inherit_post']
    capture.use_ray_tracing_if_enabled = original['ray_tracing']
    u.unregister_slate_post_tick_callback(state['handle'])
    (OUT / 'capture_metadata.json').write_text(json.dumps(meta, indent=2))
    u.log('YOLO_CAMERA_CAPTURE_COMPLETE ' + str(state['index']))
    if os.environ.get('YOLO_CAPTURE_QUIT') == '1':
        u.SystemLibrary.quit_editor()

def tick(delta):
    try:
        now = time.monotonic()
        if stop_file.exists():
            finish()
            return


        if not game_world:
            position = capture.get_world_location()
            capture.set_world_location(u.Vector(position.x + 0.01, position.y, position.z), False, True)
            capture.set_world_location(position, False, True)
        if now - state['start'] < 20 or now - state['last'] < 1:
            return
        state['last'] = now
        filename = 'frame_%06d.png' % (state['index'] if limit else state['index'] % 2)
        u.RenderingLibrary.export_render_target(camera, target, str(OUT), 'capture_tmp.png')
        (OUT / 'capture_tmp.png').replace(OUT / filename)
        meta['samples'].append({'file': filename, 'unix_time': time.time()})
        meta['samples'] = meta['samples'][-30:]
        (OUT / 'capture_metadata.json').write_text(json.dumps(meta, indent=2))
        state['index'] += 1
        if limit and state['index'] >= limit:
            finish()
    except Exception:
        u.log_error(traceback.format_exc())
        finish()

state['handle'] = u.register_slate_post_tick_callback(tick)
u._ppe_capture_finish = finish
if os.environ.get('YOLO_CAPTURE_QUIT') == '1':
    levels.editor_set_viewport_realtime(True)
    u.EditorLevelLibrary.set_level_viewport_camera_info(capture.get_world_location(), capture.get_world_rotation())
u.log('YOLO_CAMERA_CAPTURE_STARTED ' + str(width) + 'x' + str(height))
