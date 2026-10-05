# Código morto e telas órfãs

Lista de arquivos do frontend e do backend que não são usados pelo sistema
em produção, ou que têm pendências de manutenção pontual. Serve para
removermos aos poucos, sem misturar com outras mudanças.

Como registrar um item:
- **Caminho:** arquivo ou pasta.
- **Situação:** órfão (ninguém importa), duplicado (outra tela faz o mesmo) ou pendência (está em uso, mas tem algo a corrigir).
- **Evidência:** como foi verificado (busca de importação, rota etc.).
- **Ação:** o que falta fazer. Remover só depois de confirmação explícita.

---

## Itens em aberto

### 1. `frontend/src/pages/Pessoas.jsx` — órfão

- **Situação:** órfão. Nenhum arquivo importa `pages/Pessoas`.
- **Evidência:** na rota `/clientes` (`app/lazyPages.jsx`), `Pessoas` aponta para `preloadPessoas`, que carrega `pages/ClientesNovo.jsx`. O nome da exportação é enganoso, porque o arquivo realmente usado é outro.
- **Alterações feitas em 2026-10-05 que ficam sem efeito no sistema:**
  - Filtro de tipo trocado de `<select>` para `SeletorOpcoes`.
  - Busca trocada de `<input>` para `InputTexto`, com rótulo "Buscar".
  - Checkboxes de seleção trocados para `InputCheckbox`.
  - Debounce de 300 ms na busca.
  - Coluna "Acoes" movida para a primeira posição.
  - Remoção de `tipo_cadastro` dos badges e da tabela (uso de `tipos_cadastro`).
- **Ação:** remover o arquivo depois de confirmar que nenhuma outra tela o usa. As melhorias acima devem ser aplicadas na tela viva (ver item 2).

### 2. Tela viva `/clientes` — pendências de manutenção

Arquivos em uso (não são código morto), mas com pendências:

- `frontend/src/pages/ClientesNovo.jsx` — tela principal.
- `frontend/src/components/clientes/ClientesNovoActionsBar.jsx` — controle nativo `<input>` (linha ~37), provavelmente a busca.
- `frontend/src/components/clientes/ClientesNovoTabelaSection.jsx` — `<input>` nativo nas linhas ~54 e ~367 (checkbox de seleção). Coluna "Acoes" fica por último (linha ~344).
- `frontend/src/components/clientes/ClientesOrigemResumo.jsx` — controle nativo `<input>`.
- Busca já tem debounce em `frontend/src/hooks/useClientesNovoListagem.js` (linha ~29). Não precisa de nova implementação.

**Ação:** trocar os controles nativos por componentes v2 (`InputTexto`, `InputCheckbox`, `SeletorOpcoes`) e mover "Acoes" para a primeira posição, conforme a regra da memória do projeto.

---

## Itens resolvidos

_Nenhum ainda._

---

## Componentes v2 novos criados nesta rodada

Não são código morto, mas precisam ser conferidos no navegador quando forem usados na tela viva.

- `frontend/src/components/v2/InputCheckbox/` — checkbox quadrado para seleção em tabelas. Registrado em `styleGuideCatalog.js`.
