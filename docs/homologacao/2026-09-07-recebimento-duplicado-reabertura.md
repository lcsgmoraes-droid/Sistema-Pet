# Recebimento duplicado apos reabertura com desconto

## Causa comprovada

Em 04/09/2026, a venda 202609040004 (ID 1115674) do tenant Vira Lata
recebeu R$ 121 de um total inicial de R$ 135. A auditoria registra baixa parcial,
reabertura e alteracao do total para R$ 121 por desconto de R$ 14. A nova
finalizacao nao incluiu outro pagamento, mas o pos-processamento reapresentou
todos os pagamentos persistidos para gerar recebiveis novamente.

A conta original 7600/recebimento 6055 e a duplicada 7601/recebimento 6056
foram criadas, respectivamente, as 12:39:07 e 12:40:21 UTC. Existe somente um
VendaPagamento (6930). Auditorias da sequencia: 35317, 35320, 35323, 35325.
Nao existem movimentacoes de caixa vinculadas a essa venda.

## Correcao preventiva

- Venda bloqueada com SELECT FOR UPDATE e leitura atualizada antes da validacao.
- Reabertura usa o mesmo bloqueio.
- Recebiveis gerados apenas para IDs de pagamentos criados na transacao atual.
- Valores ja destinados a contas existentes nao geram outra conta/baixa.
- Pagamento e recebivel confirmados na mesma transacao; falha reverte ambos.
- Finalizacao sem dinheiro novo cancela previsoes residuais da venda quitada.
- Pos-commit permanece responsavel pelas notificacoes e demais efeitos secundarios.
- Sem migration, alteracao fiscal ou release de aplicativo mobile.

## Evidencia automatizada

Os testes reproduziram, antes da correcao, duplicidade na reabertura, repeticao de
pagamento parcial anterior e pagamento confirmado apesar de falha nos recebiveis.

Depois da correcao: 13 testes aprovados em PostgreSQL local, em schemas isolados
e removidos ao terminar. Cobrem reabertura/desconto, duas baixas parciais,
parcelamento, baixa de conta existente, isolamento entre tenants, rollback e retry,
duas finalizacoes concorrentes (segunda conexao observada aguardando lock),
dry-run do reparo, auditoria atomica, idempotencia e recusa de dados divergentes.

Arquivos: `test_finalizacao_recebiveis_atomicidade.py` e
`test_reparar_recebimento_duplicado.py`, em `backend/tests/unit/`.

## Plano de reparo autorizado

Lucas autorizou investigar, corrigir a duplicidade e prevenir recorrencia nesta tarefa.
Executar `python -m app.scripts.reparar_recebimento_duplicado` com tenant e IDs
explicitos. Sem `--apply`, apenas apresentar plano. Aplicar somente apos backup
do deploy e conferencias do estado atual.

- Preservar conta 7600 e recebimento 6055 de R$ 121 em 04/09/2026.
- Remover recebimento duplicado 6056; cancelar conta 7601 e zerar seu recebido.
- Cancelar previsoes residuais 6972 e 6973 de R$ 14 cada; desconto nao e entrada.
- Guardar snapshots completos anteriores em `audit_logs`, na mesma transacao.
- Recusar alteracoes se houver outros pagamentos, valores distintos ou vinculos.
- Repeticao do reparo retorna a auditoria existente, sem reaplicar a mudanca.

Total esperado de recebimentos de 09/08 a 07/09: R$ 1.964,92 (antes R$ 2.085,92).
Contas pendentes devem permanecer R$ 3.144,20. Nenhuma devolucao financeira real.

## Checklist de publicacao e rollback

- Responsavel: Codex, mediante autorizacao do Lucas; ambiente: producao CorePet.
- Validacao focada e teste real de concorrencia: aprovados.
- Gate completo de release e checks do PR: conferir antes do deploy.
- Publicacao: somente pelo launcher oficial `scripts/deploy_producao_remoto.ps1`.
- Backup: registrar o dump e o diretorio operacional informados pelo launcher.
- Verificar health, watchdog, commit servido, plano de reparo e total final.
- Rollback de codigo: reverter o PR pelo fluxo oficial; nao ha migration a reverter.
- Nao restaurar banco inteiro por causa deste reparo. Os snapshots auditados
  permitem revisar/reverter os registros especificos sem afetar movimentacoes novas.
