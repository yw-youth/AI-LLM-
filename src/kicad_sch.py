"""BOM + 网表 → KiCad 8 可打开的原理图（.kicad_sch）。

为什么手写 s-expression 而不是用 kiutils 之类的库：
    课程要求"clone 下来不装依赖就能跑"，而 kiutils 需要 pip install。手写的好处是
    完全可控；代价是必须严格对齐文件格式版本——所以这里只输出 KiCad 8
    (version 20231120) 认识的字段，不用 v9/v10 新增的 (hide yes)、(show_name) 等，
    否则助教用 KiCad 8 打开会报"文件版本过新"。

连接怎么表达（这一版改过）：
    上一版只在引脚端点放网络标签、不画导线。电气上是对的（KiCad 里同名 label 即同一
    网络，ERC 也认可），但视觉上像一堆互不相干的器件——读图人第一眼看不出"这是一张电路"。
    这一版改成三层表达，和真人画图的习惯一致：
      1. 本地小网络（2–3 个引脚）画真正的正交导线，拐点自动避让器件包围盒；
      2. 引脚放在符号的哪一侧由引脚名决定（电源在上、地在下方、XTAL 在左），
         这样导线自然走短，不会横穿芯片；
      3. 走不通的网络退回网络标签，保证任何输入都能出图，不因排版失败而崩。

    画导线之后暴露出一个更严重的问题：**ERC 全绿不等于图画对了**。两个网络各画各的，
    谁也不知道别人占了哪条走廊，两条干线重合就把两个网并成了一个——而 ERC 查不出来
    （两个被动脚短接不违反任何电气规则）。所以布线时必须把"别人的线段、别人的引脚端点
    及其逃逸段"都当成禁区，另外用 scripts/sch_netlist_check.py 做网表等价校验兜底。
"""

from __future__ import annotations

import json
import re
import uuid as _uuid
from pathlib import Path

import pinmap

# 所有 uuid 都由内容派生：同一份输入每次生成同样的文件，便于 git diff 复核
_NS = _uuid.UUID("6f1b8f3e-0d1a-4f2b-9d2e-7c5a1b3e9f00")


def _uid(*parts: object) -> str:
    return str(_uuid.uuid5(_NS, "|".join(str(p) for p in parts)))


def _n(v: float) -> str:
    """KiCad 习惯：最多 4 位小数，去掉多余的 0。"""
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return s if s not in ("", "-0") else "0"


GRID = 1.27
PIN_LEN = 3.81


def _snap(v: float, grid: float = GRID) -> float:
    return round(v / grid) * grid


# ---------------------------------------------------------------- 被动器件符号

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
    """晶振：竖放两脚，中间画晶体块、两侧画电极板。"""
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


def _sym_led(name: str) -> str:
    """LED：横放两脚，1 脚阳极在左。三角形 + 竖杠 + 两个出光箭头。

    为什么单独建符号而不复用矩形：指示灯是读图时最先被找的元件之一，
    画成方框会让人以为是个 IC。
    """
    base = name.split(":")[-1]
    return f"""    (symbol "{name}"
      (pin_numbers hide)
      (pin_names (offset 0) hide)
      (exclude_from_sim no)
      (in_bom yes)
      (on_board yes)
      (property "Reference" "D" (at 0 2.54 0) (effects (font (size 1.27 1.27))))
      (property "Value" "LED" (at 0 -3.81 0) (effects (font (size 1.27 1.27))))
      (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (property "Datasheet" "~" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (symbol "{base}_0_1"
        (polyline (pts (xy -1.27 1.27) (xy -1.27 -1.27) (xy 1.27 0) (xy -1.27 1.27))
          (stroke (width 0.254) (type default)) (fill (type none)))
        (polyline (pts (xy 1.27 1.27) (xy 1.27 -1.27))
          (stroke (width 0.254) (type default)) (fill (type none)))
        (polyline (pts (xy 1.27 1.27) (xy 2.54 2.54))
          (stroke (width 0.2) (type default)) (fill (type none)))
        (polyline (pts (xy 2.032 0.762) (xy 3.302 2.032))
          (stroke (width 0.2) (type default)) (fill (type none)))
      )
      (symbol "{base}_1_1"
        (pin passive line (at -3.81 0 0) (length 2.54)
          (name "A" (effects (font (size 1.016 1.016))))
          (number "1" (effects (font (size 1.016 1.016)))))
        (pin passive line (at 3.81 0 180) (length 2.54)
          (name "K" (effects (font (size 1.016 1.016))))
          (number "2" (effects (font (size 1.016 1.016)))))
      )
    )"""


