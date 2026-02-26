# MCP Ops/API - Sistema Pet

Servidor MCP para operar e validar o Sistema Pet no fluxo oficial DEV -> PROD.

## Objetivo

Este servidor entrega ferramentas MCP para:

- executar o fluxo único (`check`, `dev-up`, `release-check`, `prod-up`, `status`)
- validar saúde de API
- validar rota de login multitenant
- validar permissões que liberam as abas de Cadastros e Financeiro

## Arquitetura

- `ops_api_mcp/server.py`: expõe ferramentas MCP
- `ops_api_mcp/services/command_service.py`: execução segura de comandos PowerShell
- `ops_api_mcp/services/api_service.py`: chamadas HTTP e validações de autenticação
- `ops_api_mcp/config.py`: resolução de caminhos e limites
- `ops_api_mcp/models.py`: modelos de resposta padronizados

## Instalação

Na raiz deste módulo:

```bash
cd mcp/ops_api_server
pip install -e .
```

## Execução local

```bash
ops-api-mcp
```

ou

```bash
python -m ops_api_mcp.main
```

## Ferramentas MCP disponíveis

- `fluxo_check`
- `fluxo_dev_up`
- `fluxo_release_check`
- `fluxo_prod_up`
- `fluxo_status`
- `api_health_check`
- `api_auth_route_smoke`
- `auth_validate_tabs_permissions`

## Exemplo de configuração no cliente MCP

```json
{
  "mcpServers": {
    "sistema-pet-ops-api": {
      "command": "python",
      "args": ["-m", "ops_api_mcp.main"],
      "cwd": "c:/Users/Lucas/OneDrive/Área de Trabalho/Programa/Sistema Pet/mcp/ops_api_server"
    }
  }
}
```

## Regras de segurança operacional

- só executa ações permitidas do fluxo único
- usa timeout por comando
- limita tamanho de saída para evitar vazamento e travamento
- não grava segredo em log de retorno
