"""稳定性测试台架：三板型 × N 次，记录通过率与耗时，写 out/stability_report.md。

为什么需要它：老师评分表里「实验结果」要的是**有数据**，而单次跑通只能证明
"能跑"，不能证明"稳定"。这份台架把重复实验自动化，拿到 API Key 后加 --live
就能直接产出报告 4.2 节的数字——不用到时再手搓。

mock 基线现在就能跑：它给出的是"流水线本身的确定性下限"，将来 --live 的
结果要跟这条基线对照，掉到基线以下的差距就是模型不稳定的部分。
"""

from __future__ import annotations

import argparse
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"
PY = sys.executable

# 三种代表板型：最小系统（MCU+晶振）、采集（模块+传感）、电源（纯模拟）。
REQS = [
    "帮我设计一块 Arduino 最小系统板",
    "帮我设计一块 ESP32 温湿度采集板",
    "设计一个 5V 转 3.3V 稳压电源板",
]


def run_once(req: str, live: bool) -> tuple[bool, float]:
    """跑一次完整流水线，返回 (是否成功, 耗时秒)。每次用独立输出目录，避免互相覆盖。"""
    t0 = time.time()
    cmd = [PY, str(ROOT / "src" / "pipeline.py"), req]
    if live:
        cmd.append("--live")
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode == 0, time.time() - t0


def pct(times: list[float], p: float) -> float:
    s = sorted(times)
    return s[min(len(s) - 1, int(len(s) * p))] if s else 0.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="调用真实模型（需 OPENAI_API_KEY）")
    ap.add_argument("-n", "--runs", type=int, default=5, help="每种板型跑几次（默认 5）")
    args = ap.parse_args()

    mode = "真实模型（--live）" if args.live else "mock 规则模型（确定性基线）"
    rows: list[tuple[str, int, int, list[float]]] = []

    for req in REQS:
        results = [run_once(req, args.live) for _ in range(args.runs)]
        ok = sum(1 for passed, _ in results if passed)
        times = [t for _, t in results]
        rows.append((req, ok, len(results), times))
        print(f"{req}: {ok}/{len(results)} 通过  中位 {statistics.median(times):.2f}s")

    lines = [
        "# 稳定性测试报告",
        "",
        f"- 模式：{mode}",
        f"- 方法：三种代表板型 × {args.runs} 次，完整五步流水线 + 自检，退出码 0 判通过",
        "",
        "| 板型 | 通过 | 耗时中位 | P95 |",
        "|---|---|---|---|",
    ]
    total_ok = 0
    total_n = 0
    for req, ok, n, times in rows:
        total_ok += ok
        total_n += n
        lines.append(f"| {req} | {ok}/{n} | {statistics.median(times):.2f}s | {pct(times, 0.95):.2f}s |")
    lines.append("")
    lines.append(f"**总通过率 {total_ok}/{total_n}。**")

    if not args.live:
        lines += [
            "",
            "> 本表为 mock 基线：mock 是确定性规则，理论上应 100% 通过；",
            "> 任何一条失败都说明流水线本身有 bug，而不是模型不稳定。",
            "> 接入真实模型后用 `python scripts/stability.py --live` 重跑，",
            "> 与本基线的差值即为模型不稳定性——这正是自检闭环要治理的对象。",
        ]
    (OUT / "stability_report.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"\n报告已写入 {OUT / 'stability_report.md'}")
    return 0 if total_ok == total_n else 1


if __name__ == "__main__":
    raise SystemExit(main())
