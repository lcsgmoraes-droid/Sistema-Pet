# Guia de maturidade dos MCPs do Sistema Pet

Atualizado em: 2026-05-16

Este arquivo e o quadro de controle dos MCPs locais. Use para saber o que ja foi feito, o que falta e qual deve ser o proximo passo sem se perder.

## Objetivo

Levar os MCPs locais do Sistema Pet para um padrao seguro, repetivel e facil de manter.

Nota inicial estimada: 4/10.

Nota atual estimada: 8,5/10.

Meta: 10/10 para uso interno profissional.

## MCPs atuais

| MCP | Caminho | Funcao |
|---|---|---|
| `sistema-pet-frontend-react` | `mcp/frontend_react_server` | validar frontend React/Vite, builds e smoke HTTP |
| `sistema-pet-ops-api` | `mcp/ops_api_server` | validar fluxo unico, API local, Docker DEV, campanhas e logs |

## Feito

| Status | Item | Referencia |
|---|---|---|
| Feito | Auditoria inicial de estrutura e maturidade | conversa Codex em 2026-05-16 |
| Feito | Separacao basica entre MCP de frontend e MCP de operacoes | `mcp/` |
| Feito | Trava de seguranca para `fluxo_prod_up` | `mcp/ops_api_server/src/ops_api_mcp/services/command_service.py` |
| Feito | Configuracao por variaveis de ambiente | `mcp/*/src/*/config.py` |
| Feito | Remocao de hardcode quebrado do usuario Postgres DEV | `SISTEMA_PET_MCP_DEV_DB_USER` |
| Feito | Allowlist de hosts HTTP locais | `mcp/*/src/*/security.py` |
| Feito | Redaction basica de tokens, senhas e secrets | `mcp/*/src/*/security.py` |
| Feito | Auditoria local em JSONL no diretorio temporario | `audit_service.py` dos MCPs |
| Feito | Separacao de services do MCP Ops/API | `api_service`, `campaign_service`, `docker_service`, `log_service`, `command_service` |
| Feito | Testes unitarios dos MCPs | `mcp/*/tests` |
| Feito | Script unico para testes dos MCPs | `scripts/test_mcp.ps1` |
| Feito | Bootstrap automatico de `.venv` com `-InstallDevDependencies` | `scripts/test_mcp.ps1` |
| Feito | CI do GitHub para MCPs | `.github/workflows/mcp-ci.yml` |
| Feito | Documentacao de uso e arquitetura dos MCPs | `mcp/README.md` e READMEs internos |
| Feito | Badge visual do CI no README dos MCPs | `mcp/README.md` |

## PRs ja juntados

| PR | Conteudo | Status |
|---|---|---|
| #44 | Hardening dos MCPs: seguranca, services, testes, auditoria, docs | Mergeado |
| #45 | CI dos MCPs e bootstrap automatico dos venvs | Mergeado |

## Como validar agora

Pela raiz do projeto:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\test_mcp.ps1
```

Em computador limpo ou depois de apagar `.venv`:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\test_mcp.ps1 -InstallDevDependencies
```

Validacao geral do fluxo:

```powershell
.\FLUXO_UNICO.bat check
```

## O que falta para 10/10

| Prioridade | Status | Item | Motivo |
|---|---|---|---|
| Alta | Pendente | Proteger a branch `main` exigindo o check `MCP tests` | Impede merge de PR que quebre MCPs |
| Alta | Pendente | Criar teste de protocolo MCP ponta a ponta | Garante que o servidor MCP responde como cliente real espera |
| Media | Pendente | Criar checklist obrigatorio para novas ferramentas MCP | Evita ferramenta nova sem teste, docs e classificacao de risco |
| Media | Pendente | Classificar cada ferramenta por risco: leitura, escrita DEV, escrita sensivel | Ajuda o Lucas e assistentes a nao usarem ferramenta errada |
| Media | Pendente | Centralizar auditoria ou criar relatorio local de auditoria | Facilita rastrear uso sem abrir JSONL manualmente |
| Baixa | Pendente | Revisao periodica de dependencias dos MCPs | Mantem `mcp`, `requests` e `pytest` atualizados com seguranca |

## Proximo passo recomendado

1. Configurar branch protection da `main` no GitHub.
2. Exigir o check `MCP tests` quando houver PR.
3. Depois abrir nova tarefa para teste MCP ponta a ponta.

## Como configurar branch protection manualmente

No GitHub:

1. Abrir o repositorio `lcsgmoraes-droid/Sistema-Pet`.
2. Ir em `Settings`.
3. Ir em `Branches`.
4. Criar ou editar regra para `main`.
5. Ativar `Require status checks to pass before merging`.
6. Selecionar o check `MCP tests`.
7. Salvar.

Observacao: ate o momento, o conector GitHub disponivel aqui nao expos uma ferramenta para configurar branch protection automaticamente. Por isso este passo ficou operacional/manual.

## Regra para novas ferramentas MCP

Antes de adicionar uma ferramenta MCP nova, preencher mentalmente estes itens:

| Pergunta | Obrigatorio |
|---|---|
| A ferramenta e leitura, escrita DEV ou sensivel? | Sim |
| Tem limite de timeout? | Sim |
| Tem truncamento/redaction de saida? | Sim |
| Evita shell livre e argumentos inseguros? | Sim |
| Usa config/env em vez de hardcode? | Sim |
| Tem teste automatizado? | Sim |
| Esta documentada no README do MCP? | Sim |

Se uma resposta for "nao", a ferramenta ainda nao esta pronta para entrar.
