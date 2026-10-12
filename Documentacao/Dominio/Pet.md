---
tipo: dominio
atualizado: 2026-10-10
---

# Entidade — Pet

Ver [[Cliente]], [[EmpresaGrupo]], [[Veterinario]], [[Banho-e-Tosa]].

## Relação com grupo comercial (desde 10/2026)

**Pet é compartilhado por GRUPO comercial, igual Cliente** — mesmo mecanismo,
mesma migration (`zzzv20261005a1_rls_grupo_pessoas_pets.py` já cobre `clientes`
E `pets` no mesmo loop). Um animal cadastrado numa loja fica visível e editável
por qualquer loja ativa do mesmo grupo do tutor — não existe mais um cadastro
separado por loja para o mesmo pet.

- `origem_tenant_id` (campo desta tabela, **imutável** após gravado, mesmo
  `@validates` que Cliente usa) registra a loja que introduziu o pet no grupo.
- Visibilidade/edição roda em duas camadas, como Cliente: filtro automático
  do ORM (`app/tenancy/filters.py::pessoa_visivel_no_grupo`, reaproveitado
  para `Pet` também) e política real de RLS no Postgres
  (`pets_grupo_select`/`pets_grupo_update`).
- O antigo mecanismo de "pet-mestre" (vínculo manual, análogo ao
  `PessoaMestre`) foi **eliminado** — modelo, service, rotas e tabela
  removidos (migration `zzzt20261005a1_remove_pet_mestre.py`).

### Divisão de campos — o que é compartilhado, o que é por loja

Decisão de negócio (10/2026): nem todo dado do pet é compartilhado. Só
**identidade/cadastro** fica no `Pet` (visível/editável por todo o grupo);
**movimentação clínica** (o que aconteceu, quando, em qual loja) é sempre
por loja.

**Ficam diretos no `Pet` (compartilhados pelo grupo)**: `nome`, `especie`,
`raca`, `sexo`, `castrado`/`castrado_data`, `data_nascimento`,
`idade_aproximada`, `porte`, `cor`/`cor_pelagem`, `microchip`, `alergias` +
`alergias_lista`, `doencas_cronicas` + `condicoes_cronicas_lista`,
`medicamentos_continuos` + `medicamentos_continuos_lista`,
`restricoes_alimentares_lista`, `tipo_sanguineo`, `pedigree_registro`,
`observacoes`, `foto_url`, `ativo`. Alterações nesses campos diretos geram
`PetHistoricoAlteracao` (data, usuário, loja de quem editou, campo, valor
anterior/novo — chamado em `app/pets_routes.py::atualizar_pet`, mesmo padrão
de `ClienteHistoricoAlteracao`). Campos rastreados hoje:
`CAMPOS_RASTREADOS_PET` em `app/services/pet_historico_service.py` — `nome`,
`especie`, `raca`, `sexo`, `castrado`, `data_nascimento`, `porte`, `cor`,
`microchip`, `pedigree_registro`, `ativo` (os campos JSON de lista —
alergias/condições crônicas/medicamentos contínuos/restrições — ainda não
entram nesse rastreamento de texto simples).

**Viram registro por loja, em `PetRegistroClinico`** (tabela
`pets_registros_clinicos`, `app/models_cadastros.py`): `peso` (medição) e
`historico_clinico` (texto) — cada marcação tem sua própria `tenant_id` (a
loja que registrou), `registrado_em`, `user_id`, e `tipo` (`"peso"` ou
`"historico"`). Todas as lojas do grupo **leem** todas as marcações (via
`app/services/pet_registros_clinicos_service.py::listar_registros`, sem
filtro de tenant explícito — herda a visibilidade de grupo do `Pet` pai via
`app/tenancy/filters.py::_PAI_DO_HISTORICO`); só a loja que registrou pode
editar/apagar (`app/pets_routes.py`, sub-rotas
`/pets/{pet_id}/registros-clinicos`, checagem de tenant em
`_obter_registro_da_loja`). Colunas legadas `Pet.peso`/`Pet.historico_clinico`
continuam existindo na tabela `pets` (compatibilidade — ainda lidas/gravadas
por ~13 módulos fora do fluxo principal: veterinário, banho&tosa, app
mobile) e refletem **o valor mais recente de qualquer loja do grupo**
(`_ultimo_peso_do_pet`/`_ultimo_historico_do_pet` em `app/pets_routes.py`,
via `registros_service.ultimo_registro(..., tenant_id=None)`) — é uma visão
"resumo rápido", não a fonte de verdade; a fonte de verdade por marcação é
sempre `PetRegistroClinico`.

