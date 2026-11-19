import unreal as u, os, json, traceback
SOURCE='E:/Odyssey/output/ppe-demo/unreal-source'
ROOT='/Game/PPEWorker'
REPORT='E:/Odyssey/output/ppe-demo/unreal-import-report.json'
tools=u.AssetToolsHelpers.get_asset_tools()
assets=u.EditorAssetLibrary
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')

def import_mesh(name,skeleton=None):
    existing=u.load_asset(ROOT+'/Parts/SK_'+name)
    if existing:return existing
    task=u.AssetImportTask();task.filename=f'{SOURCE}/{name}.fbx';task.destination_path=ROOT+'/Parts';task.destination_name='SK_'+name;task.automated=True;task.replace_existing=True
    task.factory=u.FbxFactory();opt=u.FbxImportUI();opt.import_as_skeletal=True;opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False
    opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
    opt.skeletal_mesh_import_data.set_editor_property('ImportContentType',u.FBXImportContentType.FBXICT_ALL)
    if skeleton:opt.skeleton=skeleton
    task.options=opt;tools.import_asset_tasks([task])
    return next(u.load_asset(p) for p in task.imported_object_paths if isinstance(u.load_asset(p),u.SkeletalMesh))

body=import_mesh('Body');skeleton=body.get_editor_property('skeleton')
if not skeleton:raise RuntimeError('Body import has no skeleton')
meshes={'Body':body}
for name in ['Shirt','Pants','Boots','SafetyVest','CasualVest','Helmet','Beard','Eyelashes','Scalp','Hair']:
    meshes[name]=import_mesh(name,skeleton)
assets.save_directory(ROOT,only_if_is_dirty=False,recursive=True)

task=u.AssetImportTask();task.filename='E:/Odyssey/output/ppe-demo/retarget-test/Worker_Shoveling.fbx';task.destination_path=ROOT+'/Animations';task.destination_name='A_Worker_Shoveling';task.automated=True;task.replace_existing=True;task.factory=u.FbxFactory()
opt=u.FbxImportUI();opt.import_mesh=False;opt.import_animations=True;opt.import_materials=False;opt.import_textures=False;opt.skeleton=skeleton;opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
task.options=opt;tools.import_asset_tasks([task])
animation=next(u.load_asset(p) for p in task.imported_object_paths if isinstance(u.load_asset(p),u.AnimSequence))

textures={}
for filename in os.listdir(SOURCE+'/Textures'):
    t=u.AssetImportTask();t.filename=SOURCE+'/Textures/'+filename;t.destination_path=ROOT+'/Textures';t.automated=True;t.replace_existing=True
    tools.import_asset_tasks([t]);tex=u.load_asset(t.imported_object_paths[0]);textures[filename]=tex
    if 'Normal' in filename:
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP);tex.set_editor_property('srgb',False)
    elif 'Glossiness' in filename or 'Specular' in filename:
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS);tex.set_editor_property('srgb',False)

ML=u.MaterialEditingLibrary
def material(name):
    path=ROOT+'/Materials/'+name
    return u.load_asset(path) or tools.create_asset(name,ROOT+'/Materials',u.Material,u.MaterialFactoryNew())
def node(mat,kind):return ML.create_material_expression(mat,getattr(u,'MaterialExpression'+kind))
def link(a,out,b,inp):
    if ML.connect_material_expressions(a,out,b,inp):return
    if inp=='Input' and ML.connect_material_expressions(a,out,b,''):return
    raise RuntimeError(f'Material link failed {a.get_class().get_name()} {out} -> {b.get_class().get_name()} {inp}')
def scalar(mat,value):
    n=node(mat,'Constant');n.set_editor_property('r',value);return n
def vector(mat,color,param=None):
    n=node(mat,'VectorParameter' if param else 'Constant3Vector')
    n.set_editor_property('default_value' if param else 'constant',u.LinearColor(*color))
    if param:n.set_editor_property('parameter_name',param)
    return n
