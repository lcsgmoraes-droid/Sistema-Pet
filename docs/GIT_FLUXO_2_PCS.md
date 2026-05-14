# Fluxo Git para trabalhar em 2 PCs

Este projeto deve seguir branch por tarefa. A `main` fica limpa e estavel.

## Uma vez em cada computador

Depois de clonar ou atualizar o projeto, rode:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\git_setup_guardrails.ps1
```

Isso ativa os hooks locais que bloqueiam commit e push direto na `main`.

## Comecar uma tarefa

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\git_start_task.ps1 -Tipo feat -Nome "cadastro de pet"
```

O script faz:

- Confere se nao ha alteracoes soltas.
- Atualiza `main` com `origin/main`.
- Cria uma branch nova, por exemplo `feat/20260514-1015-cadastro-de-pet`.

## Fechar uma tarefa

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\git_finish_task.ps1 -Mensagem "Adiciona cadastro de pet" -Push
```

O script faz:

- Bloqueia commit se voce estiver na `main`.
- Mostra o que sera commitado.
- Bloqueia delecao acidental de arquivos protegidos.
- Roda validacao do fluxo.
- Cria o commit.
- Envia a branch para o GitHub.

Depois disso, abra o Pull Request no GitHub e faca o merge pela interface.

## No outro computador

Depois que o Pull Request for juntado, basta iniciar a proxima tarefa pelo mesmo script:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\git_start_task.ps1 -Tipo feat -Nome "proxima tarefa"
```

Ele atualiza a `main` antes de criar a branch nova.

## Saber se este PC precisa atualizar

Quando estiver em duvida se o outro computador subiu alguma novidade, rode:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\git_check_updates.ps1
```

O script consulta o GitHub e mostra:

- se a `main` deste PC precisa baixar commits novos;
- se a branch atual precisa baixar novidades;
- se a branch atual tem commits locais que ainda precisam subir.

Ele nao faz pull, push nem deploy sozinho. E apenas um aviso seguro para decidir o proximo passo.

No VS Code, tambem existe a tarefa:

```text
Git Seguro: Verificar atualizacoes
```

## Emergencia

Os hooks bloqueiam `main/master`, mas podem ser contornados manualmente. Use isso somente se voce tiver certeza e depois de autorizacao explicita:

```powershell
$env:ALLOW_MAIN_PUSH = "1"
git push origin main
Remove-Item Env:ALLOW_MAIN_PUSH
```

Para producao, continuam valendo as regras de `docs/FLUXO_UNICO_DEV_PROD.md`.
