---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — bens_imobilizados

## Definição
Ativo imobilizado do tenant (equipamento, móvel etc.) com depreciação e valor de mercado, usado na avaliação de valor da empresa.

## Confirmado no código
- Modelo: `financeiro/models_imobilizado.py:19-63` (`BemImobilizado`).
- Colunas: `categoria`, `quantidade`, `valor_aquisicao`/`valor_residual`/`valor_mercado`, `depreciar`, `vida_util_meses`, `status`, `data_baixa`.
- `CheckConstraint`: `valor_residual <= valor_aquisicao` e `quantidade > 0` (garantido no banco). `UniqueConstraint(tenant_id, codigo_patrimonial)`.
- Sem nenhuma FK no arquivo.

## Relacionamentos
- Sem FK de saída nem de entrada.

## Utilizado por
- `financeiro/imobilizado_routes.py`, `financeiro/valor_empresa_service.py`.

## Não identificado
- Nada notável — módulo bem isolado e com constraints de integridade no próprio banco (incomum no resto do sistema).
