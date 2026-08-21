# Fluxo Unico DEV -> PROD (guia simples)

Este arquivo foi feito para quem **nao programa**.

Objetivo: trabalhar sem bagunca e sem perder mudancas entre DEV e producao.

---

## O que voce testou agora (e estava certo)

Quando voce rodou a tarefa **Fluxo: 1) Check**, ela mostrou erro.

Isso foi **correto**: o sistema detectou um problema real e bloqueou para proteger seu ambiente.

No seu caso, o bloqueio foi por "multiplas heads de migration" (duas linhas de evolucao do banco ao mesmo tempo).

---

## O que cada comando faz (em portugues simples)

### 1) `FLUXO_UNICO.bat check`
Use para: fazer uma checagem geral rapida.

Ele verifica:
- se tem problema no Git
- se tem arquivo local indevido no repositorio
- se tem conflito estrutural de banco

Se der erro: ele esta te protegendo.

### 2) `FLUXO_UNICO.bat dev-up`
Use para: subir ambiente de desenvolvimento (onde voce mexe e testa com seguranca).

### 3) `FLUXO_UNICO.bat release-check`
Use para: validar se esta tudo pronto para subir em producao.

Regra: **nunca pular este passo**.

### 3.1) `FLUXO_UNICO.bat dev-down`
Use para: parar somente os containers do ambiente DEV local.

O atalho antigo `PARAR_TUDO.bat` encaminha para esse mesmo comando.

### 4) `FLUXO_UNICO.bat prod-up`
Uso legado/local. Para producao real no servidor, prefira `bash scripts/deploy_producao_seguro.sh`.

### 5) `FLUXO_UNICO.bat status`
Use para: ver se os servicos estao de pe e saudaveis.

---

## Rotina diaria enxuta

Use esta rotina quando estiver desenvolvendo em uma branch de tarefa:

1. `git status --short --branch`
2. Se estiver em `main` ou `master`, iniciar branch com:
   `powershell -ExecutionPolicy Bypass -File .\scripts\git_start_task.ps1 -Tipo feat -Nome "nome da tarefa"`
3. Se ja estiver em branch de tarefa, continuar nela.
4. Rodar apenas os testes focados no que foi alterado.
5. Antes de fechar/enviar a branch, usar:
   `powershell -ExecutionPolicy Bypass -File .\scripts\git_finish_task.ps1 -Mensagem "mensagem clara" -Push`

Regra pratica: verificar a `main` no inicio de uma nova tarefa e antes de fechar
a branch. Nao precisa repetir essa verificacao a cada micro-etapa se voce
continua na mesma branch e no mesmo computador.

## Release e producao

1. `FLUXO_UNICO.bat check`
2. `FLUXO_UNICO.bat dev-up` quando precisar validar o ambiente local
3. `FLUXO_UNICO.bat release-check`
4. **Se mexeu em qualquer arquivo dentro de `frontend/src`:** commitar apenas o codigo-fonte
   - Nao versionar `frontend/dist`
   - O build de producao deve gerar os arquivos em `runtime/frontend/dist`
   - Sem esse passo no deploy, a producao continua mostrando o codigo antigo
5. Executar: `powershell -ExecutionPolicy Bypass -File .\scripts\deploy_producao_remoto.ps1`
   - O destino preferencial e sempre `petdeploy@corepet.com.br`; nao copiar IP para comandos operacionais.
   - O launcher, o wrapper remoto e o script oficial validam o destino antes de alterar codigo ou banco.
   - `root@corepet.com.br` fica apenas como fallback operacional autorizado.
   - Guia oficial com dominio, health e validacoes: `docs/PRODUCAO_DEPLOY_SSH.md`
6. `FLUXO_UNICO.bat status`

---

## Se aparecer erro, o que significa

### "Alteracoes locais"
Significa: ainda existem arquivos alterados no seu computador.

Acao: organizar essas mudancas antes de release.

### "Arquivos proibidos rastreados"
Significa: entrou arquivo local indevido no Git (backup, dump, temporario etc).

