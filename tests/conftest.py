"""pytest fixtures：用 PyMuPDF 现场合成论文 PDF，测试不依赖网络。

simple_pdf 页面布局（pt，页面 612x792）：
  - 矢量绘图区    y 100-200
  - 图内文字标签   y ~228-248（TXT 块，回归场景）
  - Figure caption y ~258-267
  - 正文          y ~313 起
"""
import sys
from pathlib import Path


def pytest_addoption(parser):
    parser.addoption("--net", action="store_true", default=False,
                     help="run network smoke tests")

import fitz
import pytest

# 让测试直接 import scripts/ 下的模块
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


def line_bboxes(page, needle):
    """返回页面中包含 needle 的文本行 bbox 列表。"""
    out = []
    for b in page.get_text("dict")["blocks"]:
        for l in b.get("lines", []):
            s = "".join(sp["text"] for sp in l["spans"])
            if needle in s:
                out.append(fitz.Rect(l["bbox"]))
    return out


@pytest.fixture
def simple_pdf(tmp_path):
    doc = fitz.open()
    page = doc.new_page()
    # 矢量图（image/vector 块）
    page.draw_rect(fitz.Rect(100, 100, 400, 200), color=(0, 0, 0), width=2)
    page.draw_line(fitz.Point(120, 150), fitz.Point(380, 180), color=(0, 0, 1), width=2)
    # 图内文字标签：TXT 块，不属于 drawings（曾漏并导致被切）
    page.insert_text((280, 235), "Inner Loop", fontname="helv", fontsize=10)
    page.insert_text((180, 246), "legend label", fontname="helv", fontsize=8)
    # caption 与正文
    page.insert_text((100, 265), "Figure 1: synthetic test figure", fontname="helv", fontsize=10)
    page.insert_text((72, 320), "Body text after the figure.", fontname="helv", fontsize=10)
    path = tmp_path / "simple.pdf"
    doc.save(str(path))
    doc.close()
    return str(path)
