"""Server-rendered educational pages, independent of trading state."""
from __future__ import annotations

import json
from functools import lru_cache
from html import escape
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlsplit

DATA = Path(__file__).resolve().parent / "static" / "academy"
CRAWL_MANIFEST = DATA.parents[1] / "data" / "blog-crawl" / "manifest.json"
DISCOVERY_MANIFEST = DATA.parents[1] / "data" / "digitalyoming-discovery.json"
DIGITALYOMING_CATEGORIES = ("入门与账户", "资金与安全", "现货与订单", "合约与杠杆", "机器人与策略", "理财与产品", "概念与工具", "活动与旧资讯")
STAGES = [
    ("认识市场", "先读懂价格与一笔买卖", ["money", "profit", "candles", "orders"]),
    ("熟悉平台", "认识账户、资产与模拟环境", ["safety", "binance-map", "transfer", "demo"]),
    ("学会控制风险", "从成本、杠杆到每笔仓位", ["fees", "spot-futures", "leverage", "sizing"]),
    ("理解策略", "别只盯着胜率和收益", ["drawdown", "expectancy", "strategies", "indicators"]),
    ("验证一个想法", "把规则放到可信的实验里", ["quant-rules", "data", "backtest", "validation"]),
    ("运行与复盘", "读懂 Agent，记录模拟过程", ["paper", "agent", "api", "review"]),
]
LAB_MAP = {"profit": "pnl", "candles": "candle", "orders": "order", "fees": "fees", "leverage": "leverage", "sizing": "sizing", "drawdown": "recovery", "expectancy": "expectancy", "quant-rules": "signal", "backtest": "bias"}
ARCHIVED_GUIDES = {
    "digitalyoming-binance-savings-tutorial", "digitalyoming-binance-auto-invest-index-linked-plan",
    "digitalyoming-binance-liquidity-farming", "digitalyoming-binance-range-bound-tutorial",
    "digitalyoming-binance-bnb-vault-tutorial",
}
STARTER_GUIDES = (
    ("digitalyoming-binance", "认识平台"),
    ("digitalyoming-spot", "学会下单"),
    ("digitalyoming-binance-fees", "算清费用"),
    ("digitalyoming-binance-futures-mock-trading", "模拟练习"),
)


def h(value: Any) -> str:
    return escape(str(value), quote=True)


@lru_cache(maxsize=1)
def content() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], list[dict[str, str]]]:
    lessons: dict[str, dict[str, Any]] = {}
    sources: dict[str, dict[str, Any]] = {}
    terms: list[dict[str, str]] = []
    for name in ("basics", "risk", "quant"):
        bundle = json.loads((DATA / f"{name}.json").read_text(encoding="utf-8"))
        lessons.update({item["slug"]: item for item in bundle["lessons"]})
        sources.update({item["id"]: item for item in bundle["sources"]})
        terms.extend(bundle["terms"])
    ordered = [lessons[slug] for _, _, slugs in STAGES for slug in slugs]
    return ordered, sources, terms


@lru_cache(maxsize=1)
def blog_posts() -> list[dict[str, Any]]:
    posts = []
    for name in ("blog-featured", "blog-posts", "blog-digitalyoming-a", "blog-digitalyoming-b", "blog-digitalyoming-c"):
        if not (DATA / f"{name}.json").is_file():
            continue
        posts.extend(json.loads((DATA / f"{name}.json").read_text(encoding="utf-8"))["posts"])
    return posts


def crawl_records() -> dict[str, dict[str, Any]]:
    try:
        data = json.loads(CRAWL_MANIFEST.read_text(encoding="utf-8"))
        return {record["slug"]: record for record in data["posts"]}
    except (FileNotFoundError, json.JSONDecodeError, KeyError, TypeError):
        return {}


def lesson_link(lesson: dict[str, Any], index: int, row: bool = False) -> str:
    slug = lesson["slug"]
    search = " ".join([lesson["title"], lesson["subtitle"], *lesson["goals"], *[p for sec in lesson["sections"] for p in [sec["title"], *sec.get("paragraphs", []), *sec.get("bullets", [])]]]) if row else ""
    return f'''<a class="{'course-row' if row else 'nav-lesson'}" href="/learn/{h(slug)}" data-course="{h(slug)}" data-search="{h(search)}"><span class="lesson-number">{index:02}</span><span><b>{h(lesson['title'])}</b>{f'<small>{h(lesson["subtitle"])}</small>' if row else ''}</span><span class="lesson-meta">{h(lesson['minutes'])} 分钟</span><span class="done-label" hidden>已学</span></a>'''


