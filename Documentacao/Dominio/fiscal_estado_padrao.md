---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — fiscal_estado_padrao

Ver [[empresa_config_fiscal]].

## Definição
Tabela de referência (por UF) com alíquotas ICMS padrão, CFOPs e regime mais comum — usada para pré-preencher a config fiscal de uma empresa nova.

## Confirmado no código
🔴 **Mesma duplicação com risco de crash de [[fiscal_catalogo_produtos]]**: `fiscal_estado_padrao_models.py:6` (top-level, canônica em runtime) vs `fiscal_models/fiscal_estado_padrao.py:6` (cópia idêntica, só usada por Alembic/seed scripts). Mesmo risco de `InvalidRequestError` se importadas juntas.
- Colunas: `uf` (unique), `icms_aliquota_interna`/`interestadual`, `aplica_difal` (bool), `cfop_venda_interna`/`interestadual`/`compra`, `regime_mais_comum`, `observacoes_fiscais`.

## Relacionamentos
- Sem FK de saída.
- ⚠️ FK fantasma de entrada: `empresa_config_fiscal.fiscal_estado_padrao_id` é `Integer` sem `ForeignKey()`, com comentário *"Temporariamente sem FK até fiscal_estado_padrao ser recriado"* — **comentário desatualizado**: a tabela existe e é ativamente consultada.

## Utilizado por
- `services/fiscal_config_service.py` — função `criar_config_fiscal_empresa` (busca por UF e copia alíquotas/CFOPs para nova [[empresa_config_fiscal]]).

## Não identificado
- 🔴 **Achado importante**: `criar_config_fiscal_empresa` (única função que grava `fiscal_estado_padrao_id`) **nunca é chamada em lugar nenhum do código**. A função realmente usada em produção (`obter_ou_criar_config_fiscal_empresa_padrao`) nunca preenche esse campo — na prática, `fiscal_estado_padrao_id` fica sempre `NULL` no fluxo real.
- 🔴 Mesmo risco de crash por duplicação já citado em [[fiscal_catalogo_produtos]] — remover a cópia órfã em `fiscal_models/`.
