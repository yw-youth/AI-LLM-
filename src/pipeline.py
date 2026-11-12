"""五步走主流程 —— 这就是作业的"基础任务 40 分"。

    [1/5] 环境检查       Python 版本 / KiCad 是否在 PATH
    [2/5] 需求 → BOM      LLM 或 mock
    [3/5] BOM → 网表      引脚级连接（ref + pin → net）
    [4/5] 自检            悬空网络 / 引脚冲突 / 未定义器件
    [5/5] 导出            bom.csv / bom.json / netlist.json / board.net / board.kicad_sch

用法：
    python src/pipeline.py "帮我设计一块 Arduino 最小系统板"
    python src/pipeline.py "帮我设计一块 ESP32 温湿度采集板" --live
    python src/pipeline.py "帮我设计一块 Arduino 最小系统板" --revise "把 C3 换成 100nF"
"""

from __future__ import annotations

import argparse
import platform
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import design
import kicad_export
import kicad_sch
import llm
import validate

ROOT = Path(__file__).resolve().parent.parent
MAX_RETRY = 2  # 单阶段最多重试次数；进阶「DRC 闭环」可以调大


# ---------------------------------------------------------------- 输出样式


class Log:
    def __init__(self) -> None:
        self.t0 = time.time()

    def step(self, n: int, title: str) -> None:
        print(f"[{n}/5] {title} ", end="", flush=True)

    def ok(self, msg: str = "OK") -> None:
        # step() 结尾没换行，这里接着打在同一行
        print(f"OK  {msg}   ({time.time() - self.t0:.1f}s)")

    def fail(self, msg: str) -> None:
        print(f"FAIL  {msg}")

    def info(self, msg: str) -> None:
        print(f"        {msg}")


# ---------------------------------------------------------------- 各阶段


def step_env(log: Log) -> bool:
    log.step(1, "环境检查       ")
    v = sys.version_info
    if v < (3, 10):
        log.fail(f"Python {v.major}.{v.minor} 太低，需要 3.10+")
        return False
    bits = [f"Python {v.major}.{v.minor}.{v.micro}"]
    kicad = shutil.which("kicad") or shutil.which("kicad-cli")
    bits.append("KiCad 在 PATH" if kicad else "KiCad 未在 PATH（不影响本步，W5 需要）")
    bits.append("API Key 已配置" if llm.has_key() else "无 API Key → 使用 mock 模型")
    log.ok(" / ".join(bits))
    return True


def _generate_live(log: Log, prompt_name: str, user_msg: str, checker) -> dict:
    """带反馈重试的单阶段生成 —— 这就是最小可用的 Agent 闭环。"""
    system = llm.load_prompt("system")
    user = user_msg
    last_err: list[dict] = []
    for attempt in range(1, MAX_RETRY + 2):
        raw = llm.chat(system, user)
        try:
            data = llm.extract_json(raw)
        except Exception as e:  # noqa: BLE001
            last_err = [{"level": "ERROR", "code": "parse", "msg": f"输出不是合法 JSON：{e}"}]
            user = f"{user_msg}\n\n{validate.format_for_llm(last_err)}"
            log.info(f"第 {attempt} 次：JSON 解析失败，回填错误后重试")
            continue

        errors = checker(data)
        if not validate.has_errors(errors):
            if attempt > 1:
                log.info(f"第 {attempt} 次通过（前 {attempt - 1} 次被自检驳回）")
            return data
        last_err = [e for e in errors if e["level"] == "ERROR"]
        user = f"{user_msg}\n\n{validate.format_for_llm(last_err)}"
        log.info(f"第 {attempt} 次：{validate.summarize(errors)}，回填后重试")

    raise RuntimeError("模型连续多次未通过自检：" + validate.format_for_llm(last_err))


def step_bom(log: Log, requirement: str, live: bool) -> dict:
    log.step(2, "需求 → BOM     ")
    if live:
        bom = _generate_live(
            log,
            "bom",
            llm.load_prompt("bom").replace("{requirement}", requirement),
            validate.check_bom,
        )
    else:
        bom = design.mock_bom(requirement)
    n = len(bom["items"])
    log.ok(f"{bom['board']['type']} / {bom['board']['mcu']} / {n} 项元器件")
    return bom


