
param([string[]]$ResourcePaths = @('E:\Construction_Demo\Content\ConstructionSite\Maps\Showcase.umap'))
$ErrorActionPreference = 'Stop'
if (-not ('WorkerSiteLockQuery' -as [type])) {
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class WorkerSiteLockQuery {
    [StructLayout(LayoutKind.Sequential)]
    public struct UniqueProcess { public int Id; public System.Runtime.InteropServices.ComTypes.FILETIME Start; }
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    public struct ProcessInfo {
        public UniqueProcess Process;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst=256)] public string AppName;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst=64)] public string ServiceName;
        public uint AppType;
        public uint AppStatus;
        public uint SessionId;
        [MarshalAs(UnmanagedType.Bool)] public bool Restartable;
    }
    [DllImport("rstrtmgr.dll", CharSet=CharSet.Unicode)]
    public static extern int RmStartSession(out uint session, int flags, string key);
    [DllImport("rstrtmgr.dll", CharSet=CharSet.Unicode)]
    public static extern int RmRegisterResources(uint session, uint files, string[] names, uint apps, UniqueProcess[] processes, uint services, string[] serviceNames);
    [DllImport("rstrtmgr.dll")]
    public static extern int RmGetList(uint session, out uint needed, ref uint count, [In,Out] ProcessInfo[] info, ref uint reasons);
    [DllImport("rstrtmgr.dll")]
    public static extern int RmEndSession(uint session);
}
'@
}
foreach ($resource in $ResourcePaths) {
    [uint32]$lockSession = 0
    $result = [WorkerSiteLockQuery]::RmStartSession([ref]$lockSession,0,[guid]::NewGuid().ToString('N'))
    if ($result -ne 0) { throw "Restart Manager start failed: $result" }
    try {
        $result = [WorkerSiteLockQuery]::RmRegisterResources($lockSession,1,@($resource),0,$null,0,$null)
        if ($result -ne 0) { throw "Register failed: $result" }
        [uint32]$needed = 0; [uint32]$count = 0; [uint32]$reasons = 0
        $result = [WorkerSiteLockQuery]::RmGetList($lockSession,[ref]$needed,[ref]$count,$null,[ref]$reasons)
        if ($result -eq 234) {
            $info = New-Object 'WorkerSiteLockQuery+ProcessInfo[]' $needed
            $count = $needed
            $result = [WorkerSiteLockQuery]::RmGetList($lockSession,[ref]$needed,[ref]$count,$info,[ref]$reasons)
            if ($result -ne 0) { throw "Query failed: $result" }
            for ($index=0; $index -lt $count; $index++) {
                [pscustomobject]@{Resource=$resource;ProcessId=$info[$index].Process.Id;Application=$info[$index].AppName;SessionId=$info[$index].SessionId}
            }
        } elseif ($result -ne 0) { throw "Query failed: $result" }
    } finally { [void][WorkerSiteLockQuery]::RmEndSession($lockSession) }
}
