"""规则版「假模型」：没有 API Key 时也能跑通全链路。

存在的意义有三个：
1. 演示兜底——答辩现场断网也能跑完五步。
2. 对照基准——真实模型的输出要跟这里的"标准答案"比，才能算准准确率。
3. 回归测试——改导出代码时，输入输出不变，便于定位是谁坏了。

注意：引脚号按教学常用封装整理，工程上必须对着数据手册复核。
"""

from __future__ import annotations

import copy
import re

# ---------------------------------------------------------------- 封装库

F = {
    "R0603": "Resistor_SMD:R_0603_1608Metric",
    "C0603": "Capacitor_SMD:C_0603_1608Metric",
    "C0805": "Capacitor_SMD:C_0805_2012Metric",
    "LED0603": "LED_SMD:LED_0603_1608Metric",
    "TQFP32": "Package_QFP:TQFP-32_7x7mm_P0.8mm",
    "HC49": "Crystal:Crystal_HC49-U_Vertical",
    "SOT223": "Package_TO_SOT_SMD:SOT-223-3_TabPin2",
    "HDR2": "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
    "ESP32": "RF_Module:ESP32-WROOM-32",
    "DHT11": "Sensor:DHT11",
}


def _i(ref, value, footprint, desc):
    return {"ref": ref, "value": value, "footprint": footprint, "description": desc, "qty": 1}


def _p(ref, pin):
    return {"ref": ref, "pin": pin}


def _net(name, pins):
    return {"name": name, "pins": pins}


# ---------------------------------------------------------------- BOM

# 每个物理器件一个唯一位号。qty 恒为 1 —— 原理图里没有"数量"这个概念，
# 只有"多少个不同位号"。把 2 个 22pF 写成 qty=2 是新手最常犯的错。
_BOM_ARDUINO = {
    "board": {"type": "Arduino 最小系统板", "mcu": "ATmega328P-AU", "supply": "+5V"},
    "items": [
        _i("U1", "ATmega328P-AU", F["TQFP32"], "8 位 AVR 单片机"),
        _i("Y1", "16MHz", F["HC49"], "无源晶振"),
        _i("C1", "22pF", F["C0603"], "Y1 负载电容（XTAL1 侧）"),
        _i("C2", "22pF", F["C0603"], "Y1 负载电容（XTAL2 侧）"),
        _i("C3", "100nF", F["C0603"], "U1 VCC 去耦"),
        _i("C4", "100nF", F["C0603"], "U1 AVCC 去耦"),
        _i("C5", "10uF", F["C0805"], "电源入口滤波"),
        _i("R1", "10kΩ", F["R0603"], "RESET 上拉"),
        _i("R2", "1kΩ", F["R0603"], "LED 限流"),
        _i("D1", "LED-Green", F["LED0603"], "电源指示"),
        _i("J1", "Conn_01x02", F["HDR2"], "5V 电源输入"),
    ],
}

_BOM_ESP32 = {
    "board": {"type": "ESP32 温湿度采集板", "mcu": "ESP32-WROOM-32", "supply": "+3V3"},
    "items": [
        _i("U1", "ESP32-WROOM-32", F["ESP32"], "WiFi 主控模组（板载天线）"),
        _i("U2", "AMS1117-3.3", F["SOT223"], "5V 转 3.3V LDO"),
        _i("U3", "DHT11", F["DHT11"], "温湿度传感器"),
        _i("C1", "10uF", F["C0805"], "U2 输入滤波"),
        _i("C2", "100nF", F["C0603"], "U2 输出去耦"),
        _i("C3", "100nF", F["C0603"], "U1 3V3 就近去耦"),
        _i("C4", "10uF", F["C0805"], "U1 3V3 储能"),
        _i("R1", "10kΩ", F["R0603"], "U1 EN 上拉"),
        _i("R2", "10kΩ", F["R0603"], "U3 DATA 上拉"),
        _i("R3", "1kΩ", F["R0603"], "D1 限流"),
        _i("D1", "LED-Green", F["LED0603"], "电源指示"),
        _i("J1", "Conn_01x02", F["HDR2"], "5V 电源输入"),
    ],
}

