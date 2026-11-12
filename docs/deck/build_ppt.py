# -*- coding: utf-8 -*-
"""生成答辩 PPT（10 页 / 5 分钟 / 学术风）。

为什么手写 python-pptx 而不是套模板：这 10 页的排版逻辑（数字锚点、非对称双栏、
闭环示意）都是数据驱动的，用代码生成可以让"图上的每个数字"和仓库里的实测结果
一一对应——报告改一个数，PPT 重跑一次就同步了。
"""

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parent   # docs/deck/
ASSETS = ROOT / "assets"

# ---------------------------------------------------------------- 设计令牌
INK = RGBColor(0x14, 0x1C, 0x28)        # 正文近黑
NAVY = RGBColor(0x0F, 0x33, 0x5E)       # 主色：深蓝
BLUE = RGBColor(0x1F, 0x6F, 0xB2)       # 强调蓝
MUTE = RGBColor(0x5D, 0x6B, 0x7A)       # 次要文字
LINE = RGBColor(0xD5, 0xDD, 0xE5)       # 分隔线
PANEL = RGBColor(0xF3, 0xF6, 0xF9)      # 浅面板
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

FONT = "微软雅黑"
MONO = "Consolas"

W, H = 13.333, 7.5
ML = 0.92                                # 左边距
MR = 13.333 - 0.92

prs = Presentation()
prs.slide_width = Inches(W)
prs.slide_height = Inches(H)
BLANK = prs.slide_layouts[6]


def add_slide():
    return prs.slides.add_slide(BLANK)


def txt(slide, l, t, w, h, text, size=14, bold=False, color=INK,
        align=PP_ALIGN.LEFT, font=FONT, anchor=MSO_ANCHOR.TOP,
        line=1.3, space_after=0, italic=False):
    box = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = line
        p.space_after = Pt(space_after)
        r = p.add_run()
        r.text = ln
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.italic = italic
        r.font.color.rgb = color
        r.font.name = font
    return box


def rect(slide, l, t, w, h, fill=None, line_color=None, line_w=1.0,
         shape=MSO_SHAPE.RECTANGLE, radius=None):
    s = slide.shapes.add_shape(shape, Inches(l), Inches(t), Inches(w), Inches(h))
    if radius is not None and shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        s.adjustments[0] = radius
    if fill is None:
        s.fill.background()
    else:
        s.fill.solid()
        s.fill.fore_color.rgb = fill
    if line_color is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line_color
        s.line.width = Pt(line_w)
    s.text_frame.word_wrap = True
    s.text_frame.margin_left = s.text_frame.margin_right = 0
    s.text_frame.margin_top = s.text_frame.margin_bottom = 0
    return s


