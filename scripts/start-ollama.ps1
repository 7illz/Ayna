param([switch]$Restart)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$runtimeRoot = Join-Path $projectRoot '.data'
$knownPath = Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe'
$ollamaCommand = Get-Command ollama.exe -ErrorAction SilentlyContinue
$ollamaExe = if ($ollamaCommand) { $ollamaCommand.Source } elseif (Test-Path -LiteralPath $knownPath) { $knownPath } else { $null }
if (-not $ollamaExe) { throw 'Ollama is missing. Install the official Ollama.Ollama Winget package first.' }
$ollamaExe = (Resolve-Path -LiteralPath $ollamaExe).Path

$requiredModels = @('qwen3:0.6b', 'qwen3-embedding:0.6b')
$officialRoot = (Split-Path -Parent $ollamaExe)
$ownedProcesses = @(Get-Process -Name 'ollama', 'ollama app' -ErrorAction SilentlyContinue | Where-Object {
    $_.Path -and $_.Path.StartsWith($officialRoot, [System.StringComparison]::OrdinalIgnoreCase)
})

$serverReady = $false
try {
    $version = Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/version' -TimeoutSec 2
    $serverReady = [bool]$version.version
} catch { }

# A server not launched by this script has unknown accelerator policy. Restart only verified
# official Ollama processes, never an unrelated process that happens to share a name.
$recordPath = Join-Path $runtimeRoot 'ollama-process.json'
if ($Restart -or $serverReady -or -not (Test-Path -LiteralPath $recordPath)) {
    foreach ($process in $ownedProcesses) { Stop-Process -Id $process.Id -Force }
    Start-Sleep -Milliseconds 700
    $env:OLLAMA_HOST = '127.0.0.1:11434'
    $env:CUDA_VISIBLE_DEVICES = '-1'
    $env:OLLAMA_LLM_LIBRARY = 'cpu_avx2'
    $env:OLLAMA_NUM_PARALLEL = '1'
    $env:OLLAMA_MAX_LOADED_MODELS = '1'
    $env:OLLAMA_MAX_QUEUE = '16'
    $env:OLLAMA_CONTEXT_LENGTH = '4096'
    $env:OLLAMA_KEEP_ALIVE = '0'
    $env:OLLAMA_NO_CLOUD = 'true'
    New-Item -ItemType Directory -Force -Path $runtimeRoot | Out-Null
    $server = Start-Process -FilePath $ollamaExe -ArgumentList 'serve' -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtimeRoot 'ollama.out.log') -RedirectStandardError (Join-Path $runtimeRoot 'ollama.err.log')
    @{ id = $server.Id; executable = $ollamaExe; cpu_only = $true } | ConvertTo-Json | Set-Content -LiteralPath $recordPath -Encoding UTF8
}

for ($attempt = 0; $attempt -lt 20; $attempt++) {
    try {
        $version = Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/version' -TimeoutSec 2
        if ($version.version) { break }
    } catch {
        if ($attempt -eq 19) { throw 'Ollama did not become ready. Check .data/ollama.err.log.' }
        Start-Sleep -Milliseconds 500
    }
}
$installed = @(& $ollamaExe list | Select-Object -Skip 1 | ForEach-Object { ($_ -split '\s+')[0] })
$missing = @($requiredModels | Where-Object { $_ -notin $installed })
if ($missing.Count) { throw "Missing Ollama models: $($missing -join ', '). Run ollama pull for each model once." }

$body = @{ model = 'qwen3:0.6b'; prompt = 'Reply OK'; stream = $false; think = $false; keep_alive = '30s'; options = @{ num_predict = 4; num_ctx = 4096 } } | ConvertTo-Json -Depth 4
$null = Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:11434/api/generate' -ContentType 'application/json' -Body $body -TimeoutSec 60
$placement = (& $ollamaExe ps | Out-String)
if ($placement -notmatch '100% CPU') { throw "Ollama CPU-only verification failed. Current placement:`n$placement" }
$unload = @{ model = 'qwen3:0.6b'; keep_alive = 0 } | ConvertTo-Json
$null = Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:11434/api/generate' -ContentType 'application/json' -Body $unload -TimeoutSec 30
Write-Output "Ollama $($version.version): localhost only, 100% CPU"
Write-Output "Models: $($requiredModels -join ', ')"
