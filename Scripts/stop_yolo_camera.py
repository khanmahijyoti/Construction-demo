import unreal as u
from pathlib import Path
import uuid
Path('E:/Construction_Demo/AI/detection_session.txt').write_text('stopped-' + uuid.uuid4().hex)
pending = getattr(u, '_ppe_start_pending', None)
if pending is not None:
    u.unregister_slate_post_tick_callback(pending)
    u._ppe_start_pending = None
finish = getattr(u, '_ppe_capture_finish', None)
if finish:
    try:
        finish()
    except Exception as e:
        u.log_warning(str(e))
    u._ppe_capture_finish = None
for child in getattr(u, '_ppe_yolo_children', []):
    if child.poll() is None:
        child.terminate()
u._ppe_yolo_children = []
if getattr(u, '_ppe_started_play', False):
    u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
    u._ppe_started_play = False
u.log('PPE capture stopped; previous view and camera settings restored.')
