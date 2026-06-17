"""
Serviço de Geração Automática de Comissões
Chamado ao finalizar vendas para calcular e registrar comissões
"""

import logging
from decimal import Decimal
from typing import Optional, Dict
from datetime import datetime
from app.utils.logger import StructuredLogger
from app.tenancy.context import get_current_tenant_id, set_tenant_context
from app.empresa_config_fiscal_models import EmpresaConfigFiscal
from app.utils.tenant_safe_sql import TenantSafeSQLError, execute_tenant_safe

logger = logging.getLogger(__name__)
struct_logger = StructuredLogger(__name__)


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


def gerar_comissoes_venda(
    venda_id: int,
    funcionario_id: int,
    valor_pago: Optional[Decimal] = None,
    forma_pagamento: Optional[str] = None,  # ✅ Nova: Forma de pagamento específica
    parcela_numero: int = 1,
    db=None,
    tenant_id=None,
):
    """
    Gera comissões para uma venda
    NOVA ARQUITETURA: 6 etapas lineares sem ajustes posteriores

    🔒 HARDENING 3 (SPRINT 3 - PASSO 2): Comissão proporcional a pagamentos parciais
    🔒 HARDENING 4 (SPRINT 3 - PARTE 3): Snapshot financeiro imutável

    PRINCÍPIO DE IMUTABILIDADE:
    - Comissão gerada = snapshot financeiro PERMANENTE
    - NUNCA recalcula comissões existentes
    - NUNCA consulta dados atuais de produto/custo
    - SEMPRE usa dados gravados em comissoes_itens

    Args:
        venda_id: ID da venda
        funcionario_id: ID do funcionário/veterinário
        valor_pago: Se informado, gera comissão proporcional (venda parcial)
        forma_pagamento: Forma de pagamento específica (para calcular taxa correta)
        parcela_numero: Número da parcela de pagamento (para idempotência)
        db: Sessão do SQLAlchemy (OBRIGATÓRIO para PostgreSQL)
    """
    if db is None:
        logger.error("❌ Sessão db é obrigatória para gerar_comissoes_venda")
        return {"success": False, "error": "Sessão db não fornecida"}

    try:
        # 🔒 VALIDAÇÃO 1: Status da venda
        tenant_id = _require_tenant_id(tenant_id)

        result = execute_tenant_safe(
            db,
            """
            SELECT id, total, status, desconto_valor, taxa_entrega, tem_entrega, data_venda, tenant_id, entregador_id 
            FROM vendas
            WHERE id = :venda_id
              AND {tenant_filter}
        """,
            {"venda_id": venda_id},
            tenant_id=tenant_id,
        )

        venda_row = result.fetchone()
        if not venda_row:
            logger.error(f"❌ Venda {venda_id} não encontrada")
            return {"success": False, "error": "Venda não encontrada"}

        # Converter row para dict
        venda = {
            "id": venda_row[0],
            "total": venda_row[1],
            "status": venda_row[2],
            "desconto_valor": venda_row[3],
            "taxa_entrega": venda_row[4],
            "tem_entrega": venda_row[5],
            "data_venda": venda_row[6],
            "tenant_id": venda_row[7] if venda_row[7] else tenant_id,
            "entregador_id": venda_row[8] if len(venda_row) > 8 else None,
        }

        # Validar status (apenas finalizada ou baixa_parcial podem gerar comissão)
        if venda["status"] not in ["finalizada", "baixa_parcial"]:
            logger.warning(
                f"⚠️ Tentativa de gerar comissão para venda {venda_id} com status '{venda['status']}'"
            )
            return {
                "success": False,
                "error": f"Venda com status '{venda['status']}' não gera comissão",
            }

        # 🔒 VALIDAÇÃO 2: IMUTABILIDADE - Comissões já existentes PARA ESTA PARCELA
        # PRINCÍPIO: Snapshot financeiro já criado = IMUTÁVEL
        result = execute_tenant_safe(
            db,
            """
            SELECT COUNT(*) as total 
            FROM comissoes_itens 
            WHERE venda_id = :venda_id
              AND funcionario_id = :func_id
              AND parcela_numero = :parcela
              AND {tenant_filter}
        """,
            {
                "venda_id": venda_id,
                "func_id": funcionario_id,
                "parcela": parcela_numero,
            },
            tenant_id=tenant_id,
        )

        count_row = result.fetchone()
        count = count_row[0] if count_row else 0

        if count > 0:
            # 🔒 SNAPSHOT FINANCEIRO JÁ EXISTE - BLOQUEIO DE RECÁLCULO
            struct_logger.warning(
                "COMMISSION_RECALCULATION_BLOCKED",
                "Tentativa de recalcular comissão bloqueada - snapshot financeiro imutável",
                venda_id=venda_id,
                funcionario_id=funcionario_id,
                parcela=parcela_numero,
                reason="Snapshot financeiro já existe",
            )

            # ✅ Retorno idempotente (não é erro, apenas já foi processado)
            return {
                "success": True,
                "message": f"Comissões já geradas para parcela {parcela_numero}",
                "duplicated": True,
                "total_comissao": 0,
                "snapshot_preservado": True,  # Indica que o snapshot foi preservado
            }

        # 🔒 SNAPSHOT FINANCEIRO - Capturar dados DO MOMENTO da venda
        # IMPORTANTE: Estes dados serão gravados em comissoes_itens e NUNCA mais consultados
        # Mudanças futuras em produto/custo NÃO afetarão esta comissão
        result = execute_tenant_safe(
            db,
            """
            SELECT 
                vi.id,
                vi.produto_id,
                vi.quantidade,
                vi.preco_unitario,
                vi.subtotal,
                p.preco_custo,
                p.nome as produto_nome,
                v.valor_taxa_entregador
            FROM venda_itens vi
            JOIN produtos p ON vi.produto_id = p.id AND p.tenant_id = vi.tenant_id
            JOIN vendas v ON v.id = vi.venda_id AND v.tenant_id = vi.tenant_id
            WHERE vi.venda_id = :venda_id
              AND vi.{tenant_filter}
        """,
            {"venda_id": venda_id},
            tenant_id=tenant_id,
        )

        itens_rows = result.fetchall()
        if not itens_rows:
            logger.warning(f"⚠️ Venda {venda_id} sem itens")
            return {"success": False, "error": "Venda sem itens"}

        # Converter rows para dicts
        itens = []
        valor_taxa_entregador_venda = Decimal("0")
        for row in itens_rows:
            itens.append(
                {
                    "id": row[0],
                    "produto_id": row[1],
                    "quantidade": row[2],
                    "preco_unitario": row[3],
                    "subtotal": row[4],
                    "preco_custo": row[5],
                    "produto_nome": row[6],
                }
            )
            # Capturar valor pago ao entregador (mesmo valor para todos os itens da venda)
            if row[7]:
                valor_taxa_entregador_venda = Decimal(str(row[7]))

        logger.info(f"🔄 Gerando comissões para venda {venda_id} - {len(itens)} itens")

        # ═══════════════════════════════════════════════════════════
        # ETAPA 1: NORMALIZAÇÃO DOS ITENS
        # ═══════════════════════════════════════════════════════════

        total_venda = Decimal(str(venda["total"]))
        taxa_entrega_cliente = Decimal(str(venda["taxa_entrega"] or 0))
        desconto_total_venda = Decimal(str(venda["desconto_valor"] or 0))
        valor_pago_decimal = (
            Decimal(str(valor_pago)) if valor_pago is not None else None
        )
        pagamento_parcial = (
            valor_pago_decimal is not None
            and valor_pago_decimal > Decimal("0")
            and valor_pago_decimal < total_venda - Decimal("0.01")
        )

        # Calcular soma total BRUTA (para ratear desconto)
        soma_valores_brutos = Decimal("0")
        itens_normalizados = []

        for item in itens:
            valor_bruto_item = Decimal(str(item["preco_unitario"])) * Decimal(
                str(item["quantidade"])
            )
            soma_valores_brutos += valor_bruto_item

            itens_normalizados.append(
                {
                    "item_id": item["id"],
                    "produto_id": item["produto_id"],
                    "produto_nome": item["produto_nome"],
                    "quantidade": Decimal(str(item["quantidade"])),
                    "preco_unitario": Decimal(str(item["preco_unitario"])),
                    "custo_unitario": Decimal(str(item["preco_custo"])),
                    "valor_bruto": valor_bruto_item,
                    "desconto_item": Decimal("0"),
                    "valor_liquido": Decimal("0"),
                }
            )

        # Ratear desconto proporcionalmente ao valor BRUTO
        soma_valores_liquidos = Decimal("0")
        for item_norm in itens_normalizados:
            if soma_valores_brutos > 0:
                proporcao_desconto = item_norm["valor_bruto"] / soma_valores_brutos
                item_norm["desconto_item"] = desconto_total_venda * proporcao_desconto
            else:
                item_norm["desconto_item"] = Decimal("0")

            item_norm["valor_liquido"] = (
                item_norm["valor_bruto"] - item_norm["desconto_item"]
            )
            soma_valores_liquidos += item_norm["valor_liquido"]

        logger.info("📊 ETAPA 1 - Normalização:")
        logger.info(f"   Soma valores BRUTOS: R$ {float(soma_valores_brutos):.2f}")
        logger.info(f"   Desconto total: R$ {float(desconto_total_venda):.2f}")
        logger.info(f"   Soma valores LÍQUIDOS: R$ {float(soma_valores_liquidos):.2f}")

        # ═══════════════════════════════════════════════════════════
        # ETAPA 2: CÁLCULO DOS CUSTOS GLOBAIS
        # ═══════════════════════════════════════════════════════════

        # 🆕 BUSCAR TAXA DE CARTÃO DA FORMA DE PAGAMENTO ESPECÍFICA
        taxa_cartao_percentual = Decimal("0")

        # Se forma_pagamento foi fornecida, buscar taxa específica
        if forma_pagamento:
            result = execute_tenant_safe(
                db,
                """
                SELECT taxa_percentual, nome
                FROM formas_pagamento
                WHERE nome = :forma_pagamento
                  AND {tenant_filter}
            """,
                {"forma_pagamento": forma_pagamento},
                tenant_id=tenant_id,
            )
            pagamento = result.fetchone()

            if pagamento:
                taxa_percentual = Decimal(str(pagamento[0] or 0))
                forma_nome = pagamento[1]
                taxa_cartao_percentual = taxa_percentual
                logger.info(f"💳 Forma de pagamento (específica): {forma_nome}")
                logger.info(f"💳 Taxa aplicada: {float(taxa_cartao_percentual)}%")
            else:
                logger.warning(
                    f"⚠️ Forma de pagamento '{forma_pagamento}' não encontrada"
                )
        else:
            # Fallback: buscar último pagamento da venda
            result = execute_tenant_safe(
                db,
                """
                SELECT fp.taxa_percentual, fp.nome, vp.numero_parcelas
                FROM venda_pagamentos vp
                JOIN formas_pagamento fp ON fp.nome = vp.forma_pagamento AND fp.tenant_id = vp.tenant_id
                WHERE vp.venda_id = :venda_id
                  AND vp.{tenant_filter}
                ORDER BY vp.id DESC
                LIMIT 1
            """,
                {"venda_id": venda_id},
                tenant_id=tenant_id,
            )
            pagamento = result.fetchone()
            num_parcelas = 1

            if pagamento:
                taxa_percentual = Decimal(str(pagamento[0] or 0))
                forma_nome = pagamento[1]
                num_parcelas = pagamento[2] or 1

            # Se for crédito parcelado, buscar taxa específica da parcela
            if num_parcelas > 1:
                result_parcela = execute_tenant_safe(
                    db,
                    """
                    SELECT taxas_por_parcela
                    FROM formas_pagamento
                    WHERE nome = :nome
                      AND {tenant_filter}
                """,
                    {"nome": forma_nome},
                    tenant_id=tenant_id,
                )
                config_parcela = result_parcela.fetchone()

                if config_parcela and config_parcela[0]:
                    try:
                        import json

                        taxas_json = json.loads(config_parcela[0])
                        taxa_parcela = taxas_json.get(str(num_parcelas))
                        if taxa_parcela:
                            taxa_percentual = Decimal(str(taxa_parcela))
                            logger.info(
                                f"💳 Taxa cartão parcelado ({num_parcelas}x): {float(taxa_percentual)}%"
                            )
                    except Exception:
                        pass

                taxa_cartao_percentual = taxa_percentual
                logger.info(f"💳 Forma de pagamento (fallback): {forma_nome}")
                logger.info(f"💳 Taxa aplicada: {float(taxa_cartao_percentual)}%")
            else:
                logger.warning(
                    f"⚠️ Nenhuma forma de pagamento encontrada para venda {venda_id}"
                )

        # Buscar impostos da configuração fiscal da empresa (alíquota vigente Simples Nacional)
        impostos_percentual = Decimal("7.0")  # Fallback padrão
        try:
            config_fiscal = (
                db.query(EmpresaConfigFiscal)
                .filter(EmpresaConfigFiscal.tenant_id == tenant_id)
                .first()
            )
            if config_fiscal and config_fiscal.aliquota_simples_vigente is not None:
                impostos_percentual = Decimal(
                    str(config_fiscal.aliquota_simples_vigente)
                )
                logger.info(
                    f"📊 Impostos configurados (alíquota vigente): {float(impostos_percentual)}%"
                )
            else:
                logger.info(f"📊 Usando impostos padrão: {float(impostos_percentual)}%")
        except Exception as e:
            logger.warning(
                f"⚠️ Erro ao buscar configuração fiscal, usando impostos padrão 7%: {str(e)}"
            )
            impostos_percentual = Decimal("7.0")

        # Custos sobre TOTAL da venda
        taxa_cartao_total = total_venda * (taxa_cartao_percentual / 100)
        impostos_total = total_venda * (impostos_percentual / 100)

        # Segregar custos de PRODUTOS vs FRETE
        valor_produtos = total_venda - taxa_entrega_cliente
        proporcao_produtos = (
            valor_produtos / total_venda if total_venda > 0 else Decimal("1.0")
        )

        taxa_cartao_produtos = taxa_cartao_total * proporcao_produtos
        impostos_produtos = impostos_total * proporcao_produtos

        # 🚚 CUSTOS DE ENTREGA (se a venda tem entrega)
        # 1. Taxa paga ao entregador (parte da taxa de entrega que vai pro bolso do entregador)
        # 2. Custo operacional (combustível, manutenção da moto - custo fixo da empresa)
        taxa_paga_entregador = Decimal("0")
        custo_operacional_entrega = Decimal("0")

        if venda["tem_entrega"]:
            # Taxa paga ao entregador (já calculada no PDV)
            taxa_paga_entregador = valor_taxa_entregador_venda

            # Custo operacional fixo (combustível, manutenção)
            # Buscar do cadastro do entregador (campo taxa_fixa_entrega)
            try:
                entregador_id = venda.get("entregador_id")
                if entregador_id:
                    result_entregador = execute_tenant_safe(
                        db,
                        """
                        SELECT taxa_fixa_entrega, nome
                        FROM clientes
                        WHERE id = :entregador_id
                          AND {tenant_filter}
                    """,
                        {"entregador_id": entregador_id},
                        tenant_id=tenant_id,
                    )

                    entregador_data = result_entregador.fetchone()
                    if entregador_data and entregador_data[0]:
                        custo_operacional_entrega = Decimal(str(entregador_data[0]))
                        logger.info(
                            f"🚚 Custo operacional {entregador_data[1]}: R$ {float(custo_operacional_entrega):.2f}"
                        )
                    else:
                        custo_operacional_entrega = Decimal("0")
                        logger.info("🚚 Entregador sem custo operacional configurado")
                else:
                    custo_operacional_entrega = Decimal("0")
                    logger.info("🚚 Venda sem entregador definido")
            except Exception as e:
                logger.warning(
                    f"⚠️ Erro ao buscar custo operacional do entregador: {str(e)}"
                )
                custo_operacional_entrega = Decimal("0")

        logger.info("📊 ETAPA 2 - Custos Globais:")
        logger.info(f"   Taxa cartão TOTAL: R$ {float(taxa_cartao_total):.2f}")
        logger.info(f"   Impostos TOTAL: R$ {float(impostos_total):.2f}")
        logger.info(f"   Proporção produtos: {float(proporcao_produtos) * 100:.1f}%")
        logger.info(f"   Taxa cartão PRODUTOS: R$ {float(taxa_cartao_produtos):.2f}")
        logger.info(f"   Impostos PRODUTOS: R$ {float(impostos_produtos):.2f}")
        logger.info(f"   Taxa paga ao entregador: R$ {float(taxa_paga_entregador):.2f}")
        logger.info(
            f"   Custo operacional entrega: R$ {float(custo_operacional_entrega):.2f}"
        )

        # ═══════════════════════════════════════════════════════════
        # ETAPA 3: RATEIO DE CUSTOS POR ITEM (BASE LÍQUIDA)
        # ═══════════════════════════════════════════════════════════

        custos_rateados = {
            "taxa_cartao_produtos": float(taxa_cartao_produtos),
            "impostos_produtos": float(impostos_produtos),
            "taxa_paga_entregador": float(taxa_paga_entregador),
            "custo_operacional_entrega": float(custo_operacional_entrega),
            "taxa_entrega_receita": float(
                taxa_entrega_cliente
            ),  # Receita da taxa de entrega cobrada do cliente
            "percentual_impostos": float(
                impostos_percentual
            ),  # Percentual de impostos aplicado
        }

        total_comissao = Decimal("0")
        comissoes_geradas = []

        # ═══════════════════════════════════════════════════════════
        # ETAPAS 4, 5, 6: PARA CADA ITEM
        # ═══════════════════════════════════════════════════════════

        for item_norm in itens_normalizados:
            # Buscar configuração de comissão
            config = buscar_configuracao_comissao(
                db,
                funcionario_id,
                item_norm["produto_id"],
                tenant_id=tenant_id,
            )

            if not config:
                logger.warning(
                    f"⚠️ Sem config de comissão para produto {item_norm['produto_id']}"
                )
                continue

            # Verificar se gera comissão em venda parcial
            if pagamento_parcial and not config.get("comissao_venda_parcial", True):
                logger.info(
                    f"⏭️ Produto {item_norm['produto_id']} não gera comissão parcial"
                )
                continue

            # Calcular proporção deste item no total de produtos LÍQUIDOS
            proporcao_item = (
                item_norm["valor_liquido"] / soma_valores_liquidos
                if soma_valores_liquidos > 0
                else Decimal("0")
            )

            logger.info(f"📦 Item {item_norm['produto_nome']}:")
            logger.info(f"   Valor bruto: R$ {float(item_norm['valor_bruto']):.2f}")
            logger.info(f"   Desconto: R$ {float(item_norm['desconto_item']):.2f}")
            logger.info(f"   Valor líquido: R$ {float(item_norm['valor_liquido']):.2f}")
            logger.info(f"   Proporção: {float(proporcao_item) * 100:.2f}%")

            # Calcular comissão do item
            calculo = calcular_comissao_item(
                config=config,
                valor_bruto_item=item_norm["valor_bruto"],
                valor_liquido_item=item_norm["valor_liquido"],
                custo_unitario=item_norm["custo_unitario"],
                quantidade=item_norm["quantidade"],
                proporcao_item=proporcao_item,
                custos_rateados=custos_rateados,
                tem_entrega=venda["tem_entrega"],
            )

            logger.info(f"   Base de cálculo: R$ {calculo['base_calculo']:.2f}")
            logger.info(
                f"   Comissão ({calculo['tipo_calculo']} {calculo['percentual']}%): R$ {calculo['valor_comissao']:.2f}"
            )

            # 🔒 SPRINT 3 - PASSO 2: Calcular comissão proporcional ao valor pago
            valor_base_original = Decimal(str(calculo["valor_comissao"]))
            valor_base_comissionada = valor_base_original
            valor_base_calculo_final = Decimal(
                str(calculo["base_calculo"])
            )  # Base de cálculo (pode ser proporcional)
            percentual_proporcional = Decimal("100.00")

            if valor_pago_decimal is not None and valor_pago_decimal > 0:
                # Proporção do pagamento em relação ao total da venda
                total_venda_decimal = Decimal(str(venda["total"]))
                if total_venda_decimal > 0:
                    percentual_proporcional = (
                        valor_pago_decimal / total_venda_decimal
                    ) * Decimal("100")
                    proporcao_pagamento = valor_pago_decimal / total_venda_decimal

                    # Aplicar proporção na base de cálculo E na comissão
                    valor_base_calculo_final = (
                        Decimal(str(calculo["base_calculo"])) * proporcao_pagamento
                    )
                    valor_base_comissionada = valor_base_original * proporcao_pagamento
                    calculo["valor_comissao"] = float(valor_base_comissionada)

                    logger.info("💰 COMISSÃO PROPORCIONAL:")
                    logger.info(
                        f"   Valor total venda: R$ {float(total_venda_decimal):.2f}"
                    )
                    logger.info(f"   Valor pago: R$ {float(valor_pago_decimal):.2f}")
                    logger.info(
                        f"   Percentual aplicado: {float(percentual_proporcional):.2f}%"
                    )
                    logger.info(f"   Base original: R$ {calculo['base_calculo']:.2f}")
                    logger.info(
                        f"   Base proporcional: R$ {float(valor_base_calculo_final):.2f}"
                    )
                    logger.info(
                        f"   Comissão original: R$ {float(valor_base_original):.2f}"
                    )
                    logger.info(
                        f"   Comissão proporcional: R$ {float(valor_base_comissionada):.2f}"
                    )

            # Registrar comissão do item
            execute_tenant_safe(
                db,
                """
                INSERT INTO comissoes_itens (
                    venda_id, venda_item_id, funcionario_id, produto_id,
                    data_venda, quantidade, valor_venda, valor_custo,
                    tipo_calculo, valor_base_calculo, percentual_comissao, 
                    valor_comissao, valor_comissao_gerada, percentual_pago, status,
                    valor_base_original, valor_base_comissionada, percentual_aplicado,
                    valor_pago_referencia, parcela_numero, tenant_id,
                    taxa_cartao_item, impostos_item, taxa_entregador_item, custo_operacional_item, 
                    receita_taxa_entrega_item, percentual_impostos, forma_pagamento,
                    data_criacao
                ) VALUES (
                    :venda_id, :venda_item_id, :funcionario_id, :produto_id,
                    :data_venda, :quantidade, :valor_venda, :valor_custo,
                    :tipo_calculo, :valor_base_calculo, :percentual_comissao,
                    :valor_comissao, :valor_comissao_gerada, :percentual_pago, 'pendente',
                    :valor_base_original, :valor_base_comissionada, :percentual_aplicado,
                    :valor_pago_referencia, :parcela_numero, :tenant_id,
                    :taxa_cartao_item, :impostos_item, :taxa_entregador_item, :custo_operacional_item, 
                    :receita_taxa_entrega_item, :percentual_impostos, :forma_pagamento,
                    CURRENT_TIMESTAMP
                )
            """,
                {
                    "venda_id": venda_id,
                    "venda_item_id": item_norm["item_id"],
                    "funcionario_id": funcionario_id,
                    "produto_id": item_norm["produto_id"],
                    "data_venda": venda["data_venda"]
                    if "data_venda" in venda.keys()
                    else datetime.now().date(),
                    "quantidade": float(item_norm["quantidade"]),
                    "valor_venda": calculo["valor_liquido"],
                    "valor_custo": calculo["custo_item"],
                    "tipo_calculo": calculo["tipo_calculo"],
                    "valor_base_calculo": float(
                        valor_base_calculo_final
                    ),  # ✅ Base proporcional ao pagamento
                    "percentual_comissao": calculo["percentual"],
                    "valor_comissao": calculo["valor_comissao"],
                    "valor_comissao_gerada": calculo["valor_comissao"],
                    "percentual_pago": float(percentual_proporcional),
                    "valor_base_original": float(valor_base_original),
                    "valor_base_comissionada": float(valor_base_comissionada),
                    "percentual_aplicado": float(percentual_proporcional),
                    "valor_pago_referencia": float(valor_pago) if valor_pago else None,
                    "parcela_numero": parcela_numero,
                    "tenant_id": venda.get("tenant_id"),
                    "taxa_cartao_item": calculo.get("taxa_cartao_item", 0),
                    "impostos_item": calculo.get("impostos_item", 0),
                    "taxa_entregador_item": calculo.get("taxa_entregador_item", 0),
                    "custo_operacional_item": calculo.get("custo_operacional_item", 0),
                    "receita_taxa_entrega_item": calculo.get(
                        "receita_taxa_entrega_item", 0
                    ),
                    "percentual_impostos": calculo.get("percentual_impostos", 0),
                    "forma_pagamento": forma_pagamento,  # ✅ Gravar forma de pagamento da comissão
                },
                tenant_id=tenant_id,
                require_tenant=False,
            )

            total_comissao += Decimal(str(calculo["valor_comissao"]))
            comissoes_geradas.append(
                {
                    "produto": item_norm["produto_nome"],
                    "valor": calculo["valor_comissao"],
                }
            )

        logger.info(f"✅ Total comissões FINAL: R$ {float(total_comissao):.2f}")

        db.commit()

        # 🔒 SPRINT 3 - PARTE 3: Log de snapshot financeiro criado
        struct_logger.info(
            "COMMISSION_SNAPSHOT_CREATED",
            "Snapshot financeiro imutável criado",
            venda_id=venda_id,
            funcionario_id=funcionario_id,
            parcela=parcela_numero,
            valor_total_venda=float(venda["total"]),
            valor_pago=float(valor_pago) if valor_pago else float(venda["total"]),
            valor_comissao=float(total_comissao),
            quantidade_itens=len(comissoes_geradas),
        )

        # 🔒 SPRINT 3 - PASSO 2: Log estruturado de sucesso (backward compatibility)
        if pagamento_parcial:
            struct_logger.info(
                "COMMISSION_PARTIAL_GENERATED",
                "Comissão parcial gerada",
                venda_id=venda_id,
                funcionario_id=funcionario_id,
                parcela=parcela_numero,
                valor_pago=float(valor_pago_decimal),
                valor_comissao=float(total_comissao),
            )
        else:
            struct_logger.info(
                "COMMISSION_GENERATED",
                "Comissão gerada",
                venda_id=venda_id,
                funcionario_id=funcionario_id,
                valor_comissao=float(total_comissao),
            )

        logger.info(f"✅ Comissões geradas: R$ {float(total_comissao):.2f}")
        logger.info(f"📋 Detalhes: {comissoes_geradas}")

        # ============================================================
        # PASSO 2 - Sprint 5: PROVISIONAR COMISSÕES (Conta a Pagar + DRE)
        # ============================================================
        # CONCEITO: Comissão é despesa por COMPETÊNCIA, não depende de pagamento
        # Gera automaticamente: Conta a Pagar + Lançamento DRE

        resultado_provisao = {
            "provisionada": False,
            "comissoes_provisionadas": 0,
            "valor_total": 0.0,
        }

        try:
            from app.comissoes_provisao import provisionar_comissoes_venda

            if tenant_id:
                logger.info(
                    "🎯 Iniciando provisão automática de comissões (PASSO 2)..."
                )

                # Definir contexto de tenant antes de chamar provisionar_comissoes_venda
                set_tenant_context(tenant_id)

                resultado_prov = provisionar_comissoes_venda(
                    venda_id=venda_id, tenant_id=tenant_id, db=db
                )

                if resultado_prov["success"]:
                    logger.info(
                        f"✅ PROVISÃO CONCLUÍDA: {resultado_prov['comissoes_provisionadas']} comissões, "
                        f"R$ {resultado_prov['valor_total']:.2f} - "
                        f"Contas a Pagar criadas: {resultado_prov['contas_criadas']}"
                    )
                    resultado_provisao = {
                        "provisionada": True,
                        "comissoes_provisionadas": resultado_prov[
                            "comissoes_provisionadas"
                        ],
                        "valor_total": resultado_prov["valor_total"],
                        "contas_criadas": resultado_prov["contas_criadas"],
                    }
                else:
                    logger.warning(
                        f"⚠️ Provisão não realizada: {resultado_prov['message']}"
                    )
            else:
                logger.warning(f"⚠️ tenant_id não encontrado para venda {venda_id}")

        except Exception as e:
            # ⚠️ Erro na provisão NÃO deve abortar a geração de comissões
            logger.error(
                f"⚠️ Erro ao provisionar comissões (venda {venda_id}): {str(e)}",
                exc_info=True,
            )
            # Continua normalmente - comissões já foram geradas

        return {
            "success": True,
            "total_comissao": float(total_comissao),
            "itens": comissoes_geradas,
            "duplicated": False,
            "provisao": resultado_provisao,  # ✅ Informação sobre a provisão
        }

    except Exception as e:
        db.rollback()
        logger.error(
            f"❌ Erro ao gerar comissões venda {venda_id}: {str(e)}", exc_info=True
        )
        return {"success": False, "error": str(e)}