def step_netlist(log: Log, bom: dict, requirement: str, live: bool) -> dict:
    log.step(3, "BOM → 网表     ")
    if live:
        import json

        user = (
            llm.load_prompt("netlist")
            .replace("{requirement}", requirement)
            .replace("{bom_json}", json.dumps(bom, ensure_ascii=False))
        )
        netlist = _generate_live(log, "netlist", user, lambda d: validate.check_netlist(d, bom))
    else:
        netlist = design.mock_netlist(bom, requirement)
    pins = sum(len(n["pins"]) for n in netlist["nets"])
    log.ok(f"{len(netlist['nets'])} 个网络 / {pins} 个引脚连接")
    return netlist


def step_validate(log: Log, bom: dict, netlist: dict) -> list[dict]:
    log.step(4, "自检（类 DRC）  ")
    errors = validate.check_bom(bom) + validate.check_netlist(netlist, bom)
    if validate.has_errors(errors):
        log.fail(validate.summarize(errors))
        for e in errors:
            log.info(f"  [{e['level']}][{e['code']}] {e['msg']}")
        return errors
    log.ok(validate.summarize(errors))
    warns = [e for e in errors if e["level"] == "WARN"]
    for w in warns:
        log.info(f"  [WARN] {w['msg']}")
    return errors


def step_export(log: Log, bom: dict, netlist: dict, out: Path) -> list[Path]:
    log.step(5, "导出           ")
    files = [
        kicad_export.write_bom_csv(bom, out / "bom.csv"),
        kicad_export.write_json(bom, out / "bom.json"),
        kicad_export.write_json(netlist, out / "netlist.json"),
        kicad_export.write_kicad_netlist(bom, netlist, out / "board.net"),
    ]
    # 原理图工程包（.kicad_sch + 符号库 + 库表 + .kicad_pro）
    files += kicad_sch.write_project(bom, netlist, out, stem="board")
    log.ok(", ".join(p.name for p in files))
    return files


def step_revise(log: Log, bom: dict, instruction: str, live: bool) -> dict:
    print()
    print(f"追问修正：{instruction}")
    if live:
        import json
        import os

        prompt = llm.load_prompt("bom")
        user = (
            f"{prompt}\n\n"
            f"当前 BOM：\n{json.dumps(bom, ensure_ascii=False, indent=2)}\n\n"
            f"修改要求：{instruction}\n\n"
            "只改被点名的器件，其余原样返回。"
        )
        new = llm.extract_json(llm.chat(llm.load_prompt("system"), user))
        if validate.has_errors(validate.check_bom(new)):
            print("    模型改出了不合法的 BOM，已回退到原版本")
            return bom
    else:
        new = design.mock_revise(bom, instruction)

    changes = kicad_export.diff_bom(bom, new)
    for c in changes:
        print(f"    {c}")
    return new


# ---------------------------------------------------------------- 入口


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="自然语言 → BOM → 网表 → KiCad")
    ap.add_argument("requirement", help="一句话需求，例如：帮我设计一块 Arduino 最小系统板")
    ap.add_argument("--live", action="store_true", help="调用真实 LLM（需 OPENAI_API_KEY）")
    ap.add_argument("--revise", default="", help='追问修正，例如："把 C3 换成 100nF"')
    ap.add_argument("--out", default="out", help="输出目录（默认 out/）")
    args = ap.parse_args(argv)

    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out

    log = Log()
    print(f"需求：{args.requirement}")
    mode = "真实模型（--live）" if args.live else "mock 规则模型（零额度，断网可跑）"
    print(f"模式：{mode}")
    print()

    if not step_env(log):
        return 2

    reason = design.out_of_scope(args.requirement)
    if reason:
        log.step(2, "需求可行性     ")
        log.fail("超出能力边界，拒绝生成")
        print(f"        理由：{reason}")
        print("        能做的范围：常见的单片最小系统、传感采集、线性稳压小板（单/双面板，网表级）。")
        print("        建议：把需求收敛到「用途 + 主控 + 供电」，再跑一次。")
        return 3

    bom = step_bom(log, args.requirement, args.live)
    netlist = step_netlist(log, bom, args.requirement, args.live)
    errors = step_validate(log, bom, netlist)

    if args.revise:
        bom = step_revise(log, bom, args.revise, args.live)
        netlist = design.mock_netlist(bom, args.requirement) if not args.live else step_netlist(
            log, bom, args.requirement, True
        )

    if validate.has_errors(errors):
        print()
        print("自检未通过，已停止导出。修掉上面的 ERROR 再跑一次。")
        return 1

    step_export(log, bom, netlist, out)
    print()
    print(f"完成。产物在 {out}")
    print(f"下一步：用 KiCad 打开 {out / 'board.kicad_pro'} 查看原理图。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