def mathnode(mat,kind,a,b):
    n=node(mat,kind);link(a,'',n,'A');link(b,'',n,'B');return n
def sample(mat,key,normal=False):
    n=node(mat,'TextureSample');n.set_editor_property('texture',textures[key])
    if normal:n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    return n
def output(mat,n,prop,out=''):ML.connect_material_property(n,out,prop)
def channel(mat,tex,c):
    n=node(mat,'ComponentMask')
    for letter in 'rgba':n.set_editor_property(letter,letter==c)
    link(tex,'RGB',n,'Input');return n
def greater(mat,a,b):
    difference=mathnode(mat,'Subtract',a,b)
    amplified=mathnode(mat,'Multiply',difference,scalar(mat,1000))
    n=node(mat,'Saturate');link(amplified,'',n,'Input');return n

mats={}
for style in ['Atlas','Skin','Cloth','PlainCloth','Helmet','FacialHair','Hair','YellowVest']:
    m=material('M_Worker_'+style);ML.delete_all_material_expressions(m)
    tint=vector(m,(1,1,1,1),'Tint')
    rough=scalar(m,.8)
    if style=='Hair':
        base=vector(m,(.012,.006,.003,1));m.set_editor_property('two_sided',True)
    elif style in ['PlainCloth','Helmet']:
        base=tint
        if style=='Helmet':rough=scalar(m,.36)
    else:
        key='Ch17_1002_Diffuse.png' if style=='FacialHair' else 'Ch17_1001_Diffuse.png'
        tex=sample(m,key)
        if style=='Cloth':
            gray=node(m,'Desaturation');link(tex,'RGB',gray,'Input');link(scalar(m,1),'',gray,'Fraction')
            shade=mathnode(m,'Add',mathnode(m,'Multiply',gray,scalar(m,.9)),scalar(m,.4));base=mathnode(m,'Multiply',shade,tint)
        elif style=='YellowVest':
            r=channel(m,tex,'r');g=channel(m,tex,'g');b=channel(m,tex,'b')
            orange=greater(m,r,mathnode(m,'Multiply',g,scalar(m,1.3)))
            stripe=mathnode(m,'Multiply',greater(m,g,mathnode(m,'Multiply',b,scalar(m,1.6))),mathnode(m,'Subtract',scalar(m,1),orange))
            gray=node(m,'Desaturation');link(tex,'RGB',gray,'Input');link(scalar(m,1),'',gray,'Fraction')
            shade=mathnode(m,'Add',mathnode(m,'Multiply',gray,scalar(m,.55)),scalar(m,.45))
            yellow=mathnode(m,'Multiply',shade,vector(m,(.72,1,.008,1)));silver=mathnode(m,'Multiply',shade,vector(m,(.72,.76,.78,1)))
            a=node(m,'LinearInterpolate');link(tex,'RGB',a,'A');link(yellow,'',a,'B');link(orange,'',a,'Alpha')
            base=node(m,'LinearInterpolate');link(a,'',base,'A');link(silver,'',base,'B');link(stripe,'',base,'Alpha')
            rough=mathnode(m,'Subtract',scalar(m,.72),mathnode(m,'Multiply',stripe,scalar(m,.4)))
        else:base=mathnode(m,'Multiply',tex,tint)
        normal=sample(m,'Ch17_1002_Normal.png' if style=='FacialHair' else 'Ch17_1001_Normal.png',True);output(m,normal,u.MaterialProperty.MP_NORMAL,'RGB')
        if style=='FacialHair':
            m.set_editor_property('blend_mode',u.BlendMode.BLEND_MASKED);m.set_editor_property('two_sided',True);output(m,tex,u.MaterialProperty.MP_OPACITY_MASK,'A')
    output(m,base,u.MaterialProperty.MP_BASE_COLOR);output(m,rough,u.MaterialProperty.MP_ROUGHNESS)
    ML.layout_material_expressions(m);ML.recompile_material(m);mats[style]=m

