@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Cai dat PSX Pixel

python -c "import tkinter" >nul 2>nul
if errorlevel 1 (
    echo [!] Chua co Python. Dang cai Python 3 qua winget...
    winget install -e --id Python.Python.3.12 --scope user --accept-source-agreements --accept-package-agreements
    echo.
    echo Cai Python xong. Hay DONG cua so nay va chay lai install.bat.
    pause
    exit /b
)

echo Dang cai thu vien Pillow + NumPy...
python -m pip install --user --upgrade --disable-pip-version-check -q pillow numpy
python install.py --check
if errorlevel 1 (
    echo [!] Cai thu vien that bai. Kiem tra ket noi mang roi chay lai install.bat.
    pause
    exit /b 1
)

call register.bat
echo.
echo Xong! Chuot phai vao file anh ^> PSX Pixel ^> Chuyen sang pixel PSX...
echo Hoac mo PSX Pixel tu Start Menu / Desktop roi keo tha anh vao.
echo Windows 11: chuot phai ^> Show more options (hoac Shift + chuot phai) moi thay menu.
pause
