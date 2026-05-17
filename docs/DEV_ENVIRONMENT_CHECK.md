# Check seguro de ambiente DEV

Use este check quando abrir o projeto em um PC novo, depois de atualizar a
`main`, ou antes de investigar erro local de setup.

## Bootstrap de PC novo

Para preparar um PC novo com um comando, primeiro veja o plano sem executar:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap_dev_environment.ps1 -DryRun
```

Depois execute o bootstrap:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap_dev_environment.ps1
```

Modo seguro sem baixar pacotes, util para conferencia offline:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap_dev_environment.ps1 -NoNetwork
```

Saida JSON para automacao:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap_dev_environment.ps1 -DryRun -Json
```

O bootstrap chama o check seguro, cria o `.venv` do backend quando faltar,
instala dependencias do backend, roda `npm ci` no frontend e executa o setup dos
MCPs locais. Ele nao cria nem imprime secrets.

## Comando principal

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check_dev_environment.ps1
```

Modo sem rede, bom para diagnostico rapido:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check_dev_environment.ps1 -NoNetwork
```

Saida JSON para automacao ou auditoria local:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check_dev_environment.ps1 -Json -NoNetwork
```

Modo estrito, para falhar quando houver erro critico:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check_dev_environment.ps1 -Strict
```

## O que ele valida

- Git, Python, Node.js, npm, Docker, GitHub CLI e SSH no `PATH`.
- Estrutura essencial do repositorio.
- Existencia do arquivo `.env.development`, sem imprimir valores.
- Chaves esperadas do `.env.development`, mostrando apenas nomes faltantes.
- Estado da branch atual e quantidade de alteracoes locais.
- Autenticacao do GitHub CLI, exceto quando usar `-NoNetwork`.
- Docker daemon e Docker Compose.
- `.venv` do backend, `node_modules` do frontend e `.venv` dos MCPs.

## Regra de seguranca

O script nao imprime valores de variaveis como `DATABASE_URL`,
`JWT_SECRET_KEY`, `SMTP_PASSWORD`, tokens ou webhooks. Quando precisar orientar
correcao, ele mostra apenas o nome da variavel ou o arquivo esperado.

Nao cole secrets no chat. Se faltar uma variavel real, configure no arquivo
local ou no ambiente seguro correspondente.

## Como interpretar

- `OK`: item pronto.
- `WARNING`: algo falta, mas o diagnostico pode continuar.
- `ERROR`: item essencial ausente ou repositorio invalido.
- `SKIPPED`: check pulado por falta de ferramenta ou por `-NoNetwork`.

## Correcoes comuns

| Aviso | Como corrigir |
|---|---|
| `.env.development nao encontrado` | Criar o arquivo a partir de `.env.example` ou usar as variaveis do `docker-compose.local-dev.yml`. |
| `GitHub CLI nao esta autenticado` | Rodar `gh auth login --hostname github.com --web --git-protocol https --scopes repo,workflow`. |
| `Docker daemon nao respondeu` | Abrir o Docker Desktop e aguardar ficar `Running`. |
| `frontend/node_modules nao encontrado` | Rodar `npm install` dentro de `frontend` quando for trabalhar no frontend. |
| `MCP venvs incompletos` | Rodar `powershell -ExecutionPolicy Bypass -File .\scripts\setup_mcp_local.ps1`. |
| `Branch tem alteracoes locais` | Finalizar a tarefa com `scripts/git_finish_task.ps1` ou registrar o que ficou pendente. |

