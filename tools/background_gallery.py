#!/usr/bin/env python3
"""Build a visual gallery to review `--background auto` decisions.

Manifest format (one entry per line, # comments allowed):

    /path/to/paper.pdf  2  1
    /path/to/paper.pdf  10 4  57.8,366,554.2,700

The fourth field is an optional `--clip x0,y0,x1,y1`. Relative PDF paths are
resolved against the manifest's directory.

Each entry is extracted three ways: SVG with the selected background, a forced
transparent SVG for comparison, and a PNG. They are embedded directly in the
page. The top buttons switch the page theme (light / dark) and the output shown
(SVG / transparent SVG / PNG / side by side): transparent areas show the page
background, while baked backgrounds keep their own color. That is the
difference a reader sees on a light or dark site.

    python tools/background_gallery.py manifest.txt --out /tmp/auto-gallery
    python -m http.server -d /tmp/auto-gallery 8000
"""
import argparse
import html
import re
import subprocess
import sys
from pathlib import Path

import fitz
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "pdf-figure-extract" / "scripts"

sys.path.insert(0, str(SCRIPTS))
import bgutil


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


def _filename(fmt):
    return {"svg": "extracted.svg", "transparent": "transparent.svg",
            "png": "extracted.png"}[fmt]


def parse_clip(log):
    m = re.search(r"clip=\(([^)]+)\)", log)
    if not m:
        return None
    values = [float(v) for v in m.group(1).split(",")]
    return fitz.Rect(*values) if len(values) == 4 else None


def inspect_source(entry, clip):
    """Properties of the original PDF figure: content mix and painted background."""
    doc = fitz.open(str(entry["pdf"]))
    page = doc.load_page(int(entry["page"]) - 1)
    blocks = page.get_text("dict", clip=clip).get("blocks", [])
    lines = sum(len(b.get("lines", [])) for b in blocks if b.get("type", 0) == 0)
    drawings = sum(1 for d in page.get_drawings()
                   if fitz.Rect(d["rect"]).intersects(clip))
    images = []
    for info in page.get_images(full=True):
        try:
            r = page.get_image_bbox(info)
        except Exception:  # noqa: BLE001, S112 - damaged/odd image entries
            continue
        if r and fitz.Rect(r).intersects(clip):
            images.append((info[2], info[3]))
    bg = bgutil.analyze(page, clip)
    return {
        "clip": clip,
        "lines": lines,
        "drawings": drawings,
        "images": images,
        "bg": bg,
        "bg_kind": bg_kind(bg),
    }


def bg_kind(bg):
    if bg["opaque"] < 0.5:
        return "透明画布"
    luma = bg.get("bg_luma")
    if luma is not None and luma < 0.35:
        return "自带深色底"
    if luma is not None and luma > 0.9:
        return "自带白色底"
    return "彩色 / 混合底"


def explain_background(requested, bg):
    """Mirror bgutil.resolve() and spell out which branch fired."""
    if requested != "auto":
        return f"手动指定 --background={requested}"
    opaque = bg["opaque"]
    luma = bg.get("bg_luma")
    if opaque >= 0.5:
        if luma is not None and luma < 0.35:
            return (f"不透明 {opaque:.2f} ≥ 0.50，背景亮度 {luma:.2f} < 0.35 "
                    f"→ keep（保留论文深色底）")
        shown = "n/a" if luma is None else f"{luma:.2f}"
        return (f"不透明 {opaque:.2f} ≥ 0.50，背景亮度 {shown} ≥ 0.35 "
                f"→ white（图自带浅色底）")
    dark, light = bg.get("dark", 0.0), bg.get("light", 0.0)
    if dark < 0.05 and light > 0.5:
        return (f"不透明 {opaque:.2f} < 0.50，暗墨 {dark:.2f} < 0.05、"
                f"亮墨 {light:.2f} > 0.50 → dark")
    if dark >= 0.05:
        return (f"不透明 {opaque:.2f} < 0.50，暗墨 {dark:.2f} ≥ 0.05 "
                f"→ white（透明画布默认）")
    return (f"不透明 {opaque:.2f} < 0.50，亮墨 {light:.2f} ≤ 0.50 "
            f"→ white（透明画布默认）")


