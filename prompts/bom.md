# bom.md — 需求 → BOM

## 流程位置
第 2 步。输入：用户的一句自然语言需求。输出：`bom.json`（符合 `schemas/bom.schema.json`）。

---

## Prompt 正文

```
把下面这段需求转成元器件清单（BOM）。

用户需求：
"""
{requirement}
"""

要求：
1. 先在心里确定三件事：板子类型、主控型号、供电方式。不要输出这段推理。
2. 位号规则：电阻 R1..Rn、电容 C1..Cn、晶振 Y1..、连接器 J1..、IC U1..、二极管 D1..、电感 L1..
3. 每个器件必须包含：ref / value / footprint / description / qty。
4. footprint 用 KiCad 8 标准库命名，例如 `Resistor_SMD:R_0603_1608Metric`、
   `Capacitor_SMD:C_0603_1608Metric`、`Package_QFP:TQFP-32_7x7mm_P0.8mm`。
5. 必须遵守 system 里的"设计常识"：每个 IC 电源引脚配 100nF、RESET 上拉、LED 串限流电阻、电源入口滤波。
6. 全部器件合并同类项用 qty 表示数量，但**去耦电容要按位置分开列**（C1 给 U1 的 VCC，C2 给 AVCC）。

输出格式（严格遵守，不要多字段）：
{
  "board": {"type": "...", "mcu": "...", "supply": "..."},
  "items": [
    {"ref": "U1", "value": "ATmega328P-AU", "footprint": "...", "description": "...", "qty": 1}
  ]
}
```

## Few-shot 示例（放进 user 消息之前，能显著降低失败率）

输入：`帮我设计一块 Arduino 最小系统板`

输出：
```json
{
  "board": {"type": "Arduino 最小系统板", "mcu": "ATmega328P-AU", "supply": "+5V"},
  "items": [
    {"ref": "U1", "value": "ATmega328P-AU", "footprint": "Package_QFP:TQFP-32_7x7mm_P0.8mm", "description": "8位AVR单片机", "qty": 1},
    {"ref": "Y1", "value": "16MHz", "footprint": "Crystal:Crystal_HC49-U_Vertical", "description": "无源晶振", "qty": 1},
    {"ref": "C1", "value": "22pF", "footprint": "Capacitor_SMD:C_0603_1608Metric", "description": "Y1负载电容", "qty": 2},
    {"ref": "C2", "value": "100nF", "footprint": "Capacitor_SMD:C_0603_1608Metric", "description": "U1 VCC去耦", "qty": 1},
    {"ref": "C3", "value": "100nF", "footprint": "Capacitor_SMD:C_0603_1608Metric", "description": "U1 AVCC去耦", "qty": 1},
    {"ref": "C4", "value": "10uF", "footprint": "Capacitor_SMD:C_0805_2012Metric", "description": "电源入口滤波", "qty": 1},
    {"ref": "R1", "value": "10kΩ", "footprint": "Resistor_SMD:R_0603_1608Metric", "description": "RESET上拉", "qty": 1},
    {"ref": "R2", "value": "1kΩ", "footprint": "Resistor_SMD:R_0603_1608Metric", "description": "LED限流", "qty": 1},
    {"ref": "D1", "value": "LED-Green", "footprint": "LED_SMD:LED_0603_1608Metric", "description": "电源指示", "qty": 1},
    {"ref": "J1", "value": "Conn_01x02", "footprint": "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical", "description": "5V电源输入", "qty": 1}
  ]
}
```

## 调优记录（自己填，写进报告）

| 版本 | 改动 | 失败率 |
|---|---|---|
| v1 | 自然语言描述 | ~60% |
| v2 | 强制纯 JSON | ~20% |
| v3 | 加 few-shot + Schema 校验重试 | |
