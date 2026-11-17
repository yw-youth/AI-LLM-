"""BOM + 网表 → KiCad 8 可打开的原理图（.kicad_sch）。

为什么手写 s-expression 而不是用 kiutils 之类的库：
    课程要求"clone 下来不装依赖就能跑"，而 kiutils 需要 pip install。手写的好处是
    完全可控；代价是必须严格对齐文件格式版本——所以这里只输出 KiCad 8
    (version 20231120) 认识的字段，不用 v9/v10 新增的 (hide yes)、(show_name) 等，
    否则助教用 KiCad 8 打开会报"文件版本过新"。

连接怎么表达：
    不画 wire，而是在每个引脚端点放一个同名网络标签（label）。KiCad 里同名 label
    即同一个网络，ERC 认可，且避免了自动布线——这是"原理图正确性"与"画图工作量"
    之间的取舍，报告里要写清楚。
"""

from __future__ import annotations

import json
import re
import uuid as _uuid
from pathlib import Path

# 所有 uuid 都由内容派生：同一份输入每次生成同样的文件，便于 git diff 复核
_NS = _uuid.UUID("6f1b8f3e-0d1a-4f2b-9d2e-7c5a1b3e9f00")


def _uid(*parts: object) -> str:
    return str(_uuid.uuid5(_NS, "|".join(str(p) for p in parts)))


def _n(v: float) -> str:
    """KiCad 习惯：最多 4 位小数，去掉多余的 0。"""
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return s if s not in ("", "-0") else "0"


# ---------------------------------------------------------------- 符号定义

def _sym_resistor(name: str) -> str:
    """电阻：竖放两脚，1 脚在上。

    注意：KiCad 要求子符号名必须是「父符号名_0_1」这种形式（父名去掉库前缀），
    写成 "R_0_1" 会导致整张图"加载失败"，且报错信息完全不提这一句。
    """
    base = name.split(":")[-1]
    return f"""    (symbol "{name}"
      (pin_numbers hide)
      (pin_names (offset 0) hide)
      (exclude_from_sim no)
      (in_bom yes)
      (on_board yes)
      (property "Reference" "R" (at 2.54 0 0) (effects (font (size 1.27 1.27))))
      (property "Value" "R" (at 2.54 -2.54 0) (effects (font (size 1.27 1.27))))
      (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (property "Datasheet" "~" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (symbol "{base}_0_1"
        (rectangle (start -1.016 2.54) (end 1.016 -2.54)
          (stroke (width 0.254) (type default)) (fill (type none)))
      )
      (symbol "{base}_1_1"
        (pin passive line (at 0 3.81 270) (length 1.27)
          (name "~" (effects (font (size 1.27 1.27))))
          (number "1" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 0 -3.81 90) (length 1.27)
          (name "~" (effects (font (size 1.27 1.27))))
          (number "2" (effects (font (size 1.27 1.27)))))
      )
    )"""


def _sym_capacitor(name: str) -> str:
    """电容：竖放两脚，用两条极板横线表示（比画方块更像真符号）。"""
    base = name.split(":")[-1]
    return f"""    (symbol "{name}"
      (pin_numbers hide)
      (pin_names (offset 0) hide)
      (exclude_from_sim no)
      (in_bom yes)
      (on_board yes)
      (property "Reference" "C" (at 2.54 0 0) (effects (font (size 1.27 1.27))))
      (property "Value" "C" (at 2.54 -2.54 0) (effects (font (size 1.27 1.27))))
      (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (property "Datasheet" "~" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (symbol "{base}_0_1"
        (polyline (pts (xy -2.032 0.762) (xy 2.032 0.762))
          (stroke (width 0.508) (type default)) (fill (type none)))
        (polyline (pts (xy -2.032 -0.762) (xy 2.032 -0.762))
          (stroke (width 0.508) (type default)) (fill (type none)))
      )
      (symbol "{base}_1_1"
        (pin passive line (at 0 3.81 270) (length 3.048)
          (name "~" (effects (font (size 1.27 1.27))))
          (number "1" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 0 -3.81 90) (length 3.048)
          (name "~" (effects (font (size 1.27 1.27))))
          (number "2" (effects (font (size 1.27 1.27)))))
      )
    )"""


