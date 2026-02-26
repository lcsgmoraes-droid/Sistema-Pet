# Instrucoes permanentes para o Copilot neste repositorio

Estas regras existem porque o dono do projeto nao programa e precisa de operacao previsivel, simples e sem desvio.

## Fonte de verdade

Antes de agir, leia e siga obrigatoriamente:

- `.github/assistant-rules.json`
- `docs/FLUXO_UNICO_DEV_PROD.md`
- `README.md` (secao de fluxo unico)

## Regra principal

Nunca sair do fluxo unico DEV -> PROD.

Use sempre esta sequencia:

1. `FLUXO_UNICO.bat check`
2. `FLUXO_UNICO.bat dev-up`
3. `FLUXO_UNICO.bat release-check`
4. **Se alterou arquivos em `frontend/src`: rodar `npm run build` dentro da pasta `frontend` e incluir o `dist` no commit**
5. `FLUXO_UNICO.bat prod-up`
6. `FLUXO_UNICO.bat status`

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

## Em caso de conflito

Se houver ambiguidade, priorize seguranca, rastreabilidade e simplicidade operacional.
