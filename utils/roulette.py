"""توليد صور لعبة الروليت — عجلة أوروبية + طاولة رهان (مكتبة Pillow).

كل الرسوم تُبنى وقت التشغيل بلا أي ملف خارجي: العجلة والأرقام والكرة
وطاولة الرهان مع تمييز نوع الرهان الحالي.
"""
from __future__ import annotations

import io
import math
import os
import uuid
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

# ترتيب جيوب العجلة الأوروبية — يبدأ من الأعلى ويسير باتجاه عقارب الساعة
WHEEL_ORDER = [
    0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13,
    36, 11, 30, 8, 23, 10, 5, 24, 16, 33, 1, 20, 14,
    31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26,
]

RED_NUMBERS = frozenset({1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36})
BLACK_NUMBERS = frozenset({2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35})

# ── الألوان ──────────────────────────────────────────────────────────────
C_BG = (12, 13, 18)
C_PANEL = (24, 26, 34)
C_GOLD = (240, 196, 90)
C_GOLD_DIM = (146, 118, 58)
C_RED = (196, 40, 48)
C_BLACK = (26, 27, 32)
C_GREEN = (24, 122, 70)
C_TEXT = (245, 245, 245)
C_DIM = (150, 152, 162)
C_CONE_OUT = (16, 17, 22)
C_CONE_IN = (88, 76, 46)

# ── أنواع الرهان ────────────────────────────────────────────────────────
BET_KEYS = [
    "red", "black", "odd", "even", "low", "high",
    "dozen1", "dozen2", "dozen3", "col1", "col2", "col3", "straight",
]

BETS = {
    "red": {"label": "أحمر", "emoji": "🔴", "payout": 1, "desc": "18 رقمًا أحمر"},
    "black": {"label": "أسود", "emoji": "⚫", "payout": 1, "desc": "18 رقمًا أسود"},
    "odd": {"label": "فردي", "emoji": "🔢", "payout": 1, "desc": "1, 3, 5 … 35"},
    "even": {"label": "زوجي", "emoji": "🔢", "payout": 1, "desc": "2, 4, 6 … 36"},
    "low": {"label": "منخفض", "emoji": "⬇️", "payout": 1, "desc": "الأرقام 1 - 18"},
    "high": {"label": "مرتفع", "emoji": "⬆️", "payout": 1, "desc": "الأرقام 19 - 36"},
    "dozen1": {"label": "الدزينة الأولى", "emoji": "🎁", "payout": 2, "desc": "1 - 12"},
    "dozen2": {"label": "الدزينة الثانية", "emoji": "🎁", "payout": 2, "desc": "13 - 24"},
    "dozen3": {"label": "الدزينة الثالثة", "emoji": "🎁", "payout": 2, "desc": "25 - 36"},
    "col1": {"label": "العمود الأول", "emoji": "📊", "payout": 2, "desc": "1, 4, 7 … 34"},
    "col2": {"label": "العمود الثاني", "emoji": "📊", "payout": 2, "desc": "2, 5, 8 … 35"},
    "col3": {"label": "العمود الثالث", "emoji": "📊", "payout": 2, "desc": "3, 6, 9 … 36"},
    "straight": {"label": "رقم مباشر", "emoji": "🎯", "payout": 35, "desc": "رقم واحد من 0 إلى 36"},
}


def bet_numbers(key: str, value: int | None = None) -> set[int]:
    """الأرقام التي يغطيها نوع الرهان الحالي."""
    if key == "red":
        return set(RED_NUMBERS)
    if key == "black":
        return set(BLACK_NUMBERS)
    if key == "odd":
        return {n for n in range(1, 37) if n % 2 == 1}
    if key == "even":
        return {n for n in range(1, 37) if n % 2 == 0}
    if key == "low":
        return set(range(1, 19))
    if key == "high":
        return set(range(19, 37))
    if key == "dozen1":
        return set(range(1, 13))
    if key == "dozen2":
        return set(range(13, 25))
    if key == "dozen3":
        return set(range(25, 37))
    if key == "col1":
        return {n for n in range(1, 37) if (n - 1) % 3 == 0}
    if key == "col2":
        return {n for n in range(1, 37) if (n - 1) % 3 == 1}
    if key == "col3":
        return {n for n in range(1, 37) if (n - 1) % 3 == 2}
    if key == "straight" and value is not None and 0 <= int(value) <= 36:
        return {int(value)}
    if key == "zero":
        return {0}
    return set()


