# Poesias infantis (Olavo Bilac, 1904)

Remaster da primeira edição. Texto collacionado contra o scan de 1904. Gravuras recortadas, não redesenhadas.

Obra em domínio público. Extração, restauro, marcação e código deste repositório em [CC0](../../LICENSE).

## Fonte (ficha)

Bilac, Olavo, 1865-1918. *Poesias infantis*. Rio de Janeiro: Livraria Clássica de Francisco Alves, 1904. 127 p., 1 p. s.n. índice; il.; 20,1 × 13,4 cm. Língua: português. Tipo: livro. Direitos na ficha: domínio público.

Scan: **Brasiliana Digital**, Biblioteca Brasiliana Guita e José Mindlin (USP), acervo **Livros**. [digital.bbm.usp.br/handle/bbm/4694](https://digital.bbm.usp.br/handle/bbm/4694). Arquivos `002924_c_COMPLETO.pdf` (cor) e `002924_COMPLETO.pdf` (preto e branco).

Esta edição transcreve o texto e recorta gravuras a partir desse scan. Não substitui o fac-símile da Brasiliana.

## Edição e critérios editoriais

O canônico preserva o texto e a ortografia de 1904. Wikisource serve como apoio, sem substituir o scan como fonte.

O manifesto [book.yml](book.yml) contém metadados, política editorial, ordem das peças, caminhos, hashes dos originais e recortes do fac-símile. Os caminhos de entrada são relativos a esta pasta.

As 38 peças originais estão em `collated`, estado permitido junto de `proofed`. Isso registra a colação existente; não afirma que a revisão `proofed` terminou.

Cada original tem um SHA-256 no manifesto, que fixa o arquivo completo, incluindo o front matter. Mudanças editoriais exigem revisão deliberada do estado e do hash.

O colofão é editorial, vem depois dos originais e possui permissão explícita para `draft`. A tradução inglesa existe apenas para o colofão.

As gravuras são recortes do scan. A cor das aberturas é intervenção desta edição, declarada no colofão. Os arquivos mestres permanecem em `images/`.

## Gerar a edição

Consulte o [README da coleção](../../README.md) para preparar as ferramentas e gerar a biblioteca. Execute os comandos na raiz do repositório.

```sh
uv sync --locked
uv run --locked python scripts/export_book.py \
  --source books/poesias-infantis/book.yml \
  --output build/distributions/poesias-infantis/0.2.0
```

O diretório de saída precisa ser novo. O pacote contém metadados, um HTML por peça, imagens WebP, EPUB e o mapa de fragmentos legados.

HTML e EPUB partem da mesma estrutura de texto. O EPUB usa imagens JPEG; os mestres de `images/` permanecem intactos.

## Arquivos da obra

| Caminho | Conteúdo |
|---|---|
| `book.yml` | Metadados, política, ordem, hashes e recortes |
| `text/` | Originais, colofão e tradução editorial |
| `images/extracted/` | Recortes crus |
| `images/restored/` | Gravuras usadas na edição |
| `css/` | Estilos do EPUB |
| `facsimile/` | Referências de paginação e material de conferência |
| `scans/` | PDFs da BBM, fora do Git |
| `tools/` | Ferramentas específicas de extração, OCR e recorte |

## Ferramentas editoriais

Estas ferramentas operam sobre o scan colorido `scans/002924_c_COMPLETO.pdf` e seus arquivos de trabalho. Seus caminhos independem da pasta atual do terminal.

| Ferramenta | Função |
|---|---|
| `tools/extract_pages.py` | Rasteriza o scan em `images/pages/` |
| `tools/dump_ocr.py` | Extrai o OCR para `facsimile/ocr-dump.txt` |
| `tools/crop_headers.py` | Recorta capa e gravuras conforme `book.yml` |
| `tools/restore_pilot.py` | Reproduz o recorte piloto de A Avó |
| `tools/pieces.py` | Lê o inventário do manifesto para as ferramentas de scan |

Os PDFs, páginas rasterizadas e o despejo de OCR ficam fora do Git. Recortes e restauros exigem conferência visual antes de substituir imagens da edição.

## Licença

Texto e gravuras de 1904: domínio público. Extração, restauro, marcação e código: CC0 1.0. Detalhe em [LICENSE](../../LICENSE).
