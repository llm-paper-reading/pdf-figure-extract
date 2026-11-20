"""纯逻辑单元测试：caption 锚定、边界墨迹检测、错误路径。"""
import fitz
import pytest
from PIL import Image, ImageDraw

from check_border import _scores
from conftest import line_bboxes
from extract_fig import figure_clip, find_caption


def _make_pdf(tmp_path, lines):
    doc = fitz.open()
    page = doc.new_page()
    for x, y, text in lines:
        page.insert_text((x, y), text, fontname="helv", fontsize=10)
    path = tmp_path / "t.pdf"
    doc.save(str(path))
    doc.close()
    return fitz.open(str(path))


class TestFindCaption:
    def test_finds_caption(self, simple_pdf):
        doc = fitz.open(simple_pdf)
        caps = find_caption(doc[0], "1")
        assert len(caps) == 1
        assert caps[0].y0 > 240  # caption 位于图区（y 100-200）下方

    def test_section_numbering(self, tmp_path):
        doc = _make_pdf(tmp_path, [(100, 245, "Figure 3.1: section numbered figure")])
        assert find_caption(doc[0], "3.1")

    def test_no_cross_match_between_1_and_10(self, tmp_path):
        doc = _make_pdf(tmp_path, [(100, 245, "Figure 10: another figure")])
        assert find_caption(doc[0], "1") == []
        assert find_caption(doc[0], "10")

    def test_missing_caption_returns_empty(self, tmp_path):
        doc = _make_pdf(tmp_path, [(100, 245, "no figure here at all")])
        assert find_caption(doc[0], "1") == []


class TestFigureClip:
    def test_raises_without_figure_content(self, tmp_path):
        doc = _make_pdf(tmp_path, [(100, 245, "Figure 1: caption without figure")])
        page = doc[0]
        cap = find_caption(page, "1")[0]
        with pytest.raises(RuntimeError):
            figure_clip(page, cap)


class TestScores:
    def test_clean_image(self):
        im = Image.new("RGB", (300, 300), "white")
        ImageDraw.Draw(im).rectangle([60, 60, 240, 240], outline="black", width=3)
        assert max(_scores(im)) < 0.003

    def test_border_ink_detected(self):
        """白底图上顶着上边缘的墨线应被检出（角点仍为白，背景感知不干预）。"""
        im = Image.new("RGB", (300, 300), "white")
        ImageDraw.Draw(im).rectangle([140, 0, 160, 40], fill="black")
        assert _scores(im)[0] > 0.003

    def test_full_dark_background_not_flagged(self):
        """整图深色背景（角点即背景）不应误报——背景感知的语义。"""
        im = Image.new("RGB", (300, 300), "black")
        assert max(_scores(im)) < 0.003

    def test_dark_background_no_false_positive(self):
        im = Image.new("RGB", (300, 300), (20, 20, 20))
        ImageDraw.Draw(im).ellipse([80, 80, 220, 220], fill=(220, 220, 220))
        assert max(_scores(im)) < 0.003