def svg_meta(path):
    text = path.read_text(encoding="utf-8")
    m = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', text)
    size = (round(float(m.group(1)), 1), round(float(m.group(2)), 1)) if m else None
    return {
        "bytes": path.stat().st_size,
        "size": size,
        "images": text.count("<image"),
        "colors": len(set(re.findall(r'fill="([^"]+)"', text))),
    }


def png_meta(path):
    with Image.open(path) as im:
        return {"mode": im.mode, "size": im.size, "bytes": path.stat().st_size}


def props_html(meta):
    bg = meta["bg"]
    images = meta["images"]
    if images:
        counts = {}
        for w, h in images:
            counts[(w, h)] = counts.get((w, h), 0) + 1
        image_text = "、".join(f"{w}×{h}" + (f" ×{n}" if n > 1 else "")
                               for (w, h), n in sorted(counts.items()))
    else:
        image_text = "无"
    clip = meta["clip"]

    def num(value):
        return "n/a" if value is None else f"{value:.2f}"

    rows = [
        ("图区尺寸", (f"{clip.width:.1f}×{clip.height:.1f} pt · "
                      f"{clip.width / 72:.2f}×{clip.height / 72:.2f} in")),
        ("图内内容", f"文本行 {meta['lines']} · 矢量绘图 {meta['drawings']} · 内嵌位图对象 {len(images)}"),
        ("内嵌位图像素", image_text),
        ("背景判定", (f"{meta['bg_kind']} · 不透明 {bg['opaque']:.2f} · "
                      f"透明 {1 - bg['opaque']:.2f}")),
        ("背景亮度 / 墨色", f"{num(bg.get('bg_luma'))} / {num(bg.get('ink'))}"),
        ("暗墨 / 亮墨占比", f"{bg.get('dark', 0):.2f} / {bg.get('light', 0):.2f}"),
    ]
    body = "".join(
        f'<div class="chip"><span class="k">{html.escape(k)}</span>'
        f'<span class="v">{html.escape(str(v))}</span></div>'
        for k, v in rows)
    return (f'<section class="source"><h3>PDF 原图属性</h3>'
            f'<div class="chips">{body}</div></section>')