def _sym_conn(name: str, count: int) -> str:
    """排针 / 连接器：竖排 count 个脚，引脚朝右，脚号写在框外。

    引脚朝右是因为连接器通常画在图的最左侧，线从右边出去进入电路。
    """
    base = name.split(":")[-1]
    half_h = max((count - 1) * 2.54 / 2 + 2.54, 3.81)
    half_h = _snap(half_h)
    pins = []
    for i in range(count):
        y = ((count - 1) / 2 - i) * 2.54
        pins.append(
            f"""        (pin passive line (at {_n(2.54 + PIN_LEN)} {_n(y)} 180) (length {_n(PIN_LEN)})
          (name "Pin_{i + 1}" (effects (font (size 1.016 1.016))))
          (number "{i + 1}" (effects (font (size 1.016 1.016)))))"""
        )
    return f"""    (symbol "{name}"
      (pin_names (offset 1.016) hide)
      (exclude_from_sim no)
      (in_bom yes)
      (on_board yes)
      (property "Reference" "J" (at 0 {_n(half_h + 6.35)} 0) (effects (font (size 1.27 1.27))))
      (property "Value" "Conn" (at 0 {_n(-half_h - 6.35)} 0) (effects (font (size 1.27 1.27))))
      (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (property "Datasheet" "~" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (symbol "{base}_0_1"
        (rectangle (start -2.54 {_n(half_h)}) (end 2.54 {_n(-half_h)})
          (stroke (width 0.254) (type default)) (fill (type background)))
      )
      (symbol "{base}_1_1"
{chr(10).join(pins)}
      )
    )"""


# ---------------------------------------------------------------- 有名字的 IC 符号

def _side_of(name: str) -> str:
    """引脚放哪一侧：电源在上、地在下方、晶振在左、其余在右。

    这样做的原因是导线长度：电源脚朝上就能直接连去耦电容，地脚朝下就朝下走线，
    不用横穿芯片本体。人画图也是这么排的。
    """
    u = (name or "~").upper()
    if u in pinmap.POWER_PIN_NAMES:
        return "top"
    if u in pinmap.GROUND_PIN_NAMES:
        return "bottom"
    if u.startswith("XTAL"):
        return "left"
    return "right"


def _ic_geometry(numbers: list[str], names: dict[str, str]) -> tuple[float, float, dict[str, tuple[float, float, int]]]:
    """返回 (半宽, 半高, {引脚号: (局部 x, 局部 y, 朝向角度)})。局部 +Y 向上。"""
    groups: dict[str, list[str]] = {"left": [], "right": [], "top": [], "bottom": []}
    for num in numbers:
        groups[_side_of(names.get(num, "~"))].append(num)

    n_col = max(len(groups["left"]), len(groups["right"]), 1)
    n_row = max(len(groups["top"]), len(groups["bottom"]), 1)
    longest = max([len(names.get(n, "~")) for n in numbers] + [1])

    half_w = max(15.24, (n_row - 1) * 5.08 / 2 + 7.62, longest * 0.9)
    half_h = max(12.7, (n_col - 1) * 2.54 / 2 + 7.62)
    half_w, half_h = _snap(half_w), _snap(half_h)

    offs: dict[str, tuple[float, float, int]] = {}
    for side, nums in groups.items():
        cnt = len(nums)
        for i, num in enumerate(nums):
            if side in ("left", "right"):
                y = ((cnt - 1) / 2 - i) * 2.54
                x = -half_w - PIN_LEN if side == "left" else half_w + PIN_LEN
                angle = 0 if side == "left" else 180
            else:
                x = (i - (cnt - 1) / 2) * 5.08
                y = half_h + PIN_LEN if side == "top" else -half_h - PIN_LEN
                angle = 270 if side == "top" else 90
            offs[num] = (x, y, angle)
    return half_w, half_h, offs


def _sym_ic(name: str, numbers: list[str], names: dict[str, str]) -> str:
    base = name.split(":")[-1]
    half_w, half_h, offs = _ic_geometry(numbers, names)

    pins = []
    for num in numbers:
        x, y, angle = offs[num]
        label = names.get(num, "~") or "~"
        pins.append(
            f"""        (pin passive line (at {_n(x)} {_n(y)} {angle}) (length {_n(PIN_LEN)})
          (name "{label}" (effects (font (size 0.889 0.889))))
          (number "{num}" (effects (font (size 0.889 0.889)))))"""
        )

    return f"""    (symbol "{name}"
      (pin_names (offset 0.254))
      (exclude_from_sim no)
      (in_bom yes)
      (on_board yes)
      (property "Reference" "U" (at {_n(-half_w)} {_n(half_h + 3.81)} 0)
        (effects (font (size 1.27 1.27)) (justify left)))
      (property "Value" "U" (at {_n(-half_w)} {_n(-half_h - 3.81)} 0)
        (effects (font (size 1.27 1.27)) (justify left)))
      (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (property "Datasheet" "~" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (symbol "{base}_0_1"
        (rectangle (start {_n(-half_w)} {_n(half_h)}) (end {_n(half_w)} {_n(-half_h)})
          (stroke (width 0.254) (type default)) (fill (type background)))
      )
      (symbol "{base}_1_1"
{chr(10).join(pins)}
      )
    )"""