def shell(title: str, body: str, current: str = "", toc: str = "", layout: str = "course", sidebar_content: str = "") -> str:
    lessons, _, _ = content()
    by_slug = {item["slug"]: item for item in lessons}
    order = {item["slug"]: i + 1 for i, item in enumerate(lessons)}
    nav = ""
    for num, (name, _, slugs) in enumerate(STAGES, 1):
        opened = current in slugs
        nav += f'<details class="stage-nav" {"open" if opened else ""}><summary><span>{num:02}</span> {h(name)}</summary>'
        nav += "".join(lesson_link(by_slug[slug], order[slug]) for slug in slugs) + "</details>"
    auxiliary = "".join(f'<a {"aria-current=page" if current == key else ""} href="/learn/{key}">{label}</a>' for key, label in [("blogs", "个人博客导读"), ("collections/digitalyoming", "数位小帮手专题"), ("practice", "互动练习区"), ("glossary", "术语词典"), ("sources", "资料与来源")])
    course_nav = f'<nav aria-label="全部课程">{nav}</nav>'
    if sidebar_content:
        course_nav = f'{sidebar_content}<details class="secondary-nav"><summary>基础课程</summary>{course_nav}</details>'
    search = '' if layout == 'library' else '<form class="nav-search" action="/learn" method="get"><label for="nav-q">搜索基础课程</label><input id="nav-q" name="q" type="search" placeholder="输入知识点，按回车搜索"></form>'
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="theme-color" content="#fcfcfb"><title>{h(title)} | 量化学习室</title><link rel="stylesheet" href="/academy.css"><script src="/academy.js" defer></script></head>
<body data-page="{h(current)}" data-layout="{h(layout)}"><a class="skip" href="#main">跳到正文</a><header class="site-header"><a class="brand" href="/learn">量化学习室<span>学习文档</span></a><nav aria-label="快捷入口"><a href="/learn">基础课程</a><a href="/learn/blogs">博客资料</a><a href="/">模拟操作台</a></nav></header>
<div class="site-layout"><aside class="sidebar"><details class="mobile-directory" open><summary>浏览目录</summary><div class="directory"><a class="directory-home" href="/learn">从这里开始学习</a>{search}{course_nav}<div class="aux-nav">{auxiliary}</div><details class="progress-panel"><summary>我的学习进度</summary><label for="learning-progress">已完成 <span id="progress-text">0 / {len(lessons)}</span></label><progress id="learning-progress" max="{len(lessons)}" value="0"></progress><p id="storage-note">答对每课自测，进度保存在此浏览器。</p><button id="clear-progress" class="text-button">清除学习进度</button><button id="undo-progress" class="text-button" hidden>撤销清除</button></details></div></details></aside>
<main id="main">{body}<footer class="site-footer"><p>独立学习资料 / 教学与模拟</p><p>非币安或 Claude 官方网站。练习数字为教学假设，不承诺收益。</p><a href="/learn">学习路线</a><a href="/learn/sources">资料来源</a></footer></main>{toc}</div>
<noscript><div class="noscript">文章、资料搜索和分页可以正常使用；互动计算器、课程筛选和进度保存需要 JavaScript。</div></noscript></body></html>'''


def home() -> str:
    lessons, _, _ = content()
    by_slug = {item["slug"]: item for item in lessons}
    order = {item["slug"]: i + 1 for i, item in enumerate(lessons)}
    stages = ""
    for i, (name, description, slugs) in enumerate(STAGES, 1):
        stages += f'<section class="curriculum-stage" data-stage="{i}"><header><span class="stage-number">{i:02}</span><div><h2>{h(name)}</h2><p>{h(description)}</p></div></header><div class="course-list">'
        stages += "".join(lesson_link(by_slug[slug], order[slug], True) for slug in slugs) + "</div></section>"
    minutes = sum(int(item["minutes"]) for item in lessons)
    body = f'''<section class="home-hero"><p class="eyebrow">从零开始的交易与量化课程</p><h1>先看懂市场，<br>再验证规则。</h1><p class="hero-description">从第一笔买卖到一个模拟 Agent。把复杂概念拆成你能算清、能操作、能验证的小步骤。</p><div class="hero-actions"><a class="button" id="continue-learning" href="/learn/money">从第一课开始</a><a href="/learn/practice">先玩一个小实验</a></div><p class="hero-caption">{len(lessons)} 节独立课程 / 6 个阶段 / 约 {minutes} 分钟，按自己的节奏学</p><div class="book-mark" aria-hidden="true"><span>学习的顺序</span><p>理解</p><p>练习</p><p>验证</p><small>让每一个数字都有来处</small></div></section>
