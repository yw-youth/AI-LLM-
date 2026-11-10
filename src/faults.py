"""故障注入器（chaos engineering）。

为什么要主动往好的网表里"搞破坏"：
1. mock 模型的输出永远是干净的，闭环永远走不到"修复"分支，等于没实现。
2. 这些破坏不是瞎编的——每一条都对应真实 LLM 犯过的错（见 docs/06-失败案例.md），
   注入它们等于把"模型会怎么错"变成可复现的测试用例。
3. 答辩演示：现场注入一个错 → 看着 Agent 自己发现、自己修 → 比讲十页 PPT 有说服力。
"""

from __future__ import annotations

import copy


def _find_net(netlist: dict, name: str) -> dict | None:
    for n in netlist["nets"]:
        if n["name"] == name:
            return n
    return None


def drop_decap_pin(netlist: dict) -> tuple[dict, str]:
    """去耦电容 C3 只留 GND 脚——真实案例：模型忘了把另一脚接电源。"""
    nl = copy.deepcopy(netlist)
    p5 = _find_net(nl, "+5V")
    p5["pins"] = [p for p in p5["pins"] if not (p["ref"] == "C3" and p["pin"] == "1")]
    return nl, "删除 C3 在 +5V 上的引脚（去耦电容单端悬空）"


def unknown_ref(netlist: dict) -> tuple[dict, str]:
    """引用了 BOM 里不存在的 U9——真实案例：模型幻觉出一个不存在的位号。"""
    nl = copy.deepcopy(netlist)
    gnd = _find_net(nl, "GND")
    gnd["pins"].append({"ref": "U9", "pin": "1"})
    return nl, "往 GND 塞一个不存在的器件 U9（幻觉位号）"


def pin_conflict(netlist: dict) -> tuple[dict, str]:
    """把 U1 的 4 脚再挂到 GND——一个引脚两个网络，电气上说不通。"""
    nl = copy.deepcopy(netlist)
    _find_net(nl, "GND")["pins"].append({"ref": "U1", "pin": "4"})
    return nl, "U1 的 4 脚同时挂在 +5V 和 GND（引脚冲突）"


def alias_name(netlist: dict) -> tuple[dict, str]:
    """+5V 改名 VCC——真实案例：同一个电源两个名字，KiCad 里会断成两个网络。"""
    nl = copy.deepcopy(netlist)
    for n in nl["nets"]:
        if n["name"] == "+5V":
            n["name"] = "VCC"
    return nl, "把 +5V 网络改名为 VCC（电源命名混用）"


def rename_gnd(netlist: dict) -> tuple[dict, str]:
    """GND 改名 GND_——地面没了，整板悬空。"""
    nl = copy.deepcopy(netlist)
    for n in nl["nets"]:
        if n["name"] == "GND":
            n["name"] = "GND_"
    return nl, "把 GND 改名为 GND_（缺少 GND 网络）"


# 名称 → (函数, 期望触发的错误码)。期望码用来断言"自检层真的抓到了这一类错"，
# 防止以后改检查逻辑时悄悄漏检。
SCENARIOS = {
    "去耦电容单端悬空": (drop_decap_pin, "net.open_pin"),
    "幻觉位号": (unknown_ref, "net.unknown_ref"),
    "引脚冲突": (pin_conflict, "net.pin_conflict"),
    "电源命名混用": (alias_name, "net.alias"),
    "缺少 GND": (rename_gnd, "net.no_gnd"),
}
