.PHONY: all extract crop html epub book clean

all: book

extract:
	test -f source/images/pages/p001.png || uv run python scripts/extract_pages.py

crop: extract
	uv run python scripts/crop_headers.py

book:
	uv run python scripts/build_book.py

html: book
epub: book

clean:
	rm -rf build site
