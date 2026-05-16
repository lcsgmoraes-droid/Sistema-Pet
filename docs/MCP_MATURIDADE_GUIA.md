# Guia de maturidade dos MCPs do Sistema Pet

Atualizado em: 2026-05-16

Este arquivo e o quadro de controle dos MCPs locais. Use para saber o que ja foi feito, o que falta e qual deve ser o proximo passo sem se perder.

## Objetivo

Levar os MCPs locais do Sistema Pet para um padrao seguro, repetivel e facil de manter.

Nota inicial estimada: 4/10.

Nota atual estimada: 10/10.

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
| Feito | CI dos MCPs rodando em todo Pull Request para permitir branch protection | `.github/workflows/mcp-ci.yml` |
| Feito | Branch protection da `main` exigindo o check `MCP tests` | GitHub branch protection |
| Feito | Testes de protocolo MCP ponta a ponta via stdio | `tests/test_mcp_protocol.py` dos MCPs |
| Feito | Checklist obrigatorio para novas ferramentas MCP | secao "Checklist obrigatorio para novas ferramentas MCP" |
| Feito | Classificacao de risco das ferramentas atuais | READMEs internos dos MCPs |
| Feito | Relatorio local de auditoria dos MCPs | ferramenta `mcp_audit_report` |
| Feito | Revisao periodica de dependencias dos MCPs | `.github/dependabot.yml` |
| Feito | Documentacao de uso e arquitetura dos MCPs | `mcp/README.md` e READMEs internos |
| Feito | Badge visual do CI no README dos MCPs | `mcp/README.md` |
| Feito | Rodada Dependabot GitHub Actions revisada e mergeada | PRs #52, #53 e #54 |

## PRs ja juntados

| PR | Conteudo | Status |
|---|---|---|
| #44 | Hardening dos MCPs: seguranca, services, testes, auditoria, docs | Mergeado |
| #45 | CI dos MCPs e bootstrap automatico dos venvs | Mergeado |
| #47 | Ajuste do MCP CI para rodar em todo PR antes da branch protection | Mergeado |
| #48 | Guia atualizado com branch protection e proximos passos | Mergeado |
| #49 | Testes de protocolo MCP ponta a ponta | Mergeado |
| #50 | Relatorio local de auditoria dos MCPs | Mergeado |
| #52 | Dependabot: `actions/setup-node` v4 -> v6 | Mergeado |
| #53 | Dependabot: `actions/checkout` v4 -> v6 | Mergeado |
| #54 | Dependabot: `actions/setup-python` v5 -> v6 | Mergeado |

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

## O que falta para manter 10/10

| Prioridade | Status | Item | Motivo |
|---|---|---|---|
| Baixa | Continuo | Revisar PRs do Dependabot dos MCPs | Mantem `mcp`, `requests` e `pytest` atualizados com seguranca |

Rodada 2026-05-16:

- PRs Dependabot abertos para GitHub Actions revisados e mergeados: #52, #53 e #54.
- Checks obrigatorios passaram em cada PR antes do merge: `MCP tests`, `Fluxo unico safety`, `Quality Gate` e `Smoke test`.
- Teste local dos MCPs neste PC: `14 passed` via `powershell -ExecutionPolicy Bypass -File .\scripts\test_mcp.ps1`.
- Dependabot aberto relacionado a MCP/CI apos a rodada: nenhum.

## Proximo passo recomendado

1. Quando o Dependabot abrir PR, revisar e mergear se o check `MCP tests` passar.
2. Reauditar maturidade dos MCPs quando uma ferramenta nova for adicionada.

## Branch protection atual

Configurada em 2026-05-16 no GitHub:

| Regra | Valor |
|---|---|
| Branch protegida | `main` |
| Status check obrigatorio | `MCP tests` |
| Branch atualizada antes de merge | Sim (`strict: true`) |
| Force push | Bloqueado |
| Delecao da branch | Bloqueada |

Observacao: o workflow `MCP CI` roda em todo Pull Request para que o check `MCP tests` exista mesmo quando o PR nao altera arquivos em `mcp/`.

## Checklist obrigatorio para novas ferramentas MCP

Antes de adicionar uma ferramenta MCP nova, preencher estes itens no PR:

| Pergunta | Obrigatorio |
|---|---|
| A ferramenta e leitura, escrita DEV ou sensivel? | Sim |
| Tem limite de timeout? | Sim |
| Tem truncamento/redaction de saida? | Sim |
| Evita shell livre e argumentos inseguros? | Sim |
| Usa config/env em vez de hardcode? | Sim |
| Tem teste automatizado? | Sim |
| Tem teste de protocolo MCP se for ferramenta publica nova? | Sim |
| Esta documentada no README do MCP? | Sim |

Se uma resposta for "nao", a ferramenta ainda nao esta pronta para entrar.

## Classes de risco

| Classe | Uso permitido |
|---|---|
| leitura | consulta estado local ou metadados sem alterar nada |
| leitura HTTP | consulta endpoints locais permitidos por allowlist |
| leitura DEV | consulta banco, container ou logs do ambiente DEV |
| leitura autenticada | usa credenciais fornecidas pelo operador, sem retornar tokens |
| leitura/validacao | executa validacao local sem alterar dados persistentes |
| escrita DEV local | altera apenas ambiente DEV/local ou sobe processo local |
| escrita sensivel | exige trava explicita e confirmacao; nunca faz deploy remoto por MCP |
