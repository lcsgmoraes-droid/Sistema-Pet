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

## Padrao de trabalho

- Fazer mudancas pequenas e focadas.
- Explicar em portugues simples o que sera alterado antes de editar.
- Validar o que for possivel antes de encerrar.
- Nao commitar `.env`, dumps, backups, certificados, `node_modules`, builds locais indevidos ou arquivos temporarios.
