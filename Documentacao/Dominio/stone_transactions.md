---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — stone_transactions

Ver [[Venda]], [[ContaReceber]], [[operadoras_cartao]].

## Definição
⚠️ **Código morto/órfão confirmado.** Modelo bem formado para transação de cartão Stone, mas nunca usado — a reconciliação Stone real do sistema usa [[operadoras_cartao]]/[[conciliacao_lotes]], onde "Stone" é só um valor de string (`operadora`/`nome_adquirente`).

## Confirmado no código
- Modelo: `stone_models.py:23-149` (`StoneTransaction`). `extend_existing=True` (indício de alteração/relocação posterior do modelo).
- FKs de saída bem formadas: `venda_id → vendas.id`, `conta_receber_id → contas_receber.id`, `user_id → users.id` (NOT NULL, mas nunca populado).
- 🔴 **Busca exaustiva confirma zero uso**: nenhum arquivo do projeto além do próprio `stone_models.py` importa `StoneTransaction` — não há router, não há service, não aparece em `main.py`/`main_routers.py`.

## Relacionamentos
- FKs de saída: `vendas.id`, `contas_receber.id`, `users.id` — nenhuma exercitada em runtime.
- `relationship("Venda", backref="stone_transactions")` e `relationship("ContaReceber", backref="stone_transactions")` sem efeito prático hoje.

## Utilizado por
- 🔴 Nada — código morto.

## Não identificado
- 🟡 Recomenda-se ao time decidir: remover o módulo `stone_models.py` inteiro, ou retomar a implementação se a integração Stone via API (em vez de conciliação por planilha) ainda for um objetivo.
