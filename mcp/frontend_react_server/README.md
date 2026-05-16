# MCP Frontend React - Sistema Pet

Servidor MCP para automacao do frontend React/Vite do Sistema Pet.

## Objetivo

Entregar ferramentas para:

- validar status do frontend
- executar build de producao e build de desenvolvimento
- realizar smoke de inicializacao `npm run dev`
- validar disponibilidade HTTP da aplicacao
- validar resposta da rota de login multitenant da API local

## Arquitetura

- `frontend_react_mcp/server.py`: ferramentas MCP
- `frontend_react_mcp/services/frontend_service.py`: execucao segura de scripts npm
- `frontend_react_mcp/services/http_service.py`: validacoes HTTP locais
- `frontend_react_mcp/security.py`: allowlist de hosts, redaction e limites
- `frontend_react_mcp/config.py`: paths, URLs, hosts permitidos, timeouts e limites
- `frontend_react_mcp/models.py`: respostas padronizadas

## Ferramentas MCP disponiveis

| Ferramenta | Risco | Ambiente | Observacao |
|---|---|---|---|
| `front_status` | leitura | local | confere frontend, `package.json`, Node e npm |
| `front_build_check` | leitura/validacao | local | roda `npm run build` |
| `front_build_dev_check` | leitura/validacao | local | roda `npm run build:dev` |
| `front_dev_smoke` | escrita DEV local | local | roda `npm run dev` com host permitido |
| `front_http_check` | leitura HTTP | HTTP local | default `http://localhost:5173` |
| `front_api_auth_smoke` | leitura HTTP | HTTP local | default `http://localhost:8000/auth/login-multitenant` |

## Seguranca local

- URLs HTTP passam por allowlist de hosts.
- Por padrao, somente `localhost`, `127.0.0.1` e `::1` sao aceitos.
- `front_dev_smoke` aceita apenas hosts de desenvolvimento permitidos.
- Saidas de comando passam por redaction de tokens/senhas comuns.

## Variaveis principais

- `SISTEMA_PET_FRONT_MCP_FRONT_URL`
- `SISTEMA_PET_FRONT_MCP_AUTH_URL`
- `SISTEMA_PET_FRONT_MCP_ALLOWED_HTTP_HOSTS`
- `SISTEMA_PET_FRONT_MCP_ALLOWED_DEV_HOSTS`
- `SISTEMA_PET_FRONT_MCP_AUDIT_LOG`
- `SISTEMA_PET_FRONT_MCP_TIMEOUT_SECONDS`
- `SISTEMA_PET_FRONT_MCP_MAX_TIMEOUT_SECONDS`
- `SISTEMA_PET_FRONT_MCP_MAX_OUTPUT_CHARS`

Por padrao, a auditoria local fica no diretorio temporario do Windows, em `sistema_pet_mcp_frontend_audit.jsonl`.

## Instalacao

```powershell
cd mcp/frontend_react_server
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

Os testes incluem cobertura de protocolo MCP por stdio em `tests/test_mcp_protocol.py`.