<section class="orientation"><div><h2>不必一口气学完。</h2><p>零基础从第一阶段开始；只想读懂模拟操作台，可以先学“盈亏”“模拟环境”和“复盘”。每页都有算例、自测与原始来源。</p></div><div><span class="eyebrow">这套课程能帮你</span><p>看懂一笔交易的过程，识别成本与风险，检查一套规则是否值得继续研究。</p><p class="muted">短期模拟盈利不能证明长期有效。</p></div></section>
<section class="reading-note"><h2>把基础知识，接到别人的实际经验里。</h2><p>新增个人博客导读：从现货下单到网格、回测和模拟运行，每篇保留作者与原文，补充规则核对和一项小练习。</p><a href="/learn/blogs">浏览 {len(blog_posts())} 篇个人博客导读</a></section>
<section class="catalog" id="catalog"><div class="section-heading"><div><p class="eyebrow">你的学习路线</p><h2>由浅入深，一次学一件事。</h2></div><a href="/learn/glossary">遇到生词，查词典</a></div><div class="catalog-tools"><label for="course-query">搜索课程内容</label><input type="search" id="course-query" placeholder="试试：手续费、强平、过拟合"><div class="filters" role="group" aria-label="筛选课程阶段"><button data-filter="all" aria-pressed="true">全部</button>{''.join(f'<button data-filter="{i}" aria-pressed="false">阶段 {i}</button>' for i in range(1,7))}</div></div><p id="search-status" class="muted" role="status">共 {len(lessons)} 节课程</p>{stages}<p id="search-empty" class="empty" hidden>没有找到匹配课程。试试更短的词，或切回“全部”。</p></section>
<section class="reading-trail"><h2>学完后，再做这三件小事。</h2><ol><li><b>算清一笔交易。</b>从买入支出到卖出收入，把每次手续费都写上。</li><li><b>读懂一条信号。</b>知道它用了什么数据、何时触发、可能在哪里失效。</li><li><b>观察一次完整模拟。</b>记录开始与结束、成交、成本和异常，不只截一张盈利图。</li></ol><a href="/learn/paper">查看模拟观察方法</a></section>'''
    return shell("学习路线", body)


def paragraphs(items: list[str]) -> str:
    return "".join(f"<p>{h(text)}</p>" for text in items)


def bullet_list(items: list[str], ordered: bool = False) -> str:
    tag = "ol" if ordered else "ul"
    return f'<{tag}>' + "".join(f'<li>{h(text)}</li>' for text in items) + f'</{tag}>'


def range_input(key: str, label: str, low: float, high: float, step: float, default: float) -> str:
    return f'<label class="lab-label" for="{key}">{label}<output id="{key}-label" for="{key}">{default}</output></label><input id="{key}" type="range" min="{low}" max="{high}" step="{step}" value="{default}">'


def lab(kind: str) -> str:
    r = range_input
    controls: dict[str, tuple[str, str, str]] = {
        "pnl": ("一笔买卖，到底赚了多少？", r("pnl-cash", "买入成交额 / USDT", 100, 10000, 100, 1000) + r("pnl-move", "价格变化 / %", -30, 30, 1, 5), "忽略费用。持有时是浮动盈亏；卖出才实现。"),
        "fees": ("微小的上涨，够付两次费用吗？", r("fees-move", "市场价格变化 / %", -3, 3, .1, 1) + r("fees-rate", "单次手续费 / %", 0, .5, .01, .1) + '<label class="check"><input type="checkbox" id="fees-slip" checked>买卖各承受 0.05% 不利滑点</label>', "以 1,000 USDT 买入成交额计算，买入手续费另付。滑点与费率均为假设，不是平台报价。"),
        "candle": ("一根 K 线，能告诉你什么？", r("candle-close", "收盘价格 / USDT", 90, 110, 1, 105) + '<svg id="candle-chart" viewBox="0 0 360 170" role="img" aria-label="假设开盘100，最高110，最低90，收盘由滑块改变"><line x1="180" y1="20" x2="180" y2="150" stroke="currentColor" stroke-width="2"/><rect id="candle-body" x="164" y="52.5" width="32" height="32.5" fill="currentColor"/><text x="215" y="24">最高 110</text><text x="215" y="154">最低 90</text><text x="15" y="89">开盘 100</text></svg>', "固定开盘 100、最高 110、最低 90，只改变收盘价。K 线不告诉你先涨还是先跌，也不预测下一根。"),
        "order": ("挂一个限价买单，会马上成交吗？", r("order-limit", "你愿意支付的最高单价", 95, 105, 1, 98), "假设买 1 枚；当前卖单是 100 价位 0.4 枚、101 价位 0.6 枚。忽略费用、排队和订单簿变化，仅演示限价的上限含义。"),
        "leverage": ("同样的波动，不同的仓位", r("lev-times", "实际杠杆 / 倍", 1, 100, 1, 10) + r("lev-move", "价格变化 / %", -2, 2, .1, .5), "整个账户有 1,000 USDT，做多，忽略费用和资金费。这里只做线性算术，不计算强平价；真实仓位可能在价格走完前就被强平。"),
        "sizing": ("先定最多想亏多少，再定仓位", r("size-equity", "账户净资产 / USDT", 1000, 20000, 500, 10000) + r("size-risk", "这笔预设风险占比 / %", .1, 2, .1, .5) + r("size-stop", "止损距离 / %", .5, 10, .5, 2), "简化公式：风险预算 ÷ 止损距离 = 理论仓位。忽略费用、滑点、最小数量；止损无法保证成交价，实际亏损可能超过预算。"),
        "recovery": ("亏损后，需要涨多少才能回本？", r("rec-loss", "从 1,000 USDT 亏掉 / %", 0, 90, 5, 50), "固定最初投入 1,000 USDT，不追加资金。回本涨幅以亏损后的余额为分母。"),
        "expectancy": ("高胜率，是否一定赚钱？", r("exp-win", "胜率 / %", 0, 100, 5, 70) + r("exp-gain", "每次盈利毛额 / USDT", 10, 300, 10, 50) + r("exp-loss", "每次亏损毛额 / USDT", 10, 300, 10, 150) + r("exp-fee", "每笔交易总成本 / USDT", 0, 20, 1, 2), "期望 = 胜率 × 平均盈利 − 败率 × 平均亏损 − 每笔总成本。输入是假设，不是已验证的长期概率。"),
        "signal": ("只按事先写好的条件行动", r("signal-price", "今天收盘价格", 97, 107, 1, 103), "前三天收盘为 100、102、101。规则：今天收盘严格高于前三天最高收盘，才发出买入信号。只示范入场，执行需等之后的可成交时机。"),
        "bias": ("这条规则，有没有偷看未来？", '<div class="choice-buttons"><button data-bias="future">收盘后发现上涨，记为当天开盘已买入</button><button data-bias="causal">收盘后产生信号，下一次可成交时再买</button></div>', "按信息出现的时间检查每个步骤。交易模型还要计入延迟、价差、费用与订单失败。"),
    }
    title, inputs, note = controls[kind]
    return f'<section class="lab" data-lab="{kind}" id="lab-{kind}"><div class="lab-head"><p class="eyebrow">互动实验 / 教学假设</p><h2>{title}</h2></div><div class="lab-body"><div>{inputs}</div><div class="lab-result" id="{kind}-result" role="status" aria-live="polite"><p>启用 JavaScript 后可改变数字，查看计算结果。</p></div></div><p class="lab-note">{note}</p></section>'


def source_rows(ids: list[str]) -> str:
    _, sources, _ = content()
    result = ""
    for key in ids:
        source = sources[key]
        result += f'<li><a href="{h(source["url"])}" target="_blank" rel="noreferrer">{h(source["title"])}</a><p>{h(source["note"])}</p><small>核实日期：{h(source["checked"])}</small></li>'
    return result


def lesson_page(item: dict[str, Any]) -> str:
    lessons, _, _ = content()
    index = next(i for i, obj in enumerate(lessons) if obj["slug"] == item["slug"])
    stage = next(i for i, (_, _, slugs) in enumerate(STAGES, 1) if item["slug"] in slugs)
    toc_items = "".join(f'<a href="#section-{i}">{h(section["title"])}</a>' for i, section in enumerate(item["sections"], 1))
    body = f'<nav class="breadcrumb" aria-label="当前位置"><a href="/learn">学习路线</a><span>/ 阶段 {stage} / 第 {index + 1:02} 课</span></nav><article class="lesson" data-slug="{h(item["slug"])}"><header class="lesson-hero"><p class="eyebrow">{h(STAGES[stage-1][0])} / 约 {h(item["minutes"])} 分钟</p><h1>{h(item["title"])}</h1><p class="lesson-subtitle">{h(item["subtitle"])}</p><div class="objectives"><h2>学完这一课，你会</h2>{bullet_list(item["goals"])}</div></header>'
    body += f'<details class="inline-toc"><summary>这一课的内容</summary><nav aria-label="本课目录">{toc_items}<a href="#example">一步步算个例子</a><a href="#self-check">检查一下理解</a></nav></details>'
    for i, section in enumerate(item["sections"], 1):
        body += f'<section class="prose-section" id="section-{i}"><span class="section-index">{i:02}</span><h2>{h(section["title"])}</h2>{paragraphs(section.get("paragraphs", []))}{bullet_list(section["bullets"]) if section.get("bullets") else ""}</section>'
    ex = item["example"]
    body += f'<section class="worked-example" id="example"><p class="eyebrow">一步步算 / 教学假设</p><h2>{h(ex["title"])}</h2>{bullet_list(ex["steps"], True)}<p class="example-conclusion">{h(ex["conclusion"])}</p></section>'
    kind = LAB_MAP.get(item["slug"])
    if kind:
        body += lab(kind)
    body += f'<section class="pitfalls"><h2>容易弄错的地方</h2>{bullet_list(item["pitfalls"])}</section><p class="takeaway"><span>带走一句话</span>{h(item["takeaway"])}</p>'
    quiz = item["quiz"]
    answers = "".join(f'<button data-answer="{i}" aria-pressed="false">{h(option)}</button>' for i, option in enumerate(quiz["options"]))
    body += f'<section class="self-check" id="self-check" data-quiz="{h(item["slug"])}" data-correct="{quiz["answer"]}" data-explanation="{h(quiz["explanation"])}"><p class="eyebrow">检查一下理解</p><h2>{h(quiz["question"])}</h2><div class="choice-buttons">{answers}</div><p class="quiz-feedback" role="status">答对后，记录本课进度。可以重复练习。</p></section>'
    body += f'<section class="lesson-sources" id="sources"><h2>本课来源与延伸阅读</h2><p>概念依据见下列原始资料；教学算例由本课程编写。平台界面、费率与可用资格可能变化。</p><ul>{source_rows(item["source_ids"])}</ul></section></article>'
    body += related_blogs(item["slug"])
    prev = lessons[index - 1] if index else None
    after = lessons[index + 1] if index + 1 < len(lessons) else None
    body += '<nav class="lesson-pagination" aria-label="前后课程">'
    body += f'<a href="/learn/{h(prev["slug"])}"><small>上一课</small>{h(prev["title"])}</a>' if prev else '<a href="/learn"><small>回到首页</small>全部学习路线</a>'
    body += f'<a href="/learn/{h(after["slug"])}"><small>下一课</small>{h(after["title"])}</a>' if after else '<a href="/learn/practice"><small>课程结束</small>回到互动练习区</a>'
    body += '</nav>'
    toc = f'<aside class="page-toc"><p>本课目录</p>{toc_items}<a href="#example">算个例子</a><a href="#self-check">自测</a><a href="#sources">来源</a></aside>'
    return shell(item["title"], reading_tools() + body, item["slug"], toc, layout="reader")


def glossary() -> str:
    lessons, _, terms = content()
    titles = {lesson["slug"]: lesson["title"] for lesson in lessons}
    unique: dict[str, dict[str, str]] = {}
    for term in terms:
        unique.setdefault(term["term"].casefold(), term)
    body = '<header class="utility-hero"><p class="eyebrow">随时回来查</p><h1>术语，不用硬背。</h1><p>先用一句白话理解，再回到对应课程看完整例子。</p></header><label class="search-label" for="term-query">搜索中文或英文术语</label><input class="wide-search" id="term-query" type="search" placeholder="例如：回撤、USDT、API"><p id="term-status" class="muted" role="status"></p><dl class="glossary-list">'
    for term in unique.values():
        body += f'<div data-term="{h(term["term"] + " " + term["definition"])}"><dt>{h(term["term"])}</dt><dd><p>{h(term["definition"])}</p><a href="/learn/{h(term["lesson"])}">继续读：{h(titles[term["lesson"]])}</a></dd></div>'
    body += '</dl><p id="term-empty" class="empty" hidden>暂时没找到这个词。换个简称试试，或从课程目录查找。</p>'
    return shell("术语词典", body, "glossary")


def sources_page() -> str:
    _, sources, _ = content()
    unique: dict[str, str] = {}
    for key, source in sources.items():
        unique.setdefault(source["url"], key)
    body = f'<header class="utility-hero"><p class="eyebrow">先看证据，再相信结论</p><h1>资料与来源。</h1><p>优先使用交易所官方文档、量化工具文档和原始研究。这里收录 {len(unique)} 个去重来源，各课会列出对应引用。</p><a href="/learn/blogs">另见：个人博客导读与原文链接</a></header><div class="editor-note"><h2>如何使用这些资料</h2><p>先读中文课程，再按需要查看原文。外链可能是英文，也可能因地区或平台调整无法访问；没有把打不开的交易功能写成已可用。</p><p>“核实日期”指查阅日期，不是资料发布日期。具体费率、交易规则、地区资格要以你实际使用时平台显示的信息为准。本课程不使用个人暴富故事证明策略有效。</p></div><ul class="source-directory">{source_rows(list(unique.values()))}</ul>'
    return shell("资料与来源", body, "sources")


def related_blogs(slug: str) -> str:
    posts = [post for post in blog_posts() if slug in post["related"]]
    if not posts:
        return ""
    links = [f'<li><a href="/learn/blogs/{h(post["slug"])}">{h(post["title"])}</a><span class="blog-meta">{h(post["site"])}</span></li>' for post in posts]
    more = f'<details><summary>展开其余 {len(links) - 4} 篇相关阅读</summary><ul>{"".join(links[4:])}</ul></details>' if len(links) > 4 else ""
    return f'<section class="blog-related"><h2>结合个人经验再读一篇</h2><p>这些是博客导读，关键规则另有官方资料对照。</p><ul>{"".join(links[:4])}</ul>{more}</section>'


def is_archived(post: dict[str, Any]) -> bool:
    return post.get("category") == "活动与旧资讯" or post["slug"] in ARCHIVED_GUIDES


def library_url(base: str, params: dict[str, str], **changes: str) -> str:
    values = {**params, **changes}
    values = {key: value for key, value in values.items() if value and not (key == "scope" and value == "learn") and not (key == "page" and value == "1")}
    return base + ("?" + urlencode(values) if values else "")


def library_sidebar(base: str, params: dict[str, str], posts: list[dict[str, Any]]) -> str:
    scope = params.get("scope", "learn")
    scoped = [p for p in posts if (scope == "all" or is_archived(p) == (scope == "archive")) and (not params.get("site") or p["site"] == params["site"])]
    selected = params.get("category", "")
    nav = '<p class="sidebar-section-label">按主题阅读</p><nav class="library-nav" aria-label="资料主题">'
    nav += f'<a href="{h(library_url(base, params, category="", page="1"))}" {"aria-current=page" if not selected else ""}><span>全部主题</span><small>{len(scoped)}</small></a>'
    categories = [*DIGITALYOMING_CATEGORIES, "其他导读"]
    for category in categories:
        count = sum(p.get("category", "其他导读") == category for p in scoped)
        if not count and selected != category:
            continue
        link = library_url(base, params, category=category, page="1")
        nav += f'<a href="{h(link)}" {"aria-current=page" if selected == category else ""}><span>{h(category)}</span><small>{count}</small></a>'
    return nav + '</nav>'


def reading_tools() -> str:
    return '<div class="reader-tools" aria-label="阅读设置" role="group" hidden><button type="button" data-reading-toggle="focus" aria-pressed="false">专注阅读</button><button type="button" data-reading-toggle="large" aria-pressed="false">大字阅读</button></div>'


def reading_rows(posts: list[dict[str, Any]]) -> str:
    rows = ''
    for post in posts:
        category = post.get("category", "其他导读")
        level = "历史资料" if is_archived(post) else post["level"]
        rows += f'<article class="reading-row"><div class="reading-row-main"><span class="reading-category">{h(category)}</span><h2><a href="/learn/blogs/{h(post["slug"])}">{h(post["title"])}</a></h2><p>{h(post["summary"])}</p></div><div class="reading-row-meta"><span>{h(level)}</span><a href="{h(post["url"])}" target="_blank" rel="noreferrer" aria-label="阅读原文：{h(post["title"])}">原文</a></div></article>'
    return rows


def blog_index(path: str = "/learn/blogs", collection: bool = False) -> str:
    posts = [p for p in blog_posts() if not collection or urlsplit(p["url"]).hostname == "digitalyoming.com"]
    base = "/learn/collections/digitalyoming" if collection else "/learn/blogs"
    query = parse_qs(urlsplit(path).query)
    params = {key: query.get(key, [""])[0][:200].strip() for key in ("q", "category", "scope", "site")}
    if params["scope"] not in {"learn", "archive", "all"}:
        params["scope"] = "learn"
    categories = {*DIGITALYOMING_CATEGORIES, "其他导读"}
    if params["category"] not in categories:
        params["category"] = ""
    sites = sorted({post["site"] for post in posts})
    if collection or params["site"] not in sites:
        params["site"] = ""
    # All matching articles are searched before pagination, including text in their guides.
    tokens = params["q"].casefold().split()
    matching = []
    scope = params["scope"]
    for post in posts:
        text = " ".join([post["title"], post.get("original_title", ""), post["site"], post["author"], post.get("category", "其他导读"), post["summary"], *post["takeaways"], *post["caveats"], *post["exercise"].values(), *post.get("tags", [])]).casefold()
        if params["site"] and post["site"] != params["site"]:
            continue
        if all(token in text for token in tokens):
            matching.append(post)
    filtered = [post for post in matching if (scope == "all" or is_archived(post) == (scope == "archive")) and (not params["category"] or post.get("category", "其他导读") == params["category"])]
    priority = {slug: i for i, (slug, _) in enumerate(STARTER_GUIDES)}
    filtered.sort(key=lambda post: (is_archived(post), priority.get(post["slug"], 99), post["level"] != "入门"))
    total = len(filtered)
    pages = max(1, (total + 11) // 12)
    try:
        page = max(1, min(pages, int(query.get("page", ["1"])[0][:8])))
    except ValueError:
        page = 1
    visible = filtered[(page - 1) * 12:page * 12]
    archived = sum(is_archived(post) for post in matching)
    title = "数位小帮手专题" if collection else "个人博客资料库"
    intro = "按主题整理这个博客的交易教程，结合例子读懂每一步。" if collection else "从个人实践里学习，把操作经验接回基础知识。"
    body = f'<header class="library-hero"><p class="eyebrow">{"个人博客 / 系统导读" if collection else "学习资料 / 个人实践"}</p><h1>{title}</h1><p>{intro}</p></header>'
    if page == 1 and not params["q"] and not params["category"] and not params["site"] and scope == "learn":
        links = ''.join(f'<li><a href="/learn/blogs/{slug}"><span>{i:02}</span>{label}</a></li>' for i, (slug, label) in enumerate(STARTER_GUIDES, 1))
        body += f'<section class="library-trail" aria-label="推荐阅读顺序"><p>刚开始？按这个顺序读</p><ol>{links}</ol></section>'
    body += f'<section id="articles" aria-label="文章目录"><div class="library-toolbar"><form action="{base}" method="get" role="search" data-library-search><label class="sr-only" for="library-query">搜索文章内容</label><input id="library-query" name="q" type="search" maxlength="200" placeholder="搜索教程，例如：现货、网格、手续费" value="{h(params["q"])}">'
    for key in ("category", "scope"):
        if params[key]:
            body += f'<input type="hidden" name="{key}" value="{h(params[key])}">'
    if not collection:
        options = '<option value="">所有博客</option>' + ''.join(f'<option {"selected" if site == params["site"] else ""}>{h(site)}</option>' for site in sites)
        body += f'<label class="sr-only" for="library-site">博客站点</label><select id="library-site" name="site">{options}</select>'
    body += '<button type="submit">搜索</button></form></div><nav class="library-tabs" aria-label="资料类型">'
    for value, label, count in (("learn", "教程与解读", len(matching) - archived), ("archive", "历史资料", archived), ("all", "全部资料", len(matching))):
        link = library_url(base, params, scope=value, category="", page="1")
        body += f'<a href="{h(link)}" {"aria-current=page" if scope == value else ""}>{label}<small>{count}</small></a>'
    body += '</nav>'
    heading = params["category"] or {"learn": "教程与解读", "archive": "历史资料", "all": "全部资料"}[scope]
    if params["q"]:
        heading = f'“{params["q"]}”的搜索结果'
    body += f'<div class="library-context"><h2>{h(heading)}</h2><span>{f"第 {(page - 1) * 12 + 1}–{min(page * 12, total)} 篇 / 共 {total} 篇" if total else "0 篇"}</span></div>'
    if scope == "archive":
        body += '<p class="article-notice">旧活动、旧产品和历史比较，仅作学习案例。原文中的资格、收益和操作入口可能已失效。</p>'
    if visible:
        body += f'<div class="reading-list">{reading_rows(visible)}</div>'
    else:
        all_link = library_url(base, params, scope="all", category="", site="", page="1")
        body += f'<div class="empty"><h2>没有找到这类文章</h2><p>试试“订单”“手续费”等短词，或扩大搜索范围。</p><a href="{h(all_link)}">在全部资料中搜索</a><a href="{base}">清除筛选</a></div>'
    if pages > 1:
        body += '<nav class="library-pagination" aria-label="文章分页">'
        if page > 1:
            body += f'<a rel="prev" href="{h(library_url(base, params, page=str(page - 1)))}#articles">上一页</a>'
        else:
            body += '<span aria-disabled="true">上一页</span>'
        body += f'<span>第 {page} / {pages} 页</span>'
        if page < pages:
            body += f'<a rel="next" href="{h(library_url(base, params, page=str(page + 1)))}#articles">下一页</a>'
        else:
            body += '<span aria-disabled="true">下一页</span>'
        body += '</nav>'
    body += '</section><p class="library-note">每篇含导读、练习和原文链接。费率、功能与地区资格以对应平台的当前规则为准。</p>'
    if not collection:
        body += '<p class="library-note"><a href="/learn/collections/digitalyoming">单独阅读数位小帮手专题</a></p>'
    records = crawl_records()
    captured = sum(records.get(post["slug"], {}).get("status") == "ok" for post in posts)
    body += f'<details class="library-footnote"><summary>资料来源与整理说明</summary><p>本站提供短导读与原创练习，完整图文请阅读作者原文。{len(posts)} 篇资料中，{captured} 篇已保存本地研究缓存，缓存不公开展示。</p>'
    if collection:
        try:
            discovery = json.loads(DISCOVERY_MANIFEST.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            discovery = {}
        body += f'<p>发现时间：{h(discovery.get("discovered_at", "尚未记录"))}。站点目录包含 {h(discovery.get("all_article_count", "尚未记录"))} 篇；本次相关文章 {len(discovery.get("selected", []))} 篇。</p><p>{h(discovery.get("scope", "以本次公开链接发现为准。"))}</p>'
        missing = [item for item in discovery.get("selected", []) if item.get("status") != "ok"]
        if missing:
            body += '<ul>' + ''.join(f'<li><a href="{h(item["url"])}">{h(item.get("title") or item["url"])}</a>：{h(item.get("status"))}</li>' for item in missing) + '</ul>'
    body += '</details>'
    current = "collections/digitalyoming" if collection else "blogs"
    sidebar = library_sidebar(base, params, matching)
    return shell(title, body, current, layout="library", sidebar_content=sidebar)


def digitalyoming_collection(path: str = "/learn/collections/digitalyoming") -> str:
    return blog_index(path, collection=True)


def blog_page(post: dict[str, Any]) -> str:
    lessons = {item["slug"]: item for item in content()[0]}
    record = crawl_records().get(post["slug"], {})
    digital = urlsplit(post["url"]).hostname == "digitalyoming.com"
    base = "/learn/collections/digitalyoming" if digital else "/learn/blogs"
    back_label = "数位小帮手专题" if digital else "个人博客资料库"
    category = post.get("category", "其他导读")
    archived = is_archived(post)
    context = {"category": category, "scope": "archive" if archived else "learn"}
    back = library_url(base, context)
    body = f'<nav class="breadcrumb" aria-label="当前位置"><a href="{base}">{back_label}</a><span>/</span><a href="{h(back)}">{h(category)}</a></nav>{reading_tools()}'
    body += f'<article class="blog-library"><header class="article-header"><p class="eyebrow">{h(category)} / {"历史资料" if archived else h(post["level"])}</p><h1>{h(post["title"])}</h1><p class="article-summary">{h(post["summary"])}</p><div class="article-byline"><span>{h(post["site"])}</span><span>整理于 {h(post["checked"])}</span><a href="{h(post["url"])}" target="_blank" rel="noreferrer">阅读作者原文</a></div></header>'
    if archived:
        body += '<p class="article-notice">这是一篇历史资料，适合研究原理；原文活动、产品和操作入口可能已失效。</p>'
    body += f'<section class="prose-section" id="blog-takeaways"><h2>读懂这篇的重点</h2>{bullet_list(post["takeaways"])}</section>'
    body += f'<section class="prose-section" id="blog-check"><h2>阅读时需要留意</h2>{bullet_list(post["caveats"])}</section>'
    exercise = post["exercise"]
    body += f'<section class="worked-example" id="blog-practice"><p class="eyebrow">动手想一想 / 教学假设</p><h2>{h(exercise["title"])}</h2><p>{h(exercise["prompt"])}</p><details><summary>查看解释</summary><p>{h(exercise["answer"])}</p></details><a href="/learn/practice">去互动练习里试一试</a></section>'
    body += '<section class="blog-related" id="blog-next"><h2>继续学习</h2><ul>'
    for slug in post["related"]:
        body += f'<li><a href="/learn/{h(slug)}">{h(lessons[slug]["title"])}</a><span>{h(lessons[slug]["subtitle"])}</span></li>'
    body += '</ul></section><section class="lesson-sources" id="blog-sources"><h2>对照官方资料</h2><ul>'
    for source in post["official_sources"]:
        body += f'<li><a href="{h(source["url"])}" target="_blank" rel="noreferrer">{h(source["title"])}</a></li>'
    body += '</ul><p class="muted">以上是本站的导读与阅读提醒。平台的现行条款、费率和地区资格，仍需分别确认。</p></section>'
    body += f'<details class="blog-source" id="blog-provenance"><summary>原文信息与采集记录</summary><p>作者：{h(post["author"])}；语言：{h(post["language"])}。</p><p>原文标题：{h(post.get("original_title", post["title"]))}</p><p><a href="{h(post["url"])}" target="_blank" rel="noreferrer">{h(post["url"])}</a></p><p>本站只展示短导读和原创练习。完整图文属于原作者；整理日期表示阅读时间。</p>'
    if record:
        body += f'<p class="muted">采集时间：{h(record.get("fetched_at", "未记录"))}；状态：{h(record.get("status", "unknown"))}；HTTP：{h(record.get("http_status", "未记录"))}</p>'
        if record.get("sha256"):
            body += f'<p class="muted">缓存摘要 SHA-256：<code>{h(record["sha256"])}</code></p>'
        if record.get("message"):
            body += f'<pre>{h(record["message"])}</pre>'
    body += f'</details></article><nav class="lesson-pagination" aria-label="继续阅读"><a href="{h(back)}"><small>继续这个主题</small>{h(category)}</a><a href="/learn"><small>从头学习</small>基础课程</a></nav>'
    toc = '<aside class="page-toc"><p>本页内容</p><a href="#blog-takeaways">阅读重点</a><a href="#blog-check">需要留意</a><a href="#blog-practice">动手练习</a><a href="#blog-next">继续学习</a><a href="#blog-sources">官方资料</a></aside>'
    posts = [p for p in blog_posts() if not digital or urlsplit(p["url"]).hostname == "digitalyoming.com"]
    return shell(post["title"], body, "collections/digitalyoming" if digital else "blogs", toc, layout="reader", sidebar_content=library_sidebar(base, context, posts))


def practice() -> str:
    labels = {"pnl": "买卖盈亏", "candle": "认识 K 线", "order": "限价成交", "fees": "成本与回本", "leverage": "杠杆放大", "sizing": "风险与仓位", "recovery": "亏损回本", "expectancy": "交易期望", "signal": "条件信号", "bias": "识别前视偏差"}
    body = '<header class="utility-hero"><p class="eyebrow">把抽象概念变成手上的数字</p><h1>十个小实验。</h1><p>自由拖动、反复比较。所有数字都是教学假设，不读取行情、不下单，也不会改变模拟操作台的账本。</p></header><nav class="lab-index" aria-label="实验目录">'
    body += "".join(f'<a href="#lab-{key}">{label}</a>' for key, label in labels.items()) + '</nav>'
    body += "".join(lab(key) for key in labels)
    return shell("互动练习区", body, "practice")


def render(path: str) -> str | None:
    route = urlsplit(path).path.rstrip("/")
    if route == "/learn":
        return home()
    if route == "/learn/glossary":
        return glossary()
    if route == "/learn/sources":
        return sources_page()
    if route == "/learn/practice":
        return practice()
    if route == "/learn/blogs":
        return blog_index(path)
    if route == "/learn/collections/digitalyoming":
        return digitalyoming_collection(path)
    for post in blog_posts():
        if route == f'/learn/blogs/{post["slug"]}':
            return blog_page(post)
    for lesson in content()[0]:
        if route == f'/learn/{lesson["slug"]}':
            return lesson_page(lesson)
    return None