worker_class=u.load_class(None,'/Script/PPEWorkers.PPEConstructionWorker')
factory=u.BlueprintFactory();factory.set_editor_property('parent_class',worker_class)
bp=u.load_asset(ROOT+'/Blueprints/BP_ConstructionWorker') or tools.create_asset('BP_ConstructionWorker',ROOT+'/Blueprints',u.Blueprint,factory)
u.BlueprintEditorLibrary.compile_blueprint(bp)
cdo=u.get_default_object(bp.generated_class())
for key,mesh in meshes.items():cdo.set_editor_property(key.lower()+'_asset' if key not in ['SafetyVest','CasualVest','Eyelashes'] else {'SafetyVest':'safety_vest_asset','CasualVest':'casual_vest_asset','Eyelashes':'eyelashes_asset'}[key],mesh)
for key,style in {'atlas_material':'Atlas','skin_material':'Skin','cloth_material':'Cloth','plain_cloth_material':'PlainCloth','orange_vest_material':'Atlas','yellow_vest_material':'YellowVest','hardhat_material':'Helmet','beard_material':'FacialHair','hair_material':'Hair'}.items():cdo.set_editor_property(key,mats[style])
cdo.set_editor_property('animation_clip',animation)
u.BlueprintEditorLibrary.compile_blueprint(bp);assets.save_loaded_asset(bp)

with open('E:/Odyssey/output/ppe-demo/character_variants.json',encoding='utf-8') as f:configs=json.load(f)
skin={'Original light':(1,1,1,1),'Medium':(.64,.46,.34,1),'Deep':(.28,.17,.115,1)}
hats={'White':(.8,.8,.8,1),'Yellow':(1,.61,.015,1),'Blue':(.025,.18,.65,1),'Red':(.65,.025,.018,1)}
colors={'Tan':(.32,.21,.105,1),'Gray':(.20,.215,.23,1),'Olive':(.12,.16,.055,1),'Brown':(.17,.075,.035,1),'Slate':(.14,.22,.28,1),'Burgundy':(.19,.025,.035,1),'Charcoal':(.035,.042,.05,1),'Navy':(.018,.035,.075,1),'Sand':(.47,.34,.19,1),'Denim':(.035,.10,.22,1),'Original':(.025,.04,.065,1)}
presets=[]
for config in configs:
    name='BP_Worker_'+config['collection'];fac=u.BlueprintFactory();fac.set_editor_property('parent_class',bp.generated_class())
    preset=u.load_asset(ROOT+'/Presets/'+name) or tools.create_asset(name,ROOT+'/Presets',u.Blueprint,fac)
    u.BlueprintEditorLibrary.compile_blueprint(preset);d=u.get_default_object(preset.generated_class())
    props={'wear_helmet':config['helmet'],'wear_safety_vest':config['safety_vest'],'yellow_safety_vest':config.get('vest_color')=='Yellow','has_beard':config['beard'],'skin_tint':u.LinearColor(*skin[config['skin_tone']]),'helmet_color':u.LinearColor(*hats.get(config.get('hardhat_color'),hats['White'])),'shirt_color':u.LinearColor(*colors.get(config.get('shirt_color','Original'),colors['Original'])),'pants_color':u.LinearColor(*colors.get(config.get('pants_color'),(.12,.09,.055,1))),'casual_vest_color':u.LinearColor(*colors.get(config.get('casual_vest_color'),colors['Tan']))}
    for key,value in props.items():d.set_editor_property(key,value)
    u.BlueprintEditorLibrary.compile_blueprint(preset);assets.save_loaded_asset(preset)
    presets.append((preset,config))

