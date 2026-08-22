# Instrucoes permanentes para o Copilot neste repositorio

Estas regras existem porque o dono do projeto nao programa e precisa de operacao previsivel, simples e sem desvio.

## Fonte de verdade

Antes de agir, leia e siga obrigatoriamente:

- `.github/assistant-rules.json`
- `docs/FLUXO_UNICO_DEV_PROD.md`
- `README.md` (secao de fluxo unico)

## REGRA ABSOLUTA - NUNCA SUBIR PARA PRODUCAO SEM AUTORIZACAO EXPLICITA

**Antes de qualquer `git push origin main` ou qualquer comando SSH no servidor de producao (`corepet.com.br`), o assistente DEVE:**

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
6. **DEPLOY NO SERVIDOR REMOTO: usar `powershell -ExecutionPolicy Bypass -File .\scripts\deploy_producao_remoto.ps1`. O launcher conecta em `petdeploy@corepet.com.br`; o wrapper e o script oficial validam novamente se o host corresponde ao DNS antes de alterar codigo ou banco. A validacao final confere o commit servido pelo proprio dominio. O usuario `root@corepet.com.br` fica apenas como fallback operacional autorizado.**
7. `FLUXO_UNICO.bat status` mostra containers locais; para ver estado real da producao, checar via SSH

## Comunicacao com o usuario

- Sempre escrever em portugues simples, sem jargao.
- Explicar o que vai fazer antes de alterar arquivos.
- Entregar resumo curto com proximo passo claro.
- Nao assumir conhecimento tecnico do usuario.

## Guardrails obrigatorios

- Nao versionar arquivos locais (backups, dumps, temporarios, certificados).
- Nao enviar dados de DEV para producao.
- Nao versionar CSVs, planos ou relatorios de importacao; usar `runtime/importacoes-simplesvet/`.
- Nao pular validacao de release.
- Nao corrigir em producao manualmente sem refletir no Git.
- **Sempre rodar `npm run build` (na pasta `frontend`) antes de release/deploy quando houver mudancas no frontend. Nao commitar `frontend/dist`; o deploy seguro gera `runtime/frontend/dist` no servidor.**
- **NUNCA usar `git add -A` sem antes verificar `git status --short` e checar se ha arquivos de infraestrutura sendo deletados (linhas com ` D` ou `D `). Arquivos protegidos: `docker-compose.*.yml`, `.env.*`, `scripts/*.ps1`, `.github/`, `docs/FLUXO_UNICO_DEV_PROD.md`. Se aparecerem como deletados: restaurar com `git checkout HEAD -- <arquivo>` antes de commitar.**
- **PRODUCAO REAL E REMOTA: a fonte de verdade do destino e o DNS de `corepet.com.br`, nunca um IP copiado em documentacao. O `prod-up` local NAO afeta a producao real. Primeiro o PR deve estar mergeado na `main`; depois usar `scripts/deploy_producao_remoto.ps1`. NUNCA usar `git pull` + `docker restart` como deploy de codigo; o backend fica DENTRO DA IMAGEM DOCKER e precisa do script seguro com rebuild.**

## Atualizacao do app mobile: OTA antes de lojas

- O caminho padrao para mudancas somente em `app-mobile/src`, JavaScript,
  TypeScript, assets compativeis e backend e o EAS Update para as duas
  plataformas:
  `eas update --channel production --platform all --environment production`.
- Antes de qualquer build/submissao, conferir `eas build:list` e
  `eas update:list` e ler `docs/GUIA_RELEASE_APP_MOBILE_EAS.md`.
- Em OTA, manter a versao e o runtime dos binarios ativos. Nao incrementar
  `version`, `runtimeVersion`, `versionCode` ou `buildNumber`, nao acessar lojas
  e nao criar credenciais de submissao.
- Nao aplicar `expo install --fix` automaticamente durante uma OTA. Qualquer
  recomendacao que atualize dependencia nativa vira uma tarefa separada de
  release nativa.
- Somente usar EAS Build/Submit quando houver necessidade nativa comprovada
  (dependencia, plugin, permissao, codigo nativo ou runtime incompativel) e
  explicar essa evidencia ao Lucas antes de mudar o fluxo.
- Estado em 2026-08-22: iOS publicado e Android em aprovacao. Nao substituir a
  revisao/binario atual por iniciativa propria.

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
