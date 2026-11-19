import unreal as u

PATHS = [f'/Game/PPEWorker/Materials/{n}' for n in (
    'M_Worker_Atlas', 'M_Worker_Cloth', 'M_Worker_FacialHair', 'M_Worker_Hair',
    'M_Worker_Helmet', 'M_Worker_PlainCloth', 'M_Worker_Skin', 'M_Worker_YellowVest')]

for path in PATHS:
    mat = u.EditorAssetLibrary.load_asset(path)
    if not isinstance(mat, u.Material):
        u.log_error(f'MATUSAGE not a base Material: {path}')
        continue

    u.MaterialEditingLibrary.set_material_usage(mat, u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    u.MaterialEditingLibrary.recompile_material(mat)
    saved = u.EditorAssetLibrary.save_asset(path, only_if_is_dirty=False)
    u.log(f'MATUSAGE {path} used_with_skeletal_mesh={mat.get_editor_property("used_with_skeletal_mesh")} saved={saved}')
