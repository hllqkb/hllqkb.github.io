"""Export only the public learning site; run by GitHub Actions."""
from __future__ import annotations

import argparse
import json
import re
import shutil
from html import escape, unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import academy

ROOT = Path(__file__).resolve().parent


def public_url(value: str, prefix: str) -> str:
    url = urlsplit(unescape(value))
    if url.scheme or url.netloc or not url.path.startswith("/"):
        return value
    route = url.path
    if route == "/":
        route = "/learn/practice"
    if route.startswith("/learn"):
        route = route.rstrip("/") + "/"
    elif route in {"/academy.css", "/academy.js"}:
        route = "/academy-assets" + route
    else:
        raise ValueError(f"Unsupported public route: {route}")
    return escape(urlunsplit(("", "", prefix + route, url.query, url.fragment)), quote=True)


def transform(document: str, prefix: str) -> str:
    document = re.sub(r'(href|src|action)="([^"]*)"',
                      lambda m: f'{m[1]}="{public_url(m[2], prefix)}"', document)
    document = document.replace('<body ', f'<body data-base-path="{escape(prefix)}" ')
    document = document.replace('>模拟操作台</a>', '>互动练习</a>')
    document = document.replace('文章、资料搜索和分页可以正常使用；互动计算器、课程筛选和进度保存需要 JavaScript。',
                                '文章正文可以直接阅读；搜索、分页、互动计算器和进度保存需要 JavaScript。')
    document = re.sub(r'<details class="library-footnote">.*?</details>',
                      '<details class="library-footnote"><summary>资料来源与整理说明</summary>'
                      '<p>本站提供短导读与原创练习，保留作者署名及原文链接。完整图文请阅读作者原文。</p></details>',
                      document, flags=re.S)
    return document


class LinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if name in {"href", "src", "action"} and value:
                self.links.append(value)


def export(output: Path, prefix: str) -> None:
    if output.exists():
        raise ValueError("Output must be a new directory")
    output.mkdir(parents=True)
    # Private crawl data is deliberately unavailable to the public renderer.
    academy.CRAWL_MANIFEST = output / "unpublished-manifest.json"
    academy.DISCOVERY_MANIFEST = output / "unpublished-discovery.json"
    routes = ["/learn", "/learn/practice", "/learn/glossary", "/learn/sources",
              "/learn/blogs", "/learn/collections/digitalyoming"]
    routes.extend(f'/learn/{item["slug"]}' for item in academy.content()[0])
    routes.extend(f'/learn/blogs/{post["slug"]}' for post in academy.blog_posts())
    assets = output / "academy-assets"
    assets.mkdir()
    for name in ("academy.css", "academy.js", "pages-library.js"):
        shutil.copyfile(ROOT / "static" / name, assets / name)
    for route in routes:
        document = academy.render(route)
        if document is None:
            raise ValueError(f"Missing page: {route}")
        document = transform(document, prefix)
        if route in {"/learn/blogs", "/learn/collections/digitalyoming"}:
            collection = route.endswith("digitalyoming")
            entries = []
            priority = dict((slug, i) for i, (slug, _) in enumerate(academy.STARTER_GUIDES))
            for post in academy.blog_posts():
                if collection and urlsplit(post["url"]).hostname != "digitalyoming.com":
                    continue
                search = " ".join([post["title"], post.get("original_title", ""), post["site"],
                                   post["author"], post.get("category", "其他导读"), post["summary"],
                                   *post["takeaways"], *post["caveats"],
                                   *post["exercise"].values(), *post.get("tags", [])])
                entries.append({"category": post.get("category", "其他导读"), "site": post["site"],
                                "archived": academy.is_archived(post), "search": search,
                                "rank": priority.get(post["slug"], 99), "advanced": post["level"] != "入门",
                                "html": transform(academy.reading_rows([post]), prefix)})
            payload = json.dumps({"entries": entries, "categories": [*academy.DIGITALYOMING_CATEGORIES, "其他导读"]},
                                 ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
            script = f'<script type="application/json" id="library-data">{payload}</script>'
            script += f'<script src="{prefix}/academy-assets/pages-library.js" defer></script>'
            document = document.replace('</body>', script + '</body>')
        destination = output / route.lstrip("/") / "index.html"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(document, encoding="utf-8")
    # Fail the CI build on broken internal links before publishing.
    for page in output.rglob("*.html"):
        parser = LinkCollector()
        parser.feed(page.read_text(encoding="utf-8"))
        for link in parser.links:
            url = urlsplit(link)
            if url.scheme or url.netloc or not url.path.startswith("/"):
                continue
            local = url.path[len(prefix):] if prefix else url.path
            target = output / local.lstrip("/")
            if not (target.is_file() or (target / "index.html").is_file()):
                raise ValueError(f"Broken link in {page}: {link}")
    print(f"Exported {len(routes)} learning pages; internal links validated.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--base-path", default="")
    args = parser.parse_args()
    prefix = args.base_path.rstrip("/")
    if prefix and not re.fullmatch(r"/[A-Za-z0-9_/-]+", prefix):
        parser.error("base-path must be an absolute URL path")
    export(args.output, prefix)


if __name__ == "__main__":
    main()
