---
tipo: base
atualizado: 2026-09-12
---

# Domínio e Entidades

Conceitos de negócio centrais, confirmados nos modelos SQLAlchemy (`backend/app/*_models.py`). Ver [[Banco-de-Dados]] para o mapa completo de todos os ~50 arquivos de modelo; aqui estão detalhadas apenas as entidades estruturalmente centrais.

## Entidades documentadas

- [[Tenant]] — empresa, raiz do isolamento multiempresa
- [[Usuario]] — pessoa com login no sistema
- [[Role-Permission]] — RBAC por tenant
- [[Cliente]] — pessoa física/jurídica (compradora, e também reaproveitada como fornecedor/entregador)
- [[Pet]] — animal, tutor = [[Cliente]]
- [[Produto]] — item de catálogo/estoque
- [[Venda]] — transação do PDV (distinta de `Pedido` do e-commerce)
- [[ContaPagar]] — obrigação financeira do tenant
- [[ContaReceber]] — direito financeiro do tenant

## Relação estrutural (visão simplificada)

```text
Tenant
 ├─ Usuario ──(UserTenant)── Role ── Permission
 ├─ Cliente ── Pet
 ├─ Produto (categoria, marca, lote)
 ├─ Venda ── VendaItem (Produto, Pet, Lote)
 │          └─ ContaReceber (se a prazo)
 └─ ContaPagar (fornecedor = Cliente)
```

## Entidades confirmadas mas sem documento próprio (evitar arquivos redundantes)

Dezenas de outras entidades existem e estão listadas por domínio em [[Banco-de-Dados]] (ex.: `Caixa`, `EstoqueMovimentacao`, `BanhoTosaAgendamento`, `BillingWebhookEvent`, `EmpresaGrupo`). Criar um documento próprio para cada uma não agregaria valor além do que já está no mapa por domínio — só entidades com relacionamentos estruturais complexos ou centrais a múltiplas funcionalidades ganharam arquivo dedicado aqui.

## Não identificado

- ❓ Dicionário de dados campo-a-campo (fora do escopo desta fase; priorizado por entidade central, não por tabela completa, conforme instrução do escopo desta análise).
