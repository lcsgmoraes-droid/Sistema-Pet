---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — campanha_validade_automatica

Ver [[Tenant]], [[campanha_validade_exclusoes]], [[produto_lotes]].

## Definição
Configuração (por tenant) de desconto automático escalonado para produtos perto do vencimento, aplicável no app e/ou e-commerce.

## Confirmado no código
- Modelo: `produtos_estoque_models.py:248-262` (`CampanhaValidadeAutomatica`).
- Colunas: `ativo`, `aplicar_app`/`aplicar_ecommerce`, `desconto_60_dias`/`30_dias`/`7_dias` (percentuais), `rotulo_publico`, `mensagem_publica`.
- Sem FK própria — é config pura por tenant.
- ⚠️ Nenhuma unique constraint garante uma única linha por tenant (esperado ser singleton, mas o schema não impede duplicação).

## Relacionamentos
- Sem FKs de saída nem de entrada.

## Utilizado por
- `services/validade_campanha_service.py`.

## Não identificado
- ❓ Se o service garante singleton por tenant antes de inserir (não confirmado nesta pesquisa).
