---
tipo: dominio
atualizado: 2026-09-12
---

# Entidade — Cliente

Ver [[Pet]], [[Funcionalidades]] (Pessoas/Clientes), [[Venda]].

## Confirmado no código
- Modelo: `backend/app/models_cadastros.py` (`Cliente`).
- `user_id`, `auth_user_id` → `users.id` (vínculo opcional com login de app/e-commerce).
- `merged_into_id` → auto-referência (`clientes.id`) usada para **merge de clientes duplicados** — existe `PessoaMergeLog` (`models_authz.py`) para auditar essas fusões.
- `fornecedor_grupo_id` → `fornecedor_grupos.id` (um "Cliente" também pode representar um fornecedor no schema — reaproveitamento de cadastro).
- Tem muitos `Pet` (cascade delete-orphan).
- Usado também como `fornecedor_id` em [[ContaPagar]] e como `entregador_id`/`funcionario_id` em algumas vendas — o schema reaproveita a entidade `Cliente` para papéis que vão além de "cliente comprador" (fornecedor, entregador). ⚠️ Isso é uma observação estrutural, não um erro — mas pode confundir quem espera uma entidade separada para "Fornecedor" ou "Entregador".

## Utilizado por
- Cadastro de Pessoas/Clientes no menu (ver [[Funcionalidades]])
- [[Pet]] (tutor)
- [[Venda]] (comprador, e também papéis de entregador/funcionário)
- [[ContaPagar]] (fornecedor)
- [[Bling]], [[Stone]] (fluxos de conciliação e sincronização)

## Não identificado
- ❓ Confirmar com o responsável se o reaproveitamento de `Cliente` para fornecedor/entregador é uma decisão de modelagem deliberada de longo prazo ou dívida técnica a ser separada futuramente.