_BOM_POWER = {
    "board": {"type": "5V 转 3.3V 稳压电源板", "mcu": "N/A（纯模拟）", "supply": "+5V"},
    "items": [
        _i("U1", "AMS1117-3.3", F["SOT223"], "3.3V LDO"),
        _i("C1", "10uF", F["C0805"], "输入滤波"),
        _i("C2", "100nF", F["C0603"], "输入高频去耦"),
        _i("C3", "22uF", F["C0805"], "输出储能"),
        _i("C4", "100nF", F["C0603"], "输出去耦"),
        _i("R1", "1kΩ", F["R0603"], "D1 限流"),
        _i("D1", "LED-Green", F["LED0603"], "电源指示"),
        _i("J1", "Conn_01x02", F["HDR2"], "5V 输入"),
        _i("J2", "Conn_01x02", F["HDR2"], "3.3V 输出"),
    ],
}


def mock_bom(requirement: str) -> dict:
    r = requirement.lower()
    if "esp32" in r or "温湿度" in requirement or "采集" in requirement:
        return copy.deepcopy(_BOM_ESP32)
    # 注意：不能用"电源"这种泛关键词——"加个电源灯"会被误判成电源板。
    # 这类误判是规则匹配的典型缺陷，正是报告"失败案例"的素材。
    if "稳压" in requirement or "ldo" in r or "电源板" in requirement or "转 3.3" in requirement:
        return copy.deepcopy(_BOM_POWER)
    return copy.deepcopy(_BOM_ARDUINO)


# ---------------------------------------------------------------- 能力边界

# 报告 1.3「功能边界」和答辩问题"换块复杂的板子还行吗"的答案，就落在这张表上。
# 一个会拒绝的 Agent，比一个什么都答应的 Agent 可信。
UNSUPPORTED = {
    "pcie": "PCIe 属于高速串行总线，需要阻抗控制与多层叠层，超出本 Agent 的建模能力",
    "ddr": "DDR 存储器接口涉及时序等长与阻抗匹配，本 Agent 只做基础连接",
    "hdmi": "HDMI 是高速差分信号，本 Agent 不处理差分对与长度匹配",
    "usb3": "USB 3.x 属超高速差分，超出能力范围",
    "射频": "射频电路依赖版图寄生参数，无法用网表级表示",
    "天线": "天线设计需要电磁仿真，不适用本流程",
    "多层板": "本 Agent 只输出原理图与网表，不做叠层设计",
    "阻抗": "阻抗控制属于 PCB 布局阶段，超出本 Agent 范围",
}


def out_of_scope(requirement: str) -> str | None:
    """返回拒绝理由；能处理则返回 None。

    注意：这是"能力边界"，不是"错误提示"。拒绝时要给出原因和替代方案，
    这才是工程交付该有的样子。
    """
    r = requirement.lower()
    for key, reason in UNSUPPORTED.items():
        if key in r:
            return reason
    if len(requirement.strip()) < 6:
        return "需求信息不足以确定板型与主控，至少说明用途或核心器件"
    return None


# ---------------------------------------------------------------- 网表