def connector_html():
    """Three arrows aligning with the preview columns."""
    arrows = "".join(f'<span class="arrow arrow-{fmt}"></span>'
                     for fmt in ("svg", "transparent", "png"))
    return f'<div class="connector" aria-hidden="true">{arrows}</div>'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("manifest")
    ap.add_argument("--out", default="/tmp/auto-gallery")
    ap.add_argument("--background", default="auto",
                    choices=("auto", "white", "dark", "transparent"))
    ap.add_argument("--dpi", type=int, default=200, help="PNG 预览的渲染 dpi（默认 200）")
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
        clip_args = ["--clip", entry["clip"]] if entry["clip"] else []
        results = {}
        for fmt, script, path, bg_mode in (
            ("svg", "extract_svg.py", d / "extracted.svg", args.background),
            ("transparent", "extract_svg.py", d / "transparent.svg", "transparent"),
            ("png", "extract_fig.py", d / "extracted.png", args.background),
        ):
            cmd = [sys.executable, str(SCRIPTS / script),
                   str(entry["pdf"]), entry["page"], entry["fig"], str(path),
                   "--background", bg_mode, *clip_args]
            if fmt == "png":
                cmd += ["--dpi", str(args.dpi)]
            r = subprocess.run(cmd, capture_output=True, text=True, check=False)
            log = (r.stdout + r.stderr).strip()
            (d / f"log-{fmt}.txt").write_text(log + "\n", encoding="utf-8")
            m = re.search(r"background=(\w+)", log)
            results[fmt] = {
                "ok": r.returncode == 0 and path.exists(),
                "bg": m.group(1) if m else "failed",
                "log": log,
            }
        bg = results["svg"]["bg"] if results["svg"]["ok"] else results["png"]["bg"]
        failed = [fmt.upper() for fmt in ("svg", "transparent", "png") if not results[fmt]["ok"]]
        if failed:
            failures += 1

        svg_infos = {}
        for fmt in ("svg", "transparent"):
            if results[fmt]["ok"]:
                svg_infos[fmt] = svg_meta(d / _filename(fmt))
        png_info = png_meta(d / "extracted.png") if results["png"]["ok"] else None

        figures = []
        for fmt, label in (
            ("svg", f"SVG（background={args.background}）"),
            ("transparent", "SVG（background=transparent）"),
            ("png", f"PNG（background={args.background} · {args.dpi} dpi）"),
        ):
            if results[fmt]["ok"]:
                body = (f'<img src="{name}/{_filename(fmt)}" '
                        f'alt="{html.escape(name)} {fmt}">')
            else:
                body = '<p class="note">抽取失败</p>'
            cap = []
            if fmt in svg_infos:
                info = svg_infos[fmt]
                sw, sh = info["size"] or (0, 0)
                cap = [
                    f"{info['bytes'] / 1024:.1f} KB · {sw}×{sh} pt",
                    f"内嵌位图 {info['images']} · 填充色 {info['colors']}",
                    f"background={results[fmt]['bg']}",
                ]
            elif fmt == "png" and png_info:
                cap = [
                    (f"{png_info['bytes'] / 1024:.1f} KB · "
                     f"{png_info['size'][0]}×{png_info['size'][1]} px · {png_info['mode']}"),
                    f"{args.dpi} dpi",
                    f"background={results[fmt]['bg']}",
                ]
            cap_html = "".join(f'<span class="cap">{html.escape(x)}</span>' for x in cap)
            figures.append(f'<figure class="preview fmt-{fmt}">{body}'
                           f'<figcaption><b>{label}</b>{cap_html}</figcaption></figure>')

        if results["svg"]["ok"]:
            if bg == "transparent":
                note = "输出画布透明：切到深色页面会透出深色底，黑色文字可能看不清"
            else:
                note = "输出已带不透明底色：切到深色页面时图仍保持自身底色"
            if results["transparent"]["ok"]:
                note += "；透明底一列用于对照，切到 Dark 时差异最明显"
        else:
            note = f"抽取失败：{', '.join(failed)}，详见下方日志"

        clip = f" clip={entry['clip']}" if entry["clip"] else ""
        logs = "\n\n".join(f"[{fmt.upper()}]\n{results[fmt]['log']}"
                           for fmt in ("svg", "transparent", "png"))

        props = ""
        why = ""
        clip_rect = parse_clip(results["svg"]["log"]) or parse_clip(results["png"]["log"])
        if clip_rect is not None:
            try:
                src = inspect_source(entry, clip_rect)
                props = props_html(src)
                why = explain_background(args.background, src["bg"])
            except Exception as e:  # noqa: BLE001 - metadata must not break the page
                props = f'<p class="note">属性读取失败：{html.escape(str(e))}</p>'
        cards.append(f'''<section class="card">
<h2>{html.escape(name)} <span class="badge {bg}">{html.escape(bg)}</span></h2>
<p class="meta">page {html.escape(entry["page"])} · fig {html.escape(entry["fig"])}{html.escape(clip)} · {html.escape(str(entry["pdf"]))}</p>
{props}
<p class="decision"><b>background 判定：</b>{html.escape(why)}</p>
{connector_html()}
<div class="previews">{"".join(figures)}</div>
<p class="note">{html.escape(note)}</p>
<details><summary>extractor log</summary><pre>{html.escape(logs)}</pre></details>
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
figcaption {{ font-size: 12px; margin-top: 8px; opacity: .8; }}
figcaption .cap {{ display: block; font-size: 11px; margin-top: 2px;
                   font-family: ui-monospace, monospace; opacity: .8; }}
.previews {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }}
@media (max-width: 1000px) {{ .previews {{ grid-template-columns: 1fr; }} }}
.sep {{ width: 1px; align-self: stretch; background: #8884; margin: 0 6px; }}
img {{ width: 100%; height: auto; display: block; }}
.controls {{ display: flex; gap: 8px; margin: 12px 0; position: sticky; top: 0;
             padding: 10px 0; background: inherit; z-index: 2; }}
.controls button {{ font: inherit; padding: 6px 14px; border-radius: 8px;
                    border: 1px solid #8886; background: #8881; color: inherit; cursor: pointer; }}
body[data-theme="dark"] .controls button {{ background: #ffffff14; border-color: #ffffff33; }}
.controls button.active {{ background: #2563eb; border-color: #2563eb; color: #fff; }}
.rules {{ margin: 14px 0; padding: 12px 16px; border: 1px solid #8884; border-radius: 10px; font-size: 13px; }}
.rules ol {{ margin: 6px 0 0 18px; padding: 0; }}
.rules li {{ margin: 3px 0; }}
.rules code {{ font-family: ui-monospace, monospace; }}
.decision {{ margin: 10px auto 0; max-width: 980px; padding: 8px 12px; border-radius: 8px;
             background: #2563eb14; font-size: 12px; text-align: center; }}
body[data-theme="dark"] .decision {{ background: #2563eb2a; }}
.badge {{ font-size: 11px; padding: 2px 8px; border-radius: 999px; background: #8884; }}
.badge.white {{ background: #e5e7eb; color: #111; }}
.badge.dark {{ background: #1e293b; color: #eee; }}
.badge.keep {{ background: #d1fae5; color: #064e3b; }}
.badge.transparent {{ background: #fef3c7; color: #78350f; }}
.badge.failed {{ background: #fee2e2; color: #7f1d1d; }}
pre {{ overflow: auto; font-size: 12px; }}
.source {{ margin: 14px auto 0; max-width: 1100px; padding: 16px 18px;
          border: 1px solid #2563eb40; border-radius: 12px;
          background: linear-gradient(180deg, #2563eb12, #2563eb04); }}
body[data-theme="dark"] .source {{ background: linear-gradient(180deg, #2563eb24, #2563eb0a); }}
.source h3 {{ margin: 0 0 12px; font-size: 13px; font-weight: 600; text-align: center; }}
.chips {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px 22px; }}
@media (max-width: 760px) {{ .chips {{ grid-template-columns: 1fr; }} }}
.chip {{ border-bottom: 1px dashed #8883; padding-bottom: 4px; min-width: 0; }}
.chip .k {{ display: block; font-size: 11px; opacity: .6; margin-bottom: 2px; }}
.chip .v {{ display: block; font-size: 12px; font-family: ui-monospace, monospace; overflow-wrap: anywhere; }}
.connector {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin: 4px 0 8px; }}
@media (max-width: 1000px) {{ .connector {{ grid-template-columns: 1fr; }} }}
.arrow {{ display: flex; justify-content: center; height: 30px; position: relative; }}
.arrow::before {{ content: ""; width: 2px; height: 20px; background: #2563eb; }}
.arrow::after {{ content: ""; position: absolute; top: 18px;
                 border: 6px solid transparent; border-top-color: #2563eb; }}
</style></head>
<body data-theme="light">
<h1>自动背景判定画廊</h1>
<p>共 {len(entries)} 项，失败 {failures} 项。顶部切换页面主题（Light / Dark）；三列固定并排。本次生成使用 <code>--background={args.background}</code>：第一列 SVG 与第三列 PNG 都按该模式抽取，第二列固定 <code>transparent</code> 作对照。</p>
<div class="controls">
<button data-set="light" class="active">Light</button>
<button data-set="dark">Dark</button>
</div>
<section class="rules">
<strong>auto 背景判定规则</strong>
<ol>
<li>不透明 ≥ 0.50：背景亮度 &lt; 0.35 → <code>keep</code>（保留论文深色底）；否则 <code>white</code>。</li>
<li>不透明 &lt; 0.50：暗墨 &lt; 5% 且亮墨 &gt; 50% → <code>dark</code>；否则 <code>white</code>（透明画布默认）。</li>
</ol>
</section>
{"".join(cards)}
<script>
const themeButtons = [...document.querySelectorAll('.controls button[data-set]')];
function setTheme(theme) {{
  document.body.dataset.theme = theme;
  themeButtons.forEach(b => b.classList.toggle('active', b.dataset.set === theme));
}}
themeButtons.forEach(b => b.addEventListener('click', () => setTheme(b.dataset.set)));
</script>
</body></html>'''
    (outdir / "gallery.html").write_text(page, encoding="utf-8")
    print(f"{len(entries)} entries, {failures} failed -> {outdir / 'gallery.html'}")
    if failures and args.strict:
        sys.exit(1)


if __name__ == "__main__":
    main()
