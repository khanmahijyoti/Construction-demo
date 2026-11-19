import json
import unreal as u

assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Game/ConstructionSite/Maps/Showcase')
actors = u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
report = {'cameras': [], 'workers': [], 'api': {}}
for a in actors:
    if 'camera' in (a.get_class().get_name() + a.get_actor_label()).lower():
        item = {'name': a.get_name(), 'label': a.get_actor_label(), 'class': a.get_class().get_name(), 'components': []}
        for c in a.get_components_by_class(u.ActorComponent):
            d = {'name': c.get_name(), 'class': c.get_class().get_name()}
            if isinstance(c, u.SceneComponent):
                d['location'] = str(c.get_world_location())
                d['rotation'] = str(c.get_world_rotation())
            for prop in ['texture_target', 'capture_source', 'fov_angle', 'capture_every_frame', 'capture_on_movement', 'field_of_view']:
                try:
                    value = c.get_editor_property(prop)
                    d[prop] = value.get_path_name() if isinstance(value, u.Object) else str(value)
                except Exception:
                    pass
            item['components'].append(d)
        report['cameras'].append(item)
    if isinstance(a, u.PPEConstructionWorker):
        origin, extent = a.get_actor_bounds(False)
        report['workers'].append({'label': a.get_actor_label(), 'location': str(a.get_actor_location()), 'origin': str(origin), 'extent': str(extent), 'helmet': a.get_editor_property('wear_helmet'), 'vest': a.get_editor_property('wear_safety_vest')})
for name in ['export_render_target', 'export_texture2d', 'render_target_create_static_texture2d_editor_only', 'import_file_as_texture2d']:
    fn = getattr(u.RenderingLibrary, name, None)
    report['api'][name] = str(getattr(fn, '__doc__', 'missing'))
with open('E:/Construction_Demo/Saved/yolo-camera-inspection.json', 'w') as f:
    json.dump(report, f, indent=2)
u.log('YOLO_CAMERA_INSPECTION_COMPLETE')
