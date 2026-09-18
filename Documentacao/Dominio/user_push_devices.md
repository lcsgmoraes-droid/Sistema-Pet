---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — user_push_devices

Ver [[Usuario]], [[app_notifications]].

## Definição
Dispositivo registrado para notificação push (token Expo) de um usuário.

## Confirmado no código
- Modelo: `models.py:209-244` (`UserPushDevice`).
- `expo_push_token` (token Expo, não FCM/APNs direto). Unique constraint composto `(tenant_id, user_id, expo_push_token)`.
- Campos de diagnóstico (`platform`, `os_name/version`, `app_version`) e de entrega (`last_success_at`, `last_ticket_id`, `last_error*`).

## Relacionamentos
- FK de saída: `user_id → users.id`.
- Sem referências de entrada formais.

## Utilizado por
- `services/push_devices.py::load_user_push_targets` (monta lista de tokens ativos por usuário/tenant), `routes/ecommerce_auth_profiles.py`, `routes/app_mobile_routes.py`.

## Não identificado
- Nada notável.
