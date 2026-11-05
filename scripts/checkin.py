#!/usr/bin/env python
"""每周 check-in：一条命令完成"写周报 + 提交代码"。

为什么不手动 git commit：
过程分（10 分）的判据是"commit 时间线的形状"。手动提交一定会忘记，
忘记一次就少一次证据。把这件事收敛成一条命令，才可能坚持 8 周。

用法：
    python scripts/checkin.py --week 3 \
        --done "打通引脚级网表，3 种板子都过自检" \
        --blocker "LLM 偶尔漏去耦电容" \
        --next "接 KiCad 导出" --commit

    # 顺带推远程
    python scripts/checkin.py --week 3 --done "..." --commit --push

    # 只看会写什么，不落盘
    python scripts/checkin.py --week 3 --done "..." --dry-run
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROGRESS = ROOT / "PROGRESS.md"
MARKER = "<!-- checkin:end -->"

SECRET_PATTERNS = [
    (re.compile(r"sk-[A-Za-z0-9]{20,}"), "疑似 OpenAI 风格 API Key"),
    (re.compile(r"(?i)(api[_-]?key|token|secret)\s*[=:]\s*['\"]?[A-Za-z0-9_\-]{16,}"), "疑似密钥赋值"),
]


# ---------------------------------------------------------------- git


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=check)


def git_ready() -> tuple[bool, str]:
    r = git("rev-parse", "--is-inside-work-tree", check=False)
    if r.returncode != 0:
        return False, "当前目录不是 git 仓库。先在 pcb-agent/ 里执行 git init -b main"
    name = git("config", "user.name", check=False).stdout.strip()
    email = git("config", "user.email", check=False).stdout.strip()
    if not name or not email:
        return False, (
            "git 身份未配置。执行：\n"
            '  git config --global user.name "你的名字"\n'
            '  git config --global user.email "你的邮箱"'
        )
    return True, ""


def scan_secrets() -> list[str]:
    """提交前扫一遍暂存区，避免把 key 推上去。

    一旦推上去就删不掉了（历史里永远留着），只能作废密钥重发。
    所以这道检查放在 add 之后、commit 之前。
    """
    diff = git("diff", "--cached", "--unified=0", check=False).stdout
    hits = []
    for line in diff.splitlines():
        if not line.startswith("+") or line.startswith("+++"):
            continue
        for pattern, label in SECRET_PATTERNS:
            if pattern.search(line):
                hits.append(f"{label}: {line.strip()[:100]}")
    return hits


# ---------------------------------------------------------------- PROGRESS


def next_week() -> int:
    if not PROGRESS.exists():
        return 1
    weeks = [int(m) for m in re.findall(r"^\|\s*W(\d+)\s*\|", PROGRESS.read_text(encoding="utf-8"), re.M)]
    return (max(weeks) + 1) if weeks else 1


def render_row(week: int, done: str, blocker: str, nxt: str, errors: str) -> str:
    today = dt.date.today().isoformat()
    clean = lambda s: (s or "—").replace("|", "\\|").replace("\n", " ")  # noqa: E731
    return f"| W{week} | {today} | {clean(done)} | {clean(errors)} | {clean(blocker)} | {clean(nxt)} |"


def append_row(row: str) -> None:
    text = PROGRESS.read_text(encoding="utf-8") if PROGRESS.exists() else ""
    if MARKER in text:
        text = text.replace(MARKER, row + "\n" + MARKER)
    else:
        text = text.rstrip() + "\n" + row + "\n"
    text = re.sub(r"^\*最后更新：.*$", f"*最后更新：{dt.date.today().isoformat()}*", text, flags=re.M)
    PROGRESS.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------- 主流程


def main() -> int:
    ap = argparse.ArgumentParser(description="每周 check-in：写 PROGRESS.md 并提交")
    ap.add_argument("--week", type=int, help="第几周（省略则自动取最大值 +1）")
    ap.add_argument("--done", required=True, help="本周做完了什么")
    ap.add_argument("--blocker", default="无", help="卡在哪（没有就写'无'，但别空着）")
    ap.add_argument("--next", dest="nxt", default="见 8 周计划", help="下周计划")
    ap.add_argument("--errors", default="—", help="本周自检错误数 / 失败实验，可留空")
    ap.add_argument("--commit", action="store_true", help="顺便 git commit")
    ap.add_argument("--push", action="store_true", help="顺便 git push（隐含 --commit）")
    ap.add_argument("--dry-run", action="store_true", help="只打印，不落盘不提交")
    args = ap.parse_args()

    week = args.week or next_week()
    row = render_row(week, args.done, args.blocker, args.nxt, args.errors)

    print(f"将写入 PROGRESS.md：\n  {row}\n")
    if args.dry_run:
        print("--dry-run：未写入、未提交。")
        return 0

    append_row(row)
    print(f"✓ 已更新 {PROGRESS.name}")

    if not (args.commit or args.push):
        print("（未提交。加 --commit 一起提交，加 --push 顺便推远程）")
        return 0

    ok, hint = git_ready()
    if not ok:
        print(f"✗ {hint}")
        return 2

    git("add", "-A")

    hits = scan_secrets()
    if hits:
        print("✗ 暂存区里发现疑似密钥，已终止提交：")
        for h in hits:
            print(f"    {h}")
        print("  处理办法：把密钥移到 .env（已在 .gitignore 里），并把 config 里的值改成读环境变量。")
        return 3

    msg = f"chore(progress): W{week} check-in — {args.done}"
    r = git("commit", "-m", msg, check=False)
    if r.returncode != 0:
        out = (r.stdout + r.stderr).strip()
        if "nothing to commit" in out:
            print("没有文件变化，跳过 commit（PROGRESS.md 已更新但内容相同？）")
        else:
            print(f"✗ commit 失败：{out[:400]}")
            return 4
    else:
        print(f"✓ 已提交：{msg}")

    if args.push:
        r = git("push", check=False)
        if r.returncode != 0:
            print(f"✗ push 失败：{(r.stderr or r.stdout).strip()[:300]}")
            print("  常见原因：没配 remote / 需要代理 / 分支未设置上游。")
            print("  修法：git remote -v 检查；或 git push -u origin main")
            return 5
        print("✓ 已推送到远程")

    return 0


if __name__ == "__main__":
    sys.exit(main())
