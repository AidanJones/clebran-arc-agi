# #4 Novelty search arm 1M pilot — discovery-bottleneck menu
#
# B5N = B5 with novelty-score primary (instead of accuracy-score).
# Tests whether searching the program space by behavioral diversity
# finds anything test-exact that B5 doesn't.
#
# 5 seeds in parallel (8-core box). Estimated ~7-10 min wall-clock.
$ErrorActionPreference = 'Stop'
Set-Location "C:\Users\aidan\repos\clebran-arc-agi"

$seeds = @(1, 2, 3, 4, 5)
$budget = 1000000

function Run-Arm {
  param([string]$ArmName, [int[]]$Seeds, [int]$Budget)
  $jobs = @()
  $now = Get-Date -Format "HH:mm:ss"
  Write-Host "[$now] === $ArmName -- launching $($Seeds.Count) seeds at $Budget evals ==="

  foreach ($seed in $Seeds) {
    $logOut = "logs\${ArmName}_run_seed${seed}.out"
    $logErr = "logs\${ArmName}_run_seed${seed}.err"
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = "uv"
    $psi.Arguments = "run python -m clebran.baselines.b0 --arm B5N --seed $seed --budget $budget"
    $psi.RedirectStandardError = $true
    $psi.RedirectStandardOutput = $true
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8"
    $p = [System.Diagnostics.Process]::Start($psi)
    Write-Host "  launched seed=$seed pid=$($p.Id) -> b5n_1m_seed${seed}.jsonl"
    $jobs += @{ pid = $p.Id; seed = $seed; proc = $p; out = $logOut; err = $logErr }
  }

  foreach ($j in $jobs) {
    $j.proc.WaitForExit()
    $out = $j.proc.StandardOutput.ReadToEnd()
    $err = $j.proc.StandardError.ReadToEnd()
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $now = Get-Date -Format "HH:mm:ss"
    Write-Host "[$now] seed=$($j.seed) pid=$($j.pid) exit=$($j.proc.ExitCode)"
    if ($out) {
      $out | Out-File -FilePath $j.out -Encoding utf8
      Write-Host "  stdout: $($out.Length) bytes -> $($j.out)"
    }
    if ($err) {
      $err | Out-File -FilePath $j.err -Encoding utf8
      Write-Host "  stderr: $($err.Length) bytes -> $($j.err)"
    }
  }
}

Run-Arm -ArmName "b5n_1m" -Seeds $seeds -Budget $budget

Write-Host ""
Write-Host "=== B5N novelty-search 1M pilot done ==="