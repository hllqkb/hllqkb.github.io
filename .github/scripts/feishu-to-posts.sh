#!/bin/bash
# 把 Elog 输出的 _feishu/<文档id>.md 整理成 Jekyll 要求的 _posts/feishu/<日期>-<文档id>.md。
# 每次整体重建，飞书里删掉的文章（Elog 删掉的输出文件）也会从 _posts 里消失。
set -euo pipefail

src="_feishu"
dst="_posts/feishu"

rm -rf "$dst"
mkdir -p "$dst"

shopt -s nullglob
for f in "$src"/*.md; do
  name="$(basename "$f")"
  # Elog 写的 date 形如 '2026-10-27 22:49:28'，取前 10 位当文件名日期
  day="$(awk '/^date:/ { gsub(/["'"'"']/, "", $2); print $2; exit }' "$f")"
  if [[ ! "$day" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
    echo "skip $name: front matter 缺少合法的 date" >&2
    continue
  fi
  cp "$f" "$dst/$day-$name"
done

echo "synced $(find "$dst" -name '*.md' | wc -l | tr -d ' ') feishu posts"
