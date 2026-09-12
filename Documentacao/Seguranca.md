---
tipo: eixo
atualizado: 2026-09-12
---

# Segurança

Um dos 4 grandes eixos. Ver [[README]]. Análise feita por agente de exploração dedicado em 2026-09-12, lendo código real (não apenas documentação declarativa), sem execução ofensiva.

## Documentos desta área

- [[Autenticacao]] — JWT, sessões, bloqueio de conta, MFA (não ativo)
- [[Autorizacao]] — RBAC por tenant, isolamento multiempresa, BOLA/IDOR
- [[API-Security]] — rate limiting, CORS, webhooks, uploads
- [[Secrets]] — inventário de variáveis sensíveis, busca por hardcode
- [[Vulnerabilidades]] — lista consolidada de achados por severidade

## Resumo executivo

**Pontos fortes confirmados:**
- Isolamento multi-tenant em **duas camadas independentes** (Row Level Security no Postgres + filtro automático fail-closed no SQLAlchemy) — ver [[Autorizacao]] e [[Banco-de-Dados]].
- CORS fechado por padrão, sem wildcard, com bloqueio explícito no código.
- Nenhum secret hardcoded encontrado no código-fonte.
- Sessões revogáveis server-side, bloqueio de conta após 5 tentativas falhas.
- Upload de imagem de produto tratado com cuidado real (revalidação, nome gerado pelo servidor).

**Principais riscos (detalhe em [[Vulnerabilidades]]):**
1. 🟠 MFA existe no schema mas não está ativo em nenhum fluxo de login real.
2. 🟠 Rate limiting customizado é in-memory e perde eficácia com múltiplos processos/réplicas.
3. 🟠 Campo de senha criptografada da Stone (`conciliacao_password_enc`) sem implementação de cifragem confirmada — necessita validação urgente.
4. 🟡 Upload de XML de NF-e sem limite de tamanho.
5. 🟡 Log DEBUG expõe e-mail do usuário.
6. 🔵 Rota de webhook Bling sem assinatura existe como arquivo mas não está registrada (código morto, não exposto).

## Relação com os outros eixos

```text
Funcionalidade (ex: [[PDV-Vendas]])
      → usa Autenticacao/Autorizacao em toda rota
      → integrações externas (ver [[Integracoes]]) têm webhooks cobertos aqui em API-Security
      → dados sensíveis do domínio (ver docs/CATALOGO_DADOS_CRITICOS_LGPD.md, fonte já existente e aproveitada)
```

## Fonte cruzada já existente aproveitada

`docs/CATALOGO_DADOS_CRITICOS_LGPD.md` (538 linhas, 16 domínios de dados classificados) e `docs/GOVERNANCA_ENTERPRISE.md` (matriz de 14 áreas) já existiam antes desta análise e cobrem privacidade/LGPD com profundidade que não foi replicada aqui para evitar duplicação — consulte-os para: hipóteses legais de tratamento, papéis de operador/suboperador, retenção por domínio de dado. A área "Segurança e privacidade" está classificada como **Parcial forte** nesse documento; esta análise técnica corrobora essa avaliação com evidência direta de código.

## Não identificado

- ❓ Regras de branch protection do GitHub (não visível via código, ver [[CI-CD]]).
- ❓ Se há WAF (Web Application Firewall) na frente do Nginx em produção.
