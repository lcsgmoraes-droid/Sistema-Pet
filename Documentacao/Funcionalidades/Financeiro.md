---
tipo: funcionalidade
atualizado: 2026-09-12
---

# Financeiro

Ver [[Funcionalidades]], [[ContaPagar]], [[ContaReceber]], [[Stone]].

## Identificação
- **Menu:** Financeiro → Financeiro (submenu extenso: Dashboard, Vendas, Fluxo de Caixa, Bancos, DRE, Ponto de Equilíbrio, Imobilizado, Valor da Empresa, Contas a Pagar/Receber, Conciliação Bancária)
- **Rota frontend:** `/financeiro`
- **Módulo de rota:** `frontend/src/app/routes/FinanceRoutes.jsx`

## Objetivo
Gestão financeira completa: contas a pagar/receber, fluxo de caixa, DRE por canal, conciliação bancária e de cartão, ponto de equilíbrio.

## Usuários
Perfil `Financeiro` (bancos, contas, conciliações, DRE, fluxo de caixa) e `Administrador`.

## Backend (confirmado)
`contas_pagar_routes.py`, `contas_receber_routes.py` (+ variantes), `conciliacao_*_routes.py` (cartão, bancária), `financeiro_routes.py`, `lancamentos_routes.py`, `categorias_routes.py`, `dre_*_routes.py`, `simples_routes.py` (Simples Nacional), `auditoria_provisoes_routes.py`, `projecao_caixa_routes.py`. Pasta modular `backend/app/financeiro/` (`models_contas.py`, `models_caixa.py`, `models_conciliacao.py`, `models_catalogos.py`) segue o padrão-alvo documentado em `docs/BLUEPRINT_BACKEND.md` (um dos domínios que segue o padrão, ver [[Arquitetura]]).

## Banco de dados
`ContaPagar`, `ContaReceber`, `ContaBancaria`, `ExtratoBancario`, `MovimentacaoBancaria`, `ProvisaoAutomatica`, `CategoriaFinanceira` — ver [[ContaPagar]], [[ContaReceber]], [[Banco-de-Dados]].

## Integrações
[[Stone]] (conciliação de cartão via importação de arquivo — não API), conciliação bancária (formato OFX, `parsers/ofx_parser.py`).

## Segurança
⚠️ Achado relevante: campo de senha criptografada da Stone (`conciliacao_password_enc`) sem implementação de cifragem confirmada — ver [[Vulnerabilidades]] item 3 e [[Secrets]].

## Dependências
[[Venda]] (origem de conta a receber), [[Cliente]] (fornecedor em conta a pagar), [[Comissoes]] (categorias financeiras compartilhadas).

## Não identificado
- ❓ Regras de alçada/aprovação de lançamentos financeiros de maior valor.
