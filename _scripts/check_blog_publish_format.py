#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发布前格式与静态检查（Jekyll blog 子模块）。

退出码：
  0  — 无错误、无警告（或可忽略的提示）
  1  — 存在错误：不应发布，需先修复
  2  — 仅有警告：须由用户在对话中确认后再执行 git push

用法（在 blog/ 仓库根目录）：
  python3 _scripts/check_blog_publish_format.py --staged
  python3 _scripts/check_blog_publish_format.py _posts/2025-11-23-CPU.md
  python3 _scripts/check_blog_publish_format.py              # 全量检查 _posts（不含站内 .md 链警告）
  python3 _scripts/check_blog_publish_format.py --strict-links  # 全量且报告 .md 站内链警告
  python3 _scripts/check_blog_publish_format.py --staged --with-jekyll  # 暂存文件 + 尝试 jekyll build
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None  # type: ignore[misc, assignment]


ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "_posts"


class Issue:
    def __init__(self, path: Path, msg: str, *, warn: bool = False) -> None:
        self.path = path
        self.msg = msg
        self.warn = warn


def split_front_matter(path: Path, text: str) -> tuple[str, str] | None:
    if not text.startswith("---"):
        return None
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", text, flags=re.DOTALL)
    if not m:
        return None
    fm = m.group(1).strip("\n")
    body = text[m.end() :]
    return fm, body


def _post_date_from_filename(path: Path) -> bool:
    """Jekyll 允许日期仅出现在文件名 YYYY-MM-DD- 前缀中。"""
    return bool(re.match(r"^\d{4}-\d{1,2}-\d{1,2}-", path.stem))


# _posts 文章要求：东八区完整时间，避免仅写日期导致排序/Feed 与预期不一致，且与 Liquid/Jekyll 习惯对齐。
_POST_DATE_FULL_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \+0800$")


def shanghai_now_example() -> str:
    """供错误提示：当前 Asia/Shanghai 时刻，格式与 front matter 推荐写法一致。"""
    if ZoneInfo is not None:
        return datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S +0800")
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S +0800")


