[CmdletBinding()]
param(
    [ValidateSet("Plan", "Install", "Status", "Remove")]
    [string]$Action = "Plan",
    [switch]$ConfirmRemoval
)

$ErrorActionPreference = "Stop"
$TaskName = "ResearchOS Encrypted USB Backup"
$TaskPath = "\ResearchOS\"
$RepositoryRoot = [System.IO.Path]::GetFullPath(
    (Join-Path $PSScriptRoot "..")
)
$BackupScript = Join-Path $PSScriptRoot "initialize_usb_backup.ps1"
$LauncherPath = Join-Path $PSScriptRoot "run_usb_backup.cmd"
$ExplorerPath = "C:\Windows\explorer.exe"
$LogDirectory = Join-Path $RepositoryRoot "AI-Gateway\logs"
$LogPath = Join-Path $LogDirectory "usb-backup-task.log"
$Arguments = ('"{0}"' -f $LauncherPath)

function Get-ResearchOSUsbBackupTask {
    Get-ScheduledTask -TaskName $TaskName -TaskPath $TaskPath `
        -ErrorAction SilentlyContinue
}

function Write-Receipt {
    param([hashtable]$Receipt)
    $Receipt | ConvertTo-Json -Compress
}

if ($Action -eq "Plan") {
    Write-Receipt @{
        action = "plan"
        task_name = $TaskName
        task_path = $TaskPath
        schedule = "Sunday 18:00 local time"
        executable = $ExplorerPath
        launcher = $LauncherPath
        backup_script = $BackupScript
        password_storage = "none; interactive prompt"
        retention = @{
            keep_last = 8
            keep_weekly = 12
            keep_monthly = 12
        }
        changes_applied = $false
    }
    exit 0
}

if ($Action -eq "Status") {
    $existing = Get-ResearchOSUsbBackupTask
    if (-not $existing) {
        Write-Receipt @{
            action = "status"
            installed = $false
            task_name = $TaskName
            task_path = $TaskPath
        }
        exit 0
    }
    $info = Get-ScheduledTaskInfo -TaskName $TaskName -TaskPath $TaskPath
    Write-Receipt @{
        action = "status"
        installed = $true
        enabled = $existing.State -ne "Disabled"
        state = [string]$existing.State
        last_result = $info.LastTaskResult
        last_run_time = $info.LastRunTime.ToUniversalTime().ToString("o")
        next_run_time = $info.NextRunTime.ToUniversalTime().ToString("o")
        task_name = $TaskName
        task_path = $TaskPath
    }
    exit 0
}

if ($Action -eq "Install") {
    if (-not (Test-Path -LiteralPath $BackupScript -PathType Leaf)) {
        throw "Canonical USB backup script is missing"
    }
    if (-not (Test-Path -LiteralPath $LauncherPath -PathType Leaf)) {
        throw "Visible USB backup launcher is missing"
    }
    if (Get-ResearchOSUsbBackupTask) {
        throw "USB backup task already exists; inspect or remove it first"
    }
    New-Item -ItemType Directory -Force -Path $LogDirectory | Out-Null
    $scheduledAction = New-ScheduledTaskAction `
        -Execute $ExplorerPath `
        -Argument $Arguments `
        -WorkingDirectory $RepositoryRoot
$now = Get-Date
$daysUntilSunday = (
    7 + [int][DayOfWeek]::Sunday - [int]$now.DayOfWeek
) % 7
if ($daysUntilSunday -eq 0) {
    $daysUntilSunday = 7
}
$firstRun = $now.Date.AddDays($daysUntilSunday).AddHours(18)
    $trigger = New-ScheduledTaskTrigger `
        -Once `
        -At $firstRun `
        -RepetitionInterval (New-TimeSpan -Days 7)
    $principal = New-ScheduledTaskPrincipal `
        -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) `
        -LogonType Interactive `
        -RunLevel Limited
    $settings = New-ScheduledTaskSettingsSet `
        -MultipleInstances IgnoreNew `
        -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
        -StartWhenAvailable
    $task = New-ScheduledTask `
        -Action $scheduledAction `
        -Trigger $trigger `
        -Principal $principal `
        -Settings $settings `
        -Description (
            "Runs the interactive, encrypted ResearchOS USB backup workflow."
        )
    Register-ScheduledTask `
        -TaskName $TaskName `
        -TaskPath $TaskPath `
        -InputObject $task | Out-Null
    Write-Receipt @{
        action = "install"
        installed = $true
        enabled = $true
        task_name = $TaskName
        task_path = $TaskPath
        schedule = "Sunday 18:00 local time"
        changes_applied = $true
    }
    exit 0
}

if (-not $ConfirmRemoval) {
    throw "Removal requires -ConfirmRemoval"
}
$existing = Get-ResearchOSUsbBackupTask
if ($existing) {
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
    encrypted_repository_preserved = $true
    changes_applied = [bool]$existing
}
