from __future__ import annotations

import json
import re
import time
from pathlib import Path

import cv2
import numpy as np

SNAP_WIDTH = 480
CROP_HEIGHT = 200
JPEG_QUALITY = 70
MIN_LOG_S = 3.0
DEDUP_S = 60.0
DEDUP_GROWTH = 0.1
DEDUP_GATE_MAX = 3.0
DEDUP_SIZE_RATIO = 1.8
APPEARANCE_MAX = 0.45
SESSION_ID = re.compile(r'^\d{8}-\d{6}$')
SNAP_NAME = re.compile(r'^[\w.-]+\.jpg$')


def fingerprint(frame, box):

    h, w = frame.shape[:2]
    x1, y1, x2, y2 = [int(round(v)) for v in box]
    x1, y1, x2, y2 = max(0, x1), max(0, y1), min(w, x2), min(h, y2)
    if x2 - x1 < 4 or y2 - y1 < 8:
        return None
    hsv = cv2.cvtColor(frame[y1:y2, x1:x2], cv2.COLOR_BGR2HSV)
    bh = hsv.shape[0]
    out = []
    for part in (hsv[int(bh * .15):int(bh * .55)], hsv[int(bh * .55):int(bh * .95)]):
        hist = cv2.calcHist([part], [0, 1], None, [16, 8], [0, 180, 0, 256])
        out.append(cv2.normalize(hist, None).flatten())
    return out


def appearance_distance(a, b):
    if a is None or b is None:
        return 1.0
    return float(np.mean([cv2.compareHist(x, y, cv2.HISTCMP_BHATTACHARYYA) for x, y in zip(a, b)]))


def _head(box):
    return ((box[0] + box[2]) / 2, box[1])


