"""LLM 调用封装。

设计目标：
1. 只用标准库，助教不用 pip install 就能跑通（README 承诺 5 分钟）。
2. 兼容任意 OpenAI 协议的端点（OpenAI / DeepSeek / 通义 / 学校算力平台）。
3. 没有 key 时明确报错，由 pipeline 回落到 mock，保证演示不会挂。
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROMPTS = ROOT / "prompts"


class LLMError(RuntimeError):
    """模型调用失败（网络 / 鉴权 / 额度）。"""


def has_key() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY", "").strip())


def load_prompt(name: str) -> str:
    """从 prompts/<name>.md 里取出提示词正文。

    约定：文件里有 ``` 围栏就取第一个围栏块；没有则取第一个 --- 之后的内容。
    这样提示词既能当文档读，也能被程序直接吃。
    """
    path = PROMPTS / f"{name}.md"
    text = path.read_text(encoding="utf-8")
    m = re.search(r"```[a-zA-Z]*\n(.*?)```", text, re.S)
    if m:
        return m.group(1).strip()
    m = re.search(r"^---\s*$(.*)", text, re.S | re.M)
    return (m.group(1) if m else text).strip()


def chat(system: str, user: str, temperature: float = 0.1, timeout: int = 90) -> str:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        raise LLMError("未设置 OPENAI_API_KEY")

    base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.environ.get("PCB_AGENT_MODEL", "gpt-4o-mini")

    payload = json.dumps(
        {
            "model": model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        f"{base}/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")[:300]
        raise LLMError(f"HTTP {e.code}: {detail}") from e
    except Exception as e:  # noqa: BLE001 网络异常统一包一层
        raise LLMError(f"请求失败: {e}") from e

    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise LLMError(f"响应结构异常: {str(data)[:300]}") from e


def extract_json(text: str) -> dict:
    """从模型回复里捞出 JSON。

    模型即使被要求"只输出 JSON"，也常带上 ```json 围栏或一句"好的，以下是……"。
    这是实战中最常见的失败点，所以在代码里兜一层，而不是指望提示词。
    """
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    if not text.startswith("{"):
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end <= start:
            raise ValueError("回复里找不到 JSON 对象")
        text = text[start : end + 1]
    return json.loads(text)
