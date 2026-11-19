import json
import unreal as u

levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
assert levels.load_level('/Game/ConstructionSite/Maps/Showcase')
actors = u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
report = {'actors': []}
for actor in actors:
    component = actor.get_component_by_class(u.StaticMeshComponent)
    mesh = component.static_mesh if component else None
    origin, extent = actor.get_actor_bounds(False)
    location = actor.get_actor_location()
    report['actors'].append({'name': actor.get_name(), 'label': actor.get_actor_label(),
                             'class': actor.get_class().get_name(),
                             'mesh': mesh.get_path_name() if mesh else None,
                             'location': [location.x, location.y, location.z],
                             'rotation': str(actor.get_actor_rotation()),
                             'origin': [origin.x, origin.y, origin.z],
                             'extent': [extent.x, extent.y, extent.z]})
with open('E:/Construction_Demo/Saved/hazard-site-inventory.json', 'w') as handle:
    json.dump(report, handle, indent=2)
u.log('HAZARD_SITE_INVENTORY_COMPLETE ' + str(len(actors)))
