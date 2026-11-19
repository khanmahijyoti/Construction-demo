import unreal as u,json
registry=u.AssetRegistryHelpers.get_asset_registry()
registry.scan_paths_synchronous(['/Game/ConstructionSite'],True)
paths=['/Game/ConstructionSite/Maps/Overview','/Game/ConstructionSite/Maps/Showcase','/Game/ConstructionSite/Meshes/Building/Door/SM_Door01','/Game/ConstructionSite/Materials/Building/MI_Concrete']
report={'assets':{p:bool(u.load_asset(p)) for p in paths}}
levels=u.get_editor_subsystem(u.LevelEditorSubsystem)
report['showcase_loaded']=levels.load_level('/Game/ConstructionSite/Maps/Showcase')
actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
report['actor_count']=len(actors)
meshes=[a.get_component_by_class(u.StaticMeshComponent) for a in actors]
report['actors_with_static_mesh']=sum(1 for c in meshes if c and c.static_mesh)
with open('E:/Odyssey/output/ppe-demo/construction-site-check.json','w') as f:json.dump(report,f,indent=2)
u.log('CONSTRUCTION_SITE_CHECK '+json.dumps(report))
