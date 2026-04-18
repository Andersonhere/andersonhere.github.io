#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Assign unique Wikimedia Commons thumbnails as per-post excerpt_image.

Run from blog/ repo root:
  python3 _scripts/assign_commons_covers.py

Requires outbound HTTPS. Uses a descriptive User-Agent (required by Wikimedia).
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "_posts"
COVERS = ROOT / "images" / "covers"

UA = (
    "WorkGuideBlogCover/1.0 "
    "(https://andersonhere.github.io; educational; source=wikimedia.commons)"
)

GOOD_EXT = (".jpg", ".jpeg", ".png", ".svg", ".webp")


def api(params: dict) -> dict:
    q = urllib.parse.urlencode(params, safe="|")
    url = "https://commons.wikimedia.org/w/api.php?" + q
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def drain_category(cat: str, limit: int) -> list[str]:
    titles: list[str] = []
    cont: dict[str, str] = {}
    while len(titles) < limit:
        params: dict[str, str] = {
            "action": "query",
            "format": "json",
            "list": "categorymembers",
            "cmtitle": cat,
            "cmtype": "file",
            "cmlimit": "50",
        }
        params.update(cont)
        data = api(params)
        batch = data.get("query", {}).get("categorymembers", [])
        if not batch:
            break
        for m in batch:
            t = m.get("title", "")
            if not t.startswith("File:"):
                continue
            low = t.lower()
            if not any(low.endswith(e) for e in GOOD_EXT):
                continue
            if t not in titles:
                titles.append(t)
            if len(titles) >= limit:
                break
        cont_block = data.get("continue")
        if not cont_block:
            break
        cont = {k: str(v) for k, v in cont_block.items()}
        time.sleep(0.35)
    return titles[:limit]


def imageinfo_thumb(titles: list[str]) -> dict[str, str]:
    """Map File: title -> thumb URL (800px wide)."""
    out: dict[str, str] = {}
    for i in range(0, len(titles), 45):
        chunk = titles[i : i + 45]
        data = api(
            {
                "action": "query",
                "format": "json",
                "prop": "imageinfo",
                "titles": "|".join(chunk),
                # iiurlwidth needs a valid iiprop; "thumburl" alone is rejected by the API.
                "iiprop": "url",
                "iiurlwidth": "900",
            }
        )
        for _pid, page in data.get("query", {}).get("pages", {}).items():
            if "missing" in page:
                continue
            t = page.get("title")
            ii = (page.get("imageinfo") or [{}])[0]
            tu = ii.get("thumburl")
            if t and tu:
                out[t] = tu
        time.sleep(0.35)
    return out


def read_title(md: Path) -> str:
    text = md.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return md.stem
    end = text.find("\n---\n", 4)
    if end == -1:
        return md.stem
    fm = text[4:end]
    m = re.search(r"^title:\s*(.+)$", fm, re.MULTILINE)
    if not m:
        return md.stem
    return m.group(1).strip().strip("\"'")


def pool_key(title: str, stem: str) -> str:
    blob = f"{title} {stem}"
    s = blob

    if "virtual-function" in stem or "vtable" in stem or "C++" in title:
        return "source_code"
    if "Hello" in stem or "running" in title:
        return "source_code"
    if "jekyll" in stem.lower() or "Yat" in title or "Jekyll" in title:
        return "source_code"
    if stem.endswith("CPU") or ("CPU" in title and "笔记" in title):
        return "cpu"
    if "Linux" in title and "调度" in title:
        return "kernel"
    if "Operating-system" in stem or "操作系统学习" in title:
        return "os"

    rules: list[tuple[tuple[str, ...], str]] = [
        (("分布式", "NFS", "AFS", "网络文件"), "network"),
        (
            (
                "RAID",
                "磁盘驱动",
                "文件系统",
                "崩溃一致性",
                "日志结构",
                "局部性",
                "数据完整性",
                "插叙：文件",
                "磁盘阵列",
                "Andrew 文件系统",
            ),
            "disk_fs",
        ),
        (("I/O", "I-O", "I／O", "设备"), "io"),
        (
            (
                "分页",
                "TLB",
                "分段",
                "地址空间",
                "地址转换",
                "空闲空间",
                "超越物理",
                "VAX",
                "内存操作",
                "虚拟内存",
                "内存虚拟化",
                "机制：地址",
            ),
            "memory",
        ),
        (
            (
                "调度",
                "MLFQ",
                "比例份额",
                "多处理器",
                "进程",
                "受限直接",
                "进程 API",
                "CPU 虚拟",
            ),
            "cpu_sched",
        ),
        (
            (
                "锁",
                "信号量",
                "条件变量",
                "并发",
                "线程",
                "基于锁",
                "基于事件",
                "常见并发",
            ),
            "concurrent",
        ),
        (("关于本书", "操作系统介绍", "关于虚拟化", "关于持久性"), "books_os"),
        (("对话",), "dialog"),
    ]
    for keys, key in rules:
        for k in keys:
            if k in s:
                return key
    return "general"


