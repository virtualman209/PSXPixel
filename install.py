"""Tạo file .reg cho menu chuột phải PSX Pixel.

Python bản Microsoft Store bị Windows cách ly: ghi registry qua winreg sẽ vào
một bản sao riêng mà Explorer không thấy. Vì vậy script này chỉ IN nội dung
.reg ra stdout, còn register.bat dùng `reg import` (chạy ngoài Python) để ghi thật.

    python install.py --check    # kiểm tra Pillow + NumPy, in thông tin
    python install.py --reg      # in file .reg (UTF-16) để cài menu
    python install.py --unreg    # in file .reg để gỡ menu
    python install.py --pythonw  # in đường dẫn pythonw.exe
"""
import os
import sys

APP = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(APP, "psxpixel.pyw")
ICON = os.path.join(APP, "psxpixel.ico")
ROOT = r"HKEY_CURRENT_USER\Software\Classes"
KEY = "PSXPixel"
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tga", ".tif", ".tiff")


def pythonw():
    p = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    return p if os.path.isfile(p) else sys.executable


def esc(s):
    return s.replace("\\", "\\\\").replace('"', '\\"')


def cmd(mode, arg="%1"):
    return f'"{pythonw()}" "{SCRIPT}" {mode}' + (f' "{arg}"' if arg else "")


def bases():
    return [f"{ROOT}\\SystemFileAssociations\\{ext}" for ext in IMAGE_EXT] + \
           [f"{ROOT}\\Directory", f"{ROOT}\\Directory\\Background"]


def menu_items(base):
    upd = ("update", "Kiểm tra cập nhật", cmd("update", None))
    if base.endswith("\\Background") or base.endswith("\\Directory"):
        arg = "%V" if base.endswith("\\Background") else "%1"
        return [("folder", "Chuyển tất cả ảnh trong thư mục sang pixel PSX…", cmd("convert-folder", arg)), upd]
    return [("convert", "Chuyển sang pixel PSX…", cmd("convert")), upd]


def reg_text(install=True):
    out = ["Windows Registry Editor Version 5.00", ""]
    icon = f'"Icon"="{esc(ICON)}"' if os.path.isfile(ICON) else None
    for base in bases():
        root = f"{base}\\shell\\{KEY}"
        out += [f"[-{root}]", ""]
        if not install:
            continue
        out += [f"[{root}]", '"MUIVerb"="PSX Pixel"', '"SubCommands"=""', '"MultiSelectModel"="Player"']
        out += [icon, ""] if icon else [""]
        for n, (verb, label, command) in enumerate(menu_items(base), 1):
            k = f"{root}\\shell\\{n:02d}{verb}"
            out += [f"[{k}]", f'"MUIVerb"="{esc(label)}"', '"MultiSelectModel"="Player"']
            out += [icon] if icon else []
            out += ["", f"[{k}\\command]", f'@="{esc(command)}"', ""]
    return "\r\n".join(out) + "\r\n"


def check():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print("  Python : " + pythonw())
    ok = True
    for mod in ("PIL", "numpy", "tkinter"):
        try:
            __import__(mod)
            print(f"  {mod:8}: có")
        except ImportError:
            print(f"  {mod:8}: THIẾU")
            ok = False
    return ok


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "--check"
    if arg == "--check":
        sys.exit(0 if check() else 1)
    elif arg == "--pythonw":
        print(pythonw())
    elif arg in ("--reg", "--unreg"):
        sys.stdout.buffer.write(reg_text(arg == "--reg").encode("utf-16"))   # có BOM
        sys.stdout.flush()
    else:
        sys.exit(__doc__)
