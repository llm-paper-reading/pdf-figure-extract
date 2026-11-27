#!/usr/bin/env python3
"""
Anchor-based safe extractor:
- locate "Figure N:" caption on a given page,
- narrow to the figure area above the caption by union of image/vector rects,
- render at configurable DPI, then inject a 1.2% margin matching the chosen background.

Usage:
  python extract_fig.py <pdf> <page_1based> <fig_num> <out.png> [--dpi 300] [--margin-pt 20]
                        [--background auto|white|transparent]
"""
import argparse
import os
import re
import sys

import fitz
import numpy as np
from PIL import Image, ImageOps

# -I / -P 下脚本所在目录不会进入 sys.path，显式加入以便导入同目录的 bgutil。
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))

import bgutil


def find_caption(page, num):
    pat = re.compile(rf'^\s*Figure\s+{num}\s*[:.;]')
    caps = []
    for b in page.get_text('dict').get('blocks', []):
        for l in b.get('lines', []):
            s = ''.join(sp.get('text', '') for sp in l.get('spans', []))
            if pat.match(s):
                caps.append(fitz.Rect(b['bbox']))
                break
    return caps


def get_draw_and_image_rects(page):
    rects = []
    for b in page.get_text('dict').get('blocks', []):
        if b.get('type') == 1:  # image
            rects.append(fitz.Rect(b['bbox']))
    try:
        for d in page.get_drawings():
            r = d.get('rect')
            if r and r.width > 5 and r.height > 5:
                rects.append(fitz.Rect(r))
    except Exception:
        pass
    return rects


def union(rects):
    r = fitz.Rect(rects[0])
    for q in rects[1:]:
        r |= q
    return r


def figure_clip(page, cap, margin_pt=20):
    """Union of image/vector rects above the caption; pad; stop just above caption."""
    pr = page.rect
    rects = get_draw_and_image_rects(page)
    above = [r for r in rects if r.y1 <= cap.y0 + 2]
    if not above:
        above = [r for r in rects if r.y1 < cap.y0 + cap.height * 0.5] or rects
    if not above:
        raise RuntimeError('no image/vector content above caption')
    u = union(above)
    # 图内文字（图例、轴标签）是 TXT 块，不在 drawings 里——把「贴着图区底部与 caption 之间的
    # 文本行」也并入，否则 clip 会切掉图例（如 FlashAttention Figure 1 的 "Inner Loop" 标签）。
    gap = fitz.Rect(u.x0, u.y1, u.x1, cap.y0)
    if gap.height > 0:
        for b in page.get_text('dict').get('blocks', []):
            if b.get('type', 0) != 0:
                continue
            for l in b.get('lines', []):
                r = fitz.Rect(l['bbox'])
                if r.y0 >= u.y1 - 1 and r.y1 <= cap.y0 + 1 and gap.intersects(r):
                    u |= r
    return fitz.Rect(max(pr.x0, u.x0 - margin_pt),
                     max(pr.y0, u.y0 - margin_pt),
                     min(pr.x1, u.x1 + margin_pt),
                     min(pr.y1, min(u.y1 + margin_pt, cap.y0 - 1)))


def borders(im):
    """Background-aware edge ink: estimate the corner color, count deviations."""
    a = np.asarray(im.convert('RGB')).astype(int)
    corner = a[2, 2]
    ink = (np.abs(a - corner).sum(axis=-1) > 24)
    h, w = ink.shape
    band = max(4, int(min(h, w) * 0.01))
    return [ink[:band, :].mean(), ink[-band:, :].mean(),
            ink[:, :band].mean(), ink[:, -band:].mean()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pdf'); ap.add_argument('page', type=int)
    ap.add_argument('fig'); ap.add_argument('out')
    ap.add_argument('--dpi', type=int, default=300)
    ap.add_argument('--margin-pt', type=float, default=20)
    ap.add_argument('--clip', type=str, default=None,
                    help='explicit clip rect x0,y0,x1,y1 in pt (for two-column pages)')
    ap.add_argument('--background', choices=bgutil.MODES, default='auto',
                    help='auto (default): keep a painted dark background, otherwise white; '
                         'white forces white; transparent keeps an alpha channel')
    args = ap.parse_args()

    doc = fitz.open(args.pdf)
    page = doc.load_page(args.page - 1)
    if args.clip:
        clip = fitz.Rect(*[float(v) for v in args.clip.split(',')])
    else:
        caps = find_caption(page, args.fig)
        if not caps:
            sys.exit(f'ERROR: no caption "Figure {args.fig}:" on page {args.page}')
        cap = caps[0]
        if len(caps) > 1:
            print(f'note: {len(caps)} captions matched; using first {cap}', file=sys.stderr)
        clip = figure_clip(page, cap, margin_pt=args.margin_pt)

    zoom = args.dpi / 72.0
    info = bgutil.analyze(page, clip)
    bg = bgutil.resolve(args.background, info)
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=clip, alpha=True)
    im = Image.frombytes('RGBA', (pix.width, pix.height), pix.samples)
    border = max(10, int(im.width * 0.012))  # 1.2% border, colored to match the background
    transparent = bg == 'transparent'
    if transparent:
        im = ImageOps.expand(im, border=border, fill=(0, 0, 0, 0))
    else:
        if bg == 'keep':
            px = im.getpixel((0, 0))
            fill = px[:3] if px[3] > 0 else bgutil.WHITE
        else:
            fill = bgutil.COLORS[bg]
        flat = Image.alpha_composite(Image.new('RGBA', im.size, fill + (255,)), im).convert('RGB')
        im = ImageOps.expand(flat, border=border, fill=fill)
    os.makedirs(os.path.dirname(args.out) or '.', exist_ok=True)
    im.save(args.out, optimize=True)
    if transparent:
        print(f'{args.out}: size={im.size} clip={tuple(round(v, 1) for v in clip)} '
              f'{bgutil.describe(bg, info)} borders=n/a (transparent)')
        return
    scores = borders(im)
    tag = 'OK' if max(scores) < 0.003 else 'WARN'
    print(f'{args.out}: size={im.size} clip={tuple(round(v, 1) for v in clip)} '
          f'borders={["%.5f" % x for x in scores]} {tag} {bgutil.describe(bg, info)}')
    warn = bgutil.contrast_warning(bg, info, args.background)
    if warn:
        print(f'WARN {warn}', file=sys.stderr)
    if tag == 'WARN':
        sys.exit(3)


if __name__ == '__main__':
    main()
