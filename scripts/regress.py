#!/usr/bin/env python
"""回归集：10 条需求跑一遍，输出通过率表。

直接对应设计报告里"4.1 测试集 / 4.2 指标结果"那一节——
不要凭感觉写"准确率 90%"，跑出这张表再填。

每条用例都带**期望**，这是关键：
  pass   —— 应该生成成功
  refuse —— 应该被拒绝（能力边界 / 信息不足）
  na     —— mock 模型没有语义理解，判不了，需真实模型才有意义

用法：
    python scripts/regress.py            # mock 模式（秒出，用于日常回归）
    python scripts/regress.py --live     # 真实模型（要 API Key，会花钱）
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable

CASES = [
    # (用例名, 需求, 期望)
    ("Arduino 最小系统", "帮我设计一块 Arduino 最小系统板", "pass"),
    ("ESP32 采集板", "帮我设计一块 ESP32 温湿度采集板", "pass"),
    ("稳压电源板", "设计一个 5V 转 3.3V 稳压电源板", "pass"),
    ("口语化需求", "我想要个能读温度的小板子，插电脑上就能看", "pass"),
    ("带约束的需求", "做个最小系统板，但只能用 3.3V 供电，电容全用 0603", "pass"),
    ("错误前提", "用 3.3V 直接驱动 5V 继电器，不用三极管", "na"),
    ("超范围需求", "设计一块支持 PCIe 4.0 的 8 层高速板", "refuse"),
    ("缺信息需求", "帮我画个板子", "na"),
    ("多器件需求", "要能测温度、湿度、光照，还要有 OLED 显示", "pass"),
    ("中文型号混写", "主控用 atmega328p，晶振 16M，加个电源灯", "pass"),
]


def run_case(requirement: str, live: bool) -> tuple[int, str]:
    cmd = [PY, str(ROOT / "src" / "pipeline.py"), requirement, "--out", "out/regress"]
    if live:
        cmd.append("--live")
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (r.stdout or "") + (r.stderr or "")

    if r.returncode == 0:
        m = re.search(r"(\d+) 个网络 / (\d+) 个引脚连接", out)
        return 0, f"{m.group(1)} 网 / {m.group(2)} 脚" if m else "生成成功"
    if r.returncode == 3:
        return 3, "已拒绝（能力边界）"
    errs = [ln.strip() for ln in out.splitlines() if "[ERROR]" in ln]
    return r.returncode, (errs[0][:64] + "…") if errs else f"退出码 {r.returncode}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    args = ap.parse_args()

    print(f"回归集：{len(CASES)} 条  模式：{'真实模型' if args.live else 'mock 规则模型'}\n")
    print(f"{'#':>2}  {'用例':<14}{'期望':<8}{'实际':<8}说明")
    print("-" * 74)

    hit = total = 0
    skipped = 0
    for i, (name, req, expect) in enumerate(CASES, 1):
        code, detail = run_case(req, args.live)
        if expect == "pass":
            ok = code == 0
            total += 1
            hit += ok
            verdict = "PASS" if ok else "FAIL"
        elif expect == "refuse":
            ok = code == 3
            total += 1
            hit += ok
            verdict = "PASS" if ok else "FAIL"
        else:
            skipped += 1
            verdict = "N/A"
        label = {"pass": "应通过", "refuse": "应拒绝", "na": "需语义"}[expect]
        print(f"{i:>2}  {name:<14}{label:<8}{verdict:<8}{detail}")

    print("-" * 74)
    print(f"可判定 {total} 条：命中 {hit}/{total} = {hit / total:.0%}" if total else "无可判定用例")
    if skipped:
        print(f"另有 {skipped} 条标为「需语义」——mock 规则模型判不了，用 --live 才有意义。")
    print()
    print("写报告时这样用：")
    print("  「真实模型」的通过率 = --live 的结果；「本表可判定项」= mock 的回归基线。")
    print("  两类数字不要混着写，答辩会被问穿。")
    return 0 if hit == total else 1


if __name__ == "__main__":
    sys.exit(main())
