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
Use para: subir producao pelo caminho seguro e padronizado.

### 5) `FLUXO_UNICO.bat status`
Use para: ver se os servicos estao de pe e saudaveis.

---

## Ordem certa (sempre igual)

1. `FLUXO_UNICO.bat check`
2. `FLUXO_UNICO.bat dev-up`
3. `FLUXO_UNICO.bat release-check`
4. `FLUXO_UNICO.bat prod-up`
5. `FLUXO_UNICO.bat status`

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
