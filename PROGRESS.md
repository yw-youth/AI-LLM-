# PROGRESS · 进度留痕

> 老师原话：**每周进展以 commit 为证，仓库就是你的"成长日记"。**  
> 这张表就是过程分（10 分）的证据链。每周日花 5 分钟，一条命令更新。

*最后更新：2026-11-12*

## 每周 check-in

> 说明：学期 W7 布置作业，W7–W9 为调研期未提交；W10 起每周固定 checkin。
> 对应关系：学期 W10 ≈ 项目补课周（补齐原 W1 环境账）。

| 周次 | 日期         | 本周完成                                                             | 自检/失败实验 | 卡点         | 下周计划                        |
| -- | ---------- | ---------------------------------------------------------------- | ------- | ---------- | --------------------------- |
| W1 | 2026-11-05 | 搭建项目骨架：五步流水线(mock 可跑)、BOM/网表 Schema、Prompt 模板、自检层、导出层、checkin 脚本 | 自检 0 错误 | KiCad 尚未安装 | 装 KiCad 8 + 配 API Key，跑真实模型 |
| W10 | 2026-11-06 | 原理图生成打通：`kicad_sch.py` 输出 KiCad 8 工程包（.kicad_sch + 符号库 + 库表 + .kicad_pro）；三种板型 ERC 均 0 错误 0 警告；自检层补"器件引脚悬空"检查 | 3 板型 ERC 0/0；修掉 C3 悬空、DHT11 封装名两处真 bug | KiCad 只有 10.0.7（课程要 8） | 装 KiCad 8.0 复验；接真实模型 |
| W10 | 2026-11-10 | DRC 检查闭环：`loop.py/repair.py/faults.py` + `demo_loop.py`，5 故障场景（去耦悬空/幻觉位号/引脚冲突/电源混用/缺GND）全部 ≤2 轮收敛，修复结果过 KiCad ERC 5/5；发现并修复"修复器振荡"bug（失败案例 6） | 闭环 5/5；ERC 终验 5/5 PASS | 无 | GitHub 推送；KiCad 8 复验 |
| W10 | 2026-11-11 | W11/W14 提前：稳定性台架 `stability.py`（三板型×5 基线 15/15，中位 0.82–0.87s）；设计报告初稿 `docs/07-设计报告初稿.md`（六章全，数字来自真实运行，⏳ 项待 --live 回填） | mock 基线 15/15 | API Key 未配、GitHub 未推 | --live 后跑 `stability.py --live` 回填报告 4.2/4.3 节 |
| W11 | 2026-11-12 | ① 原理图排版重做：按功能分区（主控居中/电源时钟在左/去耦指示在右）+ 图幅 A4-A3-A2 自适应 + 1.27mm 栅格吸附；② 版本策略定案：产物写 v8 格式、用 KiCad 10 验证，取消"必须装 8"的前置条件；③ 答辩 PPT 成品（10 页）与演示视频脚本；④ 仓库身份与远程对齐 `github.com/yw-youth/AI-LLM-` | 美化后 ERC 曾跳 11 条 endpoint_off_grid，吸附后回落 0/0（失败案例 7） | GitHub TLS 在沙箱被拦，push 需本机执行 | 本机 push；拿到 API Key 后回填真实模型数据 |

## 里程碑

- [x] 脚手架跑通（`python src/pipeline.py "..."` 能出产物文件）
- [x] 需求 → BOM + 引脚级网表（三种板型；回归集 8/8）
- [x] 原理图生成（`out/board.kicad_pro` 可打开；ERC 0 错误 0 警告）
- [x] DRC 闭环（5 故障场景 ≤2 轮收敛，修复结果过 KiCad ERC 5/5；`out/loop_report.md`）
- [x] 设计报告初稿（`docs/07-设计报告初稿.md`；⏳ 项待 --live 数据回填）
- [x] 答辩 PPT（`docs/deck/答辩PPT.pptx`，10 页；`build_ppt.py` 可重建）
- [x] 演示视频脚本（`docs/08-演示视频脚本.md`：分镜/旁白/命令清单）
- [ ] 真实模型接入（台架已备好：`python scripts/stability.py --live`）
- [ ] 演示视频录制（脚本已就绪，需本机录屏 + 配音）
- [ ] 正式交付（仓库 + 报告 + 视频 + PPT 齐备后提交）

## 怎么更新

```bash
python scripts/checkin.py --week 2 \
  --done "接入真实模型，BOM 输出连续 5 次通过 Schema" \
  --blocker "去耦电容偶尔漏" \
  --next "做引脚级网表" --commit
```

加 `--push` 会顺便推到 GitHub。

## 自查：commit 时间线

```bash
git log --date=short --pretty=format:'%ad' | sort | uniq -c
```

每周都应该有数字。某周是 0，说明那一周没有留痕——过程分就少一块。
| W11 | 2026-11-12 | 新增 scripts/rehearse.bat：录视频前一键彩排（清空 out、跑主流程、ERC、闭环），确认全绿再开机录 | — | 无 | 推 GitHub + 领 Key 跑 --live + 按分镜表录视频 |
