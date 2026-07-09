# Instrucoes permanentes para o Copilot neste repositorio

Estas regras existem porque o dono do projeto nao programa e precisa de operacao previsivel, simples e sem desvio.

## Fonte de verdade

Antes de agir, leia e siga obrigatoriamente:

- `.github/assistant-rules.json`
- `docs/FLUXO_UNICO_DEV_PROD.md`
- `README.md` (secao de fluxo unico)

## REGRA ABSOLUTA - NUNCA SUBIR PARA PRODUCAO SEM AUTORIZACAO EXPLICITA

**Antes de qualquer `git push origin main` ou qualquer comando SSH no servidor de producao (mlprohub.com.br / 192.241.150.121), o assistente DEVE:**

1. Parar o que esta fazendo
2. Perguntar em portugues simples: "Posso subir para producao agora? O que vai subir: [lista]"
3. Aguardar o Lucas dizer "sim" ou "pode subir"
4. SO ENTAO executar o deploy

**Esta regra nao tem excecoes. Nem urgencia, nem simplicidade da mudanca justificam pular esta etapa.**

---

## Regra principal

Nunca sair do fluxo unico DEV -> PROD.

Para trabalho diario em branch, use a sequencia enxuta:

1. `git status --short --branch`
2. Se estiver em `main`/`master`, abrir branch com `scripts/git_start_task.ps1`
3. Se ja estiver em branch de tarefa, continuar nela
4. Rodar testes focados no que foi alterado
5. Fechar com `scripts/git_finish_task.ps1 -Mensagem "mensagem clara" -Push`

Para release/deploy, use a sequencia completa:

1. `FLUXO_UNICO.bat check`
2. `FLUXO_UNICO.bat dev-up` quando precisar validar o ambiente local
3. `FLUXO_UNICO.bat release-check`
4. **Se alterou arquivos em `frontend/src`: rodar `npm run build` dentro da pasta `frontend`; nao commitar `frontend/dist`**
5. Abrir/atualizar Pull Request e juntar pela interface do GitHub quando os checks passarem
6. **DEPLOY NO SERVIDOR REMOTO (mlprohub.com.br / 192.241.150.121): preferir o usuario operacional `petdeploy` e rodar `ssh -i ~/.ssh/mlprohub_codex_deploy -o IdentitiesOnly=yes -o BatchMode=yes petdeploy@192.241.150.121 "sudo -n /usr/local/sbin/petshop-deploy-producao"`. Esse wrapper root-owned executa o script oficial `scripts/deploy_producao_seguro.sh`, que faz pull, build frontend, rebuild backend/worker, migrations e health. `root@192.241.150.121` fica apenas como fallback operacional autorizado.**
7. `FLUXO_UNICO.bat status` mostra containers locais; para ver estado real da producao, checar via SSH

Para update OTA do app mobile via EAS, depois da autorizacao do Lucas, publicar
a mesma versao nos canais `production` e `preview`, salvo excecao combinada
explicitamente. Validar os dois com `update:list` e `channel:view`, porque
aparelhos de teste podem estar instalados no canal `preview`.

## Comunicacao com o usuario

- Sempre escrever em portugues simples, sem jargao.
- Explicar o que vai fazer antes de alterar arquivos.
- Entregar resumo curto com proximo passo claro.
- Nao assumir conhecimento tecnico do usuario.

## Guardrails obrigatorios

- Nao versionar arquivos locais (backups, dumps, temporarios, certificados).
- Nao enviar dados de DEV para producao.
- Nao pular validacao de release.
- Nao corrigir em producao manualmente sem refletir no Git.
- **Sempre rodar `npm run build` (na pasta `frontend`) antes de release/deploy quando houver mudancas no frontend. Nao commitar `frontend/dist`; o deploy seguro gera `runtime/frontend/dist` no servidor.**
- **NUNCA usar `git add -A` sem antes verificar `git status --short` e checar se ha arquivos de infraestrutura sendo deletados (linhas com ` D` ou `D `). Arquivos protegidos: `docker-compose.*.yml`, `.env.*`, `scripts/*.ps1`, `.github/`, `docs/FLUXO_UNICO_DEV_PROD.md`. Se aparecerem como deletados: restaurar com `git checkout HEAD -- <arquivo>` antes de commitar.**
- **PRODUCAO REAL E REMOTA: `mlprohub.com.br` esta hospedado no servidor DigitalOcean (IP 192.241.150.121). O `prod-up` local NAO afeta a producao real. Para deployar em producao: primeiro o PR deve estar mergeado na `main`; depois usar `petdeploy@192.241.150.121` com `sudo -n /usr/local/sbin/petshop-deploy-producao`. NUNCA usar `git pull` + `docker restart` como deploy de codigo; o backend fica DENTRO DA IMAGEM DOCKER e precisa do script seguro com rebuild.**

## Padronizacao de numeros e moeda (OBRIGATORIO)

**Formato brasileiro obrigatorio em todo o sistema:**
- Ponto como separador de milhar: `17.555,25`
- Virgula como separador decimal: `0,99`
- NUNCA usar `value.toFixed(2).replace('.', ',')` - isso nao inclui separador de milhar.

**Funcoes utilitarias - sempre usar:**
- `formatBRL(value)` -> `"17.555,25"` (sem prefixo)
- `formatMoneyBRL(value)` -> `"R$ 17.555,25"` (com prefixo)
- Arquivo: `frontend/src/utils/formatters.js`

**Inputs monetarios - sempre usar `CurrencyInput`:**
- Comportamento de virgula fixa: digitos entram da direita para esquerda
- Ex: digitar 5 -> 0,05 -> 0,55 -> 5,55 -> 55,55
- Suporta selecionar tudo e digitar para substituir
- Mostra separador de milhar automaticamente: `17.555,25`
- Arquivo: `frontend/src/components/CurrencyInput.jsx`

**Ao encontrar qualquer numero formatado errado no sistema (sem separador de milhar), corrigir usando `formatBRL()` ou `CurrencyInput`.**

## Em caso de conflito

Se houver ambiguidade, priorize seguranca, rastreabilidade e simplicidade operacional.
