from __future__ import annotations

NORMALISE = {
    'person': 'person', 'human': 'person',
    'hardhat': 'helmet', 'helmet': 'helmet',
    'no-hardhat': 'no_helmet', 'no-helmet': 'no_helmet',
    'safety vest': 'vest', 'vest': 'vest',
    'no-safety vest': 'no_vest', 'no-vest': 'no_vest',
}
PPE_KINDS = ('helmet', 'no_helmet', 'vest', 'no_vest')
# A missing vest is only inferred (no explicit no_vest box) when the torso is evidently
# visible: the person box must reach at least this many head-box heights below the top of
# the helmet / no-helmet box, i.e. to about hip level. Measured on recorded frames: fully
# visible workers reach 6.8-10.7 head heights; hips are at roughly 4-5.5.
TORSO_REACH_HEADS = 5.0


def torso_visible(head_box, person_box) -> bool:
    if not head_box or not person_box:
        return False
    head_h = head_box[3] - head_box[1]
    return head_h > 0 and person_box[3] >= head_box[1] + TORSO_REACH_HEADS * head_h


def normalise(name: str) -> str | None:
    return NORMALISE.get(name.lower())


def _area(b):
    return max(0., b[2] - b[0]) * max(0., b[3] - b[1])


def _inter(a, b):
    return _area((max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])))


def _iou(a, b):
    i = _inter(a, b)
    return i / (_area(a) + _area(b) - i + 1e-9)


def _union(a, b):
    return [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]


def _x_overlap(a, b):

    w = min(a[2] - a[0], b[2] - b[0])
    return max(0., min(a[2], b[2]) - max(a[0], b[0])) / (w + 1e-9)


def fuse(dets: list[dict], conf: float = 0.5, person_conf: float = 0.4) -> list[dict]:

    persons = sorted((d for d in dets if d['kind'] == 'person' and d['conf'] >= person_conf),
                     key=lambda d: -d['conf'])
    ppe = [d for d in dets if d['kind'] in PPE_KINDS and d['conf'] >= conf]


    workers = []
    for p in persons:
        for w in workers:
            if _iou(p['box'], w['person_box']) > 0.45:
                w['sources'].add(p['model'])
                break
        else:
            workers.append({'person_box': list(p['box']), 'box': list(p['box']),
                            'sources': {p['model']}, 'items': []})


    orphans = []
    for d in ppe:
        best, best_c = None, 0.
        for w in workers:
            c = _inter(d['box'], w['person_box']) / (_area(d['box']) + 1e-9)
            if c > best_c:
                best, best_c = w, c
        if best is not None and best_c >= 0.5:
            best['items'].append(d)
        else:
            orphans.append(d)


    for d in sorted(orphans, key=lambda d: d['box'][1]):
        for w in workers:
            if not w['person_box'] and _x_overlap(d['box'], w['box']) > 0.5:
                w['items'].append(d)
                w['box'] = _union(w['box'], d['box'])
                break
        else:
            workers.append({'person_box': None, 'box': list(d['box']),
                            'sources': set(), 'items': [d]})

    out = []
    for w in workers:
        if not w['items']:


            continue
        best = {}
        for d in w['items']:
            if d['kind'] not in best or d['conf'] > best[d['kind']]['conf']:
                best[d['kind']] = d
            w['box'] = _union(w['box'], d['box'])
        h, nh, v, nv = (best.get(k) for k in PPE_KINDS)

        if nh and (not h or nh['conf'] > h['conf']):
            helmet = 'violation'
        elif h:
            helmet = 'ok'
        else:
            helmet = 'unknown'

        if v:
            vest = 'ok'
        elif nv:
            vest = 'violation'  # a model explicitly judged the torso as having no vest
        elif torso_visible((h or nh or {}).get('box'), w['person_box']):
            vest = 'violation'  # no vest found although the torso is visible
        else:
            vest = 'unknown'    # torso hidden or not evidenced: can't tell

        out.append({
            'box': w['box'],
            'person_box': w['person_box'],
            'helmet': helmet, 'vest': vest,
            'helmet_box': (h or nh or {}).get('box'),
            'vest_box': (v or nv or {}).get('box'),
            'evidence': {k: {'conf': round(d['conf'], 3), 'model': d['model']} for k, d in best.items()},
            'person_models': sorted(w['sources']),
        })
    return out
