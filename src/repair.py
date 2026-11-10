"""规则修复器：mock 模式下闭环的"修复"环节。

设计立场（答辩会被问，先写清楚）：
- 真实模式里，"修复"由模型完成——validate.format_for_llm() 的错误文本回填进 Prompt。
- mock 模式里没有模型，这里用规则代替。但规则只修**能从错误信息本身安全推断**的错：
  改名类、删幻觉类、补去耦类。凡是要"设计知识"才能修的（比如单端网络该接到哪），
  一律不动、如实上报 unfixable——宁可承认修不了，也不瞎修一个看似合法实则错误的网表。
  这个边界感本身就是答辩卖点："代码做语法落地，语义决策留给模型"。
"""

from __future__ import annotations

import copy

# 可修复的错误码 → 修复函数。新增检查项时同步在这里登记，
# 没登记的错误码会被 loop 归入 unfixable，而不是静默忽略。
_FIXABLE = {"net.alias", "net.unknown_ref", "net.pin_conflict", "net.open_pin", "net.no_gnd"}


def _find_net(netlist: dict, name: str) -> dict | None:
    for n in netlist["nets"]:
        if n["name"] == name:
            return n
    return None


def _supply_name(bom: dict) -> str:
    """板子的主电源网络名，如 +5V。"""
    return "+" + str((bom.get("board") or {}).get("supply", "+5V")).lstrip("+")


def fix(netlist: dict, bom: dict, errors: list[dict]) -> tuple[dict, list[str], list[str]]:
    """按错误码逐条修复。返回 (新网表, 修了什么, 修不了什么)。"""
    nl = copy.deepcopy(netlist)
    applied: list[str] = []
    unfixable: list[str] = []

    for e in errors:
        code = e["code"]
        if code not in _FIXABLE:
            unfixable.append(f"{e['msg']}（需要设计知识，规则不动）")
            continue

        if code == "net.alias":
            # 把非标准电源名改回标准名。标准名取自 board.supply。
            target = _supply_name(bom)
            for n in nl["nets"]:
                if n["name"].upper() in ("VCC", "VDD", "PWR"):
                    applied.append(f"网络 {n['name']} 改名为 {target}")
                    n["name"] = target

        elif code == "net.unknown_ref":
            # 删掉幻觉位号的引脚。位号从错误信息里解析（格式固定，见 validate.py）。
            import re

            m = re.search(r"不存在的器件 (\w+)$", e["msg"])
            if m:
                bad = m.group(1)
                for n in nl["nets"]:
                    before = len(n["pins"])
                    n["pins"] = [p for p in n["pins"] if p["ref"] != bad]
                    if len(n["pins"]) < before:
                        applied.append(f"从网络 {n['name']} 移除不存在的器件 {bad}")

        elif code == "net.pin_conflict":
            # 引脚冲突：保留先出现的网络，从后到的网络里删掉该引脚。
            import re

            m = re.search(r"(\w+) 的引脚 (\w+) 同时出现在 (\S+?) 和 (\S+?)（", e["msg"])
            if m:
                ref, pin, first, second = m.group(1), m.group(2), m.group(3), m.group(4)
                net2 = _find_net(nl, second)
                if net2:
                    net2["pins"] = [p for p in net2["pins"] if not (p["ref"] == ref and p["pin"] == pin)]
                    applied.append(f"{ref}.{pin} 保留在 {first}，从 {second} 移除")

        elif code == "net.open_pin":
            # 两脚器件单端悬空。注意报错文案里的引脚号是"已连接"的那只脚，
            # 要补的是另一只（两脚器件无非 1/2）。补接到哪：已接脚在 GND 就补
            # 主电源（去耦电容的标准接法），否则补 GND。
            import re

            m = re.search(r"(\w+) 只有引脚 (\w+) 进了网络", e["msg"])
            if m:
                ref, connected = m.group(1), m.group(2)
                dangling = "1" if connected == "2" else "2"
                where = next((n["name"] for n in nl["nets"] if any(p["ref"] == ref for p in n["pins"])), None)
                if where == "GND":
                    sup = _find_net(nl, _supply_name(bom))
                    if sup is not None:
                        sup["pins"].append({"ref": ref, "pin": dangling})
                        applied.append(f"{ref} 的悬空脚 {dangling} 补接到 {_supply_name(bom)}")
                else:
                    gnd = _find_net(nl, "GND")
                    if gnd is not None:
                        gnd["pins"].append({"ref": ref, "pin": dangling})
                        applied.append(f"{ref} 的悬空脚 {dangling} 补接到 GND")

        elif code == "net.no_gnd":
            # GND 被改了名：找出疑似地（名字以 GND 开头），改回 GND。
            for n in nl["nets"]:
                if n["name"].upper().startswith("GND") and n["name"] != "GND":
                    applied.append(f"网络 {n['name']} 改回 GND")
                    n["name"] = "GND"

    return nl, applied, unfixable
