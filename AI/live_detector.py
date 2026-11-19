import argparse
import hashlib
import json
import queue
import threading
import time
from concurrent.futures import Future
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import cv2
import numpy as np
import torch
from ultralytics import YOLO

from ppe_fusion import fuse, normalise
from ppe_session import SessionRecorder
from ppe_tracking import WorkerTracker

ROOT = Path(__file__).resolve().parent
MODELS = {
    'v8s': ROOT / 'models' / 'ppe-yolov8s.pt',
    'y11n': ROOT / 'models' / 'ppe-yolo11n-melih.pt',
}
ALLOWED_ORIGINS = {'http://127.0.0.1:8088', 'http://localhost:8088'}

parser = argparse.ArgumentParser()
parser.add_argument('--mode', choices=['ensemble', *MODELS], default='ensemble')
parser.add_argument('--port', type=int, default=8766)
parser.add_argument('--imgsz', type=int, default=0, help='default: 1280 on GPU, 640 on CPU')
parser.add_argument('--conf', type=float, default=0.5, help='PPE box threshold used by the fusion')
parser.add_argument('--device', default=None, help="'cpu' or a CUDA index like '0' (default: auto)")
parser.add_argument('--min-height', type=float, default=90,
                    help='workers shorter than this (px, relative to a 1280 px-high frame) are too far to judge')
parser.add_argument('--window', type=float, default=2.0, help='seconds of evidence per worker decision')
parser.add_argument('--sessions-dir', default=str(Path(__file__).resolve().parent / 'sessions'),
                    help='where tracking sessions (violation logs + screenshots) are stored')
parser.add_argument('--lost-ttl', type=float, default=10.0,
                    help='seconds a lost worker (occluded / out of frame) is remembered for re-acquisition')
args = parser.parse_args()

device = args.device or ('0' if torch.cuda.is_available() else 'cpu')
args.imgsz = args.imgsz or (640 if device == 'cpu' else 1280)
active = list(MODELS) if args.mode == 'ensemble' else [args.mode]


jobs: 'queue.Queue[tuple[str, object, Future]]' = queue.Queue(maxsize=8)
ready = threading.Event()


def new_tracker():
    return WorkerTracker(window=args.window, min_height_frac=args.min_height / 1280,
                         lost_ttl=args.lost_ttl)


tracker = new_tracker()
recorder = SessionRecorder(Path(args.sessions_dir), lost_ttl=args.lost_ttl)
# Last processed frame (SHA-1 of the JPEG bytes + its result). Identical resubmissions
# are answered from here and never advance the tracker or the violation log.
last_frame = {'digest': None, 'result': None}


def control(cmd):

    global tracker
    if cmd == 'start':
        tracker = new_tracker()
        last_frame.update(digest=None, result=None)
        return recorder.start()
    if cmd == 'stop':
        return recorder.stop()
    raise ValueError(cmd)


def inference_worker():
    with torch.inference_mode():
        models = {tag: YOLO(str(MODELS[tag])) for tag in active}

        class_ids = {tag: [i for i, n in m.names.items() if normalise(n)] for tag, m in models.items()}
        blank = np.zeros((args.imgsz, args.imgsz, 3), np.uint8)
        for m in models.values():
            m.predict(blank, imgsz=args.imgsz, device=device, verbose=False)
        ready.set()
        while True:
            kind, frame, fut = jobs.get()
            if kind != 'frame':
                try:
                    fut.set_result(control(kind))
                except Exception as e:
                    fut.set_exception(e)
                continue
            frame, digest = frame
            if digest == last_frame['digest'] and last_frame['result'] is not None:
                # Byte-identical to the previous frame (frozen stream / resubmission):
                # return the previous result without feeding the tracker or the log, so a
                # still image can't accumulate violation evidence over time.
                dets, workers, timing, ms, alerts, _ = last_frame['result']
                fut.set_result((dets, workers, timing, ms, alerts, recorder.status(), True))
                continue
            try:
                t_frame = time.monotonic()
                t0 = time.perf_counter()
                dets, timing = [], {}
                for tag, m in models.items():
                    t = time.perf_counter()

                    r = m.predict(frame, imgsz=args.imgsz, conf=0.25, classes=class_ids[tag],
                                  device=device, verbose=False)[0]
                    timing[tag] = round((time.perf_counter() - t) * 1000, 1)
                    for b, c, k in zip(r.boxes.xyxy.tolist(), r.boxes.conf.tolist(), r.boxes.cls.tolist()):
                        dets.append({'kind': normalise(m.names[int(k)]), 'label': m.names[int(k)],
                                     'conf': c, 'box': b, 'model': tag})

                workers = tracker.update(fuse(dets, conf=args.conf), t=t_frame, frame_h=frame.shape[0])
                recorder.on_frame(frame, workers)
                result = (dets, workers, timing, (time.perf_counter() - t0) * 1000,
                          list(tracker.alerts)[:10], recorder.status())
                last_frame.update(digest=digest, result=result)
                fut.set_result(result + (False,))
            except Exception as e:
                fut.set_exception(e)


