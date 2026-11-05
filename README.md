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
ls out/            # bom.csv / bom.json / netlist.json / board.net
```

预期输出类似：

```
[1/5] 解析需求 ............ OK  板卡: Arduino 最小系统板, 主控: ATmega328P-AU, 供电: 5V
[2/5] 生成 BOM ............ OK  Arduino 最小系统板 / ATmega328P-AU / 11 项元器件
[3/5] 生成引脚级网表 ...... OK  8 个网络 / 29 个引脚连接
[4/5] 自检（类 DRC） ...... OK  无悬空网络、无重复引脚、无未定义器件
[5/5] 导出 ................ OK  out/bom.csv, out/bom.json, out/netlist.json, out/board.net
```

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
│   ├── validate.py         # 自检：悬空网络、重复引脚、器件缺号
│   └── kicad_export.py     # JSON → KiCad 网表（.net）与原理图骨架
├── scripts/
│   └── checkin.py          # 每周 check-in：写 PROGRESS.md + git commit
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

## AI 使用声明（必填，学术诚信要求）

| 环节 | 用了什么 | 说明 |
|---|---|---|
| 代码骨架 | Claude / ChatGPT | 脚手架、JSON Schema、导出脚本初版由 AI 生成，本人改写与调试 |
| Prompt | | |
| 文档 / 报告 | | |
| 图 / PPT | | |

关键设计决策（为什么这么连、为什么这么写 Prompt）必须能口头解释，答辩会问。

## 参考出处

- 课程模板工程：`<填写课程提供的仓库地址>`
- KiCad 8 官方文档：https://docs.kicad.org/
- `<其他引用的开源仓库>`

---

## 当前状态

见 [PROGRESS.md](./PROGRESS.md)。