def number_color(n: int) -> tuple[int, int, int]:
    if n == 0:
        return C_GREEN
    return C_RED if n in RED_NUMBERS else C_BLACK


def number_emoji(n: int) -> str:
    if n == 0:
        return "🟢"
    return "🔴" if n in RED_NUMBERS else "⚫"


# ── الخطوط ──────────────────────────────────────────────────────────────
_FONT_PATHS = [
    r"C:\Windows\Fonts\arialbd.ttf",
    r"C:\Windows\Fonts\seguisb.ttf",
    r"C:\Windows\Fonts\verdanab.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
]


def _font(size: int):
    for path in _FONT_PATHS:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _lerp(a, b, t: float):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def _center_text(d: ImageDraw.ImageDraw, box, text, font, fill):
    x0, y0, x1, y1 = box
    bb = d.textbbox((0, 0), text, font=font)
    w, h = bb[2] - bb[0], bb[3] - bb[1]
    d.text((x0 + (x1 - x0 - w) / 2 - bb[0], y0 + (y1 - y0 - h) / 2 - bb[1]),
           text, font=font, fill=fill)


def _polar(cx, cy, r, deg_cw_from_top: float):
    """نقطة على دائرة بزاوية تُقاس باتجاه عقارب الساعة من الأعلى."""
    a = math.radians(deg_cw_from_top)
    return cx + r * math.sin(a), cy - r * math.cos(a)


# ── العجلة ──────────────────────────────────────────────────────────────
def render_wheel(winner: int | None = None, size: int = 640) -> Image.Image:
    """عجلة روليت أوروبية؛ تُرسم الكرة على الجيب الفائز إن وُجد `winner`."""
    scale = 2
    w = size * scale
    img = Image.new("RGBA", (w, w), C_BG + (255,))
    d = ImageDraw.Draw(img)
    cx = cy = w / 2

    r_rim_out = w * 0.492      # الحافة الذهبية الخارجية
    r_track = w * 0.470        # مسار الكرة
    r_poc_out = w * 0.415      # خارجي الجيوب
    r_poc_in = w * 0.262       # داخلي الجيوب

    d.ellipse([cx - r_rim_out, cy - r_rim_out, cx + r_rim_out, cy + r_rim_out], fill=C_GOLD + (255,))
    d.ellipse([cx - r_track, cy - r_track, cx + r_track, cy + r_track], fill=C_BG + (255,))

    # الجيوب
    step = 360.0 / len(WHEEL_ORDER)
    for i, n in enumerate(WHEEL_ORDER):
        a0 = i * step - 90.0
        a1 = a0 + step
        box = [cx - r_poc_out, cy - r_poc_out, cx + r_poc_out, cy + r_poc_out]
        d.pieslice(box, a0, a1, fill=number_color(n) + (255,))

    # تغطية مركز الجيوب بالقرص الداكن
    d.ellipse([cx - r_poc_in, cy - r_poc_in, cx + r_poc_in, cy + r_poc_in], fill=C_BG + (255,))

    # فواصل الجيوب + الأرقام
    f_num = _font(int(w * 0.038))
    r_mid = r_poc_in + (r_poc_out - r_poc_in) * 0.5
    for i, n in enumerate(WHEEL_ORDER):
        mid = (i + 0.5) * step
        p0 = _polar(cx, cy, r_poc_in, i * step)
        p1 = _polar(cx, cy, r_poc_out, i * step)
        d.line([p0, p1], fill=C_GOLD + (255,), width=max(2, int(w * 0.004)))
        _wheel_label(img, cx, cy, str(n), mid, r_mid, f_num)

    # القُمّة الداخلية بتدرّج (يُبنى صغيرًا ثم يُكبّر — أسرع بكثير)
    cone_r = int(r_poc_in)
    cone = _cone_gradient(cone_r * 2)
    mask = Image.new("L", cone.size, 0)
    ImageDraw.Draw(mask).ellipse([0, 0, cone.size[0] - 1, cone.size[1] - 1], fill=255)
    img.paste(cone, (int(cx - cone_r), int(cy - cone_r)), mask)

    # أضلاع القُمّة
    for i in range(len(WHEEL_ORDER)):
        p = _polar(cx, cy, r_poc_in, i * step)
        d.line([cx, cy, p[0], p[1]], fill=C_GOLD_DIM + (255,), width=max(1, int(w * 0.003)))

    cap = w * 0.055
    d.ellipse([cx - cap, cy - cap, cx + cap, cy + cap], fill=C_GOLD + (255,))
    d.ellipse([cx - cap * 0.55, cy - cap * 0.55, cx + cap * 0.55, cy + cap * 0.55],
              fill=C_CONE_OUT + (255,))

    # الكرة
    if winner in WHEEL_ORDER:
        idx = WHEEL_ORDER.index(winner)
        r_ball = r_poc_in + (r_poc_out - r_poc_in) * 0.80
        bx, by = _polar(cx, cy, r_ball, (idx + 0.5) * step)
        br = w * 0.023
        d.ellipse([bx - br * 1.15, by - br * 0.85, bx + br * 1.15, by + br * 1.35],
                  fill=(0, 0, 0, 120))
        d.ellipse([bx - br, by - br, bx + br, by + br], fill=(250, 250, 252, 255))
        d.ellipse([bx - br * 0.55, by - br * 0.7, bx + br * 0.1, by - br * 0.05],
                  fill=(255, 255, 255, 255))

    # إطار خارجي رفيع يجمع الصورة مع طاولة الرهان
    d.rounded_rectangle([2, 2, w - 3, w - 3], radius=int(w * 0.03),
                        outline=C_GOLD_DIM + (255,), width=max(2, int(w * 0.004)))

    return img.resize((size, size), Image.Resampling.LANCZOS)


