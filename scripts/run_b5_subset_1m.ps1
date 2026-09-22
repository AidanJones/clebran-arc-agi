# #3 task-subset specialization - 2 arms x 5 seeds at 1M each.
#
#   arm A: B5-1M on data/hard15_subset.json  (15 hard tasks)
#   arm B: B5-1M on data/random15_subset.json (15 random stage1 tasks)
#
# Each arm runs 5 seeds in parallel (8-core box). Estimated ~7 min/seed
# at 1M, so ~7-10 min per arm wall-clock.
$ErrorActionPreference = 'Stop'
Set-Location "C:\Users\aidan\repos\clebran-arc-agi"

$seeds = @(1, 2, 3, 4, 5)
$budget = 1000000
$arms = @(
  @{ name = "hard15"; subset = "hard15_subset" },
  @{ name = "random15"; subset = "random15_subset" }
)

function Run-Arm {
  param([string]$ArmName, [string]$Subset, [int[]]$Seeds, [int]$Budget)
  $jobs = @()
  $now = Get-Date -Format "HH:mm:ss"
  Write-Host "[$now] === $ArmName -- launching $($Seeds.Count) seeds ==="

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
    $psi.EnvironmentVariables["CLEBRAN_SUBSET"] = $Subset
    $p = [System.Diagnostics.Process]::Start($psi)
    Write-Host "  launched seed=$seed pid=$($p.Id) -> $logOut"
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

foreach ($arm in $arms) {
  Run-Arm -ArmName $arm.name -Subset $arm.subset -Seeds $seeds -Budget $budget
}

Write-Host ""
Write-Host "=== #3 task-subset specialization done ==="
