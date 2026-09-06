"""Build every work and the bilingual library in this repository only."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import yaml
from export_book import FRONT, PANDOC_VERSION, Book, ExportError, sha256

ROOT = Path(__file__).resolve().parents[1]


def presentation(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ExportError(f"Missing presentation: {path}")
    text = path.read_text(encoding="utf-8")
    match = FRONT.match(text)
    metadata = yaml.safe_load(match[1]) if match else None
    if not isinstance(metadata, dict) or not metadata.get("description"):
        raise ExportError(f"Presentation requires front matter and description: {path}")
    return {"metadata": metadata, "body": text[match.end() :]}


def build_library(root: Path = ROOT) -> None:
    root = root.resolve()
    web = root / "web"
    manifests = sorted((root / "books").glob("*/book.yml"))
    if not manifests:
        raise ExportError("No books/*/book.yml found")
    books = [Book(path) for path in manifests]
    seen: set[str] = set()
    pages = {}
    for book in books:
        book_id = book.meta["id"]
        if book_id in seen or book.root.name != book_id:
            raise ExportError(
                f"Duplicate book or directory does not match id: {book_id}"
            )
        seen.add(book_id)
        pages[book_id] = {
            lang: presentation(book.root / f"presentation.{lang}.md")
            for lang in ("pt", "en")
        }
    version = subprocess.check_output(["pandoc", "--version"], text=True).splitlines()[
        0
    ]
    if version != f"pandoc {PANDOC_VERSION}":
        raise ExportError(f"Expected pandoc {PANDOC_VERSION}; found {version}")
    # Source, policy and both presentations are validated before any generated output changes.
    with tempfile.TemporaryDirectory(prefix=".library-", dir=root) as temp:
        stage = Path(temp)
        editions = stage / "editions"
        entries = []
        for book in books:
            book_id, version = book.meta["id"], book.meta["version"]
            output = editions / book_id / version
            output.mkdir(parents=True)
            book.export(output)
            entries.append(
                {
                    "id": book_id,
                    "version": version,
                    "directory": f".editions/{book_id}/{version}",
                    "sha256": sha256(output / "book.json"),
                    "presentation": pages[book_id],
                }
            )
        shutil.rmtree(web / ".editions", ignore_errors=True)
        editions.rename(web / ".editions")
        (web / "data").mkdir(exist_ok=True)
        (web / "data/books.lock.json").write_text(
            json.dumps({"schema": 1, "books": entries}, ensure_ascii=False, indent=2)
            + "\n",
            encoding="utf-8",
        )
        subprocess.run(["node", str(web / "scripts/import-books.mjs")], check=True)
        output_site = stage / "site"
        subprocess.run(
            [
                "hugo",
                "--source",
                str(web),
                "--destination",
                str(output_site),
                "--cleanDestinationDir",
                "--printPathWarnings",
                "--panicOnWarning",
            ],
            check=True,
        )
        # The hosting origin is an implementation detail. Direct visitors go to the public library.
        (output_site / "index.html").write_text(
            '<!doctype html><html lang="pt-BR"><meta charset="utf-8">'
            '<title>Livros</title><link rel="canonical" href="https://pfelrodrigues.com.br/books/">'
            '<meta http-equiv="refresh" content="0;url=https://pfelrodrigues.com.br/books/">'
            '<a href="https://pfelrodrigues.com.br/books/">Livros</a></html>\n',
            encoding="utf-8",
        )
        (output_site / ".nojekyll").touch()
        subprocess.run(
            ["node", str(web / "scripts/verify-site.mjs"), str(output_site)], check=True
        )
        # Keep the last publication intact if conversion, templates or link verification fail.
        previous = stage / "previous-site"
        if (root / "site").exists():
            (root / "site").rename(previous)
        try:
            output_site.rename(root / "site")
        except OSError:
            if previous.exists():
                previous.rename(root / "site")
            raise
    print(f"Built {len(books)} book(s): {root / 'site'}")


if __name__ == "__main__":
    build_library()
