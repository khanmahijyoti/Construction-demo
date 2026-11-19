"""Offline tests for ppe_fusion's per-worker verdicts (synthetic detections).

    AI/.venv-gpu/Scripts/python.exe AI/test_ppe_fusion.py
"""
from ppe_fusion import fuse

HEAD = [100, 400, 130, 418]  # helmet box, 18 px tall


def det(kind, box, conf=0.8, model='y11n'):
    return {'kind': kind, 'conf': conf, 'box': box, 'model': model}


def person(reach_heads):
    """Person box from the helmet top down to `reach_heads` head heights."""
    return det('person', [92, 400, 138, 400 + 18 * reach_heads])


def only(dets):
    ws = fuse(dets)
    assert len(ws) == 1, ws
    return ws[0]


def test_full_body_no_vest_is_violation():
    assert only([person(9), det('helmet', HEAD)])['vest'] == 'violation'


def test_legs_hidden_but_torso_visible_is_violation():
    # The 7:25 case: legs hidden by a worker in front, person box ~6 head heights.
    assert only([person(6), det('helmet', HEAD)])['vest'] == 'violation'


def test_torso_hidden_is_unknown():
    # Only head and shoulders visible above a railing / rebar.
    assert only([person(3), det('helmet', HEAD)])['vest'] == 'unknown'


def test_no_person_box_is_unknown():
    assert only([det('helmet', HEAD)])['vest'] == 'unknown'


def test_no_helmet_with_hidden_torso_is_unknown_vest():
    w = only([person(3), det('no_helmet', HEAD)])
    assert w['helmet'] == 'violation' and w['vest'] == 'unknown'


def test_explicit_no_vest_counts_without_torso_evidence():
    w = only([person(3), det('helmet', HEAD), det('no_vest', [95, 420, 135, 450], model='v8s')])
    assert w['vest'] == 'violation'


def test_vest_overrules_no_vest():
    w = only([person(9), det('helmet', HEAD), det('vest', [95, 420, 135, 470]),
              det('no_vest', [95, 420, 135, 470], model='v8s')])
    assert w['vest'] == 'ok'


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
