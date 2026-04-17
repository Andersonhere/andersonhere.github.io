#!/usr/bin/env python3
"""Insert excerpt_image into _posts front matter for Theme Yat list thumbnails."""
from __future__ import annotations

import re
import sys
from pathlib import Path

POSTS = Path(__file__).resolve().parent.parent / "_posts"

IMG_OSTEP = "/images/homepage/5833e314e4402.jpeg"
IMG_CPP = "/images/homepage/7e58f9564691a8.png"
IMG_JEKYLL = "/images/jekyll-logo.png"
IMG_LINUX = "/images/first-post.png"
IMG_LEGACY = "/images/config.png"


def pick_image(fm: str, filename: str) -> str:
    blob = fm + "\n" + filename
    if "OSTEP" in blob:
        return IMG_OSTEP
    if re.search(r"现代 C\+\+|categories:.*C\+\+", blob) or "cpp-virtual-function" in filename:
        return IMG_CPP
    if re.search(r"tags:.*Linux|Linux进程调度", blob):
        return IMG_LINUX
    if "Jekyll" in blob or "welcome-to-jekyll" in filename:
        return IMG_JEKYLL
    if "Hello-World" in filename or "2014-3-3" in filename:
        return IMG_LEGACY
    if "操作系统" in blob:
        return IMG_OSTEP
    return IMG_OSTEP


def insert_after_tags(fm_lines: list[str], img: str) -> list[str]:
    out: list[str] = []
    inserted = False
    for line in fm_lines:
        out.append(line)
        if not inserted and line.startswith("tags:"):
            out.append(f"excerpt_image: {img}")
            inserted = True
    if not inserted:
        out.append(f"excerpt_image: {img}")
    return out


def patch_with_front_matter(raw: str, path: Path) -> str | None:
    if not raw.startswith("---"):
        return None
    parts = raw.split("---", 2)
    if len(parts) < 3:
        return None
    fm = parts[1]
    rest = parts[2]
    if "excerpt_image:" in fm:
        return raw
    img = pick_image(fm, path.name)
    lines = fm.lstrip("\n").rstrip("\n").split("\n")
    new_fm = "\n".join(insert_after_tags(lines, img))
    return f"---\n{new_fm}\n---{rest}"


def prepend_front_matter(raw: str, path: Path) -> str:
    img = pick_image("", path.name)
    if path.name.startswith("2025-11-23") and "CPU" in path.name:
        fm = f"""---
title: CPU 与操作系统（笔记）
date: 2025-11-23 12:00:00 +0800
categories: [操作系统]
tags: [CPU, 操作系统]
excerpt_image: {img}
---

"""
    elif "Operating-system" in path.name or "O-system" in path.name:
        fm = f"""---
title: 操作系统学习记录
date: 2025-11-16 12:00:00 +0800
categories: [操作系统]
tags: [操作系统, 虚拟化]
excerpt_image: {img}
---

"""
    else:
        fm = f"""---
title: Post
date: 2014-03-03 12:00:00 +0800
excerpt_image: {img}
---

"""
    return fm + raw


def main() -> int:
    changed = 0
    for path in sorted(POSTS.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        if raw.startswith("---") and raw.count("---") >= 2:
            new = patch_with_front_matter(raw, path)
            if new is None:
                continue
            if new != raw:
                path.write_text(new, encoding="utf-8")
                changed += 1
        else:
            new = prepend_front_matter(raw, path)
            if new != raw:
                path.write_text(new, encoding="utf-8")
                changed += 1
    print(f"updated {changed} files", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
