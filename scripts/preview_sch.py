"""原理图预览：kicad-cli 导出 PDF → 渲染 PNG，方便肉眼检查排版。

为什么单独写这个脚本：
    ERC 只验电气，验不了"这张图能不能读"。改排版时必须看图，
    靠文字日志判断不了导线有没有压器件、标签有没有叠在一起。
    这个脚本只给开发时用，核心流水线不依赖它（pypdfium2 是可选依赖）。

用法：
    python scripts/preview_sch.py                # 默认 out/board.kicad_sch
    python scripts/preview_sch.py out/board.kicad_sch out/preview.png
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

KICAD_CLI = Path(r"D:\Kicad\bin\kicad-cli.exe")


def main() -> int:
    sch = Path(sys.argv[1] if len(sys.argv) > 1 else "out/board.kicad_sch")
    png = Path(sys.argv[2] if len(sys.argv) > 2 else "out/preview.png")
    if not sch.exists():
        print(f"找不到 {sch}")
        return 1

    pdf = png.with_suffix(".pdf")
    r = subprocess.run(
        [str(KICAD_CLI), "sch", "export", "pdf",
         "--exclude-drawing-sheet", "--no-background-color",
         "-o", str(pdf), str(sch)],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        print(r.stdout, r.stderr)
        return r.returncode

    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(str(pdf))
    page = doc[0]
    img = page.render(scale=2.4).to_pil()
    png.parent.mkdir(parents=True, exist_ok=True)
    img.save(png)
    print(f"OK -> {png}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
