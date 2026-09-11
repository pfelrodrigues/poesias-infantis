"""PDF A5 da edição, gerado no mesmo export do EPUB."""

from __future__ import annotations

import html
import tempfile
from pathlib import Path

import pymupdf

PAPER = (0.953, 0.929, 0.875)
MUTED = (0.42, 0.38, 0.33)
A5 = pymupdf.paper_rect("A5")
WHERE = A5 + (48, 52, -48, -58)


def _inlines(items: list) -> str:
    parts: list[str] = []
    for item in items:
        kind = item["t"]
        if kind == "Str":
            parts.append(html.escape(item["c"]))
        elif kind in {"Space", "SoftBreak"}:
            parts.append(" ")
        elif kind == "LineBreak":
            parts.append("<br>")
        elif kind == "Emph":
            parts.append(f"<i>{_inlines(item['c'])}</i>")
        elif kind == "Strong":
            parts.append(f"<b>{_inlines(item['c'])}</b>")
        elif kind == "Code":
            text = item["c"][1] if isinstance(item["c"], (list, tuple)) else item["c"]
            parts.append(f"<code>{html.escape(text)}</code>")
        elif kind == "Quoted":
            parts.append(_inlines(item["c"][1]))
        elif kind == "Link":
            parts.append(_inlines(item["c"][1]))
        elif kind == "Image":
            continue
        elif kind == "Note":
            continue
        else:
            child = item.get("c")
            if isinstance(child, list) and child and isinstance(child[0], dict):
                parts.append(_inlines(child))
            elif isinstance(child, list) and len(child) > 1 and isinstance(child[1], list):
                parts.append(_inlines(child[1]))
    return "".join(parts)


def _text_blocks(piece: dict) -> list[str]:
    blocks = []
    for node in piece["ast"]["blocks"][1:]:
        if node["t"] == "Para":
            text = _inlines(node["c"])
            if text.strip():
                blocks.append(f"<p>{text}</p>")
        elif node["t"] == "Header":
            name = _inlines(node["c"][2]).strip()
            if name:
                blocks.append(f"<h2>{name}</h2>")
    return blocks


def _first_image(piece: dict, book) -> Path | None:
    from export_book import nodes

    for node in nodes(piece["ast"]):
        if node["t"] != "Image":
            continue
        stem = Path(node["c"][2][0]).stem
        for path in book.images:
            if path.stem == stem:
                return path
    return None


def write_pdf(book, destination: Path) -> None:
    parts = [
        "<article class='cover'>",
        f"<h1 class='book-title'>{html.escape(book.meta['title'])}</h1>",
        f"<p class='author'>{html.escape(book.meta['author'])}</p>",
        f"<p class='note'>{html.escape(book.meta['license'])}</p>",
        "</article>",
        "<nav class='toc'><h1>Índice</h1><ul>",
    ]
    archive = pymupdf.Archive()
    added_dirs: set[str] = set()

    def add_dir(path: Path) -> None:
        parent = str(path.parent)
        if parent not in added_dirs:
            archive.add(parent)
            added_dirs.add(parent)

    if book.cover:
        for path, record in book.images.items():
            if record.get("src") == book.cover["src"]:
                add_dir(path)
                parts.insert(
                    1,
                    f"<p class='cover-image'><img src='{html.escape(path.name)}' alt=''></p>",
                )
                break
    for piece in book.pieces:
        parts.append(f"<li>{html.escape(piece['title'])}</li>")
    parts.append("</ul></nav>")
    for piece in book.pieces:
        img = _first_image(piece, book)
        img_html = ""
        if img is not None:
            add_dir(img)
            img_html = (
                f"<p class='figure'><img src='{html.escape(img.name)}' alt=''></p>"
            )
        body = "\n".join(_text_blocks(piece))
        klass = "chapter" if piece["spec"]["original"] else "chapter colophon"
        parts.append(
            f"<section class='{klass}'>"
            f"<h1>{html.escape(piece['title'])}</h1>"
            f"{img_html}{body}</section>"
        )
    css = """
    body { font-family: serif; color: #302B23; }
    h1 { font-size: 13pt; text-align: center; margin: 0 0 10pt; }
    h2 { font-size: 11pt; text-align: center; margin: 12pt 0 6pt; }
    p { font-size: 10.2pt; line-height: 1.4; text-align: justify; margin: 0 0 7pt; }
    code { font-size: 9pt; }
    .cover { text-align: center; page-break-after: always; }
    .book-title { font-size: 22pt; margin: 10pt 0 8pt; padding-bottom: 8pt;
                  border-bottom: 0.4pt solid #966019; }
    .author { font-size: 12pt; color: #6B6255; text-align: center; margin: 0 0 6pt; }
    .note { font-size: 9pt; color: #6B6255; text-align: center; }
    .cover-image { text-align: center; margin: 4pt 0 10pt; }
    .cover-image img { width: 72mm; height: auto; }
    .toc { page-break-after: always; }
    .toc ul { list-style: none; padding: 0; margin: 0; font-size: 9pt; line-height: 1.45; }
    .toc li { margin: 0 0 2pt; text-align: left; }
    .chapter { page-break-before: always; }
    .figure { text-align: center; margin: 0 0 10pt; }
    .figure img { width: 48mm; height: auto; }
    """
    html_doc = "<html><body>" + "\n".join(parts) + "</body></html>"
    story = pymupdf.Story(html_doc, user_css=css, archive=archive)

    def rectfn(_rect_num, _filled):
        return A5, WHERE, None

    with tempfile.TemporaryDirectory(prefix="book-pdf-") as temp:
        draft = Path(temp) / "draft.pdf"
        writer = pymupdf.DocumentWriter(str(draft))
        story.write(writer, rectfn)
        writer.close()
        doc = pymupdf.open(draft)
        doc.set_metadata(
            {
                "title": book.meta["title"],
                "author": book.meta["author"],
                "creator": "books",
            }
        )
        for page in doc:
            page.draw_rect(page.rect, color=None, fill=PAPER, overlay=False)
            if page.number == 0:
                continue
            page.insert_textbox(
                pymupdf.Rect(48, A5.height - 42, A5.width - 48, A5.height - 22),
                str(page.number + 1),
                fontsize=8,
                fontname="tiro",
                color=MUTED,
                align=pymupdf.TEXT_ALIGN_CENTER,
            )
        destination.parent.mkdir(parents=True, exist_ok=True)
        doc.save(destination, deflate=True, garbage=4)
        doc.close()
