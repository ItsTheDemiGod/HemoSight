# Launch the selection-aware permutation run as a DETACHED OS process.
#
# Start-Process gives the run its own process, not a child job of whatever shell
# started it, so it survives this terminal, this Claude Code session being compacted or
# cleared, and the window being closed. It does NOT survive a reboot or a logout - if
# either happens, re-run this script and the JSONL checkpoint resumes where it stopped.
#
#   powershell -ExecutionPolicy Bypass -File scripts\launch_perm_extended.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\launch_perm_extended.ps1 -Target 480
#
# Progress:  .\.venv\Scripts\python.exe scripts\permutation_run_status_phase5.py

param(
    [int]$Target = 240,
    [int]$TrainBatch = 128
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$py   = Join-Path $root ".venv\Scripts\python.exe"
$out  = Join-Path $root "data\interim\phase5"
$log  = Join-Path $out "perm_extended.log"
$err  = Join-Path $out "perm_extended.err"
$pidf = Join-Path $out "perm_extended.pid"

New-Item -ItemType Directory -Force -Path $out | Out-Null

# Refuse to start a second copy: two processes appending to one JSONL would duplicate
# permutation indices and waste a GPU-day.
if (Test-Path $pidf) {
    $old = Get-Content $pidf -ErrorAction SilentlyContinue
    if ($old) {
        $running = Get-Process -Id $old -ErrorAction SilentlyContinue
        if ($running -and $running.ProcessName -eq "python") {
            Write-Host "ALREADY RUNNING as PID $old - not launching a second copy."
            Write-Host "Stop it with:  Stop-Process -Id $old"
            exit 1
        }
    }
}

# Start-Process truncates its redirect targets, so keep the previous attempt's log.
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
foreach ($f in @($log, $err)) {
    if (Test-Path $f) { Move-Item $f "$f.$stamp" -Force }
}

$p = Start-Process -FilePath $py `
    -ArgumentList "-u", "scripts\permutation_extended_run_phase5.py", "--target", "$Target", "--train-batch", "$TrainBatch" `
    -WorkingDirectory $root `
    -RedirectStandardOutput $log `
    -RedirectStandardError $err `
    -WindowStyle Hidden `
    -PassThru

$p.Id | Out-File -FilePath $pidf -Encoding ascii
Write-Host "launched PID $($p.Id), target $Target permutations"
Write-Host "stdout : $log"
Write-Host "stderr : $err"
Write-Host "pid    : $pidf"
