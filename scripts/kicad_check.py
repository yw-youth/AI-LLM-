"""用 KiCad 自己的 ERC 检查生成的原理图 —— 让"能不能打开"变成机器判据。

为什么需要它：
    "我这里能打开"没有任何说服力；ERC 是 KiCad 内置的电气规则检查，它跑通
    0 违规，才是可以写进报告、录进视频的证据。进阶挑战「DRC 检查闭环」也是
    在这个脚本的基础上，把 ERC 报告回填给模型重生成。

用法：
    python scripts/kicad_check.py                 # 检查 out/board.kicad_sch
    python scripts/kicad_check.py path/to/x.kicad_sch

找不到 kicad-cli 时返回码 2（说明环境没配好，而不是检查失败）。
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 常见安装位置：PATH 优先，其次 Windows 默认路径与 D 盘自定义路径
CANDIDATES = [
    "kicad-cli",
    "kicad-cli.exe",
    r"D:\KiCad\bin\kicad-cli.exe",
    r"C:\Program Files\KiCad\8.0\bin\kicad-cli.exe",
    r"C:\Program Files\KiCad\9.0\bin\kicad-cli.exe",
    r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe",
]


def find_cli() -> str | None:
    for c in CANDIDATES:
        p = shutil.which(c)
        if p:
            return p
        if Path(c).exists():
            return c
    return None


def main(argv: list[str]) -> int:
    sch = Path(argv[1]) if len(argv) > 1 else ROOT / "out" / "board.kicad_sch"
    if not sch.exists():
        print(f"找不到原理图：{sch}\n先跑：python src/pipeline.py \"帮我设计一块 Arduino 最小系统板\"")
        return 2

    cli = find_cli()
    if not cli:
        print("找不到 kicad-cli。请安装 KiCad 8 或把 <KiCad>/bin 加入 PATH。")
        return 2

    ver = subprocess.run([cli, "version"], capture_output=True, text=True).stdout.strip()
    rpt = sch.with_suffix(".erc.rpt")
    r = subprocess.run(
        [cli, "sch", "erc", "--output", str(rpt), "--severity-all", str(sch)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    out = (r.stdout + r.stderr).strip()
    print(f"kicad-cli {ver}")
    print(out)

    if "失败" in out or not rpt.exists():
        return 1

    text = rpt.read_text(encoding="utf-8", errors="replace")
    # 从 "** ERC messages: N  Errors E  Warnings W" 里取数
    m = re.search(r"ERC messages:\s*(\d+)\s+Errors\s+(\d+)\s+Warnings\s+(\d+)", text)
    if not m:
        return 0
    total, errs, warns = (int(x) for x in m.groups())
    print(f"\n汇总：{errs} 错误 / {warns} 警告（报告：{rpt.name}）")

    # 版本提醒：课程要求 KiCad 8，用更高版本验证只能证明"新版本能开"
    if not ver.startswith("8."):
        print(f"注意：当前用 KiCad {ver} 验证。助教用 KiCad 8 批改，")
        print("      建议 W12 前并装 8.0 再跑一次本脚本，结果才算数。")

    return 0 if errs == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
