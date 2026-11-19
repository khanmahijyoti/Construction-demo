import ast
import json
from pathlib import Path
import unreal as u

root = Path('E:/Construction_Demo')
tree = ast.parse((root/'Scripts/pixelstream_cctv.py').read_text())
helper = next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='attach_view_camera')
namespace = {'u':u}
exec(compile(ast.Module(body=[helper],type_ignores=[]),'pixelstream_cctv.py','exec'),namespace)
levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
assert levels.load_level('/Game/ConstructionSite/Maps/Showcase')
actors = u.get_editor_subsystem(u.EditorActorSubsystem)
blueprint = next(a for a in actors.get_all_level_actors() if a.get_class().get_name().startswith('BP_Camera_C'))
capture = blueprint.get_component_by_class(u.SceneCaptureComponent2D)
assert capture
original_actor = blueprint.get_actor_transform().copy()
original_capture = capture.get_relative_transform().copy()
camera = actors.spawn_actor_from_class(u.CameraActor,capture.get_world_location(),capture.get_world_rotation())
report = {'checks':[],'level_camera_actors':[a.get_actor_label() for a in actors.get_all_level_actors()
                                            if isinstance(a,u.CameraActor) and a != camera]}
def check(label):
    assert camera.get_owner()==blueprint
    assert camera.get_attach_parent_actor()==blueprint
    assert camera.root_component.get_attach_parent()==capture
    a,b = camera.get_actor_location(),capture.get_world_location()
    error = ((a.x-b.x)**2+(a.y-b.y)**2+(a.z-b.z)**2)**.5
    delta = u.MathLibrary.normalized_delta_rotator(camera.get_actor_rotation(),capture.get_world_rotation())
    assert error < .01 and max(abs(delta.pitch),abs(delta.yaw),abs(delta.roll)) < .01
    report['checks'].append({'operation':label,'position_error_cm':error})
try:
    namespace['attach_view_camera'](camera,blueprint,capture)
    check('initial attachment')
    p = blueprint.get_actor_location()
    blueprint.set_actor_location(u.Vector(p.x+157,p.y-83,p.z+41),False,True)
    check('moving BP_Camera')
    r = blueprint.get_actor_rotation()
    blueprint.set_actor_rotation(u.Rotator(pitch=r.pitch+7,yaw=r.yaw+33,roll=r.roll),False)
    check('rotating BP_Camera')
    p = capture.get_relative_transform().translation
    capture.set_relative_location(u.Vector(p.x+40,p.y+20,p.z+12),False,True)
    check('moving scene capture component')
    r = capture.get_editor_property('relative_rotation')
    capture.set_relative_rotation(u.Rotator(pitch=r.pitch-12,yaw=r.yaw+17,roll=r.roll+3),False,True)
    check('rotating scene capture component')
finally:
    capture.set_relative_transform(original_capture,False,True)
    blueprint.set_actor_transform(original_actor,False,True)
    camera.destroy_actor()
report['passed'] = True
(root/'Saved/cctv-attachment-validation.json').write_text(json.dumps(report,indent=2))
u.log('CCTV_ATTACHMENT_VALIDATED')
