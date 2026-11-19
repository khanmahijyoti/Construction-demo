import bisect
import heapq
import json
import math
from pathlib import Path

DURATION = 180.0
SPEED = 110.0
STEP = 40
SEPARATION = 74.0

def distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])

def angle_delta(a, b):
    return (b - a + 180) % 360 - 180

def sample(keys, time):
    i = max(0, min(len(keys)-2, bisect.bisect_right([k[0] for k in keys], time)-1))
    a, b = keys[i:i+2]
    alpha = max(0., min(1., (time-a[0]) / max(1e-8, b[0]-a[0])))
    return [a[j] + (b[j]-a[j])*alpha for j in range(1, 5)]

class Deck:
    def __init__(self, inventory):
        self.surfaces, self.obstacles = [], []
        for actor in inventory['actors']:
            mesh = actor.get('mesh') or ''
            x, y, z = actor['origin']
            ex, ey, ez = actor['extent']
            if not (-1600 < x < 3000 and 2600 < y < 4000):
                continue
            if ('FormworkReinforcment04' in mesh or '/SM_Plywood' in mesh or '/SM_Beam01.' in mesh) and -360 < z < -295 and ez < 25:
                self.surfaces.append((x-ex, x+ex, y-ey, y+ey, z+ez, actor['label']))
            if ('SM_ConcreteColumn01.' in mesh or 'FormworkReinforcment01.' in mesh) and z+ez > -315 and z-ez < -130:
                self.obstacles.append((x, y, max(ex, ey)+43))
            if 'WheelBarrow' in mesh and -350 < z < -200:
                self.obstacles.append((x, y, 105))
        assert self.surfaces

    def height(self, p):
        hits = [r[4] for r in self.surfaces if r[0]-18 <= p[0] <= r[1]+18 and r[2]-18 <= p[1] <= r[3]+18]
        return max(hits) if hits else None

    def clear(self, p, others=()):
        return self.height(p) is not None and all(distance(p, o) > o[2] for o in self.obstacles) and all(distance(p, q) > SEPARATION+3 for q in others)

    def segment_clear(self, a, b, others):
        count = max(1, math.ceil(distance(a, b)/18))
        return all(self.clear((a[0]+(b[0]-a[0])*i/count, a[1]+(b[1]-a[1])*i/count), others) for i in range(count+1))

    def route(self, start, target, others):
        def nearest(p):
            candidates = [(round(p[0]/STEP)*STEP+dx*STEP, round(p[1]/STEP)*STEP+dy*STEP) for dx in range(-3, 4) for dy in range(-3, 4)]
            return min((q for q in candidates if self.clear(q, others) and self.segment_clear(p, q, others)), key=lambda q: distance(q, p))
        first, goal = nearest(start), nearest(target)
        queue = [(distance(first, goal), 0, first)]
        cost, parent = {first: 0.}, {}
        while queue:
            _, current_cost, p = heapq.heappop(queue)
            if p == goal:
                path = [goal]
                while path[-1] != first:
                    path.append(parent[path[-1]])
                path = [tuple(start)] + list(reversed(path)) + [tuple(target)]
                smooth, i = [path[0]], 0
                while i < len(path)-1:
                    j = len(path)-1
                    while j > i+1 and not self.segment_clear(path[i], path[j], others):
                        j -= 1
                    smooth.append(path[j]); i = j
                return [p for i, p in enumerate(smooth) if i == 0 or distance(p, smooth[i-1]) > .1]
            if current_cost > cost[p]+.01:
                continue
            for dx, dy in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
                q = (p[0]+dx*STEP, p[1]+dy*STEP)
                if not self.segment_clear(p, q, others):
                    continue
                new_cost = current_cost + distance(p, q)
                if new_cost < cost.get(q, float('inf')):
                    cost[q], parent[q] = new_cost, p
                    heapq.heappush(queue, (new_cost+distance(q,goal), new_cost, q))
        raise RuntimeError('No supported route: '+str((start, target)))

