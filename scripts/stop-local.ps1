$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$statePath = Join-Path $projectRoot '.data\local-processes.json'
if (-not (Test-Path -LiteralPath $statePath)) { Write-Output 'No native Ayna process record found.'; return }
$state = Get-Content -Raw -LiteralPath $statePath | ConvertFrom-Json
if ($state.workspace -ne $projectRoot) { throw 'The process record belongs to another workspace.' }
foreach ($record in $state.processes) {
    $ownedProcess = Get-Process -Id $record.id -ErrorAction SilentlyContinue
    if (-not $ownedProcess) { continue }
    if ($ownedProcess.StartTime.ToUniversalTime().ToString('o') -ne $record.started) { throw 'A recorded PID has been reused. Refusing to stop an unrelated process.' }
    $command = (Get-CimInstance Win32_Process -Filter "ProcessId = $($record.id)").CommandLine
    if (-not $command -or $command.IndexOf($projectRoot, [System.StringComparison]::OrdinalIgnoreCase) -lt 0) { throw 'A recorded process is outside this Ayna workspace.' }
    & taskkill.exe /PID $record.id /T /F
    if ($LASTEXITCODE -ne 0) { throw "Could not stop owned Ayna process $($record.id)" }
}
Remove-Item -LiteralPath $statePath
Write-Output 'Stopped the native Ayna servers. Database and assets retained.'
