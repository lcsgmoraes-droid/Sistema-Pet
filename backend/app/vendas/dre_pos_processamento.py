# -*- coding: utf-8 -*-
"""Operacoes auxiliares de pos-processamento de vendas."""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import String, func
from sqlalchemy.orm import Session

from app.services.venda_rentabilidade_snapshot_service import (
    get_or_build_venda_rentabilidade_snapshot,
)
from app.utils.timezone import now_brasilia

logger = logging.getLogger(__name__)


def gerar_dre_competencia_venda(
    venda_id: int, user_id: int, tenant_id: str, db: Session
) -> Dict[str, Any]:
    """
    Gera lançamentos de DRE por competência para uma venda (PASSO 1 - Sprint 5).

    Esta função é chamada no PRIMEIRO MOMENTO em que a venda se torna EFETIVADA
    (ou seja, quando passa a ter qualquer valor recebido, parcial ou total).

    Operações executadas:
    1. Lançar RECEITA (100% do valor bruto) na DRE
    2. Lançar CMV (custo total dos produtos) na DRE
    3. Lançar DESCONTO (se houver) na DRE

    GARANTIAS:
    - ✅ Idempotente: verifica se DRE já foi gerada (campo venda.dre_gerada)
    - ✅ Multi-tenant: todos os lançamentos isolados por tenant_id
    - ✅ Regime de competência: gera no momento da efetivação, não no pagamento
    - ✅ Atomicidade: chamada dentro da transação principal

    Args:
        venda_id: ID da venda
        user_id: ID do usuário (para auditoria)
        tenant_id: UUID do tenant (isolamento multi-tenant)
        db: Sessão do SQLAlchemy (NÃO faz commit, apenas flush)

    Returns:
        Dict com resultado:
        {
            'success': bool,
            'lancamentos_criados': int,
            'receita_gerada': float,
            'cmv_gerado': float,
            'desconto_gerado': float,
            'message': str
        }

    Raises:
        HTTPException: Se venda não encontrada ou subcategorias DRE inválidas

    Exemplo:
        >>> resultado = gerar_dre_competencia_venda(
        ...     venda_id=120,
        ...     user_id=1,
        ...     tenant_id="uuid-tenant",
        ...     db=db
        ... )
        >>> logger.info(f"DRE gerada: {resultado['lancamentos_criados']} lançamentos")
    """
    from app.vendas_models import Venda
    from app.domain.dre.lancamento_dre_sync import atualizar_dre_por_lancamento
    from app.dre_plano_contas_models import DRESubcategoria, NaturezaDRE

    logger.info(f"📊 Iniciando geração de DRE por competência - Venda #{venda_id}")

    try:
        # ============================================================
        # ETAPA 0: GARANTIR TENANT_ID COMO UUID
        # ============================================================

        # Converter tenant_id para UUID se necessário (fix PostgreSQL cast error)
        if tenant_id and not isinstance(tenant_id, UUID):
            try:
                tenant_uuid = UUID(str(tenant_id))
            except (ValueError, AttributeError):
                tenant_uuid = tenant_id
        else:
            tenant_uuid = tenant_id

        # ============================================================
        # ETAPA 1: BUSCAR VENDA E VALIDAR
        # ============================================================

        venda = db.query(Venda).filter_by(id=venda_id, tenant_id=tenant_uuid).first()

        if not venda:
            raise HTTPException(status_code=404, detail="Venda não encontrada")

        # ✅ IDEMPOTÊNCIA: Verificar se DRE já foi gerada
        if venda.dre_gerada:
            logger.info(
                f"⚠️  DRE já foi gerada anteriormente para venda #{venda.numero_venda} "
                f"em {venda.data_geracao_dre}"
            )
            return {
                "success": False,
                "lancamentos_criados": 0,
                "receita_gerada": 0,
                "cmv_gerado": 0,
                "desconto_gerado": 0,
                "message": "DRE já foi gerada anteriormente (idempotência)",
            }

        canal = venda.canal or "loja_fisica"
        canal_labels = {
            "loja_fisica": "Loja Fisica",
            "pdv": "Loja Fisica",
            "mercado_livre": "Mercado Livre",
            "shopee": "Shopee",
            "amazon": "Amazon",
            "ecommerce": "E-commerce",
            "app": "App",
        }
        canal_label = canal_labels.get(canal, "Loja Fisica")

        # ============================================================
        # ETAPA 2: BUSCAR SUBCATEGORIAS DRE
        # ============================================================

        # Buscar subcategoria de RECEITA
        subcat_receita = (
            db.query(DRESubcategoria)
            .filter(
                DRESubcategoria.tenant_id == tenant_uuid,
                DRESubcategoria.nome.ilike("%receita%venda%"),
                DRESubcategoria.ativo.is_(True),
            )
            .first()
        )

        if not subcat_receita:
            # Tentar buscar qualquer receita
            subcat_receita = (
                db.query(DRESubcategoria)
                .filter(
                    DRESubcategoria.tenant_id == tenant_uuid,
                    DRESubcategoria.ativo.is_(True),
                )
                .join(DRESubcategoria.categoria)
                .filter(
                    func.lower(
                        func.cast(
                            DRESubcategoria.categoria.property.mapper.class_.natureza,
                            String,
                        )
                    ).like("%receita%")
                )
                .first()
            )

        if not subcat_receita:
            raise HTTPException(
                status_code=500,
                detail="Subcategoria DRE de Receita não encontrada. Configure o plano de contas DRE.",
            )

        # Buscar subcategoria de CMV
        subcat_cmv = (
            db.query(DRESubcategoria)
            .filter(
                DRESubcategoria.tenant_id == tenant_uuid,
                DRESubcategoria.nome.ilike("%cmv%"),
                DRESubcategoria.ativo.is_(True),
            )
            .first()
        )

        if not subcat_cmv:
            # Tentar buscar "Custo dos Produtos Vendidos"
            subcat_cmv = (
                db.query(DRESubcategoria)
                .filter(
                    DRESubcategoria.tenant_id == tenant_uuid,
                    DRESubcategoria.nome.ilike("%custo%produto%"),
                    DRESubcategoria.ativo.is_(True),
                )
                .first()
            )

        if not subcat_cmv:
            raise HTTPException(
                status_code=500,
                detail="Subcategoria DRE de CMV não encontrada. Configure o plano de contas DRE.",
            )

        # Buscar subcategoria de DESCONTO (opcional)
        subcat_desconto = (
            db.query(DRESubcategoria)
            .filter(
                DRESubcategoria.tenant_id == tenant_uuid,
                DRESubcategoria.nome.ilike("%desconto%"),
                DRESubcategoria.ativo.is_(True),
            )
            .first()
        )

        if not subcat_desconto:
            # Tentar buscar "Deduções de Receita"
            subcat_desconto = (
                db.query(DRESubcategoria)
                .filter(
                    DRESubcategoria.tenant_id == tenant_uuid,
                    DRESubcategoria.nome.ilike("%dedu%"),
                    DRESubcategoria.ativo.is_(True),
                )
                .first()
            )

        logger.info(
            f"✅ Subcategorias DRE localizadas: "
            f"Receita (ID={subcat_receita.id}), "
            f"CMV (ID={subcat_cmv.id}), "
            f"Desconto (ID={subcat_desconto.id if subcat_desconto else 'N/A'})"
        )

        def buscar_subcategoria(padroes, natureza=None):
            for padrao in padroes:
                query = db.query(DRESubcategoria).filter(
                    DRESubcategoria.tenant_id == tenant_uuid,
                    DRESubcategoria.nome.ilike(padrao),
                    DRESubcategoria.ativo.is_(True),
                )
                if natureza is not None:
                    query = query.filter(
                        DRESubcategoria.categoria.has(natureza=natureza)
                    )
                subcategoria = query.first()
                if subcategoria:
                    return subcategoria
            return None

        subcat_receita_frete = buscar_subcategoria(
            [f"%Taxa de Frete%{canal_label}%", "%Taxa de Frete%", "%Receita%Frete%"],
            NaturezaDRE.RECEITA,
        )
        subcat_imposto = buscar_subcategoria(
            [
                "%Simples Nacional%",
                "%ICMS%",
                "%PIS%",
                "%COFINS%",
                "%ISS%",
                "%impost%",
                "%tribut%",
            ],
            NaturezaDRE.DESPESA,
        )
        subcat_taxa_cartao = buscar_subcategoria(
            [f"%Cart%{canal_label}%", "%Cart%", "%PIX%", "%Boleto%"],
            None,
        )
        subcat_entrega = buscar_subcategoria(
            [
                f"%Frete Operacional%{canal_label}%",
                "%Frete Operacional%",
                "%Fretes sobre Vendas%",
            ],
            None,
        )
        subcat_comissao = buscar_subcategoria(
            ["%Comiss%Vendas%", "%Comiss%Entregador%", "%Comiss%"],
            None,
        )
        subcat_campanha = buscar_subcategoria(
            ["%Programas de Fidelidade%", "%Campanha%", "%Marketing%", "%Brinde%"],
            None,
        )

        # ============================================================
        # ETAPA 3: CALCULAR VALORES
        # ============================================================

        snapshot = get_or_build_venda_rentabilidade_snapshot(
            venda,
            db,
            tenant_uuid,
            persist_if_missing=True,
            force_refresh=True,
        )

        # Receita, CMV e desconto passam a seguir a fotografia financeira da venda.
        receita_bruta = Decimal(str(snapshot.get("venda_bruta", 0) or 0))
        receita_frete = Decimal(str(snapshot.get("taxa_loja", 0) or 0))
        cmv_total = Decimal(str(snapshot.get("custo_produtos", 0) or 0))
        desconto_total = Decimal(str(snapshot.get("desconto", 0) or 0))
        imposto_total = Decimal(str(snapshot.get("imposto", 0) or 0))
        taxa_cartao_total = Decimal(str(snapshot.get("taxa_cartao", 0) or 0))
        repasse_entrega_total = Decimal(str(snapshot.get("taxa_entrega", 0) or 0))
        taxa_operacional_total = Decimal(str(snapshot.get("taxa_operacional", 0) or 0))
        comissao_total = Decimal(str(snapshot.get("comissao", 0) or 0))
        campanha_total = Decimal(str(snapshot.get("custo_campanha", 0) or 0))

        # Canal da venda (para DRE por canal)
        canal = venda.canal or "loja_fisica"

        # Data da venda (para identificar período DRE)
        data_venda = (
            venda.data_venda.date()
            if isinstance(venda.data_venda, datetime)
            else venda.data_venda
        )

        logger.info(
            f"💰 Valores calculados: "
            f"Receita=R$ {float(receita_bruta):.2f}, "
            f"CMV=R$ {float(cmv_total):.2f}, "
            f"Desconto=R$ {float(desconto_total):.2f}"
        )

        # ============================================================
        # ETAPA 4: GERAR LANÇAMENTOS NA DRE
        # ============================================================

        lancamentos_criados = 0
        receita_bruta_retorno = receita_bruta
        cmv_total_retorno = cmv_total
        desconto_total_retorno = desconto_total

        componentes_dre = [
            ("Receita de produtos/servicos", subcat_receita, receita_bruta, "RECEITA"),
            ("Receita de frete", subcat_receita_frete, receita_frete, "RECEITA"),
            ("Descontos concedidos", subcat_desconto, desconto_total, "DESPESA"),
            ("Impostos sobre vendas", subcat_imposto, imposto_total, "DESPESA"),
            ("CMV", subcat_cmv, cmv_total, "DESPESA"),
            (
                "Taxas de cartao/meios de pagamento",
                subcat_taxa_cartao,
                taxa_cartao_total,
                "DESPESA",
            ),
            (
                "Repasse/custo de entrega",
                subcat_entrega,
                repasse_entrega_total,
                "DESPESA",
            ),
            (
                "Custo operacional de entrega",
                subcat_entrega,
                taxa_operacional_total,
                "DESPESA",
            ),
            ("Comissoes de venda", subcat_comissao, comissao_total, "DESPESA"),
            (
                "Campanhas, cupons e cashback",
                subcat_campanha,
                campanha_total,
                "DESPESA",
            ),
        ]

        for (
            descricao_componente,
            subcategoria_dre,
            valor_componente,
            tipo_movimentacao,
        ) in componentes_dre:
            if valor_componente <= 0:
                continue
            if not subcategoria_dre:
                logger.warning(
                    "  DRE: %s de R$ %.2f nao lancado (subcategoria nao encontrada)",
                    descricao_componente,
                    float(valor_componente),
                )
                continue

            try:
                atualizar_dre_por_lancamento(
                    db=db,
                    tenant_id=tenant_uuid,
                    dre_subcategoria_id=subcategoria_dre.id,
                    canal=canal,
                    valor=valor_componente,
                    data_lancamento=data_venda,
                    tipo_movimentacao=tipo_movimentacao,
                )
                lancamentos_criados += 1
                logger.info(
                    "  DRE: %s lancado: R$ %.2f",
                    descricao_componente,
                    float(valor_componente),
                )
            except Exception as e:
                logger.error(
                    "  Erro ao lancar %s na DRE: %s",
                    descricao_componente,
                    str(e),
                    exc_info=True,
                )
                raise

        # Os blocos legados abaixo ficam desativados para evitar duplicidade.
        receita_bruta = Decimal("0")
        cmv_total = Decimal("0")
        desconto_total = Decimal("0")

        # 4.1 - Lançamento de RECEITA (100%)
        if receita_bruta > 0:
            try:
                atualizar_dre_por_lancamento(
                    db=db,
                    tenant_id=tenant_uuid,
                    dre_subcategoria_id=subcat_receita.id,
                    canal=canal,
                    valor=receita_bruta,
                    data_lancamento=data_venda,
                    tipo_movimentacao="RECEITA",
                )
                lancamentos_criados += 1
                logger.info(f"  ✅ Receita lançada: R$ {float(receita_bruta):.2f}")
            except Exception as e:
                logger.error(f"  ❌ Erro ao lançar receita: {str(e)}", exc_info=True)
                raise

        # 4.2 - Lançamento de CMV
        if cmv_total > 0:
            try:
                atualizar_dre_por_lancamento(
                    db=db,
                    tenant_id=tenant_uuid,
                    dre_subcategoria_id=subcat_cmv.id,
                    canal=canal,
                    valor=cmv_total,
                    data_lancamento=data_venda,
                    tipo_movimentacao="DESPESA",  # CMV é um custo
                )
                lancamentos_criados += 1
                logger.info(f"  ✅ CMV lançado: R$ {float(cmv_total):.2f}")
            except Exception as e:
                logger.error(f"  ❌ Erro ao lançar CMV: {str(e)}", exc_info=True)
                raise

        # 4.3 - Lançamento de DESCONTO (se houver e se tiver subcategoria)
        if desconto_total > 0 and subcat_desconto:
            try:
                atualizar_dre_por_lancamento(
                    db=db,
                    tenant_id=tenant_uuid,
                    dre_subcategoria_id=subcat_desconto.id,
                    canal=canal,
                    valor=desconto_total,
                    data_lancamento=data_venda,
                    tipo_movimentacao="DESPESA",  # Desconto reduz receita
                )
                lancamentos_criados += 1
                logger.info(f"  ✅ Desconto lançado: R$ {float(desconto_total):.2f}")
            except Exception as e:
                logger.error(f"  ❌ Erro ao lançar desconto: {str(e)}", exc_info=True)
                raise
        elif desconto_total > 0:
            logger.warning(
                f"  ⚠️  Desconto de R$ {float(desconto_total):.2f} não lançado (subcategoria não encontrada)"
            )

        receita_bruta = receita_bruta_retorno
        cmv_total = cmv_total_retorno
        desconto_total = desconto_total_retorno

        # ============================================================
        # ETAPA 5: MARCAR VENDA COMO DRE GERADA
        # ============================================================

        venda.dre_gerada = True
        venda.data_geracao_dre = now_brasilia()
        db.flush()

        logger.info(
            f"✅ ✅ ✅ DRE POR COMPETÊNCIA GERADA: Venda #{venda.numero_venda} ✅ ✅ ✅\n"
            f"   📊 Lançamentos criados: {lancamentos_criados}\n"
            f"   💰 Receita: R$ {float(receita_bruta):.2f}\n"
            f"   📦 CMV: R$ {float(cmv_total):.2f}\n"
            f"   🎁 Desconto: R$ {float(desconto_total):.2f}\n"
            f"   🏪 Canal: {canal}"
        )

        return {
            "success": True,
            "lancamentos_criados": lancamentos_criados,
            "receita_gerada": float(receita_bruta),
            "cmv_gerado": float(cmv_total),
            "desconto_gerado": float(desconto_total),
            "message": f"{lancamentos_criados} lançamentos criados na DRE",
        }

    except HTTPException:
        # Re-lançar HTTPException
        raise

    except Exception as e:
        logger.error(
            f"❌ ERRO CRÍTICO ao gerar DRE por competência: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Erro ao gerar DRE: {str(e)}")
