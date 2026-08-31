"""Monta o Markdown do livro e chama o pandoc (HTML + EPUB)."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pieces import PIECES

ROOT = Path(__file__).resolve().parents[1]
TEXT = ROOT / "source" / "text"
RESTORED = ROOT / "source" / "images" / "restored"
BUILD = ROOT / "build"
SITE = ROOT / "site"
CSS = ROOT / "source" / "css" / "book.css"
TEMPLATE = ROOT / "source" / "templates" / "html.html"

FRONT_RE = re.compile(r"^---\n.*?\n---\n", re.S)


def body_of(md: Path) -> str:
    raw = md.read_text(encoding="utf-8")
    return FRONT_RE.sub("", raw).strip() + "\n"


def assemble() -> tuple[str, list[Path]]:
    missing: list[str] = []
    images: list[Path] = []
    parts: list[str] = []
    capa = RESTORED / "capa.png"
    if capa.exists():
        images.append(capa)
        parts.append(
            '![](capa.png){alt="Capa da edição de 1904: palmeiras, rapazes lendo, '
            'litografia colorida assinada HM."}\n'
        )
    for piece in PIECES:
        md = TEXT / f"{piece['id']}.md"
        if not md.exists():
            missing.append(piece["id"])
            continue
        fig = RESTORED / f"{piece['id']}.png"
        block = body_of(md)
        if fig.exists() and f"]({fig.name})" not in block and f"](../images/restored/{fig.name})" not in block:
            # A imagem já entra pelo markdown da peça, se houver.
            pass
        if fig.exists():
            images.append(fig)
        parts.append(block)
    colophon = TEXT / "colofao.md"
    if colophon.exists():
        parts.append(body_of(colophon))
    if missing:
        print("faltando:", ", ".join(missing))
    return "\n\n".join(parts) + "\n", images


def rewrite_image_paths(md: str) -> str:
    md = md.replace("../images/restored/", "")
    md = md.replace("images/", "")
    return md


def run_pandoc(src: Path, fmt: str, extra: list[str], out: Path) -> None:
    cmd = [
        "pandoc",
        str(src),
        "--from",
        "markdown-smart",
        "--to",
        fmt,
        "--css",
        str(CSS) if fmt == "epub3" else "book.css",
        "--resource-path",
        str(BUILD),
        "--metadata",
        "title=Poesias infantis",
        "--metadata",
        "author=Olavo Bilac",
        "--metadata",
        "lang=pt",
        "--toc",
        "--toc-depth=1",
        "--output",
        str(out),
        *extra,
    ]
    subprocess.run(cmd, check=True)


def main() -> None:
    BUILD.mkdir(parents=True, exist_ok=True)
    SITE.mkdir(parents=True, exist_ok=True)
    text, images = assemble()
    text = rewrite_image_paths(text)
    book = BUILD / "book.md"
    book.write_text(text, encoding="utf-8")
    if RESTORED.exists():
        for img in RESTORED.glob("*.png"):
            shutil.copy2(img, BUILD / img.name)
            shutil.copy2(img, SITE / img.name)
    else:
        for img in images:
            shutil.copy2(img, BUILD / img.name)
            shutil.copy2(img, SITE / img.name)
    shutil.copy2(CSS, SITE / "book.css")
    (SITE / ".nojekyll").touch()
    capa = BUILD / "capa.png"
    html_extra = [
        "--standalone",
        "--template",
        str(TEMPLATE),
    ]
    epub_extra: list[str] = []
    if capa.exists():
        epub_extra += ["--epub-cover-image", str(capa)]
    run_pandoc(book, "html5", html_extra, SITE / "index.html")
    run_pandoc(book, "epub3", epub_extra, BUILD / "poesias-infantis.epub")
    print(f"HTML {SITE / 'index.html'}")
    print(f"EPUB {BUILD / 'poesias-infantis.epub'}")


if __name__ == "__main__":
    main()
