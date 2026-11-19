import json
import tempfile
from pathlib import Path
from unittest import mock

import numpy as np

import ppe_session
from ppe_session import MIN_LOG_S, SessionRecorder

STEP = 0.25


YELLOW_BROWN = ((40, 220, 230), (40, 70, 110))
ORANGE_NAVY = ((30, 120, 250), (90, 40, 20))


def wk(tid, x=100, y=400, h=160, vest='ok', helmet='ok'):
    return {'id': tid, 'box': [x, y, x + h * 0.35, y + h], 'helmet': helmet, 'vest': vest,
            'height_px': float(h), 'evidence': {}}


def frame(*painted):

    f = np.full((1280, 1280, 3), 90, np.uint8)
    f[::7, :] = 70
    for w, (torso, legs) in painted:
        x1, y1, x2, y2 = [int(v) for v in w['box']]
        mid = y1 + int((y2 - y1) * 0.55)
        f[y1:mid, x1:x2] = torso
        f[mid:y2, x1:x2] = legs
    return f


class Clock:
    def __init__(self):
        self.t = 1_000_000.0

    def __call__(self):
        return self.t


class Rec:
    def __init__(self, tmp):
        self.clock = Clock()
        self.patch = mock.patch.object(ppe_session.time, 'time', self.clock)
        self.patch.start()
        self.r = SessionRecorder(Path(tmp), lost_ttl=10.0)
        self.sid = self.r.start()['active']

    def hold(self, seconds, *painted):

        for _ in range(max(1, round(seconds / STEP))):
            self.r.on_frame(frame(*painted), [w for w, _ in painted])
            self.clock.t += STEP

    def gap(self, seconds):
        self.hold(seconds)

    def stop(self):
        data = self.r.stop()
        self.patch.stop()
        return data

    def snaps(self):
        return sorted(p.name for p in (self.r.root / self.sid / 'snapshots').iterdir())


def test_short_violation_is_not_logged():
    with tempfile.TemporaryDirectory() as tmp:
        r = Rec(tmp)
        r.hold(MIN_LOG_S - 1, (wk(1, vest='violation'), YELLOW_BROWN))
        r.hold(2, (wk(1), YELLOW_BROWN))
        assert r.stop()['events'] == []


def test_logged_entry_time_is_when_violation_started():
    with tempfile.TemporaryDirectory() as tmp:
        r = Rec(tmp)
        t0 = r.clock.t
        r.hold(MIN_LOG_S + 1, (wk(1, vest='violation'), YELLOW_BROWN))
        data = r.stop()
        assert len(data['events']) == 1 and abs(data['events'][0]['start'] - t0) < 1e-6


def test_resolved_violation_is_dropped_with_images():
    with tempfile.TemporaryDirectory() as tmp:
        r = Rec(tmp)
        r.hold(MIN_LOG_S + 1, (wk(1, vest='violation'), YELLOW_BROWN))
        assert len(r.snaps()) == 2
        r.hold(1, (wk(1), YELLOW_BROWN))
        assert r.snaps() == []
        assert r.stop()['events'] == []


def test_reviolation_after_resolve_is_logged_again():
    with tempfile.TemporaryDirectory() as tmp:
        r = Rec(tmp)
        r.hold(MIN_LOG_S + 1, (wk(1, vest='violation'), YELLOW_BROWN))
        r.hold(1, (wk(1), YELLOW_BROWN))
        r.hold(MIN_LOG_S + 1, (wk(1, vest='violation'), YELLOW_BROWN))
        data = r.stop()
        assert len(data['events']) == 1 and data['events'][0]['n'] == 2


def test_new_id_same_place_same_clothes_is_merged():

    with tempfile.TemporaryDirectory() as tmp:
        r = Rec(tmp)
        r.hold(MIN_LOG_S + 1, (wk(77, x=550, y=560, h=195, helmet='violation'), YELLOW_BROWN))
        r.gap(17)
        r.hold(MIN_LOG_S + 1, (wk(81, x=620, y=560, h=141, helmet='violation'), YELLOW_BROWN))
        data = r.stop()
        assert len(data['events']) == 1, [(e['track'], e['kind']) for e in data['events']]
        assert data['events'][0]['reopened'] == 1


