# Books: regras da coleção

- Cada obra vive em `books/<id>/`, com `book.yml`, fontes e regras editoriais próprias.
- Leia o `AGENTS.md` e o `README.md` da obra antes de alterar suas fontes.
- A edição canônica, os estados permitidos e as fontes de referência pertencem à política de cada obra.
- Preserve os bytes dos textos originais e das imagens mestres durante mudanças de estrutura ou de ferramentas.
- Registre emendas editoriais deliberadas no colofão da obra e atualize os hashes do manifesto.
- Mantenha ferramentas compartilhadas em `scripts/`; ferramentas específicas ficam em `books/<id>/tools/`.
- Não introduza títulos, ordem de peças ou recortes de uma obra nas ferramentas compartilhadas.
- Git guarda fontes e configuração. EPUB, PDF, HTML e arquivos intermediários são gerados.
- Scans e arquivos de trabalho permanecem fora do Git; respeite a origem e a licença declaradas por obra.
- Valide o manifesto, a integridade das fontes e as saídas afetadas antes de concluir.
