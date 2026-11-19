from __future__ import annotations

import itertools
import time
from collections import deque

import numpy as np

from ppe_fusion import _iou

ATTRS = ('helmet', 'vest')


class BoxKalman:


    REF_FPS = 30.0
    STD_POS, STD_VEL = 1 / 20, 1 / 160

    def __init__(self, box):
        z = self._measure(box)
        h = z[3]
        self.x = np.r_[z, 0, 0, 0, 0].astype(float)
        sp, sv = self.STD_POS * h, self.STD_VEL * h * self.REF_FPS
        self.P = np.diag(np.square([2 * sp, 2 * sp, 1e-2, 2 * sp, 10 * sv, 10 * sv, 1e-5, 10 * sv]))
        self.H = np.hstack([np.eye(4), np.zeros((4, 4))])

    @staticmethod
    def _measure(b):
        w, h = b[2] - b[0], b[3] - b[1]
        return np.array([(b[0] + b[2]) / 2, (b[1] + b[3]) / 2, w / max(h, 1e-6), h])

    def predict(self, dt, move_dt):

        if dt <= 0:
            return
        F = np.eye(8)
        F[:4, 4:] = np.eye(4) * move_dt
        h = max(self.x[3], 1.0)
        k = dt * self.REF_FPS
        sp, sv = self.STD_POS * h, self.STD_VEL * h * self.REF_FPS
        Q = np.diag(np.square([sp, sp, 1e-2, sp, sv, sv, 1e-5, sv])) * k
        self.x = F @ self.x
        self.P = F @ self.P @ F.T + Q
        self.x[3] = max(self.x[3], 1.0)

    def update(self, box):
        z = self._measure(box)
        h = max(self.x[3], 1.0)
        R = np.diag(np.square([self.STD_POS * h, self.STD_POS * h, 1e-1, self.STD_POS * h]))
        S = self.H @ self.P @ self.H.T + R
        K = self.P @ self.H.T @ np.linalg.inv(S)
        self.x = self.x + K @ (z - self.H @ self.x)
        self.P = (np.eye(8) - K @ self.H) @ self.P

    def box(self):
        cx, cy, a, h = self.x[:4]
        w = a * h
        return [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2]


def _height(b):
    return b[3] - b[1]


def _centre(b):
    return ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)


