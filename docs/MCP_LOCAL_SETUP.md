# MCP local do Sistema Pet

Este projeto tem dois servidores MCP locais:

- `sistema-pet-frontend-react`: ferramentas para validar o frontend React.
- `sistema-pet-ops-api`: ferramentas para validar fluxo, API e operacao.

## Preparar neste PC

Os ambientes virtuais ficam dentro de `mcp/*/.venv` e nao entram no Git.

Em PC novo, use o bootstrap geral primeiro:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap_dev_environment.ps1 -DryRun
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap_dev_environment.ps1
```

Antes do setup, voce pode rodar o diagnostico seguro de ambiente DEV:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check_dev_environment.ps1 -NoNetwork
```

Detalhes e correcoes comuns ficam em `docs/DEV_ENVIRONMENT_CHECK.md`.

Forma automatica:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_mcp_local.ps1 -InstalarGitHubCli
```

Forma manual:

```powershell
cd mcp/frontend_react_server
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .

cd ..\ops_api_server
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
```

O VS Code le a configuracao em `.vscode/mcp.json`.

## Testar MCPs neste PC

Depois de preparar os ambientes:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\test_mcp.ps1
```

Em um PC limpo, este comando tambem cria os `.venv` e instala dependencias de teste:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\test_mcp.ps1 -InstallDevDependencies
```

O guia de maturidade e proximos passos fica em `docs/MCP_MATURIDADE_GUIA.md`.

Os testes tambem sobem os servidores MCP por stdio e usam um cliente real do SDK MCP para validar `initialize`, `list_tools` e uma chamada segura de ferramenta.

## Ver auditoria local dos MCPs

No Codex ou VS Code, use a ferramenta `mcp_audit_report` do MCP Ops/API para resumir os eventos locais dos dois MCPs.

Ela le os arquivos JSONL configurados por:

- `SISTEMA_PET_MCP_AUDIT_LOG`
- `SISTEMA_PET_FRONT_MCP_AUDIT_LOG`

## Depurar com MCP Inspector

O Inspector pode ser instalado globalmente:

```powershell
npm install -g @modelcontextprotocol/inspector
```

Frontend:

```powershell
mcp-inspector .\mcp\frontend_react_server\.venv\Scripts\python.exe -m frontend_react_mcp.main
```

Ops/API:

```powershell
mcp-inspector .\mcp\ops_api_server\.venv\Scripts\python.exe -m ops_api_mcp.main
```

Se o comando `mcp-inspector` nao aparecer no terminal atual, feche e abra o terminal do VS Code.
