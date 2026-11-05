# PROGRESS · 进度留痕

> 老师原话：**每周进展以 commit 为证，仓库就是你的"成长日记"。**
> 这张表就是过程分（10 分）的证据链。每周日花 5 分钟，一条命令更新。

*最后更新：2026-11-05*

## 每周 check-in

| 周次 | 日期 | 本周完成 | 自检/失败实验 | 卡点 | 下周计划 |
|---|---|---|---|---|---|
| W1 | 2026-11-05 | 搭建项目骨架：五步流水线(mock 可跑)、BOM/网表 Schema、Prompt 模板、自检层、导出层、checkin 脚本 | 自检 0 错误 | KiCad 尚未安装 | 装 KiCad 8 + 配 API Key，跑真实模型 |
<!-- checkin:end -->

## 里程碑

- [x] W1 脚手架跑通（`python src/pipeline.py "..."` 能出 4 个产物文件）
- [ ] W2 会写工具调用 / Prompt 稳定产出合规 BOM
- [ ] W3–W4 MVP 演示（需求 → BOM + 网表）
- [ ] W5–W6 原理图生成（KiCad 打开成功）
- [ ] W7 闭环通过（DRC 自纠）
- [ ] W8 正式交付（仓库 + 报告 + 视频 + PPT）

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
