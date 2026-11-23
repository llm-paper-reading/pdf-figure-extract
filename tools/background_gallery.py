#!/usr/bin/env python3
"""Build a visual gallery to review `--background auto` decisions.

Manifest format (one entry per line, # comments allowed):

    /path/to/paper.pdf  2  1
    /path/to/paper.pdf  10 4  57.8,366,554.2,700

The fourth field is an optional `--clip x0,y0,x1,y1`. Relative PDF paths are
resolved against the manifest's directory.

Each entry is extracted to SVG, then rendered on a white and a dark backdrop
so light ink that would vanish on white (and dark ink that would vanish on
dark) is obvious at a glance.

    python tools/background_gallery.py manifest.txt --out /tmp/auto-gallery
    python -m http.server -d /tmp/auto-gallery 8000
"""
import argparse
import html
import re
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "pdf-figure-extract" / "scripts"
WHITE = (255, 255, 255)
DARK = (15, 23, 42)


def parse_manifest(path):
    entries = []
    for lineno, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 3:
            sys.exit(f"{path}:{lineno}: expected: <pdf> <page> <fig> [clip]")
        pdf = Path(parts[0])
        if not pdf.is_absolute():
            pdf = (Path(path).resolve().parent / pdf).resolve()
        entries.append({
            "pdf": pdf,
            "page": parts[1],
            "fig": parts[2],
            "clip": parts[3] if len(parts) > 3 else None,
        })
    return entries


def slug(entry):
    base = re.sub(r"[^A-Za-z0-9._-]+", "-", entry["pdf"].stem).strip("-") or "fig"
    name = f"{base}-p{entry['page']}-f{entry['fig']}"
    if entry["clip"]:
        name += "-clip"
    return name