class SessionRecorder:
    def __init__(self, root: Path, lost_ttl: float = 10.0):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.lost_ttl = lost_ttl
        self.active: dict | None = None


    def start(self) -> dict:
        if self.active:
            self.stop()
        now = time.time()
        sid = time.strftime('%Y%m%d-%H%M%S', time.localtime(now))
        d = self.root / sid
        (d / 'snapshots').mkdir(parents=True, exist_ok=True)


        self.active = {'id': sid, 'dir': d, 'started': now, 'stopped': None, 'frames': 0,
                       'workers': set(), 'events': [], 'open': {}, 'pending': {}, 'fps': {},
                       'next_n': 1}
        self._save()
        return self.status()

    def stop(self) -> dict | None:
        s = self.active
        if not s:
            return None
        now = time.time()
        for ev in s['open'].values():
            ev['end'], ev['ended_by'] = now, 'session_stopped'
        s['open'].clear()
        s['stopped'] = now
        self._save()
        self.active = None
        return self.load(s['id'])

    def status(self) -> dict:
        s = self.active
        if not s:
            return {'active': None}
        return {'active': s['id'], 'started': s['started'], 'frames': s['frames'],
                'workers_seen': len(s['workers']), 'violations': len(s['events']),
                'open_violations': len(s['open'])}


    def on_frame(self, frame, workers):
        s = self.active
        if not s:
            return
        now = time.time()
        s['frames'] += 1
        s['workers'].update(w['id'] for w in workers)
        changed = False

        present = {w['id']: w for w in workers}
        for w in workers:
            for attr in ('helmet', 'vest'):
                key = (w['id'], 'no_' + attr)
                if key in s['open']:
                    continue
                if w[attr] != 'violation':
                    s['pending'].pop(key, None)
                    continue
                first, _ = s['pending'].get(key, (now, now))
                s['pending'][key] = (first, now)
                if now - first < MIN_LOG_S:
                    continue
                del s['pending'][key]
                dup = self._find_duplicate(frame, w, key[1], now, present)
                if dup is not None:

                    for k in [k for k, e in s['open'].items() if e is dup]:
                        del s['open'][k]
                    dup['end'], dup['ended_by'] = None, None
                    dup['reopened'] = dup.get('reopened', 0) + 1
                    dup['track'] = w['id']
                    s['open'][key] = dup
                else:
                    s['open'][key] = self._new_event(frame, w, key[1], first)
                changed = True


        s['pending'] = {k: v for k, v in s['pending'].items() if now - v[1] <= 1.5}

        for key, ev in list(s['open'].items()):
            track, kind = key
            attr = kind[3:]
            w = present.get(track)
            if w is not None:
                ev['last_seen'] = now
                ev['last_box'] = [round(v, 1) for v in w['box']]
                ev['last_height'] = w.get('height_px')
                if w[attr] == 'ok':

                    del s['open'][key]
                    self._discard(ev)
                    changed = True
                elif w[attr] != 'violation':
                    ev['end'], ev['ended_by'] = now, 'undetermined'
                    del s['open'][key]
                    changed = True
            elif now - ev['last_seen'] > self.lost_ttl:
                ev['end'], ev['ended_by'] = ev['last_seen'], 'left_view'
                del s['open'][key]
                changed = True

        if changed or s['frames'] % 100 == 0:
            self._save()

    def _find_duplicate(self, frame, worker, kind, now, present):

        s = self.active
        fp = None
        best, best_d = None, None
        for ev in reversed(s['events']):
            if ev['kind'] != kind:
                continue
            ref_t = ev['end'] or ev['last_seen']
            if now - ref_t > DEDUP_S:
                continue
            owner_open = ev['end'] is None
            if owner_open and ev['track'] in present:
                continue
            if ev['track'] == worker['id']:
                return ev
            last_box = ev.get('last_box') or ev.get('box')
            h_new = worker.get('height_px') or (worker['box'][3] - worker['box'][1])
            h_old = ev.get('last_height') or ev.get('height_px') or (last_box[3] - last_box[1])
            if max(h_new, h_old) / max(min(h_new, h_old), 1e-6) > DEDUP_SIZE_RATIO:
                continue
            (ax, ay), (bx, by) = _head(worker['box']), _head(last_box)
            gap = max(0.0, now - ref_t)
            gate = max(h_new, h_old) * min(1 + DEDUP_GROWTH * gap, DEDUP_GATE_MAX)
            dist = ((ax - bx) ** 2 + (ay - by) ** 2) ** .5
            if dist > gate:
                continue
            if fp is None:
                fp = fingerprint(frame, worker['box'])
            d = appearance_distance(fp, s['fps'].get(ev['n']))
            if d <= APPEARANCE_MAX and (best_d is None or d < best_d):
                best, best_d = ev, d
        return best

    def _discard(self, ev):
        s = self.active
        s['events'] = [e for e in s['events'] if e is not ev]
        for f in (ev.get('snapshot'), ev.get('crop')):
            if f:
                (s['dir'] / 'snapshots' / f).unlink(missing_ok=True)

    def _new_event(self, frame, worker, kind, now) -> dict:
        s = self.active
        n = s['next_n']
        s['next_n'] += 1
        track = worker['id']
        base = f"{n:03d}_w{track}_{kind}"
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = [int(round(v)) for v in worker['box']]
        x1, y1, x2, y2 = max(0, x1), max(0, y1), min(w - 1, x2), min(h - 1, y2)
        label = kind.replace('_', ' ').upper()


        scale = SNAP_WIDTH / w
        thumb = cv2.resize(frame, (SNAP_WIDTH, round(h * scale)), interpolation=cv2.INTER_AREA)
        p1, p2 = (round(x1 * scale), round(y1 * scale)), (round(x2 * scale), round(y2 * scale))
        cv2.rectangle(thumb, p1, p2, (60, 60, 255), 2)
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
        ty = max(p1[1], th + 6)
        cv2.rectangle(thumb, (p1[0], ty - th - 6), (p1[0] + tw + 6, ty), (60, 60, 255), -1)
        cv2.putText(thumb, label, (p1[0] + 3, ty - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.imwrite(str(s['dir'] / 'snapshots' / f'{base}.jpg'), thumb, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])


        mx, my = round((x2 - x1) * 0.35), round((y2 - y1) * 0.15)
        cx1, cy1, cx2, cy2 = max(0, x1 - mx), max(0, y1 - my), min(w, x2 + mx), min(h, y2 + my)
        crop_file = None
        if cx2 - cx1 > 2 and cy2 - cy1 > 2:
            crop = frame[cy1:cy2, cx1:cx2]
            cs = CROP_HEIGHT / crop.shape[0]
            crop = cv2.resize(crop, (max(1, round(crop.shape[1] * cs)), CROP_HEIGHT),
                              interpolation=cv2.INTER_CUBIC if cs > 1 else cv2.INTER_AREA)
            crop_file = f'{base}_crop.jpg'
            cv2.imwrite(str(s['dir'] / 'snapshots' / crop_file), crop, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])

        box = [round(v, 1) for v in worker['box']]
        ev = {'n': n, 'track': track, 'kind': kind, 'start': now, 'end': None,
              'ended_by': None, 'last_seen': time.time(), 'height_px': worker.get('height_px'),
              'box': box, 'last_box': box, 'last_height': worker.get('height_px'),
              'evidence': worker.get('evidence', {}), 'snapshot': f'{base}.jpg', 'crop': crop_file}
        s['fps'][n] = fingerprint(frame, worker['box'])
        s['events'].append(ev)
        return ev


    def _summary(self, s) -> dict:
        end = s['stopped'] or time.time()
        by_kind = {}
        for e in s['events']:
            by_kind[e['kind']] = by_kind.get(e['kind'], 0) + 1
        return {'id': s['id'], 'started': s['started'], 'stopped': s['stopped'],
                'duration_s': round(end - s['started'], 1), 'frames': s['frames'],
                'workers_seen': len(s['workers']), 'violations': len(s['events']),
                'by_kind': by_kind, 'workers_with_violations': len({e['track'] for e in s['events']})}

    def _save(self):
        s = self.active
        data = {'summary': self._summary(s), 'events': s['events']}
        tmp = s['dir'] / 'session.json.tmp'
        tmp.write_text(json.dumps(data, indent=1))
        tmp.replace(s['dir'] / 'session.json')

    @staticmethod
    def _without_resolved(data: dict) -> dict:

        events = [e for e in data.get('events', []) if e.get('ended_by') != 'resolved']
        if len(events) != len(data.get('events', [])):
            by_kind = {}
            for e in events:
                by_kind[e['kind']] = by_kind.get(e['kind'], 0) + 1
            data['events'] = events
            data['summary'].update(violations=len(events), by_kind=by_kind,
                                   workers_with_violations=len({e['track'] for e in events}))
        return data

    def load(self, sid: str) -> dict | None:
        if not SESSION_ID.match(sid):
            return None
        f = self.root / sid / 'session.json'
        if self.active and self.active['id'] == sid:
            self._save()
        return self._without_resolved(json.loads(f.read_text())) if f.exists() else None

    def list(self) -> list[dict]:
        out = []
        for d in sorted(self.root.iterdir(), reverse=True):
            f = d / 'session.json'
            if d.is_dir() and SESSION_ID.match(d.name) and f.exists():
                try:
                    out.append(self._without_resolved(json.loads(f.read_text()))['summary'])
                except (OSError, ValueError, KeyError):
                    pass
        return out

    def snapshot_path(self, sid: str, name: str) -> Path | None:
        if not (SESSION_ID.match(sid) and SNAP_NAME.match(name)):
            return None
        p = self.root / sid / 'snapshots' / name
        return p if p.exists() else None
