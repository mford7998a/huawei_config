@echo off
REG ADD "HKLM\SYSTEM\CurrentControlSet\Services\USBSTOR" /v "Start" /t REG_DWORD /d "4" /f
REG ADD "HKLM\SYSTEM\CurrentControlSet\Services\cdrom" /v "AutoRun" /t REG_DWORD /d "0" /f
echo USB storage and AutoRun have been disabled
pause 