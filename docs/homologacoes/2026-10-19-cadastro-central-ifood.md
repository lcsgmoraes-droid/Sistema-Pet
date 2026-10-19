# Validação local — cadastro e central iFood

| Campo | Valor |
|---|---|
| Entrega | Cadastro canônico e central local do catálogo iFood |
| Data | 2026-10-19 |
| Versão | Branch `feat/20261019-1708-cadastro-e-central-ifood` |
| Ambiente | HOMOLOG local isolada, `http://127.0.0.1:18080` |
| Responsável técnico | Codex |
| Aceite de negócio | Lucas, pendente de revisão |
| Massa | Tenant fictício CorePet Homologacao Local |

## Pré-condições

Projeto Docker `corepet-homolog`, credenciais locais existentes preservadas,
dados fictícios. Escrita/polling/operação iFood e demais integrações reais
desabilitados. Sem cópia de dados de produção ou reset de volumes.

## Evidências

- Data: 2026-10-19. Branch indicada acima; registro acompanha o commit da entrega.
  Ambiente: somente HOMOLOG local. Responsável: Codex.
- `scripts/homologacao_local.ps1 -Acao verificar-config`: aprovado.
- `scripts/homologacao_local.ps1 -Acao subir`: imagens reconstruídas,
  migration aplicada, frontend/backend saudáveis. `alembic current` no container:
  `zzzzg20261019a1 (head)`.
- `scripts/homologacao_local.ps1 -Acao validar`: 1 E2E do Plano Básico aprovado
  após o rebuild final, usando o tenant fictício. Sem rede iFood.
- Em `backend`, Python 3.12.10 / `.venv`, SQLite em memória:
  `python -m pytest tests/unit/test_ifood_management.py tests/unit/test_ifood_routes_contract.py tests/unit/test_ifood_catalog_contract.py tests/unit/test_ifood_client_contract.py tests/unit/test_ifood_orders_contract.py -q`:
  **31 aprovados**.
- Em `frontend`, `TZ=America/Sao_Paulo`:
  `node --test src/pages/produtosFormUtils.test.mjs src/utils/produtoMargem.test.mjs src/utils/produtoRecorrencia.test.mjs src/components/produto/ifoodProdutoDates.test.mjs`:
  **28 aprovados**.
- `npm run test:app-routes-refactor`: aprovado. `npm run build`: aprovado;
  permanece aviso já existente de tamanho do chunk PDV. `dist` não versionado.
- ESLint nos arquivos frontend alterados e Ruff no backend da funcionalidade:
  aprovados. `git diff --check` e fluxo único: aprovados; uma única head.
- `git fetch origin main` antes de encerrar: branch parte da main atual, sem
  commits pendentes de incorporação naquele momento.

## Cenários de aceite

| ID | Cenário | Resultado obtido / evidência | Status |
|---|---|---|---|
| H01 | Central abre edição canônica | Menu da linha levou a `/produtos/5/editar`; não há formulário de anúncio separado | Aprovado no Chrome local |
| H02 | Salvar e reabrir seleção/preço | Exemplo `DEV iFood Ração 3 kg`, custo R$ 60,00, ERP R$ 100,00, específico R$ 100,00 manteve valores e seleção | Aprovado no Chrome local |
| H03 | Preço zero como pendência | R$ 0,00 foi salvo no ERP, recarregado como específico e mostrado `Com pendências` na central; depois restaurado para R$ 100,00 | Aprovado no Chrome local |
| H04 | Taxa desconhecida | Inicialmente contribuição não calculada; não foi assumida taxa zero | Aprovado no Chrome local e testes |
| H05 | Configuração pela loja | Operador com permissão do tenant salvou regras; endpoint rejeita campos de conexão e nega falta de permissão | Aprovado no Chrome local e testes |
| H06 | Contribuição nos dois cenários | Preço 100 − custo 60 − comissão 10/20 − pagamento 2 − tributos 5 − adicional 3 = contribuição 20/10 (20%/10%). Meta 30% gera aviso | Aprovado no Chrome local e testes |
| H07 | Regra e preço específico | Acréscimo geral 10% alterou os produtos sem preço próprio de 10 para 11; exemplo específico continuou 100 | Aprovado no Chrome local e testes |
| H08 | Busca e detalhamento | Busca `DEV iFood` encontrou o item; menu abriu parcelas, orientações e cenário iFood | Aprovado no Chrome local |
| H09 | Promoção/fuso/preservação | Janela Brasília/UTC, término, datas inválidas e ausência de herança dos outros canais | Aprovado nos testes |
| H10 | Estoque/kit/pausa | Reservas e capacidade em lote; composição editada exige salvar antes de confirmar estoque/custo; pausa sobrevive reposição | Aprovado nos testes |
| H11 | Isolamento e permissão | ID de outra empresa recusado; edição compartilhada comum preserva oferta e alteração iFood da origem é bloqueada | Aprovado nos testes |
| H12 | Migration e regressão ERP | Head aplicada e E2E de venda/cancelamento existente passou; sem publicação externa | Aprovado localmente |

Evidência visual entregue no chat: central e memória de cálculo com dados
fictícios, identificadas como `ifood-central-dev.png` e `ifood-margem-dev.png`.
Imagens são artefatos locais do chat, não arquivos de aplicação versionados.

## Inconsistências corrigidas durante a validação

- Restrição antiga baseada em administrador global impedia o administrador da
  loja de configurar taxas: criada superfície comercial com permissão do tenant,
  mantendo conexão/operações externas separadas.
- Horário de promoção sem offset e custo de kit editado poderiam divergir:
  conversão de datas e comparação da composição foram cobertas pelos testes.
- Diferença de centavos entre parcelas e contribuição: arredondamento monetário
  aplicado antes da subtração, com regressão específica.
- Não foi executado downgrade em banco com dados: migration é aditiva e o
  rollback operacional preserva as novas colunas. Aceite visual de negócio e
  implantação em produção seguem pendentes por escopo.

## Decisão

Validação técnica aprovada para revisão do Lucas em DEV. O exemplo fictício
permanece disponível para inspeção. Aceite de negócio e publicação em produção
continuam separados; esta entrega não autoriza deploy nem ativa o canal remoto.
