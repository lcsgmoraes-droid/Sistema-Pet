# Homologação local — calculadora iFood

| Campo | Valor |
|---|---|
| Data / responsável técnico | 2026-10-20 / Codex |
| Branch | `codex/ifood-calculadora-central` |
| Ambiente | DEV isolado `corepet-ifood-dev`, porta 18081 |
| Massa | Tenant e produto fictícios; sem dados de produção |
| Aceite de negócio | Lucas, após revisão em DEV |

## Cenários e evidências

| ID | Cenário | Resultado | Evidência |
|---|---|---|---|
| H01 | Alterar no cadastro de 100 para 150 e salvar | Preço ERP permaneceu 100/custo 60; contribuição própria 61,50 (41%), iFood 46,50 (31%); aviso abaixo da meta sumiu | Chrome local, cadastro reaberto e central atualizada |
| H02 | Simular preço sem gravar | Simular 100 mostrou contribuição própria 20 e aviso de margem; simular zero mostrou impedimento de preço; cadastro recarregado continuou 150 | API e Chrome local |
| H03 | Aplicar pela central e reabrir o cadastro | Aplicar 120 mostrou entrega iFood 24,60/20,50%; cadastro recarregado confirmou específico 120 e ERP 100/custo 60. Aplicar 150 novamente restaurou o final nas duas telas | API e Chrome local |
| H04 | Preço zero, nulo, promoção e custo de kit | Aprovado nos testes de backend | `test_ifood_management.py` |
| H05 | Visualizar sem editar e ID de outra empresa | Aprovado nos testes de backend | Simulação permitida a leitura; gravação segue controle canônico; foreign ID 404 |
| H06 | Migration desde g e desde main | Grafo com uma head e upgrade sem reaplicar g; banco local chegou a `zzzzl20261020a1 (head) (mergepoint)` | Teste Alembic e migração local |

Backend: 35 testes iFood aprovados com Python 3.12.10 e SQLite em memória:
`python -m pytest tests/unit/test_ifood_management.py tests/unit/test_ifood_catalog_contract.py tests/unit/test_ifood_routes_contract.py tests/unit/test_ifood_orders_contract.py tests/unit/test_ifood_client_contract.py -q`.

Regressão frontend: 28 testes produto/clonagem/recorrência/datas e 4 testes de
compartilhamento existentes aprovados. Fluxo único: uma head e nenhum artefato
indevido.

- `npm run build`: aprovado; aviso existente do tamanho do chunk PDV.
- `npm run test:app-routes-refactor`: aprovado.
- ESLint dos arquivos da calculadora/ModalPadrao/catalog e Ruff backend: aprovados.
- `docker compose -p corepet-ifood-dev --env-file .env.homolog.local -f docker-compose.homolog.yml -f ifood-calculadora.override.yml up -d --build --remove-orphans`:
  fonte do worktree, imagens reconstruídas e volumes existentes preservados. Os
  arquivos de configuração da prévia estão fora do Git. Backend/frontend saudáveis.
- `docker exec corepet-ifood-dev-backend-1 alembic current`: head de convergência l.
- `scripts/homologacao_local.ps1 -Acao validar` da prévia adaptada: E2E Plano
  Básico aprovado (1 teste) contra 18081 após o rebuild.
- Flags de escrita, operação e polling iFood verificadas falsas.
- Captura entregue no chat: `ifood-calculadora-dev-2026-10-20.png`, dados fictícios.
  Artefato local do chat; não é arquivo de aplicação versionado.

Oferta final: específico iFood 150; ERP 100; custo 60; estoque 4. Contribuição
estimada própria 61,50/41% e iFood 46,50/31%; meta 30% atendida nos dois cenários.
Resta uma recomendação de foto. Nenhum impedimento de cadastro ou aviso de
rentabilidade no exemplo final. A publicação remota continua desativada.

## Decisão

Validação técnica integrada aprovada para revisão do Lucas. Produção e envio ao
iFood desativados. Downgrade não foi executado em banco com dados; rollback por
código/imagem preserva as novas colunas conforme a ficha de entrega.

Revisão independente do fluxo não identificou bloqueio. Limitação não bloqueante:
se outra operação alterar custo/promoção entre a última simulação e a gravação,
o detalhe pode manter a estimativa anterior até reabrir; a central consulta os
dados novamente após aplicar. Não há bloqueio transacional dos custos durante
uma simulação de preço.
