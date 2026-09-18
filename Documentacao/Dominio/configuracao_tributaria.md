---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — configuracao_tributaria

Ver [[empresa_config_fiscal]], [[Tenant]].

## Definição
Configuração tributária usada pelo módulo de IA financeira (regime, alíquotas Simples/Presumido/ICMS/ISS) — possivelmente sobreposta a [[empresa_config_fiscal]] (não confirmado se são consolidadas ou paralelas).

## Confirmado no código
- Modelo: `ia/aba7_extrato_models.py:255-296` (`ConfiguracaoTributaria`). `UniqueConstraint(tenant_id)` — 1 config por tenant.
- ⚠️ Contém um bloco de relationship **duplicado e comentado duas vezes** (linhas 294-298, cópia exata do comentário acima) — resíduo de edição, campo morto no arquivo.
- O próprio arquivo termina forçando import de `app.financeiro_models`/`DREPeriodo` "para garantir registro do modelo complementar" — indício direto de uma dependência circular conhecida (comentada em `db/base.py:51`).

## Relacionamentos
- Sem FK real além do `tenant_id`.

## Utilizado por
- Módulo de extrato/DRE com IA.

## Não identificado
- ❓ Não confirmado se esta tabela é redundante com [[empresa_config_fiscal]] ou serve propósito distinto — vale investigar se são duas fontes de verdade tributária divergentes.
