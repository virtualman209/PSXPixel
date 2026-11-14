"""Tự cập nhật PSX Pixel từ GitHub.

So sánh version.txt trên GitHub với bản trên máy. Nếu có bản mới thì tải zip
của nhánh main về và chép đè vào thư mục tool (giữ nguyên style, cấu hình và token).
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile

REPO = "virtualman209/PSXPixel"   # đổi nếu bạn đặt tên repo khác
BRANCH = "main"
APP_DIR = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(APP_DIR, "update_state.json")
TOKEN_FILE = os.path.join(APP_DIR, "github_token.txt")   # token đọc repo private, không đưa lên GitHub
KEEP = {"styles.json", "update_state.json", "settings.json", "update_error.txt", "github_token.txt", "bin", ".git"}
CHECK_EVERY = 6 * 3600          # tự kiểm tra tối đa 6 tiếng / lần
RAW = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/version.txt"
ZIP = f"https://codeload.github.com/{REPO}/zip/refs/heads/{BRANCH}"
# Repo private: đi qua GitHub API kèm token
API_RAW = f"https://api.github.com/repos/{REPO}/contents/version.txt?ref={BRANCH}"
API_ZIP = f"https://api.github.com/repos/{REPO}/zipball/{BRANCH}"


def _token():
    tok = os.environ.get("PSXPIXEL_TOKEN", "").strip()
    if not tok:
        try:
            with open(TOKEN_FILE, encoding="utf-8-sig") as f:
                tok = f.read().strip()
        except OSError:
            pass
    return tok


def _vtuple(v):
    return tuple(int(x) if x.isdigit() else 0 for x in v.strip().lstrip("v").split("."))


def _read_version_file(text):
    lines = text.strip().splitlines() or ["0"]
    return lines[0].strip(), "\n".join(lines[1:]).strip()


def local_version():
    try:
        with open(os.path.join(APP_DIR, "version.txt"), encoding="utf-8") as f:
            return _read_version_file(f.read())[0]
    except OSError:
        return "0"


def _get(kind, timeout=6):
    """kind: "version" hoặc "zip". Có token thì dùng GitHub API (repo private)."""
    tok = _token()
    headers = {"User-Agent": "PSXPixel-updater", "Cache-Control": "no-cache"}
    if tok:
        url = API_RAW if kind == "version" else API_ZIP
        headers["Authorization"] = f"Bearer {tok}"
        headers["Accept"] = "application/vnd.github.raw" if kind == "version" else "application/vnd.github+json"
    else:
        url = RAW if kind == "version" else ZIP
        url += ("&" if "?" in url else "?") + f"t={int(time.time())}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        if e.code in (401, 403, 404):
            raise RuntimeError("GitHub từ chối truy cập. Repo private cần token hợp lệ trong "
                               "github_token.txt (xem README).") from None
        raise


def _state():
    try:
        with open(STATE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_state(**kw):
    s = _state()
    s.update(kw)
    try:
        with open(STATE, "w", encoding="utf-8") as f:
            json.dump(s, f)
    except OSError:
        pass


def check(force=False):
    """Trả về (version_mới, ghi_chú) nếu có bản mới hơn, ngược lại None."""
    if os.path.isdir(os.path.join(APP_DIR, ".git")):
        return None                       # đang là thư mục dev, không tự cập nhật
    st = _state()
    if not force and time.time() - st.get("last_check", 0) < CHECK_EVERY:
        return None
    remote, notes = _read_version_file(_get("version").decode("utf-8", "replace"))
    _save_state(last_check=time.time())
    if _vtuple(remote) > _vtuple(local_version()):
        if not force and st.get("skip") == remote:
            return None
        return remote, notes
    return None


def skip(version):
    _save_state(skip=version)


def apply_update():
    """Cập nhật. Trên Windows giao cho update.bat (PowerShell) để file được ghi thật,
    không bị Python bản Microsoft Store cách ly; rồi chờ version.txt đổi."""
    if os.name == "nt" and os.path.isfile(os.path.join(APP_DIR, "update.bat")):
        before = local_version()
        err_file = os.path.join(APP_DIR, "update_error.txt")
        subprocess.Popen(["explorer.exe", os.path.join(APP_DIR, "update.bat")])
        t0 = time.time()
        while time.time() - t0 < 300:
            time.sleep(1)
            if _vtuple(local_version()) > _vtuple(before):
                time.sleep(3)          # chờ register.bat ghi menu xong
                _save_state(skip=None)
                return local_version()
            if time.time() - t0 > 5 and os.path.isfile(err_file):
                with open(err_file, encoding="utf-8-sig", errors="replace") as f:
                    raise RuntimeError(f.read().strip() or "update.ps1 lỗi")
        raise RuntimeError("Quá thời gian chờ cập nhật. Hãy chạy lại lệnh cài đặt trong PowerShell.")
    return _apply_update_python()


def _apply_update_python():
    """Tải và chép đè bản mới. Trả về version mới."""
    data = _get("zip", timeout=60)
    tmp = tempfile.mkdtemp(prefix="psxpixel_upd_")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            z.extractall(tmp)
        roots = [os.path.join(tmp, d) for d in os.listdir(tmp)]
        src = roots[0] if len(roots) == 1 and os.path.isdir(roots[0]) else tmp
        if not any(os.path.isfile(os.path.join(src, f)) for f in ("psxpixel.pyw",)):
            raise RuntimeError("Gói cập nhật không hợp lệ.")
        for name in os.listdir(src):
            if name in KEEP:
                continue
            s, d = os.path.join(src, name), os.path.join(APP_DIR, name)
            if os.path.isdir(s):
                shutil.copytree(s, d, dirs_exist_ok=True)
            else:
                shutil.copy2(s, d)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    # Cài lại menu chuột phải (phòng khi bản mới thêm/đổi menu).
    # Mở register.bat qua explorer.exe để nó chạy ngoài vùng cách ly của Python bản Store.
    if os.name == "nt":
        subprocess.Popen(["explorer.exe", os.path.join(APP_DIR, "register.bat")])
    _save_state(skip=None)
    return local_version()


def restart():
    """Mở lại tool với đúng tham số cũ."""
    subprocess.Popen([sys.executable] + sys.argv, creationflags=0x08000000 if os.name == "nt" else 0)


if __name__ == "__main__":      # python updater.py  -> cập nhật từ dòng lệnh
    r = check(force=True)
    if r:
        print(f"Có bản mới {r[0]} (đang dùng {local_version()}). Đang cập nhật…")
        print("Đã cập nhật lên", apply_update())
    else:
        print("Đang dùng bản mới nhất:", local_version())