# ---------------------------------------------------------------- 符号类型与几何

def _pick_symbol_kind(ref: str, value: str) -> str:
    prefix = "".join(ch for ch in ref if ch.isalpha()).upper()
    if prefix == "R":
        return "RES"
    if prefix == "C":
        return "CAP"
    if prefix in ("Y", "X"):
        return "XTAL"
    if prefix == "D":
        return "LED"
    if prefix == "J":
        return "CONN"
    return "BOX"


def _conn_count(numbers: list[str]) -> int:
    """排针脚数：按用到的最大脚号算，至少 2。"""
    nums = [int(n) for n in numbers if n.isdigit()]
    return max(max(nums) if nums else 1, 2)


def _pin_offsets(kind: str, numbers: list[str], names: dict[str, str] | None = None) -> dict[str, tuple[float, float, int]]:
    if kind in ("RES", "CAP", "XTAL"):
        # 角度必须与符号定义一致：1 脚在上、引脚朝下指向本体 = 270；2 脚 = 90。
        # 写反了会让上下两只脚的引线都往器件内部走，两条线碰在一起 → 两个网络短路。
        return {numbers[0]: (0.0, 3.81, 270), numbers[1]: (0.0, -3.81, 90)}
    if kind == "LED":
        return {"1": (-3.81, 0.0, 0), "2": (3.81, 0.0, 180)}
    if kind == "CONN":
        count = _conn_count(numbers)
        return {
            num: (2.54 + PIN_LEN, ((count - 1) / 2 - i) * 2.54, 180)
            for i, num in enumerate(str(k) for k in range(1, count + 1))
        }
    _hw, _hh, offs = _ic_geometry(numbers, names or {})
    return offs


def _symbol_size(kind: str, numbers: list[str], names: dict[str, str] | None = None) -> tuple[float, float]:
    """半宽/半高，含引脚长度。排版与避让都用它算包围盒。"""
    if kind in ("RES", "CAP", "XTAL"):
        return (2.032, 3.81 + 3.81)
    if kind == "LED":
        return (3.81, 1.27)
    if kind == "CONN":
        count = _conn_count(numbers)
        return (2.54 + 2 * PIN_LEN + 2.54, max(_snap((count - 1) * 2.54 / 2 + 2.54), 3.81) + PIN_LEN)
    hw, hh, _offs = _ic_geometry(numbers, names or {})
    return (hw + PIN_LEN, hh + PIN_LEN)


# ---------------------------------------------------------------- 布局

_PAPERS = [("A4", 297.0, 210.0), ("A3", 420.0, 297.0), ("A2", 594.0, 420.0)]

ROW_STEP = 20.32
COL_GAP = 20.32
_CONN_GAP = 0.0


