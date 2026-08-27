# Regras para assistentes neste repositorio

Estas regras existem para manter o Sistema Pet organizado e seguro. Hoje o Lucas
trabalha principalmente em um computador, entao a checagem da `main` deve ser
feita nos momentos certos, sem virar repeticao a cada micro-etapa.

## Fluxo Git obrigatorio para codigo

- Antes de alterar arquivos, verificar `git status --short --branch`.
- Se estiver em `main` ou `master` e a tarefa exigir edicao, criar uma branch de tarefa antes de mexer:
  `powershell -ExecutionPolicy Bypass -File .\scripts\git_start_task.ps1 -Tipo feat -Nome "nome da tarefa"`.
- Se ja estiver em uma branch de tarefa, continuar nela.
- Verificar a `main` no inicio de uma nova tarefa e antes de fechar/enviar a branch.
  Durante a mesma tarefa, nao repetir essa verificacao a cada passo se a branch
  nao mudou e nao houve troca de computador.
- Nunca fazer commit direto em `main` ou `master`.
- Nunca fazer push direto para `main` ou `master`; usar branch e Pull Request no GitHub.
- Ao terminar uma tarefa, usar:
  `powershell -ExecutionPolicy Bypass -File .\scripts\git_finish_task.ps1 -Mensagem "mensagem clara" -Push`.
- Depois que o Pull Request for juntado no GitHub, atualizar a `main` antes de
  comecar nova tarefa. O script `git_start_task.ps1` ja faz isso ao criar a
  proxima branch.

## Producao continua protegida

- Estas regras nao autorizam deploy de producao.
- Antes de qualquer `git push origin main` ou comando no servidor de producao, pedir autorizacao explicita ao Lucas em portugues simples.
- Seguir tambem `.github/assistant-rules.json`, `.github/copilot-instructions.md` e `docs/FLUXO_UNICO_DEV_PROD.md`.

## Controle direto do navegador

- Para operar sites como Play Console, App Store Connect, Expo e o ERP, usar
  primeiro o controlador direto do Chrome conectado a aba e ao perfil ja
  autenticados pelo Lucas.
- Nao usar o controle geral do Windows enquanto o controlador direto do Chrome
  estiver disponivel para a tarefa.
- Quando houver mais de uma janela, perfil ou sessao do Chrome, identificar a
  janela correta pelo titulo e pela URL retornados pelo controlador direto e
  validar novamente depois de navegacoes relevantes.
- Nao abrir nem trocar para outro perfil se o Lucas indicou uma sessao ja
  autenticada.
- Usar o controle geral do Windows apenas quando o alvo nao puder ser operado
  pelo controlador direto do navegador. Antes desse fallback, explicar o motivo
  ao Lucas e pedir autorizacao.

## Fluxo obrigatorio do app mobile

- Antes de gerar novo APK/AAB/IPA, enviar para uma loja ou configurar credenciais
  de loja, verificar o historico do EAS e classificar a mudanca como OTA ou nativa.
- Se a mudanca estiver limitada a JavaScript/TypeScript, assets compativeis e
  backend, preservar a versao/runtime dos binarios instalados e usar o fluxo ja
  existente:
  `eas update --channel production --platform all --environment production`.
- Nesse caso, nao incrementar `version`, `runtimeVersion`, `versionCode` ou
  `buildNumber`, nao criar build de loja e nao abrir fluxo de Service Account.
- Nao executar nem aceitar automaticamente `expo install --fix` durante uma
  OTA. Recomendacoes do Expo Doctor que atualizem dependencias nativas devem ser
  tratadas em uma tarefa separada de release nativa.
- Novo build e submissao as lojas so sao cabiveis quando houver mudanca nativa,
  como dependencia nativa, plugin, permissao, pasta `android`/iOS ou runtime
  realmente incompativel. Explicar a evidencia ao Lucas antes de trocar de fluxo.
- Se houver duvida, consultar `docs/GUIA_RELEASE_APP_MOBILE_EAS.md`, executar
  `eas build:list`, `eas update:list` e comparar o fingerprint com os binarios
  ativos antes de agir.
- Estado verificado nas lojas em 2026-08-27: iOS e Android estao publicados.
  Nao substituir os binarios/revisoes atuais sem autorizacao especifica para
  uma nova versao nativa.

## Padrao de trabalho

- Fazer mudancas pequenas e focadas.
- Explicar em portugues simples o que sera alterado antes de editar.
- Validar o que for possivel antes de encerrar.
- Nao commitar `.env`, dumps, backups, certificados, `node_modules`, builds locais indevidos ou arquivos temporarios.