# ATmega328P-AU / TQFP-32：VCC=4,6  GND=3,5,21  AVCC=18  AREF=20
# RESET=29  XTAL1=7  XTAL2=8  PB5=17(Arduino D13)
_NET_ARDUINO = {
    "nets": [
        _net("+5V", [_p("J1", "1"), _p("U1", "4"), _p("U1", "6"), _p("R1", "1"), _p("C5", "1")]),
        _net("GND", [
            _p("J1", "2"), _p("U1", "3"), _p("U1", "5"), _p("U1", "21"),
            _p("C1", "2"), _p("C2", "2"), _p("C3", "2"), _p("C4", "2"),
            _p("C5", "2"), _p("D1", "2"),
        ]),
        _net("AVCC", [_p("U1", "18"), _p("C4", "1")]),
        _net("RESET", [_p("U1", "29"), _p("R1", "2")]),
        _net("XTAL1", [_p("U1", "7"), _p("Y1", "1"), _p("C1", "1")]),
        _net("XTAL2", [_p("U1", "8"), _p("Y1", "2"), _p("C2", "1")]),
        _net("LED_DRV", [_p("U1", "17"), _p("R2", "1")]),
        _net("LED_A", [_p("R2", "2"), _p("D1", "1")]),
    ]
}

# ESP32-WROOM-32：3V3=1  EN=2  GND=14,38  IO4=25
# DHT11：1=VDD 2=DATA 3=NC 4=GND
_NET_ESP32 = {
    "nets": [
        _net("+5V", [_p("J1", "1"), _p("U2", "3"), _p("C1", "1")]),
        _net("GND", [
            _p("J1", "2"), _p("U2", "1"), _p("U1", "14"), _p("U1", "38"),
            _p("U3", "4"), _p("C1", "2"), _p("C2", "2"), _p("C3", "2"),
            _p("C4", "2"), _p("D1", "2"),
        ]),
        _net("+3V3", [
            _p("U2", "2"), _p("U1", "1"), _p("C2", "1"), _p("C3", "1"),
            _p("C4", "1"), _p("R1", "1"), _p("R2", "1"), _p("R3", "1"),
        ]),
        _net("EN", [_p("U1", "2"), _p("R1", "2")]),
        _net("DHT_DATA", [_p("U3", "2"), _p("U1", "25"), _p("R2", "2")]),
        _net("LED_A", [_p("R3", "2"), _p("D1", "1")]),
    ]
}

# AMS1117-3.3 / SOT-223：1=GND 2=VOUT 3=VIN
_NET_POWER = {
    "nets": [
        _net("+5V", [_p("J1", "1"), _p("U1", "3"), _p("C1", "1"), _p("C2", "1")]),
        _net("GND", [
            _p("J1", "2"), _p("U1", "1"), _p("J2", "2"), _p("C1", "2"),
            _p("C2", "2"), _p("C3", "2"), _p("C4", "2"), _p("D1", "2"),
        ]),
        _net("+3V3", [_p("U1", "2"), _p("C3", "1"), _p("C4", "1"), _p("R1", "1"), _p("J2", "1")]),
        _net("LED_A", [_p("R1", "2"), _p("D1", "1")]),
    ]
}


def mock_netlist(bom: dict, requirement: str = "") -> dict:
    board = bom.get("board", {})
    tag = f"{board.get('type', '')} {board.get('mcu', '')}"
    if "ESP32" in tag:
        return copy.deepcopy(_NET_ESP32)
    if "稳压" in tag or "电源" in tag or "AMS1117" in tag:
        return copy.deepcopy(_NET_POWER)
    return copy.deepcopy(_NET_ARDUINO)


def mock_revise(bom: dict, instruction: str) -> dict:
    """增量修正：只改被点名的器件，其余原样返回。

    真实模型这里最容易"顺手改别的"，所以代码层面对 diff 也要做限制：
    返回后由 pipeline 比对，发现未授权改动就回退。
    """
    new = copy.deepcopy(bom)
    m = re.search(r"([RCYULDJQ]\d+)[^0-9]{0,6}(?:换成|改为|改成)\s*([0-9.]+\s*[a-zA-ZμΩ]+)", instruction)
    if not m:
        return new
    ref, value = m.group(1), m.group(2)
    for item in new["items"]:
        if item["ref"] == ref:
            item["value"] = value.replace("μ", "u").strip()
            item["description"] = f"{item['description']}（按用户要求调整）"
    return new
