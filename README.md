# Construction Demo — Unreal project source

Unreal Engine 5.8 project for a synthetic construction-site PPE monitoring demo.

## Initial source snapshot

- `Construction_Demo.uproject` and project configuration.
- `Plugins/PPEWorkers`: modular worker appearance/animation and CCTV camera subsystem.
- `Scripts`: project authoring, validation, packaging and integration scripts.
- Small custom camera/worker Blueprints and appearance presets under `Content`.
- `PPE_WORKERS.md`: worker and project workflow notes.

## Assets and local setup

The construction environment, maps, worker meshes, textures, animation clips,
generated files and packaged builds are excluded. Blueprints/configuration reference
these local assets, so this source snapshot alone is not a runnable complete scene.

Restore assets that you are licensed to use at their original project paths before
opening the scene, running authoring scripts or packaging. In particular, the
construction map is expected at `/Game/ConstructionSite/Maps/Showcase` and worker
dependencies under `/Game/PPEWorker`. Third-party asset redistribution rights are
not granted by this repository.

Open `Construction_Demo.uproject` with Unreal Engine 5.8. Building the custom C++
plugin requires a compatible Visual Studio C++ toolchain and Windows SDK. Some
authoring scripts contain local project, engine or source-asset paths that must be
adjusted for a different workstation.

The AI service and browser/signalling implementation are outside this initial
Unreal-only snapshot. Integration launch scripts require those local services.

Caches, virtual environments, logs, session recordings and packaged data remain
local. Small Blueprint assets are stored as binary files; larger redistributable
assets should use an appropriate asset delivery or Git LFS workflow if added later.
