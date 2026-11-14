"""PSX Pixel core: chuyển tranh thành pixel art kiểu PS1 (không phụ thuộc GUI)."""
import json
import os

import numpy as np
from PIL import Image, ImageEnhance

APP_DIR = os.path.dirname(os.path.abspath(__file__))
STYLES_PATH = os.path.join(APP_DIR, "styles.json")        # style người dùng tự lưu
SETTINGS_PATH = os.path.join(APP_DIR, "settings.json")    # tuỳ chọn chung
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tga", ".tif", ".tiff")
OUT_SUFFIX = "_psx"

# ---------------------------------------------------------------- bảng màu
PALETTES = {
    "Dunmorn (sương xám xanh)": [
        "0d0f14", "1b1f2a", "2a3140", "3b4556", "4f5b6e", "66738a",
        "8290a6", "a3afc0", "c6cfda", "e8edf2",
        "3a2a2a", "5e423b", "86604f", "b08770", "d4ad92", "f0d5c0",
        "d9d6cc", "f4f1e8",
        "6b5a1e", "b8962e", "e6c35a",
        "6e1f24", "a8323a",
        "1f3a33", "3c6157",
    ],
    "Sodium (vàng đèn đường)": [
        "0b0d06", "1d2210", "2f3618", "434b20", "5a6129", "747a32",
        "92933b", "b1ad48", "cfc75a", "ece27a", "fff7b0",
        "3a1a10", "6e3218", "a24e22", "1d3a2a", "2f5a3e",
    ],
    "Game Boy (4 màu)": ["0f380f", "306230", "8bac0f", "9bbc0f"],
    "Đen trắng (8 sắc xám)": ["000000", "242424", "494949", "6d6d6d", "929292", "b6b6b6", "dbdbdb", "ffffff"],
}
AUTO = "Tự động (lấy từ tranh)"

DITHERS = {"Bayer (chấm đều, kiểu PS1)": "bayer", "Floyd-Steinberg (mịn)": "fs", "Không dither": "none"}

DEFAULT = {
    "height": 160, "palette": "Dunmorn (sương xám xanh)", "colors": 24, "dither": "bayer",
    "strength": 1.0, "grain": 0.02, "contrast": 1.1, "saturation": 0.9,
    "tint": "", "tint_amount": 0.15, "scale": 4,
}

BUILTIN_STYLES = {
    "PSX Dunmorn – sương xám xanh": dict(DEFAULT),
    "PSX Sodium – vàng đèn đường": dict(DEFAULT, palette="Sodium (vàng đèn đường)",
                                        tint="e6c35a", tint_amount=0.12, saturation=1.0),
    "Anime 90s – mịn, nhiều màu": dict(DEFAULT, palette=AUTO, colors=32, dither="fs",
                                       height=220, grain=0.03, contrast=1.05, saturation=1.0, scale=3),
    "Giữ màu gốc – 24 màu": dict(DEFAULT, palette=AUTO, colors=24, saturation=1.0, contrast=1.0),
    "Pixel thô – Game Boy": dict(DEFAULT, palette="Game Boy (4 màu)", height=96, grain=0.0,
                                 contrast=1.2, scale=6),
}


def _read_json(path, fallback):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return fallback


def _write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def all_styles():
    styles = {k: dict(v) for k, v in BUILTIN_STYLES.items()}
    for k, v in _read_json(STYLES_PATH, {}).items():
        styles[k] = dict(DEFAULT, **v)
    return styles


def user_style_names():
    return list(_read_json(STYLES_PATH, {}).keys())


def save_style(name, params):
    data = _read_json(STYLES_PATH, {})
    data[name] = {k: params[k] for k in DEFAULT}
    _write_json(STYLES_PATH, data)


def delete_style(name):
    data = _read_json(STYLES_PATH, {})
    if data.pop(name, None) is not None:
        _write_json(STYLES_PATH, data)


def load_settings():
    return dict({"last_style": next(iter(BUILTIN_STYLES)), "open_folder": True, "close_when_done": True},
                **_read_json(SETTINGS_PATH, {}))


def save_settings(s):
    try:
        _write_json(SETTINGS_PATH, s)
    except OSError:
        pass


def is_image(p):
    return os.path.splitext(p)[1].lower() in IMAGE_EXT and not os.path.splitext(p)[0].endswith(OUT_SUFFIX)


def images_in_folder(folder):
    try:
        names = sorted(os.listdir(folder))
    except OSError:
        return []
    return [os.path.join(folder, n) for n in names if is_image(os.path.join(folder, n))]


def output_path(src):
    base = os.path.splitext(src)[0] + OUT_SUFFIX
    path, n = base + ".png", 2
    while os.path.exists(path):
        path, n = f"{base}_{n}.png", n + 1
    return path


