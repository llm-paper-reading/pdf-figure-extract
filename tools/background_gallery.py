#!/usr/bin/env python3
"""Build a visual gallery to review `--background auto` decisions.

Manifest format (one entry per line, # comments allowed):

    /path/to/paper.pdf  2  1
    /path/to/paper.pdf  10 4  57.8,366,554.2,700

The fourth field is an optional `--clip x0,y0,x1,y1`. Relative PDF paths are
resolved against the manifest's directory.

Each entry is extracted to SVG and embedded directly in the page. The top
buttons switch the page theme (light / dark / checkerboard): transparent SVG
areas show the page background, while SVGs with a baked background keep their
own color. That is the difference a reader sees on a light or dark site.

    python tools/background_gallery.py manifest.txt --out /tmp/auto-gallery
    python -m http.server -d /tmp/auto-gallery 8000
"""
import argparse
import html
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "pdf-figure-extract" / "scripts"


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


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("manifest")
    ap.add_argument("--out", default="/tmp/auto-gallery")
    ap.add_argument("--background", default="auto",
                    choices=("auto", "white", "dark", "transparent"))
    ap.add_argument("--strict", action="store_true", help="exit 1 if any entry fails")
    args = ap.parse_args()

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
        note, preview = "", ""
        if r.returncode == 0 and svg.exists():
            if bg == "transparent":
                note = "画布透明：切到深色页面会透出深色底，黑色文字可能看不清"
            elif bg in ("white", "dark", "keep"):
                note = "SVG 自带不透明底色：切到深色页面时图仍保持自身底色"
            preview = (f'<figure class="preview"><img src="{name}/extracted.svg" '
                       f'alt="{html.escape(name)}"></figure>')
        else:
            failures += 1
            note = "抽取失败，详见下方日志"
        clip = f" clip={entry['clip']}" if entry["clip"] else ""
        cards.append(f'''<section class="card">
<h2>{html.escape(name)} <span class="badge {bg}">{html.escape(bg)}</span></h2>
<p class="meta">page {html.escape(entry["page"])} · fig {html.escape(entry["fig"])}{html.escape(clip)} · {html.escape(str(entry["pdf"]))}</p>
<p class="note">{html.escape(note)}</p>
{preview}
<details><summary>extractor log</summary><pre>{html.escape(log)}</pre></details>
</section>''')

    page = f'''<!doctype html>
<html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Auto background gallery</title>
<style>
:root {{ color-scheme: light; }}
html {{ background: #fff; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        margin: 24px; max-width: 1200px; background: #fff; color: #111; }}
body[data-theme="dark"] {{ background: #0f172a; color: #e5e7eb; }}
h1 {{ font-size: 20px; }}
.card {{ border: 1px solid #8884; border-radius: 12px; padding: 16px; margin: 20px 0; }}
h2 {{ font-size: 15px; margin: 0 0 6px; font-family: ui-monospace, monospace; }}
.meta {{ font-size: 12px; opacity: .7; margin: 0 0 8px; word-break: break-all; }}
.note {{ font-size: 12px; margin: 0 0 12px; opacity: .85; }}
.preview {{ margin: 0; padding: 12px; border-radius: 8px; background: #fff; }}
body[data-theme="dark"] .preview {{ background: #0f172a; }}
body[data-theme="checker"] .preview {{
  background-color: #fff;
  background-image:
    linear-gradient(45deg, #94a3b8 25%, transparent 25%),
    linear-gradient(-45deg, #94a3b8 25%, transparent 25%),
    linear-gradient(45deg, transparent 75%, #94a3b8 75%),
    linear-gradient(-45deg, transparent 75%, #94a3b8 75%);
  background-size: 24px 24px;
  background-position: 0 0, 0 12px, 12px -12px, -12px 0;
}}
img {{ width: 100%; height: auto; display: block; }}
.controls {{ display: flex; gap: 8px; margin: 12px 0; position: sticky; top: 0;
             padding: 10px 0; background: inherit; z-index: 2; }}
.controls button {{ font: inherit; padding: 6px 14px; border-radius: 8px;
                    border: 1px solid #8886; background: #8881; color: inherit; cursor: pointer; }}
body[data-theme="dark"] .controls button {{ background: #ffffff14; border-color: #ffffff33; }}
.controls button.active {{ background: #2563eb; border-color: #2563eb; color: #fff; }}
.badge {{ font-size: 11px; padding: 2px 8px; border-radius: 999px; background: #8884; }}
.badge.white {{ background: #e5e7eb; color: #111; }}
.badge.dark {{ background: #1e293b; color: #eee; }}
.badge.keep {{ background: #d1fae5; color: #064e3b; }}
.badge.transparent {{ background: #fef3c7; color: #78350f; }}
.badge.failed {{ background: #fee2e2; color: #7f1d1d; }}
pre {{ overflow: auto; font-size: 12px; }}
</style></head>
<body data-theme="light">
<h1>自动背景判定画廊</h1>
<p>共 {len(entries)} 项，失败 {failures} 项。顶部切换页面主题：light / dark / 棋盘格。图片按 SVG 原样嵌入，透明区域会显示页面背景；带底色的 SVG 不随主题变化。</p>
<div class="controls">
<button data-set="light" class="active">Light</button>
<button data-set="dark">Dark</button>
<button data-set="checker">棋盘格</button>
</div>
{"".join(cards)}
<script>
const buttons = [...document.querySelectorAll('.controls button')];
function setTheme(theme) {{
  document.body.dataset.theme = theme;
  buttons.forEach(b => b.classList.toggle('active', b.dataset.set === theme));
}}
buttons.forEach(b => b.addEventListener('click', () => setTheme(b.dataset.set)));
</script>
</body></html>'''
    (outdir / "gallery.html").write_text(page, encoding="utf-8")
    print(f"{len(entries)} entries, {failures} failed -> {outdir / 'gallery.html'}")
    if failures and args.strict:
        sys.exit(1)


if __name__ == "__main__":
    main()
