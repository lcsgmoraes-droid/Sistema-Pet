# Registro técnico — convergência de migrations iFood no DEV

| Campo | Valor |
|---|---|
| Entrega | Atualização automática da vigência da promoção iFood |
| PR | #1533 |
| Data / responsável técnico | 2026-10-20 / Codex |
| Ambiente | DEV isolado `corepet-ifood-dev`, porta 18081 |
| Banco / massa | `corepet_homolog`, produto fictício `DEV-IFOOD-3KG` |
| Fonte | Worktree `ifood-calculadora`, branch `codex/ifood-calculadora-central`, após integrar `origin/main` em `0c9f562aa` |

## Pré-condições e motivo

A integração da main revelou dois arquivos com `revision = zzzzl20261020a1`:
a migration fiscal já publicada na main e a merge de iFood ainda pendente neste
PR. A migration fiscal foi preservada. A merge do PR passou a
`zzzzm20261020a1`, com pais `zzzzg20261019a1` (iFood) e
`zzzzl20261020a1` (fiscal).

O DEV já havia aplicado a antiga merge local L, que unia G e K sem DDL.
Deixar esse número registrado faria o Alembic considerar a nova migration
fiscal L como aplicada, embora suas colunas não existissem. O reparo abaixo
foi restrito a esse banco DEV conhecido; não é procedimento de produção.

Antes de alterar somente o registro de versões, assertions confirmaram:

- banco alvo `corepet_homolog`, com uma revisão registrada `zzzzl20261020a1`;
- as quatro colunas `nfe_cancelamento_*` da migration fiscal L ausentes;
- os seis campos iFood da migration G presentes em `produtos`;
- produto 2 com SKU `DEV-IFOOD-3KG`, ERP 100, custo 60, iFood 150, estoque 4,
  selecionado, foto presente, sem pausa e sem preço/datas de promoção;
- escrita de catálogo, operações de pedidos e polling iFood desativados.

## Cenários de aceite do reparo

| ID | Cenário | Resultado obtido | Status |
|---|---|---|---|
| M01 | Grafo sem IDs duplicados e com uma head | Teste AST de todas as revisions e Alembic: head M | Aprovado |
| M02 | Banco com G+K deve aplicar o fiscal L uma vez | Teste de upgrade planeja apenas L e M | Aprovado |
| M03 | Corrigir a identificação da antiga merge DEV | `stamp --purge G K` registrou os dois ramos já aplicados, sem executar DDL ou downgrade | Aprovado |
| M04 | Aplicar a migration fiscal verdadeira e nova merge | Runner da imagem nova aplicou K→L e G+L→M | Aprovado |
| M05 | Preservar produto e campos iFood | Pós-check com assertions confirmou os mesmos valores e foto | Aprovado |
| M06 | Evitar efeito externo | Três flags iFood continuaram falsas; somente projeto DEV 18081 operado | Aprovado |

## Comandos e evidências

Executados na pasta temporária já existente da prévia, com o override apontando
para o backend do worktree. O arquivo `.env.homolog.local` ficou fora do Git e
seu conteúdo não foi registrado.

```powershell
docker compose -p corepet-ifood-dev --env-file .env.homolog.local -f docker-compose.homolog.yml -f ifood-calculadora.override.yml build backend migrate
docker exec corepet-ifood-dev-backend-1 alembic stamp --purge zzzzg20261019a1 zzzzk20261020a1
docker compose -p corepet-ifood-dev --env-file .env.homolog.local -f docker-compose.homolog.yml -f ifood-calculadora.override.yml run --rm --no-deps migrate
docker compose -p corepet-ifood-dev --env-file .env.homolog.local -f docker-compose.homolog.yml -f ifood-calculadora.override.yml run --rm --no-deps migrate alembic current
```

Todos concluíram com exit 0. Resultado final:
`zzzzm20261020a1 (head) (mergepoint)`. O runner da imagem nova confirmou
as quatro colunas fiscais e os seis campos iFood presentes, produto preservado
e flags externas falsas. Nenhum volume foi removido. Esta operação não
reconstruiu o frontend nem recriou o serviço backend; a atualização dos serviços
faz parte da validação integrada posterior.

Backend: 47 testes iFood aprovados, incluindo contrato temporal, fuso,
intervalos inclusivos, filtros/paginação, identificação exata por tenant,
ausência de persistência nas previews e grafo de migrations. Ruff aprovado.

## Decisão

Reparo técnico do DEV aprovado. Nenhum defeito pendente neste reparo. O aceite
da atualização automática da promoção depende da homologação integrada da
entrega. Este registro não autoriza deploy de produção. Não houve alteração de
esquema ou dado em outro ambiente.
