import os
import time
from pathlib import Path
import unreal as u

os.environ['YOLO_CAPTURE_COUNT'] = '3'
play_levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
play_boot = {'start': time.monotonic()}

def start_when_playing(delta):
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
        u.unregister_slate_post_tick_callback(play_boot['handle'])
        script = Path('E:/Construction_Demo/Scripts/capture_yolo_viewport.py')
        try:
            exec(compile(script.read_text(), str(script), 'exec'), globals())
        except Exception:
            import traceback
            u.log_error(traceback.format_exc())
            u.SystemLibrary.quit_editor()
    elif time.monotonic() - play_boot['start'] > 90:
        u.unregister_slate_post_tick_callback(play_boot['handle'])
        u.log_error('Play capture startup timed out')
        u.SystemLibrary.quit_editor()

play_boot['handle'] = u.register_slate_post_tick_callback(start_when_playing)
play_levels.editor_request_begin_play()
