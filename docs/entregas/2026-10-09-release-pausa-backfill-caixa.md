# Publicação: pausa para o backfill de caixa

Quando o diff do commit anterior para o novo inclui
`zzzk20261009a1_caixa_recebimentos.py`, o deploy oficial pausa `backend`,
`worker-bling` e `worker-catalogo` depois do build e da confirmação do PostgreSQL,
antes do backup e das migrations. Nginx e PostgreSQL continuam ativos. Isso evita
recebimentos gravados pelo código antigo sem `caixa_id` depois do backfill.

Os escritores voltam no passo normal `subir_servicos`, após migrations e guard RLS.
A condição não se aplica a outras migrations ou atualizações comuns.

Se houver falha enquanto os escritores estiverem pausados, o script preserva
`DEPLOY_LOCK_FILE` com `writers_paused=zzzk20261009a1` e registra a orientação de
recuperação. O watchdog não deve reiniciar a imagem antiga. Corrigir a falha e
concluir migrations/RLS com a imagem da release antes de retomar os serviços.
Remover o marcador somente após confirmar que os novos serviços estão saudáveis.
Uma tentativa posterior também reconhece esse marcador enquanto a pausa persistir:
mesmo com o mesmo commit e diff vazio, repete a parada dos escritores e executa
backup, migrations/RLS e subida normal, sem cair no caminho de atualização já concluída.
