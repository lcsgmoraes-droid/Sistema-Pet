---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — regras_classificacao_dre

Ver [[dre_subcategorias]], [[historico_classificacao_dre]], [[regras_conciliacao]].

## Definição
Regra de aprendizado que classifica automaticamente contas a pagar/receber em subcategorias de DRE — motor paralelo a [[regras_conciliacao]] (que classifica movimentações bancárias, não contas).

## Confirmado no código
- Modelo: `dre_regras_models.py:50-132` (`RegraClassificacaoDRE`).
- Enums: `tipo_regra` (BENEFICIARIO/PALAVRA_CHAVE/TIPO_DOCUMENTO/COMBO/VENDA_AUTOMATICA/NOTA_ENTRADA), `origem` (SISTEMA/APRENDIZADO/USUARIO).
- Colunas: `criterios` (JSON flexível), `prioridade`, `confianca`, `aplicacoes_sucesso`/`aplicacoes_rejeitadas`, `sugerir_apenas`.
- Métodos de negócio embutidos no próprio model: `calcular_precisao()` e `deve_sugerir()` (linhas 116-132).
- ⚠️ FK fantasma: `criado_por_user_id` é `Integer` sem `ForeignKey("users.id")`.

## Relacionamentos
- FK de saída: `dre_subcategoria_id → dre_subcategorias.id` (NOT NULL).
- Referenciada por: [[historico_classificacao_dre]]`.regra_aplicada_id`.

## Utilizado por
- `dre_classificacao_service.py`, `financeiro/contas_pagar_classificacao.py`.

## Não identificado
- `criado_por_user_id` deveria ser FK real e não é.
