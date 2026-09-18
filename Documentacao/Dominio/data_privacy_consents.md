---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — data_privacy_consents

Ver [[Tenant]].

## Definição
Registro de consentimento LGPD (WhatsApp/marketing/analytics) de um titular de dados.

## Confirmado no código
- Modelo: `whatsapp/security.py:127-159` (`DataPrivacyConsent`). `TenantScoped` + `Base` — `tenant_id` sem FK real (mixin genérico, diferente do padrão explícito de `whatsapp/models.py`).
- Colunas: `subject_type` (customer/user/contact)/`subject_id`, `phone_number`/`email`, `consent_type` (whatsapp/marketing/analytics), `consent_given`, `consent_text`, `ip_address`/`user_agent`, `revoked_at`/`revoke_reason`.

## Relacionamentos
- Sem FK real.

## Utilizado por
- `LGPDService.record_consent/check_consent/revoke_consent` (`whatsapp/security.py`), `services/lgpd_consents.py`, `whatsapp/security_router.py`.

## Não identificado
- Inconsistência de padrão de `tenant_id` dentro do próprio módulo WhatsApp (aqui sem FK real, em `whatsapp/models.py` com FK real).
