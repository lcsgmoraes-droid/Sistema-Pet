---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — compras_pendencias_fornecedor

Ver [[notas_entrada]], [[pedidos_compra]], [[Cliente]], [[compras_pendencias_fornecedor_itens]], [[compras_pendencias_fornecedor_historico]].

## Definição
Pendência aberta com um fornecedor por divergência encontrada na conferência de uma nota de entrada (falta, avaria, valor divergente) — inclui fluxo de comunicação por e-mail.

## Confirmado no código
- Modelo: `compras_pendencias_models.py:19-83` (`CompraPendenciaFornecedor`).
- Colunas: `codigo`, `status` (default `aberta`), `origem` (default `conferencia_nf`), `tipo` (default `divergencia_fornecedor`), fluxo de e-mail (`email_destinatario`, `email_assunto`, `email_mensagem`, `email_enviado_em`), `pdf_gerado_em`, resolução (`resolvida_em`, `resolucao_observacao`).
- ⚠️ FK fantasma: `fornecedor_id` sem `ForeignKey()`, resolvido contra [[Cliente]].
- ⚠️ Desnormalização deliberada: `fornecedor_nome`, `fornecedor_cnpj`, `numero_nota`, `numero_pedido` são snapshot em texto no momento da criação (correto para histórico de comunicação), podendo divergir do estado atual das tabelas de origem se estas forem editadas depois.

## Relacionamentos
- FKs de saída: `nota_entrada_id → notas_entrada.id` (nullable), `pedido_compra_id → pedidos_compra.id` (nullable), `user_id → users.id`.
- Referenciada por: [[compras_pendencias_fornecedor_itens]]`.pendencia_id` (cascade delete-orphan), [[compras_pendencias_fornecedor_historico]]`.pendencia_id` (cascade delete-orphan).

## Utilizado por
- Criação: `compras_pendencias_criacao_routes.py:38-70` (`POST /notas/{nota_id}`), a partir de itens divergentes.
- Consulta: `compras_pendencias_consulta_routes.py`.
- Documentos/e-mail: `compras_pendencias_documentos.py`.

## Não identificado
- Nada além do já citado.