def _sym_crystal(name: str) -> str:
    """晶振：竖放两脚。"""
    base = name.split(":")[-1]
    return f"""    (symbol "{name}"
      (pin_numbers hide)
      (pin_names (offset 0) hide)
      (exclude_from_sim no)
      (in_bom yes)
      (on_board yes)
      (property "Reference" "Y" (at 2.54 0 0) (effects (font (size 1.27 1.27))))
      (property "Value" "Y" (at 2.54 -2.54 0) (effects (font (size 1.27 1.27))))
      (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (property "Datasheet" "~" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (symbol "{base}_0_1"
        (rectangle (start -1.27 1.778) (end 1.27 -1.778)
          (stroke (width 0.254) (type default)) (fill (type none)))
        (polyline (pts (xy -2.54 1.778) (xy -2.54 -1.778))
          (stroke (width 0.508) (type default)) (fill (type none)))
        (polyline (pts (xy 2.54 1.778) (xy 2.54 -1.778))
          (stroke (width 0.508) (type default)) (fill (type none)))
      )
      (symbol "{base}_1_1"
        (pin passive line (at 0 3.81 270) (length 2.032)
          (name "~" (effects (font (size 1.27 1.27))))
          (number "1" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 0 -3.81 90) (length 2.032)
          (name "~" (effects (font (size 1.27 1.27))))
          (number "2" (effects (font (size 1.27 1.27)))))
      )
    )"""


