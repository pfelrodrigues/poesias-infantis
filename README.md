# Poesias infantis (Olavo Bilac, 1904)

Remaster da primeira edição. Texto collacionado contra o scan de 1904. Gravuras recortadas, não redesenhadas.

Obra em domínio público. Trabalho deste repositório em [CC0](LICENSE).

## Fonte

O scan usado neste remaster foi baixado da Biblioteca Brasiliana Guita e José Mindlin (USP):

**[digital.bbm.usp.br/handle/bbm/4694](https://digital.bbm.usp.br/handle/bbm/4694)**

Arquivos: `002924_c_COMPLETO.pdf` (cor) e `002924_COMPLETO.pdf` (preto e branco). A BBM marca o item como domínio público. Esta edição não substitui o fac-símile deles.

## Como ler

- **No navegador:** <https://pfelrodrigues.github.io/poesias-infantis/>
- **EPUB:** [Release mais recente](https://github.com/pfelrodrigues/poesias-infantis/releases/latest)

```bash
make book
```

Gera `site/index.html` e `build/poesias-infantis.epub` na máquina.

## Arquivos no git

| Caminho | O que é |
|---|---|
| `source/book.yml` | Metadados da edição |
| `scripts/pieces.py` | Inventário: títulos, páginas, recortes |
| `source/text/` | Um Markdown por peça, ortografia de 1904 |
| `source/images/extracted/` | Recortes crus |
| `source/images/restored/` | Gravuras usadas no ebook |
| `source/scans/` | PDFs da BBM (fora do git) |

## Princípios

- Texto da edição de 1904. Sem reforma ortográfica no canônico.
- Transcrição a partir do scan. Wikisource é apoio, não fonte.
- Gravura: recortar. Não redesenhar o traço. Não branquear o papel.
- Git guarda a fonte. EPUB e HTML saem do `make book`.

## Licença

Texto e gravuras de 1904: domínio público. Extração, restauro, marcação e código: CC0 1.0. Detalhe em [LICENSE](LICENSE).
