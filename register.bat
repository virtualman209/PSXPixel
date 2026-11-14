@echo off
rem Ghi menu chuot phai vao registry + tao loi tat Start Menu / Desktop.
rem Dung reg.exe (khong dung Python) vi Python ban Microsoft Store ghi registry vao ban sao rieng.
cd /d "%~dp0"
python install.py --reg > "%TEMP%\psxpixel_menu.reg"
reg import "%TEMP%\psxpixel_menu.reg"
if errorlevel 1 (
    echo [!] Ghi registry that bai.
    exit /b 1
)
del "%TEMP%\psxpixel_menu.reg" >nul 2>nul
for /f "usebackq delims=" %%P in (`python install.py --pythonw`) do set "PP_PYW=%%P"
powershell -NoProfile -ExecutionPolicy Bypass -File "%CD%\shortcut.ps1" -PythonW "%PP_PYW%" -AppDir "%CD%"
echo Da cai menu chuot phai + loi tat PSX Pixel (Start Menu, Desktop).
