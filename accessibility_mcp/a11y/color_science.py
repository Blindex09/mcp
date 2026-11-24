"""Ciencia de cores objetiva: analise de formatos CSS, luminancia WCAG 2.2, APCA, daltonismo e ajuste minimo em OKLCH.

Apenas matematica deterministica sobre espacos de cor (sRGB, OKLCH, CIE Lab, SAPC-APCA 0.0.98G-4g, matrizes lineares de daltonismo).
"""

from __future__ import annotations

import math
import re
from typing import Any

# Constantes APCA (SAPC 0.0.98G-4g / apca-w3 0.1.9)
_S_TRC = 2.4
_BLK_THRS = 0.022
_BLK_CLMP = 1.414
_DELTA_Y_MIN = 0.0005
_S_R_CO = 0.2126729
_S_G_CO = 0.7151522
_S_B_CO = 0.072175
_NORM_TXT = 0.57
_NORM_BG = 0.56
_REV_TXT = 0.62
_REV_BG = 0.65
_SCALE_BOW = 1.14
_SCALE_WOB = 1.14
_LO_BOW_OFFSET = 0.027
_LO_WOB_OFFSET = 0.027
_LO_CLIP = 0.1

# Limiares informativos de |Lc| APCA (fato objetivo de escala perceptiva, nao determinacao normativa)
_APCA_NOTES: tuple[tuple[float, str], ...] = (
    (90.0, "|Lc| >= 90: contraste alto, recomendado para corpo de texto em qualquer peso"),
    (75.0, "|Lc| >= 75: minimo para corpo de texto; confortavel para texto grande"),
    (60.0, "|Lc| >= 60: texto grande/negrito e controles de interface"),
    (45.0, "|Lc| >= 45: texto grande em negrito, bordas de controles e indicadores de foco"),
    (30.0, "|Lc| >= 30: elementos nao textuais muito grandes apenas"),
    (15.0, "|Lc| >= 15: visibilidade minima; insuficiente para conteudo significativo"),
)

# Matrizes de simulacao de daltonismo em sRGB linear (Machado et al. / Brettel / Viénot)
CVD_TYPES: tuple[str, ...] = (
    "protanopia",
    "deuteranopia",
    "tritanopia",
    "protanomaly",
    "deuteranomaly",
    "tritanomaly",
    "achromatopsia",
    "achromatomaly",
)

_CVD_MATRICES: dict[str, tuple[tuple[float, float, float], ...]] = {
    "protanopia": ((0.567, 0.433, 0.0), (0.558, 0.442, 0.0), (0.0, 0.242, 0.758)),
    "deuteranopia": ((0.625, 0.375, 0.0), (0.7, 0.3, 0.0), (0.0, 0.3, 0.7)),
    "tritanopia": ((0.95, 0.05, 0.0), (0.0, 0.433, 0.567), (0.0, 0.475, 0.525)),
    "protanomaly": ((0.817, 0.183, 0.0), (0.333, 0.667, 0.0), (0.0, 0.125, 0.875)),
    "deuteranomaly": ((0.8, 0.2, 0.0), (0.258, 0.742, 0.0), (0.0, 0.142, 0.858)),
    "tritanomaly": ((0.967, 0.033, 0.0), (0.0, 0.733, 0.267), (0.0, 0.183, 0.817)),
    "achromatopsia": ((0.299, 0.587, 0.114), (0.299, 0.587, 0.114), (0.299, 0.587, 0.114)),
    "achromatomaly": ((0.618, 0.32, 0.062), (0.163, 0.775, 0.062), (0.163, 0.32, 0.516)),
}

_HEX3_RE = re.compile(r"^#?([0-9a-fA-F]{3})$")
_HEX6_RE = re.compile(r"^#?([0-9a-fA-F]{6})$")
_FN_RE = re.compile(r"^(rgb|rgba|hsl|hsla|oklch)\(([^()]+)\)$", re.IGNORECASE)
_NUM_UNIT_RE = re.compile(r"^([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)(%|[a-zA-Z]*)$")


