---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — arquivos_extrato_importados

Ver [[Usuario]], [[lancamentos_importados]].

## Definição
Histórico de upload de arquivo de extrato bancário para importação com IA.

## Confirmado no código
- Modelo: `ia/aba7_extrato_models.py:176-210` (`ArquivoExtratoImportado`).
- Colunas: `hash_arquivo`, `banco_detectado`, estatísticas de processamento.

## Relacionamentos
- FK de saída: `usuario_id → users.id`.

## Utilizado por
- Pipeline de importação de extrato bancário com IA.

## Não identificado
- Nada notável.
