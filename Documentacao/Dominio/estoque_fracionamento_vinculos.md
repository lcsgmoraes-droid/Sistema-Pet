---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — estoque_fracionamento_vinculos

Ver [[Produto]], [[estoque_fracionamento_conversoes]], [[produto_granel_vinculos]].

## Definição
Liga um produto "fechado" (ex.: frasco) a um produto "fracionado" (ex.: dose), para uso em fracionamento clínico — ex.: procedimento veterinário. Conceito irmão de [[produto_granel_vinculos]] (venda a granel), mesmo padrão estrutural, domínio deliberadamente separado.

## Confirmado no código
- Modelo: `estoque_fracionamento_models.py:21-58` (`EstoqueFracionamentoVinculo`).
- Colunas: `produto_origem_id`, `produto_destino_id`, `fator_conversao`, `validade_apos_abertura_dias`, `observacao`, `ativo`, `user_id` (NOT NULL).
- Unique `(tenant_id, produto_origem_id, produto_destino_id)`.
- FKs usam `ondelete RESTRICT` (diferente do padrão CASCADE do resto do sistema) — provavelmente para impedir apagar produto com histórico clínico associado.

## Relacionamentos
- FKs de saída: `produto_origem_id → produtos.id` (RESTRICT), `produto_destino_id → produtos.id` (RESTRICT), `user_id → users.id`.
- Referenciada por: [[estoque_fracionamento_conversoes]].`vinculo_id` (RESTRICT).

## Utilizado por
- `estoque/fracionamento_clinico.py` (`_obter_ou_atualizar_vinculo`, `serializar_vinculo_fracionamento`, `sugerir_fracionamento_clinico`).
- `estoque_fracionamento_routes.py`.

## Não identificado
- Nada notável além do padrão `RESTRICT` já citado.
