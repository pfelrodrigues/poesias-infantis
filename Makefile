.PHONY: all extract crop html epub book export test clean

BOOK ?= poesias-infantis
SOURCE ?= books/$(BOOK)/book.yml
OUTPUT ?= build/distribution

all: book

extract:
	test -f books/$(BOOK)/images/pages/p001.png || uv run --locked python books/$(BOOK)/tools/extract_pages.py

crop: extract
	uv run --locked python books/$(BOOK)/tools/crop_headers.py

book:
	uv run --locked python scripts/build_library.py

export:
	uv run --locked python scripts/export_book.py --source "$(SOURCE)" --output "$(OUTPUT)"

test:
	uv run --locked python -m unittest discover -s tests -v
	node --test web/tests/*.test.mjs

html: book
epub: book

clean:
	rm -rf build site web/.editions web/.generated web/resources web/data/books.lock.json
