# Poesias infantis (Olavo Bilac, 1904)

Remaster da primeira edição. Texto collacionado contra o scan de 1904. Gravuras recortadas, não redesenhadas.

Obra em domínio público. Trabalho deste repositório em [CC0](LICENSE).

## Fonte (ficha)

Bilac, Olavo, 1865-1918. *Poesias infantis*. Rio de Janeiro: Livraria Clássica de Francisco Alves, 1904. 127 p., 1 p. s.n. índice; il.; 20,1 × 13,4 cm. Língua: português. Tipo: livro. Direitos na ficha: domínio público.

Scan: **Brasiliana Digital**, Biblioteca Brasiliana Guita e José Mindlin (USP), acervo **Livros**. [digital.bbm.usp.br/handle/bbm/4694](https://digital.bbm.usp.br/handle/bbm/4694). Arquivos `002924_c_COMPLETO.pdf` (cor) e `002924_COMPLETO.pdf` (preto e branco).

Esta edição transcreve o texto e recorta gravuras a partir desse scan. Não substitui o fac-símile da Brasiliana.

## Como ler

- **No navegador:** <https://pfelrodrigues.github.io/poesias-infantis/>
- **EPUB:** [Release mais recente](https://github.com/pfelrodrigues/poesias-infantis/releases/latest)

```bash
make book
```

Gera `site/index.html` e `build/poesias-infantis.epub` na máquina.

## Distribuição para outro site

O exportador recebe um manifesto. Não contém títulos, ordem ou recortes específicos do livro no código.

```sh
uv sync --locked
make test
make export SOURCE=source/book.yml OUTPUT=build/distributions/poesias-infantis/0.2.0
```

O diretório de saída precisa ser novo. Uma exportação inválida não cria pacote parcial e não substitui uma distribuição existente.
O comando também aceita `--source` e `--output` diretamente:

```sh
uv run --locked python scripts/export_book.py --source /caminho/livro/book.yml --output /caminho/pacote
```

O pacote contém `book.json`, um HTML por peça, imagens WebP, EPUB e o mapa opcional `legacy-fragments.json`.
O mapa prepara a migração dos fragmentos antigos; nenhum redirecionamento foi ativado.
Todos os arquivos aparecem com SHA-256 em `book.json.files`. O comando imprime o caminho e o SHA-256 do próprio manifesto.
O site consumidor deve fixar esse último hash e verificar cada arquivo antes de importar.

O texto é convertido uma vez para a estrutura do Pandoc, com substituições tipográficas desativadas.
HTML e EPUB partem dessa mesma estrutura. Estrofes e parágrafos mantêm a ordem da fonte.
O HTML omite o primeiro H1, pois o site fornece o título. As seções internas permanecem com IDs.
Links internos viram `book:identificador#secao`; o importador resolve a rota.
O EPUB usa JPEG, formato básico do padrão EPUB, enquanto o site usa WebP.
Os arquivos mestres em `source/images/` permanecem intactos.

O pacote registra `source_commit`, `source_dirty` e `source_sha256`.
O último é o SHA-256 do JSON ordenado que associa cada arquivo de entrada ao seu hash, com separadores `,` e `:`.
Ele inclui manifesto, textos, traduções, imagens utilizadas e CSS do EPUB.
Uma distribuição local com alterações pendentes declara `source_dirty: true`; o commit sozinho não identifica essas alterações.
Fora de um repositório Git, o manifesto precisa fornecer `source_commit` explicitamente.

## Manifesto e estado editorial

`source/book.yml` contém metadados, política, ordem das peças, caminhos, hashes dos originais e recortes do fac-símile.
Todos os caminhos de entrada devem resolver dentro da pasta do manifesto.
Uma peça, imagem citada, capa ou folha de estilo ausente interrompe a exportação.
O exportador também rejeita links internos quebrados, IDs repetidos e estados fora da política.

As 38 peças originais estão em `collated`, permitidas explicitamente junto de `proofed`.
Isso registra a colação existente; não afirma que a etapa separada de revisão `proofed` terminou.
O colofão é editorial, vem depois dos originais e possui permissão explícita para `draft`.
A tradução inglesa existe apenas para o colofão. O exportador rejeita traduções de peças marcadas como originais.

Para acrescentar um livro, crie outro manifesto e suas fontes. Exemplo mínimo de prosa:

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

Cada Markdown requer front matter com `id`, `title` e `status`, seguido de um H1 com o mesmo título.
`sha256` na entrada da peça fixa os bytes do arquivo completo, incluindo front matter. Os 38 originais desta edição têm essa proteção.
Novas revisões editoriais exigem atualizar o estado e o hash de maneira deliberada.
Ilustrações precisam de texto alternativo; `cover` e `comparison` recebem `file`, `alt` e, opcionalmente, `name`.
`translations.en` indica o caminho de uma tradução editorial com seu próprio front matter e estado.

## Ferramentas e verificação

Versões: Python 3.12.13, uv 0.11.21 e Pandoc 3.7.0.2. Python e bibliotecas ficam fixos em `.python-version`, `pyproject.toml` e `uv.lock`.
O exportador recusa outra versão do Pandoc. Use as versões de `mise.toml` ou uma instalação equivalente.

`make test` cobre falhas de fonte/política, uma segunda obra em prosa, estrofes, tradução editorial, integridade e referências do EPUB.
Também compara todos os 38 originais com os bytes da base Git e compara todos os seus parágrafos e estrofes entre fonte, HTML e EPUB.

O workflow `verify-book` gera um artefato após os testes e o EPUBCheck 5.3.0, cujo download é fixado por SHA-256.
Ele não cria release público. O workflow Pages conserva a publicação existente e passa a executar os testes antes de gerar o site antigo.
A mudança de domínio e a ativação de redirecionamentos permanecem etapas futuras.

## Arquivos no git

| Caminho | O que é |
|---|---|
| `source/book.yml` | Metadados, política, ordem, hashes e recortes |
| `scripts/export_book.py` | Exportador parametrizado do pacote web e EPUB |
| `scripts/pieces.py` | Leitor de compatibilidade do inventário para ferramentas de scan |
| `source/text/` | Um Markdown por peça, ortografia de 1904 |
| `source/images/extracted/` | Recortes crus |
| `source/images/restored/` | Gravuras usadas no ebook |
| `source/scans/` | PDFs da BBM (fora do git) |

## Princípios

- Texto da edição de 1904. Sem reforma ortográfica no canônico.
- Transcrição a partir do scan. Wikisource é apoio, não fonte.
- Gravura: recortar do scan. Cor das aberturas é intervenção desta edição, declarada no colofão.
- Git guarda a fonte. EPUB e HTML saem do `make book`.

## Licença

Texto e gravuras de 1904: domínio público. Extração, restauro, marcação e código: CC0 1.0. Detalhe em [LICENSE](LICENSE).