def check_post_date_format(path: Path, fm: str) -> str | None:
    """
    校验 `date:` 为 `YYYY-MM-DD HH:MM:SS +0800`（可带 YAML 引号）。
    返回 None 表示通过；否则返回错误说明字符串。
    """
    m = re.search(r"^date\s*:\s*(.+)$", fm, re.MULTILINE)
    if not m:
        return None
    raw = m.group(1).strip()
    if (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
        raw = raw[1:-1].strip()
    if _POST_DATE_FULL_RE.match(raw):
        return None
    ex = shanghai_now_example()
    return (
        f"`date:` 须为东八区完整时间，格式 `YYYY-MM-DD HH:MM:SS +0800`；"
        f"当前时刻示例：`date: {ex}`；实际 front matter 解析值为 `{raw!r}`"
    )


def check_file(path: Path, *, strict_links: bool) -> list[Issue]:
    issues: list[Issue] = []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        return [Issue(path, f"非 UTF-8 或解码失败: {e}")]

    if path.suffix.lower() not in {".md", ".markdown"}:
        return issues

    parts = split_front_matter(path, text)
    if parts is None:
        issues.append(Issue(path, "缺少合法 YAML front matter（应以 --- 开头并以单独一行的 --- 结束）"))
        return issues

    fm, body = parts
    if path.parent.resolve() == POSTS.resolve():
        if not re.search(r"^title\s*:", fm, re.MULTILINE):
            issues.append(Issue(path, "_posts 文章 front matter 缺少 `title:`"))
        if not re.search(r"^date\s*:", fm, re.MULTILINE) and not _post_date_from_filename(path):
            issues.append(Issue(path, "_posts 文章 front matter 缺少 `date:`，且文件名亦非 YYYY-MM-DD- 前缀"))
        elif re.search(r"^date\s*:", fm, re.MULTILINE):
            msg = check_post_date_format(path, fm)
            if msg:
                issues.append(Issue(path, msg))

        if "argv[argv]" in body:
            issues.append(Issue(path, "正文中出现 `argv[argv]`，疑似应为 `argv[1]`"))

    if strict_links:
        for m in re.finditer(r"\]\(([^)]+)\)", body):
            url = m.group(1).strip()
            if url.endswith(".md") and "://" not in url and not url.startswith("{%"):
                issues.append(
                    Issue(
                        path,
                        f"疑似站内 Markdown 文件链（线上常 404）: ({url}) — 建议用 `/路径/` 或 `{{% post_url ... %}}`",
                        warn=True,
                    )
                )

    fence = body.count("```")
    if fence % 2 != 0:
        issues.append(Issue(path, "代码块 ``` 数量为奇数，可能存在未闭合 fence"))

    return issues


def git_staged_post_paths() -> list[Path]:
    r = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        return []
    out: list[Path] = []
    for line in r.stdout.splitlines():
        line = line.strip()
        if not line.startswith("_posts/") or not line.endswith(".md"):
            continue
        p = ROOT / line
        if p.is_file():
            out.append(p)
    return out


def resolve_targets(
    paths: list[str],
    *,
    staged: bool,
) -> list[Path]:
    if staged:
        return git_staged_post_paths()
    if paths:
        targets: list[Path] = []
        for a in paths:
            p = (ROOT / a).resolve() if not Path(a).is_absolute() else Path(a).resolve()
            if p.is_dir():
                targets.extend(sorted(p.glob("*.md")))
            elif p.is_file():
                targets.append(p)
        return targets
    return sorted(POSTS.glob("*.md"))


def run_jekyll_build() -> list[Issue]:
    issues: list[Issue] = []
    bundle = ROOT / "Gemfile"
    if not bundle.is_file():
        print("[信息] 无 Gemfile，跳过 jekyll build", file=sys.stderr)
        return issues
    if not shutil.which("bundle"):
        print("[信息] 未在 PATH 中找到 bundle，跳过 jekyll build", file=sys.stderr)
        return issues
    try:
        r = subprocess.run(
            ["bundle", "exec", "jekyll", "build", "--strict_front_matter"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
    except FileNotFoundError:
        print("[信息] bundle 执行失败，跳过 jekyll build", file=sys.stderr)
        return issues
    except subprocess.TimeoutExpired:
        issues.append(Issue(ROOT, "jekyll build 超时"))
        return issues

    if r.returncode != 0:
        tail = (r.stderr or "") + "\n" + (r.stdout or "")
        tail = tail.strip()[-4000:] or "(无输出)"
        soft = any(
            s in tail
            for s in (
                "GemNotFoundException",
                "Could not find 'bundler'",
                "Could not find gem",
                "command not found: jekyll",
            )
        )
        if soft:
            print(
                "[信息] 本机 Ruby/Bundler 与仓库不一致或缺少 jekyll，跳过 jekyll 作为阻塞项（可依赖 GitHub Actions 构建）",
                file=sys.stderr,
            )
            return issues
        issues.append(Issue(ROOT, f"`bundle exec jekyll build` 失败 (exit {r.returncode}):\n{tail}"))
    return issues


def main() -> int:
    raw = sys.argv[1:]
    staged = "--staged" in raw
    with_jekyll = "--with-jekyll" in raw
    strict_links = "--strict-links" in raw
    paths = [a for a in raw if not a.startswith("--")]

    targets = resolve_targets(paths, staged=staged)
    if staged and not targets:
        print("[错误] --staged：暂存区中没有 _posts/*.md，请先 git add 要发布的文章", file=sys.stderr)
        return 1

    # 全量扫描默认不扫站内 .md 链（历史文章多）；显式路径 / --staged / --strict-links 则检查
    link_check = strict_links or bool(paths) or staged

    all_issues: list[Issue] = []
    for p in targets:
        all_issues.extend(check_file(p, strict_links=link_check))

    if with_jekyll:
        all_issues.extend(run_jekyll_build())

    errors = [i for i in all_issues if not i.warn]
    warns = [i for i in all_issues if i.warn]

    for i in errors:
        print(f"[错误] {i.path.relative_to(ROOT)}: {i.msg}", file=sys.stderr)
    for i in warns:
        print(f"[警告] {i.path.relative_to(ROOT)}: {i.msg}", file=sys.stderr)

    if errors:
        print("\n存在错误：请先修复后再发布。", file=sys.stderr)
        return 1
    if warns:
        print(f"\n共 {len(warns)} 条警告：请向用户展示后，**待用户明确确认**再执行 git push。", file=sys.stderr)
        return 2
    print("check_blog_publish_format: OK", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