def build_plan(inventory, placements, forward_yaw=-90.):
    deck = Deck(inventory)
    homes = [tuple(w['location'][:2]) for w in placements['workers']]
    homes[8], homes[9] = (1000, 3640), (2610, 3210)
    secondary = [(590,3290),(220,3090),(390,3260),(690,3630),(1080,2900),
                 (1620,3720),(1890,2910),(2440,2920),(1040,3480),(2520,3000)]
    meetings = [(870,2990),(1100,2990),(870,3200),(1370,3480),(1100,3200),
                (1560,3480),(1870,2990),(2070,2990),(1460,3680),(1980,3190)]
    centres = [(985,3095)]*3 + [(1465,3560),(985,3095),(1465,3560),
               (1980,3075),(1980,3075),(1465,3560),(1980,3075)]
    work = ['Shoveling','DrillingFloor','IdleBreak2','DrillingFloor','PickaxeMining',
            'SawFloorVar1','Jackhammer','DrillingFloor','IdleBreak1','IdleBreak2']
    result = {'duration': DURATION, 'speed_cm_s': SPEED, 'forward_yaw': forward_yaw, 'workers': []}
    for index, entry in enumerate(placements['workers']):
        own = [homes[index], secondary[index], meetings[index]]
        others = [p for i in range(10) if i != index for p in (homes[i], secondary[i], meetings[i])]

        for p in own:
            assert deck.clear(p), 'Invalid station '+str((index+1,p))
        yaw = entry['yaw']
        keys = [[0., *homes[index], deck.height(homes[index])+89., yaw]]
        sections = []

        def append_section(a, b, clip, state):
            if b-a > .001:
                sections.append({'start': a, 'end': b, 'clip': clip, 'state': state})

        def hold(until, clip, state='work', face=None):
            nonlocal yaw
            start = keys[-1][0]
            if until <= start+.001:
                return
            if face:
                p = keys[-1][1:3]
                target_yaw = math.degrees(math.atan2(face[1]-p[1],face[0]-p[0]))-forward_yaw
                yaw += angle_delta(yaw, target_yaw)
                keys.append([min(start+.65,until), *keys[-1][1:4], yaw])
            keys.append([until, *keys[-1][1:4], yaw])
            append_section(start, until, clip, state)

        def move(target, earliest, latest, hold_until):
            nonlocal yaw
            hold(earliest, 'Idle', 'pause')
            origin = keys[-1][1:3]
            route = deck.route(origin, target, others)
            for attempt in range(31):
                departure = earliest + attempt*.4
                t, rotation = departure, yaw
                candidate = [[t, *keys[-1][1:4], rotation]]
                clips = []
                for a, b in zip(route, route[1:]):
                    heading = math.degrees(math.atan2(b[1]-a[1], b[0]-a[0]))-forward_yaw
                    delta = angle_delta(rotation, heading)
                    if abs(delta) > 4:
                        turn = max(.2, abs(delta)/180.)
                        clips.append((t,t+turn,'Idle','turn'))
                        t += turn; rotation += delta
                        candidate.append([t,a[0],a[1],deck.height(a)+89.,rotation])
                    start = t
                    count = max(1, math.ceil(distance(a,b)/20.))
                    for step in range(1,count+1):
                        p = (a[0]+(b[0]-a[0])*step/count,a[1]+(b[1]-a[1])*step/count)
                        t += distance(a,b)/SPEED/count
                        candidate.append([t,*p,deck.height(p)+89.,rotation])
                    clips.append((start,t,'Walk','walk'))
                if t > latest:
                    break
                safe = True
                for prior in result['workers']:
                    time = earliest
                    extended = [[earliest,*keys[-1][1:]], *candidate, [hold_until,*candidate[-1][1:]]]
                    while time <= hold_until:
                        if distance(sample(extended,time),sample(prior['keys'],time)) < SEPARATION:
                            safe=False; break
                        time += .12
                    if not safe:
                        break
                if safe:
                    hold(departure, 'Idle', 'yield')
                    keys.extend(candidate[1:])
                    for clip in clips:
                        append_section(*clip)
                    yaw = rotation
                    return
            raise RuntimeError('Could not schedule safe movement for worker '+str(index+1)+' at '+str(earliest))

        stagger = index*.42
        hold(8+stagger,work[index])
        move(secondary[index],8+stagger,24,32+index*.2)
        hold(32+index*.2,work[index])
        move(homes[index],32+index*.2,47,49+stagger)
        hold(49+stagger,'IdleBreak1','pause')
        move(meetings[index],49+stagger,66,79)
        hold(79,'IdleBreak1' if index%2 else 'IdleBreak2','group',centres[index])
        move(homes[index],79+stagger,98,103+stagger)
        hold(103+stagger,work[index])
        move(secondary[index],103+stagger,119,127+index*.2)
        hold(127+index*.2,work[index])
        move(meetings[index],127+index*.2,146,159)
        hold(159,'IdleBreak2' if index%2 else 'Idle','group',centres[index])
        move(homes[index],160+stagger,177,180)

        target_yaw = entry['yaw']
        end_yaw = yaw+angle_delta(yaw,target_yaw)
        hold(178,'Idle','pause')
        keys.append([179,*keys[-1][1:4],end_yaw]); yaw=end_yaw
        hold(180,'Idle','pause')

        keyed = {round(k[0]*30): k for k in keys}
        keys = [[frame/30.,*keyed[frame][1:]] for frame in sorted(keyed)]
        result['workers'].append({'label': entry['label'], 'home': homes[index],
                                  'secondary': secondary[index], 'meeting': meetings[index],
                                  'keys': keys, 'sections': sections, 'work_clip': work[index]})
    minimum = float('inf')
    for tick in range(int(DURATION*10)+1):
        poses = [sample(w['keys'],tick/10.) for w in result['workers']]
        for i,p in enumerate(poses):
            assert deck.clear(p), 'Route left deck at '+str((i,tick/10.))
            for q in poses[i+1:]:
                minimum = min(minimum,distance(p,q))
    assert minimum > SEPARATION-3, 'Worker spacing: '+str(minimum)
    result['minimum_worker_separation_cm'] = minimum
    return result

if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    plan = build_plan(json.loads((root/'Saved/hazard-site-inventory.json').read_text()),
                      json.loads((root/'Saved/hazard-workers-placement.json').read_text()))
    (root/'Saved/worker-activity-plan.json').write_text(json.dumps(plan,indent=2))
    print('Planned',len(plan['workers']),'workers; minimum spacing',plan['minimum_worker_separation_cm'])
