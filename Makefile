.PHONY: all extract crop html epub book export test clean

SOURCE ?= source/book.yml
OUTPUT ?= build/distribution

all: book

extract:
	test -f source/images/pages/p001.png || uv run python scripts/extract_pages.py

crop: extract
	uv run python scripts/crop_headers.py

book:
	uv run --locked python scripts/build_book.py

export:
	uv run --locked python scripts/export_book.py --source "$(SOURCE)" --output "$(OUTPUT)"

test:
	uv run --locked python -m unittest discover -s tests -v

html: book
epub: book

clean:
	rm -rf build site