threading.Thread(target=inference_worker, daemon=True, name='inference').start()
ready.wait()


def detect(jpeg: bytes) -> dict:
    frame = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError('could not decode JPEG')
    h, w = frame.shape[:2]
    fut = Future()
    jobs.put(('frame', (frame, hashlib.sha1(jpeg).digest()), fut), timeout=5)
    dets, workers, timing, ms, alerts, session, duplicate = fut.result(timeout=10)

    def norm(b):
        return None if b is None else [b[0] / w, b[1] / h, b[2] / w, b[3] / h]

    workers = [dict(wk, box=norm(wk['box']), helmet_box=norm(wk['helmet_box']),
                    vest_box=norm(wk['vest_box'])) for wk in workers]

    boxes = [{'label': d['label'], 'kind': d['kind'], 'model': d['model'], 'conf': round(d['conf'], 3),
              'box': norm(d['box'])} for d in dets if d['kind'] != 'person']
    counts = {'workers': len(workers),
              'assessed': sum(not wk['too_far'] for wk in workers),
              'too_far': sum(wk['too_far'] for wk in workers),
              'no_helmet': sum(wk['helmet'] == 'violation' for wk in workers),
              'no_vest': sum(wk['vest'] == 'violation' for wk in workers)}
    return {'mode': args.mode, 'workers': workers, 'boxes': boxes, 'counts': counts,
            'alerts': alerts, 'session': session, 'duplicate_frame': duplicate,
            'width': w, 'height': h, 'inference_ms': round(ms, 1), 'model_ms': timing,
            'device': str(device), 'min_height_px': args.min_height, 'window_s': args.window}


class Handler(BaseHTTPRequestHandler):
    def _cors(self):
        origin = self.headers.get('Origin')
        if origin in ALLOWED_ORIGINS:
            self.send_header('Access-Control-Allow-Origin', origin)
            self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self._cors()
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        parts = [p for p in self.path.split('?')[0].split('/') if p]
        if parts == ['health']:
            self._json(200, {'ok': True, 'mode': args.mode, 'models': active, 'device': str(device),
                             'imgsz': args.imgsz, 'conf': args.conf})
        elif parts == ['session']:
            self._json(200, recorder.status())
        elif parts == ['sessions']:
            self._json(200, recorder.list())
        elif len(parts) == 2 and parts[0] == 'sessions':
            data = recorder.load(parts[1])
            self._json(200, data) if data else self._json(404, {'error': 'no such session'})
        elif len(parts) == 4 and parts[0] == 'sessions' and parts[2] == 'snapshots':
            p = recorder.snapshot_path(parts[1], parts[3])
            if not p:
                self.send_error(404)
                return
            body = p.read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'image/jpeg')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'max-age=86400')
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(404)

    def _control(self, cmd):
        fut = Future()
        jobs.put((cmd, None, fut), timeout=5)
        return fut.result(timeout=10)

    def do_POST(self):
        path = self.path.split('?')[0]
        if path in ('/session/start', '/session/stop'):
            try:
                result = self._control(path.rsplit('/', 1)[1])
                self._json(200, result or {'active': None})
            except Exception as e:
                self._json(500, {'error': str(e)})
            return
        if path != '/detect':
            self.send_error(404)
            return
        length = int(self.headers.get('Content-Length') or 0)
        if not 0 < length < 20_000_000:
            self._json(400, {'error': 'bad length'})
            return
        try:
            self._json(200, detect(self.rfile.read(length)))
        except Exception as e:
            self._json(500, {'error': str(e)})

    def log_message(self, *a):
        pass


if __name__ == '__main__':
    print(f'PPE live detector on http://127.0.0.1:{args.port}  mode={args.mode} models={active} '
          f'device={device} imgsz={args.imgsz}', flush=True)
    ThreadingHTTPServer(('127.0.0.1', args.port), Handler).serve_forever()
