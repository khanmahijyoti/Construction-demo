# Construction workers

The modular workers are installed in this project under `/Game/PPEWorker`.

Restart an already-open Unreal Editor once to load the new PPEWorkers runtime module.

Open `/Game/PPEWorker/Maps/L_WorkerShowcase` for the 16 appearance presets and a shoveling-animation example. Open `/Game/ConstructionSite/Maps/Showcase` for the construction-site activity scenario.

## Customize a worker

The construction level `/Game/ConstructionSite/Maps/Showcase` contains ten worker presets on the plywood/rebar platforms around the excavation shown in the hazard-site reference. Find them in the Outliner folder **Hazard Site Workers**.

Press **Play** or **Simulate** to run the three-minute repeating activity sequence. Workers walk between work stations, pause for work or idle animations, and meet in three groups. Seven workers have hand-mounted tools that appear during their work sections. Group pauses occur roughly around 65–79 and 146–159 seconds. The schedules are staggered and repeat consistently for camera/detection comparisons.

Edit `/Game/PPEWorker/Sequences/LS_HazardWorkerActivity` in Sequencer to adjust movement, timing, body animation or tool visibility. The level actor **Hazard Worker Activity - Auto Play** starts the sequence and loops it indefinitely; it does not change the camera or player input. Clothing continues to follow the animated body through Leader Pose.

The scenario's walking sections use `A_Worker_Walk_Fwd`, retargeted from `/Game/NPCsBundle/Demo/Characters/Mannequins/Animations/Manny/MM_Walk_Fwd`. Its baked root travel is removed so Sequencer remains responsible for world movement. The earlier `A_Worker_Walk` from `MM_Walk_InPlace` is retained but no longer assigned to the scenario. `Scripts/use_forward_worker_walk.py` creates the new clip and updates the existing sequence without changing the level or its routes.

This is a scripted scenario. Character Movement **Default Land Movement Mode** remains `None`; Sequencer drives the actor transforms along routes constrained to the existing deck, around pillars and away from other workers. Autonomous AI navigation, dynamic avoidance and restricted-zone triggers are separate future work.

Generation: `Scripts/worker_activity_plan.py` and `Scripts/build_worker_activity.py`. Validation: `Scripts/verify_worker_activity.py`. The schedule, build summary and evaluation results are under `Saved/worker-activity-*.json`. Before regenerating, close the scenario in Sequencer and save the current level. The generator rebuilds this owned sequence and its tool actors. The previous static placement script `Scripts/place_hazard_workers.py` is retained for rebuilding the original placements and should not be run over a customized scenario.

Map backup before the scenario: `Saved/Backups/WorkerScenario/Showcase-before-activity.umap`. Original map backup before any workers: `Saved/Backups/HazardWorkers/Showcase-before-workers.umap`.

Place `/Game/PPEWorker/Blueprints/BP_ConstructionWorker` in a level. In Details, expand the Worker categories:

- Equipment: Wear Helmet, Wear Safety Vest, Yellow Safety Vest.
- Appearance: Has Beard, Skin Tint, Helmet Color, Shirt Color, Pants Color, Casual Vest Color.
- Animation: Animate, Animation Clip, Animation Rate, Animation Offset.

Changes are applied in the editor by the construction hook. At runtime, change properties and call `Apply Appearance` from Blueprint to refresh them. `Apply Appearance` is also available as a Call in Editor button.

The no-safety-vest state shows the non-reflective casual vest. It does not hide the whole torso garment, because the original shirt mesh has no complete torso underneath it.

## Shared assets

The presets under `/Game/PPEWorker/Presets` inherit the base Blueprint. All 16 use the same 11 skeletal part assets and Skeleton under `/Game/PPEWorker/Parts`. Clothing components use Leader Pose to follow the body animation.

Textures and Unreal materials are under the corresponding PPEWorker folders. Material `Tint` parameters drive appearance colors. The eye material is separate from the skin-tinted body section.