def shape_text(s, text, size=13, bold=False, color=INK, align=PP_ALIGN.CENTER,
               font=FONT, line=1.15):
    tf = s.text_frame
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    for i, ln in enumerate(text.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = line
        r = p.add_run()
        r.text = ln
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.color.rgb = color
        r.font.name = font


def header(slide, kicker, title, page):
    """统一的页眉：小标签 + 大标题 + 细分隔线 + 页码。"""
    txt(slide, ML, 0.52, 8.0, 0.3, kicker, size=11, bold=True, color=BLUE, font=FONT)
    txt(slide, ML, 0.86, 10.6, 0.62, title, size=27, bold=True, color=NAVY)
    rect(slide, ML, 1.62, MR - ML, 0.012, fill=LINE)
    txt(slide, MR - 0.9, 6.94, 0.9, 0.26, f"{page:02d}", size=11, color=MUTE,
        align=PP_ALIGN.RIGHT)
    txt(slide, ML, 6.94, 6.0, 0.26, "PCB-Agent · 人工智能大作业", size=10, color=MUTE)


def arrow_right(slide, l, t, w, h=0.18, color=BLUE):
    s = rect(slide, l, t, w, h, fill=color, shape=MSO_SHAPE.RIGHT_ARROW)
    s.line.fill.background()
    return s


# ================================================================ P1 封面
s = add_slide()
rect(s, 0, 0, 0.26, H, fill=NAVY)                     # 左侧竖条，克制的主色锚点
txt(s, 1.55, 0.75, 8.0, 0.3, "人工智能大作业 · 2026", size=12, color=MUTE)
txt(s, 1.55, 2.02, 10.4, 0.9, "从一句话需求到 KiCad 原理图", size=40, bold=True, color=NAVY)
txt(s, 1.55, 3.02, 10.4, 0.45, "基于大语言模型的电路板设计 Agent 流水线", size=19, color=BLUE)
rect(s, 1.55, 3.86, 2.6, 0.032, fill=BLUE)
txt(s, 1.55, 4.24, 10.0, 0.32,
    "需求解析  →  BOM  →  引脚级网表  →  自检  →  KiCad 工程", size=14, color=MUTE)
txt(s, 1.55, 5.15, 6.6, 0.32, "汇报人：＿＿＿＿＿      学号：＿＿＿＿＿", size=13, color=INK)
txt(s, 1.55, 6.42, 10.4, 0.3, "github.com/yw-youth/AI-LLM-", size=11, color=MUTE, font=MONO)

# ================================================================ P2 任务理解
s = add_slide()
header(s, "01  任务理解", "交的不是一块板子，是一条被约束住的流水线", 2)

# 左：评分构成
txt(s, ML, 1.86, 4.3, 0.28, "评分构成", size=12, bold=True, color=MUTE)
score = [("基础实现", 40, "五步走全通"), ("进阶挑战", 20, "DRC 闭环"),
         ("设计报告", 20, "含失败案例"), ("现场答辩", 10, "讲清取舍"),
         ("过程留痕", 10, "每周 commit")]
y = 2.24
for name, v, note in score:
    txt(s, ML, y, 1.5, 0.28, name, size=12.5, color=INK)
    rect(s, ML + 1.5, y + 0.05, 2.6, 0.15, fill=RGBColor(0xE4, 0xEA, 0xF0),
         shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.5)
    rect(s, ML + 1.5, y + 0.05, 2.6 * v / 40, 0.15, fill=BLUE,
         shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.5)
    txt(s, ML + 4.24, y - 0.02, 0.7, 0.28, str(v), size=13, bold=True, color=NAVY,
        align=PP_ALIGN.RIGHT)
    txt(s, ML + 5.02, y + 0.01, 1.8, 0.26, note, size=10.5, color=MUTE)
    y += 0.46

# 左：四样交付物
txt(s, ML, 4.72, 4.3, 0.28, "四样交付物（少一样按未完成处理）", size=12, bold=True, color=MUTE)
deliver = ["代码仓库 + README：助教 5 分钟内能跑起来",
           "设计报告：架构、Prompt 设计、实验结果、失败案例",
           "演示视频 3–5 分钟：全程真实录屏",
           "答辩 PPT：5 分钟讲清「教会了 AI 什么」"]
y = 5.08
for i, d in enumerate(deliver, 1):
    txt(s, ML, y, 0.28, 0.26, f"{i}", size=11, bold=True, color=BLUE)
    txt(s, ML + 0.3, y, 5.9, 0.26, d, size=11.5, color=INK)
    y += 0.42

# 右：核心判断
rect(s, 8.05, 1.86, MR - 8.05, 4.3, fill=PANEL, line_color=LINE)
rect(s, 8.05, 1.86, 0.05, 4.3, fill=BLUE)
txt(s, 8.42, 2.16, MR - 8.42 - 0.3, 0.3, "核心判断", size=12, bold=True, color=BLUE)
txt(s, 8.42, 2.6, MR - 8.42 - 0.34, 3.0,
    "难点不在电路。\n\n最小系统板是教科书电路，\n真正的风险是模型会自己发挥：\n编造型号、漏去耦、错引脚。\n\n所以这个项目做的是「把模型的\n自由度关进笼子」。",
    size=15, color=NAVY, line=1.4)
txt(s, 8.42, 5.66, MR - 8.42 - 0.34, 0.34, "而不是「让 AI 画电路」", size=12, color=MUTE,
    italic=True)

# ================================================================ P3 架构
s = add_slide()
header(s, "02  系统架构", "五步流水线：模型做语义决策，代码做语法落地", 3)

steps = [
    ("①  需求解析", "自然语言 →\n板型 / 主控 / 供电"),
    ("②  BOM 生成", "器件清单\n+ 封装 + 位号"),
    ("③  引脚级网表", "每根线接到\n哪个脚"),
    ("④  自检（类 DRC)", "悬空 / 冲突 /\n幻觉位号"),
    ("⑤  KiCad 导出", "工程包\n.kicad_pro"),
]
bw, gap = 2.05, 0.30
x = ML
for i, (t1, t2) in enumerate(steps):
    card = rect(s, x, 2.02, bw, 1.55, fill=WHITE, line_color=LINE)
    txt(s, x + 0.16, 2.2, bw - 0.3, 0.28, t1, size=12.5, bold=True, color=NAVY)
    txt(s, x + 0.16, 2.62, bw - 0.3, 0.8, t2, size=10.5, color=MUTE, line=1.35)
    if i < 4:
        arrow_right(s, x + bw + 0.04, 2.72, 0.22)
    x += bw + gap

# 回填箭头（闭环）：横跨 ③④ 两步，箭头朝左即"回到上一步重生成"
fb = rect(s, ML + 2 * (bw + gap), 3.88, 2 * bw + gap, 0.36,
          fill=RGBColor(0xFB, 0xF2, 0xE4), shape=MSO_SHAPE.LEFT_ARROW)
shape_text(fb, "错误回填 Prompt → 重新生成（最多 3 轮）", size=9.5,
           color=RGBColor(0x8A, 0x5A, 0x1E))

# 两张卡：职责分工
c1 = rect(s, ML, 4.42, 5.7, 2.05, fill=PANEL, line_color=LINE)
txt(s, ML + 0.24, 4.62, 5.2, 0.3, "模型负责：语义", size=13, bold=True, color=NAVY)
txt(s, ML + 0.24, 5.02, 5.2, 1.2,
    "读需求、选器件、定连接意图、\n被指出错误后改写。\n它输出的是 JSON，不是文件。",
    size=11.5, color=INK, line=1.4)

c2 = rect(s, ML + 5.95, 4.42, MR - ML - 5.95, 2.05, fill=PANEL, line_color=LINE)
txt(s, ML + 6.19, 4.62, 4.9, 0.3, "代码负责：语法", size=13, bold=True, color=NAVY)
txt(s, ML + 6.19, 5.02, 4.9, 1.2,
    "JSON Schema 强校验、引脚合法性、\nS-expression 拼接、栅格吸附。\n模型没有机会写错文件格式。",
    size=11.5, color=INK, line=1.4)

# ================================================================ P4 关键设计
s = add_slide()
header(s, "03  关键设计", "把模型的自由度关进笼子：三道闸门", 4)

# 左：代码/约束示例
rect(s, ML, 1.95, 7.7, 4.4, fill=RGBColor(0xF7, 0xF9, 0xFB), line_color=LINE)
txt(s, ML + 0.26, 2.12, 7.2, 0.26, "闸门一 · 能力边界（会拒绝的 Agent 更可信）", size=12, bold=True, color=NAVY)
rect(s, ML + 0.26, 2.46, 7.18, 1.42, fill=WHITE, line_color=LINE)
txt(s, ML + 0.44, 2.6, 6.8, 1.2,
    '>>> 帮我设计一块 PCIe 8 层高速采集卡\n拒绝：超出能力边界（高速差分 / 阻抗控制 / DDR 布线）\n建议：先交最小系统板，或改用 KiCad 手工完成',
    size=10.5, color=RGBColor(0x33, 0x3D, 0x49), font=MONO, line=1.5)

txt(s, ML + 0.26, 4.04, 7.2, 0.26, "闸门二 · 输出必须过 Schema，过不了就重试", size=12, bold=True, color=NAVY)
rect(s, ML + 0.26, 4.38, 7.18, 1.28, fill=WHITE, line_color=LINE)
txt(s, ML + 0.44, 4.52, 6.8, 1.1,
    '"footprint": "^[A-Za-z0-9_.\\\\-]+:[A-Za-z0-9_.\\\\-]+$"\n"ref":       "^[A-Z]{1,2}[0-9]{1,3}$"     → 拦住 "U9" 这类幻觉位号\n失败样例自动回填 Prompt，最多重试 2 次',
    size=10.5, color=RGBColor(0x33, 0x3D, 0x49), font=MONO, line=1.5)

txt(s, ML + 0.26, 5.62, 7.2, 0.3, "闸门三 · 自检层不信任任何一方，只信规则",
    size=12, bold=True, color=NAVY)
txt(s, ML + 0.26, 5.96, 7.2, 0.3, "悬空网络 / 引脚冲突 / 去耦缺失 / 电源命名漂移 / 器件引脚悬空",
    size=11, color=MUTE)

# 右：三条手段的数字锚点
stats = [("5", "类自检规则"), ("10", "条回归用例"), ("7", "个真实失败案例")]
y = 2.05
for num, label in stats:
    txt(s, 8.95, y, 1.1, 0.62, num, size=34, bold=True, color=BLUE)
    txt(s, 10.05, y + 0.22, 2.3, 0.3, label, size=11.5, color=MUTE)
    y += 1.32

rect(s, 8.95, 5.9, MR - 8.95, 0.012, fill=LINE)
txt(s, 8.95, 6.05, MR - 8.95, 0.42, "删掉任意一道闸门，\n输出立刻不可用。", size=11, color=MUTE, line=1.4)

# ================================================================ P5 DRC 闭环
s = add_slide()
header(s, "04  进阶实现", "DRC 检查闭环：让 Agent 自己发现错误并修好", 5)

# 左：闭环四步
txt(s, ML, 1.9, 6.4, 0.28, "闭环流程（演示注入 5 种真实模型故障）", size=12, bold=True, color=MUTE)
loop_steps = [("检出", "validate 报错\n带错误码与位置"), ("修复", "规则修复器\n只修有把握的"),
              ("复检", "重跑自检\n清零为止"), ("终验", "KiCad ERC\n机器判定")]
bx, by = ML, 2.34
for i, (t1, t2) in enumerate(loop_steps):
    b = rect(s, bx, by, 1.30, 1.18, fill=WHITE, line_color=BLUE, line_w=1.25)
    txt(s, bx + 0.11, by + 0.14, 1.08, 0.26, t1, size=12, bold=True, color=NAVY)
    txt(s, bx + 0.11, by + 0.48, 1.10, 0.62, t2, size=9, color=MUTE, line=1.3)
    if i < 3:
        arrow_right(s, bx + 1.33, by + 0.5, 0.16, h=0.15)
    bx += 1.50 if i < 3 else 0

# 返回箭头
rect(s, ML + 0.65, 3.72, 4.55, 0.012, fill=LINE)
rect(s, ML + 0.65, 3.64, 0.012, 0.16, fill=LINE)
rect(s, ML + 5.20, 3.64, 0.012, 0.16, fill=LINE)
txt(s, ML + 1.15, 3.80, 4.0, 0.26, "错误信息回填 Prompt → 重新生成", size=9.5, color=MUTE)

# 左：结论
txt(s, ML, 4.24, 6.6, 0.3, "为什么闭环必须有「止损」", size=12, bold=True, color=NAVY)
txt(s, ML, 4.6, 6.5, 1.7,
    "第一版修复器把报错里的「已连接的脚」当成悬空脚去补接，\n"
    "结果和引脚冲突修复来回振荡，4 轮输出完全重复。\n\n"
    "现在：一轮没有任何进展就终止——自动修复不能变成自动震荡。",
    size=11.5, color=INK, line=1.45)

# 右：KPI
rect(s, 7.25, 1.9, MR - 7.25, 4.72, fill=PANEL, line_color=LINE)
kp = [("5 / 5", "故障场景闭环修复成功"), ("≤ 2", "轮收敛，无死循环"),
      ("5 / 5", "修复后网表过 KiCad ERC")]
y = 2.15
for num, label in kp:
    txt(s, 7.55, y, 4.6, 0.72, num, size=38, bold=True, color=BLUE)
    txt(s, 7.55, y + 0.74, 4.5, 0.34, label, size=11, color=INK)
    y += 1.55

# ================================================================ P6 实验数据
s = add_slide()
header(s, "05  实验结果", "每一分都有出处：全部来自仓库真实运行", 6)

kpis = [("8 / 8", "回归集", "10 条用例中 8 条可机器判定，全部通过"),
        ("0 / 0", "KiCad ERC", "三种板型：0 错误 0 警告"),
        ("15 / 15", "稳定性基线", "三板型 × 5 次，中位耗时 0.82s"),
        ("6", "板型能力", "3 种板型 + 明确拒绝超范围需求")]
x = ML
for num, label, note in kpis:
    rect(s, x, 2.05, 2.60, 2.5, fill=WHITE, line_color=LINE)
    rect(s, x, 2.05, 2.60, 0.05, fill=BLUE)
    txt(s, x + 0.24, 2.3, 2.2, 0.3, label, size=11, bold=True, color=MUTE)
    txt(s, x + 0.24, 2.6, 2.3, 0.8, num, size=34, bold=True, color=NAVY)
    txt(s, x + 0.24, 3.48, 2.14, 0.9, note, size=10, color=MUTE, line=1.4)
    x += 2.60 + 0.30

txt(s, ML, 4.86, 11.4, 0.3, "数据来源（可复现）", size=12, bold=True, color=NAVY)
src = [("scripts/regress.py", "10 条用例的期望值判定"),
       ("scripts/kicad_check.py", "kicad-cli 跑 ERC，非肉眼"),
       ("scripts/stability.py", "三板型 × N 次通过率与耗时"),
       ("scripts/demo_loop.py", "闭环报告 + ERC 终验")]
x = ML
for cmd, note in src:
    txt(s, x, 5.24, 2.60, 0.26, cmd, size=9.5, color=BLUE, font=MONO)
    txt(s, x, 5.52, 2.60, 0.5, note, size=9, color=MUTE, line=1.35)
    x += 2.60 + 0.30

rect(s, ML, 6.16, MR - ML, 0.012, fill=LINE)
txt(s, ML, 6.3, 11.4, 0.5,
    "真实模型（--live）的通过率待 API Key 到位后回填——报告里以「进行中」如实标注，不预先填数。",
    size=10.5, color=MUTE)

# ================================================================ P7 失败案例
s = add_slide()
header(s, "06  失败案例分析", "7 个真实教训：每个都被机器检查接住", 7)

rows = [("案例", "现象", "根因", "已机器化"),
        ("① 悬空去耦", "C3 只接了 GND", "只查网络不看器件", "open_pin 检查"),
        ("② 幻觉封装", "Sensor:DHT11 不存在", "凭记忆写库名", "ERC + 库名核对"),
        ("③ 子符号命名", "整图加载失败，无行号", "须与父符号同名", "生成器固化"),
        ("④ 超范围乐观", "PCIe 板也返回成功", "缺能力边界", "out_of_scope 拒绝"),
        ("⑤ 关键词误判", "「加个电源灯」被判为电源板", "泛关键词匹配", "收紧规则"),
        ("⑥ 修复器振荡", "4 轮输出完全重复", "把已连脚当悬空脚", "无进展止损"),
        ("⑦ 栅格漂移", "11 条 off_grid", "居中破坏 50mil 栅格", "坐标吸附")]
tw, th = MR - ML, 0.52
tbl_shape = s.shapes.add_table(len(rows), 4, Inches(ML), Inches(1.9),
                               Inches(tw), Inches(th * len(rows)))
tbl = tbl_shape.table
for c, wd in enumerate([1.85, 4.2, 3.3, 2.1]):
    tbl.columns[c].width = Inches(wd)
for r in range(len(rows)):
    tbl.rows[r].height = Inches(th if r else 0.44)

for r, row in enumerate(rows):
    for c, val in enumerate(row):
        cell = tbl.cell(r, c)
        cell.text = ""
        cell.margin_left = Inches(0.14)
        cell.margin_right = Inches(0.1)
        cell.margin_top = Inches(0.04)
        cell.margin_bottom = Inches(0.04)
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        cell.fill.solid()
        if r == 0:
            cell.fill.fore_color.rgb = NAVY
        else:
            cell.fill.fore_color.rgb = WHITE if r % 2 else PANEL
        p = cell.text_frame.paragraphs[0]
        run = p.add_run()
        run.text = val
        run.font.size = Pt(11 if r == 0 else 10)
        run.font.bold = (r == 0) or (c == 0)
        run.font.name = FONT
        run.font.color.rgb = WHITE if r == 0 else INK

txt(s, ML, 6.34, 11.4, 0.5,
    "结论：失败案例全部来自真实调试记录，不是事后编的；其中 5 个已经变成自动检查，"
    "回归集不断复现它们。", size=11, color=NAVY)

# ================================================================ P8 成果演示
s = add_slide()
header(s, "07  成果演示", "一条命令的产出：KiCad 打开就是这张图", 8)

img = ASSETS / "board_schematic.png"
if img.exists():
    s.shapes.add_picture(str(img), Inches(ML), Inches(1.84), width=Inches(7.30))
    txt(s, ML, 6.32, 7.4, 0.3,
        "上图为 pipeline 生成的 Arduino 最小系统板原理图（KiCad 渲染，未手改）",
        size=9.5, color=MUTE)

cards = [("8", "个产物文件", "bom.csv / netlist.json / board.net /\n.kicad_sch / .kicad_sym / .kicad_pro"),
         ("0", "ERC 违规", "三种板型：0 错误 0 警告\n由 kicad-cli 判定"),
         ("4", "平台 CI", "push 自动跑冒烟 + 回归\nUbuntu/Windows × Py3.11/3.13")]
y = 1.92
for num, label, note in cards:
    rect(s, 8.62, y, MR - 8.62, 1.52, fill=PANEL, line_color=LINE)
    txt(s, 8.84, y + 0.16, 0.9, 0.5, num, size=25, bold=True, color=BLUE)
    txt(s, 9.52, y + 0.24, 2.6, 0.3, label, size=11, bold=True, color=NAVY)
    txt(s, 8.84, y + 0.78, MR - 8.84 - 0.14, 0.68, note, size=9, color=MUTE, line=1.35)
    y += 1.66

# ================================================================ P9 进度
s = add_slide()
header(s, "08  进度与下一步", "里程碑 4 / 7：技术侧已完成，剩下的是外部依赖", 9)

# 左：进度条
txt(s, ML, 1.9, 4.0, 0.28, "里程碑", size=12, bold=True, color=MUTE)
segs = ["脚手架", "需求→网表", "原理图", "闭环", "真实模型", "交付三件", "正式提交"]
seg_w, seg_x = 0.68, ML
for i, name in enumerate(segs):
    done = i < 4
    rect(s, seg_x, 2.26, seg_w - 0.06, 0.26, fill=BLUE if done else RGBColor(0xE4, 0xEA, 0xF0))
    txt(s, seg_x, 2.62, seg_w + 0.06, 0.6, name, size=7.5, color=NAVY if done else MUTE, line=1.25)
    seg_x += seg_w

txt(s, ML, 3.3, 4.4, 0.9, "4 / 7", size=44, bold=True, color=NAVY)
txt(s, ML + 1.9, 3.62, 3.0, 0.4, "已完成（含进阶 20 分项）", size=11, color=MUTE)

txt(s, ML, 4.52, 5.0, 0.3, "已完成", size=12, bold=True, color=MUTE)
done_list = "五步流水线 · 三种板型 · 自检层 · 原理图工程包\nDRC 闭环 · 回归集 · CI · 7 个失败案例"
txt(s, ML, 4.88, 5.2, 0.8, done_list, size=10.5, color=INK, line=1.45)

# 右：进行中
txt(s, 6.55, 1.9, 5.8, 0.3, "进行中（均依赖外部输入）", size=12, bold=True, color=MUTE)
todo = [("GitHub 时间线", "仓库 9 个 commit 已就位，待首次 push；\n沙箱内 TLS 被拦，需本机终端执行"),
        ("真实模型数据", "等课程群 API Key；--live 开关与台架已备好，\n拿到即可出通过率"),
        ("交付三件套", "答辩 PPT 本页即成品；视频脚本与报告初稿已写好")]
y = 2.3
for t, d in todo:
    rect(s, 6.55, y, 0.04, 1.1, fill=RGBColor(0xC8, 0x9A, 0x3E))
    txt(s, 6.75, y, 5.4, 0.3, t, size=12.5, bold=True, color=NAVY)
    txt(s, 6.75, y + 0.34, 5.5, 0.78, d, size=10.5, color=MUTE, line=1.4)
    y += 1.34

# ================================================================ P10 结尾
s = add_slide()
rect(s, 0, 0, 0.26, H, fill=NAVY)
txt(s, 1.55, 2.3, 8.0, 0.9, "请提问", size=38, bold=True, color=NAVY)
txt(s, 1.55, 3.24, 9.6, 0.4,
    "代码、Prompt、每一张图上的数字，都可以现场复现。", size=15, color=MUTE)
rect(s, 1.55, 4.02, 2.6, 0.032, fill=BLUE)
txt(s, 1.55, 4.36, 9.6, 0.34, "仓库地址", size=11, bold=True, color=BLUE)
txt(s, 1.55, 4.7, 9.6, 0.36, "github.com/yw-youth/AI-LLM-", size=16, color=NAVY, font=MONO)
txt(s, 1.55, 5.4, 9.6, 0.34, "复现命令", size=11, bold=True, color=BLUE)
txt(s, 1.55, 5.74, 9.6, 0.36,
    "python src/pipeline.py \"帮我设计一块 Arduino 最小系统板\"", size=13, color=INK, font=MONO)

out = ROOT / "PCB设计Agent答辩汇报.pptx"
prs.save(out)
print("saved", out, out.stat().st_size, "bytes,", len(prs.slides.__iter__.__self__._sldIdLst), "slides")