def srgb_to_linear(c: int) -> float:
    """Converte componente sRGB (0..255) para sRGB linear usando o corte IEC/WCAG 0.04045."""
    s = c / 255.0
    return s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4


def linear_to_srgb(c: float) -> int:
    """Converte componente sRGB linear para inteiro sRGB (0..255), limitado ao gamut sRGB."""
    if c <= 0.0:
        return 0
    if c >= 1.0:
        return 255
    s = c * 12.92 if c <= 0.0031308 else 1.055 * (c ** (1.0 / 2.4)) - 0.055
    return round(max(0.0, min(255.0, s * 255.0)))


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def relative_luminance(rgb: tuple[int, int, int]) -> float:
    """Luminancia relativa WCAG 2.x (Y no espaco linear Rec.709)."""
    r, g, b = (srgb_to_linear(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def wcag_contrast_ratio(fg: tuple[int, int, int], bg: tuple[int, int, int]) -> float:
    l1, l2 = relative_luminance(fg), relative_luminance(bg)
    return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)


def _parse_number(token: str) -> tuple[float, str]:
    m = _NUM_UNIT_RE.match(token.strip())
    if not m:
        raise ValueError(f"numero/unidade invalido: {token!r}")
    return float(m.group(1)), m.group(2).lower()


def _parse_alpha(token: str) -> float:
    val, unit = _parse_number(token)
    if unit == "%":
        val /= 100.0
    elif unit:
        raise ValueError(f"unidade de alfa invalida: {token!r}")
    if val < 0.0 or val > 1.0:
        raise ValueError(f"alfa fora do intervalo [0, 1]: {token!r}")
    return val


def _parse_hue(token: str) -> float:
    if token.strip().lower() == "none":
        return 0.0
    val, unit = _parse_number(token)
    if unit in ("", "deg"):
        deg = val
    elif unit == "rad":
        deg = math.degrees(val)
    elif unit == "turn":
        deg = val * 360.0
    elif unit == "grad":
        deg = val * 0.9
    else:
        raise ValueError(f"unidade de matiz invalida: {token!r}")
    return deg % 360.0


def _split_fn_args(body: str) -> tuple[list[str], str | None]:
    """Divide argumentos funcionais CSS (por virgula ou espaco + `/ alfa` opcional)."""
    alpha_part: str | None = None
    main = body.strip()
    if "/" in main:
        parts = main.split("/")
        if len(parts) != 2:
            raise ValueError(f"sintaxe alfa invalida em {body!r}")
        main, alpha_part = parts[0].strip(), parts[1].strip()
    if "," in main:
        tokens = [t.strip() for t in main.split(",") if t.strip()]
    else:
        tokens = [t.strip() for t in main.split() if t.strip()]
    return tokens, alpha_part


def _hsl_to_rgb(h: float, s: float, lightness: float) -> tuple[int, int, int]:
    """Converte matiz [0, 360), saturacao [0, 1], luminosidade [0, 1] em RGB 0..255."""
    s = max(0.0, min(1.0, s))
    lightness = max(0.0, min(1.0, lightness))
    c = (1.0 - abs(2.0 * lightness - 1.0)) * s
    x = c * (1.0 - abs((h / 60.0) % 2.0 - 1.0))
    m = lightness - c / 2.0
    if h < 60:
        r1, g1, b1 = c, x, 0.0
    elif h < 120:
        r1, g1, b1 = x, c, 0.0
    elif h < 180:
        r1, g1, b1 = 0.0, c, x
    elif h < 240:
        r1, g1, b1 = 0.0, x, c
    elif h < 300:
        r1, g1, b1 = x, 0.0, c
    else:
        r1, g1, b1 = c, 0.0, x
    return (
        round(max(0.0, min(255.0, (r1 + m) * 255.0))),
        round(max(0.0, min(255.0, (g1 + m) * 255.0))),
        round(max(0.0, min(255.0, (b1 + m) * 255.0))),
    )


def oklch_to_rgb(lightness: float, chroma: float, hue_deg: float) -> tuple[int, int, int]:
    """Converte OKLCH (L 0..1, C >= 0, H em graus) para sRGB 0..255."""
    hr = math.radians(hue_deg)
    a = chroma * math.cos(hr)
    b = chroma * math.sin(hr)
    l_ = lightness + 0.3963377774 * a + 0.2158037573 * b
    m_ = lightness - 0.1055613458 * a - 0.0638541728 * b
    s_ = lightness - 0.0894841775 * a - 1.2914855480 * b
    ell = l_ ** 3
    em = m_ ** 3
    es = s_ ** 3
    lr = +4.0767416621 * ell - 3.3077115913 * em + 0.2309699292 * es
    lg = -1.2684380046 * ell + 2.6097574011 * em - 0.3413193965 * es
    lb = -0.0041960863 * ell - 0.7034186147 * em + 1.7076147010 * es
    return linear_to_srgb(lr), linear_to_srgb(lg), linear_to_srgb(lb)


def rgb_to_oklch(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    """Converte sRGB (0..255) para OKLCH (L, C, H em graus)."""
    lr, lg, lb = (srgb_to_linear(c) for c in rgb)
    ell = 0.4122214708 * lr + 0.5363325363 * lg + 0.0514459929 * lb
    em = 0.2119034982 * lr + 0.6806995451 * lg + 0.1073969566 * lb
    es = 0.0883024619 * lr + 0.2817188376 * lg + 0.6299787005 * lb
    l_ = math.copysign(abs(ell) ** (1.0 / 3.0), ell)
    m_ = math.copysign(abs(em) ** (1.0 / 3.0), em)
    s_ = math.copysign(abs(es) ** (1.0 / 3.0), es)
    lightness = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    b = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    chroma = math.hypot(a, b)
    hue = math.degrees(math.atan2(b, a)) % 360.0 if chroma > 1e-7 else 0.0
    return lightness, chroma, hue


def parse_color(value: str) -> tuple[int, int, int]:
    """Analisa #rgb, #rrggbb, rgb()/rgba(), hsl()/hsla() e oklch() opacos; rejeita nomes e alfa < 1."""
    raw = value.strip()
    if m3 := _HEX3_RE.match(raw):
        h = "".join(c * 2 for c in m3.group(1))
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    if m6 := _HEX6_RE.match(raw):
        h = m6.group(1)
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    mfn = _FN_RE.match(raw)
    if not mfn:
        raise ValueError(f"cor invalida: {value!r} (use #rgb, #rrggbb, rgb(), rgba(), hsl() ou oklch())")
    kind = mfn.group(1).lower()
    tokens, slash_alpha = _split_fn_args(mfn.group(2))
    alpha_tok = slash_alpha
    if kind in ("rgb", "rgba", "hsl", "hsla") and len(tokens) == 4 and alpha_tok is None:
        alpha_tok = tokens.pop()
    if len(tokens) != 3:
        raise ValueError(f"cor {kind}() invalida: {value!r}")
    if alpha_tok is not None and _parse_alpha(alpha_tok) < 0.999:
        raise ValueError(f"cor com alfa < 1 ({value!r}): componha sobre o fundo antes de medir contraste")
    if kind in ("rgb", "rgba"):
        channels: list[int] = []
        for tok in tokens:
            v, unit = _parse_number(tok)
            if unit == "%":
                v = v / 100.0 * 255.0
            elif unit:
                raise ValueError(f"unidade invalida em rgb(): {tok!r}")
            channels.append(round(max(0.0, min(255.0, v))))
        return channels[0], channels[1], channels[2]
    if kind in ("hsl", "hsla"):
        hue = _parse_hue(tokens[0])
        sat_val, sat_unit = _parse_number(tokens[1])
        lit_val, lit_unit = _parse_number(tokens[2])
        if sat_unit not in ("", "%") or lit_unit not in ("", "%"):
            raise ValueError(f"unidade invalida em hsl(): {value!r}")
        return _hsl_to_rgb(hue, sat_val / 100.0, lit_val / 100.0)
    # oklch(L C H)
    l_val, l_unit = _parse_number(tokens[0])
    if l_unit == "%":
        l_val /= 100.0
    elif l_unit:
        raise ValueError(f"luminosidade L invalida em oklch(): {tokens[0]!r}")
    c_val, c_unit = _parse_number(tokens[1])
    if c_unit == "%":
        c_val = c_val / 100.0 * 0.4
    elif c_unit:
        raise ValueError(f"croma C invalido em oklch(): {tokens[1]!r}")
    if c_val < 0.0:
        raise ValueError(f"croma negativo em oklch(): {tokens[1]!r}")
    hue_val = _parse_hue(tokens[2])
    return oklch_to_rgb(max(0.0, min(1.0, l_val)), c_val, hue_val)


def apca_contrast(text_rgb: tuple[int, int, int], bg_rgb: tuple[int, int, int]) -> float:
    """Contraste perceptual APCA (SAPC 0.0.98G-4g): positivo em texto escuro sobre fundo claro, negativo no inverso."""

    def to_y(rgb: tuple[int, int, int]) -> float:
        r, g, b = ((c / 255.0) ** _S_TRC for c in rgb)
        return max(0.0, _S_R_CO * r + _S_G_CO * g + _S_B_CO * b)

    def clamp_black(y: float) -> float:
        return y if y >= _BLK_THRS else y + (_BLK_THRS - y) ** _BLK_CLMP

    y_txt = to_y(text_rgb)
    y_bg = to_y(bg_rgb)
    if abs(y_txt - y_bg) < _DELTA_Y_MIN:
        return 0.0
    y_txt = clamp_black(y_txt)
    y_bg = clamp_black(y_bg)
    if y_bg > y_txt:
        sapc = (y_bg ** _NORM_BG - y_txt ** _NORM_TXT) * _SCALE_BOW
        return 0.0 if sapc < _LO_CLIP else (sapc - _LO_BOW_OFFSET) * 100.0
    sapc = (y_bg ** _REV_BG - y_txt ** _REV_TXT) * _SCALE_WOB
    return 0.0 if sapc > -_LO_CLIP else (sapc + _LO_WOB_OFFSET) * 100.0


def apca_note(lc: float) -> str:
    abs_lc = abs(lc)
    for threshold, msg in _APCA_NOTES:
        if abs_lc >= threshold:
            return msg
    return "|Lc| < 15: contraste muito baixo ate para elementos visuais simples"


def _rgb_to_cielab(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    r, g, b = (srgb_to_linear(c) for c in rgb)
    x = (0.4124564 * r + 0.3575761 * g + 0.1804375 * b) / 0.95047
    y = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
    z = (0.0193339 * r + 0.1191920 * g + 0.9503041 * b) / 1.08883
    eps, kappa = 0.008856, 903.3

    def f(t: float) -> float:
        return t ** (1.0 / 3.0) if t > eps else (kappa * t + 16.0) / 116.0

    fx, fy, fz = f(x), f(y), f(z)
    return 116.0 * fy - 16.0, 500.0 * (fx - fy), 200.0 * (fy - fz)


def delta_e_lab(c1: tuple[int, int, int], c2: tuple[int, int, int]) -> float:
    l1, a1, b1 = _rgb_to_cielab(c1)
    l2, a2, b2 = _rgb_to_cielab(c2)
    return math.sqrt((l1 - l2) ** 2 + (a1 - a2) ** 2 + (b1 - b2) ** 2)


def _search_lightness(
    bg_rgb: tuple[int, int, int],
    l_low: float,
    l_high: float,
    chroma: float,
    hue: float,
    target_ratio: float,
    darker: bool,
    taper_chroma_from: float | None = None,
) -> tuple[int, int, int] | None:
    def cand_at(lightness: float) -> tuple[int, int, int]:
        eff_c = chroma
        if taper_chroma_from is not None and taper_chroma_from > 0:
            if darker:
                eff_c = chroma * max(0.0, min(1.0, lightness / taper_chroma_from))
            else:
                denom = max(1e-6, 1.0 - taper_chroma_from)
                eff_c = chroma * max(0.0, min(1.0, (1.0 - lightness) / denom))
        return oklch_to_rgb(lightness, eff_c, hue)

    best: tuple[int, int, int] | None = None
    lo, hi = l_low, l_high
    for _ in range(36):
        mid = (lo + hi) / 2.0
        rgb = cand_at(mid)
        ok = wcag_contrast_ratio(rgb, bg_rgb) >= target_ratio
        if ok:
            best = rgb
            if darker:
                lo = mid  # aproxima do original (mais claro dentro do escuro)
            else:
                hi = mid  # aproxima do original (mais escuro dentro do claro)
        elif darker:
            hi = mid
        else:
            lo = mid
    if best is None:
        edge = cand_at(l_low if darker else l_high)
        if wcag_contrast_ratio(edge, bg_rgb) >= target_ratio:
            return edge
    return best


def suggest_contrast_fix(
    fg_rgb: tuple[int, int, int], bg_rgb: tuple[int, int, int], target_ratio: float
) -> dict[str, Any] | None:
    """Encontra o ajuste minimo na luminosidade OKLCH do primeiro plano para atingir target_ratio sobre bg."""
    if wcag_contrast_ratio(fg_rgb, bg_rgb) >= target_ratio:
        return None
    l0, c0, h0 = rgb_to_oklch(fg_rgb)
    candidates: list[tuple[str, tuple[int, int, int]]] = []
    for direction, lo, hi, darker in (("darker", 0.0, l0, True), ("lighter", l0, 1.0, False)):
        found = _search_lightness(bg_rgb, lo, hi, c0, h0, target_ratio, darker)
        if found is None and c0 > 0:
            found = _search_lightness(bg_rgb, lo, hi, c0, h0, target_ratio, darker, taper_chroma_from=l0)
        if found is not None:
            candidates.append((direction, found))
    if not candidates:
        return None
    direction, best = min(candidates, key=lambda item: delta_e_lab(fg_rgb, item[1]))
    return {
        "hex": rgb_to_hex(best),
        "ratio": round(wcag_contrast_ratio(best, bg_rgb), 2),
        "delta_e": round(delta_e_lab(fg_rgb, best), 2),
        "direction": direction,
    }


def simulate_cvd(rgb: tuple[int, int, int], kind: str) -> tuple[int, int, int]:
    """Simula visao de cores para os 8 tipos padronizados de daltonismo em sRGB linear."""
    matrix = _CVD_MATRICES.get(kind)
    if matrix is None:
        raise ValueError(f"tipo de daltonismo desconhecido: {kind!r}")
    lr, lg, lb = (srgb_to_linear(c) for c in rgb)
    return (
        linear_to_srgb(matrix[0][0] * lr + matrix[0][1] * lg + matrix[0][2] * lb),
        linear_to_srgb(matrix[1][0] * lr + matrix[1][1] * lg + matrix[1][2] * lb),
        linear_to_srgb(matrix[2][0] * lr + matrix[2][1] * lg + matrix[2][2] * lb),
    )


def cvd_contrast_report(fg_rgb: tuple[int, int, int], bg_rgb: tuple[int, int, int]) -> dict[str, dict[str, Any]]:
    """Razao de contraste WCAG aproximada entre fg e bg simulados para todos os 8 tipos de daltonismo."""
    out: dict[str, dict[str, Any]] = {}
    for kind in CVD_TYPES:
        sfg = simulate_cvd(fg_rgb, kind)
        sbg = simulate_cvd(bg_rgb, kind)
        out[kind] = {
            "foreground": rgb_to_hex(sfg),
            "background": rgb_to_hex(sbg),
            "ratio": round(wcag_contrast_ratio(sfg, sbg), 2),
        }
    return out