def build_pools() -> dict[str, deque[str]]:
    spec: list[tuple[str, list[str]]] = [
        ("network", ["Category:Computer networks"]),
        ("disk_fs", ["Category:File systems", "Category:RAID", "Category:Hard disk drives"]),
        ("memory", ["Category:Computer memory", "Category:Paging"]),
        ("cpu_sched", ["Category:Microprocessors", "Category:Computer hardware"]),
        ("concurrent", ["Category:Operating system technology", "Category:Computer programming"]),
        ("io", ["Category:Computer keyboards", "Category:Computer mice"]),
        ("source_code", ["Category:Source code", "Category:Computer programming"]),
        ("kernel", ["Category:Linux kernel", "Category:Operating system kernels"]),
        ("cpu", ["Category:Microprocessors", "Category:Central processing units"]),
        ("os", ["Category:Operating systems", "Category:Computer hardware"]),
        ("books_os", ["Category:Bookshelves", "Category:Operating systems"]),
        ("dialog", ["Category:Bookshelves", "Category:Operating system technology"]),
        ("general", ["Category:Computer hardware", "Category:Electronics"]),
    ]
    pools: dict[str, deque[str]] = defaultdict(deque)
    seen: set[str] = set()
    for name, cats in spec:
        need = 22 if name in {"general", "cpu_sched", "memory"} else 16
        got: list[str] = []
        for cat in cats:
            for t in drain_category(cat, 40):
                if t in seen:
                    continue
                seen.add(t)
                got.append(t)
                if len(got) >= need:
                    break
            if len(got) >= need:
                break
        pools[name] = deque(got)
    return pools


def pick_file(pools: dict[str, deque[str]], used: set[str], key: str) -> str | None:
    for k in (key, "general", "os", "cpu_sched", "memory", "disk_fs", "network"):
        dq = pools.get(k)
        if not dq:
            continue
        while dq:
            t = dq.popleft()
            if t not in used:
                used.add(t)
                return t
    return None


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(6):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                dest.write_bytes(r.read())
            break
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 5:
                wait = 8 * (attempt + 1)
                print(f"  429, sleep {wait}s then retry ({attempt + 1}/5)…")
                time.sleep(wait)
                continue
            raise
    time.sleep(0.55)


def set_excerpt_image(md: Path, url_path: str) -> None:
    text = md.read_text(encoding="utf-8")
    if re.search(r"(?m)^excerpt_image:\s*", text):
        text_new = re.sub(
            r"(?m)^excerpt_image:\s*.*$",
            f"excerpt_image: {url_path}",
            text,
            count=1,
        )
    else:
        text_new = re.sub(
            r"(?m)^(---\n)",
            rf"\1excerpt_image: {url_path}\n",
            text,
            count=1,
        )
    md.write_text(text_new, encoding="utf-8")


def main() -> None:
    COVERS.mkdir(parents=True, exist_ok=True)
    pools = build_pools()
    posts = sorted(POSTS.glob("*.md"))
    plan: list[tuple[Path, str, str]] = []
    used_titles: set[str] = set()
    for md in posts:
        title = read_title(md)
        pk = pool_key(title, md.stem)
        ft = pick_file(pools, used_titles, pk)
        if not ft:
            raise SystemExit(f"No commons file left for {md.name}")
        plan.append((md, pk, ft))

    all_titles = [t for _, _, t in plan]
    thumbs = imageinfo_thumb(all_titles)
    missing = [t for t in all_titles if t not in thumbs]
    if missing:
        raise SystemExit(f"imageinfo missing for: {missing[:5]} ... ({len(missing)} total)")

    for md, _pk, ftitle in plan:
        safe = re.sub(r"[^\w\-.]+", "_", md.stem)[:120]
        ext = ".jpg" if ".svg" not in ftitle.lower() else ".png"
        dest = COVERS / f"{safe}{ext}"
        rel = f"/images/covers/{dest.name}"
        text0 = md.read_text(encoding="utf-8")
        if dest.exists() and dest.stat().st_size > 400 and re.search(
            rf"(?m)^excerpt_image:\s*{re.escape(rel)}\s*$", text0
        ):
            print("skip", md.name, "->", dest.name)
            continue
        download(thumbs[ftitle], dest)
        set_excerpt_image(md, rel)
        print("OK", md.name, "->", dest.name)

    print("Done:", len(plan), "posts.")


if __name__ == "__main__":
    main()
