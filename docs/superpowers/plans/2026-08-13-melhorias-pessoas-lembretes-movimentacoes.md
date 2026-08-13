# Melhorias Operacionais em Pessoas, Lembretes e Movimentacoes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Aplicar o desenho clean aprovado nas tres telas sem alterar APIs ou regras de negocio.

**Architecture:** Reutilizar o componente `CopyableValue` na lista de Pessoas, manter o controller de validade intacto e alterar apenas a camada de apresentacao, e controlar a expansao de observacoes localmente na tabela de movimentacoes. Os contratos existentes serao preservados e novos testes focados verificarao os comportamentos visuais essenciais.

**Tech Stack:** React 18, Tailwind CSS, Lucide React, React Icons, Node.js test runner, ESLint e Vite.

---

### Task 1: Contratos de regressao

**Files:**
- Create: `frontend/src/components/clientes/clientesNovoTabelaCopy.test.mjs`
- Create: `frontend/src/pages/lembretes/lembretesValidadePresentation.test.mjs`
- Create: `frontend/src/components/estoque/movimentacoesObservacao.test.mjs`

- [ ] **Step 1: Escrever testes inicialmente falhos**

Os testes devem ler os componentes como contrato e exigir: uso de `CopyableValue` nos tres campos, novos rotulos/estilos semanticos de validade, e observacao com expansao por linha e largura minima da tabela.

- [ ] **Step 2: Confirmar as falhas antes da implementacao**

Run:

```powershell
node --test src/components/clientes/clientesNovoTabelaCopy.test.mjs src/pages/lembretes/lembretesValidadePresentation.test.mjs src/components/estoque/movimentacoesObservacao.test.mjs
```

Expected: FAIL nos contratos ainda nao presentes.

### Task 2: Copia contextual na lista de Pessoas

**Files:**
- Modify: `frontend/src/components/clientes/ClientesNovoTabelaSection.jsx`
- Test: `frontend/src/components/clientes/clientesNovoTabelaCopy.test.mjs`

- [ ] **Step 1: Importar e reutilizar `CopyableValue`**

Aplicar o componente em codigo, nome e celular no desktop. Configurar `title`, classes e valores vazios sem botao.

- [ ] **Step 2: Cobrir os mesmos campos no cartao mobile**

Manter alvos de toque adequados e garantir que o clique nao propague para a abertura da pessoa.

- [ ] **Step 3: Rodar o teste focado**

Run:

```powershell
node --test src/components/clientes/clientesNovoTabelaCopy.test.mjs
```

Expected: PASS.

### Task 3: Lembretes de validade clean operacional

**Files:**
- Modify: `frontend/src/pages/lembretes/LembretesValidadeSection.jsx`
- Test: `frontend/src/pages/lembretes/lembretesValidadePresentation.test.mjs`
- Test: `frontend/src/pages/lembretesValidadeFlow.test.mjs`

- [ ] **Step 1: Trocar os estilos inline pelos paineis clean aprovados**

Preservar os tres estados do controller e a mesma chamada de processamento.

- [ ] **Step 2: Modernizar cabecalho, contador e botoes**

Usar verde-petroleo como acao principal, ambar suave para o alerta e rotulos `Descartar`, `Registrar troca` e `Retornar ao estoque`.

- [ ] **Step 3: Rodar os testes focados e o contrato legado**

Run:

```powershell
node --test src/pages/lembretes/lembretesValidadePresentation.test.mjs src/pages/lembretesValidadeFlow.test.mjs
npm run test:lembretes-refactor
```

Expected: PASS.

### Task 4: Observacoes legiveis nas movimentacoes

**Files:**
- Modify: `frontend/src/components/estoque/MovimentacoesLancamentosTable.jsx`
- Test: `frontend/src/components/estoque/movimentacoesObservacao.test.mjs`
- Test: `frontend/src/components/estoque/movimentacoesProdutoUtils.test.mjs`

- [ ] **Step 1: Dar largura minima previsivel a tabela e a coluna**

Aplicar rolagem horizontal e impedir quebra caractere por caractere.

- [ ] **Step 2: Adicionar expansao local por movimentacao**

Mostrar duas linhas por padrao e alternar `Ver mais`/`Ver menos`, bloqueando propagacao para o modal da linha.

- [ ] **Step 3: Rodar os testes focados e de regressao**

Run:

```powershell
node --test src/components/estoque/movimentacoesObservacao.test.mjs src/components/estoque/movimentacoesProdutoUtils.test.mjs
```

Expected: PASS.

### Task 5: Verificacao, entrega e producao

**Files:**
- Modify only if verification finds an issue in the files above.

- [ ] **Step 1: Rodar formatacao e lint focados**

Run:

```powershell
npx prettier --check src/components/clientes/ClientesNovoTabelaSection.jsx src/pages/lembretes/LembretesValidadeSection.jsx src/components/estoque/MovimentacoesLancamentosTable.jsx
npx eslint src/components/clientes/ClientesNovoTabelaSection.jsx src/pages/lembretes/LembretesValidadeSection.jsx src/components/estoque/MovimentacoesLancamentosTable.jsx
```

Expected: PASS.

- [ ] **Step 2: Rodar build de producao**

Run: `npm run build`

Expected: Vite build concluido sem erro e sem versionar `frontend/dist`.

- [ ] **Step 3: Revisar diff e finalizar a branch**

Run: `powershell -ExecutionPolicy Bypass -File .\scripts\git_finish_task.ps1 -Mensagem "feat: melhora pessoas lembretes e movimentacoes" -Push`

Expected: commit criado e branch enviada, sem arquivos protegidos ou temporarios.

- [ ] **Step 4: Abrir e mesclar Pull Request**

Confirmar checks verdes e mesclar na `main`, sem push direto para a branch protegida.

- [ ] **Step 5: Executar deploy seguro autorizado**

Usar o wrapper oficial remoto `sudo -n /usr/local/sbin/petshop-deploy-producao` pelo usuario `petdeploy` e validar `/health/watchdog` e `/api/health`.

