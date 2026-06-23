"""
Fachada de compatibilidade da DRE por canal.

A implementacao fica em app.dre_canais.* para manter os modulos menores,
mas este arquivo continua exportando os nomes antigos usados por imports legados.
"""

from app.dre_canais.agregacao import (
    _bulk_cashback_por_venda,
    _bulk_comissoes_por_venda,
    _bulk_cupons_por_venda,
    _bulk_estoque_custos_por_venda,
    _bulk_taxa_operacional_por_venda,
    _formas_pagamento_map,
    _impostos_percentual,
    _obter_vendas_por_canal_legacy,
    _preparar_snapshots_vendas,
    _subcategorias_contas_map,
    _valor_snapshot_campo,
    agregar_contas_pagar_por_canal,
    agregar_fretes_sobre_compras,
    obter_despesas_operacionais,
    obter_vendas_por_canal,
)
from app.dre_canais.base import (
    CANAIS_CONFIG,
    CANAL_ALIASES,
    ORIGENS_DRE,
    _campo_zero,
    _canal_expr,
    _classificar_conta_dre,
    _conta_valor,
    _data_iso,
    _decimal,
    _eh_custo_de_venda_ja_vindo_da_venda,
    _filtro_status_venda_dre,
    _load_rentabilidade_snapshot,
    _normalizar_canal,
    _normalizar_forma_pagamento,
    _novo_canal,
    _periodo_label,
    _periodo_mes,
    _separar_receita_produto_servico,
    _snapshot_pronto,
    _texto_conta,
    _valor_item_bruto,
)
from app.dre_canais.detalhes import (
    CAMPOS_DETALHE_CONTAS,
    CAMPOS_DETALHE_VENDAS,
    _detalhes_contas_campo,
    _detalhes_vendas_campo,
    _paginar_detalhes,
    detalhar_linha_dre_por_canal,
)
from app.dre_canais.linhas import (
    _adicionar_linhas_campo,
    _linha_canal,
    _linha_total,
    _percentual,
    _somar,
    montar_linhas_dre_competencia,
)
from app.dre_canais.routes import gerar_dre_por_canais, router
from app.dre_canais.schemas import (
    DREDetalheItem,
    DREDetalheResponse,
    DREPorCanalResponse,
    LinhaCanal,
)

__all__ = [name for name in globals() if not name.startswith("__")]
