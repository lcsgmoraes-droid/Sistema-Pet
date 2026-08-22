# Deploy: guia atual

<!-- LEGACY_DOCUMENT_REDIRECT -->

Este nome foi mantido para nao quebrar favoritos ou referencias antigas.

O procedimento anterior foi descontinuado porque continha dominio, comandos de
servidor e passos manuais que nao representam mais a producao atual.

Use somente:

- `docs/PRODUCAO_DEPLOY_SSH.md` para o deploy real;
- `docs/PRODUCAO_ROLLBACK_CHECKLIST.md` para a verificacao antes do deploy;
- `docs/PRODUCAO_BACKUP_RESTORE_TESTE.md` para backup e restore;
- `docs/INDICE_OPERACIONAL.md` para localizar os demais guias.

O deploy oficial e iniciado por `scripts/deploy_producao_remoto.ps1` e continua
exigindo autorizacao explicita antes de acessar producao.
