#!/usr/bin/env python3
"""Fix OSTEP post ordering for Jekyll previous/next; remove broken in-body nav links."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POSTS = ROOT / "_posts"

# 正文中常见为中文冒号 「：」
NAV_LINE = re.compile(r"^\*\*(上一章|下一章)\*\*[：:].+$", re.MULTILINE)
FM_SPLIT = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*\r?\n", re.DOTALL)


def split_front_matter(raw: str) -> tuple[str, str] | tuple[None, None]:
    m = FM_SPLIT.match(raw)
    if not m:
        return None, None
    return m.group(1), raw[m.end() :]


def join_front_matter(fm: str, body: str) -> str:
    return "---\n" + fm.strip() + "\n---\n" + body


def main() -> None:
    for path in sorted(POSTS.glob("2026-04-17-第*.md")):
        m = re.match(r"2026-04-17-第(\d+)章", path.name)
        if not m:
            continue
        ch = int(m.group(1))
        new_date = f"date: 2026-04-17 00:{ch:02d}:00 +0800"
        raw = path.read_text(encoding="utf-8")
        fm, body = split_front_matter(raw)
        if fm is None:
            print(f"skip (no fm): {path.name}")
            continue
        if re.search(r"^date:", fm, flags=re.M):
            fm = re.sub(r"^date:.*$", new_date, fm, count=1, flags=re.M)
        else:
            fm = fm.rstrip() + "\n" + new_date + "\n"
        body = NAV_LINE.sub("", body)
        path.write_text(join_front_matter(fm, body), encoding="utf-8")
        print(f"ok {path.name} -> {new_date}")

    welcome = POSTS / "2026-04-17-welcome-to-jekyll-theme-yat.md"
    if welcome.exists():
        raw = welcome.read_text(encoding="utf-8")
        fm, body = split_front_matter(raw)
        if fm is not None:
            wdate = "date: 2026-04-17 01:00:00 +0800"
            if re.search(r"^date:", fm, flags=re.M):
                fm = re.sub(r"^date:.*$", wdate, fm, count=1, flags=re.M)
            else:
                fm = fm.rstrip() + "\n" + wdate + "\n"
            welcome.write_text(join_front_matter(fm, body), encoding="utf-8")
            print(f"ok welcome -> {wdate} (after all chapters in prev/next)")


if __name__ == "__main__":
    main()
