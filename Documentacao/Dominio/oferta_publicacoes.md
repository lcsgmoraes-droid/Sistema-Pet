---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — oferta_publicacoes

Ver [[oferta_publicacao_tokens]], [[Produto]].

## Definição
Snapshot imutável de uma arte promocional publicada (Estúdio de Ofertas — gerador de artes tipo jornal de ofertas).

## Confirmado no código
- Modelo: `ofertas_estudio_models.py:12-35` (`OfertaPublicacao`).
- Colunas: `titulo`, `periodicidade` (default "avulsa"), `tipo_arte` (default "jornal"), `formato` (default "quadrado"), `inicio_em`/`fim_em`/`expira_em`/`desativada_em`, `imagens_urls` (JSON), `produtos_snapshot` (JSON — **snapshot de produtos, não FK**), `configuracao` (JSON).
- Relationship `indice_publico` → [[oferta_publicacao_tokens]], 1:1, `cascade="all, delete-orphan"`.
- Design intencional: não referencia `Produto` por FK — é deliberadamente desacoplado, preservando os preços/dados do momento da publicação mesmo que o produto mude depois.

## Relacionamentos
- FK de saída: `criado_por_id → users.id`.
- Referenciada por: [[oferta_publicacao_tokens]]`.publicacao_id` (unique, CASCADE).

## Utilizado por
- `ofertas_estudio_routes.py:391` (criação).

## Não identificado
- Nada notável — a ausência de FK para produto é design deliberado (snapshot), não um achado de risco.
