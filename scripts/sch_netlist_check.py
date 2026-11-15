"""原理图网表等价性校验：把"图画对了吗"变成机器判据。

为什么 ERC 不够：
    ERC 查的是电气**规则**（悬空、驱动冲突、多标签……），它不知道我们**想连什么**。
    实测踩过：晶振 XTAL1/XTAL2 两个网络被一条竖干线并成了一个网，ERC 依然 0 违规
    —— 因为"两个被动脚连在一起"并不违反任何电气规则，它只是错的。
    真正的判据是：让 KiCad 从原理图里自己导出网表，再和设计网表逐网比对。

判定口径（按"分网"而不是"网络名"比较，因为 KiCad 会自己改名 Net-(U1-XTAL1)）：
    OK    图上该网引脚集合 == 设计该网引脚集合
    合并  图上某个网同时包含多个设计网络的引脚（短接，最危险）
    拆开  设计的一个网在图上是多个网（漏连）
    缺脚  设计里的引脚没出现在图上任何网络里

用法：
    python scripts/sch_netlist_check.py                       # out/board.kicad_sch + out/netlist.json
    python scripts/sch_netlist_check.py a.kicad_sch b.json
返回码 0 = 全部一致；1 = 有差异；2 = 环境问题（找不到 kicad-cli / 文件不存在）。
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CANDIDATES = [
    "kicad-cli",
    "kicad-cli.exe",
    r"D:\KiCad\bin\kicad-cli.exe",
    r"D:\Kicad\bin\kicad-cli.exe",
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


def sch_nets(cli: str, sch: Path) -> list[set[tuple[str, str]]]:
    """让 KiCad 从原理图导出网表，返回按网络分组的 (位号, 引脚号) 集合。"""
    xml = Path(tempfile.gettempdir()) / f"{sch.stem}_check.xml"
    r = subprocess.run(
        [cli, "sch", "export", "netlist", "--format", "kicadxml", "-o", str(xml), str(sch)],
        capture_output=True, text=True,
    )
    if r.returncode != 0 or not xml.exists():
        raise RuntimeError(r.stdout + r.stderr)
    root = ET.parse(xml).getroot()
    nets = []
    for net in root.findall(".//nets/net"):
        pins = {(nd.get("ref"), nd.get("pin")) for nd in net.findall("node")}
        if pins:
            nets.append(pins)
    return nets


def design_nets(path: Path) -> dict[str, set[tuple[str, str]]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {n["name"]: {(p["ref"], p["pin"]) for p in n["pins"]} for n in data["nets"]}


def main(argv: list[str]) -> int:
    sch = Path(argv[1]) if len(argv) > 1 else ROOT / "out" / "board.kicad_sch"
    nlf = Path(argv[2]) if len(argv) > 2 else ROOT / "out" / "netlist.json"
    for p in (sch, nlf):
        if not p.exists():
            print(f"找不到 {p}\n先跑：python src/pipeline.py \"帮我设计一块 Arduino 最小系统板\"")
            return 2
    cli = find_cli()
    if not cli:
        print("找不到 kicad-cli，无法从原理图导出网表。")
        return 2

    got = sch_nets(cli, sch)
    want = design_nets(nlf)

    # 引脚 → 设计网络名，用来判断图上某个网"混了哪几个设计网"
    pin2want: dict[tuple[str, str], str] = {}
    for name, pins in want.items():
        for p in pins:
            pin2want[p] = name

    print(f"原理图：{sch.name}   图上 {len(got)} 个网络 / 设计 {len(want)} 个网络\n")
    problems: list[str] = []

    # 1) 合并检测：一个图上网络里出现了多个设计网络
    merged_of: dict[str, list[set[tuple[str, str]]]] = {}
    for pins in got:
        names = {pin2want[p] for p in pins if p in pin2want}
        if len(names) > 1:
            merged_of.setdefault("+".join(sorted(names)), []).append(pins)

    # 2) 逐设计网络核对
    for name, pins in want.items():
        hit = [g for g in got if g & pins]
        if not hit:
            print(f"  {name:<10} 缺脚   图上找不到该网络的任何引脚")
            problems.append(f"{name} 缺脚")
            continue
        cover = set().union(*hit)
        extra = cover - pins
        missing = pins - cover
        if extra or missing:
            tag = "合并" if extra else "拆开"
            detail = []
            if extra:
                others = sorted({pin2want[p] for p in extra if p in pin2want})
                detail.append("被并入的其它网络：" + "、".join(others) if others else "")
            if missing:
                detail.append("漏掉引脚：" + " ".join(f"{a}.{b}" for a, b in sorted(missing)))
            print(f"  {name:<10} {tag}   " + "；".join(d for d in detail if d))
            problems.append(f"{name} {tag}")
        else:
            print(f"  {name:<10} OK      {len(pins)} 脚")

    print()
    if not problems:
        print("汇总：设计网表与原理图网表完全一致（分网等价）")
        return 0
    print(f"汇总：{len(problems)} 处不一致 —— 这张图电气上是错的，ERC 通过也没用")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