def _layout(draw: list[tuple[dict, str, list[str], dict[str, str]]]) -> tuple[dict[str, tuple[float, float]], str]:
    """按功能分区排版：主控居中，时钟与连接器在左，其余在右。

    这一版把间距压紧了（上一版给每个引脚留 26mm 标签位，导致器件之间大片空白）。
    压紧是因为现在真的画导线：器件离得近，线才短，图才读得下去。
    """
    if not draw:
        return {}, "A4"

    sizes = {item["ref"]: _symbol_size(kind, nums, names) for item, kind, nums, names in draw}

    # 锚点 = 引脚最多的器件（主控/稳压器），它是读图人的视觉中心
    anchor = max(draw, key=lambda d: len(d[2]))
    a_ref = anchor[0]["ref"]
    a_hw, a_hh = sizes[a_ref]

    clock_refs = {
        item["ref"] for item, _kind, _nums, _names in draw
        if "".join(ch for ch in item["ref"] if ch.isalpha()).upper() in ("Y", "X")
    }
    # 挂在这些网络上的电容跟着晶振走（它们本来就是一簇）
    xtal_nets = {net for (net, pins) in _NET_PINS.items() if any(r in clock_refs for r, _p in pins)}

    # 主控电源脚所在的网络 → 接在这些网络上的电容就是去耦电容，应该贴在芯片上方
    anchor_names = dict(next(e[3] for e in draw if e[0]["ref"] == a_ref))
    anchor_power_nets = {
        _PIN_TO_NET[(a_ref, num)]
        for num, nm in anchor_names.items()
        if _side_of(nm) == "top" and (a_ref, num) in _PIN_TO_NET
    }

    clocks, conns, decoup, right_items = [], [], [], []
    for entry in draw:
        ref = entry[0]["ref"]
        if ref == a_ref:
            continue
        prefix = "".join(ch for ch in ref if ch.isalpha()).upper()
        nets = {_PIN_TO_NET[k] for k in _PIN_TO_NET if k[0] == ref}
        if ref in clock_refs or (prefix == "C" and nets & xtal_nets):
            clocks.append(entry)          # 晶振 + 负载电容：一簇
        elif prefix == "C" and nets & anchor_power_nets:
            decoup.append(entry)          # 去耦：排到芯片正上方
        elif prefix == "J":
            conns.append(entry)           # 电源入口：最左
        else:
            right_items.append(entry)     # 指示/复位等：右侧

    pos: dict[str, tuple[float, float]] = {a_ref: (0.0, 0.0)}

    def stack(items, x: float):
        """同列纵向堆叠并垂直居中。

        间距必须按每个器件的实际高度累加：固定步长装不下 25mm 高的 IC，
        两个器件的包围盒会直接重叠（ESP32 板的 DHT11 和 AMS1117 就这么撞过）。
        """
        if not items:
            return
        gap = 10.16
        heights = [2 * sizes[e[0]["ref"]][1] for e in items]
        total_h = sum(heights) + gap * (len(items) - 1)
        y = -total_h / 2
        for entry, h in zip(items, heights):
            pos[entry[0]["ref"]] = (_snap(x), _snap(y + h / 2))
            y += h + gap

    def col_half_w(items) -> float:
        return max([sizes[e[0]["ref"]][0] for e in items] + [0.0])

    clock_x = -(a_hw + COL_GAP + col_half_w(clocks))
    stack(clocks, clock_x)
    conn_x = clock_x - col_half_w(clocks) - COL_GAP - col_half_w(conns)
    stack(conns, conn_x if conns else 0.0)
    # 右侧多于 4 个器件就分两列：单列堆 7 个会把图拉成一竖条，图幅被迫升到 A2
    if len(right_items) > 4:
        half = (len(right_items) + 1) // 2
        first, second = right_items[:half], right_items[half:]
        first_x = a_hw + COL_GAP + col_half_w(first)
        stack(first, first_x)
        stack(second, first_x + col_half_w(first) + COL_GAP + col_half_w(second))
    else:
        stack(right_items, a_hw + COL_GAP + col_half_w(right_items))

    # 去耦电容横排贴在主控上方：这是"去耦"这个动作在图纸上的固定画法
    if decoup:
        row_y = -(a_hh + 22.86)
        step = 15.24
        x0 = -((len(decoup) - 1) * step) / 2
        for i, entry in enumerate(decoup):
            pos[entry[0]["ref"]] = (_snap(x0 + i * step), _snap(row_y))

    # 由占位反推图幅
    xs, ys = [], []
    for item, kind, nums, names in draw:
        hw, hh = sizes[item["ref"]]
        cx, cy = pos[item["ref"]]
        xs += [cx - hw, cx + hw]
        ys += [cy - hh, cy + hh]

    margin_x, margin_y = 15.24, 15.24
    min_x, max_x = min(xs) - margin_x, max(xs) + margin_x
    min_y, max_y = min(ys) - margin_y, max(ys) + margin_y
    need_w, need_h = max_x - min_x, max_y - min_y

    paper, page_w, page_h = _PAPERS[-1][0], _PAPERS[-1][1], _PAPERS[-1][2]
    for name, pw, ph in _PAPERS:
        if pw >= need_w + 20.32 and ph >= need_h + 20.32:
            paper, page_w, page_h = name, pw, ph
            break

    dx = (page_w - need_w) / 2 - min_x
    dy = (page_h - need_h) / 2 - min_y
    return {ref: (_snap(cx + dx), _snap(cy + dy)) for ref, (cx, cy) in pos.items()}, paper


# ---------------------------------------------------------------- 走线

# 这两个全局量在 build() 里填，_layout 需要知道"谁和谁同网络"才能把器件分到一簇
_NET_PINS: dict[str, list[tuple[str, str]]] = {}
_PIN_TO_NET: dict[tuple[str, str], str] = {}


def _escape(x: float, y: float, angle: int, stub: float = 2.54) -> tuple[float, float, float, float]:
    """引脚端点 → (逃逸点 x, y, 外向 dx, dy)。图纸坐标 Y 向下。"""
    out = {0: (-1.0, 0.0), 180: (1.0, 0.0), 90: (0.0, 1.0), 270: (0.0, -1.0)}[angle]
    return x + out[0] * stub, y + out[1] * stub, out[0], out[1]


