# Instrucoes permanentes para o Copilot neste repositorio

Estas regras existem porque o dono do projeto nao programa e precisa de operacao previsivel, simples e sem desvio.

## Fonte de verdade

Antes de agir, leia e siga obrigatoriamente:

- `.github/assistant-rules.json`
- `docs/FLUXO_UNICO_DEV_PROD.md`
- `README.md` (secao de fluxo unico)

## REGRA ABSOLUTA — NUNCA SUBIR PARA PRODUCAO SEM AUTORIZACAO EXPLICITA

**Antes de qualquer `git push origin main` ou qualquer comando SSH no servidor de producao (mlprohub.com.br / 192.241.150.121), o assistente DEVE:**

1. Parar o que esta fazendo
2. Perguntar em portugues simples: "Posso subir para producao agora? O que vai subir: [lista]"
3. Aguardar o Lucas dizer "sim" ou "pode subir"
4. SÓ ENTAO executar o deploy

**Esta regra nao tem excecoes. Nem urgencia, nem simplicidade da mudanca justificam pular esta etapa.**

---

## Regra principal

Nunca sair do fluxo unico DEV -> PROD.

Use sempre esta sequencia:

1. `FLUXO_UNICO.bat check`
2. `FLUXO_UNICO.bat dev-up`
3. `FLUXO_UNICO.bat release-check`
4. **Se alterou arquivos em `frontend/src`: rodar `npm run build` dentro da pasta `frontend` e incluir o `dist` no commit com `git add -f frontend/dist`**
5. `git push origin main`
6. **DEPLOY NO SERVIDOR REMOTO (mlprohub.com.br / 192.241.150.121): via MCP SSH (conexao ID 1 ou nome mlprohub-producao), rodar: `cd /opt/petshop && git pull origin main && docker restart petshop-prod-nginx`. Se houver mudancas no backend (qualquer arquivo dentro de `backend/`): OBRIGATORIO reconstruir a imagem antes de reiniciar: `docker compose -f docker-compose.prod.yml build backend && docker compose -f docker-compose.prod.yml up -d backend` — um simples `docker restart` NAO e suficiente porque o codigo fica dentro da imagem Docker, nao em volume montado.**
7. `FLUXO_UNICO.bat status` (mostra containers locais; para ver estado real da producao, checar via SSH)

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
- **Sempre rodar `npm run build` (na pasta `frontend`) antes de qualquer deploy quando houver mudancas no frontend. O nginx de producao serve arquivos estaticos da pasta `dist` — sem build, o codigo novo nao aparece em producao.**
- **NUNCA usar `git add -A` sem antes verificar `git status --short` e checar se ha arquivos de infraestrutura sendo deletados (linhas com ` D` ou `D `). Arquivos protegidos: `docker-compose.*.yml`, `.env.*`, `scripts/*.ps1`, `.github/`, `docs/FLUXO_UNICO_DEV_PROD.md`. Se aparecerem como deletados: restaurar com `git checkout HEAD -- <arquivo>` antes de commitar.**
- **PRODUCAO REAL E REMOTA: `mlprohub.com.br` esta hospedado no servidor DigitalOcean (IP 192.241.150.121). O `prod-up` local NAO afeta a producao real. Para deployar em producao: fazer `git push origin main` e depois SSH no servidor via MCP (ID 1) e rodar `cd /opt/petshop && git pull origin main && docker restart petshop-prod-nginx`. Se houver mudancas no backend: NUNCA usar apenas `docker restart petshop-prod-backend` — o codigo do backend fica DENTRO DA IMAGEM DOCKER (nao em volume), entao e obrigatorio reconstruir: `docker compose -f docker-compose.prod.yml build backend && docker compose -f docker-compose.prod.yml up -d backend`.**

## Em caso de conflito

Se houver ambiguidade, priorize seguranca, rastreabilidade e simplicidade operacional.
