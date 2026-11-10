"""闭环演示：注入 5 种真实模型会犯的错 → 看闭环逐轮修复 → 写出 loop_report.md。

这份报告就是「进阶挑战 DRC 闭环」的过程证据：每个场景一轮一轮记录
检出什么、修了什么、还剩什么，供报告和答辩直接引用。

用法：
    python scripts/demo_loop.py            # 跑全部场景，写 out/loop_report.md
    python scripts/demo_loop.py --quiet    # 只写报告，不刷屏
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import design
import faults
import loop

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"


def _find_kicad_cli() -> str | None:
    import shutil

    found = shutil.which("kicad-cli")
    if found:
        return found
    for d in (r"D:\KiCad\bin\kicad-cli.exe", r"C:\Program Files\KiCad\8.0\bin\kicad-cli.exe"):
        if Path(d).exists():
            return d
    return None


def _erc_errors(kicad: str, sch: Path) -> int:
    """只数 ERROR 级；返回违规数。报告文件读完即删，避免污染 out/。"""
    import subprocess

    rpt = OUT / "healed.rpt"
    subprocess.run(
        [kicad, "sch", "erc", "--output", str(rpt), "--severity-error", str(sch)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    n = rpt.read_text(encoding="utf-8", errors="replace").count("[error]") if rpt.exists() else 1
    rpt.unlink(missing_ok=True)
    return n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true", help="只在终端打结果表，不逐轮刷屏")
    args = ap.parse_args()

    bom = design.mock_bom("帮我设计一块 Arduino 最小系统板")
    clean = design.mock_netlist(bom, "帮我设计一块 Arduino 最小系统板")

    report = [
        "# DRC 检查闭环 · 故障注入演示报告",
        "",
        f"- 基准网表：Arduino 最小系统板（mock）",
        f"- 方法：注入故障 → 自检 → 规则修复 → 复检，最多 {loop.MAX_ROUNDS} 轮",
        f"- 判定：ERROR 及阻塞级 WARN（open_pin / alias）清零为修复成功",
        "",
    ]

    ok_count = 0
    for name, (inject, expect_code) in faults.SCENARIOS.items():
        broken, desc = inject(clean)
        # 先断言自检层真的抓到了预期类别的错——注入器和检查器必须互相咬合。
        found_codes = {e["code"] for e in __import__("validate").check_netlist(broken, bom)}
        caught = expect_code in found_codes

        result = loop.self_heal(broken, bom)

        if not caught:
            report.append(f"## 场景：{name}\n\n❌ **自检层漏检**（期望 {expect_code}，实际 {sorted(found_codes)}）——注入器与检查器脱节，需要修！\n")
            print(f"✗ {name}: 漏检（期望 {expect_code}）")
            continue

        report.append(loop.render_report(result, name, desc))
        status = "✅ 修复" if result["healed"] else "❌ 未全修"
        ok_count += result["healed"]
        print(f"{status} {name}（{len(result['rounds'])} 轮）")
        if not args.quiet:
            for r in result["rounds"]:
                for f in r["found"]:
                    print(f"    检出 {f}")
                for a in r["applied"]:
                    print(f"    修复 {a}")
                for u in r["unfixable"]:
                    print(f"    未修 {u}")

    total = len(faults.SCENARIOS)
    report.insert(5, f"**结果**：{ok_count}/{total} 个场景闭环修复成功\n")
    print(f"\n汇总：{ok_count}/{total} 场景闭环修复成功")

    # 终验：修好的网表生成原理图，交给 KiCad ERC 亲自判。
    # 自检层说"修好了"不算数——出题人（KiCad）判 PASS 才算闭环真的闭合。
    kicad = _find_kicad_cli()
    if kicad:
        import kicad_sch

        report.append("---")
        report.append("## 终验：修复结果过 KiCad ERC")
        erc_pass = 0
        for name, (inject, _) in faults.SCENARIOS.items():
            broken, _ = inject(clean)
            r = loop.self_heal(broken, bom)
            p = kicad_sch.write_schematic(bom, r["netlist"], OUT / "healed.kicad_sch")
            n = _erc_errors(kicad, p)
            mark = "PASS" if n == 0 else f"{n} errors"
            erc_pass += n == 0
            report.append(f"- {name}: {mark}")
            print(f"  KiCad ERC [{name}]: {mark}")
        report.append("")
        report.append(f"**{erc_pass}/{total} 个修复后的原理图通过 KiCad ERC。**")
        report.append("")
        print(f"终验：{erc_pass}/{total} 通过 KiCad ERC")
    else:
        report.append("（本机未找到 kicad-cli，跳过 ERC 终验）")

    OUT.mkdir(exist_ok=True)
    (OUT / "loop_report.md").write_text("\n".join(report), encoding="utf-8", newline="\n")
    print(f"报告已写入 {OUT / 'loop_report.md'}")
    return 0 if ok_count == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
