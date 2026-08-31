# Poesias infantis (Olavo Bilac, 1904)

Remaster da primeira edição. Texto collacionado contra o scan de 1904. Gravuras restauradas, não redesenhadas.

Obra em domínio público. Trabalho deste repositório em [CC0](LICENSE).

Scan de origem: [Biblioteca Brasiliana Mindlin, bbm/4694](https://digital.bbm.usp.br/handle/bbm/4694).

## Como ler

Ainda não há release. O piloto é o poema *A Avó*:

```bash
mise exec -- just html   # site/index.html
mise exec -- just epub   # build/poesias-infantis.epub
```

## Fonte

| Caminho | O que é |
|---|---|
| `source/book.yml` | Metadados da edição |
| `source/text/` | Um Markdown por peça, ortografia de 1904 |
| `source/images/extracted/` | Recortes crus do PDF |
| `source/images/restored/` | Gravuras usadas no ebook |
| `source/scans/` | PDFs da BBM (fora do git) |

Estado da colação no front matter: `draft` → `collated` → `proofed`.

## Princípios

- Texto da edição de 1904. Sem reforma ortográfica no canônico.
- Transcrição a partir do scan. Wikisource é apoio, não fonte.
- Gravura: recortar, endireitar, corrigir cor. Não redesenhar o traço.
- Git guarda a fonte. EPUB, PDF e AZW3 saem do build.

## Licença

Texto e gravuras de 1904: domínio público. Extração, restauro, marcação e código: CC0 1.0. Detalhe em [LICENSE](LICENSE).
