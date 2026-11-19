from ppe_tracking import WorkerTracker

HZ = 14.0


def worker(x, y, h, helmet='ok', vest='ok', person=True):
    box = [x, y, x + h * 0.3, y + h]
    return {'box': box, 'person_box': box if person else None, 'helmet_box': None,
            'vest_box': None, 'helmet': helmet, 'vest': vest, 'evidence': {}}


def run(frames, tracker=None):
    tr = tracker or WorkerTracker()
    history = []
    for i, ws in enumerate(frames):
        history.append(tr.update(ws, t=i / HZ, frame_h=1280))
    return tr, history


def test_steady_violation_needs_min_span_and_alerts_once():
    tr, hist = run([[worker(100, 400, 150, vest='violation')] for _ in range(60)])
    first = next(i for i, h in enumerate(hist) if h[0]['vest'] == 'violation')
    assert first / HZ >= 1.0, f'violation after only {first / HZ:.2f}s'
    assert first / HZ <= 1.2, f'violation too slow: {first / HZ:.2f}s'
    assert len(tr.alerts) == 1 and tr.alerts[0]['kind'] == 'no_vest'
    assert hist[-1][0]['helmet'] == 'ok'


def test_single_frame_flicker_is_ignored():
    frames = [[worker(100, 400, 150, vest='violation' if i % 10 == 5 else 'ok')] for i in range(80)]
    tr, hist = run(frames)
    assert all(h[0]['vest'] in ('ok', 'unknown') for h in hist)
    assert not tr.alerts


def test_far_worker_is_not_judged():
    tr, hist = run([[worker(100, 400, 60, vest='violation', helmet='violation')] for _ in range(60)])
    assert all(h[0]['too_far'] for h in hist)
    assert hist[-1][0]['vest'] == 'unknown' and hist[-1][0]['helmet'] == 'unknown'
    assert not tr.alerts


def test_ppe_only_worker_uses_scaled_height():

    tr, hist = run([[worker(100, 400, 60, person=False)] for _ in range(20)])
    assert not hist[-1][0]['too_far'] and hist[-1][0]['vest'] == 'ok'


def test_moving_worker_keeps_id():
    frames = [[worker(100 + 4 * i, 400, 150)] for i in range(60)]
    _, hist = run(frames)
    assert len({h[0]['id'] for h in hist}) == 1


def test_two_workers_keep_separate_ids():
    frames = [[worker(100, 400, 150, vest='violation'), worker(400, 420, 150)] for _ in range(40)]
    _, hist = run(frames)
    ids = {tuple(sorted(w['id'] for w in h)) for h in hist}
    assert ids == {(1, 2)}
    by_x = sorted(hist[-1], key=lambda w: w['box'][0])
    assert by_x[0]['vest'] == 'violation' and by_x[1]['vest'] == 'ok'


def test_violation_clears_when_vest_seen():
    frames = ([[worker(100, 400, 150, vest='violation')] for _ in range(40)] +
              [[worker(100, 400, 150, vest='ok')] for _ in range(40)])
    tr, hist = run(frames)
    assert hist[39][0]['vest'] == 'violation'
    assert hist[-1][0]['vest'] == 'ok'
    assert len(tr.alerts) == 1


def test_worker_walking_away_becomes_unknown():
    frames = ([[worker(100, 400, 150)] for _ in range(30)] +
              [[worker(100, 400, 70)] for _ in range(40)])
    _, hist = run(frames)
    assert hist[29][0]['vest'] == 'ok'
    assert hist[-1][0]['vest'] == 'unknown' and hist[-1][0]['too_far']


def test_alert_cooldown():
    tr = WorkerTracker(cooldown=30.0)
    v = [[worker(100, 400, 150, vest='violation')] for _ in range(30)]
    ok = [[worker(100, 400, 150, vest='ok')] for _ in range(30)]
    run(v + ok + v, tr)
    assert len(tr.alerts) == 1


def gap(seconds):
    return [[] for _ in range(round(seconds * HZ))]


def test_occluded_worker_keeps_id_state_and_no_duplicate_alert():
    v = [[worker(100, 400, 150, vest='violation')] for _ in range(40)]
    back = [[worker(110, 400, 150, vest='violation')] for _ in range(20)]
    tr, hist = run(v + gap(3) + back)
    assert hist[39][0]['vest'] == 'violation'
    after = hist[40 + round(3 * HZ)][0]
    assert after['id'] == hist[0][0]['id'], 'ID changed after occlusion'
    assert after['reacquired_after_s'] is not None and after['reacquired_after_s'] >= 3
    assert after['vest'] == 'violation', 'violation state was not held on return'
    assert hist[-1][0]['vest'] == 'violation'
    assert len(tr.alerts) == 1, f'duplicate alert: {list(tr.alerts)}'


