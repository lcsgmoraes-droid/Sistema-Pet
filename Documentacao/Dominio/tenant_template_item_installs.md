---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — tenant_template_item_installs

Ver [[template_items]], [[tenant_template_installs]].

## Definição
Vínculo item-a-item entre um [[template_items|TemplateItem]] global e a cópia criada na tabela tenant-owned correspondente.

## Confirmado no código
- Modelo: `template_models.py:103-136` (`TenantTemplateItemInstall`).
- Colunas: `target_table` (nome da tabela destino, texto livre), `target_id` (PK do registro criado na tabela destino — referência polimórfica genérica, intencionalmente sem FK), `status` (default "active").
- ⚠️ `created_by_user_id` sem FK real.
- Referência polimórfica (`target_table`+`target_id`) sem qualquer validação de integridade a nível de banco — depende inteiramente da aplicação manter consistência.

## Relacionamentos
- Sem FK de saída real (design intencional, dado o caráter polimórfico de `target_table`/`target_id`).

## Utilizado por
- `tenant_onboarding_item_installs.py`.

## Não identificado
- Nenhuma garantia de integridade referencial para `target_table`/`target_id` — aceitável dado o design polimórfico, mas vale saber ao depurar dados inconsistentes.
