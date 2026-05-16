# MCP local do Sistema Pet

Este projeto tem dois servidores MCP locais:

- `sistema-pet-frontend-react`: ferramentas para validar o frontend React.
- `sistema-pet-ops-api`: ferramentas para validar fluxo, API e operacao.

## Preparar neste PC

Os ambientes virtuais ficam dentro de `mcp/*/.venv` e nao entram no Git.

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
