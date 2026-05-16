# MCPs do Sistema Pet

Este diretorio contem os MCPs locais usados pelo VS Code e pelo Codex.

## Servidores

| Servidor | Caminho | Responsabilidade |
|---|---|---|
| `sistema-pet-frontend-react` | `mcp/frontend_react_server` | validacao e operacao do frontend React/Vite |
| `sistema-pet-ops-api` | `mcp/ops_api_server` | fluxo unico, API local, Docker DEV, campanhas e logs |

## Regra de seguranca

Ferramentas de leitura podem rodar normalmente. Ferramentas que sobem ambiente ou escrevem dados ficam limitadas ao ambiente local/DEV e devem ter travas claras.

`fluxo_prod_up` fica bloqueado por padrao e exige variavel de ambiente mais frase de confirmacao. Deploy remoto de producao nao e feito por estes MCPs.

## Testes

Pela raiz do projeto:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\test_mcp.ps1 -InstallDevDependencies
```

Depois da primeira instalacao de dependencias de teste:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\test_mcp.ps1
```