def test_new_id_same_place_different_clothes_is_separate():
    with tempfile.TemporaryDirectory() as tmp:
        r = Rec(tmp)
        r.hold(MIN_LOG_S + 1, (wk(1, x=550, helmet='violation'), YELLOW_BROWN))
        r.gap(12)
        r.hold(MIN_LOG_S + 1, (wk(2, x=560, helmet='violation'), ORANGE_NAVY))
        assert len(r.stop()['events']) == 2


def test_same_clothes_far_away_is_separate():
    with tempfile.TemporaryDirectory() as tmp:
        r = Rec(tmp)
        r.hold(MIN_LOG_S + 1, (wk(1, x=100, helmet='violation'), YELLOW_BROWN))
        r.gap(2)
        r.hold(MIN_LOG_S + 1, (wk(2, x=1100, helmet='violation'), YELLOW_BROWN))
        assert len(r.stop()['events']) == 2


def test_two_workers_violating_at_once_are_separate_even_if_alike():
    with tempfile.TemporaryDirectory() as tmp:
        r = Rec(tmp)
        r.hold(MIN_LOG_S + 1, (wk(1, x=500, vest='violation'), YELLOW_BROWN),
               (wk(2, x=600, vest='violation'), YELLOW_BROWN))
        assert len(r.stop()['events']) == 2


def test_different_kind_is_never_merged():
    with tempfile.TemporaryDirectory() as tmp:
        r = Rec(tmp)
        r.hold(MIN_LOG_S + 1, (wk(1, x=500, vest='violation'), YELLOW_BROWN))
        r.gap(12)
        r.hold(MIN_LOG_S + 1, (wk(2, x=510, helmet='violation'), YELLOW_BROWN))
        kinds = sorted(e['kind'] for e in r.stop()['events'])
        assert kinds == ['no_helmet', 'no_vest']


def test_old_entry_beyond_dedup_window_is_separate():
    with tempfile.TemporaryDirectory() as tmp:
        r = Rec(tmp)
        r.hold(MIN_LOG_S + 1, (wk(1, x=500, helmet='violation'), YELLOW_BROWN))
        r.gap(75)
        r.hold(MIN_LOG_S + 1, (wk(2, x=500, helmet='violation'), YELLOW_BROWN))
        assert len(r.stop()['events']) == 2


def test_left_view_and_undetermined_are_kept():
    with tempfile.TemporaryDirectory() as tmp:
        r = Rec(tmp)
        r.hold(MIN_LOG_S + 1, (wk(1, x=100, vest='violation'), YELLOW_BROWN),
               (wk(2, x=700, helmet='violation'), ORANGE_NAVY))
        r.hold(1, (wk(2, x=700, helmet='unknown'), ORANGE_NAVY))
        r.gap(11)
        ended = {e['kind']: e['ended_by'] for e in r.stop()['events']}
        assert ended == {'no_vest': 'left_view', 'no_helmet': 'undetermined'}, ended


def test_one_missed_frame_does_not_restart_the_wait():
    with tempfile.TemporaryDirectory() as tmp:
        r = Rec(tmp)
        r.hold(2, (wk(1, vest='violation'), YELLOW_BROWN))
        r.gap(STEP)
        r.hold(1.5, (wk(1, vest='violation'), YELLOW_BROWN))
        assert len(r.stop()['events']) == 1


def test_old_sessions_hide_resolved_entries():
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp) / '20260101-120000'
        d.mkdir()
        events = [{'n': 1, 'track': 1, 'kind': 'no_vest', 'ended_by': 'resolved'},
                  {'n': 2, 'track': 2, 'kind': 'no_helmet', 'ended_by': 'left_view'}]
        summary = {'id': d.name, 'violations': 2, 'by_kind': {'no_vest': 1, 'no_helmet': 1},
                   'workers_with_violations': 2}
        (d / 'session.json').write_text(json.dumps({'summary': summary, 'events': events}))
        rec = SessionRecorder(Path(tmp))
        data = rec.load(d.name)
        assert [e['n'] for e in data['events']] == [2]
        assert data['summary']['violations'] == 1 and rec.list()[0]['violations'] == 1


if __name__ == '__main__':
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith('test_')]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print('PASS', name)
        except AssertionError as e:
            failed += 1
            print('FAIL', name, '-', e)
    print(f'\n{len(tests) - failed}/{len(tests)} passed')
    raise SystemExit(1 if failed else 0)
