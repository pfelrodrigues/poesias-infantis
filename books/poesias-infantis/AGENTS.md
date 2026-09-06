# Poesias infantis: regras da obra

Os caminhos abaixo são relativos a `books/poesias-infantis/`.

- Canônico = edição de 1904. Ortografia da época. Sem reforma no texto.
- Transcrever do scan em `scans/`. Wikisource é apoio, não fonte.
- Gravura: recortar e corrigir. Não redesenhar. Não branquear o papel.
- Estado no front matter: `draft` → `collated` → `proofed`.
- `[Editorial]` no commit só para emenda da edição de 1904, com nota no colofão.
- `book.yml` declara política, ordem das peças, hashes dos originais e recortes do fac-símile.
- Preserve os textos de `text/` e os mestres de `images/` durante alterações no pipeline.
- Git guarda a fonte. EPUB/PDF/HTML saem das ferramentas compartilhadas na raiz do repositório.
- Ferramentas de extração, OCR e recorte desta edição ficam em `tools/`.
- Scan BBM não entra no git. Release, se houver.
- Hub do vault: `~/Notes/Projetos/Poesias Infantis/Poesias Infantis.md`.
