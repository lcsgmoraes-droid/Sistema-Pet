"""
Serviço de Geração Automática de Comissões
Chamado ao finalizar vendas para calcular e registrar comissões
"""

import logging
from decimal import Decimal
from typing import Optional, Dict
from app.tenancy.context import get_current_tenant_id
from app.utils.tenant_safe_sql import TenantSafeSQLError, execute_tenant_safe

logger = logging.getLogger(__name__)


CONFIGURACAO_COMISSAO_COLUMNS = """
            id,
            funcionario_id,
            tipo,
            referencia_id,
            tipo_calculo,
            percentual,
            percentual_loja,
            desconta_taxa_cartao,
            desconta_impostos,
            desconta_custo_entrega,
            comissao_venda_parcial,
            permite_edicao_venda,
            observacoes,
            ativo
"""


def _configuracao_row_to_dict(config) -> Dict:
    return {
        "id": config[0],
        "funcionario_id": config[1],
        "tipo": config[2],
        "referencia_id": config[3],
        "tipo_calculo": config[4] or "percentual",
        "percentual": config[5],
        "percentual_loja": config[6],
        "desconta_taxa_cartao": config[7] if config[7] is not None else True,
        "desconta_impostos": config[8] if config[8] is not None else True,
        "desconta_custo_entrega": config[9] if config[9] is not None else False,
        "comissao_venda_parcial": config[10] if config[10] is not None else True,
        "permite_edicao_venda": config[11] if config[11] is not None else True,
        "observacoes": config[12] or "",
        "ativo": config[13],
    }


def _require_tenant_id(tenant_id=None):
    resolved_tenant_id = tenant_id if tenant_id is not None else get_current_tenant_id()
    if resolved_tenant_id is None or resolved_tenant_id == "":
        raise TenantSafeSQLError(
            "tenant_id ausente em comissoes_service. Informe tenant_id ou configure "
            "app.tenancy.context antes de calcular comissoes."
        )
    return resolved_tenant_id


def buscar_configuracao_comissao(
    db,
    funcionario_id: int,
    produto_id: int,
    tenant_id=None,
) -> Optional[Dict]:
    """
    Busca configuração de comissão seguindo hierarquia:
    1. Produto (mais específico - prioridade)
    2. Categoria do produto (sobe recursivamente pela hierarquia)
    3. Regra geral do funcionario

    Retorna: dict com config ou None
    """
    tenant_id = _require_tenant_id(tenant_id)

    try:
        # 1. Tentar buscar config de PRODUTO
        result = execute_tenant_safe(
            db,
            f"""
            SELECT {CONFIGURACAO_COMISSAO_COLUMNS}
            FROM comissoes_configuracao
            WHERE funcionario_id = :func_id
              AND tipo = 'produto'
              AND referencia_id = :ref_id
              AND ativo = true
              AND {{tenant_filter}}
        """,
            {"func_id": funcionario_id, "ref_id": produto_id},
            tenant_id=tenant_id,
        )

        config = result.fetchone()
        if config:
            logger.info(f"✅ Config encontrada: PRODUTO {produto_id}")
            return _configuracao_row_to_dict(config)

        # 2. Buscar categoria do produto
        result = execute_tenant_safe(
            db,
            """
            SELECT categoria_id
            FROM produtos
            WHERE id = :produto_id
              AND {tenant_filter}
        """,
            {"produto_id": produto_id},
            tenant_id=tenant_id,
        )

        row = result.fetchone()
        if not row or not row[0]:
            logger.warning(f"⚠️ Produto {produto_id} sem categoria")
            categoria_atual_id = None
        else:
            categoria_atual_id = row[0]

        # 3. Subir recursivamente pela hierarquia de categorias até encontrar configuração
        max_depth = 10  # Proteção contra loops infinitos
        depth = 0

        while categoria_atual_id and depth < max_depth:
            # Tentar buscar config para esta categoria
            result = execute_tenant_safe(
                db,
                f"""
                SELECT {CONFIGURACAO_COMISSAO_COLUMNS}
                FROM comissoes_configuracao
                WHERE funcionario_id = :func_id
                  AND tipo = 'categoria'
                  AND referencia_id = :ref_id
                  AND ativo = true
                  AND {{tenant_filter}}
            """,
                {"func_id": funcionario_id, "ref_id": categoria_atual_id},
                tenant_id=tenant_id,
            )

            config = result.fetchone()
            if config:
                logger.info(
                    f"✅ Config encontrada: CATEGORIA {categoria_atual_id} (nível {depth})"
                )
                return _configuracao_row_to_dict(config)

            # Buscar categoria pai
            result = execute_tenant_safe(
                db,
                """
                SELECT categoria_pai_id
                FROM categorias
                WHERE id = :cat_id
                  AND {tenant_filter}
            """,
                {"cat_id": categoria_atual_id},
                tenant_id=tenant_id,
            )

            row = result.fetchone()
            categoria_atual_id = row[0] if row else None
            depth += 1

        # 4. Usar regra geral do funcionario como fallback para todos os itens
        result = execute_tenant_safe(
            db,
            f"""
            SELECT {CONFIGURACAO_COMISSAO_COLUMNS}
            FROM comissoes_configuracao
            WHERE funcionario_id = :func_id
              AND tipo = 'geral'
              AND referencia_id = 0
              AND ativo = true
              AND {{tenant_filter}}
        """,
            {"func_id": funcionario_id},
            tenant_id=tenant_id,
        )

        config = result.fetchone()
        if config:
            logger.info(
                f"✅ Config encontrada: REGRA GERAL para funcionario {funcionario_id}"
            )
            return _configuracao_row_to_dict(config)

        logger.warning(
            f"⚠️ Nenhuma config encontrada para funcionário {funcionario_id} e produto {produto_id} (verificou {depth} níveis)"
        )
        return None

    except TenantSafeSQLError:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao buscar config comissão: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return None


