---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — cargos

Ver [[Cliente]], [[ContaPagar]].

## Definição
Cargo de funcionário, com parametrização salarial e de encargos trabalhistas (INSS, FGTS, férias, 13º).

## Confirmado no código
- Modelo: `cargo_models.py:11-52` (`Cargo`).
- Colunas: `nome`, `descricao`, `salario_base`, `regime_remuneracao` (default "clt"), `gera_encargos`, `inss_patronal_percentual` (default 20), `fgts_percentual` (default 8), `inss_funcionario_percentual`/`valor`, `desconto_transporte_valor`, `outros_descontos_valor`, `gera_ferias`/`gera_decimo_terceiro` (flags de provisão automática), `ativo`.

## Relacionamentos
- Sem FK de saída.
- 🔴 **FK fantasma confirmada e notável**: `Cliente.cargo_id` (funcionário = [[Cliente]] com `tipo_cadastro="funcionario"`) tem a linha `ForeignKey("cargos.id")` **comentada no código** (`models_cadastros.py:164-167`), substituída por `Integer` solto, com comentário "FK temporária sem constraint (tabela cargos não existe ainda)" — **comentário desatualizado**: `cargos` existe e é usada em produção por pelo menos 7 serviços diferentes. Isolamento multi-tenant depende inteiramente de filtros manuais `Cargo.tenant_id == tenant_id` espalhados pelo código, sem garantia de schema.

## Utilizado por
- CRUD: `cargos_routes.py` (registrado em `main_routers.py:566`, tag "RH - Cargos").
- Join manual `Cliente.cargo_id == Cargo.id` em: `services/ferias_service.py`, `services/decimo_terceiro_service.py`, `services/provisao_trabalhista_service.py`, `services/provisao_beneficios_service.py`, `dashboard/ponto_equilibrio_classificacao.py`, `dre_canais/folha.py`, `banho_tosa_custos_reais.py` (custo de mão de obra do banho&tosa usa `Cargo.salario_base`).

## Não identificado
- 🔴 `Cliente.cargo_id` deveria ser FK real e não é — recomenda-se ao time promover a constraint, já que a tabela-alvo está pronta e em uso há tempo.