def checkerboard(size, square=16):
    """RGBA checkerboard used to reveal transparency in an SVG."""
    w, h = size
    yy, xx = np.indices((h, w))
    mask = ((xx // square) + (yy // square)) % 2 == 1
    arr = np.full((h, w, 4), 255, dtype=np.uint8)
    arr[mask] = (148, 163, 184, 255)  # 深浅交错，透明区域一眼可见
    return Image.fromarray(arr, "RGBA")


def render_on(svg, out, background, width):
    tmp = out.with_suffix(".tmp.png")
    rc = subprocess.run(["rsvg-convert", "-w", str(width), str(svg), "-o", str(tmp)],
                        capture_output=True, text=True, check=False)
    if rc.returncode != 0:
        raise RuntimeError(rc.stderr.strip() or "rsvg-convert failed")
    im = Image.open(tmp).convert("RGBA")
    canvas = Image.new("RGBA", im.size, background + (255,))
    Image.alpha_composite(canvas, im).convert("RGB").save(out, optimize=True)
    tmp.unlink()


def render_checker(svg, out, width):
    tmp = out.with_suffix(".tmp.png")
    rc = subprocess.run(["rsvg-convert", "-w", str(width), str(svg), "-o", str(tmp)],
                        capture_output=True, text=True, check=False)
    if rc.returncode != 0:
        raise RuntimeError(rc.stderr.strip() or "rsvg-convert failed")
    im = Image.open(tmp).convert("RGBA")
    canvas = checkerboard(im.size)
    Image.alpha_composite(canvas, im).convert("RGB").save(out, optimize=True)
    tmp.unlink()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("manifest")
    ap.add_argument("--out", default="/tmp/auto-gallery")
    ap.add_argument("--background", default="auto",
                    choices=("auto", "white", "dark", "transparent"))
    ap.add_argument("--width", type=int, default=1400)
    ap.add_argument("--strict", action="store_true", help="exit 1 if any entry fails")
    args = ap.parse_args()

    if not shutil.which("rsvg-convert"):
        sys.exit("rsvg-convert not found (brew install librsvg)")
    entries = parse_manifest(args.manifest)
    if not entries:
        sys.exit("manifest is empty")

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    cards, failures = [], 0

    for entry in entries:
        name = slug(entry)
        d = outdir / name
        d.mkdir(parents=True, exist_ok=True)
        svg = d / "extracted.svg"
        cmd = [sys.executable, str(SCRIPTS / "extract_svg.py"),
               str(entry["pdf"]), entry["page"], entry["fig"], str(svg),
               "--background", args.background]
        if entry["clip"]:
            cmd += ["--clip", entry["clip"]]
        r = subprocess.run(cmd, capture_output=True, text=True, check=False)
        log = (r.stdout + r.stderr).strip()
        (d / "log.txt").write_text(log + "\n", encoding="utf-8")
        m = re.search(r"background=(\w+)", log)
        bg = m.group(1) if m else "failed"
        pair = ""
        note = ""
        if r.returncode == 0 and svg.exists():
            try:
                render_on(svg, d / "on-white.png", WHITE, args.width)
                render_on(svg, d / "on-dark.png", DARK, args.width)
                render_checker(svg, d / "on-checker.png", args.width)
                if bg == "transparent":
                    note = "SVG 画布透明：棋盘格透出，切换白底/深底可见明显差异"
                elif bg in ("white", "dark", "keep"):
                    note = "SVG 自带不透明底色：切换白底/深底看到的是同一块底色"
                pair = (
                    '<div class="previews">'
                    f'<figure class="preview" data-bg="white"><figcaption>白底</figcaption>'
                    f'<img src="{name}/on-white.png" alt="white background"></figure>'
                    f'<figure class="preview" data-bg="dark"><figcaption>深底</figcaption>'
                    f'<img src="{name}/on-dark.png" alt="dark background"></figure>'
                    f'<figure class="preview" data-bg="checker"><figcaption>棋盘格（透明检查）</figcaption>'
                    f'<img src="{name}/on-checker.png" alt="checkerboard"></figure>'
                    "</div>"
                )
            except Exception as e:  # noqa: BLE001 - report and keep going
                log += f"\nrender failed: {e}"
                bg = "failed"
        if bg == "failed":
            failures += 1
        clip = f" clip={entry['clip']}" if entry["clip"] else ""
        cards.append(f'''<section class="card">
<h2>{html.escape(name)} <span class="badge {bg}">{html.escape(bg)}</span></h2>
<p class="meta">page {html.escape(entry["page"])} · fig {html.escape(entry["fig"])}{html.escape(clip)} · {html.escape(str(entry["pdf"]))}</p>
<p class="note">{html.escape(note)}</p>
{pair}
<details><summary>extractor log</summary><pre>{html.escape(log)}</pre></details>
</section>''')

    page = f'''<!doctype html>
<html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Auto background gallery</title>
<style>
:root {{ color-scheme: light dark; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        margin: 24px; max-width: 1200px; }}
h1 {{ font-size: 20px; }}
.card {{ border: 1px solid #8884; border-radius: 12px; padding: 16px; margin: 20px 0; }}
h2 {{ font-size: 15px; margin: 0 0 6px; font-family: ui-monospace, monospace; }}
.meta {{ font-size: 12px; opacity: .7; margin: 0 0 12px; word-break: break-all; }}
.pair, .previews {{ display: grid; grid-template-columns: 1fr; gap: 12px; }}
.preview {{ display: none; margin: 0; padding: 8px; border-radius: 8px; background: #fff; color: #111; }}
.preview[data-bg="dark"] {{ background: #0f172a; color: #eee; }}
.preview[data-bg="checker"] {{ background: #f8fafc; color: #111; }}
body[data-bg="white"] .preview[data-bg="white"],
body[data-bg="dark"] .preview[data-bg="dark"],
body[data-bg="checker"] .preview[data-bg="checker"] {{ display: block; }}
.controls {{ display: flex; gap: 8px; margin: 12px 0; position: sticky; top: 0;
             padding: 10px 0; background: Canvas; z-index: 2; }}
.controls button {{ font: inherit; padding: 6px 14px; border-radius: 8px;
                    border: 1px solid #8886; background: #8881; color: inherit; cursor: pointer; }}
.controls button.active {{ background: #2563eb; border-color: #2563eb; color: #fff; }}
figure {{ margin: 0; padding: 8px; border-radius: 8px; background: #fff; color: #111; }}
figure.dark {{ background: #0f172a; color: #eee; }}
figcaption {{ font-size: 12px; margin-bottom: 6px; }}
img {{ width: 100%; height: auto; display: block; }}
.badge {{ font-size: 11px; padding: 2px 8px; border-radius: 999px; background: #8884; }}
.badge.white {{ background: #e5e7eb; color: #111; }}
.badge.dark {{ background: #1e293b; color: #eee; }}
.badge.keep {{ background: #d1fae5; color: #064e3b; }}
.badge.transparent {{ background: #fef3c7; color: #78350f; }}
.badge.failed {{ background: #fee2e2; color: #7f1d1d; }}
pre {{ overflow: auto; font-size: 12px; }}
</style></head>
<body data-bg="white">
<h1>自动背景判定画廊</h1>
<p>共 {len(entries)} 项，失败 {failures} 项。用顶部按钮切换白底 / 深底 / 棋盘格。白底与深底看起来相同，说明 SVG 已自带不透明底色；棋盘格透出，说明画布透明。</p>
<div class="controls">
<button data-set="white" class="active">白底</button>
<button data-set="dark">深底</button>
<button data-set="checker">棋盘格</button>
</div>
{"".join(cards)}
<script>
const buttons = [...document.querySelectorAll('.controls button')];
function setBg(bg) {{
  document.body.dataset.bg = bg;
  buttons.forEach(b => b.classList.toggle('active', b.dataset.set === bg));
}}
buttons.forEach(b => b.addEventListener('click', () => setBg(b.dataset.set)));
</script>
</body></html>'''
    (outdir / "gallery.html").write_text(page, encoding="utf-8")
    print(f"{len(entries)} entries, {failures} failed -> {outdir / 'gallery.html'}")
    if failures and args.strict:
        sys.exit(1)


if __name__ == "__main__":
    main()
