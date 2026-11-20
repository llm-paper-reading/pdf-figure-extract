"""历史 bug 回归测试：每条对应一个已修复的真实缺陷，防止复发。"""
import subprocess
import sys
from pathlib import Path

import fitz
import numpy as np
from PIL import Image

from conftest import line_bboxes
from extract_fig import figure_clip, find_caption

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "pdf-figure-extract" / "scripts"


class TestLegendTextClipped:
    """图内图例（如 FlashAttention Figure 1 的 "Inner Loop" 标签）是
    TXT 块而非 drawing，figure_clip 旧版只并 image/vector 块，图例被 clip 切掉。
    """

    def test_clip_covers_legend_labels(self, simple_pdf):
        doc = fitz.open(simple_pdf)
        page = doc[0]
        cap = find_caption(page, "1")[0]
        clip = figure_clip(page, cap, margin_pt=20)
        for needle in ("Inner Loop", "legend label"):
            label = line_bboxes(page, needle)[0]
            assert clip.y1 >= label.y1 - 1, f"{needle} 被 clip 底界切掉"
        # 仍不得包含 caption 与正文
        assert clip.y1 < cap.y0
        body = line_bboxes(page, "Body text")[0]
        assert clip.y1 < body.y0

    def test_both_scripts_stay_in_sync(self, simple_pdf):
        """extract_fig 与 extract_svg 各有一份 figure_clip，行为必须一致。"""
        from extract_svg import figure_clip as clip_svg

        doc = fitz.open(simple_pdf)
        page = doc[0]
        cap = find_caption(page, "1")[0]
        c1 = figure_clip(page, cap)
        c2 = clip_svg(page, cap)
        assert (round(c1.x0), round(c1.y0), round(c1.x1), round(c1.y1)) == (
            round(c2.x0), round(c2.y0), round(c2.x1), round(c2.y1))

    def test_cli_output_contains_legend(self, simple_pdf, tmp_path):
        """端到端：渲染出的 PNG 里图例区域必须有墨迹（未被裁掉）。"""
        out = tmp_path / "fig1.png"
        dpi = 150
        r = subprocess.run(
            [sys.executable, str(SCRIPTS / "extract_fig.py"),
             simple_pdf, "1", "1", str(out), "--dpi", str(dpi)],
            capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr

        doc = fitz.open(simple_pdf)
        page = doc[0]
        cap = find_caption(page, "1")[0]
        clip = figure_clip(page, cap)  # 与 CLI 默认参数一致（margin 20）
        label = line_bboxes(page, "Inner Loop")[0]
        scale = dpi / 72
        border = max(10, int(clip.width * scale * 0.012))
        x0 = int(border + (label.x0 - clip.x0) * scale) - 3
        x1 = int(border + (label.x1 - clip.x0) * scale) + 3
        y0 = int(border + (label.y0 - clip.y0) * scale) - 3
        y1 = int(border + (label.y1 - clip.y0) * scale) + 3
        a = np.asarray(Image.open(out).convert("RGB"))
        ink = (a < 245).any(axis=-1)
        region = ink[max(0, y0):y1, max(0, x0):x1]
        assert region.size, "图例区域落在输出图像之外"
        assert region.mean() > 0.02, f"图例区域墨迹仅 {region.mean():.3f}，疑似被裁掉"
