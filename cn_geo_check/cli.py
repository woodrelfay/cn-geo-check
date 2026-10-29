"""命令行：生成一整套 GEO 自测包到输出文件夹。

用法：
  python -m cn_geo_check --brand 星桥家政 --industry 家政服务 --product 日常保洁 \
      --region 广州 --competitor 云洁家政 --url https://example.com --out ./geo-pack
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from .generator import ENGINES, SCORE_DIMS, TEST_RULES, BrandProfile, generate_questions
from .sitecheck import check_site


def render_questions_md(p: BrandProfile, questions) -> str:
    lines = [f"# GEO 自测问题包：{p.brand}", "",
             f"- 品牌：{p.brand}｜行业：{p.industry}｜核心产品/服务：{p.product}"
             + (f"｜地区：{p.region}" if p.region else "")
             + (f"｜主要竞品：{p.competitor}" if p.competitor else ""),
             f"- 问题总数：{len(questions)}（四组各 3 题）｜测试引擎：{'、'.join(e['name'] for e in ENGINES)}",
             "", "## 测试铁律（先看完再测）", ""]
    lines += [f"{i}. {r}" for i, r in enumerate(TEST_RULES, 1)]
    lines += ["", "## 引擎测试卡", ""]
    for e in ENGINES:
        lines.append(f"- **{e['name']}** {e['url']} — {e['note']}")
    lines += ["", "## 问题清单", ""]
    cat = ""
    for q in questions:
        if q.category != cat:
            cat = q.category
            lines += [f"### {cat}词组" if False else f"### {cat}", ""]
        lines += [f"**{q.qid}** {q.text}", f"（测什么：{q.intent}）", ""]
    lines += ["## 评分维度", ""]
    for name, desc in SCORE_DIMS:
        lines.append(f"- **{name}**：{desc}")
    lines += ["", "综合可见度分（本工具口径，0-100）= 提及率×60 + 首推率×20 + (平均准确性/5)×20。"
              "口径固定才可周周对比，分数本身不与任何第三方工具通用。", ""]
    return "\n".join(lines)


def write_scorecard(path: Path, questions) -> None:
    header = ["问题编号", "类别", "问题", "引擎", "测试日期", "是否提及(1/0)", "提及位置",
              "准确性(1-5)", "情感倾向", "竞品出现", "答案原文存档", "备注"]
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(header)
        for q in questions:
            for e in ENGINES:
                w.writerow([q.qid, q.category, q.text, e["name"], "", "", "", "", "", "", "", ""])


def render_report_template(p: BrandProfile) -> str:
    return f"""# GEO 周报：{p.brand}（第 __ 周）

- 测试日期：____-__-__｜测试人：____｜问题包版本：12 题标准版
- 本周一句话结论：（先写结论，再贴数据。例如：豆包提及率升至 8/12，DeepSeek 仍查无此品牌）

## 一、核心指标（按引擎）

| 引擎 | 提及率（x/12） | 首推率 | 平均准确性 | 综合可见度分 | 较上周 |
|---|---|---|---|---|---|
| 豆包 |  |  |  |  |  |
| Kimi |  |  |  |  |  |
| DeepSeek |  |  |  |  |  |
| 腾讯元宝 |  |  |  |  |  |
| 通义千问 |  |  |  |  |  |

综合可见度分 = 提及率×60 + 首推率×20 + (平均准确性/5)×20，只用真实测得的数据填，不估算。

## 二、本周发现（只写有原文存档支撑的）

1. 新出现/消失的提及：
2. 明显的事实错误（附题号和原文摘录）：
3. 竞品动态（谁在哪些题里稳定出现）：

## 三、下周动作（不超过 3 件，写明负责人）

1.
2.
3.
"""


def render_sitecheck_md(items) -> str:
    icon = {"通过": "✅", "提醒": "⚠️", "未通过": "❌", "未检测": "❓"}
    lines = ["# 网站基础检查", ""]
    for it in items:
        lines.append(f"- {icon.get(it.status, '')} **{it.name}**（{it.status}）：{it.detail}")
    lines += ["", "说明：本检查只判断机械可验证项，不预测排名。llms.txt 不是已被证实的排名因素，"
              "只是低成本加分项；真正决定 AI 引用的仍是内容里有没有可引用的事实、数据和出处。", ""]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="cn-geo-check",
                                 description="中国 AI 引擎 GEO 自测包生成器：12 问 + 评分表 + 周报模板 + 网站基础检查（零依赖，纯本地生成）")
    ap.add_argument("--brand", required=True, help="品牌全称，如 星桥家政")
    ap.add_argument("--industry", required=True, help="行业/品类，如 家政服务")
    ap.add_argument("--product", default="", help="核心产品/服务，默认同行业")
    ap.add_argument("--region", default="", help="服务地区（可选），如 广州")
    ap.add_argument("--competitor", default="", help="主要竞品（可选）")
    ap.add_argument("--url", default="", help="官网地址（可选），填了会做网站基础检查，需要联网")
    ap.add_argument("--out", default="geo-pack", help="输出文件夹，默认 ./geo-pack")
    args = ap.parse_args(argv)

    profile = BrandProfile(brand=args.brand, industry=args.industry, product=args.product,
                           region=args.region, competitor=args.competitor)
    questions = generate_questions(profile)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    (out / "01-测试问题包.md").write_text(render_questions_md(profile, questions), encoding="utf-8")
    write_scorecard(out / "02-评分表.csv", questions)
    (out / "03-周报模板.md").write_text(render_report_template(profile), encoding="utf-8")
    made = ["01-测试问题包.md", "02-评分表.csv（12 题 × 5 引擎 = 60 行待填）", "03-周报模板.md"]

    if args.url:
        items = check_site(args.url)
        (out / "04-网站基础检查.md").write_text(render_sitecheck_md(items), encoding="utf-8")
        made.append("04-网站基础检查.md")
        for it in items:
            print(f"  [{it.status}] {it.name}：{it.detail}")

    print(f"已为「{args.brand}」生成自测包 → {out}/")
    for m in made:
        print(f"  - {m}")
    print("下一步：照 01 的测试铁律，在豆包/Kimi/DeepSeek/元宝/通义逐题提问，把结果填进 02，周末汇总到 03。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
