"""Export an immutable, verified book package from a book.yml and its source files.

Markdown is parsed once with typography substitutions disabled. Both formats use
that same Pandoc AST; only image resources, heading IDs and link targets differ.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any, NotRequired, TypedDict
from urllib.parse import unquote, urlsplit

import yaml
from PIL import Image, ImageOps

PANDOC_VERSION = "3.7.0.2"
ROOT = Path(__file__).resolve().parents[1]
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FRONT = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)


class ImageRecord(TypedDict):
    src: str
    width: int
    height: int
    alt: NotRequired[str]


class ExportError(ValueError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def nodes(value: Any) -> Iterator[dict[str, Any]]:
    if isinstance(value, dict):
        if "t" in value:
            yield value
        for child in value.values():
            yield from nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from nodes(child)


def inline_text(value: Any) -> str:
    parts = []
    for node in nodes(value):
        if node["t"] in {"Str", "Code"}:
            parts.append(node["c"] if node["t"] == "Str" else node["c"][1])
        elif node["t"] in {"Space", "SoftBreak", "LineBreak"}:
            parts.append(" ")
    return "".join(parts)


def pandoc(
    content: str,
    *args: str,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> str:
    result = subprocess.run(
        ["pandoc", *args],
        check=False,
        input=content,
        text=True,
        capture_output=True,
        cwd=cwd,
        env=env,
    )
    if result.returncode:
        raise ExportError(f"Pandoc failed: {result.stderr.strip()}")
    if result.stderr.strip():
        raise ExportError(f"Pandoc warning: {result.stderr.strip()}")
    return result.stdout


class Book:
    def __init__(self, source: Path) -> None:
        self.manifest_path = source.resolve()
        self.root = self.manifest_path.parent
        self.used = {self.manifest_path}
        self.meta = yaml.safe_load(self.manifest_path.read_text(encoding="utf-8"))
        if not isinstance(self.meta, dict):
            raise ExportError("book.yml must contain a mapping")
        for field in ("id", "version", "title", "author", "language", "license"):
            if (
                not isinstance(self.meta.get(field), str)
                or not self.meta[field].strip()
            ):
                raise ExportError(f"Missing required metadata: {field}")
        for field in ("publisher", "place", "source_url", "repository_url"):
            if field in self.meta and not isinstance(self.meta[field], str):
                raise ExportError(f"Metadata {field} must be text")
        if "year" in self.meta and type(self.meta["year"]) is not int:
            raise ExportError("Metadata year must be an integer")
        self.css = (
            self.path(self.meta["epub_css"], "stylesheet")
            if self.meta.get("epub_css")
            else None
        )
        if not SLUG.fullmatch(self.meta["id"]):
            raise ExportError("Invalid book id")
        if not re.fullmatch(r"\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?", self.meta["version"]):
            raise ExportError("Invalid version; expected semantic version")
        self.policy = self.meta.get("policy")
        if not isinstance(self.policy, dict):
            raise ExportError("An explicit publication policy is required")
        for key in ("original_statuses", "editorial_statuses", "editorial_pieces"):
            if not isinstance(self.policy.get(key), list):
                raise ExportError(f"Missing policy.{key}")
        valid_statuses = {"draft", "collated", "proofed"}
        if not set(self.policy["original_statuses"]).issubset(
            valid_statuses
        ) or not set(self.policy["editorial_statuses"]).issubset(valid_statuses):
            raise ExportError("Unknown status in publication policy")
        specs = self.meta.get("pieces")
        if not isinstance(specs, list) or not specs:
            raise ExportError("At least one piece is required")
        self.pieces = []
        self.by_id = {}
        self.by_path = {}
        self.images: dict[Path, ImageRecord] = {}
        self.image_names = set()
        editorial_started = False
        for spec in specs:
            if not isinstance(spec, dict) or not SLUG.fullmatch(
                str(spec.get("id", ""))
            ):
                raise ExportError("Invalid piece id")
            if spec["id"] in self.by_id:
                raise ExportError(f"Duplicate piece: {spec['id']}")
            if type(spec.get("original")) is not bool or not spec.get("kind"):
                raise ExportError(f"Piece {spec['id']} needs original and kind")
            if spec["original"]:
                if editorial_started:
                    raise ExportError("All originals must precede editorial pieces")
                if spec.get("translations"):
                    raise ExportError(
                        "Translations of original historical text are forbidden"
                    )
            else:
                editorial_started = True
                if spec["id"] not in self.policy["editorial_pieces"]:
                    raise ExportError(f"Unpermitted editorial piece: {spec['id']}")
            path = self.path(spec.get("file", ""), "piece")
            if spec.get("sha256") and sha256(path) != spec["sha256"]:
                raise ExportError(f"Source checksum mismatch: {spec['id']}")
            piece = self.read_piece(path, spec)
            self.by_id[spec["id"]] = piece
            self.by_path[path] = piece
            self.pieces.append(piece)
        original_count = sum(p["spec"]["original"] for p in self.pieces)
        if self.policy.get("expected_original_count") != original_count:
            raise ExportError(
                "Original count differs from policy.expected_original_count"
            )
        self.cover = (
            self.image_spec(self.meta["cover"]) if self.meta.get("cover") else None
        )
        self.comparison = {
            key: self.image_spec(spec)
            for key, spec in self.meta.get("comparison", {}).items()
        }
        for piece in self.pieces:
            self.prepare_ast(piece)
            for language, file in piece["spec"].get("translations", {}).items():
                if not re.fullmatch(r"[a-z]{2,3}(?:-[A-Za-z]{2,4})?", language):
                    raise ExportError(f"Invalid translation language: {language}")
                translated = self.read_piece(self.path(file, "piece"), piece["spec"])
                self.prepare_ast(translated)
                piece["translations"][language] = translated

    def path(self, name: str, kind: str, relative: Path | None = None) -> Path:
        if not isinstance(name, str) or not name:
            raise ExportError(f"Missing {kind} file")
        path = ((relative or self.root) / name).resolve()
        if not path.is_relative_to(self.root):
            raise ExportError(f"Path outside source: {name}")
        if not path.is_file():
            raise ExportError(f"Missing {kind}: {name}")
        self.used.add(path)
        return path

    def read_piece(self, path: Path, spec: dict[str, Any]) -> dict[str, Any]:
        raw = path.read_text(encoding="utf-8")
        match = FRONT.match(raw)
        if not match:
            raise ExportError(f"Missing front matter: {path.name}")
        front = yaml.safe_load(match.group(1))
        if not isinstance(front, dict) or front.get("id") != spec["id"]:
            raise ExportError(f"Piece id mismatch: {path.name}")
        key = "original_statuses" if spec["original"] else "editorial_statuses"
        if front.get("status") not in self.policy[key]:
            raise ExportError(
                f"Unpermitted status {front.get('status')!r}: {path.name}"
            )
        ast = json.loads(
            pandoc(
                raw[match.end() :],
                "--from=markdown-smart-implicit_figures",
                "--to=json",
            )
        )
        blocks = ast["blocks"]
        if not blocks or blocks[0]["t"] != "Header" or blocks[0]["c"][0] != 1:
            raise ExportError(f"Piece must start with one H1: {path.name}")
        title = inline_text(blocks[0]["c"][2])
        if title != front.get("title"):
            raise ExportError(f"Title differs from front matter: {path.name}")
        headers = [n for n in nodes(ast) if n["t"] == "Header"]
        if sum(h["c"][0] == 1 for h in headers) != 1:
            raise ExportError(f"Piece must contain exactly one H1: {path.name}")
        header_ids = [h["c"][1][0] for h in headers[1:]]
        if len(set(header_ids)) != len(header_ids):
            raise ExportError(f"Duplicate section id: {path.name}")
        legacy_id = blocks[0]["c"][1][0]
        blocks[0]["c"][1][0] = spec["id"]
        return {
            "spec": spec,
            "path": path,
            "front": front,
            "ast": ast,
            "title": title,
            "sections": [
                {"id": h["c"][1][0], "title": inline_text(h["c"][2])}
                for h in headers
                if h["c"][0] == 2
            ],
            "header_ids": set(header_ids),
            "legacy_id": legacy_id,
            "translations": {},
        }

    def image(self, path: Path, name: str | None = None) -> ImageRecord:
        if path in self.images:
            return self.images[path]
        name = name or path.stem
        if not SLUG.fullmatch(name) or name in self.image_names:
            raise ExportError(f"Invalid or colliding image name: {name}")
        self.image_names.add(name)
        with Image.open(path) as image:
            image = ImageOps.exif_transpose(image)
            max_width = self.meta.get("web_images", {}).get("max_width", 1400)
            if not isinstance(max_width, int) or not 100 <= max_width <= 4000:
                raise ExportError("web_images.max_width must be 100..4000")
            scale = min(1, max_width / image.width)
            width, height = round(image.width * scale), round(image.height * scale)
        record = {"src": f"images/{name}.webp", "width": width, "height": height}
        self.images[path] = record
        return record

    def image_spec(self, spec: dict[str, Any]) -> ImageRecord:
        if (
            not isinstance(spec, dict)
            or not isinstance(spec.get("alt"), str)
            or not spec["alt"].strip()
        ):
            raise ExportError("Declared image requires meaningful alt text")
        record = self.image(self.path(spec.get("file", ""), "image"), spec.get("name"))
        return {**record, "alt": spec["alt"]}

    def prepare_ast(self, piece: dict[str, Any]) -> None:
        for node in nodes(piece["ast"]):
            kind = node["t"]
            if kind in {"RawBlock", "RawInline"}:
                raise ExportError(f"Raw markup is not allowed: {piece['path'].name}")
            if kind == "Image":
                attrs, caption, target = node["c"]
                parsed = urlsplit(target[0])
                if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment:
                    raise ExportError(f"Images must be local source files: {target[0]}")
                path = self.path(unquote(parsed.path), "image", piece["path"].parent)
                record = self.image(path)
                alt = dict(attrs[2]).get("alt", inline_text(caption)).strip()
                if not alt:
                    raise ExportError(
                        f"Image requires meaningful alt text: {path.name}"
                    )
                node["c"] = [
                    [
                        attrs[0],
                        attrs[1],
                        [
                            ["width", str(record["width"])],
                            ["height", str(record["height"])],
                            ["loading", "lazy"],
                        ],
                    ],
                    [{"t": "Str", "c": alt}],
                    [record["src"], target[1]],
                ]
            elif kind == "Link":
                node["c"][2][0] = self.link(node["c"][2][0], piece)
            if kind in {"Header", "CodeBlock", "Div", "Span", "Code", "Link"}:
                attr = node["c"][1] if kind == "Header" else node["c"][0]
                if any(
                    key.lower().startswith("on") or key.lower() == "style"
                    for key, _ in attr[2]
                ):
                    raise ExportError("Inline styles and event handlers are forbidden")

    def link(self, target: str, piece: dict[str, Any]) -> str:
        url = urlsplit(target)
        if url.scheme in {"http", "https", "mailto"}:
            return target
        if url.scheme == "book":
            dest = self.by_id.get(url.path)
        elif not url.scheme and not url.netloc:
            if not url.path:
                dest = piece
            else:
                dest = self.by_path.get(
                    (piece["path"].parent / unquote(url.path)).resolve()
                )
        else:
            dest = None
        if not dest or url.query:
            raise ExportError(f"Unknown local link: {target}")
        fragment = unquote(url.fragment)
        if (
            fragment
            and fragment != dest["spec"]["id"]
            and fragment not in dest["header_ids"]
        ):
            raise ExportError(f"Broken section link: {target}")
        return f"book:{dest['spec']['id']}" + (
            f"#{fragment}" if fragment and fragment != dest["spec"]["id"] else ""
        )

    def write_images(self, output: Path, resources: Path) -> None:
        quality = self.meta.get("web_images", {}).get("quality", 88)
        if not isinstance(quality, int) or not 1 <= quality <= 100:
            raise ExportError("web_images.quality must be 1..100")
        (output / "images").mkdir()
        (resources / "images").mkdir(parents=True)
        for source, record in self.images.items():
            with Image.open(source) as original:
                image = ImageOps.exif_transpose(original).convert("RGB")
                image = image.resize(
                    (record["width"], record["height"]), Image.Resampling.LANCZOS
                )
                image.save(output / record["src"], "WEBP", quality=quality, method=6)
                # JPEG is a core EPUB media type; WebP is reserved for the website.
                image.save(
                    resources / record["src"].replace(".webp", ".jpg"),
                    "JPEG",
                    quality=85,
                    optimize=True,
                )

    def fragment(self, piece: dict[str, Any]) -> str:
        ast = copy.deepcopy(piece["ast"])
        ast["blocks"] = ast["blocks"][1:]
        return pandoc(json.dumps(ast), "--from=json", "--to=html5", "--wrap=none")

    def epub_ast(self) -> dict[str, Any]:
        book = {
            "pandoc-api-version": self.pieces[0]["ast"]["pandoc-api-version"],
            "meta": {},
            "blocks": [],
        }
        for piece in self.pieces:
            ast = copy.deepcopy(piece["ast"])
            for node in nodes(ast):
                if node["t"] == "Header" and node["c"][0] > 1:
                    node["c"][1][0] = piece["spec"]["id"] + "--" + node["c"][1][0]
                elif node["t"] == "Image":
                    node["c"][2][0] = node["c"][2][0].replace(".webp", ".jpg")
                    node["c"][0][2] = [a for a in node["c"][0][2] if a[0] != "loading"]
                elif node["t"] == "Link" and node["c"][2][0].startswith("book:"):
                    target = urlsplit(node["c"][2][0])
                    node["c"][2][0] = (
                        "#"
                        + target.path
                        + ("--" + target.fragment if target.fragment else "")
                    )
            book["blocks"].extend(ast["blocks"])
        return book

    def provenance(self) -> dict[str, Any]:
        commit = self.meta.get("source_commit")
        git = subprocess.run(
            ["git", "-C", str(self.root), "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
        )
        if commit is None and git.returncode == 0:
            commit = git.stdout.strip()
        if not isinstance(commit, str) or not re.fullmatch("[0-9a-f]{40}", commit):
            raise ExportError(
                "Provide source_commit (40 lowercase hex) when source is outside Git"
            )
        dirty = False
        if git.returncode == 0:
            status = subprocess.run(
                ["git", "-C", str(self.root), "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=True,
            )
            dirty = bool(status.stdout.strip())
        entries = {
            p.relative_to(self.root).as_posix(): sha256(p) for p in sorted(self.used)
        }
        digest = hashlib.sha256(
            json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return {"source_commit": commit, "source_dirty": dirty, "source_sha256": digest}

    def export(self, output: Path) -> None:
        manifest = {
            "schema": 1,
            **{
                k: self.meta[k]
                for k in (
                    "id",
                    "version",
                    "language",
                    "title",
                    "author",
                    "year",
                    "publisher",
                    "place",
                    "license",
                    "source_url",
                    "repository_url",
                )
                if k in self.meta
            },
            **self.provenance(),
        }
        manifest["policy"] = self.policy
        manifest["generator"] = {"pandoc": PANDOC_VERSION}
        manifest["epub"] = self.meta["id"] + ".epub"
        manifest["pieces"] = []
        if self.cover:
            manifest["cover"] = self.cover
        if self.comparison:
            manifest["comparison"] = self.comparison
        if self.meta.get("legacy_fragments"):
            fragments = {}
            for piece in self.pieces:
                for old_id, target in [
                    (piece["legacy_id"], f"book:{piece['spec']['id']}")
                ] + [
                    (section, f"book:{piece['spec']['id']}#{section}")
                    for section in sorted(piece["header_ids"])
                ]:
                    if old_id in fragments:
                        raise ExportError(f"Ambiguous legacy fragment: {old_id}")
                    fragments[old_id] = target
            manifest["legacy_fragments"] = "legacy-fragments.json"
            (output / manifest["legacy_fragments"]).write_text(
                json.dumps(
                    {"schema": 1, "book_id": self.meta["id"], "fragments": fragments},
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
        (output / "chapters").mkdir()
        for piece in self.pieces:
            html_path = f"chapters/{piece['spec']['id']}.html"
            (output / html_path).write_text(self.fragment(piece), encoding="utf-8")
            item = {
                "id": piece["spec"]["id"],
                "title": piece["title"],
                "kind": piece["spec"]["kind"],
                "original": piece["spec"]["original"],
                "status": piece["front"]["status"],
                "html": html_path,
                "sections": piece["sections"],
                "source_sha256": sha256(piece["path"]),
            }
            if "page" in piece["front"]:
                item["page"] = piece["front"]["page"]
            if piece["translations"]:
                item["translations"] = {}
                for language, translated in piece["translations"].items():
                    path = f"chapters/{item['id']}.{language}.html"
                    (output / path).write_text(
                        self.fragment(translated), encoding="utf-8"
                    )
                    item["translations"][language] = {
                        "html": path,
                        "title": translated["title"],
                        "status": translated["front"]["status"],
                        "sections": translated["sections"],
                    }
            manifest["pieces"].append(item)
        with tempfile.TemporaryDirectory(prefix="book-epub-") as temp:
            resources = Path(temp)
            self.write_images(output, resources)
            meta = {
                "title": self.meta["title"],
                "author": self.meta["author"],
                "lang": self.meta["language"],
                "identifier": f"urn:book:{self.meta['id']}:{self.meta['version']}:{manifest['source_sha256']}",
                "date": str(self.meta.get("year", "")),
                "rights": self.meta["license"],
            }
            metadata = resources / "metadata.json"
            metadata.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
            args = [
                "--from=json",
                "--to=epub3",
                "--toc",
                "--toc-depth=2",
                "--split-level=1",
                "--metadata-file=" + str(metadata),
                "--resource-path=" + str(resources),
                "--output=" + str(output / manifest["epub"]),
            ]
            if self.cover:
                args.append(
                    "--epub-cover-image="
                    + str(resources / self.cover["src"].replace(".webp", ".jpg"))
                )
            if self.css:
                args.append("--css=" + str(self.css))
            env = {**os.environ, "SOURCE_DATE_EPOCH": "0"}
            pandoc(json.dumps(self.epub_ast()), *args, cwd=resources, env=env)
        manifest["files"] = {
            p.relative_to(output).as_posix(): sha256(p)
            for p in sorted(output.rglob("*"))
            if p.is_file()
        }
        (output / "book.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=ROOT / "source/book.yml",
        help="Source manifest, or its directory",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="New immutable distribution directory; must not exist",
    )
    args = parser.parse_args(argv)
    try:
        output = args.output.resolve()
        if output.exists():
            raise ExportError(f"Output already exists: {output}")
        source = args.source / "book.yml" if args.source.is_dir() else args.source
        if not source.is_file():
            raise ExportError(f"Missing source manifest: {source}")
        version = subprocess.run(
            ["pandoc", "--version"], capture_output=True, text=True, check=True
        ).stdout.splitlines()[0]
        if version != f"pandoc {PANDOC_VERSION}":
            raise ExportError(f"Expected pandoc {PANDOC_VERSION}; found {version}")
        book = Book(source)
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix=".book-export-", dir=output.parent
        ) as temp:
            staging = Path(temp) / "package"
            staging.mkdir()
            book.export(staging)
            if output.exists():
                raise ExportError(f"Output already exists: {output}")
            staging.rename(output)
        print(f"Directory: {output}\nSHA-256: {sha256(output / 'book.json')}")
        return 0
    except (
        ExportError,
        OSError,
        yaml.YAMLError,
        subprocess.CalledProcessError,
    ) as error:
        print(f"Export failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
