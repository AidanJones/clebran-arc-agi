# 4M B5D pilot — run remaining seeds (8-15) in series.
# Skip seed 7 (the bash wrapper timed out before it finished).
# Estimated: 8 seeds × 25-30 min = 3.5-4 hours.
$ErrorActionPreference = 'Stop'
Set-Location "C:\Users\aidan\repos\clebran-arc-agi"

$seeds = @(8, 9, 10, 11, 12, 13, 14, 15)
$budget = 4000000
$results = @()

foreach ($seed in $seeds) {
  $now = Get-Date -Format "HH:mm:ss"
  Write-Host "[$now] === B5D seed=$seed budget=$budget ==="
  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName = "uv"
  $psi.Arguments = "run python -m clebran.baselines.b0 --arm B5D --seed $seed --budget $budget"
  $psi.RedirectStandardError = $true
  $psi.RedirectStandardOutput = $true
  $psi.UseShellExecute = $false
  $psi.CreateNoWindow = $true
  $psi.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8"
  $p = [System.Diagnostics.Process]::Start($psi)
  $p.WaitForExit()
  $out = $p.StandardOutput.ReadToEnd()
  $err = $p.StandardError.ReadToEnd()
  [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
  Write-Host $out
  if ($err) { Write-Host "STDERR: $err" }
  $results += $out
}

Write-Host ""
Write-Host "=== remaining 4M B5D pilot summary ==="
foreach ($r in $results) { Write-Host $r }
