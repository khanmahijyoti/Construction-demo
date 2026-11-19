from pathlib import Path
import time
import traceback
import unreal as u

pending = getattr(u, '_ppe_start_pending', None)
if pending is not None:
    u.unregister_slate_post_tick_callback(pending)
    u._ppe_start_pending = None
finish_previous = getattr(u, '_ppe_capture_finish', None)
if finish_previous:
    finish_previous()

bootstrap = {'started': time.monotonic(), 'ready_since': None}
levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
already_playing = bool(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world())
u._ppe_started_play = getattr(u, '_ppe_started_play', False) or not already_playing

def launch_live_capture():
    script = Path('E:/Construction_Demo/Scripts/start_yolo_camera_now.py')
    namespace = {'__file__': str(script), '__name__': '__ppe_live_capture__'}
    exec(compile(script.read_text(), str(script), 'exec'), namespace)

def wait_for_play(delta):
    world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
    if world and u.GameplayStatics.get_player_controller(world, 0):
        if bootstrap['ready_since'] is None:
            bootstrap['ready_since'] = time.monotonic()
        if time.monotonic() - bootstrap['ready_since'] < 2:
            return
        u.unregister_slate_post_tick_callback(u._ppe_start_pending)
        u._ppe_start_pending = None
        try:
            launch_live_capture()
        except Exception:
            u.log_error(traceback.format_exc())
            if __import__('os').environ.get('YOLO_CAPTURE_QUIT') == '1':
                u.SystemLibrary.quit_editor()
    elif time.monotonic() - bootstrap['started'] > 90:
        u.unregister_slate_post_tick_callback(u._ppe_start_pending)
        u._ppe_start_pending = None
        u.log_error('PPE feed could not enter Play mode within 90 seconds')

if already_playing:
    launch_live_capture()
else:
    u._ppe_start_pending = u.register_slate_post_tick_callback(wait_for_play)
    levels.editor_request_begin_play()
    u.log('Starting Play mode for the live BP_Camera feed...')