def _seg_hits_rect(x1, y1, x2, y2, rect) -> bool:
    """轴对齐线段与矩形（外扩 1.27）是否相交。

    边界算相交（inclusive）：包围盒边界正是引脚尖端所在的位置，用严格不等式会
    漏掉"线正好贴着引脚尖走"的情况——实测就是这条缝把 EN 和 DHT_DATA 并了网。
    """
    rx1, ry1, rx2, ry2 = rect
    m = 1.27
    rx1, ry1, rx2, ry2 = rx1 - m, ry1 - m, rx2 + m, ry2 + m
    if abs(y1 - y2) < 1e-6:  # 水平
        if not (ry1 <= y1 <= ry2):
            return False
        return not (max(x1, x2) < rx1 or min(x1, x2) > rx2)
    if abs(x1 - x2) < 1e-6:  # 垂直
        if not (rx1 <= x1 <= rx2):
            return False
        return not (max(y1, y2) < ry1 or min(y1, y2) > ry2)
    return False


def _pt_on_seg(px: float, py: float, seg) -> bool:
    """点是否落在线段上（含端点）。"""
    x1, y1, x2, y2 = seg
    eps = 1e-6
    if abs(y1 - y2) < eps:  # 水平
        return abs(py - y1) < eps and min(x1, x2) - eps <= px <= max(x1, x2) + eps
    if abs(x1 - x2) < eps:  # 垂直
        return abs(px - x1) < eps and min(y1, y2) - eps <= py <= max(y1, y2) + eps
    return False


def _segs_connect(a, b) -> bool:
    """两条线段会不会被 KiCad 判成电气连通。

    为什么必须查这个：KiCad 的连接判定里，**线的端点搭在另一条线上就是连接**，
    共线重叠更是直接连通；只有"十字交叉且没有 junction"才不连。布线时如果
    两个网络各画各的、互不知情，就会出现"两条竖干线重合 → XTAL1 和 XTAL2 并成
    一个网"这类错误，而 ERC 查不出来（两个被动脚短接不违反任何规则）。
    """
    return (_pt_on_seg(a[0], a[1], b) or _pt_on_seg(a[2], a[3], b)
            or _pt_on_seg(b[0], b[1], a) or _pt_on_seg(b[2], b[3], a))


def _segs_cross(a, b) -> bool:
    """一横一竖、且在各自内部相交（不是端点搭接）。

    交叉本身不导电，是合法画法；但贴着别人的节点交叉会让人误读成连接，
    所以只作为"扣分项"而不是"禁止项"。
    """
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    eps = 1e-6
    if abs(ay1 - ay2) < eps and abs(bx1 - bx2) < eps:
        x, y = bx1, ay1
        return (min(ax1, ax2) + eps < x < max(ax1, ax2) - eps
                and min(by1, by2) + eps < y < max(by1, by2) - eps)
    if abs(ax1 - ax2) < eps and abs(by1 - by2) < eps:
        x, y = ax1, by1
        return (min(bx1, bx2) + eps < x < max(bx1, bx2) - eps
                and min(ay1, ay2) + eps < y < max(ay1, ay2) - eps)
    return False


