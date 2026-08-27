# Entrega - integridade e RTO do backup

Data: 2026-08-27

## Problema tratado

O restore smoke existente provava que tabelas podiam ser restauradas, mas o
painel considerava o RTO comprovado apenas pela data do ultimo sucesso. A
evidencia nao dizia se o checksum tinha sido conferido nem quanto tempo a
recuperacao levou.

## Mudancas

- SHA-256 obrigatorio antes de iniciar qualquer restore.
- Duracao total do restore registrada em segundos.
- Evento de continuidade ampliado sem conteudo do banco ou segredo.
- RTO marcado como comprovado somente quando a evidencia e recente, o checksum
  foi validado e a duracao ficou dentro do objetivo interno.
- Painel `/ops` mostra duracao e integridade da ultima recuperacao.
- Testes cobrem evidencia completa, evidencia antiga incompleta e restore acima
  do objetivo.

## Seguranca

- O banco de origem e somente lido.
- A restauracao ocorre em container e volume descartaveis.
- Nao ha porta publicada nem copia de dados para o repositorio.
- Arquivos temporarios ficam fora do Git e sao removidos ao final.
- A entrega nao executa nem autoriza producao.

## Evidencia

O restore real em homologacao local aprovou checksum, 255 tabelas publicas,
`alembic_version`, duracao de 8 segundos e limpeza dos recursos temporarios.
Detalhes: `docs/homologacoes/2026-08-27-integridade-rto-backup.md`.
