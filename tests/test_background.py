"""背景自动判断：白底 / 深底 / 保留原底 / 透明，以及透明 SVG 的边界检查。"""
import subprocess
import sys
from pathlib import Path

import fitz
import numpy as np
import pytest
from PIL import Image

import bgutil

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "pdf-figure-extract" / "scripts"


def run(script, *args):
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *map(str, args)],
        capture_output=True, text=True)


def make_light_ink(tmp_path):
    """透明画布 + 浅色线条/文字 → 自动应选深底。"""
    doc = fitz.open()
    page = doc.new_page()
    page.draw_rect(fitz.Rect(100, 100, 400, 200), color=(1, 1, 1), width=3)
    page.insert_text((120, 150), "light label", color=(1, 1, 1), fontsize=12)
    page.insert_text((100, 265), "Figure 1: light ink", color=(0, 0, 0), fontsize=10)
    p = tmp_path / "light.pdf"
    doc.save(p)
    doc.close()
    return p


def make_dark_paper(tmp_path):
    """PDF 自己画了深色背景 → 自动应保留，不再叠底。"""
    doc = fitz.open()
    page = doc.new_page()
    page.draw_rect(page.rect, color=None, fill=(0.06, 0.09, 0.16))
    page.insert_text((100, 120), "light on dark", color=(1, 1, 1), fontsize=12)
    page.insert_text((100, 340), "Figure 1: dark paper", color=(0, 0, 0), fontsize=10)
    p = tmp_path / "dark.pdf"
    doc.save(p)
    doc.close()
    return p


class TestResolve:
    def test_opaque_dark_paper_is_kept(self):
        assert bgutil.resolve("auto", {"opaque": 1.0, "ink": 0.9, "dark": 0.0,
                                       "light": 0.9, "bg_luma": 0.1}) == "keep"

    def test_opaque_light_paper_gets_white(self):
        assert bgutil.resolve("auto", {"opaque": 0.8, "ink": 0.1, "dark": 0.6,
                                       "light": 0.1, "bg_luma": 1.0}) == "white"

    def test_dark_ink_gets_white(self):
        assert bgutil.resolve("auto", {"opaque": 0.0, "ink": 0.1, "dark": 0.6,
                                       "light": 0.1, "bg_luma": None}) == "white"

    def test_light_ink_gets_dark(self):
        assert bgutil.resolve("auto", {"opaque": 0.0, "ink": 0.9, "dark": 0.0,
                                       "light": 0.9, "bg_luma": None}) == "dark"

    def test_mixed_ink_defaults_to_white(self):
        assert bgutil.resolve("auto", {"opaque": 0.0, "ink": 0.58, "dark": 0.4,
                                       "light": 0.2, "bg_luma": None}) == "white"

    def test_forced_mode_wins(self):
        assert bgutil.resolve("transparent", {"opaque": 1.0, "ink": 0.1, "dark": 0.9,
                                              "light": 0.0, "bg_luma": 0.1}) == "transparent"


class TestAutoBackground:
    def test_svg_white_for_dark_ink(self, simple_pdf, tmp_path):
        out = tmp_path / "a.svg"
        r = run("extract_svg.py", simple_pdf, "1", "1", out)
        assert r.returncode == 0, r.stdout + r.stderr
        assert 'fill="#ffffff"' in out.read_text()
        assert "background=white" in r.stdout

    def test_svg_dark_for_light_ink(self, tmp_path):
        pdf = make_light_ink(tmp_path)
        out = tmp_path / "light.svg"
        r = run("extract_svg.py", pdf, "1", "1", out)
        assert r.returncode == 0, r.stdout + r.stderr
        assert 'fill="#0f172a"' in out.read_text()
        assert "background=dark" in r.stdout

    def test_svg_keeps_painted_background(self, tmp_path):
        pdf = make_dark_paper(tmp_path)
        out = tmp_path / "dark.svg"
        r = run("extract_svg.py", pdf, "1", "1", out)
        assert r.returncode == 0, r.stdout + r.stderr
        assert "background=keep" in r.stdout
        assert 'fill="#ffffff"' not in out.read_text()

    def test_forced_dark(self, simple_pdf, tmp_path):
        out = tmp_path / "forced.svg"
        r = run("extract_svg.py", simple_pdf, "1", "1", out, "--background", "dark")
        assert r.returncode == 0
        assert 'fill="#0f172a"' in out.read_text()

    def test_transparent_svg(self, simple_pdf, tmp_path):
        out = tmp_path / "t.svg"
        r = run("extract_svg.py", simple_pdf, "1", "1", out, "--background", "transparent")
        assert r.returncode == 0
        text = out.read_text()
        assert 'fill="#ffffff"' not in text and 'fill="#0f172a"' not in text
        assert "background=transparent" in r.stdout

    def test_png_auto_white(self, simple_pdf, tmp_path):
        out = tmp_path / "a.png"
        r = run("extract_fig.py", simple_pdf, "1", "1", out, "--dpi", "150")
        assert r.returncode == 0, r.stdout + r.stderr
        a = np.asarray(Image.open(out).convert("RGB"))
        assert (a[0, 0] == 255).all()
        assert "background=white" in r.stdout

    def test_png_auto_dark(self, tmp_path):
        pdf = make_light_ink(tmp_path)
        out = tmp_path / "light.png"
        r = run("extract_fig.py", pdf, "1", "1", out, "--dpi", "150")
        assert r.returncode == 0, r.stdout + r.stderr
        corner = np.asarray(Image.open(out).convert("RGB"))[0, 0]
        assert tuple(corner) == bgutil.DARK
        assert "background=dark" in r.stdout

    def test_png_transparent(self, simple_pdf, tmp_path):
        out = tmp_path / "t.png"
        r = run("extract_fig.py", simple_pdf, "1", "1", out, "--background", "transparent")
        assert r.returncode == 0
        im = Image.open(out)
        assert im.mode == "RGBA"
        assert im.getpixel((0, 0))[3] == 0


class TestTransparentBorderCheck:
    def test_transparent_svg_edge_ink_is_detected(self, tmp_path):
        svg = tmp_path / "edge.svg"
        svg.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">'
            '<rect x="0" y="0" width="100" height="20" fill="#000"/></svg>')
        r = run("check_border.py", svg)
        assert r.returncode == 3, r.stdout + r.stderr

    def test_transparent_svg_clean_passes(self, tmp_path):
        svg = tmp_path / "clean.svg"
        svg.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">'
            '<rect x="30" y="30" width="40" height="40" fill="#000"/></svg>')
        r = run("check_border.py", svg)
        assert r.returncode == 0, r.stdout + r.stderr
