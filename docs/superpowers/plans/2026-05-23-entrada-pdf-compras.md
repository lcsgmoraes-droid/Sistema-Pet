# Entrada por PDF em compras Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir importar pedido de fornecedor em PDF pela Central NF-e Entradas e processar estoque/financeiro pelo fluxo existente.

**Architecture:** Criar um parser pequeno para o layout do PDF, transformar o resultado em dados compativeis com a entrada atual e expor um endpoint `upload-pdf`. No frontend, adicionar um modal de upload com fornecedor obrigatorio e aviso sobre limites fiscais do PDF.

**Tech Stack:** FastAPI, SQLAlchemy, pypdf, pytest, React, Vite, Axios, lucide-react.

---

### Task 1: Parser PDF e contrato de dados

**Files:**
- Create: `backend/app/notas_entrada_pdf_parser.py`
- Test: `backend/tests/test_notas_entrada_pdf_parser.py`

- [ ] **Step 1: Write failing parser test**

Testar que o texto extraido de `PEDIDO 2.pdf` gera pedido `117061`, data `2026-05-22`, cinco itens, total `2220.97` e tres parcelas.

- [ ] **Step 2: Run parser test and confirm RED**

Run: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_notas_entrada_pdf_parser.py -q`

- [ ] **Step 3: Implement parser**

Implementar funcoes `extract_pdf_text`, `parse_pedido_pdf_text`, `build_pdf_synthetic_nfe_xml` e helpers de moeda/data.

- [ ] **Step 4: Run parser test and confirm GREEN**

Run: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_notas_entrada_pdf_parser.py -q`

### Task 2: Endpoint de upload PDF

**Files:**
- Modify: `backend/app/notas_entrada_routes.py`
- Modify: `backend/requirements.txt`
- Test: `backend/tests/test_notas_entrada_pdf_parser.py`

- [ ] **Step 1: Add failing compatibility test**

Testar que o XML sintetico produzido pelo parser e aceito por `parse_nfe_xml`.

- [ ] **Step 2: Implement endpoint**

Adicionar `POST /notas-entrada/upload-pdf` com `file` e `fornecedor_id`, criando `NotaEntrada` e `NotaEntradaItem` como o fluxo XML.

- [ ] **Step 3: Preserve fiscal data**

Extrair helper para aplicar dados fiscais no produto somente quando o item trouxer valores nao vazios.

- [ ] **Step 4: Run backend focused tests**

Run: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_notas_entrada_pdf_parser.py -q`

### Task 3: UI de upload PDF

**Files:**
- Modify: `frontend/src/components/entrada-xml/EntradaXmlHeader.jsx`
- Modify: `frontend/src/components/entrada-xml/useEntradaXmlUpload.js`
- Modify: `frontend/src/components/EntradaXML.jsx`
- Create: `frontend/src/components/entrada-xml/EntradaPdfUploadModal.jsx`

- [ ] **Step 1: Add PDF button**

Adicionar botao `Importar PDF` no header da Central NF-e Entradas.

- [ ] **Step 2: Add upload modal**

Criar modal com seletor de fornecedor, campo PDF, aviso fiscal e acao de importar.

- [ ] **Step 3: Wire API call**

Enviar `multipart/form-data` para `/notas-entrada/upload-pdf` e atualizar a lista apos sucesso.

### Task 4: Verification and PR

**Files:**
- No new files expected.

- [ ] **Step 1: Run backend focused tests**

Run: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_notas_entrada_pdf_parser.py -q`

- [ ] **Step 2: Run frontend build**

Run: `npm run build`

- [ ] **Step 3: Run fluxo unico check when available**

Run: `.\FLUXO_UNICO.bat check`

- [ ] **Step 4: Finish branch**

Run: `powershell -ExecutionPolicy Bypass -File .\scripts\git_finish_task.ps1 -Mensagem "feat: adicionar entrada por pdf em compras" -Push`