def _route_net(points: list[tuple[float, float, int, str]],
               boxes: dict[str, tuple[float, float, float, float]],
               used: list[tuple[float, float, float, float]] = (),
               blocked: list[tuple[float, float]] = ()):
    """给一个网络布线，返回 (segments, junctions)；走不通返回 None。

    策略：所有引脚先沿自己的朝向逃出一小段，然后找一条水平或垂直的"干线"把它们串起来。
    这是手画原理图时最常用的画法（一条母线 + 若干下垂线），也最不容易压到器件。

    used / blocked 是**其它网络**已经占用的线段与引脚端点：
    - used：本网络任何一段与之共线重叠或端点搭接，就会被 KiCad 判成连通（并网）；
    - blocked：线正好穿过别人的引脚尖同样会连上，而这偏偏落在包围盒边界上，
      只靠矩形检查漏得掉。两个网络悄悄并成一个，ERC 是查不出来的。
    """
    if len(points) < 2:
        return None

    esc = []
    for (x, y, ang, ref) in points:
        ex, ey, dx, dy = _escape(x, y, ang)
        esc.append((x, y, ex, ey, dx, dy, ref))

    cands: list[tuple[str, float]] = []
    # 候选干线 = 基准位置（最小/最大/中点）× 一组偏移。偏移要细到 2.54：
    # 相邻网络常常贴着同一条走廊走，差 2.54 就能各走各的；档位太粗会被吸附到
    # 别人已占的坐标上，被判成共线重叠，整网只好退回标签（晶振簇就是这样丢的线）。
    offs = (0, 2.54, -2.54, 5.08, -5.08, 7.62, -7.62, 10.16, -10.16, 12.7, -12.7,
            15.24, -15.24, 20.32, -20.32, 22.86, -22.86, 25.4, -25.4, 30.48, -30.48)
    ys = [e[3] for e in esc]
    xs = [e[2] for e in esc]
    for base in (min(ys), max(ys), (min(ys) + max(ys)) / 2):
        for off in offs:
            cands.append(("h", _snap(base + off)))
    for base in (min(xs), max(xs), (min(xs) + max(xs)) / 2):
        for off in offs:
            cands.append(("v", _snap(base + off)))
    seen_c: set[tuple[str, float]] = set()
    uniq: list[tuple[str, float]] = []
    for c in cands:
        if c not in seen_c:
            seen_c.add(c)
            uniq.append(c)
    cands = uniq

    best = None
    for orient, g in cands:
        segs, junctions, length = _build_tree(esc, orient, g)
        if segs is None:
            continue
        hits = 0
        crosses = 0
        for (x1, y1, x2, y2), own in segs:
            # 每个线段只豁免"它自己那只脚"所属的器件：从引脚拉出去的第一段必然
            # 贴着自家包围盒（包围盒已经算进引脚长度）——但同网络的其它器件不能豁免，
            # 否则线会从它们的符号中间穿过去（ESP32 板 +3V3 线穿 DHT11 就是这个原因）
            for ref, rect in boxes.items():
                if ref in own:
                    continue
                if _seg_hits_rect(x1, y1, x2, y2, rect):
                    hits += 1
            # 与其它网络的已有线搭上 = 会把两个网并成一个，电气错误，权重比压器件更高
            for other in used:
                if _segs_connect((x1, y1, x2, y2), other):
                    hits += 1
                elif _segs_cross((x1, y1, x2, y2), other):
                    crosses += 1
            # 线穿过别人引脚尖（哪怕只是擦过包围盒边界）同样会连上
            for (bx, by) in blocked:
                if _pt_on_seg(bx, by, (x1, y1, x2, y2)):
                    hits += 1
        score = hits * 1000 + crosses * 80 + length
        if best is None or score < best[0]:
            best = (score, hits, segs, junctions)

    if best is None or best[1] > 0:
        return None  # 会压到器件就不画，退回标签
    return [s[0] for s in best[2]], best[3]


def _build_tree(esc, orient: str, g: float):
    """按干线方向拼线段。返回 ([(seg, 连接方集合)], junctions, 总长)。"""
    segs: list[tuple[tuple[float, float, float, float], set[str]]] = []
    joins: list[tuple[float, float]] = []
    total = 0.0
    conn_pts = []

    owner_set: set[str] = set()
    for (x, y, ex, ey, dx, dy, ref) in esc:
        owner_set.add(ref)
        # 引脚 → 逃逸点
        if abs(x - ex) > 1e-9 or abs(y - ey) > 1e-9:
            segs.append(((x, y, ex, ey), {ref}))
            total += abs(x - ex) + abs(y - ey)
        # 逃逸点 → 干线
        if orient == "h":
            if abs(ey - g) > 1e-9:
                segs.append(((ex, ey, ex, g), {ref}))
                total += abs(ey - g)
            conn_pts.append((ex, g))
        else:
            if abs(ex - g) > 1e-9:
                segs.append(((ex, ey, g, ey), {ref}))
                total += abs(ex - g)
            conn_pts.append((g, ey))

    if orient == "h":
        xs_ = sorted(p[0] for p in conn_pts)
        if len(xs_) >= 2:
            segs.append(((xs_[0], g, xs_[-1], g), owner_set))
            total += xs_[-1] - xs_[0]
        # 中间落点都是 T 型接头，需要 junction 圆点
        joins = sorted({(px, g) for px in xs_[1:-1]})
    else:
        ys_ = sorted(p[1] for p in conn_pts)
        if len(ys_) >= 2:
            segs.append(((g, ys_[0], g, ys_[-1]), owner_set))
            total += ys_[-1] - ys_[0]
        joins = sorted({(g, py) for py in ys_[1:-1]})

    return segs, joins, total


# ---------------------------------------------------------------- 主流程

