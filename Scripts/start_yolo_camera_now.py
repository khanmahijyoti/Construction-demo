from pathlib import Path
import socket
import subprocess
import json
import uuid
import unreal as u

root = Path('E:/Construction_Demo')
python = root / 'AI/.venv/Scripts/python.exe'
assert python.exists(), 'Missing AI virtual environment'
previous = getattr(u, '_ppe_yolo_children', [])
for child in previous:
    if child.poll() is None:
        child.terminate()
finish_previous = getattr(u, '_ppe_capture_finish', None)
if finish_previous:
    try:
        finish_previous()
    except Exception:
        pass
u._ppe_yolo_children = []
(root / 'AI/detection_session.txt').write_text(uuid.uuid4().hex)
for name, command in [('live-verification', ['verify_camera.py', '--watch', '--seconds', '86400', '--imgsz', '1280']),
                      ('viewer', ['viewer.py'])]:
    if name == 'viewer':
        with socket.socket() as probe:
            if probe.connect_ex(('127.0.0.1', 8765)) == 0:
                continue
    log = open(root / ('AI/' + name + '.log'), 'w')
    errors = open(root / ('AI/' + name + '-errors.log'), 'w')
    child = subprocess.Popen([str(python), *command], cwd=str(root / 'AI'), stdout=log, stderr=errors,
                             creationflags=subprocess.CREATE_NO_WINDOW)
    log.close()
    errors.close()
    u._ppe_yolo_children.append(child)
(root / 'AI/session-pids.json').write_text(json.dumps([p.pid for p in u._ppe_yolo_children]))
capture_script = root / 'Scripts/capture_yolo_viewport.py'
exec(compile(capture_script.read_text(), str(capture_script), 'exec'), globals())
u.log('PPE viewer: http://127.0.0.1:8765 ; warm-up >=20 seconds plus initial asset loading. Stop with stop_yolo_camera.py')
