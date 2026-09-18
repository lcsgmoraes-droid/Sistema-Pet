---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — pendencias_estoque

Ver [[Cliente]], [[Produto]], [[Venda]].

## Definição
Lista de espera de produto em falta: cliente pede para ser avisado quando o produto voltar ao estoque. Dispara notificação automática (push/WhatsApp) quando o estoque é reposto.

## Confirmado no código
- Modelo: `pendencia_estoque_models.py:22-107` (`PendenciaEstoque`).
- Colunas: `cliente_id`, `produto_id`, `usuario_registrou_id`, `quantidade_desejada`, `valor_referencia`, `observacoes`, `status` (pendente/notificado/finalizado/cancelado), `data_notificacao`, `whatsapp_enviado`, `mensagem_whatsapp_id`, `data_finalizacao`, `venda_id` (nullable, venda que finalizou a pendência), `motivo_cancelamento`, `prioridade` (0 normal/1 alta/2 urgente), `data_registro`. Tem método `to_dict()` customizado.

## Relacionamentos
- FKs de saída: `cliente_id → clientes.id`, `produto_id → produtos.id`, `usuario_registrou_id → users.id`, `venda_id → vendas.id` (nullable).
- Sem FK de outras tabelas apontando pra cá; acessada via backref (`Cliente.pendencias_estoque`, `Produto.pendencias`).

## Utilizado por
- `services/pendencia_estoque_service.py` (`verificar_e_notificar_pendencias`, `_notificar_pendencia`, `marcar_pendencia_finalizada` — envio de WhatsApp/push).
- `services/nao_venda_service.py`.

## Não identificado
- Nada notável.