def calcular_comissao_item(
    config: Dict,
    valor_bruto_item: Decimal,
    valor_liquido_item: Decimal,
    custo_unitario: Decimal,
    quantidade: Decimal,
    proporcao_item: Decimal,
    custos_rateados: Dict,
    tem_entrega: bool,
) -> Dict:
    """
    Calcula comissão de um item baseado na configuração
    NOVA ARQUITETURA: Custos reduzem a BASE, nunca a comissão pronta

    Args:
        config: Configuração de comissão do funcionário
        valor_bruto_item: Valor bruto do item (preço × qtd)
        valor_liquido_item: Valor líquido do item (bruto - desconto)
        custo_unitario: Custo unitário do produto
        quantidade: Quantidade vendida
        proporcao_item: Proporção deste item no total de produtos LÍQUIDOS
        custos_rateados: Dict com taxa_cartao_produtos, impostos_produtos, custo_operacional_entrega
        tem_entrega: Se a venda tem entrega

    Returns:
        Dict com valores calculados
    """
    tipo_calculo = config["tipo_calculo"]
    percentual = Decimal(str(config["percentual"]))

    custo_total = custo_unitario * quantidade

    # ETAPA 4: CALCULAR BASE DE COMISSÃO
    if tipo_calculo == "lucro":
        # Base inicial = valor líquido - custo produto
        base = valor_liquido_item - custo_total
    else:  # tipo_calculo == 'percentual'
        # Base inicial = valor líquido
        base = valor_liquido_item

    # Ratear custos pela proporção deste item
    taxa_cartao_item = (
        Decimal(str(custos_rateados.get("taxa_cartao_produtos", 0))) * proporcao_item
    )
    impostos_item = (
        Decimal(str(custos_rateados.get("impostos_produtos", 0))) * proporcao_item
    )
    taxa_entregador_item = (
        Decimal(str(custos_rateados.get("taxa_paga_entregador", 0))) * proporcao_item
    )
    custo_operacional_item = (
        Decimal(str(custos_rateados.get("custo_operacional_entrega", 0)))
        * proporcao_item
    )
    receita_taxa_entrega_item = (
        Decimal(str(custos_rateados.get("taxa_entrega_receita", 0))) * proporcao_item
    )

    # ADICIONAR RECEITA da taxa de entrega (cliente paga, empresa recebe)
    if receita_taxa_entrega_item > 0:
        base += receita_taxa_entrega_item

    # Aplicar deduções CONDICIONAIS
    if config.get("desconta_taxa_cartao", True):
        base -= taxa_cartao_item

    if config.get("desconta_impostos", True):
        base -= impostos_item

    if config.get("desconta_custo_entrega", True) and tem_entrega:
        # Deduzir AMBOS: taxa paga ao entregador + custo operacional
        base -= taxa_entregador_item
        base -= custo_operacional_item

    # ETAPA 5: APLICAR PERCENTUAL
    comissao_bruta = base * (percentual / 100)
    comissao_final = max(Decimal("0"), comissao_bruta)

    return {
        "valor_comissao": float(comissao_final),
        "base_calculo": float(base),
        "tipo_calculo": tipo_calculo,
        "percentual": float(percentual),
        "valor_bruto": float(valor_bruto_item),
        "valor_liquido": float(valor_liquido_item),
        "custo_item": float(custo_total),
        "taxa_cartao_item": float(taxa_cartao_item),
        "impostos_item": float(impostos_item),
        "taxa_entregador_item": float(taxa_entregador_item),
        "custo_operacional_item": float(custo_operacional_item),
        "receita_taxa_entrega_item": float(receita_taxa_entrega_item),
        "percentual_impostos": custos_rateados.get("percentual_impostos", 0),
    }
