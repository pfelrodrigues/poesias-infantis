"""Rasteriza o PDF colorido da BBM para source/images/pages/."""

from __future__ import annotations

from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
SCAN = ROOT / "source" / "scans" / "002924_c_COMPLETO.pdf"
OUT = ROOT / "source" / "images" / "pages"
# 2× o tamanho do PDF (~150 dpi nativo → ~300 dpi de trabalho).
ZOOM = 2.0


def main() -> None:
    if not SCAN.exists():
        raise SystemExit(f"scan ausente: {SCAN}")
    OUT.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open(SCAN)
    matrix = pymupdf.Matrix(ZOOM, ZOOM)
    for i, page in enumerate(doc, start=1):
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        dest = OUT / f"p{i:03d}.png"
        pix.save(dest)
        print(f"{dest.name} {pix.width}x{pix.height}")
    print(f"{len(doc)} páginas em {OUT}")


if __name__ == "__main__":
    main()
