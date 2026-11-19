
$Logs = 'E:\Construction_Demo\Saved\LiveStream'
Get-CimInstance Win32_Process |
    Where-Object { $_.Name -match '^(UnrealEditor|Construction_Demo.*)\.exe$' -and
                   $_.CommandLine -match 'PixelStreamingConnectionURL' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force; "Stopped Unreal stream ($($_.ProcessId))" }
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -match 'live_detector\.py' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force; "Stopped detector ($($_.ProcessId))" }
Get-CimInstance Win32_Process -Filter "Name='node.exe'" |
    Where-Object { $_.CommandLine -match 'dist/index\.js' -and $_.CommandLine -match '8888' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force; "Stopped signalling server ($($_.ProcessId))" }
Remove-Item "$Logs\pids.json" -ErrorAction SilentlyContinue
