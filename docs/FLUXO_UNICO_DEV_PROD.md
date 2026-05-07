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

### 4) `FLUXO_UNICO.bat prod-up`
Uso legado/local. Para producao real no servidor, prefira `bash scripts/deploy_producao_seguro.sh`.

### 5) `FLUXO_UNICO.bat status`
Use para: ver se os servicos estao de pe e saudaveis.

---

## Ordem certa (sempre igual)

1. `FLUXO_UNICO.bat check`
2. `FLUXO_UNICO.bat dev-up`
3. `FLUXO_UNICO.bat release-check`
4. **Se mexeu em qualquer arquivo dentro de `frontend/src`:** commitar apenas o codigo-fonte
   - Nao versionar `frontend/dist`
   - O build de producao deve gerar os arquivos em `runtime/frontend/dist`
   - Sem esse passo no deploy, a producao continua mostrando o codigo antigo
5. No servidor: `bash scripts/deploy_producao_seguro.sh`
   - Producao real via SSH: `ssh root@192.241.150.121 "cd /opt/petshop && bash scripts/deploy_producao_seguro.sh"`
   - Guia oficial com IP, health e validacoes: `docs/PRODUCAO_DEPLOY_SSH.md`
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

Para producao real, acessar por SSH direto no IP:

```
ssh root@192.241.150.121
```

No servidor de producao, o caminho padrao agora e:

```
cd /opt/petshop
bash scripts/deploy_producao_seguro.sh
```

Esse script:
- bloqueia se o Git estiver sujo
- atualiza o codigo para `origin/main`
- impede `frontend/dist` e `runtime` versionados
- gera o frontend em `runtime/frontend/dist`
- reconstrui o backend
- sobe `postgres`, `backend` e `nginx`
- valida `/health/watchdog` e `/api/health`
- termina falhando se o Git ficar sujo

---

## Assistente automatico (com confirmacao)

Se quiser que o sistema te guie e pergunte antes de cada passo importante, use:

- `ASSISTENTE_RELEASE.bat`

O que ele faz:
1. Prepara os 3 blocos de commit (higiene, fluxo, migrations).
2. Mostra os arquivos e pergunta se pode commitar cada bloco.
3. Roda `check` e `release-check` no final.
4. Pergunta: "Posso fazer push final?"
5. So faz push se voce confirmar.

---

## Resultado esperado

Seguindo esse fluxo, voce ganha:
- previsibilidade
- menos retrabalho
- menos risco de "funciona no dev e nao esta em producao"
- operacao mais simples no dia a dia
