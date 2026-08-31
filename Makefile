PANDOC ?= pandoc
BUILD := build
SITE := site
TEXT := source/text/a-avo.md
CSS := source/css/book.css
TEMPLATE := source/templates/html.html
TITLE := Poesias infantis
AUTHOR := Olavo Bilac
PAGE := source/images/pages/p009.png
RESTORED := source/images/restored/avo-cabecalho.png

.PHONY: all html epub extract restore clean

all: html epub

$(PAGE):
	uv run python scripts/extract_pages.py

$(RESTORED): $(PAGE)
	uv run python scripts/restore_pilot.py

extract: $(PAGE)

restore: $(RESTORED)

html: $(RESTORED)
	mkdir -p $(SITE)/images
	cp $(RESTORED) $(SITE)/images/
	$(PANDOC) $(TEXT) \
		--from markdown-smart \
		--to html5 \
		--standalone \
		--template $(TEMPLATE) \
		--css=book.css \
		--resource-path=source/text \
		--metadata title="$(TITLE)" \
		--metadata author="$(AUTHOR)" \
		--metadata lang=pt \
		--output $(SITE)/index.html
	cp $(CSS) $(SITE)/book.css
	sed -i.bak 's|src="../images/restored/|src="images/|' $(SITE)/index.html && rm $(SITE)/index.html.bak

epub: $(RESTORED)
	mkdir -p $(BUILD)
	$(PANDOC) $(TEXT) \
		--from markdown-smart \
		--to epub3 \
		--css $(CSS) \
		--resource-path=source/text \
		--metadata title="$(TITLE)" \
		--metadata author="$(AUTHOR)" \
		--metadata lang=pt \
		--epub-cover-image=$(RESTORED) \
		--output $(BUILD)/poesias-infantis.epub

clean:
	rm -rf $(BUILD) $(SITE)
