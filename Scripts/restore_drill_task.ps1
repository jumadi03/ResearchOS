[CmdletBinding()]
param(
    [ValidateSet("Plan", "Install", "Status", "Remove")]
    [string]$Action = "Plan",
    [switch]$ConfirmRemoval
)

$ErrorActionPreference = "Stop"
$TaskName = "ResearchOS Canonical Restore Drill Trigger"
$TaskPath = "\ResearchOS\"
$RepositoryRoot = [System.IO.Path]::GetFullPath(
    (Join-Path $PSScriptRoot "..")
)
$ControllerPath = Join-Path `
    -Path $RepositoryRoot `
    -ChildPath "deploy\restore\run_restore_drill_controller.py"
$PythonPath = Join-Path `
    -Path $RepositoryRoot `
    -ChildPath "AI-Gateway\.venv\Scripts\python.exe"
$Owner = "windows-task-scheduler:$($env:COMPUTERNAME):$($env:USERNAME)"
$Arguments = (
    '"{0}" --owner "{1}" --lease-seconds 7200 --scheduled' -f
    $ControllerPath, $Owner
)

function Get-ResearchOSTask {
    Get-ScheduledTask -TaskName $TaskName -TaskPath $TaskPath `
        -ErrorAction SilentlyContinue
}

function Write-Receipt {
    param([hashtable]$Receipt)
    $Receipt | ConvertTo-Json -Compress
}

function Assert-LocalContract {
    if (-not (Test-Path -LiteralPath $ControllerPath -PathType Leaf)) {
        throw "Canonical restore-drill controller is missing"
    }
    if (-not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) {
        throw "ResearchOS Python environment is missing"
    }
    if (-not (Get-Command docker.exe -ErrorAction SilentlyContinue)) {
        throw "Docker Desktop command is unavailable"
    }
}

if ($Action -eq "Plan") {
    Write-Receipt @{
        action = "plan"
        task_name = $TaskName
        task_path = $TaskPath
        executable = $PythonPath
        arguments = $Arguments
        working_directory = $RepositoryRoot
        trigger_interval_minutes = 60
        initial_task_state = "disabled"
        logon_type = "interactive"
        run_level = "limited"
        database_schedule_authority = $true
        changes_applied = $false
    }
    exit 0
}

if ($Action -eq "Status") {
    $Existing = Get-ResearchOSTask
    if (-not $Existing) {
        Write-Receipt @{
            action = "status"
            installed = $false
            task_name = $TaskName
            task_path = $TaskPath
        }
        exit 0
    }
    $TaskInfo = Get-ScheduledTaskInfo -TaskName $TaskName -TaskPath $TaskPath
    Write-Receipt @{
        action = "status"
        installed = $true
        enabled = $Existing.State -ne "Disabled"
        state = [string]$Existing.State
        last_result = $TaskInfo.LastTaskResult
        last_run_time = $TaskInfo.LastRunTime.ToUniversalTime().ToString("o")
        next_run_time = $TaskInfo.NextRunTime.ToUniversalTime().ToString("o")
        task_name = $TaskName
        task_path = $TaskPath
    }
    exit 0
}

if ($Action -eq "Install") {
    Assert-LocalContract
    if (Get-ResearchOSTask) {
        throw "ResearchOS restore trigger already exists; inspect or remove it first"
    }
    $ScheduledAction = New-ScheduledTaskAction `
        -Execute $PythonPath `
        -Argument $Arguments `
        -WorkingDirectory $RepositoryRoot
    $Trigger = New-ScheduledTaskTrigger `
        -Once `
        -At ((Get-Date).AddMinutes(5)) `
        -RepetitionInterval (New-TimeSpan -Hours 1)
    $Principal = New-ScheduledTaskPrincipal `
        -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) `
        -LogonType Interactive `
        -RunLevel Limited
    $Settings = New-ScheduledTaskSettingsSet `
        -MultipleInstances IgnoreNew `
        -ExecutionTimeLimit (New-TimeSpan -Hours 3) `
        -StartWhenAvailable
    $Task = New-ScheduledTask `
        -Action $ScheduledAction `
        -Trigger $Trigger `
        -Principal $Principal `
        -Settings $Settings `
        -Description "Requests PostgreSQL due decisions for isolated ResearchOS restore drills."
    Register-ScheduledTask `
        -TaskName $TaskName `
        -TaskPath $TaskPath `
        -InputObject $Task | Out-Null
    Disable-ScheduledTask -TaskName $TaskName -TaskPath $TaskPath | Out-Null
    Write-Receipt @{
        action = "install"
        installed = $true
        enabled = $false
        task_name = $TaskName
        task_path = $TaskPath
        changes_applied = $true
    }
    exit 0
}

if (-not $ConfirmRemoval) {
    throw "Removal requires -ConfirmRemoval"
}
$Existing = Get-ResearchOSTask
if ($Existing) {
    Unregister-ScheduledTask `
        -TaskName $TaskName `
        -TaskPath $TaskPath `
        -Confirm:$false
}
Write-Receipt @{
    action = "remove"
    installed = $false
    task_name = $TaskName
    task_path = $TaskPath
    schedule_data_preserved = $true
    restore_evidence_preserved = $true
    changes_applied = [bool]$Existing
}