**Diagnósticos/laudos, tratamentos, vacinas, compra de medicamento**: não
existem como campos/tabela própria do domínio Pet — vivem nos módulos
veterinário e banho&tosa (`ConsultaVet`, exames, vacinas etc.), fora deste
documento. São "atendimentos por loja" e devem seguir a mesma regra de
leitura (todo o grupo lê, só quem registrou edita) quando esses módulos
forem adaptados — ainda não foi feito.

**Endpoint pronto para "gráfico de peso e histórico, com loja"** (pedido de
produto): `GET /pets/{pet_id}/registros-clinicos` já devolve todos os
registros do pet (todas as lojas do grupo), cada um com `loja_id`,
`loja_nome`, `registrado_em`, `valor`/`texto` e `pode_editar`. Sem tela
própria ainda no frontend — é a próxima peça a construir (ver
`frontend/src/pages/pet-detalhes/PetDetalhesSaudeTab.jsx`, que hoje só
mostra o `historico_clinico` achatado, sem indicar loja/data por marcação).

## Confirmado no código
- Modelo: `backend/app/models_cadastros.py:373-434` (`Pet`), tabela `pets`.
- `cliente_id` → `clientes.id` (tutor) — `Cliente.pets` (relationship).
- `user_id` → `users.id` (criador do registro).
- `codigo` — código único do pet.
- Relaciona-se com `Especie`/`Raca` **só por texto livre** — `especie`/`raca`
  no `Pet` não são `ForeignKey`, mesmo havendo um mecanismo `EspecieMestre`/
  `RacaMestre` parecido com o antigo `ProdutoMestre` (fora do escopo deste
  documento).
- É referenciado por `VendaItem.pet_id` (venda associada a um pet específico
  — comum em pet shop para ração/serviço recorrente por animal).
- `PetHistoricoAlteracao` (`pets_historico_alteracoes`, mixin `TenantScoped`,
  não `BaseTenantModel` — não muda o schema de tenant, segue a visibilidade
  do `Pet` pai).
- `PetRegistroClinico` (`pets_registros_clinicos`, mesmo mixin
  `TenantScoped`).
- Nenhuma das duas tabelas de histórico/registro tem RLS própria no
  Postgres — dependem 100% do filtro automático do ORM, mesma convenção
  usada para `ClienteHistoricoAlteracao`.

## Rotas (3 módulos distintos, histórico de evolução do produto)

Hoje existem três conjuntos de rotas de Pet, todos em uso real pelo
frontend — não é duplicação acidental recente, é evolução histórica que
ainda não foi consolidada:

- **`backend/app/pets_routes.py`** (módulo dedicado, montado em `/pets`) —
  o mais completo: CRUD de pet + sub-rotas de `registros-clinicos`. Usado
  por `GerenciamentoPets.jsx`/`PetForm.jsx`.
- **`backend/app/clientes/pets_routes.py`** (montado dentro de `/clientes`)
  — CRUD mais simples, sem os sub-recursos de registro clínico (lê/grava
  `pet.peso`/`pet.historico_clinico` direto). Usado pela aba de pets no
  cadastro de Pessoa (`ClientesNovo.jsx`/`useClientesNovoCadastro.js`) e
  pela calculadora de ração.
- **`backend/app/veterinario_agenda_routes_parts/pets_routes.py`** — listagem
  só-leitura para a agenda veterinária, com seu próprio mecanismo de
  "tenants acessíveis" (`_all_accessible_tenant_ids`, parceria clínica↔pet
  shop, mesmo padrão de `get_all_accessible_tenant_ids`).

Todos os três, mais `app/routes/app_mobile_pets_routes.py` (app do tutor,
intencionalmente restrito ao próprio tenant de cadastro — grupo comercial
não se aplica à visão do consumidor final), já aplicam visibilidade de grupo
nos pontos de leitura/escrita por ID (`pet_visivel`/`cliente_visivel` em
`app/services/pet_registros_clinicos_service.py`) e nas listagens.

## Utilizado por
- [[Veterinario]] (consultas, exames, prontuário, internações)
- [[Banho-e-Tosa]] (agendamentos)
- [[PDV-Vendas]] (item de venda vinculado a um pet, ex. recorrência de ração)
- App mobile (tutores acompanham o próprio pet — sem grupo comercial, só o
  tenant de cadastro)

## Não identificado
- ⚠️ Não identificado no código analisado: rota específica de upload de foto
  de pet e suas validações de segurança — ❓ necessita validação adicional
  se esse fluxo existir fora do escopo já coberto.
- ❓ Diagnósticos/laudos, tratamentos, vacinas e compra de medicamento (hoje
  nos módulos veterinário/banho&tosa) ainda não foram revisados para seguir
  a mesma regra "todo o grupo lê, só quem registrou edita" que já vale para
  peso/histórico clínico em `PetRegistroClinico` — fica como próxima rodada.
