# #3 task-subset specialization - matched-compute baseline.
#
# B5-2M on full stage1 (30 tasks). Per-task compute is 2M / 30 = 67k/task,
# which *matches* the hard15 / random15 specialized arms' per-task compute
# (1M / 15 = 67k/task). Same total compute as the specialized arms
# (2M), spread across the full 30-task subset.
#
# Goal: confirm whether the random15 arm's apparent +1.0 solve gain over
# B5-1M on the same subset (p = 0.007) is fully explained by the 2x
# per-task compute doubling (67k vs 33k/task). If B5-2M-on-random15
# gets ~5.6 solves (matching the random15 arm), the per-task compute
# doubling is sufficient. If B5-2M-on-random15 gets <5.6, the specialized
# arm was doing something on top of compute.
#
# 5 seeds in parallel (8-core box). Estimated ~14-20 min wall-clock.
$ErrorActionPreference = 'Stop'
Set-Location "C:\Users\aidan\repos\clebran-arc-agi"

$seeds = @(1, 2, 3, 4, 5)
$budget = 2000000

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
    $psi.Arguments = "run python -m clebran.baselines.b0 --arm B5 --seed $seed --budget $budget"
    $psi.RedirectStandardError = $true
    $psi.RedirectStandardOutput = $true
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8"
    # no CLEBRAN_SUBSET => default (stage1_subset, 30 tasks)
    $p = [System.Diagnostics.Process]::Start($psi)
    Write-Host "  launched seed=$seed pid=$($p.Id) -> b5_2m_seed${seed}.jsonl"
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

Run-Arm -ArmName "b5_2m" -Seeds $seeds -Budget $budget

Write-Host ""
Write-Host "=== B5-2M matched-compute baseline done ==="