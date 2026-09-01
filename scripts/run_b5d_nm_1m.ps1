# B5D-NM (failure-mode dreaming) 1M pilot — 5 seeds in series.
$ErrorActionPreference = 'Stop'
Set-Location "C:\Users\aidan\repos\clebran-arc-agi"

$seeds = @(1, 2, 3, 4, 5)
$budget = 1000000
$results = @()

foreach ($seed in $seeds) {
  $now = Get-Date -Format "HH:mm:ss"
  Write-Host "[$now] === B5D-NM seed=$seed budget=$budget ==="
  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName = "uv"
  $psi.Arguments = "run python -m clebran.baselines.b0 --arm B5D-NM --seed $seed --budget $budget"
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
Write-Host "=== B5D-NM 1M pilot summary ==="
foreach ($r in $results) { Write-Host $r }