# ---------------------------------------------------------------- xử lý ảnh
BAYER4 = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]],
                   dtype=np.float32) + 0.5) / 16.0 - 0.5
_W = np.array([0.30, 0.59, 0.11], dtype=np.float32) * 3


def hex_to_rgb(h):
    h = (h or "").strip().lstrip("#")
    if len(h) != 6:
        raise ValueError(f"Mã màu không hợp lệ: {h!r}")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def get_palette(name, image_rgb, colors):
    if name == AUTO or name not in PALETTES and not os.path.isfile(name):
        q = Image.fromarray(image_rgb).quantize(colors=max(2, min(256, int(colors))),
                                                method=Image.Quantize.MEDIANCUT)
        n = len(set(q.getdata()))
        return np.array(q.getpalette()[: max(n, 2) * 3], dtype=np.uint8).reshape(-1, 3)
    if name in PALETTES:
        cols = PALETTES[name]
    else:  # file .hex của Lospec
        with open(name, encoding="utf-8") as f:
            cols = [ln.strip() for ln in f if ln.strip() and not ln.startswith(";")]
    return np.array([hex_to_rgb(c) for c in cols], dtype=np.uint8)


def _nearest(pixels, pal):
    p = pal.astype(np.float32)
    flat = pixels.reshape(-1, 3)
    out = np.empty(flat.shape[0], dtype=np.int32)
    for i in range(0, flat.shape[0], 32768):
        c = flat[i:i + 32768]
        out[i:i + 32768] = ((((c[:, None, :] - p[None]) ** 2) * _W).sum(2)).argmin(1)
    return out.reshape(pixels.shape[:2])


def _spread(pal):
    p = pal.astype(np.float32)
    d = np.sqrt(((p[:, None] - p[None]) ** 2).sum(2))
    d[d == 0] = np.inf
    m = d.min(1)
    m = m[np.isfinite(m)]
    return float(np.median(m)) if m.size else 32.0


def _floyd(img, pal, mask):
    h, w, _ = img.shape
    buf = img.astype(np.float32).copy()
    p = pal.astype(np.float32)
    idx = np.zeros((h, w), dtype=np.int32)
    for y in range(h):
        row, nxt = buf[y], buf[y + 1] if y + 1 < h else None
        for x in range(w):
            if not mask[y, x]:
                continue
            old = np.clip(row[x], 0, 255)
            k = int((((p - old) ** 2) * _W).sum(1).argmin())
            idx[y, x] = k
            e = old - p[k]
            if x + 1 < w:
                row[x + 1] += e * 0.4375
            if nxt is not None:
                if x:
                    nxt[x - 1] += e * 0.1875
                nxt[x] += e * 0.3125
                if x + 1 < w:
                    nxt[x + 1] += e * 0.0625
    return idx


def convert(src, params, scale=None, seed=7):
    """src: PIL.Image. params: dict theo DEFAULT. Trả về (ảnh RGBA, số màu)."""
    p = dict(DEFAULT, **params)
    img = src.convert("RGBA")
    rgb = img.convert("RGB")
    rgb = ImageEnhance.Contrast(rgb).enhance(float(p["contrast"]))
    rgb = ImageEnhance.Color(rgb).enhance(float(p["saturation"]))
    if p.get("tint"):
        rgb = Image.blend(rgb, Image.new("RGB", rgb.size, hex_to_rgb(p["tint"])), float(p["tint_amount"]))

    height = max(8, int(p["height"]))
    width = max(1, round(img.width * height / img.height))
    small = np.asarray(rgb.resize((width, height), Image.Resampling.BOX), dtype=np.float32)
    alpha = np.asarray(img.getchannel("A").resize((width, height), Image.Resampling.BOX))
    mask = alpha >= 128

    if float(p["grain"]) > 0:
        rng = np.random.default_rng(seed)
        small = small + rng.normal(0, float(p["grain"]) * 255, size=small.shape[:2])[..., None]

    pal = get_palette(p["palette"], np.clip(small, 0, 255).astype(np.uint8), p["colors"])
    if p["dither"] == "bayer":
        tile = np.tile(BAYER4, (height // 4 + 1, width // 4 + 1))[:height, :width]
        idx = _nearest(small + tile[..., None] * _spread(pal) * float(p["strength"]), pal)
    elif p["dither"] == "fs":
        idx = _floyd(small, pal, mask)
    else:
        idx = _nearest(small, pal)

    out = Image.fromarray(np.dstack([pal[idx], np.where(mask, 255, 0).astype(np.uint8)]), "RGBA")
    s = int(p["scale"] if scale is None else scale)
    if s > 1:
        out = out.resize((out.width * s, out.height * s), Image.Resampling.NEAREST)
    return out, len(pal)


def convert_file(path, params):
    with Image.open(path) as im:
        out, _ = convert(im, params)
    dst = output_path(path)
    out.save(dst)
    return dst
