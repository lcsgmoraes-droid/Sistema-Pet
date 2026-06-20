---
applyTo: "**"
---
# Fluxo Git simples e seguro

O Lucas hoje trabalha principalmente em um PC, mas o fluxo continua preparado
para dois computadores. Mantenha o Git previsivel sem repetir checagens a cada
micro-etapa.

## Antes de editar

- Rode `git status --short --branch`.
- Se estiver em `main` ou `master`, crie branch de tarefa antes de alterar arquivos:
  `powershell -ExecutionPolicy Bypass -File .\scripts\git_start_task.ps1 -Tipo feat -Nome "nome da tarefa"`.
- Se ja estiver em uma branch de tarefa, continue nela.
- Confira a `main` no inicio de uma nova tarefa e antes de fechar/enviar a
  branch. Nao repita essa checagem a cada passo pequeno na mesma branch.

## Ao finalizar

- Nunca commitar em `main` ou `master`.
- Nunca fazer push direto para `main` ou `master`.
- Para fechar uma tarefa, use:
  `powershell -ExecutionPolicy Bypass -File .\scripts\git_finish_task.ps1 -Mensagem "mensagem clara" -Push`.
- Abra Pull Request no GitHub e junte pela interface do GitHub.

## Depois do merge

- Atualize a `main` antes de iniciar outra tarefa depois de um PR mergeado.
- O script `git_start_task.ps1` ja faz `fetch`, troca para `main`, executa `pull --ff-only` e cria a nova branch.

## Producao

- Este fluxo nao substitui as regras de producao.
- Antes de qualquer `git push origin main` ou SSH no servidor de producao, pedir autorizacao explicita ao Lucas.
