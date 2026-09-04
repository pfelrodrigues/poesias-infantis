"""Contract tests: run the real CLI, Pandoc and image encoder."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from html.parser import HTMLParser
from pathlib import Path

import yaml
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "export_book.py"


class TextBlocks(HTMLParser):
    """Read the text readers actually see, preserving stanza and paragraph boundaries."""

    def __init__(self) -> None:
        super().__init__()
        self.blocks = []
        self.current = None
        self.images = []
        self.links = []
        self.stanzas = []
        self.current_is_stanza = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs = dict(attrs)
        if tag == "p" or (
            tag == "div" and "line-block" in attrs.get("class", "").split()
        ):
            self.current = []
            self.current_is_stanza = tag == "div"
        if tag == "br" and self.current is not None:
            self.current.append("\n")
        if tag == "img":
            self.images.append(attrs)
        if tag == "a":
            self.links.append(attrs.get("href"))

    def handle_data(self, data: str) -> None:
        if self.current is not None:
            self.current.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"p", "div"} and self.current is not None:
            value = "".join(self.current).strip()
            if value:
                self.blocks.append(re.sub(r"[ \t\r\f\v]+", " ", value))
                if self.current_is_stanza:
                    self.stanzas.append(value.replace("\n\n", "\n"))
            self.current = None


def read_blocks(html: str) -> TextBlocks:
    parser = TextBlocks()
    parser.feed(html)
    return parser


class ExportContract(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "other-book"
        self.output = self.root / "distribution"
        (self.source / "text").mkdir(parents=True)
        (self.source / "images").mkdir()
        Image.new("RGB", (64, 48), "wheat").save(self.source / "images" / "drawing.png")
        self.first = (
            "---\nid: first\ntitle: Primeiro capítulo\nstatus: proofed\n---\n"
            "# Primeiro capítulo\n\nUma historia d'outro tempo : sem modernização.\n\n"
            "![Casa junto ao rio.](../images/drawing.png)\n\n"
            "## Caminho\n\nO auctor voltou... «Cheguei!»\n\n"
            "[Continuar](second.md#fim)\n"
        )
        self.second = (
            "---\nid: second\ntitle: Segundo capítulo\nstatus: proofed\n---\n"
            "# Segundo capítulo\n\n## Fim\n\nA historia termina aqui.\n"
        )
        (self.source / "text" / "first.md").write_text(self.first)
        (self.source / "text" / "second.md").write_text(self.second)
        self.manifest = {
            "id": "small-prose",
            "version": "1.2.3",
            "language": "pt",
            "title": "Livro de prosa",
            "author": "Outro auctor",
            "year": 1901,
            "license": "CC0-1.0",
            "source_commit": "1" * 40,
            "policy": {
                "original_statuses": ["proofed"],
                "editorial_statuses": ["draft"],
                "editorial_pieces": [],
                "expected_original_count": 2,
            },
            "pieces": [
                {
                    "id": "first",
                    "file": "text/first.md",
                    "kind": "prose",
                    "original": True,
                },
                {
                    "id": "second",
                    "file": "text/second.md",
                    "kind": "prose",
                    "original": True,
                },
            ],
        }

    def run_export(self) -> subprocess.CompletedProcess[str]:
        (self.source / "book.yml").write_text(
            yaml.safe_dump(self.manifest, allow_unicode=True)
        )
        return subprocess.run(
            [
                sys.executable,
                str(CLI),
                "--source",
                str(self.source / "book.yml"),
                "--output",
                str(self.output),
            ],
            check=False,
            capture_output=True,
            text=True,
            cwd=self.root,
        )

    def assert_fails(self, phrase: str) -> None:
        result = self.run_export()
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn(phrase, result.stderr.lower())
        self.assertFalse(
            self.output.exists(),
            "An invalid source must not leave a partial distribution",
        )

    def test_exports_second_prose_book_without_book_specific_code(self) -> None:
        result = self.run_export()
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads((self.output / "book.json").read_text())
        self.assertEqual(manifest["id"], "small-prose")
        self.assertEqual(manifest["title"], "Livro de prosa")
        self.assertEqual([p["id"] for p in manifest["pieces"]], ["first", "second"])
        self.assertEqual(
            manifest["pieces"][0]["sections"], [{"id": "caminho", "title": "Caminho"}]
        )
        self.assertEqual(manifest["pieces"][0]["status"], "proofed")
        self.assertEqual(manifest["epub"], "small-prose.epub")
        html = (self.output / "chapters/first.html").read_text()
        self.assertNotIn("<h1", html)
        self.assertNotIn("style=", html)
        parsed = read_blocks(html)
        self.assertIn("Uma historia d'outro tempo : sem modernização.", parsed.blocks)
        self.assertIn("O auctor voltou... «Cheguei!»", parsed.blocks)
        self.assertEqual(parsed.links, ["book:second#fim"])
        self.assertEqual(parsed.images[0]["src"], "images/drawing.webp")
        self.assertEqual(parsed.images[0]["alt"], "Casa junto ao rio.")
        self.assertEqual(
            (parsed.images[0]["width"], parsed.images[0]["height"]), ("64", "48")
        )
        self.assertEqual(parsed.images[0]["loading"], "lazy")
        actual = {
            p.relative_to(self.output).as_posix(): hashlib.sha256(
                p.read_bytes()
            ).hexdigest()
            for p in self.output.rglob("*")
            if p.is_file() and p.name != "book.json"
        }
        self.assertEqual(manifest["files"], actual)
        self.assertIn(
            hashlib.sha256((self.output / "book.json").read_bytes()).hexdigest(),
            result.stdout,
        )
        self.assertEqual((self.source / "text/first.md").read_text(), self.first)
        with zipfile.ZipFile(self.output / manifest["epub"]) as epub:
            self.assertEqual(epub.read("mimetype"), b"application/epub+zip")
            self.assertEqual(epub.infolist()[0].filename, "mimetype")
            self.assertEqual(epub.infolist()[0].compress_type, zipfile.ZIP_STORED)
            chapters = [
                epub.read(name).decode()
                for name in epub.namelist()
                if re.search(r"/ch\d+\.xhtml$", name)
            ]
            self.assertEqual(len(chapters), 2)
            self.assertEqual(read_blocks(chapters[0]).blocks, parsed.blocks)
            nav = next(
                epub.read(n).decode()
                for n in epub.namelist()
                if n.endswith("/nav.xhtml")
            )
            self.assertIn("Caminho", nav)
            self.assertIn("Segundo capítulo", nav)
            for name in epub.namelist():
                if name.endswith((".xhtml", ".opf", ".ncx", ".xml")):
                    ET.fromstring(epub.read(name))
            self.assertNotIn("book:", "".join(chapters))

    def test_missing_piece_aborts(self) -> None:
        (self.source / "text/second.md").unlink()
        self.assert_fails("missing piece")

    def test_missing_referenced_image_aborts(self) -> None:
        (self.source / "images/drawing.png").unlink()
        self.assert_fails("missing image")

    def test_missing_cover_aborts(self) -> None:
        self.manifest["cover"] = {"file": "images/missing.png", "alt": "Capa"}
        self.assert_fails("missing image")

    def test_missing_policy_aborts(self) -> None:
        del self.manifest["policy"]
        self.assert_fails("policy")

    def test_unpermitted_status_aborts(self) -> None:
        path = self.source / "text/first.md"
        path.write_text(self.first.replace("status: proofed", "status: draft"))
        self.assert_fails("status")

    def test_removing_original_from_manifest_aborts(self) -> None:
        self.manifest["pieces"].pop()
        self.assert_fails("original count")

    def test_unpermitted_editorial_piece_aborts(self) -> None:
        self.manifest["pieces"][1]["original"] = False
        self.manifest["policy"]["expected_original_count"] = 1
        self.assert_fails("editorial")

    def test_changed_original_text_checksum_aborts(self) -> None:
        self.manifest["pieces"][0]["sha256"] = "0" * 64
        self.assert_fails("checksum")

    def test_broken_internal_link_aborts(self) -> None:
        path = self.source / "text/first.md"
        path.write_text(self.first.replace("second.md#fim", "second.md#unknown"))
        self.assert_fails("link")

    def test_path_escape_aborts(self) -> None:
        self.manifest["pieces"][0]["file"] = "../outside.md"
        (self.root / "outside.md").write_text(self.first)
        self.assert_fails("outside source")

    def test_missing_epub_stylesheet_aborts(self) -> None:
        self.manifest["epub_css"] = "css/missing.css"
        self.assert_fails("missing stylesheet")

    def test_publisher_must_be_text(self) -> None:
        self.manifest["publisher"] = {"unexpected": "mapping"}
        self.assert_fails("publisher")

    def test_original_translation_is_rejected(self) -> None:
        self.manifest["pieces"][0]["translations"] = {"en": "text/second.md"}
        self.assert_fails("translations of original")

    def test_legacy_fragments_are_prepared_without_redirect_code(self) -> None:
        self.manifest["legacy_fragments"] = True
        result = self.run_export()
        self.assertEqual(result.returncode, 0, result.stderr)
        path = self.output / "legacy-fragments.json"
        self.assertTrue(path.is_file(), "Export must prepare the legacy map")
        mapping = json.loads(path.read_text())
        self.assertEqual(mapping["fragments"]["primeiro-capítulo"], "book:first")
        self.assertEqual(mapping["fragments"]["caminho"], "book:first#caminho")
        self.assertEqual(
            sorted(p.suffix for p in self.output.iterdir() if p.is_file()),
            [".epub", ".json", ".json"],
        )

    def test_poem_stanzas_survive_both_formats(self) -> None:
        (self.source / "text/first.md").write_text(
            "---\nid: first\ntitle: Primeiro capítulo\nstatus: proofed\n---\n"
            "# Primeiro capítulo\n\n| D'esta historia... quem diria!\n| «A vida» -- assim dizia.\n\n"
            "| Annos, mezes, coração :\n| Não mudes a pontuação !\n"
        )
        result = self.run_export()
        self.assertEqual(result.returncode, 0, result.stderr)
        expected = [
            "D'esta historia... quem diria!\n«A vida» -- assim dizia.",
            "Annos, mezes, coração :\nNão mudes a pontuação !",
        ]
        web = read_blocks((self.output / "chapters/first.html").read_text()).blocks
        # HTML pretty-printing adds source line breaks after br; collapse only those pairs.
        self.assertEqual([b.replace("\n\n", "\n") for b in web], expected)
        with zipfile.ZipFile(self.output / "small-prose.epub") as epub:
            chapter = next(
                epub.read(n).decode()
                for n in epub.namelist()
                if n.endswith("ch001.xhtml")
            )
            self.assertEqual(read_blocks(chapter).blocks, web)

    def test_existing_output_is_immutable(self) -> None:
        self.output.mkdir()
        marker = self.output / "do-not-replace"
        marker.write_text("keep")
        result = self.run_export()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("already exists", result.stderr)
        self.assertEqual(marker.read_text(), "keep")

    def test_editorial_translation_has_status_and_does_not_translate_originals(
        self,
    ) -> None:
        self.manifest["pieces"][1]["original"] = False
        self.manifest["pieces"][1]["kind"] = "colophon"
        self.manifest["pieces"][1]["translations"] = {"en": "text/second.en.md"}
        self.manifest["policy"]["editorial_pieces"] = ["second"]
        self.manifest["policy"]["editorial_statuses"] = ["proofed", "draft"]
        self.manifest["policy"]["expected_original_count"] = 1
        (self.source / "text/second.en.md").write_text(
            "---\nid: second\ntitle: Colophon\nstatus: draft\n---\n# Colophon\n\nEditorial translation.\n"
        )
        result = self.run_export()
        self.assertEqual(result.returncode, 0, result.stderr)
        m = json.loads((self.output / "book.json").read_text())
        translation = m["pieces"][1]["translations"]["en"]
        self.assertEqual(translation["status"], "draft")
        self.assertIn(
            "Editorial translation.", (self.output / translation["html"]).read_text()
        )
        self.assertNotIn("translations", m["pieces"][0])


class OriginalEdition(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.output = Path(cls.temp.name) / "edition"
        result = subprocess.run(
            [
                sys.executable,
                str(CLI),
                "--source",
                str(ROOT / "source/book.yml"),
                "--output",
                str(cls.output),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode:
            raise AssertionError(result.stderr)
        cls.manifest = json.loads((cls.output / "book.json").read_text())

    def test_original_files_are_byte_identical_to_checkout_base(self) -> None:
        originals = [p for p in self.manifest["pieces"] if p["original"]]
        self.assertEqual(len(originals), 38)
        for piece in originals:
            with self.subTest(piece=piece["id"]):
                relative = f"source/text/{piece['id']}.md"
                baseline = subprocess.run(
                    ["git", "show", f"HEAD:{relative}"],
                    cwd=ROOT,
                    check=True,
                    capture_output=True,
                ).stdout
                actual = (ROOT / relative).read_bytes()
                self.assertEqual(actual, baseline)
                self.assertEqual(
                    hashlib.sha256(actual).hexdigest(), piece["source_sha256"]
                )

    def test_every_original_stanza_and_paragraph_matches_source_and_epub(self) -> None:
        with zipfile.ZipFile(self.output / self.manifest["epub"]) as epub:
            for index, piece in enumerate(self.manifest["pieces"], 1):
                if not piece["original"]:
                    continue
                with self.subTest(piece=piece["id"]):
                    raw = (ROOT / f"source/text/{piece['id']}.md").read_text()
                    body = re.sub(r"\A---\n.*?\n---\n", "", raw, flags=re.DOTALL)
                    web = read_blocks((self.output / piece["html"]).read_text())
                    chapter = epub.read(f"EPUB/text/ch{index:03}.xhtml").decode()
                    self.assertEqual(web.blocks, read_blocks(chapter).blocks)
                    source_stanzas = [
                        "\n".join(
                            line[2:] if line.startswith("| ") else line[1:]
                            for line in group.strip().splitlines()
                        )
                        for group in re.findall(
                            r"(?:^\|.*(?:\n|$))+", body, flags=re.MULTILINE
                        )
                    ]
                    self.assertEqual(web.stanzas, source_stanzas)
                    independent = subprocess.run(
                        [
                            "pandoc",
                            "--from=markdown-smart-implicit_figures",
                            "--to=html5",
                            "--wrap=none",
                        ],
                        input=body,
                        text=True,
                        capture_output=True,
                        check=True,
                    ).stdout
                    self.assertEqual(web.blocks, read_blocks(independent).blocks)

    def test_epub_toc_and_resources_resolve(self) -> None:
        from posixpath import dirname, join, normpath
        from urllib.parse import unquote, urlsplit

        with zipfile.ZipFile(self.output / self.manifest["epub"]) as epub:
            names = set(epub.namelist())
            roots = {
                name: ET.fromstring(epub.read(name))
                for name in names
                if name.endswith((".xhtml", ".opf", ".ncx", ".xml"))
            }
            ids = {
                name: {node.attrib["id"] for node in root.iter() if "id" in node.attrib}
                for name, root in roots.items()
            }
            for name, root in roots.items():
                for node in root.iter():
                    for key in ("href", "src"):
                        target = node.attrib.get(key, "")
                        url = urlsplit(target)
                        if not target or url.scheme or url.netloc:
                            continue
                        path = (
                            normpath(join(dirname(name), unquote(url.path)))
                            if url.path
                            else name
                        )
                        self.assertIn(path, names, (name, target))
                        if url.fragment:
                            self.assertIn(
                                unquote(url.fragment), ids[path], (name, target)
                            )
            nav = roots["EPUB/nav.xhtml"]
            self.assertGreaterEqual(
                len(list(nav.iter("{http://www.w3.org/1999/xhtml}a"))), 39
            )

    def test_legacy_make_aborts_before_replacing_output_when_piece_missing(
        self,
    ) -> None:
        # Copy the small source tree to test the legacy command without mutating this checkout.
        import shutil

        with tempfile.TemporaryDirectory() as temp:
            tree = Path(temp)
            shutil.copytree(ROOT / "scripts", tree / "scripts")
            (tree / "source/text").mkdir(parents=True)
            shutil.copy2(ROOT / "source/book.yml", tree / "source/book.yml")
            (tree / "site").mkdir()
            (tree / "site/index.html").write_text("previous release")
            result = subprocess.run(
                [sys.executable, str(tree / "scripts/build_book.py")],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual((tree / "site/index.html").read_text(), "previous release")
            self.assertFalse(
                (tree / "build/book.md").exists(),
                "Validate all source files before creating an incomplete manuscript",
            )


if __name__ == "__main__":
    unittest.main()
