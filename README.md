# PCB-Agent：自然语言 → KiCad 原理图

> 人工智能课程大作业 · AI Agent 电路板设计
> 你输入一句话需求，Agent 产出 BOM 元器件清单 + 引脚级网表 + KiCad 可打开的原理图。

---

## 这是什么

不是"用 AI 帮你画板子"，而是**造一个会画板子的 Agent**。核心是一条六段式流水线：

| 段 | 做什么 | 关键产出 |
|---|---|---|
| 起点 | 自然语言需求 | `需求文本` |
| 核心 | LLM + Prompt 设计 | 结构化设计意图 |
| 桥梁 | 结构化输出 | `bom.json` / `netlist.json` |
| 落地 | KiCad 脚本接口 | `*.kicad_sch` / `*.net` |
| 成果 | 原理图 · PCB | KiCad 中真实可打开 |
| 闭环 | 自检 / DRC 反馈 | 错误 → 改 Prompt → 重跑 |

## 5 分钟跑起来（不需要 API Key）

```bash
# 1. 环境：Python 3.10+（不需要第三方依赖）
python --version

# 2. 跑通最小闭环（用内置 mock 模型，不消耗额度）
python src/pipeline.py "帮我设计一块 Arduino 最小系统板"

# 3. 看产物
ls out/            # bom.csv / bom.json / netlist.json / board.net / board.kicad_sch ...
```

预期输出类似：

```
[1/5] 环境检查        OK  Python 3.13 / KiCad 未在 PATH（不影响本步） / 无 API Key → 使用 mock 模型
[2/5] 需求 → BOM      OK  Arduino 最小系统板 / ATmega328P-AU / 11 项元器件
[3/5] BOM → 网表      OK  8 个网络 / 30 个引脚连接
[4/5] 自检（类 DRC）   OK  无悬空网络、无重复引脚、无未定义器件
[5/5] 导出            OK  bom.csv, bom.json, netlist.json, board.net, board.kicad_sch, ...
```

## 在 KiCad 里看结果 + 机器验收

用 **KiCad 8** 打开 `out/board.kicad_pro`，就能看到自动生成的原理图（器件符号 + 网络标签）。

想证明"真的没问题"不要靠肉眼，跑 KiCad 自带的电气规则检查：

```bash
python scripts/kicad_check.py          # 自动找 kicad-cli，跑 ERC，汇总错误/警告数
```

当前三种板型的结果均为 **0 错误 / 0 警告**（明细见 `out/board.erc.rpt`）。

> 连接用**网络标签**表达（同名即同网络），不画 wire——这是"连接正确性"与"画图工作量"
> 之间的取舍，报告的技术选型一节有完整说明。

接真实大模型时：

```bash
export OPENAI_API_KEY=sk-xxx          # 或学校算力平台给的 key
export OPENAI_BASE_URL=https://api.xxx/v1   # 兼容 OpenAI 协议的任意端点
export PCB_AGENT_MODEL=gpt-4o-mini
python src/pipeline.py "帮我设计一块 ESP32 温湿度采集板" --live
```

## 目录结构

```
pcb-agent/
├── README.md               # 本文件（助教按这里能在 5 分钟内跑起来）
├── PROGRESS.md             # 周报 / 留痕时间线，checkin.py 自动追加
├── requirements.txt
├── prompts/                # 提示词工程，全部可版本化、可 diff
│   ├── system.md           #   角色与输出约束
│   ├── bom.md              #   需求 → BOM
│   ├── netlist.md          #   BOM → 引脚级连接
│   └── revise.md           #   追问修正（"把电容换成 100nF"）
├── schemas/                # JSON Schema，约束 LLM 输出，避免解析失败
│   ├── bom.schema.json
│   └── netlist.schema.json
├── src/
│   ├── pipeline.py         # 五步主流程 + 编排
│   ├── llm.py              # LLM 调用封装（兼容 OpenAI 协议）+ mock 兜底
│   ├── design.py           # 需求解析 / BOM / 网表 的 mock 规则实现
│   ├── validate.py         # 自检：悬空网络、重复引脚、器件缺号、两脚器件单端悬空
│   ├── kicad_sch.py        # 网表 → 原理图工程（.kicad_sch + 符号库 + 库表 + .kicad_pro）
│   └── kicad_export.py     # JSON → KiCad 网表（.net）
├── scripts/
│   ├── checkin.py          # 每周 check-in：写 PROGRESS.md + git commit + 密钥扫描
│   ├── kicad_check.py      # 调 kicad-cli 跑 ERC，把"能打开"变成机器判据
│   └── regress.py          # 10 条用例回归集（mock 可判定项的基线）
├── .github/workflows/      # CI：push 时自动跑冒烟 + 回归（Linux/Windows × 2 个 Python 版本）
├── .env.example            # 环境变量模板（复制为 .env，已被 gitignore）
├── LICENSE                 # MIT
├── docs/
│   ├── 01-任务拆解与评分策略.md
│   ├── 02-8周执行计划.md
│   ├── 03-设计报告骨架.md
│   ├── 04-答辩5分钟提纲.md
│   └── 05-Git留痕规范.md
└── out/                    # 运行产物（已被 .gitignore 忽略）
```

## 对照评分表

| 项 | 分值 | 怎么拿 |
|---|---|---|
| 基础功能 | 40 | 五步走全部跑通：环境 → BOM → 连接关系 → KiCad 原理图 → 追问修正 |
| 进阶挑战 | 20 | 建议选「DRC 检查闭环」（`src/validate.py` 已是雏形，最容易变成完整闭环） |
| 设计报告 | 20 | 按 `docs/03-设计报告骨架.md` 填，重点写**失败案例** |
| 答辩演示 | 10 | 按 `docs/04-答辩5分钟提纲.md` 讲，现场真跑一次 |
| 过程表现 | 10 | 每周 `python scripts/checkin.py` 一条 commit，见 `PROGRESS.md` |

## AI 使用声明（学术诚信要求，如实申报）

| 环节 | 用了什么 | 说明 |
|---|---|---|
| 代码骨架 | AI 助手（WorkBuddy） | 流水线骨架、JSON Schema、导出与自检脚本初版由 AI 生成，本人逐行审查、调试并修正（如封装命名正则、电源板关键词误判） |
| Prompt | AI 助手初稿 + 本人迭代 | `prompts/` 四个模板；失败案例驱动的改写由本人完成 |
| 文档 / 报告 | 本人撰写，AI 辅助排版 | 技术决策、实验数据均为本人产出 |
| 图 / PPT | | |

> 待办：报告提交前逐行核对本表，与实际使用情况一致；`<你的姓名/学号>` 处见 LICENSE。

关键设计决策（为什么这么连、为什么这么写 Prompt）必须能口头解释，答辩会问。

## 参考出处

- 课程模板工程：`<!-- TODO：拿到课程模板仓库后，在此填地址并注明借鉴了哪些部分 -->`
- KiCad 8 官方文档：https://docs.kicad.org/
- KiCad 网表格式（`board.net` 的目标格式）：https://dev-docs.kicad.org/en/file-formats/

---

## 当前状态

见 [PROGRESS.md](./PROGRESS.md)。