class WorkerTracker:
    def __init__(self, window=2.0, enter=0.7, exit=0.6, min_judged=5, min_span=1.0,
                 min_height_frac=90 / 1280, iou_match=0.2, max_age=1.5, cooldown=30.0,
                 ppe_only_height_scale=1.8, lost_ttl=10.0, reacquire_gate=1.0,
                 reacquire_growth=0.3, reacquire_gate_max=3.0, reacquire_size_ratio=1.5,
                 predict_horizon=2.0):
        self.window, self.enter, self.exit = window, enter, exit
        self.min_judged, self.min_span = min_judged, min_span
        self.min_height_frac, self.iou_match = min_height_frac, iou_match
        self.max_age, self.cooldown = max_age, cooldown


        self.lost_ttl = lost_ttl
        self.reacquire_gate, self.reacquire_growth = reacquire_gate, reacquire_growth
        self.reacquire_gate_max, self.reacquire_size_ratio = reacquire_gate_max, reacquire_size_ratio


        self.predict_horizon = predict_horizon


        self.ppe_only_height_scale = ppe_only_height_scale
        self.tracks: dict[int, dict] = {}
        self.alerts: deque = deque(maxlen=50)
        self.new_alerts: list = []
        self._ids = itertools.count(1)


    def _predict(self, tr, t):

        prev = tr['kf_t']
        horizon_end = tr['last_t'] + self.predict_horizon
        move_dt = max(0.0, min(t, horizon_end) - min(prev, horizon_end))
        tr['kf'].predict(t - prev, move_dt)
        tr['kf_t'] = t
        tr['pred_box'] = tr['kf'].box()

    def _match(self, workers, t):
        for tr in self.tracks.values():
            self._predict(tr, t)
        active = {tid: tr for tid, tr in self.tracks.items() if t - tr['last_t'] <= self.max_age}
        assigned = self._match_active(workers, active)
        lost = {tid: tr for tid, tr in self.tracks.items() if tid not in active}
        assigned.update(self._match_lost(workers, lost, set(assigned), t))
        return assigned

    def _match_lost(self, workers, lost, taken, t):

        pairs = []
        for wi, w in enumerate(workers):
            if wi in taken:
                continue
            mb = w['person_box'] or w['box']
            for tid, tr in lost.items():
                last, gap = tr['match_box'], t - tr['last_t']
                h_last, h_new = _height(last), _height(mb)
                if not (1 / self.reacquire_size_ratio <= h_new / max(h_last, 1e-6) <= self.reacquire_size_ratio):
                    continue


                (ax, ay), (bx, by) = _centre(mb), _centre(tr['pred_box'])
                d = ((ax - bx) ** 2 + (ay - by) ** 2) ** .5
                gate = h_last * min(self.reacquire_gate + self.reacquire_growth * gap, self.reacquire_gate_max)
                if d <= gate:
                    pairs.append((d / gate, gap, wi, tid))
        out, used = {}, set()
        for _, _, wi, tid in sorted(pairs):
            if wi not in out and tid not in used:
                out[wi] = tid
                used.add(tid)
        return out

    def _match_active(self, workers, tracks):
        pairs = []
        for wi, w in enumerate(workers):
            mb = w['person_box'] or w['box']
            for tid, tr in tracks.items():
                pb = tr['pred_box']
                iou = _iou(mb, pb)
                if iou < self.iou_match:

                    (ax, ay), (bx, by) = _centre(mb), _centre(pb)
                    d = ((ax - bx) ** 2 + (ay - by) ** 2) ** .5
                    if d > 0.5 * max(_height(mb), _height(pb)):
                        continue
                    iou = 0.01
                pairs.append((iou, wi, tid))
        assigned, used = {}, set()
        for iou, wi, tid in sorted(pairs, reverse=True):
            if wi not in assigned and tid not in used:
                assigned[wi] = tid
                used.add(tid)
        return assigned


    def _decide(self, tr, key, t):
        win = [s for s in tr['samples'] if t - s['t'] <= self.window]
        judged = [s for s in win if s[key] != 'unknown']
        cur = tr['state'][key]
        if not judged:
            if len(win) <= 1:


                return cur

            return 'unknown' if t - tr['first_t'] >= self.window else cur
        if len(judged) < self.min_judged:
            return cur
        vf = sum(s[key] == 'violation' for s in judged) / len(judged)
        span = t - judged[0]['t']
        if cur == 'violation':
            return 'ok' if 1 - vf >= self.exit else 'violation'
        if vf >= self.enter and span >= self.min_span:
            return 'violation'
        if 1 - vf >= self.exit:
            return 'ok'
        return cur


    def update(self, workers, t=None, frame_h=1280):

        t = time.monotonic() if t is None else t
        assigned = self._match(workers, t)
        out = []
        self.new_alerts = []
        for wi, w in enumerate(workers):
            tid = assigned.get(wi)
            mb = w['person_box'] or w['box']
            if tid is None:
                tid = next(self._ids)
                self.tracks[tid] = {'id': tid, 'first_t': t, 'last_t': t, 'samples': deque(maxlen=200),
                                    'state': {k: 'unknown' for k in ATTRS},
                                    'since': {k: None for k in ATTRS},
                                    'last_alert': {k: -1e9 for k in ATTRS}, 'reacquired': 0,
                                    'kf': BoxKalman(mb), 'kf_t': t, 'pred_box': list(mb)}
            else:
                self.tracks[tid]['kf'].update(mb)
            tr = self.tracks[tid]
            gap = t - tr['last_t']
            reacquired = gap > self.max_age
            if reacquired:
                tr['reacquired'] += 1
            tr['match_box'] = mb
            tr['last_t'] = t

            if w['person_box']:
                height = _height(w['person_box'])
            else:
                height = _height(w['box']) * self.ppe_only_height_scale
            too_far = height < self.min_height_frac * frame_h
            obs = {k: ('unknown' if too_far else w[k]) for k in ATTRS}
            tr['samples'].append({'t': t, **obs})

            for k in ATTRS:
                new = self._decide(tr, k, t)
                if new != tr['state'][k]:
                    tr['since'][k] = t
                    if new == 'violation' and t - tr['last_alert'][k] >= self.cooldown:
                        tr['last_alert'][k] = t
                        alert = {'wall_time': time.time(), 'track': tid, 'kind': 'no_' + k}
                        self.alerts.appendleft(alert)
                        self.new_alerts.append(dict(alert, box=list(w['box']),
                                                    height_px=round(height, 1),
                                                    evidence=w['evidence']))
                tr['state'][k] = new

            out.append({
                'id': tid,
                'box': w['box'], 'helmet_box': w['helmet_box'], 'vest_box': w['vest_box'],
                'helmet': tr['state']['helmet'], 'vest': tr['state']['vest'],
                'obs': obs, 'too_far': too_far, 'height_px': round(height, 1),
                'state_for_s': {k: (round(t - tr['since'][k], 1) if tr['since'][k] is not None else None)
                                for k in ATTRS},
                'evidence': w['evidence'],
                'reacquired_after_s': round(gap, 1) if reacquired else None,
                'reacquired_count': tr['reacquired'],
            })


        for tid in [i for i, tr in self.tracks.items() if t - tr['last_t'] > self.lost_ttl]:
            del self.tracks[tid]
        return out
