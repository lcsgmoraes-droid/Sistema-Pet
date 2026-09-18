---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — conciliacao_logs

Ver [[conciliacao_validacoes]].

## Definição
Log de auditoria com versionamento do módulo de conciliação de cartões.

## Confirmado no código
- Modelo: `conciliacao_models.py:606-680` (`ConciliacaoLog`).
- ⚠️ **FK fantasma confirmada**: `conciliacao_validacao_id` é `Integer` (nullable) com comentário explícito `# was: ForeignKey('conciliacao_validacao_id', ondelete='CASCADE')` / "FK desabilitado - tabela conciliacao_validacoes não existe" — **isso é falso**: [[conciliacao_validacoes]] existe no mesmo arquivo (`conciliacao_models.py`). A FK foi desabilitada por engano, não por ausência real da tabela. Relationship correspondente também está comentada.

## Relacionamentos
- FK de saída real: `criado_por_id → users.id` (RESTRICT).
- `conciliacao_validacao_id` deveria referenciar [[conciliacao_validacoes]]`.id` mas não tem constraint real.
- Sem referências de entrada.

## Utilizado por
- `conciliacao_routes.py`, `conciliacao_services_importacao.py`.

## Não identificado
- 🔴 Mesmo achado documentado em [[conciliacao_validacoes]] — FK deveria ser restaurada.
