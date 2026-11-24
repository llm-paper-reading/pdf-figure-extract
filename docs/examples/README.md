# 额外示例

命令中 `$SKILL_DIR` 指 skill 安装目录（例如 `~/skills/pdf-figure-extract`）。

## PPO Algorithm 1

- 论文：John Schulman, Filip Wolski, Prafulla Dhariwal, Alec Radford, Oleg Klimov. *Proximal Policy Optimization Algorithms*. 2017. [arXiv:1707.06347](https://arxiv.org/abs/1707.06347)
- 论文许可：[arXiv non-exclusive distribution license 1.0](http://arxiv.org/licenses/nonexclusive-distrib/1.0/)
- 生成命令：

```bash
curl -sL -o ppo.pdf https://arxiv.org/pdf/1707.06347
python "$SKILL_DIR/scripts/extract_svg.py" ppo.pdf 5 1 ppo-algorithm1.svg --clip "60,455,535,600"
```

- 说明：`--clip` 单位是 PDF 点，坐标基于该版本 PDF 第 5 页的版面；论文重排版后需要重新测量。
- 版权：图形内容版权归原作者，仅用于展示本技能可以抽取算法伪代码，不在仓库根目录 MIT 许可范围内。

## PPO Table 1

- 论文：同上，[arXiv:1707.06347](https://arxiv.org/abs/1707.06347)
- 生成命令：

```bash
curl -sL -o ppo.pdf https://arxiv.org/pdf/1707.06347
python "$SKILL_DIR/scripts/extract_svg.py" ppo.pdf 6 1 ppo-table1.svg --clip "165,370,430,547"
```

- 说明：该表在第 6 页，caption 位于表格下方；clip 下界取在表格底线之上、caption 之前，上界包含表头与顶部横线。
- 版权：同 Algorithm 1，仅用于展示表格抽取效果，不在 MIT 许可范围内。

## PPO 公式 (3) 与 (4)

- 论文：同上，[arXiv:1707.06347](https://arxiv.org/abs/1707.06347)
- 生成命令：

```bash
curl -sL -o ppo.pdf https://arxiv.org/pdf/1707.06347
python "$SKILL_DIR/scripts/extract_svg.py" ppo.pdf 2 3 ppo-formulas-3-4.svg --clip "185,446,410,509"
```

- 说明：两条公式在第 2 页相邻排版，用一个 clip 同时框住，合并输出为一张 SVG；右边界停在公式编号之前，上下界避开前后正文。
- 版权：同 Algorithm 1，仅用于展示公式抽取效果，不在 MIT 许可范围内。
