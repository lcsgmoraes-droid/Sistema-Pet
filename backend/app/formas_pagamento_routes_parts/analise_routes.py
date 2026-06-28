"""Rota de analise financeira de venda no PDV."""

from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.empresa_config_fiscal_models import EmpresaConfigFiscal
from app.financeiro_models import FormaPagamento
from app.formas_pagamento_models import ConfiguracaoImposto, FormaPagamentoTaxa
from app.produtos_models import Produto
from app.security.permissions_decorator import require_any_permission
from app.utils.logger import logger

from .schemas import (
    AlertaAnalise,
    AnaliseVendaRequest,
    AnaliseVendaResponse,
    DetalhamentoComissao,
    FormaPagamentoAnalise,
)

router = APIRouter()


@router.post("/analisar-venda", response_model=AnaliseVendaResponse)
@require_any_permission(("vendas.criar", "configuracoes.editar"))
def analisar_venda(
    dados: AnaliseVendaRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Analisa uma venda e retorna:
    - Composição financeira
    - Deduções (comissão, taxa cartão, impostos, custos)
    - Resultado (lucro e margem)
    - Alertas e sugestões
    """
    try:
        current_user, tenant_id = user_and_tenant

        # ===== 1. COMPOSIÇÃO FINANCEIRA =====
        total_produtos = sum(item.preco_venda * item.quantidade for item in dados.items)
        subtotal = total_produtos - dados.desconto - dados.taxa_entrega

        composicao = {
            "total_produtos": float(total_produtos),
            "desconto": float(dados.desconto),
            "taxa_entrega": float(dados.taxa_entrega),
            "subtotal": float(subtotal),
        }

        logger.info(f"📊 Analisando venda - Subtotal: R$ {subtotal:.2f}")

        # ===== 2. BUSCAR CUSTOS DOS PRODUTOS =====
        custos_total = 0
        detalhamento_comissoes = []
        itens_para_comissao = []

        try:
            for item in dados.items:
                produto = (
                    db.query(Produto)
                    .filter(
                        Produto.id == item.produto_id, Produto.tenant_id == tenant_id
                    )
                    .first()
                )
                if not produto:
                    logger.warning(f"⚠️ Produto {item.produto_id} não encontrado")
                    continue

                # Usar custo informado ou buscar do produto (campo correto: preco_custo)
                custo_item = (
                    item.custo if item.custo is not None else (produto.preco_custo or 0)
                )
                custos_total += custo_item * item.quantidade

                # Guardar os itens para calcular a comissão real depois que
                # taxas, descontos e impostos da venda estiverem fechados.
                itens_para_comissao.append((item, produto, custo_item))
        except Exception as e:
            logger.error(f"❌ Erro ao calcular custos e comissões: {e}")
            # Continuar com valores zerados em caso de erro
            custos_total = 0
            detalhamento_comissoes = []

        # ===== 4. PROCESSAR FORMAS DE PAGAMENTO E CALCULAR TAXAS =====
        # Compatibilidade: se não enviou formas_pagamento, usar forma_pagamento_id/parcelas antigo
        if not dados.formas_pagamento and dados.forma_pagamento_id:
            dados.formas_pagamento = [
                FormaPagamentoAnalise(
                    forma_pagamento_id=dados.forma_pagamento_id,
                    valor=subtotal,
                    parcelas=dados.parcelas,
                )
            ]

        detalhamento_taxas = []
        taxa_cartao_total = 0
        taxa_fixa_total = 0

        try:
            for forma_pag_item in dados.formas_pagamento:
                forma_pag = (
                    db.query(FormaPagamento)
                    .filter(
                        FormaPagamento.id == forma_pag_item.forma_pagamento_id,
                        FormaPagamento.tenant_id == tenant_id,
                    )
                    .first()
                )

                if not forma_pag:
                    logger.warning(
                        f"⚠️ Forma de pagamento {forma_pag_item.forma_pagamento_id} não encontrada"
                    )
                    continue

                logger.info(
                    f"\n🔍 Processando: {forma_pag.nome} - Valor: R$ {forma_pag_item.valor:.2f} - Parcelas: {forma_pag_item.parcelas}"
                )

                taxa_percentual = 0
                taxa_fixa = 0

                # PRIMEIRO: Se tem parcelamento, buscar do JSON taxas_por_parcela
                if (
                    forma_pag.permite_parcelamento
                    and forma_pag.taxas_por_parcela
                    and forma_pag_item.parcelas > 1
                ):
                    try:
                        import json

                        taxas_json = json.loads(forma_pag.taxas_por_parcela)
                        taxa_key = str(forma_pag_item.parcelas)

                        if taxa_key in taxas_json:
                            taxa_percentual = float(taxas_json[taxa_key])
                            logger.info(
                                f"   ✅ Taxa do JSON: {taxa_percentual}% para {forma_pag_item.parcelas}x"
                            )
                    except Exception as e:
                        logger.info(f"   ❌ Erro ao processar JSON: {e}")

                # SEGUNDO: Se não encontrou, usar campos taxa_percentual e taxa_fixa
                if taxa_percentual == 0 and forma_pag.taxa_percentual:
                    taxa_percentual = float(forma_pag.taxa_percentual)
                    logger.info(f"   ✅ Taxa percentual: {taxa_percentual}%")

                if forma_pag.taxa_fixa:
                    taxa_fixa = float(forma_pag.taxa_fixa)
                    logger.info(f"   ✅ Taxa fixa: R$ {taxa_fixa:.2f}")

                # TERCEIRO: Buscar na tabela formas_pagamento_taxas
                if taxa_percentual == 0:
                    taxa_obj = (
                        db.query(FormaPagamentoTaxa)
                        .filter(
                            FormaPagamentoTaxa.tenant_id == tenant_id,
                            FormaPagamentoTaxa.forma_pagamento_id
                            == forma_pag_item.forma_pagamento_id,
                            FormaPagamentoTaxa.parcelas == forma_pag_item.parcelas,
                        )
                        .first()
                    )

                    if taxa_obj:
                        taxa_percentual = float(taxa_obj.taxa_percentual)
                        logger.info(f"   ✅ Taxa da tabela: {taxa_percentual}%")

                # Calcular valores das taxas
                valor_taxa_percentual = forma_pag_item.valor * (taxa_percentual / 100)
                valor_taxa_fixa = taxa_fixa

                taxa_cartao_total += valor_taxa_percentual
                taxa_fixa_total += valor_taxa_fixa

                # Adicionar ao detalhamento
                detalhamento_taxas.append(
                    {
                        "forma": f"{forma_pag.nome} {forma_pag_item.parcelas}x"
                        if forma_pag_item.parcelas > 1
                        else forma_pag.nome,
                        "valor_pagamento": float(forma_pag_item.valor),
                        "taxa_percentual": float(taxa_percentual),
                        "valor_taxa_percentual": float(valor_taxa_percentual),
                        "taxa_fixa": float(taxa_fixa),
                        "valor_taxa_fixa": float(valor_taxa_fixa),
                        "total_taxas": float(valor_taxa_percentual + valor_taxa_fixa),
                    }
                )
        except Exception as e:
            logger.error(f"❌ Erro ao processar formas de pagamento: {e}")
            # Continuar sem taxas em caso de erro
            detalhamento_taxas = []
            taxa_cartao_total = 0
            taxa_fixa_total = 0

        taxa_cartao_valor = taxa_cartao_total + taxa_fixa_total

        # ===== 5. BUSCAR IMPOSTO PADRÃO =====
        imposto_percentual = 0
        imposto_valor = 0

        try:
            # 🔹 Prioridade 1: Simples Nacional (se ativo)
            config_fiscal = (
                db.query(EmpresaConfigFiscal)
                .filter(EmpresaConfigFiscal.tenant_id == tenant_id)
                .first()
            )

            if (
                config_fiscal
                and config_fiscal.simples_ativo
                and config_fiscal.aliquota_simples_vigente
            ):
                imposto_percentual = float(config_fiscal.aliquota_simples_vigente)
                imposto_valor = subtotal * (imposto_percentual / 100)
            else:
                # 🔹 Prioridade 2: Imposto padrão cadastrado
                config_imposto = (
                    db.query(ConfiguracaoImposto)
                    .filter(
                        ConfiguracaoImposto.tenant_id == tenant_id,
                        ConfiguracaoImposto.ativo.is_(True),
                        ConfiguracaoImposto.padrao.is_(True),
                    )
                    .first()
                )

                if config_imposto:
                    imposto_percentual = float(config_imposto.percentual)
                    imposto_valor = subtotal * (imposto_percentual / 100)
        except Exception as e:
            logger.error(f"❌ Erro ao buscar configuração fiscal: {e}")
            # Continuar sem impostos em caso de erro
            imposto_percentual = 0
            imposto_valor = 0

        # ===== 6. CALCULAR COMISSAO REAL DO VENDEDOR/PARCEIRO =====
        comissao_total = 0
        percentual_medio_comissao = 0

        if dados.vendedor_id and itens_para_comissao:
            try:
                from app.comissoes_service import (
                    buscar_configuracao_comissao,
                    calcular_comissao_item,
                )

                soma_brutos = sum(
                    Decimal(str(item.preco_venda)) * Decimal(str(item.quantidade))
                    for item, _, _ in itens_para_comissao
                )
                desconto_total = Decimal(str(dados.desconto or 0))
                soma_liquidos = Decimal("0")
                itens_normalizados = []

                for item, produto, custo_item in itens_para_comissao:
                    valor_bruto = Decimal(str(item.preco_venda)) * Decimal(
                        str(item.quantidade)
                    )
                    desconto_item = (
                        desconto_total * (valor_bruto / soma_brutos)
                        if soma_brutos > 0
                        else Decimal("0")
                    )
                    valor_liquido = valor_bruto - desconto_item
                    soma_liquidos += valor_liquido
                    itens_normalizados.append(
                        (
                            item,
                            produto,
                            Decimal(str(custo_item)),
                            valor_bruto,
                            valor_liquido,
                        )
                    )

                custos_rateados = {
                    "taxa_cartao_produtos": float(taxa_cartao_valor),
                    "impostos_produtos": float(imposto_valor),
                    "taxa_paga_entregador": 0,
                    "custo_operacional_entrega": 0,
                    "taxa_entrega_receita": float(dados.taxa_entrega or 0),
                    "percentual_impostos": float(imposto_percentual),
                }

                soma_percentuais = 0
                itens_com_config = 0

                for (
                    item,
                    produto,
                    custo_item,
                    valor_bruto,
                    valor_liquido,
                ) in itens_normalizados:
                    config = buscar_configuracao_comissao(
                        db,
                        dados.vendedor_id,
                        item.produto_id,
                        tenant_id=tenant_id,
                    )
                    if not config:
                        continue

                    proporcao_item = (
                        valor_liquido / soma_liquidos
                        if soma_liquidos > 0
                        else Decimal("0")
                    )
                    calculo = calcular_comissao_item(
                        config=config,
                        valor_bruto_item=valor_bruto,
                        valor_liquido_item=valor_liquido,
                        custo_unitario=custo_item,
                        quantidade=Decimal(str(item.quantidade)),
                        proporcao_item=proporcao_item,
                        custos_rateados=custos_rateados,
                        tem_entrega=bool(dados.taxa_entrega),
                    )

                    comissao_total += float(calculo["valor_comissao"])
                    soma_percentuais += float(calculo["percentual"])
                    itens_com_config += 1
                    detalhamento_comissoes.append(
                        DetalhamentoComissao(
                            produto=produto.nome,
                            percentual=float(calculo["percentual"]),
                            valor=float(calculo["valor_comissao"]),
                        )
                    )

                if itens_com_config:
                    percentual_medio_comissao = soma_percentuais / itens_com_config
            except Exception as e:
                logger.error(
                    f"Erro ao calcular comissao real na analise do PDV: {e}",
                    exc_info=True,
                )
                comissao_total = 0
                percentual_medio_comissao = 0
                detalhamento_comissoes = []

        # ===== 7. CALCULAR RESULTADO =====
        total_deducoes = (
            comissao_total + taxa_cartao_valor + imposto_valor + custos_total
        )
        lucro_liquido = subtotal - total_deducoes
        margem_liquida = (lucro_liquido / subtotal * 100) if subtotal > 0 else 0

        # Definir cor do indicador
        if margem_liquida >= 20:
            cor_indicador = "verde"
        elif margem_liquida >= 10:
            cor_indicador = "amarelo"
        else:
            cor_indicador = "vermelho"

        deducoes = {
            "comissao": {
                "valor": float(comissao_total),
                "percentual": float(round(percentual_medio_comissao, 2)),
                "tipo": "percentual",
            },
            "taxa_percentual": float(taxa_cartao_total),
            "taxa_fixa": float(taxa_fixa_total),
            "impostos": {
                "valor": float(imposto_valor),
                "percentual": float(imposto_percentual),
            },
            "custos": float(custos_total),
            "total_deducoes": float(total_deducoes),
        }

        resultado = {
            "lucro_liquido": float(lucro_liquido),
            "margem_liquida": float(round(margem_liquida, 2)),
            "cor_indicador": cor_indicador,
        }

        # ===== 7. GERAR ALERTAS =====
        alertas = []

        # Alerta de margem
        if margem_liquida < 10:
            alertas.append(
                AlertaAnalise(
                    tipo="error",
                    icone="⚠️",
                    mensagem="Margem baixa - evite mais descontos",
                )
            )
        elif margem_liquida >= 20:
            margem_disponivel = lucro_liquido * 0.3  # Pode usar até 30% da margem
            alertas.append(
                AlertaAnalise(
                    tipo="success",
                    icone="✅",
                    mensagem=f"Margem excelente - permite desconto de até R$ {margem_disponivel:.2f}",
                )
            )
        elif margem_liquida >= 15:
            alertas.append(
                AlertaAnalise(
                    tipo="info",
                    icone="✅",
                    mensagem="Margem boa - pode oferecer pequeno desconto adicional",
                )
            )
        else:
            alertas.append(
                AlertaAnalise(
                    tipo="warning",
                    icone="⚠️",
                    mensagem="Margem moderada - cuidado com descontos adicionais",
                )
            )

        # Alerta de taxa de cartão (verificar maior taxa)
        maior_taxa = max([t["taxa_percentual"] for t in detalhamento_taxas], default=0)
        if maior_taxa > 5:
            alertas.append(
                AlertaAnalise(
                    tipo="warning",
                    icone="⚠️",
                    mensagem=f"Taxa de cartão alta ({maior_taxa}%) - sugira à vista ou menos parcelas",
                )
            )

        # Alerta de custo
        percentual_custo = (
            (custos_total / total_produtos * 100) if total_produtos > 0 else 0
        )
        if percentual_custo > 70:
            alertas.append(
                AlertaAnalise(
                    tipo="warning",
                    icone="⚠️",
                    mensagem=f"Custo muito alto ({percentual_custo:.1f}% do total) - verifique margem antes de parcelar",
                )
            )
        elif percentual_custo > 60:
            alertas.append(
                AlertaAnalise(
                    tipo="info",
                    icone="💡",
                    mensagem=f"Custo dos produtos: {percentual_custo:.1f}% do total",
                )
            )

        # Alerta de desconto
        if dados.desconto > 0:
            percentual_desconto = (
                (dados.desconto / total_produtos * 100) if total_produtos > 0 else 0
            )
            if percentual_desconto > 15:
                alertas.append(
                    AlertaAnalise(
                        tipo="warning",
                        icone="⚠️",
                        mensagem=f"Desconto alto ({percentual_desconto:.1f}%) aplicado - margem reduzida",
                    )
                )

        # Se não houver alertas, adicionar mensagem positiva
        if not alertas:
            alertas.append(
                AlertaAnalise(
                    tipo="success", icone="✅", mensagem="Venda com margem saudável"
                )
            )

        # ===== 8. RETORNAR RESPOSTA =====
        return AnaliseVendaResponse(
            composicao=composicao,
            deducoes=deducoes,
            resultado=resultado,
            alertas=alertas,
            detalhamento_comissoes=detalhamento_comissoes,
            detalhamento_taxas=detalhamento_taxas,
        )

    except Exception as e:
        logger.error(f"❌ ERRO CRÍTICO em analisar_venda: {str(e)}", exc_info=True)

        # Retornar resposta com valores padrão para não quebrar o frontend
        total_produtos = (
            sum(item.preco_venda * item.quantidade for item in dados.items)
            if dados.items
            else 0
        )
        subtotal = total_produtos - dados.desconto - dados.taxa_entrega

        return AnaliseVendaResponse(
            composicao={
                "total_produtos": float(total_produtos),
                "desconto": float(dados.desconto),
                "taxa_entrega": float(dados.taxa_entrega),
                "subtotal": float(subtotal),
            },
            deducoes={
                "comissao": {"valor": 0.0, "percentual": 0.0, "tipo": "percentual"},
                "taxa_percentual": 0.0,
                "taxa_fixa": 0.0,
                "impostos": {"valor": 0.0, "percentual": 0.0},
                "custos": 0.0,
                "total_deducoes": 0.0,
            },
            resultado={
                "lucro_liquido": float(subtotal),
                "margem_liquida": 100.0,
                "cor_indicador": "verde",
            },
            alertas=[
                AlertaAnalise(
                    tipo="error",
                    icone="⚠️",
                    mensagem=f"Erro ao calcular análise: {str(e)}",
                )
            ],
            detalhamento_comissoes=[],
            detalhamento_taxas=[],
        )
