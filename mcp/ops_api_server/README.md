# MCP Ops/API - Sistema Pet

Servidor MCP para operar e validar o Sistema Pet no fluxo oficial DEV -> PROD.

## Objetivo

Este servidor entrega ferramentas MCP para:

- executar validacoes do fluxo unico (`check`, `dev-up`, `release-check`, `status`)
- proteger a acao local `prod-up` com trava explicita
- validar saude da API local
- validar rota de login multitenant
- validar permissoes usadas por abas do sistema
- consultar logs e fila do motor de campanhas no banco DEV
- ler logs recentes do backend DEV com redaction de segredos

## Arquitetura

- `ops_api_mcp/server.py`: expoe ferramentas MCP
- `ops_api_mcp/services/command_service.py`: execucao segura do fluxo unico
- `ops_api_mcp/services/api_service.py`: chamadas HTTP locais e validacoes de autenticacao
- `ops_api_mcp/services/campaign_service.py`: consultas e eventos de teste do motor de campanhas DEV
- `ops_api_mcp/services/docker_service.py`: execucao Docker com timeout e redaction
- `ops_api_mcp/services/log_service.py`: leitura filtrada de logs do backend DEV
- `ops_api_mcp/security.py`: allowlist de hosts, redaction e limites
- `ops_api_mcp/config.py`: paths, ambiente, containers, banco e limites
- `ops_api_mcp/models.py`: respostas padronizadas

## Ferramentas MCP disponiveis

| Ferramenta | Tipo | Ambiente | Observacao |
|---|---|---|---|
| `fluxo_check` | leitura/validacao | local | roda `FLUXO_UNICO check` |
| `fluxo_dev_up` | escrita operacional | DEV local | sobe DEV local |
| `fluxo_release_check` | leitura/validacao | local | valida release sem permitir alteracoes locais |
| `fluxo_status` | leitura | local | consulta status do compose usado pelo fluxo |
| `fluxo_prod_up` | escrita sensivel | local PROD | bloqueada por padrao |
| `api_health_check` | leitura | HTTP local | default `http://localhost:8000/health` |
| `api_auth_route_smoke` | leitura | HTTP local | default `http://localhost:8000/auth/login-multitenant` |
| `auth_validate_tabs_permissions` | leitura autenticada | HTTP local | nao retorna tokens |
| `campaign_logs` | leitura | banco DEV | usa container/banco configurados |
| `campaign_queue_status` | leitura | banco DEV | usa container/banco configurados |
| `campaign_enqueue_test_event` | escrita de teste | banco DEV | valida evento, UUID e JSON |
| `backend_logs` | leitura | container DEV | aplica redaction de segredos |

## Trava de prod-up

`fluxo_prod_up` nao roda por padrao. Para liberar conscientemente:

```powershell
$env:SISTEMA_PET_MCP_ALLOW_PROD_ACTIONS = "true"
$env:SISTEMA_PET_MCP_PROD_CONFIRMATION = "AUTORIZO PROD-UP LOCAL"
```

Mesmo liberada, a ferramenta exige o parametro `confirmacao` com a frase exata. Ela nao faz deploy remoto.

## Variaveis principais

- `SISTEMA_PET_MCP_HEALTH_URL`
- `SISTEMA_PET_MCP_AUTH_URL`
- `SISTEMA_PET_MCP_ALLOWED_HTTP_HOSTS`
- `SISTEMA_PET_MCP_DEV_POSTGRES_CONTAINER`
- `SISTEMA_PET_MCP_DEV_BACKEND_CONTAINER`
- `SISTEMA_PET_MCP_DEV_DB_USER`
- `SISTEMA_PET_MCP_DEV_DB_NAME`
- `SISTEMA_PET_MCP_AUDIT_LOG`
- `SISTEMA_PET_MCP_TIMEOUT_SECONDS`
- `SISTEMA_PET_MCP_MAX_TIMEOUT_SECONDS`
- `SISTEMA_PET_MCP_MAX_OUTPUT_CHARS`

Por padrao, a auditoria local fica no diretorio temporario do Windows, em `sistema_pet_mcp_ops_audit.jsonl`.

## Instalacao

```powershell
cd mcp/ops_api_server
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
```

Para rodar testes:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .[dev]
.\.venv\Scripts\python.exe -m pytest
```

Ou, pela raiz do projeto:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\test_mcp.ps1 -InstallDevDependencies
```
