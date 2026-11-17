"""DRC 检查闭环 —— 进阶挑战 20 分的主实现。

闭环结构（答辩时画在黑板上的那张图）：

    生成网表 → 自检层检查 → 有错？
                              ├─ 否 → 导出
                              └─ 是 → 错误文本（format_for_llm）回填给"修复者"
                                      → 修复 → 再自检（回到开头，最多 MAX_ROUNDS 轮）

关键点：
- 检查器永远不变，变的是输入。这样"修复者"没法糊弄——同一把尺子量到底。
- 每一轮的检出/修复/剩余都记录在案，最终写成 loop_report，作为过程证据。
- 规则修复器（mock）修不了的错如实标 unfixable；真实模式下这一步换成
  把 format_for_llm() 的文本塞回 Prompt 让模型重出——接口形状完全一致。
"""

from __future__ import annotations

import validate
import repair

MAX_ROUNDS = 4  # 防死循环：同一个错修了 4 轮还在，说明规则有 bug，停下来报告

# WARN 里必须闭环处理的子集：open_pin 是真实缺陷（悬空脚），
# alias 会让 KiCad 把一个电源断成两个网络。其余 WARN（如缺去耦）只提醒不拦截。
BLOCKING_WARNS = {"net.open_pin", "net.alias"}


def _blocking(errors: list[dict]) -> list[dict]:
    return [e for e in errors if e["level"] == "ERROR" or e["code"] in BLOCKING_WARNS]


def self_heal(netlist: dict, bom: dict) -> dict:
    """对一份（可能带错的）网表反复"检查 → 修复 → 复检"，直到干净或轮次用尽。

    返回报告 dict，字段见 _round()。
    """
    rounds: list[dict] = []
    current = netlist

    for i in range(1, MAX_ROUNDS + 1):
        errors = validate.check_netlist(current, bom)
        hard = _blocking(errors)
        if not hard and i == 1:
            # 第一轮就干净：闭环没有用武之地，如实记录而不是假装"修复成功"。
            rounds.append(_round(i, errors, [], []))
            break

        fixed, applied, unfixable = repair.fix(current, bom, errors)
        rounds.append(_round(i, errors, applied, unfixable))

        # 一轮下来一条都没修成 → 再循环也不会有进展，及时止损。
        if not applied:
            break
        current = fixed

        # 复检：阻塞项清零即成功（其余 WARN 留在报告里）。
        remain = _blocking(validate.check_netlist(current, bom))
        if not remain:
            rounds.append(_round(i + 1, validate.check_netlist(current, bom), [], []))
            break

    final_errors = validate.check_netlist(current, bom)
    return {
        "healed": not _blocking(final_errors),
        "rounds": rounds,
        "netlist": current,
        "final_errors": final_errors,
    }


def _round(n: int, errors: list[dict], applied: list[str], unfixable: list[str]) -> dict:
    return {
        "round": n,
        "found": [f"[{e['level']}][{e['code']}] {e['msg']}" for e in errors],
        "applied": applied,
        "unfixable": unfixable,
    }


def render_report(result: dict, scenario: str, fault_desc: str) -> str:
    """把一轮闭环渲染成 markdown——直接进 out/loop_report.md，作为 GitHub 过程证据。"""
    lines = [f"## 场景：{scenario}", "", f"> 注入故障：{fault_desc}", ""]
    for r in result["rounds"]:
        tag = f"第 {r['round']} 轮"
        if r["found"]:
            lines.append(f"**{tag} 检出**（{len(r['found'])} 条）")
            lines.extend(f"- {f}" for f in r["found"])
        else:
            lines.append(f"**{tag} 检出**：无错误 ✅")
        for a in r["applied"]:
            lines.append(f"- 🔧 修复：{a}")
        for u in r["unfixable"]:
            lines.append(f"- ⚠️ 未修：{u}")
        lines.append("")
    verdict = "✅ **闭环修复成功**，网表已通过自检" if result["healed"] else "❌ 未能完全修复（见上方未修项）"
    lines.append(f"**结论**：{verdict}")
    lines.append("")
    return "\n".join(lines)