def test_compliant_worker_returning_is_not_reset_to_unknown():
    ok = [[worker(100, 400, 150)] for _ in range(30)]
    tr, hist = run(ok + gap(4) + ok)
    returned = hist[30 + round(4 * HZ)][0]
    assert returned['id'] == hist[0][0]['id'] and returned['vest'] == 'ok'


def test_gap_longer_than_lost_ttl_gets_new_id():
    ok = [[worker(100, 400, 150)] for _ in range(20)]
    _, hist = run(ok + gap(11) + ok)
    assert hist[-1][0]['id'] != hist[0][0]['id']


def test_reappearing_far_away_gets_new_id():
    ok = [[worker(100, 400, 150)] for _ in range(20)]
    other_side = [[worker(900, 400, 150)] for _ in range(20)]
    _, hist = run(ok + gap(2) + other_side)
    assert hist[-1][0]['id'] != hist[0][0]['id']


def test_different_size_in_same_spot_gets_new_id():
    near = [[worker(100, 400, 150)] for _ in range(20)]
    small = [[worker(100, 430, 80)] for _ in range(20)]
    _, hist = run(near + gap(2) + small)
    assert hist[-1][0]['id'] != hist[0][0]['id']


def test_gate_grows_with_gap_for_walking_worker():

    before = [[worker(100, 400, 150)] for _ in range(20)]
    after = [[worker(280, 400, 150)] for _ in range(20)]
    _, hist = run(before + gap(3) + after)
    assert hist[-1][0]['id'] == hist[0][0]['id']


def test_two_workers_hidden_then_back_keep_their_own_ids():
    a, b = (lambda v: worker(100, 400, 150, vest=v)), (lambda v: worker(500, 400, 150, vest=v))
    both = [[a('violation'), b('ok')] for _ in range(30)]
    back = [[worker(510, 400, 150, vest='ok'), worker(110, 400, 150, vest='violation')] for _ in range(10)]
    _, hist = run(both + gap(2) + back)
    first = {round(w['box'][0], -2): w['id'] for w in hist[0]}
    last = {round(w['box'][0], -2): w for w in hist[-1]}
    assert last[100]['id'] == first[100] and last[100]['vest'] == 'violation'
    assert last[500]['id'] == first[500] and last[500]['vest'] == 'ok'


def walk(x0, v_px_s, seconds, h=150, y=400, t0=0.0, **kw):

    n = round(seconds * HZ)
    return [[worker(x0 + v_px_s * (t0 + i / HZ), y, h, **kw)] for i in range(n)]


def test_kalman_keeps_walker_id_through_occlusion():


    v = 150
    before = walk(100, v, 2.0)
    after = walk(100, v, 1.0, t0=4.0)
    _, hist = run(before + gap(2.0) + after)
    assert hist[-1][0]['id'] == hist[0][0]['id']


def test_kalman_reappearing_opposite_direction_gets_new_id():
    v = 150
    before = walk(500, v, 2.0)
    back = [[worker(500 - 300, 400, 150)] for _ in range(14)]
    _, hist = run(before + gap(2.0) + back)
    assert hist[-1][0]['id'] != hist[0][0]['id']


def test_kalman_prediction_stops_after_horizon():


    v = 150
    before = walk(100, v, 2.0)
    far = walk(100, v, 1.0, t0=8.0)
    _, hist = run(before + gap(6.0) + far)
    assert hist[-1][0]['id'] != hist[0][0]['id']


def test_kalman_crossing_walkers_keep_ids():
    frames = []
    for i in range(round(4 * HZ)):
        t = i / HZ
        frames.append([worker(100 + 150 * t, 400, 150), worker(700 - 150 * t, 405, 150)])
    _, hist = run(frames)
    first = {('A' if w['box'][0] < 400 else 'B'): w['id'] for w in hist[0]}

    last = {('A' if w['box'][0] > 400 else 'B'): w['id'] for w in hist[-1]}
    assert first == last, f'IDs swapped while crossing: {first} -> {last}'


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
