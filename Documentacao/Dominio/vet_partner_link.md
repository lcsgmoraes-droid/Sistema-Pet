---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — vet_partner_link

Ver [[Tenant]], [[vet_procedimentos_consulta]], [[EmpresaGrupo]].

## Definição
Vínculo entre dois tenants (empresa dona da loja ↔ veterinário parceiro) — mecanismo de split financeiro e, notavelmente, de **compartilhamento controlado de dados entre tenants**.

## Confirmado no código
- Modelo: `veterinario_models.py:895-933` (`VetPartnerLink`). `Base` puro (não-tenant, por natureza liga dois tenants).
- Colunas: `empresa_tenant_id` (UUID), `vet_tenant_id` (UUID), `tipo_relacao` (`parceiro` | `funcionario`, default `parceiro`), `comissao_empresa_pct` (Numeric 5,2), `ativo`. Sem `ForeignKey()` reais para os UUIDs de tenant (consistente com o padrão do projeto, onde `tenant_id` não é FK).

## Relacionamentos
- Sem FK de banco real (tenant_id nunca é FK neste sistema).
- Usado logicamente por [[vet_procedimentos_consulta]] para decidir split financeiro.

## Utilizado por
- 🟠 **`tenancy/filters.py:98-102`** — usado para **expandir filtros de tenant**: um tenant "empresa" pode enxergar dados do tenant "vet" parceiro vinculado. É um caso especial de compartilhamento de dados entre tenants no sistema multi-tenant, fora da mecânica normal de [[EmpresaGrupo]].
- `partner_utils.py` (helper de resolução do link ativo).
- `veterinario_financeiro.py:322-346` — determina se o veterinário opera em modo `parceiro` (financeiro separado, split via `comissao_empresa_pct`) ou `funcionario` (mesmo tenant da loja).
- `veterinario_core.py`, `veterinario_parcerias_routes.py` (CRUD do vínculo).

## Não identificado
- 🟠 **Recomenda-se auditoria de segurança**: este é um caso sensível e intencional de "vazamento controlado" de dados entre tenants — vale confirmar com o time que o filtro em `tenancy/filters.py` é sempre aplicado corretamente e não pode ser burlado (ex.: por uma rota que esqueça de aplicar o filtro expandido).
