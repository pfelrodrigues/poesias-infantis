"""Recorta e restaura a gravura de cabeçalho de A Avó (página 9 do PDF).

O pixmap composto lê melhor que o JPEG embutido: o PDF empilha duas
imagens e a extração crua sai desbotada. Não inverter; o papel já é creme.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "source" / "images" / "pages" / "p009.png"
EXTRACTED = ROOT / "source" / "images" / "extracted" / "avo-cabecalho.png"
RESTORED = ROOT / "source" / "images" / "restored" / "avo-cabecalho.png"

# Fração da página 9: o desenho. O título tipográfico fica de fora.
CROP_FRAC = (0.07, 0.02, 0.95, 0.395)


def restore(img: Image.Image) -> Image.Image:
    # Neste dpi o recorte limpo é o restauro. Contraste agressivo apaga o papel.
    return img.convert("RGB")


def main() -> None:
    if not PAGE.exists():
        raise SystemExit(f"página ausente: {PAGE} (rode extract_pages.py)")
    page = Image.open(PAGE)
    w, h = page.size
    x0, y0, x1, y1 = CROP_FRAC
    box = (int(w * x0), int(h * y0), int(w * x1), int(h * y1))
    crop = page.crop(box)
    EXTRACTED.parent.mkdir(parents=True, exist_ok=True)
    RESTORED.parent.mkdir(parents=True, exist_ok=True)
    crop.save(EXTRACTED)
    restore(crop).save(RESTORED)
    print(f"extracted {EXTRACTED} {crop.size}")
    print(f"restored  {RESTORED}")


if __name__ == "__main__":
    main()
