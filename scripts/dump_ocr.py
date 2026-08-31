"""Despeja o texto OCR do PDF colorido, página a página."""

from __future__ import annotations

from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
SCAN = ROOT / "source" / "scans" / "002924_c_COMPLETO.pdf"
OUT = ROOT / "source" / "facsimile" / "ocr-dump.txt"


def main() -> None:
    doc = pymupdf.open(SCAN)
    chunks: list[str] = []
    for i, page in enumerate(doc, start=1):
        text = (page.get_text() or "").rstrip()
        chunks.append(f"===== PDF {i:03d} =====\n{text}\n")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(chunks), encoding="utf-8")
    print(f"{len(doc)} páginas → {OUT}")


if __name__ == "__main__":
    main()
