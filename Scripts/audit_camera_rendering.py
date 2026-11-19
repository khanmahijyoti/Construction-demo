import json
import unreal as u

u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Game/ConstructionSite/Maps/Showcase')
actors = u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
report = {'captures': [], 'post_volumes': [], 'cameras': []}
fields = ['auto_exposure_method', 'auto_exposure_bias', 'auto_exposure_min_brightness',
          'auto_exposure_max_brightness', 'dynamic_global_illumination_method', 'reflection_method',
          'lumen_surface_cache_resolution', 'lumen_final_gather_quality', 'lumen_scene_lighting_quality',
          'film_slope', 'film_toe', 'film_shoulder', 'color_gamma', 'color_gain', 'indirect_lighting_intensity']
def post_info(post):
    result = {}
    for name in fields:
        try:
            result[name] = {'override': bool(getattr(post, 'override_' + name)), 'value': str(getattr(post, name))}
        except Exception:
            pass
    return result
for actor in actors:
    cap = actor.get_component_by_class(u.SceneCaptureComponent2D)
    if cap:
        item = {'actor': actor.get_actor_label(), 'post': post_info(cap.post_process_settings),
                'flags': [{'name': f.show_flag_name, 'enabled': f.enabled} for f in cap.show_flag_settings]}
        for name in ['capture_source', 'post_process_blend_weight', 'always_persist_rendering_state',
                     'capture_every_frame', 'main_view_family', 'main_view_camera',
                     'inherit_main_view_camera_post_process_settings', 'render_in_main_renderer']:
            item[name] = str(getattr(cap, name))
        report['captures'].append(item)
    if isinstance(actor, u.PostProcessVolume):
        report['post_volumes'].append({'actor': actor.get_actor_label(), 'enabled': actor.enabled,
                                     'unbound': actor.unbound, 'blend_weight': actor.blend_weight,
                                     'priority': actor.priority, 'post': post_info(actor.settings)})
    component = actor.get_component_by_class(u.CameraComponent)
    if component:
        report['cameras'].append({'actor': actor.get_actor_label(), 'post': post_info(component.post_process_settings)})
with open('E:/Construction_Demo/AI/rendering-audit.json', 'w') as f:
    json.dump(report, f, indent=2)