levels=u.get_editor_subsystem(u.LevelEditorSubsystem);actors=u.get_editor_subsystem(u.EditorActorSubsystem)
map_path=ROOT+'/Maps/L_WorkerShowcase'
if not levels.new_level(map_path):raise RuntimeError('Cannot create showcase map')
floor=actors.spawn_actor_from_class(u.StaticMeshActor,u.Vector(360,345,-3));floor.set_actor_label('Worker Showcase Floor');floor.static_mesh_component.set_static_mesh(u.load_asset('/Engine/BasicShapes/Plane'));floor.set_actor_scale3d(u.Vector(22,22,1))
floor_mat=material('M_ShowcaseFloor');ML.delete_all_material_expressions(floor_mat);output(floor_mat,vector(floor_mat,(.13,.15,.17,1)),u.MaterialProperty.MP_BASE_COLOR);output(floor_mat,scalar(floor_mat,.9),u.MaterialProperty.MP_ROUGHNESS);ML.recompile_material(floor_mat);floor.static_mesh_component.set_material(0,floor_mat)
sun=actors.spawn_actor_from_class(u.DirectionalLight,u.Vector(0,0,600),u.Rotator(pitch=-45,yaw=-35,roll=0));sun.light_component.set_editor_property('intensity',5.0);sun.light_component.set_editor_property('atmosphere_sun_light',True)
sky=actors.spawn_actor_from_class(u.SkyAtmosphere,u.Vector(0,0,0));sky.set_actor_label('Sky')
ambient=actors.spawn_actor_from_class(u.SkyLight,u.Vector(0,0,400));ambient.light_component.set_editor_property('intensity',1.2);ambient.light_component.set_editor_property('real_time_capture',True)
spawned=[]
for i,(preset,config) in enumerate(presets):
    row=i//4;col=i%4;loc=u.Vector(row*240,col*230,88)
    actor=actors.spawn_actor_from_class(preset.generated_class(),loc,u.Rotator(pitch=0,yaw=180,roll=0));actor.set_actor_label(config['collection']);actor.set_editor_property('animate',False);actor.apply_appearance()
    label=actors.spawn_actor_from_class(u.TextRenderActor,u.Vector(row*240,col*230,208),u.Rotator(pitch=0,yaw=180,roll=0));label.set_actor_label('Label '+config['collection']);component=label.get_component_by_class(u.TextRenderComponent);component.set_text(config['collection'].replace('_',' '));component.set_world_size(11);component.set_horizontal_alignment(u.HorizTextAligment.EHTA_CENTER)
    spawned.append(actor)
hero=actors.spawn_actor_from_class(bp.generated_class(),u.Vector(-270,345,88),u.Rotator(pitch=0,yaw=180,roll=0));hero.set_actor_label('Animated Shoveling Preview');hero.set_editor_property('animate',True);hero.apply_appearance()
camera=actors.spawn_actor_from_class(u.CameraActor,u.Vector(-950,280,650));rotation=u.MathLibrary.find_look_at_rotation(camera.get_actor_location(),u.Vector(250,345,80));camera.set_actor_rotation(rotation,False);camera.set_actor_label('Worker Showcase Camera');camera.camera_component.set_editor_property('field_of_view',55)
start=actors.spawn_actor_from_class(u.PlayerStart,u.Vector(-650,345,220),u.Rotator(pitch=-8,yaw=0,roll=0));start.set_actor_label('Showcase Start')
levels.save_current_level();assets.save_directory(ROOT,only_if_is_dirty=False,recursive=True)
report={'project':'E:/Construction_Demo/Construction_Demo.uproject','map':map_path,'blueprint':bp.get_path_name(),'animation':animation.get_path_name(),'skeleton':skeleton.get_path_name(),'parts':{k:v.get_path_name() for k,v in meshes.items()},'body_slots':[str(m.material_slot_name) for m in body.get_editor_property('materials')],'presets':len(presets),'actors':len(spawned)+1,'skeletal_mesh_count':len(meshes),'note':'Hair exported as a shared skinned strand mesh for this demo.'}
with open(REPORT,'w') as f:json.dump(report,f,indent=2)
u.log('PPE_IMPORT_COMPLETE '+json.dumps(report))