Acao: limpar do Git (sem apagar seus dados locais).

### "Multiplas heads de migration"
Significa: duas evolucoes de banco estao em paralelo e precisam ser unificadas.

Acao: fazer correcao de merge de migrations antes de producao.

---

## Regra de ouro

Se `release-check` falhar, **nao subir producao**.

## Importacao de dados de uma nova empresa

Importacao de CSV nao faz parte do deploy. Ela possui um fluxo proprio para
evitar mistura entre empresas:

1. usar `scripts/importar_simplesvet_seguro.ps1` em modo `Simular`;
2. conferir empresa, usuario, contagens, rejeicoes e `plan_id`;
3. aplicar somente o plano gerado, ainda valido e com os mesmos arquivos;
4. em producao, fazer backup e obter autorizacao explicita antes de aplicar.

O procedimento completo esta em `docs/IMPORTACAO_SIMPLESVET_SEGURA.md`.

---

## Regra critica de deploy do backend no servidor

O codigo Python do backend fica **dentro da imagem Docker** (nao em uma pasta montada).

Isso significa:
- `git pull` no servidor: atualiza os arquivos no disco — mas o container ainda roda o codigo antigo
- `docker restart petshop-prod-backend`: reinicia o mesmo container com o mesmo codigo antigo
- **Para aplicar mudancas no backend, e obrigatorio reconstruir a imagem:**

```
docker compose -f docker-compose.prod.yml build backend
docker compose -f docker-compose.prod.yml up -d backend
```

So o frontend e diferente: o nginx serve os arquivos estaticos gerados em `runtime/frontend/dist`, fora da arvore versionada. O Git guarda o codigo-fonte; o build de producao deve gerar/copiar os artefatos para `runtime/frontend/dist` e recriar/reiniciar o `nginx`.

---

## Deploy seguro no servidor

Para producao real, acessar por SSH direto no IP usando o usuario operacional:

```
ssh -i ~/.ssh/mlprohub_codex_deploy -o IdentitiesOnly=yes petdeploy@corepet.com.br
```

No servidor de producao, o caminho padrao com root-owned wrapper e:

```
sudo -n /usr/local/sbin/petshop-deploy-producao
```

Esse script:
- bloqueia se o Git estiver sujo
- bloqueia antes de atualizar o codigo se o Node.js do host nao atender `>=20.19.4` ou `>=22.12.0`
- atualiza o codigo para `origin/main`
- impede `frontend/dist` e `runtime` versionados
- gera o frontend em `runtime/frontend/dist`
- reconstrui o backend
- sobe `postgres`, `backend` e `nginx`
- valida `/health/watchdog` e `/api/health`
- termina falhando se o Git ficar sujo

### Runtime Node.js de producao

- O build frontend de producao requer Node.js 22 LTS no host de deploy.
- O script `scripts/deploy_producao_seguro.sh` bloqueia o deploy antes de atualizar o codigo quando o Node local nao atende `>=20.19.4` ou `>=22.12.0`.
- A producao nao deve voltar para Node 18 enquanto o frontend estiver em Vite 8.
- Atualizacao de Node no servidor de producao exige autorizacao explicita do Lucas antes de qualquer comando com `sudo` ou mudanca no host.

---

## Atalhos antigos de release

`ASSISTENTE_RELEASE.bat` e `ASSISTENTE_RELEASE_EXECUTAR.bat` foram bloqueados.
Eles preparavam tres blocos historicos de alteracoes que ja foram concluidos e
nao representam o trabalho atual.

O fluxo Git atual e sempre o descrito em `CONTRIBUTING.md`: abrir uma branch com
`scripts/git_start_task.ps1`, validar e fechar com `scripts/git_finish_task.ps1`.

---

## Resultado esperado

Seguindo esse fluxo, voce ganha:
- previsibilidade
- menos retrabalho
- menos risco de "funciona no dev e nao esta em producao"
- operacao mais simples no dia a dia
