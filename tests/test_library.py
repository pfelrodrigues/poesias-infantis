"""Build a collection with two unrelated works and no personal-site checkout."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_library import build_library


class LibraryBuild(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(
            ROOT / "web",
            self.root / "web",
            ignore=shutil.ignore_patterns(
                ".generated*", ".editions", "resources", "books.lock.json"
            ),
        )
        for book_id, language in (("first-book", "pt"), ("second-book", "es")):
            book = self.root / "books" / book_id
            (book / "text").mkdir(parents=True)
            (book / "text/opening.md").write_text(
                "---\nid: opening\ntitle: Abertura\nstatus: proofed\n---\n"
                f"# Abertura\n\nOriginal {book_id}.\n",
                encoding="utf-8",
            )
            (book / "book.yml").write_text(
                yaml.safe_dump(
                    {
                        "id": book_id,
                        "version": "1.0.0",
                        "title": book_id,
                        "author": "Autor",
                        "language": language,
                        "license": "CC0-1.0",
                        "source_commit": "1" * 40,
                        "policy": {
                            "original_statuses": ["proofed"],
                            "editorial_statuses": [],
                            "editorial_pieces": [],
                            "expected_original_count": 1,
                        },
                        "pieces": [
                            {
                                "id": "opening",
                                "file": "text/opening.md",
                                "original": True,
                                "kind": "prose",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            for lang in ("pt", "en"):
                (book / f"presentation.{lang}.md").write_text(
                    f"---\ndescription: About {book_id}\nblurb: Book {book_id}\n---\n"
                    f"Presentation {book_id} {lang}.\n",
                    encoding="utf-8",
                )

    def test_builds_two_books_and_both_interfaces_under_public_domain_paths(
        self,
    ) -> None:
        build_library(self.root)
        site = self.root / "site"
        for book_id, language in (("first-book", "pt"), ("second-book", "es")):
            for prefix, reader in (("", "ler"), ("en/", "read")):
                catalog = (site / prefix / "books/index.html").read_text()
                self.assertIn(book_id, catalog)
                presentation = (
                    site / prefix / "books" / book_id / "index.html"
                ).read_text()
                self.assertIn(f"Presentation {book_id}", presentation)
                chapter = (
                    site / prefix / "books" / book_id / reader / "opening/index.html"
                ).read_text()
                self.assertIn(f"Original {book_id}.", chapter)
                self.assertIn(f'id="reading-content" lang="{language}"', chapter)
                self.assertIn(
                    f"https://pfelrodrigues.com.br/{prefix}books/{book_id}/{reader}/opening/",
                    chapter,
                )
                self.assertNotIn("github.io", chapter)
            self.assertTrue(
                (
                    site / "books/assets" / book_id / "1.0.0" / f"{book_id}.epub"
                ).is_file()
            )
        manifest = json.loads((self.root / "web/data/books.lock.json").read_text())
        self.assertEqual(len(manifest["books"]), 2)
        self.assertFalse((site / "fonts").exists())
        self.assertEqual(len(list((site / "books/ui/fonts").glob("*.woff2"))), 3)

    def test_invalid_second_book_preserves_previous_site(self) -> None:
        (self.root / "site").mkdir()
        (self.root / "site/index.html").write_text("previous publication")
        (self.root / "books/second-book/text/opening.md").unlink()
        with self.assertRaises(ValueError):
            build_library(self.root)
        self.assertEqual(
            (self.root / "site/index.html").read_text(), "previous publication"
        )

    def test_missing_english_presentation_stops_publication(self) -> None:
        (self.root / "books/second-book/presentation.en.md").unlink()
        with self.assertRaisesRegex(ValueError, "presentation.en.md"):
            build_library(self.root)

    def test_editorial_notes_keep_their_own_titles_and_translated_sections(
        self,
    ) -> None:
        book = self.root / "books/second-book"
        manifest = yaml.safe_load((book / "book.yml").read_text())
        manifest["language"] = "pt"
        manifest["policy"]["editorial_statuses"] = ["proofed"]
        manifest["policy"]["editorial_pieces"] = ["notes"]
        manifest["pieces"].append(
            {
                "id": "notes",
                "file": "text/notes.md",
                "kind": "prose",
                "original": False,
                "translations": {"en": "text/notes.en.md"},
            }
        )
        (book / "book.yml").write_text(yaml.safe_dump(manifest))
        for suffix, title, section in (
            ("", "Notas editoriais", "Contexto"),
            (".en", "Editorial notes", "Context"),
        ):
            (book / f"text/notes{suffix}.md").write_text(
                f"---\nid: notes\ntitle: {title}\nstatus: proofed\n---\n"
                f"# {title}\n\n## {section}\n\nUma nota.\n",
                encoding="utf-8",
            )
        build_library(self.root)
        for prefix, reader, title, section in (
            ("", "ler", "Notas editoriais", "contexto"),
            ("en/", "read", "Editorial notes", "context"),
        ):
            path = self.root / "site" / prefix / "books/second-book"
            contents = (path / "index.html").read_text()
            chapter = (path / reader / "opening/index.html").read_text()
            self.assertIn(title, contents)
            self.assertIn(title, chapter)
            self.assertIn(f"/notes/#{section}", contents)
            self.assertNotIn("Colophon", chapter)
            self.assertNotIn("Colofão", chapter)


if __name__ == "__main__":
    unittest.main()
