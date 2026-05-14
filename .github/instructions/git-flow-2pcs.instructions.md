---
applyTo: "**"
---
# Fluxo Git para dois computadores

O Lucas trabalha no mesmo projeto em dois PCs. Mantenha o Git previsivel.

## Antes de editar

- Rode `git status --short --branch`.
- Se estiver em `main` ou `master`, crie branch de tarefa antes de alterar arquivos:
  `powershell -ExecutionPolicy Bypass -File .\scripts\git_start_task.ps1 -Tipo feat -Nome "nome da tarefa"`.
- Se ja estiver em uma branch de tarefa, continue nela.

## Ao finalizar

- Nunca commitar em `main` ou `master`.
- Nunca fazer push direto para `main` ou `master`.
- Para fechar uma tarefa, use:
  `powershell -ExecutionPolicy Bypass -File .\scripts\git_finish_task.ps1 -Mensagem "mensagem clara" -Push`.
- Abra Pull Request no GitHub e junte pela interface do GitHub.

## Depois do merge

- No outro PC, atualize a `main` antes de iniciar outra tarefa.
- O script `git_start_task.ps1` ja faz `fetch`, troca para `main`, executa `pull --ff-only` e cria a nova branch.

## Producao

- Este fluxo nao substitui as regras de producao.
- Antes de qualquer `git push origin main` ou SSH no servidor de producao, pedir autorizacao explicita ao Lucas.
