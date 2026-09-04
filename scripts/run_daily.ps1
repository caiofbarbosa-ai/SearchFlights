# Flight Monitor - daily execution (Variant A, Decision 12)
# Called by Task Scheduler; writes a log per day.
# NOTE: keep this file ASCII-only (PowerShell 5.1 parses no-BOM files as ANSI).

param([string]$Only = "")

$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo
$env:PYTHONUTF8 = "1"  # UTF-8 logs (cp1252 console mangles accents)

# resolve Python: user PATH first; fallback to the known install
$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) {
    $fallback = Join-Path $env:LOCALAPPDATA "Python\pythoncore-3.14-64\python.exe"
    if (Test-Path $fallback) { $py = $fallback }
}
if (-not $py) {
    "ERRO: python nao encontrado no PATH" | Add-Content "$repo\logs\erro_agendamento.log"
    exit 1
}

if (-not (Test-Path "$repo\.env")) {
    Write-Output ".env ausente - copie .env.example e preencha."
    exit 1
}

New-Item -ItemType Directory -Force -Path "$repo\logs" | Out-Null
# scheduler_*.log = wrapper; o app grava o proprio YYYY-MM-DD.log (main.py).
# Redirecionar ambos para o MESMO arquivo causava Permission denied (lock).
$log = Join-Path $repo "logs\scheduler_$(Get-Date -Format 'yyyy-MM-dd').log"

"=== inicio $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ===" | Add-Content $log
$py_args = @("-m", "src.main")
if ($Only) { $py_args += @("--only", $Only) }
& $py @py_args *>> $log
$code = $LASTEXITCODE
"=== fim (exit $code) $(Get-Date -Format 'HH:mm:ss') ===" | Add-Content $log
exit $code