def _wheel_label(target: Image.Image, cx, cy, text, angle_cw, radius, font):
    """يرسم رقمًا صغيرًا عند مركز العجلة ثم يدوّره وينقله إلى الجيب."""
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    bb = probe.textbbox((0, 0), text, font=font)
    tw, th = bb[2] - bb[0] + 8, bb[3] - bb[1] + 8

    tile = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    ImageDraw.Draw(tile).text((4 - bb[0], 4 - bb[1]), text, font=font, fill=C_TEXT)
    rot = tile.rotate(-angle_cw, resample=Image.Resampling.BICUBIC, expand=True)

    px, py = _polar(cx, cy, radius, angle_cw)
    target.paste(rot, (int(px - rot.width / 2), int(py - rot.height / 2)), rot)


def _cone_gradient(diameter: int) -> Image.Image:
    """قرص داكن متدرّج للقُمّة الداخلية — يُبنى صغيرًا ثم يُكبّر."""
    n = 96
    small = Image.new("RGB", (n, n), C_CONE_OUT)
    sd = ImageDraw.Draw(small)
    c = (n - 1) / 2
    for i in range(int(c), 0, -1):
        t = 1 - i / c
        sd.ellipse([c - i, c - i, c + i, c + i], fill=_lerp(C_CONE_OUT, C_CONE_IN, t))
    d = max(8, int(diameter))
    return small.resize((d, d), Image.Resampling.LANCZOS)


# ── طاولة الرهان ────────────────────────────────────────────────────────
_CELL_W, _CELL_H = 64, 58
_ZERO_W = 54
_COL_W = 46
_DOZ_H = 42
_OUT_H = 42
_M = 20


def _table_size():
    grid_w = 12 * _CELL_W
    return (_M * 2 + _ZERO_W + grid_w + 3 * _COL_W,
            _M * 2 + 3 * _CELL_H + _DOZ_H + _OUT_H, grid_w)


