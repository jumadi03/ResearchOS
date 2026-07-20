@echo off
setlocal
C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\ResearchOS\scripts\monitor_hostinger_backup.ps1 -SuppressInteractiveNotification
exit /b %ERRORLEVEL%
