---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — arquivos_evidencia

Ver [[conciliacao_importacoes]].

## Definição
Arquivo bruto importado (planilha de adquirente), preservado como evidência — comentário explícito no código: "nunca apagar informações importadas, arquivos são evidências".

## Confirmado no código
- Modelo: `conciliacao_models.py:203-272` (`ArquivoEvidencia`).
- Colunas: `hash_md5` (indexado, para detectar duplicatas), `hash_sha256`, `caminho_storage`, `periodo_inicio`/`fim`.

## Relacionamentos
- FK de saída: `criado_por_id → users.id` (RESTRICT, NOT NULL).
- Referenciada por: [[conciliacao_importacoes]]`.arquivo_evidencia_id` (RESTRICT, NOT NULL).

## Utilizado por
- `conciliacao_helpers.py`, `conciliacao_services_importacao.py`, `conciliacao_services_stone.py`.

## Não identificado
- Nada notável.
