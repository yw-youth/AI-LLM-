"""自检层（类 DRC）。

这是整条流水线里最值钱的一段：它把"模型的一次性输出"变成"可被机器反驳的假设"。
进阶挑战「DRC 检查闭环」就是把这里的返回值回填给 Prompt，重生成，再检查。

错误分两级：
  ERROR —— 电气上说不通，必须重来（悬空网络、引脚互斥、位号不存在）
  WARN  —— 工程上不推荐，但不至于不能用（缺去耦、网络名混用）

返回结构统一为 list[dict]，方便直接序列化成 JSON 喂回给模型。
"""

from __future__ import annotations

import re

REF_PATTERN = re.compile(r"^(R|C|L|Y|U|D|J|Q|SW|F)\d+$")
NET_PATTERN = re.compile(r"^(\+[0-9.]+V[0-9]?|GND|[A-Z][A-Z0-9_]{1,23})$")
FOOTPRINT_PATTERN = re.compile(r"^[A-Za-z0-9_.\-]+:[A-Za-z0-9_.\-]+$")

POWER_ALIASES = {"VCC", "VDD", "5V", "3V3", "3.3V", "PWR"}


def _err(code, msg, **extra):
    return {"level": "ERROR", "code": code, "msg": msg, **extra}


def _warn(code, msg, **extra):
    return {"level": "WARN", "code": code, "msg": msg, **extra}


# ---------------------------------------------------------------- BOM


def check_bom(bom: dict) -> list[dict]:
    out: list[dict] = []

    board = bom.get("board") or {}
    for k in ("type", "mcu", "supply"):
        if not str(board.get(k, "")).strip():
            out.append(_err("bom.board_missing", f"board.{k} 为空"))

    items = bom.get("items")
    if not isinstance(items, list) or not items:
        out.append(_err("bom.items_empty", "items 为空或不是数组"))
        return out

    seen: dict[str, int] = {}
    for n, item in enumerate(items):
        ref = str(item.get("ref", ""))
        if not REF_PATTERN.match(ref):
            out.append(_err("bom.bad_ref", f"第 {n + 1} 项位号非法: {ref!r}"))
            continue
        if ref in seen:
            out.append(_err("bom.dup_ref", f"位号重复: {ref}（第 {seen[ref]} 项与第 {n + 1} 项）"))
        seen[ref] = n + 1

        if not str(item.get("value", "")).strip():
            out.append(_err("bom.no_value", f"{ref} 没有 value"))
        if not FOOTPRINT_PATTERN.match(str(item.get("footprint", ""))):
            out.append(_err("bom.bad_footprint", f"{ref} 封装格式应为 '库:封装'，实得 {item.get('footprint')!r}"))
        qty = item.get("qty", 1)
        if not isinstance(qty, int) or qty < 1:
            out.append(_err("bom.bad_qty", f"{ref} 的 qty 必须是正整数"))

    # 工程惯例：至少要有电源输入连接器 + 主控
    refs = {i.get("ref") for i in items if isinstance(i, dict)}
    if not any(str(r).startswith("J") for r in refs):
        out.append(_warn("bom.no_connector", "没有任何连接器（J*），电源无处接入"))
    if board.get("mcu") not in (None, "", "N/A（纯模拟）") and not any(str(r).startswith("U") for r in refs):
        out.append(_err("bom.no_ic", "声明了 mcu 但 BOM 里没有 U*（IC）"))

    return out


# ---------------------------------------------------------------- 网表


def check_netlist(netlist: dict, bom: dict | None = None) -> list[dict]:
    out: list[dict] = []

    nets = netlist.get("nets")
    if not isinstance(nets, list) or not nets:
        out.append(_err("net.empty", "nets 为空或不是数组"))
        return out

    bom_refs = {i["ref"] for i in (bom or {}).get("items", []) if "ref" in i}

    names: dict[str, int] = {}
    pin_owner: dict[tuple[str, str], str] = {}
    used_refs: set[str] = set()

    for net in nets:
        name = str(net.get("name", ""))
        pins = net.get("pins") or []

        if not NET_PATTERN.match(name):
            out.append(_err("net.bad_name", f"网络名非法: {name!r}（应为 +5V / GND / 大写信号名）"))
        if name in names:
            out.append(_err("net.dup_name", f"网络名重复: {name}"))
        names[name] = 1

        if len(pins) < 2:
            out.append(_err("net.single_ended", f"网络 {name} 只连了 {len(pins)} 个引脚（至少 2 个）"))

        for pin in pins:
            ref, num = str(pin.get("ref", "")), str(pin.get("pin", ""))
            if not REF_PATTERN.match(ref):
                out.append(_err("net.bad_ref", f"网络 {name} 里位号非法: {ref!r}"))
                continue
            if not num:
                out.append(_err("net.no_pin", f"网络 {name} 里 {ref} 没有引脚号"))
                continue
            if bom_refs and ref not in bom_refs:
                out.append(_err("net.unknown_ref", f"网络 {name} 引用了 BOM 里不存在的器件 {ref}"))
            used_refs.add(ref)

            key = (ref, num)
            if key in pin_owner and pin_owner[key] != name:
                out.append(_err(
                    "net.pin_conflict",
                    f"{ref} 的引脚 {num} 同时出现在 {pin_owner[key]} 和 {name}（一个引脚只能属于一个网络）",
                ))
            pin_owner[key] = name

    # GND 必须存在
    if "GND" not in names:
        out.append(_err("net.no_gnd", "缺少 GND 网络"))

    # 电源网络命名混用检测
    for name in names:
        if name.upper() in POWER_ALIASES:
            out.append(_warn("net.alias", f"网络名 {name} 与标准写法（+5V / +3V3 / GND）不一致，易导致多驱动"))

    # 器件连接性
    if bom_refs:
        dangling = sorted(bom_refs - used_refs)
        if dangling:
            out.append(_warn("net.dangling_parts", "BOM 里这些器件未出现在任何网络: " + ", ".join(dangling)))

    # 去耦电容：每个 U* 有电源引脚，就应至少有一个 C* 落在同一电源网络
    for net in nets:
        name = str(net.get("name", ""))
        if name == "GND" or not name.startswith("+"):
            continue
        pins = net.get("pins") or []
        has_ic = any(str(p.get("ref", "")).startswith("U") for p in pins)
        has_cap = any(str(p.get("ref", "")).startswith("C") for p in pins)
        if has_ic and not has_cap:
            out.append(_warn("net.no_decoupling", f"电源网络 {name} 上有 IC 但没有去耦电容"))

    return out


# ---------------------------------------------------------------- 汇总


def summarize(errors: list[dict]) -> str:
    e = sum(1 for x in errors if x["level"] == "ERROR")
    w = sum(1 for x in errors if x["level"] == "WARN")
    if not errors:
        return "无悬空网络、无重复引脚、无未定义器件"
    return f"{e} 个错误 / {w} 个警告"


def has_errors(errors: list[dict]) -> bool:
    return any(x["level"] == "ERROR" for x in errors)


def format_for_llm(errors: list[dict]) -> str:
    """把错误列表转成给模型看的文本——这就是反馈闭环的"弹药"。"""
    if not errors:
        return "上一次输出通过了全部检查。"
    lines = ["上一次输出有以下问题，请修正后重新输出完整 JSON："]
    for x in errors:
        lines.append(f"- [{x['level']}][{x['code']}] {x['msg']}")
    return "\n".join(lines)