The Blender hair is converted to a shared, head-weighted strand mesh for this demo (70,368 vertices, 61,572 source polygons), not an Unreal Groom asset. This keeps it usable with the shared skeleton without requiring Alembic Groom plugins. The original Blender groom is preserved.

`/Game/PPEWorker/Animations/A_Worker_Shoveling` is the animation baked from the user's Construction NPC Animations pack onto the Mixamo worker rig.

## Retargeted site animations

Twenty additional clips are baked onto the production `/Game/PPEWorker/Parts/SK_Body_Skeleton` and saved in `/Game/PPEWorker/Animations`, with the prefix `A_Worker_`:

- Movement: `Walk`, `Jog` (both in place).
- Idle: `Idle`, `Idle1H`, `Idle2H`, `IdleBreak1`, `IdleBreak2`.
- Transport: `CarryLoad`, `Cartwheel` (the source pack's wheelbarrow-related clip), both in place.
- Tools: `Equip1H`, `Equip2H`, `Unequip1H`, `Unequip2H`.
- Work: `HammeringFloor`, `HammeringWall`, `DrillingFloor`, `DrillWall`, `Jackhammer`, `PickaxeMining`, `SawFloorVar1`.

The existing `A_Worker_Shoveling` is preserved. Source pack assets are unchanged.

To review the clips on a fully clothed worker, open `L_WorkerShowcase`, select a worker, and set **Worker > Animation > Animation Clip** to a retargeted clip. Keep **Animate** enabled and press Play or Simulate. Alternatively, double-click a clip in the Content Browser to scrub it in the Animation Editor. Restart the editor if newly generated assets have not appeared.

Visual review is pending. Check foot contact/sliding, facing direction, shoulders and wrists, loop seams, and tool grip. Equip/unequip clips are intended as one-shot actions; the current worker actor loops whichever clip is selected. Props are not attached by these animation assets. Runtime transitions and navigation are separate setup work.

Reusable setup: `/Game/PPEWorker/Rigs/IK_Manny_Source`, `IK_PPE_Worker`, and `RTG_Manny_PPEWorker`. The retargeter uses automatic chain mapping, target pose alignment and Full Body IK. Root-motion extraction is disabled on the new clips for CharacterMovement-driven workers.

- Rebuild missing outputs: `Scripts/retarget_worker_animations.py` (preserves existing outputs and their manual edits).
- After rebuilding transport clips, run `Scripts/make_worker_transport_in_place.py` to remove their linear travel and validate all clips. This edits `Jog`, `CarryLoad`, and `Cartwheel`.
- Fresh-process structural validation: `Scripts/verify_worker_retargets.py`.
- Output manifest: `Saved/worker-retarget-report.json`.
- Validation report: `Saved/worker-retarget-validation.json`.

## Validation

- Runtime plugin built for Unreal Engine 5.8.4, Win64 Editor, Development and Shipping.
- Imported assets reloaded in a fresh Unreal process.
- 17 showcase workers checked, with no missing part meshes or Leader Pose mismatches.
- Helmet, safety vest, casual vest, beard and hair toggles checked.
- Animation and modular parts share the same Skeleton.
- All 17 showcase workers reload upright with zero pitch and roll.
- Validation report: `E:/Odyssey/output/ppe-demo/unreal-validation.json`.

The unused first-pass imports under `/Game/PPEWorker/Meshes` are not referenced by the final worker. Corrected production assets are in `Parts`. Automated deletion of that first-pass folder was rejected, so it was retained.

## Source and rebuild

- Runtime actor implementation: `Plugins/PPEWorkers/Source/PPEWorkers`.
- Import/material/preset/map builder: `Scripts/import_ppe_workers.py`.
- Asset validation: `Scripts/verify_ppe_workers.py`.
- Original Blender source: `E:/Odyssey/output/ppe-demo/PPE_Character_Variants.blend`.

The importer is intended for rebuilding this generated asset set. It is not a general-purpose importer for arbitrary characters.
