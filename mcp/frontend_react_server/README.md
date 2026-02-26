# MCP Frontend React - Sistema Pet

Servidor MCP para automação do frontend React (Vite) do Sistema Pet.

## Objetivo

Entregar ferramentas para:

- validar status do frontend
- executar build de produção e build de desenvolvimento
- realizar smoke de inicialização `npm run dev`
- validar disponibilidade HTTP da aplicação
- validar resposta da rota de login multitenant da API (do ponto de vista do front)

## Arquitetura

- `frontend_react_mcp/server.py`: ferramentas MCP
- `frontend_react_mcp/services/frontend_service.py`: execução segura de scripts npm
- `frontend_react_mcp/services/http_service.py`: validações HTTP (front e API)
- `frontend_react_mcp/config.py`: paths, timeout e limites
- `frontend_react_mcp/models.py`: respostas padronizadas

## Instalação (ambiente isolado recomendado)

```bash
cd mcp/frontend_react_server
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

## Execução

```bash
frontend-react-mcp
```

ou

```bash
python -m frontend_react_mcp.main
```

## Ferramentas MCP disponíveis

- `front_status`
- `front_build_check`
- `front_build_dev_check`
- `front_dev_smoke`
- `front_http_check`
- `front_api_auth_smoke`

## Exemplo de configuração MCP no VS Code

```json
{
  "mcpServers": {
    "sistema-pet-frontend-react": {
      "command": "python",
      "args": ["-m", "frontend_react_mcp.main"],
      "cwd": "c:/Users/Lucas/OneDrive/Área de Trabalho/Programa/Sistema Pet/mcp/frontend_react_server"
    }
  }
}
```
