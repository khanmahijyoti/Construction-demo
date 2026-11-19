









param(
    [string]$Map = '/Game/ConstructionSite/Maps/Showcase',
    [int]$Res = 1280,
    [int]$Fps = 30,
    [switch]$ShowWindow,
    [switch]$Editor,
    [switch]$RestartGame,
    [ValidateSet('ensemble', 'v8s', 'y11n')]
    [string]$DetectorMode = 'ensemble'
)
$ErrorActionPreference = 'Stop'
$Project = 'E:\Construction_Demo'
$Engine  = 'E:\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe'
$PackagedExe = "$Project\Packaged\Windows\Construction_Demo.exe"
$ActivityPackagedExe = "$Project\Packaged\WorkerActivity\Windows\Construction_Demo.exe"
if ((Test-Path $ActivityPackagedExe) -and (Test-Path "$Project\Packaged\WorkerActivity\worker-activity-ready.json")) {
    $PackagedExe = $ActivityPackagedExe
}
$Wilbur  = "$Project\PixelStreaming\SignallingWebServer"
$Logs    = "$Project\Saved\LiveStream"
New-Item -ItemType Directory -Force $Logs | Out-Null

function Test-Port([int]$Port) {
    [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}
function Wait-Port([int]$Port, [int]$Seconds, [string]$Name) {
    $deadline = (Get-Date).AddSeconds($Seconds)
    while (-not (Test-Port $Port)) {
        if ((Get-Date) -gt $deadline) { throw "$Name did not open port $Port within $Seconds s (see $Logs)" }
        Start-Sleep -Milliseconds 500
    }
}
$pids = @{}


if (Test-Port 8888) { Write-Host 'Signalling server already running.' }
else {
    $p = Start-Process node -WorkingDirectory $Wilbur -WindowStyle Hidden -PassThru `
        -ArgumentList 'dist/index.js', '--serve', '--http_root', "`"$Wilbur\www`"", '--homepage', 'home.html',
                      '--player_port', '8088', '--streamer_port', '8888', '--console_messages', 'basic' `
        -RedirectStandardOutput "$Logs\signalling.log" -RedirectStandardError "$Logs\signalling-errors.log"
    $pids.signalling = $p.Id
    Wait-Port 8888 20 'Signalling server'
    Write-Host "Signalling server started (pid $($p.Id))."
}


if (Test-Port 8766) { Write-Host 'Detector already running.' }
else {
    $py = "$Project\AI\.venv-gpu\Scripts\python.exe"
    if (-not (Test-Path $py)) { $py = "$Project\AI\.venv\Scripts\python.exe" }
    $p = Start-Process $py -WorkingDirectory "$Project\AI" -WindowStyle Hidden -PassThru `
        -ArgumentList "$Project\AI\live_detector.py", '--mode', $DetectorMode `
        -RedirectStandardOutput "$Logs\detector.log" -RedirectStandardError "$Logs\detector-errors.log"
    $pids.detector = $p.Id
    Wait-Port 8766 120 'Detector'
    Write-Host "Detector started (pid $($p.Id)): $(Get-Content "$Logs\detector.log" -Raw)".Trim()
}


$running = Get-CimInstance Win32_Process |
    Where-Object { $_.Name -match '^(UnrealEditor|Construction_Demo.*)\.exe$' -and
                   $_.CommandLine -match 'PixelStreamingConnectionURL' }
if ($RestartGame -and $running) {
    foreach ($game in $running) {
        Stop-Process -Id $game.ProcessId -Force -ErrorAction SilentlyContinue
    }
    $running = $null
}
if ($running) { Write-Host "Unreal stream already running (pid $($running.ProcessId -join ', '))." }
else {
    $common = @($Map, '-Windowed', "-ResX=$Res", "-ResY=$Res", '-ForceRes',
        '-PixelStreamingConnectionURL=ws://127.0.0.1:8888',
        "-PixelStreamingWebRTCFps=$Fps",
        '-PixelStreamingEncoderCodec=H264',
        "-abslog=`"$Logs\unreal.log`"", '-NoSound', '-nosplash', '-Unattended')
    if (-not $ShowWindow) { $common += '-RenderOffScreen' }
    $maxFps = [Math]::Max($Fps, 30)
    if ((Test-Path $PackagedExe) -and -not $Editor) {

        $exe = $PackagedExe
        $ueArgs = $common + @('-PPECCTV', "-ExecCmds=`"t.MaxFPS $maxFps`"")
        $mode = 'packaged build'
    } else {

        $exe = $Engine
        $ueArgs = @("`"$Project\Construction_Demo.uproject`"", '-game') + $common +
            @("-ExecCmds=`"t.MaxFPS $maxFps, py E:/Construction_Demo/Scripts/pixelstream_cctv.py`"")
        $mode = 'editor -game'
    }
    $p = Start-Process $exe -ArgumentList $ueArgs -PassThru
    $pids.unreal = $p.Id
    Write-Host "Unreal started from $mode (pid $($p.Id)). Loading can take a minute; log: $Logs\unreal.log"
}

$pids | ConvertTo-Json | Set-Content -Encoding utf8 "$Logs\pids.json"
Start-Process 'http://127.0.0.1:8088/home.html'
