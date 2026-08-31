"""Recorta gravuras de cabeçalho e a capa a partir das páginas raster."""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pieces import PIECES

ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "source" / "images" / "pages"
EXTRACTED = ROOT / "source" / "images" / "extracted"
RESTORED = ROOT / "source" / "images" / "restored"


def crop_box(img: Image.Image, frac: tuple[float, float, float, float]) -> Image.Image:
    w, h = img.size
    x0, y0, x1, y1 = frac
    return img.crop((int(w * x0), int(h * y0), int(w * x1), int(h * y1)))


def save_pair(src: Image.Image, stem: str) -> None:
    EXTRACTED.mkdir(parents=True, exist_ok=True)
    RESTORED.mkdir(parents=True, exist_ok=True)
    rgb = src.convert("RGB")
    rgb.save(EXTRACTED / f"{stem}.png")
    rgb.save(RESTORED / f"{stem}.png")
    print(f"{stem} {rgb.size}")


def crop_cover() -> None:
    page = Image.open(PAGES / "p001.png")
    # Corta a lombada vermelha à esquerda.
    save_pair(crop_box(page, (0.035, 0.0, 1.0, 1.0)), "capa")


EXTRA_CROPS = [
    ("as-estacoes-inverno", 33, (0.06, 0.02, 0.96, 0.38)),
    ("as-estacoes-primavera", 35, (0.06, 0.02, 0.96, 0.38)),
    ("as-estacoes-verao", 37, (0.06, 0.02, 0.96, 0.38)),
    ("as-estacoes-outono", 39, (0.06, 0.02, 0.96, 0.40)),
]


def crop_piece(piece: dict) -> None:
    crop = piece.get("crop")
    if not crop:
        return
    pdf = piece["pdf"][0]
    path = PAGES / f"p{pdf:03d}.png"
    if not path.exists():
        raise SystemExit(f"página ausente: {path}")
    save_pair(crop_box(Image.open(path), crop), piece["id"])


def main() -> None:
    if not (PAGES / "p001.png").exists():
        raise SystemExit("rode scripts/extract_pages.py primeiro")
    only = set(sys.argv[1:])
    crop_cover()
    for piece in PIECES:
        if only and piece["id"] not in only:
            continue
        crop_piece(piece)
    for stem, pdf, frac in EXTRA_CROPS:
        if only and stem not in only:
            continue
        path = PAGES / f"p{pdf:03d}.png"
        save_pair(crop_box(Image.open(path), frac), stem)


if __name__ == "__main__":
    main()