def build(bom: dict, netlist: dict) -> str:
    global _NET_PINS, _PIN_TO_NET

    board = bom.get("board", {})
    board_name = board.get("type") or board.get("name") or "board"
    sch_uuid = _uid("root", board_name)
    project = "pcb-agent"

    _PIN_TO_NET = {}
    _NET_PINS = {}
    for net in netlist.get("nets", []):
        pins = [(n["ref"], str(n["pin"])) for n in net.get("pins", [])]
        _NET_PINS[net["name"]] = pins
        for key in pins:
            _PIN_TO_NET[key] = net["name"]

    comps = bom.get("items", [])

    pins_of_ref: dict[str, list[str]] = {}
    for (ref, pin) in _PIN_TO_NET:
        pins_of_ref.setdefault(ref, []).append(pin)
    for ref in pins_of_ref:
        pins_of_ref[ref].sort(key=lambda p: (int(p) if p.isdigit() else 999, p))

    draw: list[tuple[dict, str, list[str], dict[str, str]]] = []
    for item in comps:
        numbers = pins_of_ref.get(item["ref"], [])
        if not numbers:
            continue
        kind = _pick_symbol_kind(item["ref"], item.get("value", ""))
        if kind in ("RES", "CAP", "XTAL") and len(numbers) < 2:
            kind = "BOX"
        names = pinmap.pin_names(item.get("value", ""), numbers) if kind == "BOX" else {}
        draw.append((item, kind, numbers, names))

    pos, paper = _layout(draw)

    lib_defs: list[str] = []
    lib_cache: dict[str, str] = {}

    def lib_name_for(kind: str, numbers: list[str], names: dict[str, str], value: str) -> str:
        if kind in ("RES", "CAP", "XTAL", "LED"):
            name = kind
            if name not in lib_cache:
                factory = {
                    "RES": lambda n: _sym_resistor(n),
                    "CAP": lambda n: _sym_capacitor(n),
                    "XTAL": lambda n: _sym_crystal(n),
                    "LED": lambda n: _sym_led(n),
                }[kind]
                lib_defs.append(factory(f"pcbagent:{name}"))
                lib_cache[name] = f"pcbagent:{name}"
            return lib_cache[name]
        if kind == "CONN":
            count = _conn_count(numbers)
            name = f"CONN_1x{count:02d}"
            if name not in lib_cache:
                lib_defs.append(_sym_conn(f"pcbagent:{name}", count))
                lib_cache[name] = f"pcbagent:{name}"
            return lib_cache[name]
        # 有引脚名的器件按型号建符号（同名同形，可复用）；没名字的按引脚集合去重
        tag = re.sub(r"[^0-9A-Za-z_.+-]", "_", value) if pinmap.has_names(names) else "BOX_" + "_".join(numbers)
        name = f"IC_{tag}"
        if name not in lib_cache:
            lib_defs.append(_sym_ic(f"pcbagent:{name}", numbers, names))
            lib_cache[name] = f"pcbagent:{name}"
        return lib_cache[name]

    body: list[str] = []
    boxes: dict[str, tuple[float, float, float, float]] = {}
    pin_pts: dict[tuple[str, str], tuple[float, float, int]] = {}

    for item, kind, numbers, names in draw:
        ref = item["ref"]
        lib_id = lib_name_for(kind, numbers, names, item.get("value", ""))
        cx, cy = pos[ref]

        if kind in ("BOX", "CONN"):
            half_w, half_h = _symbol_size(kind, numbers, names)
            ref_x, ref_y = cx - half_w - 2.54, cy - half_h - 2.54
            val_y = ref_y - 2.54
            justify = " (justify left)"
        elif kind == "LED":
            ref_x, ref_y = cx - 1.27, cy - 5.08
            val_y = cy + 5.08
            justify = " (justify left)"
        else:
            ref_x, ref_y = cx + 4.318, cy - 1.27
            val_y = cy + 1.27
            justify = " (justify left)"

        body.append(
            f"""  (symbol (lib_id "{lib_id}") (at {_n(cx)} {_n(cy)} 0) (unit 1)
    (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)
    (uuid "{_uid('sym', ref)}")
    (property "Reference" "{ref}" (at {_n(ref_x)} {_n(ref_y)} 0)
      (effects (font (size 1.27 1.27)){justify}))
    (property "Value" "{item.get('value', '')}" (at {_n(ref_x)} {_n(val_y)} 0)
      (effects (font (size 1.27 1.27)){justify}))
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

        half_w, half_h = _symbol_size(kind, numbers, names)
        boxes[ref] = (cx - half_w - PIN_LEN, cy - half_h - PIN_LEN,
                      cx + half_w + PIN_LEN, cy + half_h + PIN_LEN)

        offsets = _pin_offsets(kind, numbers, names)
        for num in numbers:
            ox, oy, ang = offsets[num]
            # 符号 +Y 向上，图纸 Y 向下，所以取负
            pin_pts[(ref, num)] = (cx + ox, cy - oy, ang)

    # ---- 连线：能画导线的网络画导线，画不动的退回网络标签
    wire_lines: list[str] = []
    label_lines: list[str] = []
    routed: set[str] = set()
    used_segs: list[tuple[float, float, float, float]] = []

    # 每个引脚"引脚尖 → 逃逸点"这一小段要算作其它网络的禁区：
    # 别人的干线只要压在这个点上，KiCad 就认成连通（EN 与 DHT_DATA 就是这样并的）
    reserved: list[tuple[tuple[float, float, float, float], tuple[str, str]]] = []
    for (ref, num), (gx, gy, ang) in pin_pts.items():
        ex, ey, _, _ = _escape(gx, gy, ang)
        reserved.append(((gx, gy, ex, ey), (ref, num)))

    # 引脚朝向查表：回退画标签时要知道"这只脚属于什么器件"，
    # 之前这里复用了外层循环残留的 kind，CONN 的 2.54 引出量会串到所有器件上
    kind_of: dict[str, str] = {item["ref"]: k for item, k, _, _ in draw}

    # 先布"器件少、跨距短"的网：它们的走线选择余地最小，越晚布越容易被别人占掉通道
    route_order = sorted(
        (n for n, p in _NET_PINS.items() if 2 <= len(p) <= 3),
        key=lambda n: (len(_NET_PINS[n]), n),
    )

    for net_name in route_order:
        pins = _NET_PINS[net_name]
        if any(p not in pin_pts for p in pins):
            continue
        mine = set(pins)
        pts = [(pin_pts[k][0], pin_pts[k][1], pin_pts[k][2], k[0]) for k in pins]
        blocked = [(pin_pts[k][0], pin_pts[k][1]) for k in pin_pts
                   if _PIN_TO_NET.get(k) != net_name]
        guard = used_segs + [seg for seg, owner in reserved if owner not in mine]
        res = _route_net(pts, boxes, guard, blocked)
        if not res:
            continue
        segs, junctions = res
        routed.add(net_name)
        used_segs.extend(segs)
        for i, (x1, y1, x2, y2) in enumerate(segs):
            wire_lines.append(
                f"""  (wire (pts (xy {_n(x1)} {_n(y1)}) (xy {_n(x2)} {_n(y2)}))
    (stroke (width 0) (type default))
    (uuid "{_uid('wire', net_name, i)}")
  )"""
            )
        for i, (jx, jy) in enumerate(junctions):
            wire_lines.append(
                f"""  (junction (at {_n(jx)} {_n(jy)}) (diameter 0) (color 0 0 0 0)
    (uuid "{_uid('junction', net_name, i)}")
  )"""
            )

    for net_name, pins in _NET_PINS.items():
        if net_name in routed:
            continue
        for (ref, num) in pins:
            if (ref, num) not in pin_pts:
                continue
            gx, gy, ang = pin_pts[(ref, num)]
            dx, dy = {0: (-1.0, 0.0), 180: (1.0, 0.0), 90: (0.0, 1.0), 270: (0.0, -1.0)}[ang]
            # 只有上下朝向的引脚需要引出一段：它们的标签会压住符号内的引脚名。
            # 左右朝向的引脚标签本来就在符号外，再引出反而会跟相邻引脚的标签挤在一起。
            stub = 5.08 if dy != 0 else (2.54 if kind_of.get(ref) == "CONN" else 0.0)
            ex, ey = gx + dx * stub, gy + dy * stub
            if stub:
                wire_lines.append(
                    f"""  (wire (pts (xy {_n(gx)} {_n(gy)}) (xy {_n(ex)} {_n(ey)}))
    (stroke (width 0) (type default))
    (uuid "{_uid('stub', ref, num, net_name)}")
  )"""
                )
            ang_label = 0 if dy == 0 and dx > 0 else (180 if dy == 0 else 0)
            justify = "right" if ang_label == 180 else "left"
            label_lines.append(
                f"""  (label "{net_name}" (at {_n(ex)} {_n(ey)} {ang_label})
    (effects (font (size 1.143 1.143)) (justify {justify} bottom))
    (uuid "{_uid('label', ref, num, net_name)}")
  )"""
            )

    lib_symbols = "\n".join(lib_defs)
    body_text = "\n".join(body + wire_lines + label_lines)

    return f"""(kicad_sch
  (version 20231120)
  (generator "eeschema")
  (generator_version "8.0")
  (uuid "{sch_uuid}")
  (paper "{paper}")
  (title_block
    (title "{board_name}")
    (rev "1")
    (comment 1 "Generated by PCB-Agent — 本地网络走导线，长网络用网络标签")
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
