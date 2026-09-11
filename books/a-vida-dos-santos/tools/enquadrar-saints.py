#!/usr/bin/env python3
"""Enquadra cada gravura em 3:4, no papel da edição, sem cortar o santo."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "images" / "saints"
W, H = 720, 960
PAPER = (243, 237, 223)  # #F3EDDF
PAD = 0.08


def fit(path: Path) -> None:
    with Image.open(path) as original:
        image = original.convert("RGB")
    canvas = Image.new("RGB", (W, H), PAPER)
    inner_w, inner_h = round(W * (1 - 2 * PAD)), round(H * (1 - 2 * PAD))
    scale = min(inner_w / image.width, inner_h / image.height)
    size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    fitted = image.resize(size, Image.Resampling.LANCZOS)
    x = (W - fitted.width) // 2
    y = (H - fitted.height) // 2
    canvas.paste(fitted, (x, y))
    canvas.save(path, "JPEG", quality=88, optimize=True)


def main() -> None:
    files = sorted(SRC.glob("*.jpg"))
    for path in files:
        fit(path)
        print(path.name)
    print(f"enquadradas {len(files)} em {W}x{H}")


if __name__ == "__main__":
    main()
