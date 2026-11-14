@echo off
cd /d "%~dp0"
python install.py --unreg > "%TEMP%\psxpixel_unmenu.reg"
reg import "%TEMP%\psxpixel_unmenu.reg"
del "%TEMP%\psxpixel_unmenu.reg" >nul 2>nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%CD%\shortcut.ps1" -Remove
echo Da go PSX Pixel khoi menu chuot phai, Start Menu va Desktop.
echo Co the xoa thu muc nay de go hoan toan: %CD%
pause
