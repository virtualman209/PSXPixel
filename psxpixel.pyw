"""PSX Pixel — chuyển tranh thành pixel art kiểu PS1 từ menu chuột phải Windows Explorer.

Cách gọi:
    pythonw psxpixel.pyw convert <ảnh1> [ảnh2 ...]   # mở cửa sổ chọn style (gom nhiều lần gọi từ Explorer)
    pythonw psxpixel.pyw convert-folder <thư mục>    # mọi ảnh trong thư mục
    pythonw psxpixel.pyw update                      # kiểm tra cập nhật
    pythonw psxpixel.pyw                             # màn hình chính (kéo thả ảnh vào)
"""
import base64
import io
import json
import os
import socket
import subprocess
import sys
import threading
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core  # noqa: E402
import updater  # noqa: E402

import tkinter as tk  # noqa: E402
from tkinter import ttk, filedialog, messagebox, simpledialog, colorchooser  # noqa: E402

from PIL import Image  # noqa: E402

APP = "PSX Pixel"
PORT = 47871
LOG = os.path.join(os.environ.get("TEMP", "/tmp"), "psxpixel.log")
PREVIEW = 460          # kích thước khung xem trước (px)


# ============================================================ gom file từ nhiều lần gọi
def gather_paths(paths):
    """Explorer gọi tool 1 lần cho MỖI file được chọn. Tiến trình đầu tiên mở cổng
    localhost, gom đường dẫn từ các tiến trình sau rồi mở 1 cửa sổ duy nhất."""
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    try:
        srv.bind(("127.0.0.1", PORT))
    except OSError:
        srv.close()
        for _ in range(40):
            try:
                with socket.create_connection(("127.0.0.1", PORT), timeout=1) as c:
                    c.sendall(json.dumps(paths).encode("utf-8"))
                return None
            except OSError:
                time.sleep(0.05)
        return paths
    srv.listen(64)
    srv.settimeout(0.1)
    got = list(paths)
    deadline = time.time() + 0.9
    while time.time() < deadline:
        try:
            conn, _ = srv.accept()
        except socket.timeout:
            continue
        with conn:
            buf = b""
            conn.settimeout(1)
            try:
                while True:
                    chunk = conn.recv(65536)
                    if not chunk:
                        break
                    buf += chunk
                got += json.loads(buf.decode("utf-8"))
            except Exception:
                pass
        deadline = time.time() + 0.5
    srv.close()
    seen, out = set(), []
    for p in got:
        k = os.path.normcase(os.path.abspath(p))
        if k not in seen:
            seen.add(k)
            out.append(p)
    return out


def expand(paths):
    out = []
    for p in paths:
        if os.path.isdir(p):
            out += core.images_in_folder(p)
        elif os.path.isfile(p) and core.is_image(p):
            out.append(p)
    return out


# ============================================================ tiện ích UI
def setup_style(root):
    style = ttk.Style(root)
    if "vista" in style.theme_names():
        style.theme_use("vista")
    style.configure("Big.TButton", padding=(16, 6))
    style.configure("Hint.TLabel", foreground="#666")
    style.configure("Head.TLabel", font=("Segoe UI", 10, "bold"))
    root.option_add("*Font", ("Segoe UI", 10))


