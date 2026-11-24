#!/usr/bin/env python3
"""Background decision for extracted figures.

Samples the clipped region with alpha to answer two questions:
- does the figure already paint its own dark background?
- if not, the safe default is white, because papers are authored for white paper.

`auto` therefore returns `keep` or `white` only. Transparent output is
available explicitly for pages/slides whose own background should show through.
"""
import re
from pathlib import Path

import fitz
import numpy as np

WHITE = (255, 255, 255)
COLORS = {"white": WHITE}
HEX = {"white": "#ffffff"}
MODES = ("auto", "white", "transparent")


def analyze(page, clip, zoom=0.5):
    """Return {'opaque': ratio of fully opaque pixels, 'ink': alpha-weighted mean luma}.
    Transparent paper means the PDF does not paint a background."""
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=clip, alpha=True)
    arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    if pix.n == 4:
        a = arr[..., 3].astype(np.float32) / 255.0
        rgb = arr[..., :3].astype(np.float32) / 255.0
    else:  # pragma: no cover - alpha=True always yields RGBA here
        a = np.ones(arr.shape[:2], dtype=np.float32)
        rgb = arr[..., :3].astype(np.float32) / 255.0
    opaque = float((a > 0.99).mean())
    ink_mask = a > 0.15
    if not ink_mask.any():
        return {"opaque": opaque, "ink": None, "dark": 0.0, "light": 0.0, "bg_luma": None}
    luma = 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]
    weight = a[ink_mask]
    vals = luma[ink_mask]
    ink = float((vals * weight).sum() / weight.sum())
    dark = float((vals < 0.35).mean())
    light = float((vals > 0.70).mean())
    op = a > 0.5
    bg_luma = float(np.median(luma[op])) if op.any() else None
    return {"opaque": opaque, "ink": ink, "dark": dark, "light": light, "bg_luma": bg_luma}


def resolve(mode, info):
    """Turn `auto` into keep or white.

    Academic figures are authored for white paper, so white is the safe
    default. A figure that paints a dark background keeps it. For dark-themed
    sites, use `transparent` and let the page background show through.
    """
    if mode != "auto":
        return mode
    opaque = info["opaque"]
    if opaque >= 0.5:
        if info.get("bg_luma") is not None and info["bg_luma"] < 0.35:
            return "keep"
        return "white"
    return "white"


def describe(mode, info):
    ink = "n/a" if info["ink"] is None else f"{info['ink']:.2f}"
    return f"background={mode} (ink_luma={ink}, opaque={info['opaque']:.2f})"


def contrast_warning(mode, info, requested):
    """Warn only for forced backgrounds; `auto` already picks by ink distribution."""
    if requested == "auto" or mode not in COLORS or info["ink"] is None:
        return None
    bg = np.dot(np.array(COLORS[mode], dtype=float) / 255.0, [0.2126, 0.7152, 0.0722])
    hi, lo = max(bg, info["ink"]), min(bg, info["ink"])
    ratio = (hi + 0.05) / (lo + 0.05)
    if ratio < 3.0:
        return f"contrast {ratio:.1f}:1 (< 3:1), check the output"
    return None


def svg_add_background(path, mode):
    """Paint a full-canvas rect behind the SVG content; no-op for keep/transparent."""
    if mode not in HEX:
        return False
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    root = re.search(r"<svg[^>]*>", text)
    if not root:
        return False
    vb = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', root.group(0))
    if vb:
        w, h = vb.group(1), vb.group(2)
    else:
        wm = re.search(r'width="([\d.]+)', root.group(0))
        hm = re.search(r'height="([\d.]+)', root.group(0))
        if not (wm and hm):
            return False
        w, h = wm.group(1), hm.group(1)
    rect = f'<rect x="0" y="0" width="{w}" height="{h}" fill="{HEX[mode]}"/>'
    path.write_text(text[: root.end()] + "\n" + rect + text[root.end():], encoding="utf-8")
    return True
