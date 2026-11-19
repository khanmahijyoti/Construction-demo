
$ErrorActionPreference = 'Stop'
$activityProject = 'E:/Construction_Demo'
$activityEngine = 'E:/UE_5.8'
$activityLogs = "$activityProject/Saved/WorkerActivityUAT"
New-Item -ItemType Directory -Path $activityLogs -Force | Out-Null
Set-Item -Path Env:uebp_LogFolder -Value $activityLogs
Set-Item -Path Env:uebp_FinalLogFolder -Value $activityLogs
& "$activityEngine/Engine/Build/BatchFiles/RunUAT.bat" -NoCompile -NoP4 BuildCookRun `
    "-project=$activityProject/Construction_Demo.uproject" -platform=Win64 -clientconfig=Development `
    -skipbuild -nocompile -nocompileeditor -skipcook -stage -pak -iostore -archive -utf8output `
    "-cookoutputdir=$activityProject/Saved/CookedWorkerActivity" `
    "-stagingdirectory=$activityProject/Saved/StagedWorkerActivity" `
    "-archivedirectory=$activityProject/Packaged/WorkerActivity"
exit $LASTEXITCODE