def render_table(bet_key: str | None = None, bet_value: int | None = None) -> Image.Image:
    """طاولة الرهان مع تمييز ذهبي للأرقام التي يغطيها الرهان الحالي."""
    scale = 2
    tw, th, grid_w = _table_size()
    W, H = tw * scale, th * scale
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    d.rounded_rectangle([0, 0, W - 1, H - 1], radius=18 * scale, fill=C_PANEL + (255,),
                        outline=C_GOLD_DIM + (255,), width=2 * scale)

    covered = bet_numbers(bet_key, bet_value) if bet_key else set()
    # الخطوط تُصمَّ مكبّرة ×2 ثم تُصغَّر؛ ديسكورد يعرض الصورة بنصف حجمها تقريبًا
    f_num = _font(int(32 * scale))
    f_lbl = _font(int(24 * scale))
    f_tag = _font(int(20 * scale))

    grid_w = 12 * _CELL_W * scale          # عرض شبكة الأرقام بعد التكبير
    x0, y0 = (_M + _ZERO_W) * scale, _M * scale
    cw, ch = _CELL_W * scale, _CELL_H * scale

    def cell(box, fill, text, font, text_fill, highlight, radius=6 * scale):
        d.rounded_rectangle(box, radius=radius, fill=fill + (255,),
                            outline=C_GOLD_DIM + (255,), width=scale)
        _center_text(d, box, text, font, text_fill)
        if highlight:
            d.rounded_rectangle(box, radius=radius, outline=C_GOLD + (255,),
                                width=3 * scale)

    # 0
    zero_box = [_M * scale, y0, (_M + _ZERO_W) * scale, y0 + 3 * ch]
    cell(zero_box, C_GREEN, "0", f_num, C_TEXT, bet_key == "zero" or (bet_key == "straight" and bet_value == 0))

    # الأرقام 1 - 36
    for n in range(1, 37):
        col = (n - 1) // 3
        row = 2 - ((n - 1) % 3)
        box = [x0 + col * cw, y0 + row * ch, x0 + (col + 1) * cw, y0 + (row + 1) * ch]
        cell(box, number_color(n), str(n), f_num, C_TEXT, n in covered)

    # أعمدة الربح (2:1)
    for i in range(3):
        box = [x0 + grid_w + i * _COL_W * scale, y0 + i * ch,
               x0 + grid_w + (i + 1) * _COL_W * scale, y0 + (i + 1) * ch]
        cell(box, (38, 41, 52), "2:1", f_tag, C_GOLD, bet_key == f"col{i + 1}", radius=4 * scale)

    # الدزينات
    dy = y0 + 3 * ch
    dz_w = grid_w // 3
    for i in range(3):
        box = [x0 + i * dz_w, dy, x0 + (i + 1) * dz_w, dy + _DOZ_H * scale]
        cell(box, (38, 41, 52), ["1-12", "13-24", "25-36"][i], f_lbl, C_TEXT,
             bet_key == f"dozen{i + 1}", radius=4 * scale)

    # صفوف الخارج — أسماء لاتينية لأن PIL لا يشكّل الحروف العربية
    oy = dy + _DOZ_H * scale
    oh = _OUT_H * scale
    out_cells = [("1-18", "low"), ("EVEN", "even"), ("RED", "red"),
                 ("BLACK", "black"), ("ODD", "odd"), ("19-36", "high")]
    ow = grid_w // 6
    for i, (lbl, key) in enumerate(out_cells):
        fill = C_RED if key == "red" else C_BLACK if key == "black" else (38, 41, 52)
        box = [x0 + i * ow, oy, x0 + (i + 1) * ow, oy + oh]
        cell(box, fill, lbl, f_lbl, C_TEXT, bet_key == key, radius=4 * scale)

    return img.resize((tw, th), Image.Resampling.LANCZOS)


# ── الملفات الجاهزة للإرفاق ────────────────────────────────────────────
@lru_cache(maxsize=128)
def _wheel_png(winner: int | None) -> bytes:
    out = io.BytesIO()
    render_wheel(winner).convert("RGB").save(out, format="PNG")
    return out.getvalue()


@lru_cache(maxsize=128)
def _table_png(bet) -> bytes:
    bet_key, bet_value = bet if bet else (None, None)
    out = io.BytesIO()
    render_table(bet_key, bet_value).save(out, format="PNG")
    return out.getvalue()


def wheel_file(winner: int | None = None) -> tuple[io.BytesIO, str]:
    """صورة العجلة (مرفقة كصورة رئيسية في رسالة البوت)."""
    return io.BytesIO(_wheel_png(winner)), f"wheel_{uuid.uuid4().hex[:8]}.png"


def table_file(bet_key: str | None = None, bet_value: int | None = None) -> tuple[io.BytesIO, str]:
    """صورة طاولة الرهان مع تمييز الرهان الحالي."""
    key = None if bet_key is None else (bet_key, None if bet_value is None else int(bet_value))
    return io.BytesIO(_table_png(key)), f"table_{uuid.uuid4().hex[:8]}.png"
