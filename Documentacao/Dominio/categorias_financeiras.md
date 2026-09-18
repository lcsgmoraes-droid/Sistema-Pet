---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — categorias_financeiras

Ver [[ContaPagar]], [[ContaReceber]], [[dre_subcategorias]].

## Definição
Categoria de receita/despesa do tenant, hierárquica (auto-referência) e ligada opcionalmente a uma subcategoria de DRE.

## Confirmado no código
- Modelo: `financeiro/models_catalogos.py:20-53` (`CategoriaFinanceira`).
- Colunas: `tipo` (receita/despesa), `tipo_custo` (fixo/variavel/ambos), `categoria_pai_id` (self-FK, hierarquia), `dre_subcategoria_id`.
- Relationships diretas: `contas_pagar = relationship("ContaPagar", back_populates="categoria")`, `contas_receber = relationship("ContaReceber", back_populates="categoria")`.

## Relacionamentos
- FKs de saída: `categoria_pai_id → categorias_financeiras.id` (self), `dre_subcategoria_id → dre_subcategorias.id`, `user_id → users.id`.
- Referenciada por: `movimentacoes_financeiras.categoria_id`, `lancamentos_manuais.categoria_id`, `lancamentos_recorrentes.categoria_id`, [[ContaPagar]], [[ContaReceber]], `ia/aba7_extrato_models.py` (3 ocorrências).

## Utilizado por
- `categorias_routes.py`, `ai_core/analyzers/extrato_analyzer.py`, `dashboard/ponto_equilibrio_margem.py`.

## Não identificado
- Nada notável — é o hub de categorização financeira do sistema.