def _sym_box(name: str, numbers: list[str]) -> str:
    """通用矩形符号：IC / 连接器 / MCU 都用它，引脚数由网表实际用到的引脚号决定。

    为什么不做每种芯片的"像真"符号：真实符号库有几千个器件，靠生成器拼不现实；
    先用"引脚号 + 网络标签"保证连接语义正确，符号外观属于后期打磨项。
    """
    base = name.split(":")[-1]
    left = numbers[: (len(numbers) + 1) // 2]
    right = numbers[(len(numbers) + 1) // 2 :]
    rows = max(len(left), len(right), 1)

    half_w = 7.62
    half_h = (rows - 1) * 2.54 / 2 + 2.54
    pin_len = 3.81
    top = (rows - 1) * 2.54 / 2

    pins = []
    for i, num in enumerate(left):
        y = top - i * 2.54
        pins.append(
            f"""        (pin passive line (at {_n(-half_w - pin_len)} {_n(y)} 0) (length {_n(pin_len)})
          (name "~" (effects (font (size 1.016 1.016))))
          (number "{num}" (effects (font (size 1.016 1.016)))))"""
        )
    for i, num in enumerate(right):
        y = top - i * 2.54
        pins.append(
            f"""        (pin passive line (at {_n(half_w + pin_len)} {_n(y)} 180) (length {_n(pin_len)})
          (name "~" (effects (font (size 1.016 1.016))))
          (number "{num}" (effects (font (size 1.016 1.016)))))"""
        )

    pin_text = "\n".join(pins)
    return f"""    (symbol "{name}"
      (pin_names (offset 0.254) hide)
      (exclude_from_sim no)
      (in_bom yes)
      (on_board yes)
      (property "Reference" "U" (at {_n(-half_w)} {_n(half_h + 1.27)} 0)
        (effects (font (size 1.27 1.27)) (justify left)))
      (property "Value" "U" (at {_n(-half_w)} {_n(-half_h - 1.27)} 0)
        (effects (font (size 1.27 1.27)) (justify left)))
      (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (property "Datasheet" "~" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (symbol "{base}_0_1"
        (rectangle (start {_n(-half_w)} {_n(half_h)}) (end {_n(half_w)} {_n(-half_h)})
          (stroke (width 0.254) (type default)) (fill (type background)))
      )
      (symbol "{base}_1_1"
{pin_text}
      )
    )"""


# 被动器件按值/位号前缀选符号；其余一律矩形
def _pick_symbol_kind(ref: str, value: str) -> str:
    prefix = "".join(ch for ch in ref if ch.isalpha()).upper()
    if prefix == "R":
        return "RES"
    if prefix == "C":
        return "CAP"
    if prefix in ("Y", "X"):
        return "XTAL"
    return "BOX"


# ---------------------------------------------------------------- 坐标计算

def _pin_offsets(kind: str, numbers: list[str]) -> dict[str, tuple[float, float, int]]:
    """返回 {引脚号: (局部 x, 局部 y, 朝外角度)}。局部坐标 +Y 朝上。"""
    if kind in ("RES", "CAP", "XTAL"):
        return {numbers[0]: (0.0, 3.81, 90), numbers[1]: (0.0, -3.81, 270)}

    left = numbers[: (len(numbers) + 1) // 2]
    right = numbers[(len(numbers) + 1) // 2 :]
    rows = max(len(left), len(right), 1)
    half_w = 7.62
    pin_len = 3.81
    top = (rows - 1) * 2.54 / 2

    out: dict[str, tuple[float, float, int]] = {}
    for i, num in enumerate(left):
        out[num] = (-half_w - pin_len, top - i * 2.54, 180)
    for i, num in enumerate(right):
        out[num] = (half_w + pin_len, top - i * 2.54, 0)
    return out


def _label_angle(pin_angle: int) -> int:
    """标签文字方向：让文字永远从引脚向外延伸，不压到符号上。"""
    return 0 if pin_angle == 0 else 180


# ---------------------------------------------------------------- 主流程

def build(bom: dict, netlist: dict) -> str:
    board = bom.get("board", {})
    board_name = board.get("type") or board.get("name") or "board"
    sch_uuid = _uid("root", board_name)
    project = "pcb-agent"

    # (ref, pin) -> net（网表里每个网络下挂 pins: [{ref, pin}]）
    net_of_pin: dict[tuple[str, str], str] = {}
    for net in netlist.get("nets", []):
        for node in net.get("pins", []):
            net_of_pin[(node["ref"], str(node["pin"]))] = net["name"]

    comps = bom.get("items", [])

    # 每个器件用到了哪些引脚（按网表里出现的引脚号，数值序）
    pins_of_ref: dict[str, list[str]] = {}
    for (ref, pin), _net in net_of_pin.items():
        pins_of_ref.setdefault(ref, []).append(pin)
    for ref in pins_of_ref:
        pins_of_ref[ref].sort(key=lambda p: (int(p) if p.isdigit() else 999, p))

    # 布局：一行 4 个，间距按符号宽度放大，避免标签互相压
    cols = 4
    col_gap, row_gap = 63.5, 76.2
    origin_x, origin_y = 50.8, 63.5

    lib_defs: list[str] = []
    lib_cache: dict[str, str] = {}

    def lib_name_for(kind: str, numbers: list[str]) -> str:
        if kind in ("RES", "CAP", "XTAL"):
            name = kind
            if name not in lib_cache:
                factory = {
                    "RES": _sym_resistor,
                    "CAP": _sym_capacitor,
                    "XTAL": _sym_crystal,
                }[kind]
                lib_defs.append(factory(f"pcbagent:{name}"))
                lib_cache[name] = f"pcbagent:{name}"
            return lib_cache[name]
        # 矩形符号按"引脚号集合"去重，同规格器件共用一个定义
        name = f"BOX_{'_'.join(numbers)}"
        if name not in lib_cache:
            lib_defs.append(_sym_box(f"pcbagent:{name}", numbers))
            lib_cache[name] = f"pcbagent:{name}"
        return lib_cache[name]

    body: list[str] = []

    for idx, item in enumerate(comps):
        ref = item["ref"]
        numbers = pins_of_ref.get(ref, [])
        if not numbers:
            continue  # 网表里没连接的器件不画（例如仅上料的测试点）

        kind = _pick_symbol_kind(ref, item.get("value", ""))
        # 只连了一个脚的被动器件（数据有误时）退回矩形符号，宁可画得难看也不要崩
        if kind in ("RES", "CAP", "XTAL") and len(numbers) < 2:
            kind = "BOX"
        lib_id = lib_name_for(kind, numbers)

        cx = origin_x + (idx % cols) * col_gap
        cy = origin_y + (idx // cols) * row_gap

        prop_off = 6.35 if kind == "BOX" else 3.81
        body.append(
            f"""  (symbol (lib_id "{lib_id}") (at {_n(cx)} {_n(cy)} 0) (unit 1)
    (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)
    (uuid "{_uid('sym', ref)}")
    (property "Reference" "{ref}" (at {_n(cx)} {_n(cy - prop_off - 2.54)} 0)
      (effects (font (size 1.27 1.27))))
    (property "Value" "{item.get('value', '')}" (at {_n(cx)} {_n(cy - prop_off)} 0)
      (effects (font (size 1.27 1.27))))
    (property "Footprint" "{item.get('footprint', '')}" (at {_n(cx)} {_n(cy)} 0)
      (effects (font (size 1.27 1.27)) hide))
    (property "Datasheet" "~" (at {_n(cx)} {_n(cy)} 0)
      (effects (font (size 1.27 1.27)) hide))
{chr(10).join(f'    (pin "{num}" (uuid "{_uid("pin", ref, num)}"))' for num in numbers)}
    (instances
      (project "{project}"
        (path "/{sch_uuid}" (reference "{ref}") (unit 1))))
  )"""
        )

        # 网络标签：贴在每个引脚端点上。注意 KiCad 图纸 Y 轴向下，符号 +Y 向上，故取负
        offsets = _pin_offsets(kind, numbers)
        for num in numbers:
            ox, oy, pin_angle = offsets[num]
            gx, gy = cx + ox, cy - oy
            net = net_of_pin.get((ref, num))
            if not net:
                continue
            ang = _label_angle(pin_angle)
            justify = "right" if ang == 180 else "left"
            body.append(
                f"""  (label "{net}" (at {_n(gx)} {_n(gy)} {ang})
    (effects (font (size 1.143 1.143)) (justify {justify} bottom))
    (uuid "{_uid('label', ref, num, net)}")
  )"""
            )

    lib_symbols = "\n".join(lib_defs)
    body_text = "\n".join(body)
    title = board_name

    return f"""(kicad_sch
  (version 20231120)
  (generator "eeschema")
  (generator_version "8.0")
  (uuid "{sch_uuid}")
  (paper "A4")
  (title_block
    (title "{title}")
    (rev "1")
    (comment 1 "Generated by PCB-Agent — 引脚级连接以网络标签表达")
  )
  (lib_symbols
{lib_symbols}
  )
{body_text}
  (sheet_instances
    (path "/" (page "1"))
  )
)
"""


def write_schematic(bom: dict, netlist: dict, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    # KiCad 对 UTF-8 无 BOM 最友好；换行统一 LF，避免 Windows 上 diff 噪音
    path.write_text(build(bom, netlist), encoding="utf-8", newline="\n")
    return path


# ---------------------------------------------------------------- 完整工程

def write_project(bom: dict, netlist: dict, out_dir: Path, stem: str = "board") -> list[Path]:
    """写出一个 KiCad 能直接打开的"工程包"：原理图 + 符号库 + 库表 + 项目文件。

    为什么一个 .kicad_sch 不够：
        符号虽已内嵌在原理图里，KiCad 也能画出来，但 ERC 会对每个器件报
        "当前配置不包含符号库 'pcbagent'"。补上 .kicad_sym + sym-lib-table +
        .kicad_pro 之后 ERC 才真正 0 违规——这是"能打开"与"能验收"的差别。
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    text = build(bom, netlist)

    sch_path = out_dir / f"{stem}.kicad_sch"
    sch_path.write_text(text, encoding="utf-8", newline="\n")
    files = [sch_path]

    m = re.search(r"\(lib_symbols\n(.*?)\n  \)\n", text, re.S)
    if m:
        # .kicad_sym 里符号名不带库前缀（库名由 sym-lib-table 提供）
        lib_body = m.group(1).replace('(symbol "pcbagent:', '(symbol "')
        sym_path = out_dir / "pcbagent.kicad_sym"
        sym_path.write_text(
            "(kicad_symbol_lib\n"
            "  (version 20231120)\n"
            '  (generator "kicad_symbol_editor")\n'
            '  (generator_version "8.0")\n'
            f"{lib_body}\n"
            ")\n",
            encoding="utf-8",
            newline="\n",
        )
        files.append(sym_path)

        table = out_dir / "sym-lib-table"
        table.write_text(
            "(sym_lib_table\n"
            "  (version 7)\n"
            '  (lib (name "pcbagent")(type "KiCad")(uri "${KIPRJMOD}/pcbagent.kicad_sym")'
            '(options "")(descr "PCB-Agent 自动生成符号"))\n'
            ")\n",
            encoding="utf-8",
            newline="\n",
        )
        files.append(table)

        pro = out_dir / f"{stem}.kicad_pro"
        pro.write_text(
            json.dumps(
                {
                    "meta": {"filename": f"{stem}.kicad_pro", "version": 1},
                    "schematic": {"legacy_lib_dir": "", "legacy_lib_list": []},
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        files.append(pro)

    return files
