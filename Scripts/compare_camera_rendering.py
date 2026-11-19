import os
from pathlib import Path
os.environ['YOLO_CAPTURE_COUNT'] = '10'
script = Path('E:/Construction_Demo/Scripts/capture_yolo_camera.py')
exec(compile(script.read_text(), str(script), 'exec'), globals())
reference_camera = u.get_editor_subsystem(u.EditorActorSubsystem).spawn_actor_from_class(
    u.CameraActor, capture.get_world_location(), capture.get_world_rotation(), transient=True)
reference_component = reference_camera.get_component_by_class(u.CameraComponent)
reference_component.field_of_view = capture.fov_angle
reference_component.aspect_ratio = width / height
reference_component.constrain_aspect_ratio = True
reference_component.post_process_settings = original_post.copy()
reference_component.post_process_blend_weight = original['post_blend']
u.AutomationLibrary.take_high_res_screenshot(
    width, height, str(OUT / 'matched_viewport_reference.png'), camera=reference_camera, delay=22.0)
