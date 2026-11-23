# 额外示例

命令中 `$SKILL_DIR` 指 skill 安装目录（例如 `~/skills/pdf-figure-extract`）。

## PPO Algorithm 1

- 论文：John Schulman, Filip Wolski, Prafulla Dhariwal, Alec Radford, Oleg Klimov. *Proximal Policy Optimization Algorithms*. 2017. [arXiv:1707.06347](https://arxiv.org/abs/1707.06347)
- 论文许可：[arXiv non-exclusive distribution license 1.0](http://arxiv.org/licenses/nonexclusive-distrib/1.0/)
- 生成命令：

```bash
curl -sL -o ppo.pdf https://arxiv.org/pdf/1707.06347
python "$SKILL_DIR/scripts/extract_svg.py" ppo.pdf 5 1 ppo-algorithm1.svg --clip "69,460,526,588"
```

- 说明：`--clip` 单位是 PDF 点，坐标基于该版本 PDF 第 5 页的版面；论文重排版后需要重新测量。
- 版权：图形内容版权归原作者，仅用于展示本技能可以抽取算法伪代码，不在仓库根目录 MIT 许可范围内。
