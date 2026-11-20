# 对比素材说明

本目录中的 SVG 由本技能从论文 PDF 直接抽取，仅用于 README 的效果对比。

## 来源

- Tian Zhou, Peisong Niu, Xue Wang, Liang Sun, Rong Jin. *One Fits All: Power General Time Series Analysis by Pretrained LM*. NeurIPS 2023 Spotlight. [arXiv:2302.11939](https://arxiv.org/abs/2302.11939)
- 官方代码仓库：[DAMO-DI-ML/NeurIPS2023-One-Fits-All](https://github.com/DAMO-DI-ML/NeurIPS2023-One-Fits-All)
- 论文许可：[CC BY-NC-SA 4.0](http://creativecommons.org/licenses/by-nc-sa/4.0/)

## 生成命令

```bash
curl -sL -o ofa.pdf https://arxiv.org/pdf/2302.11939
python <skill-dir>/scripts/extract_svg.py ofa.pdf 2 1 one-fits-all-figure1.svg   # Figure 1
python <skill-dir>/scripts/extract_svg.py ofa.pdf 4 2 one-fits-all-figure2.svg   # Figure 2
```

## 版权

- SVG 中的图形内容版权归论文作者所有，按 CC BY-NC-SA 4.0 使用，**不得商用**；
- 本目录内容不在仓库根目录 MIT 许可的覆盖范围内；
- README 中引用的官方仓库图片未复制进本仓库，仅通过 GitHub 原始链接展示，版权归原作者所有。
