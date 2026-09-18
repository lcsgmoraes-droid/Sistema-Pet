---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — mensagens_whatsapp

Ver [[conversas_whatsapp]].

## Definição
Mensagem trocada numa [[conversas_whatsapp|conversa de WhatsApp comercial]], com intenção detectada e resposta da IA.

## Confirmado no código
- Modelo: `ia/aba6_aba9_models.py:80-107` (`MensagemWhatsApp`).

## Relacionamentos
- FK de saída: `conversa_id → conversas_whatsapp.id` (correta).

## Utilizado por
- `routes/whatsapp_routes.py`.

## Não identificado
- Nada notável.
