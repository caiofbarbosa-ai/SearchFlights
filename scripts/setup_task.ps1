# Flight Monitor - scheduled tasks registration (Variant A, Decision 12)
# Run ONCE:
#   powershell -ExecutionPolicy Bypass -File scripts\setup_task.ps1
#
# Task 1 "FlightMonitor Daily" - 10:00 BRT, full run (all sources + Telegram)
# Task 2 "FlightMonitor RSS"   - 14/18/22/02/06h, RSS-only scans (fast feeds
#                                roll their 10-post window in ~7h; without
#                                these scans articles are lost between cycles)
# Power plan requirement: "Allow wake timers" = Enabled (default on AC).
# NOTE: keep this file ASCII-only (PowerShell 5.1 parses no-BOM files as ANSI).

$repo = Split-Path -Parent $PSScriptRoot
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive

# --- Task 1: full daily run -----------------------------------------------
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$repo\scripts\run_daily.ps1`"" `
    -WorkingDirectory $repo
$trigger = New-ScheduledTaskTrigger -Daily -At 10:00
$settings = New-ScheduledTaskSettingsSet `
    -WakeToRun `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 60) `
    -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName "FlightMonitor Daily" `
    -Action $action -Trigger $trigger -Settings $settings `
    -Principal $principal -Force

# --- Task 2: RSS-only intermediate scans ----------------------------------
$rssAction = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$repo\scripts\run_daily.ps1`" -Only rss" `
    -WorkingDirectory $repo
$rssTriggers = @(
    (New-ScheduledTaskTrigger -Daily -At 14:00),
    (New-ScheduledTaskTrigger -Daily -At 18:00),
    (New-ScheduledTaskTrigger -Daily -At 22:00),
    (New-ScheduledTaskTrigger -Daily -At 02:00),
    (New-ScheduledTaskTrigger -Daily -At 06:00)
)
$rssSettings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 15) `
    -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName "FlightMonitor RSS" `
    -Action $rssAction -Trigger $rssTriggers -Settings $rssSettings `
    -Principal $principal -Force

Write-Output ""
Write-Output "Task 'FlightMonitor Daily' registered: daily at 10:00 (local/BRT), wakes from sleep."
Write-Output "Task 'FlightMonitor RSS' registered: RSS scans at 14/18/22/02/06h."
Write-Output "Manual test:   Start-ScheduledTask -TaskName 'FlightMonitor Daily'"
Write-Output "Reminder: power plan needs 'Allow wake timers' = Enabled (default on AC)."
