#!/usr/bin/env python3
"""把构建产物里的文章图片地址改写到图床（Cloudflare R2）。

仓库里正文写的是站内路径 /assets/img/posts/<文件>，本地预览直接可用；
发布前把 _site 里的这些地址换成 <IMAGE_CDN_BASE>/posts/<文件>，
并删除 _site/assets/img/posts，线上站点不再携带原图。

用法：python3 rewrite_image_urls.py <site_dir> <cdn_base> <site_url>
"""
import re
import shutil
import sys
from pathlib import Path

LOCAL_PREFIX = "/assets/img/posts/"
TEXT_SUFFIXES = {".html", ".xml", ".json", ".txt"}


def build_pattern(site_url: str) -> re.Pattern[str]:
    # 匹配站点绝对地址（feed 里用）或站内绝对路径；
    # 站内路径前面不能是字母数字、点、冒号或斜杠，避免改到别的域名下的同名路径。
    return re.compile(
        "(?:" + re.escape(site_url.rstrip("/")) + r"|(?<![\w.:/]))" + re.escape(LOCAL_PREFIX)
    )


def rewrite_file(path: Path, pattern: re.Pattern[str], replacement: str) -> int:
    text = path.read_text(encoding="utf-8")
    new_text, count = pattern.subn(replacement, text)
    if count:
        path.write_text(new_text, encoding="utf-8")
    return count


def main(site_dir: Path, cdn_base: str, site_url: str) -> None:
    replacement = cdn_base.rstrip("/") + "/posts/"
    pattern = build_pattern(site_url)
    total = 0
    for path in site_dir.rglob("*"):
        if path.is_file() and path.suffix in TEXT_SUFFIXES:
            total += rewrite_file(path, pattern, replacement)
    shutil.rmtree(site_dir / LOCAL_PREFIX.strip("/"), ignore_errors=True)
    print(f"rewrote {total} image URL(s) to {replacement}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(Path(sys.argv[1]), sys.argv[2], sys.argv[3])
