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
