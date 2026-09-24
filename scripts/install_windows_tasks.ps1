$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskEnvironmentPython = Join-Path $taskRoot 'data/service-venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $taskEnvironmentPython)) { throw 'Install data/service-venv first.' }
$taskBasePython = & $taskEnvironmentPython -c 'import sys; print(sys._base_executable)'
if ($LASTEXITCODE -ne 0) { throw 'Cannot resolve Python runtime.' }
$taskPython = Join-Path (Split-Path -Parent $taskBasePython) 'pythonw.exe'
if (-not (Test-Path -LiteralPath $taskPython)) { throw 'Windowless Python runtime unavailable.' }
$taskRunner = Join-Path $PSScriptRoot 'windows_entry.py'
$taskUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$taskPrincipal = New-ScheduledTaskPrincipal -UserId $taskUser -LogonType Interactive -RunLevel Limited
$taskSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew
foreach ($taskMode in @('watch','dashboard','backup','telegram')) {
    $taskName = 'Immortal-Trading-' + $taskMode
    $taskExisting = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if ($taskExisting) { throw "Task already exists: $taskName. Review before updating." }
    $taskArguments = '"' + $taskRunner + '" ' + $taskMode
    $taskAction = New-ScheduledTaskAction -Execute $taskPython -Argument $taskArguments -WorkingDirectory $taskRoot
    if ($taskMode -eq 'backup') {
        $taskTrigger = New-ScheduledTaskTrigger -Daily -At '03:15'
    } else {
        $taskTrigger = New-ScheduledTaskTrigger -AtLogOn -User $taskUser
    }
    Register-ScheduledTask -TaskName $taskName -Action $taskAction -Trigger $taskTrigger -Settings $taskSettings -Principal $taskPrincipal -Description "Immortal-Trading $taskMode; workspace: $taskRoot" | Out-Null
    Write-Output "Registered $taskName"
}
