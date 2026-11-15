"""引脚号 → 引脚名 映射表。

为什么需要这张表：
    网表里只有 (位号, 引脚号)，没有引脚名。原理图如果没有引脚名，读图人看到
    "U1 的 3 号脚接 GND" 得去翻 datasheet 才知道那是地——这不叫原理图。
    真符号库里当然有名字，但我们不引入 KiCad 库依赖（clone 即跑），
    所以把课程用到的几款器件的引脚名写死在这张表里，覆盖不到就退回引脚号。

维护规则：
    新器件只加一行；键用 BOM 里的 value（与 design.py 的型号字符串一致）。
    引脚号用字符串，兼容 TQFP/SOT 这类数字引脚。
"""

from __future__ import annotations

# 引脚名分类用的词表，kicad_sch 排版时据此决定引脚放在符号哪一侧
POWER_PIN_NAMES = {"VCC", "VDD", "VIN", "AVCC", "VOUT", "3V3", "+5V", "+3V3", "VBUS", "5V"}
GROUND_PIN_NAMES = {"GND", "VSS", "AGND", "DGND"}

ATmega328P_AU = {
    "1": "PD3", "2": "PD4", "3": "GND", "4": "VCC",
    "5": "GND", "6": "VCC", "7": "XTAL1", "8": "XTAL2",
    "9": "PD5", "10": "PD6", "11": "PD7", "12": "PB0",
    "13": "PB1", "14": "PB2", "15": "PB3", "16": "PB4",
    "17": "PB5", "18": "AVCC", "19": "ADC6", "20": "AREF",
    "21": "GND", "22": "ADC7", "23": "PC0", "24": "PC1",
    "25": "PC2", "26": "PC3", "27": "PC4", "28": "PC5",
    "29": "RESET", "30": "PD0", "31": "PD1", "32": "PD2",
}

ESP32_WROOM_32 = {
    "1": "3V3", "2": "EN", "3": "SENSOR_VP", "4": "SENSOR_VN",
    "5": "IO34", "6": "IO35", "7": "IO32", "8": "IO33",
    "9": "IO25", "10": "IO26", "11": "IO27", "12": "IO14",
    "13": "IO12", "14": "GND", "15": "IO13", "16": "SD2",
    "17": "SD3", "18": "CMD", "19": "CLK", "20": "SD0",
    "21": "SD1", "22": "IO15", "23": "IO2", "24": "IO0",
    "25": "IO4", "26": "IO16", "27": "IO17", "28": "IO5",
    "29": "IO18", "30": "IO19", "31": "NC", "32": "IO21",
    "33": "RXD0", "34": "TXD0", "35": "IO22", "36": "IO23",
    "37": "NC", "38": "GND", "39": "GND",
}

AMS1117_33 = {"1": "GND", "2": "VOUT", "3": "VIN"}

DHT11 = {"1": "VDD", "2": "DATA", "3": "NC", "4": "GND"}

_KNOWN: dict[str, dict[str, str]] = {
    "ATmega328P-AU": ATmega328P_AU,
    "ATMEGA328P-AU": ATmega328P_AU,
    "ESP32-WROOM-32": ESP32_WROOM_32,
    "AMS1117-3.3": AMS1117_33,
    "AMS1117": AMS1117_33,
    "DHT11": DHT11,
}


def pin_names(value: str, numbers: list[str]) -> dict[str, str]:
    """返回 {引脚号: 引脚名}；表里没有的引脚退回 "~"（KiCad 里表示不显示名字）。"""
    table = _KNOWN.get((value or "").strip().upper(), {})
    out: dict[str, str] = {}
    for num in numbers:
        out[num] = table.get(num, "~")
    return out


def has_names(names: dict[str, str]) -> bool:
    return any(v not in ("", "~") for v in names.values())
