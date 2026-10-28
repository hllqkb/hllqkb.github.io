#!/usr/bin/env python3
"""生成「每日速递」：搜索 / 推荐 / 3D 生成 / Agent 方向的公开动态摘要。

来源只取标题、摘要和链接：Hugging Face Daily Papers、arXiv（cs.IR、cs.GR）、Hacker News。
模型只负责挑选和写中文摘要；链接、标题、来源一律取自抓到的候选，不用模型输出。

用法：python3 daily_digest.py <输出目录 _daily> <已发记录 _data/digest_seen.json>
环境变量：GEMINI_API_KEY（必填）、GEMINI_MODEL（默认 gemini-2.5-flash）、DIGEST_DATE（默认北京时间今天）
退出码：0 = 已生成或当天条目不足而跳过；1 = 出错。
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

BEIJING = timezone(timedelta(hours=8))
MIN_ITEMS = 5
MAX_ITEMS = 12
HN_KEYWORDS = re.compile(
    r"\b(search|recommend\w*|ranking|retrieval|rag|embedding|vector|llm|agent\w*|3d|gaussian|mesh|diffusion)\b",
    re.IGNORECASE,
)
USER_AGENT = "hllqkb-daily-digest/1.0 (+https://hllqkb.github.io/)"


@dataclass
class Candidate:
    key: str  # 去重键：arXiv 编号或规范化 URL
    source: str
    title: str
    url: str
    abstract: str


def http_get(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def arxiv_key(text: str) -> str | None:
    m = re.search(r"(\d{4}\.\d{4,5})", text)
    return f"arxiv:{m.group(1)}" if m else None


def normalize_url(url: str) -> str:
    parts = urllib.parse.urlsplit(url.strip())
    return f"url:{parts.netloc.lower().removeprefix('www.')}{parts.path.rstrip('/')}"


def fetch_hf() -> list[Candidate]:
    data = json.loads(http_get("https://huggingface.co/api/daily_papers?limit=50"))
    data.sort(key=lambda d: d.get("paper", {}).get("upvotes", 0), reverse=True)
    out: list[Candidate] = []
    for d in data[:12]:
        paper = d.get("paper", {})
        pid = paper.get("id", "")
        if not pid:
            continue
        out.append(Candidate(f"arxiv:{pid}", "Hugging Face Daily Papers", paper.get("title", "").strip(),
                             f"https://huggingface.co/papers/{pid}", (paper.get("summary") or "").strip()))
    return out


def fetch_arxiv(category: str, limit: int) -> list[Candidate]:
    q = urllib.parse.urlencode({"search_query": f"cat:{category}", "sortBy": "submittedDate",
                                "sortOrder": "descending", "max_results": limit})
    root = ET.fromstring(http_get(f"https://export.arxiv.org/api/query?{q}", timeout=60))
    ns = {"a": "http://www.w3.org/2005/Atom"}
    out: list[Candidate] = []
    for e in root.findall("a:entry", ns):
        abs_url = (e.findtext("a:id", "", ns) or "").strip()
        key = arxiv_key(abs_url)
        if not key:
            continue
        title = " ".join((e.findtext("a:title", "", ns) or "").split())
        summary = " ".join((e.findtext("a:summary", "", ns) or "").split())
        out.append(Candidate(key, f"arXiv {category}", title, re.sub(r"v\d+$", "", abs_url), summary))
    return out


def fetch_hn(limit: int = 60) -> list[Candidate]:
    ids = json.loads(http_get("https://hacker-news.firebaseio.com/v0/topstories.json"))[:limit]
    out: list[Candidate] = []
    for i in ids:
        item = json.loads(http_get(f"https://hacker-news.firebaseio.com/v0/item/{i}.json"))
        title = (item or {}).get("title", "")
        if not title or not HN_KEYWORDS.search(title):
            continue
        url = item.get("url") or f"https://news.ycombinator.com/item?id={i}"
        key = arxiv_key(url) or normalize_url(url)
        out.append(Candidate(key, "Hacker News", title, url, ""))  # HN 只有标题
    return out


def collect(seen: set[str]) -> list[Candidate]:
    fetchers = [fetch_hf, lambda: fetch_arxiv("cs.IR", 12), lambda: fetch_arxiv("cs.GR", 8), fetch_hn]
    by_key: dict[str, Candidate] = {}
    for fetch in fetchers:
        try:
            items = fetch()
        except Exception as exc:  # 单个来源失败不影响其他来源
            print(f"source failed: {exc}", file=sys.stderr)
            continue
        for c in items:
            if c.key in seen or not c.title:
                continue
            by_key.setdefault(c.key, c)  # 同一篇论文在 HF 和 arXiv 只留先到的一条
    return list(by_key.values())


PROMPT = """你是技术编辑，为一个后端工程师的个人博客挑选今天值得看的动态，方向：搜索、推荐、信息检索、3D 生成、LLM Agent 工程。
下面是候选（JSON），每条有 idx、来源、标题、摘要（可能为空）。
规则：
1. 挑 {lo} 到 {hi} 条最相关、最有信息量的；不相关的宁缺毋滥。
2. 每条只根据给出的标题和摘要写，不得补充候选里没有的方法、数字或结论。
3. summary：2 句中文，说清做了什么。摘要为空时只能复述标题含义，并在 limits 里写「只有标题，未读原文」。
4. why：1 句，说明对做搜索/推荐/3D/Agent 工程的人具体有什么用；不要写「对工程师有价值」这类空话。
5. limits：1 句，写信息缺口或适用边界，如「摘要未给实验规模」「仅在英文数据集上评测」。
6. title_zh：中文标题，简短。
只输出 JSON。
候选：
{candidates}
"""

SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "idx": {"type": "integer"},
                    "title_zh": {"type": "string"},
                    "summary": {"type": "string"},
                    "why": {"type": "string"},
                    "limits": {"type": "string"},
                },
                "required": ["idx", "title_zh", "summary", "why", "limits"],
            },
        }
    },
    "required": ["items"],
}


def ask_gemini(cands: list[Candidate], api_key: str, model: str) -> list[dict]:
    payload = [{"idx": i, "source": c.source, "title": c.title, "abstract": c.abstract[:1200]}
               for i, c in enumerate(cands)]
    body = {
        "contents": [{"parts": [{"text": PROMPT.format(lo=MIN_ITEMS, hi=MAX_ITEMS,
                                                      candidates=json.dumps(payload, ensure_ascii=False))}]}],
        "generationConfig": {"responseMimeType": "application/json", "responseSchema": SCHEMA,
                             "temperature": 0.3},
    }
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(text)["items"]


def clean(text: str) -> str:
    # 去掉换行和可能漏出来的候选编号，避免破坏 Markdown 列表
    text = re.sub(r"\b(?:idx|候选)\s*[#:：]?\s*\d+\b", "", text)
    return " ".join(text.replace("|", "／").split())


def render(day: str, picked: list[tuple[Candidate, dict]], model: str) -> str:
    lines = [
        "---",
        "layout: post",
        f'title: "每日速递 {day}"',
        f"date: {day} 09:00:00 +0800",
        "tags: [每日速递]",
        f'subtitle: "搜索 / 推荐 / 3D / Agent，{len(picked)} 条"',
        "---",
        "",
        f"> AI 整理（{model}），以原文链接为准。每条只根据标题和摘要撰写。",
        "",
    ]
    for n, (c, it) in enumerate(picked, 1):
        lines += [
            f"### {n}. {clean(it['title_zh'])}",
            "",
            f"{clean(it['summary'])}",
            "",
            f"- **为什么值得看**：{clean(it['why'])}",
            f"- **局限**：{clean(it['limits'])}",
            f"- **原文**：[{clean(c.title).replace('[', '［').replace(']', '］')}]({c.url})（{c.source}）",
            "",
        ]
    return "\n".join(lines)


def main(out_dir: Path, seen_path: Path) -> int:
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("GEMINI_API_KEY not set; skip")
        return 0
    model = os.environ.get("GEMINI_MODEL") or "gemini-2.5-flash"
    day = os.environ.get("DIGEST_DATE") or datetime.now(BEIJING).strftime("%Y-%m-%d")
    out_file = out_dir / f"{day}.md"
    if out_file.exists():
        print(f"{out_file} exists; skip")
        return 0

    seen: dict[str, str] = json.loads(seen_path.read_text()) if seen_path.exists() else {}
    cands = collect(set(seen))
    print(f"{len(cands)} candidates")
    if len(cands) < MIN_ITEMS:
        print("not enough candidates; skip")
        return 0

    picked: list[tuple[Candidate, dict]] = []
    used: set[int] = set()
    for it in ask_gemini(cands, api_key, model):
        idx = it.get("idx")
        # 只接受真实存在、未重复的候选；链接与标题取自候选本身
        if not isinstance(idx, int) or not 0 <= idx < len(cands) or idx in used:
            continue
        if not all(str(it.get(k, "")).strip() for k in ("title_zh", "summary", "why", "limits")):
            continue
        used.add(idx)
        picked.append((cands[idx], it))
    picked = picked[:MAX_ITEMS]
    if len(picked) < MIN_ITEMS:
        print(f"only {len(picked)} valid items; skip")
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    out_file.write_text(render(day, picked, model), encoding="utf-8")
    for c, _ in picked:
        seen[c.key] = day
    # 只保留最近 60 天的记录，文件不会无限增长
    cutoff = (datetime.strptime(day, "%Y-%m-%d") - timedelta(days=60)).strftime("%Y-%m-%d")
    seen = {k: v for k, v in seen.items() if v >= cutoff}
    seen_path.parent.mkdir(parents=True, exist_ok=True)
    seen_path.write_text(json.dumps(seen, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
    print(f"wrote {out_file} with {len(picked)} items")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    sys.exit(main(Path(sys.argv[1]), Path(sys.argv[2])))
