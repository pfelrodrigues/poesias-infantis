# Books

Coleção de livros antigos remasterizados para leitura no navegador e em EPUB.
Biblioteca, leitor, fontes editoriais e geradores ficam neste repositório.

O endereço público previsto é [pfelrodrigues.com.br/books/](https://pfelrodrigues.com.br/books/).
A interface e as apresentações têm versões PT/BR e EN. Os textos originais permanecem no idioma e na grafia da edição.

## Obras

- [Poesias infantis, Olavo Bilac, 1904](books/poesias-infantis/README.md). Contém 38 peças originais e um colofão editorial.
- [A vida dos Santos](books/a-vida-dos-santos/README.md). Caderno de Maria Luiza. 61 peças e um colofão editorial. Leitura gratuita. Sem venda.

## Organização

```text
books/
  poesias-infantis/
    book.yml                 metadados, ordem, política e hashes
    presentation.pt.md       apresentação em português
    presentation.en.md       apresentação em inglês
    text/                    textos da edição
    images/                  mestres e recortes
    css/                     estilo do EPUB
    tools/                   ferramentas específicas do fac-símile
scripts/                     exportação e geração compartilhadas
web/                         catálogo, leitor Hugo, estilos e traduções da interface
tests/                       integridade editorial e geração da coleção
site/                        biblioteca gerada, fora do Git
```

## Gerar e verificar

As versões estão fixadas em `mise.toml`: Python 3.12.13, uv 0.11.21, Pandoc 3.7.0.2, Hugo 0.163.3 e Node 22.22.0.
O Node usa apenas módulos nativos. Python usa `uv.lock`.

```sh
mise install
mise exec -- uv sync --locked
mise exec -- make test
mise exec -- make book
```

`make book` encontra todos os manifestos `books/*/book.yml`. Valida fontes e apresentações, gera HTML e EPUB da mesma estrutura do Pandoc e monta o site bilíngue.
Verifica links, recursos, âncoras, canonical e hreflang antes de substituir `site/`.
Uma falha preserva a última publicação gerada.

Os pacotes intermediários, hashes e páginas geradas ficam em `web/.editions/`, `web/data/books.lock.json` e `web/.generated/`. Nenhum entra no Git.
O site pessoal não importa esses pacotes nem recebe textos, imagens ou EPUBs.

Para exportar uma edição isolada:

```sh
mise exec -- make export BOOK=poesias-infantis OUTPUT=build/poesias-infantis/0.2.0
```

A saída precisa ser uma pasta nova. `--source` e `--output` também podem ser passados diretamente a `scripts/export_book.py`.
O pacote contém `book.json`, HTML por peça, imagens WebP, EPUB com imagens JPEG e mapa opcional de fragmentos legados.
Cada arquivo tem SHA-256. `source_commit`, `source_dirty` e `source_sha256` identificam a revisão e suas entradas.

## Acrescentar uma obra

Crie `books/outro-livro/`, com `book.yml`, textos e apresentações PT/EN. O nome da pasta precisa coincidir com `id`.
O gerador não precisa de mudanças para títulos, autores, ordem ou número de capítulos diferentes.

```yaml
id: outro-livro
version: 1.0.0
title: Outro livro
author: Nome do autor
language: pt
license: CC0-1.0
policy:
  original_statuses: [proofed]
  editorial_statuses: [draft, proofed]
  editorial_pieces: []
  expected_original_count: 1
pieces:
  - id: primeiro-capitulo
    file: text/primeiro-capitulo.md
    kind: prose
    original: true
```

Cada texto requer front matter com `id`, `title` e `status`, seguido de um H1 com o mesmo título.
Use `sha256` na entrada da peça para fixar seus bytes. Peças, imagens, traduções ou estilos ausentes interrompem a geração.
Os caminhos resolvem dentro da pasta da obra. Traduções de peças originais são rejeitadas; `translations.en` é reservado a notas editoriais.

As apresentações precisam de front matter com `description`, seguido do texto de apresentação. `blurb`, `weight`, `editionNote`, `coverAlt` e rótulos da ficha são opcionais.
Identificador, título e rotas são derivados do manifesto. Exemplos completos estão na pasta de Poesias infantis.
Capa e comparação de imagens são opcionais, com textos alternativos obrigatórios quando presentes.

## Integração com o domínio

O GitHub Pages hospeda o artefato `site/` como origem técnica. A Vercel do site pessoal encaminha apenas `/books` e `/en/books`, incluindo capítulos e recursos, para essa origem.
O encaminhamento usa rewrites, portanto mantém `pfelrodrigues.com.br` no navegador.

Os caminhos do artefato são os mesmos caminhos públicos. Após a renomeação do repositório para `books`, por exemplo:

| URL pública | Arquivo na origem |
|---|---|
| `/books/` | `https://pfelrodrigues.github.io/books/books/index.html` |
| `/en/books/` | `https://pfelrodrigues.github.io/books/en/books/index.html` |
| `/books/poesias-infantis/ler/a-avo/` | `https://pfelrodrigues.github.io/books/books/poesias-infantis/ler/a-avo/index.html` |

CSS, JavaScript, fontes e ícones usam `/books/ui/`; imagens e EPUBs usam `/books/assets/`. Links, canonical, hreflang e downloads apontam para o domínio público.
Cada aplicação mantém sua própria publicação. Acrescentar uma obra exige publicar somente este repositório.

### Ordem de publicação inicial

1. Revisar os PRs da coleção e do site pessoal.
2. Coordenar a renomeação `poesias-infantis` para `books` com a integração e publicação deste PR. Confirmar o artefato Pages e os caminhos acima.
3. Integrar o PR do site pessoal e confirmar o encaminhamento na Vercel, incluindo inglês, capítulo, imagem e EPUB.

A renomeação no GitHub não redireciona o antigo endereço do GitHub Pages. Ela deve acontecer junto da publicação, para reduzir a interrupção.
Os redirecionamentos de URLs do repositório, incluindo o PR, são mantidos pelo GitHub. O antigo endereço de leitura `github.io/poesias-infantis/` deixa de ser o endereço público.

O workflow de PR executa testes e EPUBCheck 5.3.0 para todos os EPUBs, com download da ferramenta fixado por hash.
Gera um artefato de revisão, sem release. O workflow Pages publica ao integrar em `main`.

## Licença

O trabalho editorial e o código estão em [CC0 1.0](LICENSE). Consulte a ficha e a licença de cada obra.
As fontes Archivo e IBM Plex Mono mantêm suas licenças próprias.
