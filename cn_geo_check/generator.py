"""问题包生成：按 品牌词 / 行业词 / 长尾词 / 场景词 四组生成 12 个标准化测试问题。

设计依据：品牌在 AI 问答里的可见度，取决于四类完全不同的提问——
用户直接问品牌（品牌词）、问品类（行业词）、问细节（长尾词）、描述场景求推荐（场景词）。
每类问题用同一套评分维度，才能周周可比。
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BrandProfile:
    brand: str
    industry: str
    product: str = ""        # 核心产品/服务，默认同 industry
    region: str = ""         # 服务地区，可选
    competitor: str = ""     # 主要竞品，可选

    def __post_init__(self):
        if not self.product:
            self.product = self.industry


@dataclass
class Question:
    qid: str                 # 如 B1 / I2 / L3 / S1
    category: str            # 品牌词 / 行业词 / 长尾词 / 场景词
    text: str
    intent: str              # 这个问题在测什么


def generate_questions(p: BrandProfile) -> list[Question]:
    b, ind, prod = p.brand, p.industry, p.product
    region = p.region or ""
    comp = p.competitor

    qs: list[Question] = []
    # ---- 品牌词：用户已经知道你，AI 怎么介绍你 ----
    qs.append(Question("B1", "品牌词", f"{b}是什么？主要做什么的？",
                       "测品牌认知是否被 AI 收录、介绍是否准确"))
    qs.append(Question("B2", "品牌词", f"{b}怎么样？靠谱吗？口碑如何？",
                       "测品牌评价的情感倾向和信息完整度"))
    if comp:
        qs.append(Question("B3", "品牌词", f"{b}和{comp}哪个好？有什么区别？",
                           "测与主要竞品对比时的胜负和差异点是否正确"))
    else:
        qs.append(Question("B3", "品牌词", f"{b}有什么优缺点？适合什么人？",
                           "测 AI 能否给出具体的优缺点而非空话"))

    # ---- 行业词：用户只问品类，AI 推不推你 ----
    qs.append(Question("I1", "行业词", f"{ind}有哪些靠谱的品牌或公司值得推荐？",
                       "核心题：品类推荐名单里有没有你、排第几"))
    qs.append(Question("I2", "行业词", f"{region}{ind}哪家好？怎么选才不踩坑？" if region
                       else f"{ind}哪家好？怎么选才不踩坑？",
                       "测带选择标准的推荐里你是否出现"))
    qs.append(Question("I3", "行业词", f"2026年{ind}品牌排行榜是什么？",
                       "测榜单类回答的收录情况（AI 常编造榜单，要重点核对准确性）"))

    # ---- 长尾词：用户问得很细，AI 答得准不准、提不提你 ----
    qs.append(Question("L1", "长尾词", f"{prod}一般多少钱？价格是怎么算的？",
                       "测价格类长尾里是否提及你、价格信息是否准确"))
    qs.append(Question("L2", "长尾词", f"{prod}具体包含哪些服务？流程是什么样的？",
                       "测服务细节类回答的准确性和品牌露出"))
    qs.append(Question("L3", "长尾词", f"小公司有必要做{ind}吗？什么样的企业适合？",
                       "测教育市场类问题里你的定位是否被正确引用"))

    # ---- 场景词：用户描述自己的处境，AI 给的方案里有没有你 ----
    qs.append(Question("S1", "场景词", f"我在{region}刚开了家小店，需要{prod}，有什么推荐？" if region
                       else f"我刚开了家小店，需要{prod}，有什么推荐？",
                       "测真实场景求推荐时你是否进入候选"))
    qs.append(Question("S2", "场景词", f"预算有限，想做{ind}，是自己做还是找服务商？找的话选什么样的？",
                       "测决策类场景里服务商推荐是否包含你"))
    qs.append(Question("S3", "场景词", f"之前找的{ind}服务商效果不好，想换一家，要注意什么？",
                       "测换供应商场景——流失客户的二次机会里有没有你"))
    return qs


ENGINES = [
    {"name": "豆包", "url": "https://www.doubao.com", "note": "字节系，国内用户量最大，优先测"},
    {"name": "Kimi", "url": "https://www.kimi.com", "note": "长文本见长，常引用网页来源，注意看引用列表"},
    {"name": "DeepSeek", "url": "https://chat.deepseek.com", "note": "务必开「联网搜索」再提问，否则测的是训练记忆"},
    {"name": "腾讯元宝", "url": "https://yuanbao.tencent.com", "note": "会混入公众号/视频号内容，留意来源构成"},
    {"name": "通义千问", "url": "https://www.tongyi.com", "note": "阿里系，电商/本地生活类问题表现有差异"},
]

SCORE_DIMS = [
    ("是否提及", "答案里有没有出现品牌名：出现=1，未出现=0（行业/长尾/场景题的关键指标）"),
    ("提及位置", "品牌在推荐名单中的顺序：1/2/3…，未提及填 0；越靠前权重越高"),
    ("准确性", "1-5 分：5=关键事实全对，3=大方向对但有细节错误，1=张冠李戴或编造"),
    ("情感倾向", "正向 / 中性 / 负向：按答案整体措辞判，不按单句"),
    ("竞品出现", "同一答案里出现了哪些竞品品牌名，原样记录，用于对比份额"),
]

TEST_RULES = [
    "每个问题开一个新会话提问，避免上下文污染；同一引擎的问题在同一天内测完",
    "问题原文一字不改地粘贴，不追加「请推荐品牌」之类的引导语",
    "DeepSeek 必须打开联网搜索；其他引擎如有联网/搜索开关同样打开，并记录开关状态",
    "完整保存答案原文（截图或复制文本），不要只记结论——复盘和申诉都靠原文",
    "记录测试日期和引擎版本/模型名；答案会随模型更新漂移，周与周之间比的是同一套题",
    "品牌词的 B1/B2 若完全查无此品牌，先检查品牌全称写法是否与官网一致，再下结论",
]

ACCOUNT_RULES = [
    "五个引擎（豆包/Kimi/DeepSeek/元宝/通义）目前都需要登录后才能对话，没有游客模式——用登录账号人工测试，这是本工具的默认方式，不存在「免登录测法」",
    "每个引擎备一个专用测试账号（小号），不要用日常账号：日常账号聊过品牌相关话题后，平台记忆会「认识你」，后续答案会被你的历史带偏，而且这种漂移很难察觉",
    "能关记忆的先关：豆包、通义等在设置里提供记忆开关，测试前关掉；关不掉的引擎靠「逐题新开会话」兜底",
    "涉及城市的题（长尾词/场景词），测试账号的资料地区和定位与品牌目标市场保持一致，或干脆留空——但每周必须一致，不能这周广州下周北京",
    "每周固定同一个账号、同一套提问顺序、尽量同一时段测：绝对纯净的样本不存在，口径恒定，环比数据才可信",
    "用 API 提问测到的是「API 口径」，与消费者在 App 里看到的答案不是一回事；如使用 API，必须在评分表备注里单独标注，绝不与人工实测数据混算",
]
