---
tipo: integracao
atualizado: 2026-09-12
---

# Integração — Stone (conciliação de cartão)

Parte de [[Integracoes]]. Ver [[Financeiro]], [[Secrets]] (achado sobre `conciliacao_password_enc`).

## Identificação
- **Finalidade:** conciliação de recebíveis de cartão (Stone e também Cielo/Rede via detector de operadora) contra as vendas do PDV.

## Arquivos
`conciliacao_services_stone.py`, `conciliacao_cartao_routes.py`, `conciliacao_operadora_detector.py`, `conciliacao_helpers.py`, `parsers/ofx_parser.py`, modelo `stone_models.py`.

## Comunicação
⚠️ **Não é uma integração de API/rede** — é **importação manual de arquivo** (CSV/OFX) feita pelo operador do tenant. Sem chamada HTTP a um provedor Stone em tempo real.

## Autenticação
Não se aplica (sem API key de rede) — a autenticação é a do próprio usuário do CorePet fazendo o upload, sujeita às permissões normais de tenant/role.

## Webhook
Não há.

## Falhas, retry e resiliência
- Não se aplica timeout/retry de rede.
- Hash MD5/SHA-256 do arquivo detecta duplicidade de importação.
- Toda a operação roda em transação com rollback em caso de erro.

## Achado de segurança relevante
O modelo `StoneConfig` tem um campo `conciliacao_password_enc`, documentado no código como "Senha CRIPTOGRAFADA (AES-256-CBC)", mas **nenhum código foi encontrado que leia ou escreva esse campo**, e a dependência `pycryptodome` (instalada especificamente para esse fim, segundo comentário no `requirements.txt`) **não é importada em lugar nenhum**. Ver detalhe e recomendação em [[Secrets]] e [[Vulnerabilidades]] (item 3, 🟠 Alto).

## Fluxo
```text
Operador exporta extrato Stone/Cielo/Rede (CSV/OFX)
  → upload manual no CorePet
  → parser detecta operadora + evita duplicidade (hash)
  → concilia contra VendaPagamento
```

## Dependências de funcionalidade
[[Financeiro]] (conciliação bancária/cartão), [[PDV-Vendas]] (origem das vendas conciliadas).

## Não identificado
- ❓ Se existe (ou já existiu) um plano de integração via API real da Stone, dado que a dependência de criptografia foi instalada mas não usada.
