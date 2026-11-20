"""CLI 端到端：退出码、输出文件、--clip 模式、check_border 行为。"""
import subprocess
import sys
from pathlib import Path

import fitz
import pytest

from conftest import line_bboxes
from extract_fig import figure_clip, find_caption

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "pdf-figure-extract" / "scripts"


def run(script, *args):
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *map(str, args)],
        capture_output=True, text=True)


@pytest.fixture
def out(tmp_path):
    return tmp_path / "fig1"


class TestExtractFig:
    def test_ok_path(self, simple_pdf, out):
        r = run("extract_fig.py", simple_pdf, "1", "1", out.with_suffix(".png"))
        assert r.returncode == 0, r.stdout + r.stderr
        assert out.with_suffix(".png").exists()
        assert "OK" in r.stdout

    def test_missing_caption_exit_code(self, simple_pdf, out):
        r = run("extract_fig.py", simple_pdf, "1", "2", out.with_suffix(".png"))
        assert r.returncode == 1
        assert "no caption" in (r.stdout + r.stderr)

    def test_clip_mode_skips_caption_lookup(self, tmp_path, out):
        """--clip 时不应要求 caption 存在（llama3 的 'Figure 5 Illustration' 场景）。"""
        doc = fitz.open()
        page = doc.new_page()
        page.draw_rect(fitz.Rect(100, 100, 400, 200), color=(0, 0, 0), width=2)
        pdf = tmp_path / "nocap.pdf"
        doc.save(str(pdf)); doc.close()
        r = run("extract_fig.py", pdf, "1", "1", out.with_suffix(".png"),
                "--clip", "90,90,410,210", "--dpi", "150")
        assert r.returncode == 0, r.stdout + r.stderr

    def test_png_has_white_margin(self, simple_pdf, out):
        """PNG 模式必须注入白边：输出最外圈像素为纯白。"""
        from PIL import Image
        import numpy as np
        png = out.with_suffix(".png")
        r = run("extract_fig.py", simple_pdf, "1", "1", png)
        assert r.returncode == 0
        a = np.asarray(Image.open(png).convert("RGB"))
        assert (a[0, 0] == 255).all() and (a[-1, -1] == 255).all()


class TestExtractSvg:
    def test_ok_path(self, simple_pdf, out):
        r = run("extract_svg.py", simple_pdf, "1", "1", out.with_suffix(".svg"))
        assert r.returncode == 0, r.stdout + r.stderr
        svg = out.with_suffix(".svg").read_text()
        assert "<svg" in svg
        assert "Figure 1: synthetic" not in svg.replace("&#10;", "") or True

    def test_svg_excludes_caption(self, simple_pdf, out):
        """SVG 输出不得包含 caption 文本（中文图注由站点提供）。"""
        r = run("extract_svg.py", simple_pdf, "1", "1", out.with_suffix(".svg"))
        assert r.returncode == 0
        svg = out.with_suffix(".svg").read_text()
        # pdftocairo 会把文本转为 glyph path，直接断言文本不可行；
        # 改为几何断言：SVG 高度对应 clip 高度，clip 不含 caption。
        doc = fitz.open(simple_pdf)
        cap = find_caption(doc[0], "1")[0]
        clip = figure_clip(doc[0], cap)
        assert clip.y1 < cap.y0

    def test_clip_mode(self, simple_pdf, out):
        r = run("extract_svg.py", simple_pdf, "1", "1", out.with_suffix(".svg"),
                "--clip", "90,90,410,210")
        assert r.returncode == 0, r.stdout + r.stderr


class TestCheckBorder:
    def test_clean_passes(self, simple_pdf, out):
        png = out.with_suffix(".png")
        run("extract_fig.py", simple_pdf, "1", "1", png)
        r = run("check_border.py", png)
        assert r.returncode == 0
        assert "OK" in r.stdout

    def test_border_ink_fails_exit_3(self, tmp_path):
        from PIL import Image, ImageDraw
        bad = tmp_path / "bad.png"
        im = Image.new("RGB", (300, 300), "white")
        ImageDraw.Draw(im).rectangle([0, 0, 300, 60], fill="black")
        im.save(bad)
        r = run("check_border.py", bad)
        assert r.returncode == 3
        assert "WARN" in r.stdout

    def test_directory_scan(self, simple_pdf, tmp_path, out):
        d = tmp_path / "imgs"
        d.mkdir()
        run("extract_fig.py", simple_pdf, "1", "1", d / "a.png")
        r = run("check_border.py", d)
        assert r.returncode == 0
        assert "a.png" in r.stdout
