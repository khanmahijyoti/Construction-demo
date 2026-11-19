import json
import math
import sys
import time
import traceback
from pathlib import Path
import unreal as u

ROOT = Path('E:/Construction_Demo')
sys.path.insert(0,str(ROOT/'Scripts'))
from worker_activity_plan import sample
plan = json.loads((ROOT/'Saved/worker-activity-plan.json').read_text())
out = ROOT/'Saved/ActivityPreview'
out.mkdir(parents=True,exist_ok=True)
state = {'samples':[],'errors':[],'started':time.monotonic(),'captures':set()}

def tick(_delta):
    try:
        if time.monotonic()-state['started'] > 200:
            raise RuntimeError('Scenario observation timed out')
        world = next((w for w in u.ObjectIterator(u.World)
                      if w.get_name()=='Showcase' and u.GameplayStatics.get_player_controller(w,0)),None)
        if not world:
            return
        directors = u.GameplayStatics.get_all_actors_of_class(world,u.LevelSequenceActor)
        director = next((a for a in directors if a.get_sequence() and a.get_sequence().get_name()=='LS_HazardWorkerActivity'),None)
        if not director or not director.get_sequence_player():
            return
        player = director.get_sequence_player()
        assert player.is_playing(), 'Scenario did not autoplay'
        now = player.get_current_time()
        seconds = (now.time.frame_number.value+now.time.sub_frame)*now.rate.denominator/now.rate.numerator
        mark = next((at for at in (3,18,38,68) if seconds >= at and at not in state['captures']),None)
        if mark is None:
            return
        workers = {a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.PPEConstructionWorker)
                   if 'HazardSiteWorker' in [str(t) for t in a.tags]}
        entry = {'time':seconds,'workers':[]}
        for schedule in plan['workers']:
            actor = workers[schedule['label']]
            p = actor.get_actor_location()
            expected = sample(schedule['keys'],seconds)
            error = math.sqrt(sum((a-b)**2 for a,b in zip((p.x,p.y,p.z),expected[:3])))
            assert error < 4, actor.get_actor_label()+' did not follow sequence: '+str(error)
            entry['workers'].append({'label':actor.get_actor_label(),'location_error_cm':error,
                                    'animation_mode':str(actor.mesh.get_editor_property('animation_mode'))})
        state['samples'].append(entry)
        state['captures'].add(mark)
        if mark != 3:
            path = str(out/('activity_'+str(mark)+'.png')).replace('\\','/')
            u.SystemLibrary.execute_console_command(world,'HighResShot 1 filename='+path)
        state['passed'] = len(state['samples']) == 4
        payload = {k:v for k,v in state.items() if k not in ('captures','handle')}
        (out/'live-validation.json').write_text(json.dumps(payload,indent=2))
        u.log('WORKER_ACTIVITY_LIVE_SAMPLE '+str(mark))
        if state['passed']:
            u.unregister_slate_post_tick_callback(state['handle'])
            u.log('WORKER_ACTIVITY_LIVE_PASSED')
    except Exception:
        state['errors'].append(traceback.format_exc())
        payload = {k:v for k,v in state.items() if k not in ('captures','handle')}
        (out/'live-validation.json').write_text(json.dumps(payload,indent=2))
        u.log_error(state['errors'][-1])
        u.unregister_slate_post_tick_callback(state['handle'])

state['handle'] = u.register_slate_post_tick_callback(tick)
