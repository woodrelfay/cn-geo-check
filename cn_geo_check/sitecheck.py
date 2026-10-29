"""网站基础检查：AI 爬虫能不能进来、能不能读懂你的站。

只做机械可判定的检查（全部标准库实现）：robots.txt 是否拦截主要 AI 爬虫、
有没有 llms.txt、sitemap 是否存在、首页有没有 FAQ/Organization 结构化数据。
检查结果分 通过 / 提醒 / 未通过 / 未检测 四档，抓不到就如实写未检测。
"""
from __future__ import annotations

import re
import urllib.request
from dataclasses import dataclass

AI_BOTS = ["Bytespider", "GPTBot", "ClaudeBot", "PerplexityBot", "Baiduspider", "360Spider"]


@dataclass
class CheckItem:
    name: str
    status: str   # 通过 / 提醒 / 未通过 / 未检测
    detail: str


def parse_robots_blocked(robots_text: str, bot: str) -> bool | None:
    """判断 robots.txt 是否全站拦截某个 bot。返回 None 表示没提到该 bot（默认放行）。"""
    blocks: dict[str, list[str]] = {}
    current: list[str] = []
    for raw in robots_text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, _, val = line.partition(":")
        key, val = key.strip().lower(), val.strip()
        if key == "user-agent":
            current = [val.lower()]
            blocks.setdefault(val.lower(), [])
        elif key == "disallow" and current:
            for ua in current:
                blocks.setdefault(ua, []).append(val)
    rules = blocks.get(bot.lower())
    if rules is None:
        rules = blocks.get("*")
        if rules is None:
            return None
    return "/" in rules


def detect_schema(html: str) -> dict[str, bool]:
    """从首页 HTML 判断结构化数据。"""
    ld = re.findall(r"application/ld\+json", html)
    return {
        "has_jsonld": bool(ld),
        "faq": "FAQPage" in html,
        "organization": "Organization" in html or "LocalBusiness" in html,
    }


def _fetch(url: str, timeout: int = 12) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "cn-geo-check/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(300_000).decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception:
        return 0, ""


def check_site(base_url: str) -> list[CheckItem]:
    base = base_url.rstrip("/")
    items: list[CheckItem] = []

    status, robots = _fetch(base + "/robots.txt")
    if status == 200 and robots:
        blocked = [b for b in AI_BOTS if parse_robots_blocked(robots, b)]
        if blocked:
            items.append(CheckItem("robots.txt AI 爬虫放行", "未通过",
                                   f"以下爬虫被全站拦截，AI 引擎抓不到你的站：{', '.join(blocked)}"))
        else:
            items.append(CheckItem("robots.txt AI 爬虫放行", "通过",
                                   "主要 AI 爬虫（Bytespider/GPTBot/ClaudeBot 等）未被全站拦截"))
    else:
        items.append(CheckItem("robots.txt AI 爬虫放行", "未检测",
                               f"robots.txt 获取失败（HTTP {status or '网络错误'}），请人工确认"))

    status, _ = _fetch(base + "/llms.txt")
    if status == 200:
        items.append(CheckItem("llms.txt", "通过", "已提供 llms.txt，AI 可快速获取站点结构索引"))
    else:
        items.append(CheckItem("llms.txt", "提醒",
                               "没有 llms.txt。它不是排名因素，但成本极低，属于顺手可做的加分项"))

    status, _ = _fetch(base + "/sitemap.xml")
    items.append(CheckItem("sitemap.xml", "通过" if status == 200 else "提醒",
                           "sitemap 存在，爬虫可系统抓取全站" if status == 200
                           else "未找到 sitemap.xml，爬虫只能靠链接发现页面"))

    status, html = _fetch(base + "/")
    if status == 200 and html:
        s = detect_schema(html)
        if s["faq"]:
            items.append(CheckItem("FAQ 结构化数据", "通过",
                                   "首页含 FAQPage 结构化数据，问答内容容易被 AI 直接引用"))
        elif s["has_jsonld"]:
            items.append(CheckItem("FAQ 结构化数据", "提醒",
                                   "有 JSON-LD 但没有 FAQPage；把常见问题做成 FAQ 结构化数据是 GEO 的高性价比动作"))
        else:
            items.append(CheckItem("FAQ 结构化数据", "未通过",
                                   "首页没有任何 JSON-LD 结构化数据，AI 只能靠正文猜你的业务"))
        items.append(CheckItem("组织/商家结构化数据", "通过" if s["organization"] else "提醒",
                               "含 Organization/LocalBusiness 信息" if s["organization"]
                               else "未检测到 Organization/LocalBusiness 结构化数据，品牌实体信息不明确"))
    else:
        items.append(CheckItem("首页结构化数据", "未检测",
                               f"首页获取失败（HTTP {status or '网络错误'}）"))
    return items
