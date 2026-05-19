# Ops Tenants e Catalogo Base - Design

## Objetivo

Adicionar ao `/ops` uma aba administrativa para Lucas acompanhar tenants e disparar a importacao do catalogo base da loja `admin@mlprohub.com.br` para tenants novos.

## Escopo do MVP

- Criar rota `/ops/tenants`.
- Listar tenants com status, plano, cobranca, origem da assinatura, data de ativacao, usuario principal e contadores basicos.
- Mostrar se o pacote `catalogo-base-loja-lucas` ja foi aplicado no tenant.
- Permitir simular a importacao do catalogo base antes de gravar.
- Permitir aplicar a importacao por botao explicito apos a simulacao.

## Fora do MVP

- Edicao de plano, status e cobranca pela tela.
- Processamento de pagamento.
- Medicao real de bytes por tenant no banco ou disco.
- Importacao automatica no cadastro do cliente.

## Backend

Criar um servico `ops_tenants_service` com consultas agregadas por tenant e funcoes de importacao administrativa. As rotas ficam em `/admin/tenants`, protegidas por `require_admin`, mantendo o mesmo padrao de seguranca do `/admin/observabilidade`.

Endpoints:

- `GET /admin/tenants`: lista tenants e resumo.
- `POST /admin/tenants/{tenant_id}/catalog-import/preview`: executa dry-run.
- `POST /admin/tenants/{tenant_id}/catalog-import/apply`: executa importacao real quando `confirm=true`.

## Frontend

Adicionar `OpsTenants.jsx` e um item "Tenants" no `OpsLayout`. A tela usa o estilo atual do Ops: layout denso, tabela/lista escaneavel, metricas compactas e acoes claras por linha. O botao de aplicar fica desabilitado ate haver uma simulacao bem-sucedida para o tenant selecionado.

## Seguranca Operacional

- A importacao continua idempotente pelo `tenant_template_installs` e `tenant_template_item_installs`.
- O tenant fonte nunca pode ser o proprio destino.
- A tela nao sobrescreve alteracoes feitas pelo tenant depois da importacao.
- Aplicacao real exige confirmacao no payload e usuario admin autenticado.

## Validacao

- Testes unitarios do servico de tenants.
- Teste de rota para garantir protecao e contrato basico.
- Build frontend.
- Suite focada do importador de catalogo base.