def center(win, w, h):
    win.update_idletasks()
    x = (win.winfo_screenwidth() - w) // 2
    y = max(0, (win.winfo_screenheight() - h) // 3)
    win.geometry(f"{w}x{h}+{x}+{y}")


def to_photo(img):
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return tk.PhotoImage(data=base64.b64encode(buf.getvalue()))


def checker(w, h, cell=12):
    """Nền ô cờ để thấy rõ vùng trong suốt."""
    import numpy as np
    yy, xx = np.mgrid[0:h, 0:w]
    on = ((xx // cell + yy // cell) % 2).astype(bool)
    arr = np.empty((h, w, 3), dtype=np.uint8)
    arr[:] = (58, 60, 66)
    arr[on] = (74, 76, 84)
    return Image.fromarray(arr, "RGB")


def reveal(path):
    if os.name == "nt":
        subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])


def enable_drop(root):
    """Cho phép kéo thả file từ Explorer vào cửa sổ. Khi thả, gọi root._on_drop(list_paths)."""
    if os.name != "nt":
        return
    import ctypes
    from ctypes import wintypes
    user32, shell32 = ctypes.windll.user32, ctypes.windll.shell32
    LRESULT = ctypes.c_ssize_t
    WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
    set_long = getattr(user32, "SetWindowLongPtrW", None) or user32.SetWindowLongW
    set_long.restype = ctypes.c_void_p
    set_long.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
    user32.CallWindowProcW.restype = LRESULT
    user32.CallWindowProcW.argtypes = [ctypes.c_void_p, wintypes.HWND, wintypes.UINT, wintypes.WPARAM,
                                       wintypes.LPARAM]
    shell32.DragQueryFileW.restype = wintypes.UINT
    shell32.DragQueryFileW.argtypes = [ctypes.c_void_p, wintypes.UINT, ctypes.c_wchar_p, wintypes.UINT]
    shell32.DragFinish.argtypes = [ctypes.c_void_p]
    shell32.DragAcceptFiles.argtypes = [wintypes.HWND, wintypes.BOOL]
    WM_DROPFILES = 0x0233
    old = [None]

    def proc(hwnd, msg, wparam, lparam):
        if msg == WM_DROPFILES:
            files = []
            try:
                n = shell32.DragQueryFileW(wparam, 0xFFFFFFFF, None, 0)
                for i in range(n):
                    ln = shell32.DragQueryFileW(wparam, i, None, 0)
                    buf = ctypes.create_unicode_buffer(ln + 1)
                    shell32.DragQueryFileW(wparam, i, buf, ln + 1)
                    files.append(buf.value)
            finally:
                shell32.DragFinish(wparam)
            cb = getattr(root, "_on_drop", None)
            if cb and files:
                root.after(0, lambda: cb(files))
            return 0
        return user32.CallWindowProcW(old[0], hwnd, msg, wparam, lparam)

    root.update_idletasks()
    hwnd = int(root.wm_frame(), 16)
    root._drop_proc = WNDPROC(proc)
    old[0] = set_long(hwnd, -4, ctypes.cast(root._drop_proc, ctypes.c_void_p))
    shell32.DragAcceptFiles(hwnd, True)


# ============================================================ cửa sổ chính
class ConvertWindow:
    SLIDERS = [  # key, nhãn, min, max, bước, định dạng
        ("height", "Chiều cao pixel", 32, 360, 1, "{:.0f} px"),
        ("strength", "Cường độ dither", 0.0, 2.0, 0.05, "{:.2f}"),
        ("grain", "Hạt nhiễu", 0.0, 0.12, 0.005, "{:.3f}"),
        ("contrast", "Tương phản", 0.5, 2.0, 0.05, "{:.2f}"),
        ("saturation", "Độ bão hoà màu", 0.0, 2.0, 0.05, "{:.2f}"),
        ("tint_amount", "Độ ám màu", 0.0, 0.6, 0.01, "{:.2f}"),
        ("scale", "Phóng to khi lưu", 1, 8, 1, "x{:.0f}"),
    ]

    def __init__(self, root, paths):
        self.root = root
        self.paths = list(paths)
        self.settings = core.load_settings()
        self.styles = core.all_styles()
        self.params = dict(core.DEFAULT)
        self.src_cache = {}
        self.gen = 0
        self._busy = False
        self._pending = None
        self._loading = False
        root.title(APP)
        root.minsize(900, 620)
        center(root, 960, 660)
        root._on_drop = self.drop
        self.build()
        name = self.settings.get("last_style")
        self.apply_style(name if name in self.styles else next(iter(self.styles)))
        self.refresh_files()

    # ---------------------------------------------------------------- dựng giao diện
    def build(self):
        r = self.root
        main = ttk.Frame(r, padding=12)
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(0, weight=1)

        # --- trái: xem trước
        left = ttk.Frame(main)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)
        top = ttk.Frame(left)
        top.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        self.file_var = tk.StringVar()
        self.file_box = ttk.Combobox(top, textvariable=self.file_var, state="readonly")
        self.file_box.pack(side="left", fill="x", expand=True)
        self.file_box.bind("<<ComboboxSelected>>", lambda e: self.schedule())
        ttk.Button(top, text="Thêm ảnh…", command=self.browse).pack(side="left", padx=(6, 0))
        self.view = tk.StringVar(value="after")
        for txt, val in (("Sau", "after"), ("Trước", "before"), ("So sánh", "both")):
            ttk.Radiobutton(top, text=txt, value=val, variable=self.view,
                            command=self.redraw).pack(side="left", padx=(8, 0))
        self.canvas = tk.Canvas(left, bg="#2b2d33", highlightthickness=0, width=PREVIEW, height=PREVIEW)
        self.canvas.grid(row=1, column=0, sticky="nsew")
        self.canvas.bind("<Configure>", lambda e: self.redraw())
        self.info = ttk.Label(left, style="Hint.TLabel", text="")
        self.info.grid(row=2, column=0, sticky="w", pady=(6, 0))

        # --- phải: thông số
        right = ttk.Frame(main, width=330)
        right.grid(row=0, column=1, sticky="ns")
        right.columnconfigure(0, weight=1)
        row = 0
        ttk.Label(right, text="Style", style="Head.TLabel").grid(row=row, column=0, sticky="w"); row += 1
        self.style_var = tk.StringVar()
        self.style_box = ttk.Combobox(right, textvariable=self.style_var, state="readonly", width=36)
        self.style_box.grid(row=row, column=0, sticky="ew"); row += 1
        self.style_box.bind("<<ComboboxSelected>>", lambda e: self.apply_style(self.style_var.get()))
        sb = ttk.Frame(right)
        sb.grid(row=row, column=0, sticky="ew", pady=(4, 10)); row += 1
        ttk.Button(sb, text="Lưu thành style mới…", command=self.save_style).pack(side="left")
        self.del_btn = ttk.Button(sb, text="Xoá style", command=self.delete_style)
        self.del_btn.pack(side="left", padx=(6, 0))

        ttk.Label(right, text="Bảng màu", style="Head.TLabel").grid(row=row, column=0, sticky="w"); row += 1
        pf = ttk.Frame(right)
        pf.grid(row=row, column=0, sticky="ew"); row += 1
        self.pal_var = tk.StringVar()
        self.pal_box = ttk.Combobox(pf, textvariable=self.pal_var, state="readonly", width=26)
        self.pal_box.pack(side="left", fill="x", expand=True)
        self.pal_box.bind("<<ComboboxSelected>>", lambda e: self.on_palette())
        ttk.Button(pf, text="File .hex…", command=self.pick_hex).pack(side="left", padx=(6, 0))
        cf = ttk.Frame(right)
        cf.grid(row=row, column=0, sticky="ew", pady=(4, 0)); row += 1
        ttk.Label(cf, text="Số màu (khi tự động):").pack(side="left")
        self.colors_var = tk.IntVar(value=24)
        self.colors_spin = ttk.Spinbox(cf, from_=2, to=256, width=6, textvariable=self.colors_var,
                                       command=self.from_controls)
        self.colors_spin.pack(side="left", padx=(6, 0))
        self.colors_spin.bind("<KeyRelease>", lambda e: self.from_controls())

        ttk.Label(right, text="Dither", style="Head.TLabel").grid(row=row, column=0, sticky="w", pady=(10, 0)); row += 1
        self.dither_var = tk.StringVar()
        db = ttk.Combobox(right, textvariable=self.dither_var, state="readonly", values=list(core.DITHERS))
        db.grid(row=row, column=0, sticky="ew"); row += 1
        db.bind("<<ComboboxSelected>>", lambda e: self.from_controls())

        ttk.Label(right, text="Tinh chỉnh", style="Head.TLabel").grid(row=row, column=0, sticky="w", pady=(10, 0)); row += 1
        self.vars, self.val_labels = {}, {}
        for key, label, lo, hi, step, fmt in self.SLIDERS:
            f = ttk.Frame(right)
            f.grid(row=row, column=0, sticky="ew"); row += 1
            f.columnconfigure(1, weight=1)
            ttk.Label(f, text=label, width=16).grid(row=0, column=0, sticky="w")
            v = tk.DoubleVar()
            s = ttk.Scale(f, from_=lo, to=hi, variable=v,
                          command=lambda _=None, k=key, st=step: self.on_slider(k, st))
            s.grid(row=0, column=1, sticky="ew")
            lv = ttk.Label(f, width=7, anchor="e")
            lv.grid(row=0, column=2)
            self.vars[key], self.val_labels[key] = v, (lv, fmt)

        tf = ttk.Frame(right)
        tf.grid(row=row, column=0, sticky="ew", pady=(4, 0)); row += 1
        ttk.Label(tf, text="Ám màu:").pack(side="left")
        self.tint_swatch = tk.Label(tf, width=4, relief="groove", bg="#808080")
        self.tint_swatch.pack(side="left", padx=6)
        ttk.Button(tf, text="Chọn…", command=self.pick_tint).pack(side="left")
        ttk.Button(tf, text="Bỏ", command=self.clear_tint).pack(side="left", padx=(6, 0))

        of = ttk.Frame(right)
        of.grid(row=row, column=0, sticky="ew", pady=(12, 0)); row += 1
        self.open_var = tk.BooleanVar(value=self.settings.get("open_folder", True))
        self.close_var = tk.BooleanVar(value=self.settings.get("close_when_done", True))
        ttk.Checkbutton(of, text="Mở thư mục khi xong", variable=self.open_var).pack(anchor="w")
        ttk.Checkbutton(of, text="Tự đóng cửa sổ khi xong", variable=self.close_var).pack(anchor="w")
        ttk.Label(right, style="Hint.TLabel", wraplength=320,
                  text="Ảnh mới được lưu cạnh ảnh gốc, tên có đuôi _psx.png. Ảnh gốc không bị thay đổi."
                  ).grid(row=row, column=0, sticky="w", pady=(8, 0)); row += 1

        # --- dưới: tiến trình + nút
        bot = ttk.Frame(main)
        bot.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        bot.columnconfigure(0, weight=1)
        self.prog = ttk.Progressbar(bot, mode="determinate")
        self.prog.grid(row=0, column=0, sticky="ew", padx=(0, 12))
        self.status = ttk.Label(bot, style="Hint.TLabel", text="")
        self.status.grid(row=1, column=0, sticky="w")
        self.ok_btn = ttk.Button(bot, text="OK – Chuyển ảnh", style="Big.TButton", command=self.run)
        self.ok_btn.grid(row=0, column=1, rowspan=2)
        ttk.Button(bot, text="Huỷ", style="Big.TButton", command=self.close).grid(row=0, column=2, rowspan=2, padx=(6, 0))
        self.root.bind("<Return>", lambda e: self.run())
        self.root.bind("<Escape>", lambda e: self.close())
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    # ---------------------------------------------------------------- style & thông số
    def refresh_style_list(self, select=None):
        self.styles = core.all_styles()
        self.style_box["values"] = list(self.styles)
        if select:
            self.style_var.set(select)
        self.del_btn.state(["!disabled"] if self.style_var.get() in core.user_style_names() else ["disabled"])

    def apply_style(self, name):
        self.params = dict(core.DEFAULT, **self.styles.get(name, {}))
        self.refresh_style_list(select=name)
        self.to_controls()
        self.schedule()

    def palette_names(self):
        names = list(core.PALETTES) + [core.AUTO]
        if self.params["palette"] not in names:
            names.append(self.params["palette"])          # file .hex
        return names

    def to_controls(self):
        self._loading = True
        p = self.params
        self.pal_box["values"] = self.palette_names()
        self.pal_var.set(p["palette"])
        self.colors_var.set(int(p["colors"]))
        self.dither_var.set(next(k for k, v in core.DITHERS.items() if v == p["dither"]))
        for key, *_ in self.SLIDERS:
            self.vars[key].set(float(p[key]))
            self.show_value(key)
        self.tint_swatch.configure(bg="#" + p["tint"] if p["tint"] else "#808080",
                                   text="" if p["tint"] else "–")
        self.colors_spin.state(["!disabled"] if p["palette"] == core.AUTO else ["disabled"])
        self._loading = False

    def show_value(self, key):
        lv, fmt = self.val_labels[key]
        lv.configure(text=fmt.format(self.vars[key].get()))

    def on_slider(self, key, step):
        v = round(self.vars[key].get() / step) * step
        if step >= 1:
            v = int(v)
        self.params[key] = v
        self.show_value(key)
        if not self._loading:
            self.schedule()

    def from_controls(self):
        if self._loading:
            return
        self.params["palette"] = self.pal_var.get()
        try:
            self.params["colors"] = max(2, min(256, int(self.colors_var.get())))
        except (tk.TclError, ValueError):
            return
        self.params["dither"] = core.DITHERS.get(self.dither_var.get(), "bayer")
        self.schedule()

    def on_palette(self):
        self.colors_spin.state(["!disabled"] if self.pal_var.get() == core.AUTO else ["disabled"])
        self.from_controls()

    def pick_hex(self):
        p = filedialog.askopenfilename(parent=self.root, title="Chọn bảng màu (.hex từ Lospec)",
                                       filetypes=[("Bảng màu", "*.hex *.txt"), ("Tất cả", "*.*")])
        if p:
            self.params["palette"] = p
            self.to_controls()
            self.schedule()

    def pick_tint(self):
        c = colorchooser.askcolor(parent=self.root, title="Chọn màu ám",
                                  initialcolor="#" + self.params["tint"] if self.params["tint"] else None)
        if c and c[1]:
            self.params["tint"] = c[1].lstrip("#")
            if self.params["tint_amount"] <= 0:
                self.params["tint_amount"] = 0.15
            self.to_controls()
            self.schedule()

    def clear_tint(self):
        self.params["tint"] = ""
        self.to_controls()
        self.schedule()

    def save_style(self):
        name = simpledialog.askstring(APP, "Tên style mới:", parent=self.root)
        if not name:
            return
        name = name.strip()
        if name in core.BUILTIN_STYLES:
            messagebox.showwarning(APP, "Tên này trùng style có sẵn. Hãy chọn tên khác.", parent=self.root)
            return
        core.save_style(name, self.params)
        self.refresh_style_list(select=name)

    def delete_style(self):
        name = self.style_var.get()
        if name in core.user_style_names() and messagebox.askyesno(APP, f"Xoá style “{name}”?", parent=self.root):
            core.delete_style(name)
            self.apply_style(next(iter(core.BUILTIN_STYLES)))

    # ---------------------------------------------------------------- file
    def refresh_files(self):
        names = [os.path.basename(p) for p in self.paths]
        self.file_box["values"] = names
        if names and self.file_var.get() not in names:
            self.file_var.set(names[0])
        n = len(self.paths)
        self.ok_btn.state(["!disabled"] if n else ["disabled"])
        self.status.configure(text=f"{n} ảnh sẽ được chuyển." if n else
                              "Kéo thả ảnh vào cửa sổ, hoặc bấm “Thêm ảnh…”.")
        self.schedule()

    def browse(self):
        ps = filedialog.askopenfilenames(parent=self.root, title="Chọn ảnh",
                                         filetypes=[("Ảnh", " ".join("*" + e for e in core.IMAGE_EXT)),
                                                    ("Tất cả", "*.*")])
        if ps:
            self.drop(list(ps))

    def drop(self, paths):
        if self._busy:
            return
        known = {os.path.normcase(p) for p in self.paths}
        self.paths += [p for p in expand(paths) if os.path.normcase(p) not in known]
        self.refresh_files()

    def current_path(self):
        name = self.file_var.get()
        for p in self.paths:
            if os.path.basename(p) == name:
                return p
        return self.paths[0] if self.paths else None

    def source(self, path):
        """Ảnh gốc đã thu nhỏ sẵn (tối đa 1200px) để xem trước cho nhanh."""
        if path not in self.src_cache:
            with Image.open(path) as im:
                im = im.convert("RGBA")
                im.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
            self.src_cache[path] = im
        return self.src_cache[path]

    # ---------------------------------------------------------------- xem trước
    def schedule(self):
        if self._pending:
            self.root.after_cancel(self._pending)
        self._pending = self.root.after(180, self.render)

    def render(self):
        self._pending = None
        path = self.current_path()
        if not path:
            self.before = self.after_img = None
            self.redraw()
            return
        self.gen += 1
        gen, params = self.gen, dict(self.params)
        self.info.configure(text="Đang xem trước…")

        def work():
            try:
                src = self.source(path)
                out, ncol = core.convert(src, params, scale=1)
                res = (src, out, ncol, None)
            except Exception as e:
                res = (None, None, 0, e)
            self.root.after(0, lambda: self.show(gen, path, *res))
        threading.Thread(target=work, daemon=True).start()

    def show(self, gen, path, src, out, ncol, err):
        if gen != self.gen:
            return
        if err:
            self.before = self.after_img = None
            self.info.configure(text=f"Lỗi: {err}")
            self.redraw()
            return
        self.before, self.after_img = src, out
        with Image.open(path) as im:
            w, h = im.size
        s = int(self.params["scale"])
        self.info.configure(text=f"Gốc {w}×{h}  →  pixel {out.width}×{out.height}, {ncol} màu  →  lưu "
                                 f"{out.width * s}×{out.height * s}")
        self.redraw()

    def redraw(self):
        c = self.canvas
        c.delete("all")
        cw, ch = max(c.winfo_width(), 50), max(c.winfo_height(), 50)
        if not getattr(self, "after_img", None):
            c.create_text(cw // 2, ch // 2, fill="#9aa0aa", font=("Segoe UI", 12),
                          text="Kéo thả ảnh vào đây" if not self.paths else "")
            return
        mode = self.view.get()
        imgs = {"after": [self.after_img], "before": [self.before],
                "both": [self.before, self.after_img]}[mode]
        slot_w = (cw - 12 * (len(imgs) - 1)) // len(imgs)
        self._photos = []
        bg = checker(cw, ch)
        x0 = 0
        for im in imgs:
            k = min(slot_w / im.width, ch / im.height)
            if im is self.after_img and k >= 1:
                k = max(1, int(k))                       # phóng nguyên lần để pixel sắc
            w, h = max(1, int(im.width * k)), max(1, int(im.height * k))
            res = Image.Resampling.NEAREST if im is self.after_img else Image.Resampling.LANCZOS
            shown = im.resize((w, h), res)
            bg.paste(shown, (x0 + (slot_w - w) // 2, (ch - h) // 2), shown)
            x0 += slot_w + 12
        self._photos.append(to_photo(bg))
        c.create_image(0, 0, anchor="nw", image=self._photos[-1])

    # ---------------------------------------------------------------- chuyển
    def run(self):
        if self._busy or not self.paths:
            return
        self._busy = True
        self.ok_btn.state(["disabled"])
        self.settings.update(last_style=self.style_var.get(), open_folder=self.open_var.get(),
                             close_when_done=self.close_var.get())
        core.save_settings(self.settings)
        paths, params = list(self.paths), dict(self.params)
        self.prog.configure(maximum=len(paths), value=0)

        def work():
            done, errors = [], []
            for i, p in enumerate(paths, 1):
                self.root.after(0, lambda i=i, p=p: self.status.configure(
                    text=f"Đang chuyển {i}/{len(paths)}: {os.path.basename(p)}"))
                try:
                    done.append(core.convert_file(p, params))
                except Exception as e:
                    errors.append(f"{os.path.basename(p)}: {e}")
                self.root.after(0, lambda i=i: self.prog.configure(value=i))
            self.root.after(0, lambda: self.finished(done, errors))
        threading.Thread(target=work, daemon=True).start()

    def finished(self, done, errors):
        self._busy = False
        self.ok_btn.state(["!disabled"])
        self.status.configure(text=f"Xong {len(done)} ảnh." + (f" Lỗi {len(errors)} ảnh." if errors else ""))
        if errors:
            messagebox.showwarning(APP, "Một số ảnh bị lỗi:\n\n" + "\n".join(errors[:10]), parent=self.root)
        if done and self.open_var.get():
            reveal(done[0])
        if done and self.close_var.get() and not errors:
            self.root.after(400, self.root.destroy)

    def close(self):
        if self._busy and not messagebox.askyesno(APP, "Đang chuyển ảnh. Vẫn đóng?", parent=self.root):
            return
        self.root.destroy()


# ============================================================ cập nhật
def do_update(root, then_quit=False):
    try:
        ver = updater.apply_update()
        root.after(0, lambda: messagebox.showinfo(APP, f"Đã cập nhật lên {ver}. Mở lại {APP} để dùng bản mới."))
    except Exception as e:
        err = e
        root.after(0, lambda: messagebox.showerror(APP, f"Cập nhật thất bại:\n{err}"))
    if then_quit:
        root.after(100, root.destroy)


def manual_update(root):
    root.withdraw()
    try:
        r = updater.check(force=True)
    except Exception as e:
        messagebox.showerror(APP, f"Không kết nối được GitHub:\n{e}")
        return root.destroy()
    if not r:
        messagebox.showinfo(APP, f"Bạn đang dùng bản mới nhất ({updater.local_version()}).")
        return root.destroy()
    ver, notes = r
    if messagebox.askyesno(APP, f"Có bản mới {ver} (đang dùng {updater.local_version()}).\n\n{notes}\n\nCập nhật ngay?"):
        threading.Thread(target=lambda: do_update(root, then_quit=True), daemon=True).start()
    else:
        root.destroy()


def auto_update_check(root, busy):
    """Kiểm tra ngầm tối đa 6 tiếng / lần. Có bản mới thì hỏi người dùng."""
    def work():
        try:
            r = updater.check()
        except Exception:
            return
        if r:
            root.after(0, lambda: ask(*r))

    def ask(ver, notes):
        if busy():
            return root.after(5000, lambda: ask(ver, notes))
        if messagebox.askyesno(APP, f"Có bản mới {ver}.\n\n{notes}\n\nCập nhật ngay?", parent=root):
            threading.Thread(target=lambda: do_update(root), daemon=True).start()
        else:
            updater.skip(ver)
    root.after(1500, lambda: threading.Thread(target=work, daemon=True).start())


# ============================================================ main
def main():
    args = sys.argv[1:]
    mode = args[0] if args else "home"
    paths = args[1:]

    if mode == "update":
        root = tk.Tk()
        manual_update(root)
        root.mainloop()
        return

    if mode == "convert":
        paths = gather_paths(paths)            # Explorer gọi 1 lần / file → gom lại
        if paths is None:
            return
    elif mode == "convert-folder":
        paths = core.images_in_folder(paths[0] if paths else os.getcwd())
    elif mode != "home":
        paths = args                           # gọi kiểu: psxpixel.pyw ảnh1 ảnh2
    paths = expand(paths)

    root = tk.Tk()
    setup_style(root)
    try:
        root.iconbitmap(default=os.path.join(core.APP_DIR, "psxpixel.ico"))
    except Exception:
        pass
    win = ConvertWindow(root, paths)
    root._win = win
    root.title(f"{APP}  (v{updater.local_version()})")
    try:
        enable_drop(root)
    except Exception:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("enable_drop: " + traceback.format_exc())
    auto_update_check(root, lambda: win._busy)
    root.lift()
    root.attributes("-topmost", True)
    root.after(300, lambda: root.attributes("-topmost", False))
    root.focus_force()
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(traceback.format_exc())
        try:
            messagebox.showerror(APP, traceback.format_exc())
        except Exception:
            pass
