# 05 · Git 留痕规范（10 分过程分）

> 老师原话：**"每周进展以 commit 为证，仓库就是你的成长日记。"**
> 判分的不是代码总量，是**时间线的形状**。最后一周刷 50 个 commit 一看就知道，反而扣分。

---

## 一、核心原则

1. **一周至少 1 次提交，理想是 3–5 次。** 每次提交对应"一件做完的事"。
2. **提交时间要散开。** 8 周里均匀分布，而不是集中在 W7–W8。
3. **失败也要提交。** `experiment:` 前缀的失败尝试是报告"失败案例"的素材，也是真实性的证据。
4. **不要提交密钥。** `.env`、`config.local.py` 必须在 `.gitignore` 里。**一旦推上去就改不掉了**（历史里永远留着），要立刻去平台作废该 key。

---

## 二、Commit Message 约定

格式：`<类型>(<模块>): <做了什么>`

| 类型 | 用在哪 | 例子 |
|---|---|---|
| `feat` | 新功能 | `feat(netlist): 支持引脚级连接生成` |
| `fix` | 修 bug | `fix(schema): BOM 校验漏掉封装字段` |
| `refactor` | 重构不提功能 | `refactor(kicad): 抽出 s-expr 拼接器` |
| `docs` | 文档 | `docs: 补 README 的 5 分钟快速开始` |
| `test` | 测试 | `test: 加 10 条需求回归集` |
| `chore` | 杂务 / 周报 | `chore(progress): W3 check-in` |
| `experiment` | **失败或探索** | `experiment: 试直接生成 kicad_sch，KiCad 打开空框` |

规则：
- 一行说清"做了什么"，不要写 "update"、"fix bug"、"111"；
- 同一次提交只做一件事（不要把 Prompt 改动和 KiCad 导出混一起）；
- 重要决策写进 commit 正文（`-m` 第二段），未来写报告直接抄。

---

## 三、每周 check-in 流程（5 分钟）

```bash
# 1. 改完代码、跑通测试
python src/pipeline.py "帮我设计一块 Arduino 最小系统板"

# 2. 写周报 + 自动提交（一条命令搞定）
python scripts/checkin.py --week 3 \
  --done "打通引脚级网表，3 种板子都过自检" \
  --blocker "LLM 偶尔漏去耦电容" \
  --next "接 KiCad 导出" \
  --commit --push
```

`checkin.py` 做的事：
1. 在 `PROGRESS.md` 的进度表里追加一行（周次 / 日期 / 做了什么 / 卡点 / 下周）；
2. `git add -A` + `git commit -m "chore(progress): W3 check-in"`；
3. 加 `--push` 就推到远端。

> **周日晚上固定做。** 建议手机设个每周提醒。

---

## 四、分支策略：一个人也建议用

不用搞复杂的 GitFlow，两条分支就够：

```
main        ← 随时可运行（README 里的命令一定能跑通）
  └ dev     ← 日常开发，允许半成品
```

- 平时在 `dev` 上提交，**每周 check-in 时把 `dev` merge 回 `main`**；
- `main` 上的每个点都是一个"可演示版本"，答辩前如果新代码崩了，可以回退到最近的 `main`。

```bash
git checkout dev
git checkout main
git merge dev --no-ff -m "release: W3 可演示版本"
git push origin main
```

如果嫌麻烦，单人项目直接全在 `main` 上也行——**但一定要每周有 commit**。

---

## 五、仓库初始化的坑

### GitHub / Gitee 上建仓库时
- **不要勾选** "Add a README / .gitignore / license"——会和本地冲突，第一次 push 就报错。

### 本地推上去
```bash
cd pcb-agent
git init -b main
git add -A
git commit -m "chore: 初始化项目骨架"
git remote add origin https://github.com/<你的用户名>/pcb-agent.git
git push -u origin main
```

### 没配过身份会报错
```bash
git config --global user.name "你的名字"
git config --global user.email "你的邮箱"
```

### 国内网络推不动
- 用 Gitee（PPT 里也写了 Gitee 可以），或
- GitHub 走 SSH key，或
- 配代理：`git config --global http.proxy http://127.0.0.1:7890`

---

## 六、8 周 commit 时间线样例（供自查）

```
W1  ██ 3  chore: 初始化 / feat: mock 流水线 / docs: README
W2  ███ 4  feat: 接入真实 LLM / feat: Schema 校验 / docs: 失败案例 / experiment: few-shot 无效
W3  ████ 5 feat: 引脚级网表 / feat: validate / test: 回归集 / fix: 网络命名 / docs: 周报
W4  ████ 5 feat: 三种板型 / feat: revise 增量修正 / ...
W5  ███ 4  feat: kicad 单器件 / experiment: 直拼 s-expr 失败 / feat: lib_symbols / docs: 技术选型
W6  ████ 5 feat: 连线生成 / feat: 封装赋值 / fix: ...
W7  ███ 4  feat: DRC 闭环 / chore: 实验数据 / docs: 报告初稿 / ...
W8  ██ 3   docs: 报告终稿 / docs: 答辩PPT / chore: README 自测修复
```

自查方法（答辩前跑一下）：

```bash
git log --date=short --pretty=format:'%ad %s' | sort | awk '{print $1}' | uniq -c
```

看看每周的提交数量，如果某周是 0，想办法补一个"该周实际做过的事"的提交（**不要伪造时间戳**，如实补即可）。

---

## 七、必须在 README 里写清的外部来源

学术诚信要求"参考他人代码注明出处"：

```markdown
## 参考出处
- 课程模板工程：https://...
- kiutils（KiCad 文件读写库）：https://github.com/mvnmgrx/kiutils
- 器件白名单参考：https://...
- 以下代码由 AI 生成后本人修改：src/kicad_export.py 的 s-expr 拼接部分
```
