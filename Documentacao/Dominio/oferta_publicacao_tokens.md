---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — oferta_publicacao_tokens

Ver [[oferta_publicacoes]].

## Definição
Índice público global: token opaco → tenant/publicação. Permite compartilhar uma oferta publicamente (ex.: `/ofertas/{token}`) sem o visitante precisar saber o tenant de antemão.

## Confirmado no código
- Modelo: `ofertas_estudio_models.py:38-55` (`OfertaPublicacaoToken`). `Base` puro (não usa mixin multi-tenant — `tenant_id` é coluna solta).
- ⚠️ Design incomum mas intencional: a PK é o próprio `token` (String(64)), não um `id` autoincrement — desenhado deliberadamente para lookup público cross-tenant.

## Relacionamentos
- FK de saída: `publicacao_id → oferta_publicacoes.id` (CASCADE, unique).
- Sem referências de entrada.

## Utilizado por
- Criado junto com `OfertaPublicacao.indice_publico` (`ofertas_estudio_routes.py:422`).

## Não identificado
- Vale nota de segurança: por ser um índice público cross-tenant por design, qualquer bug de geração de token fraco teria impacto direto — vale confirmar entropia/geração do token se for auditar segurança.
