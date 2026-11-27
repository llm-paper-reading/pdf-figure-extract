# 对比素材说明

本目录中的 SVG 由本技能从论文 PDF 直接抽取，用于 README 与本文档中的效果对比。下面的命令中 `$SKILL_DIR` 指 skill 安装目录（例如 `~/skills/pdf-figure-extract`）。README 主对比使用 FlashAttention。

## 素材：FlashAttention（README 默认示例）

- 论文：Tri Dao, Daniel Y. Fu, Stefano Ermon, Atri Rudra, Christopher Ré. *FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness*. NeurIPS 2022. [arXiv:2205.14135](https://arxiv.org/abs/2205.14135)
- 官方仓库：[Dao-AILab/flash-attention](https://github.com/Dao-AILab/flash-attention)，BSD-3-Clause
- 对应官方图片：`assets/flashattn_banner.jpg`（仓库 README 顶部图，即论文 Figure 1）；本目录保留一份副本 `flashattn_banner.jpg`，便于离线/内网查看，按 BSD-3-Clause 使用并注明来源。
- 生成命令：

```bash
curl -sL -o fa.pdf https://arxiv.org/pdf/2205.14135
python "$SKILL_DIR/scripts/extract_svg.py" fa.pdf 2 1 flash-attention-figure1.svg
```

- 论文许可：[arXiv non-exclusive distribution license 1.0](http://arxiv.org/licenses/nonexclusive-distrib/1.0/)；图形内容同时随 BSD-3-Clause 的官方仓库发布。

## 版权

- 图形内容版权归各论文作者所有；
- FlashAttention 的官方图片（`flashattn_banner.jpg`）复制自 [Dao-AILab/flash-attention](https://github.com/Dao-AILab/flash-attention)，按 BSD-3-Clause 使用并保留来源说明；
- 本目录内容不在仓库根目录 MIT 许可的覆盖范围内。如权利人希望移除相关素材，请开 issue 说明，我们会尽快处理。
