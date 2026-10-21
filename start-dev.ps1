<# Start native REST + gRPC; never stop or start shared Docker containers. #>
param([switch]$NoBrowser, [switch]$DryRun)
$ErrorActionPreference = 'Stop'
$taskPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) {
    throw 'Missing .venv Python; prepare dependencies before starting this launcher.'
}
$taskArgs = @('-m', 'app.script.run_dev')
if (-not $NoBrowser) { $taskArgs += '--open-browser' }
if ($DryRun) { $taskArgs += '--dry-run' }
Push-Location $PSScriptRoot
try {
    & $taskPython @taskArgs
    if ($LASTEXITCODE -ne 0) { throw "AI dev launcher exited with code $LASTEXITCODE" }
} finally { Pop-Location }
