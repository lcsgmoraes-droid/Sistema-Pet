# -*- coding: utf-8 -*-
# ruff: noqa: F401
"""Operacoes auxiliares de pos-processamento de vendas."""

import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import String, func
from sqlalchemy.orm import Session

from app.services.venda_rentabilidade_snapshot_service import (
    get_or_build_venda_rentabilidade_snapshot,
)
from app.utils.timezone import now_brasilia

from app.vendas.dre_pos_processamento import gerar_dre_competencia_venda

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.vendas_models import Venda

# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================


def processar_comissoes_venda(
    venda_id: int,
    funcionario_id: Optional[int],
    valor_pago: Optional[float],
    user_id: int,
    db: Session,
) -> Dict[str, Any]:
    """
    Processa comissões de uma venda (operação pós-commit).

    Esta função é chamada APÓS o commit da venda principal,
    portanto erros aqui não abortam a venda.

    Args:
        venda_id: ID da venda
        funcionario_id: ID do funcionário (se houver)
        valor_pago: Valor pago (para parciais)
        user_id: ID do usuário
        db: Sessão do SQLAlchemy

    Returns:
        Dict com resultado do processamento
    """
    if not funcionario_id:
        return {"success": False, "message": "Venda sem funcionário vinculado"}

    try:
        from app.comissoes_service import gerar_comissoes_venda
        from decimal import Decimal

        valor_pago_decimal = Decimal(str(valor_pago)) if valor_pago else None

        resultado = gerar_comissoes_venda(
            venda_id=venda_id,
            funcionario_id=funcionario_id,
            valor_pago=valor_pago_decimal,
            db=db,
        )

        if resultado and resultado.get("success"):
            return {
                "success": True,
                "total_comissao": float(resultado.get("total_comissao", 0)),
                "duplicated": resultado.get("duplicated", False),
            }
        else:
            return {
                "success": False,
                "message": "Nenhuma comissão gerada (sem configuração)",
            }

    except Exception as e:
        logger.error(
            f"⚠️ Erro ao processar comissões (venda {venda_id}): {str(e)}", exc_info=True
        )
        return {"success": False, "error": str(e)}


def processar_lembretes_venda(
    venda_id: int,
    cliente_id: Optional[int],
    itens: List[Any],
    user_id: int,
    db: Session,
) -> Dict[str, Any]:
    """
    Processa lembretes/recorrências de uma venda (operação pós-commit).

    Esta função é chamada APÓS o commit da venda principal,
    portanto erros aqui não abortam a venda.

    Args:
        venda_id: ID da venda
        cliente_id: ID do cliente (se houver)
        itens: Lista de itens da venda
        user_id: ID do usuário
        db: Sessão do SQLAlchemy

    Returns:
        Dict com resultado do processamento
    """
    if not cliente_id:
        return {"success": False, "message": "Venda sem cliente vinculado"}

    try:
        from app.produtos_models import Produto
        from app.models import Pet

        lembretes_criados = []
        lembretes_atualizados = []

        for item in itens:
            if item.tipo == "produto" and item.produto_id and item.pet_id:
                produto = db.query(Produto).get(item.produto_id)
                pet = db.query(Pet).get(item.pet_id)

                if (
                    produto
                    and pet
                    and produto.tem_recorrencia
                    and produto.intervalo_dias
                ):
                    # Processar lembrete (lógica simplificada - detalhes na rota)
                    logger.info(
                        f"🔔 Processando lembrete: {produto.nome} para {pet.nome}"
                    )
                    lembretes_criados.append(produto.nome)

        return {
            "success": True,
            "lembretes_criados": len(lembretes_criados),
            "lembretes_atualizados": len(lembretes_atualizados),
        }

    except Exception as e:
        logger.error(
            f"⚠️ Erro ao processar lembretes (venda {venda_id}): {str(e)}", exc_info=True
        )
        return {"success": False, "error": str(e)}


def processar_contas_pagar_entrega(
    venda: "Venda", user_id: int, tenant_id: str, db: Session
) -> Dict[str, Any]:
    """
    Cria contas a pagar relacionadas à entrega (operação pós-commit).

    Cria 2 tipos de contas a pagar:
    1. Taxa do entregador (parte da taxa de entrega que vai para ele)
    2. Custo operacional (fixo ou controla_rh - KM rodado é criado ao fechar rota)

    Args:
        venda: Objeto Venda (já commitada)
        user_id: ID do usuário
        tenant_id: UUID do tenant
        db: Sessão do SQLAlchemy

    Returns:
        Dict com resultado:
        {
            'success': bool,
            'total_contas': int,
            'valor_total': float,
            'contas_criadas': List[int],
            'detalhes': List[str]
        }
    """
    from app.financeiro_models import ContaPagar
    from app.models import User
    from datetime import date, timedelta

    if not venda.tem_entrega or not venda.entregador_id:
        return {
            "success": True,
            "total_contas": 0,
            "valor_total": 0.0,
            "contas_criadas": [],
            "detalhes": ["Venda sem entrega ou sem entregador"],
        }

    contas_criadas_ids = []
    valor_total = Decimal("0")
    detalhes = []

    try:
        # Buscar entregador
        entregador = (
            db.query(User)
            .filter_by(id=venda.entregador_id, tenant_id=tenant_id)
            .first()
        )
        if not entregador:
            logger.warning(f"⚠️ Entregador ID {venda.entregador_id} não encontrado")
            return {
                "success": False,
                "message": f"Entregador ID {venda.entregador_id} não encontrado",
            }

        # Calcula a próxima segunda-feira de pagamento
        # Lógica: Vendas de domingo a sábado são pagas na segunda-feira seguinte
        # Ex: Venda em 08/02 (domingo) → Fecha 14/02 (sábado) → Paga 16/02 (segunda)
        data_venda = date.today()
        dia_semana = data_venda.weekday()  # 0=Segunda, 6=Domingo

        # Calcular dias até o próximo sábado (fim da semana)
        if dia_semana == 6:  # Domingo
            dias_ate_sabado = 6
        elif dia_semana == 5:  # Sábado
            dias_ate_sabado = 0
        else:  # Segunda a Sexta
            dias_ate_sabado = 5 - dia_semana

        proximo_sabado = data_venda + timedelta(days=dias_ate_sabado)
        data_vencimento = proximo_sabado + timedelta(
            days=2
        )  # Segunda-feira = sábado + 2

        # Mapear canal para nome legível (sem acentos para compatibilidade)
        CANAIS_NOMES = {
            "loja_fisica": "Loja Fisica",
            "mercado_livre": "Mercado Livre",
            "shopee": "Shopee",
            "amazon": "Amazon",
        }
        canal = venda.canal or "loja_fisica"
        canal_nome = CANAIS_NOMES.get(canal, "Loja Física")

        # 1️⃣ CONTA A PAGAR: Taxa do entregador (Comissão)
        if venda.valor_taxa_entregador and float(venda.valor_taxa_entregador) > 0:
            # Buscar subcategoria "Comissao Entregador - {Canal}" (sem acentos)
            from app.dre_plano_contas_models import DRESubcategoria

            subcategoria_comissao = (
                db.query(DRESubcategoria)
                .filter(
                    DRESubcategoria.tenant_id == tenant_id,
                    DRESubcategoria.nome == f"Comissao Entregador - {canal_nome}",
                )
                .first()
            )

            if not subcategoria_comissao:
                logger.warning(
                    f"❌ Subcategoria não encontrada: 'Comissão Entregador - {canal_nome}' (tenant: {tenant_id})"
                )
            else:
                logger.info(
                    f"✅ Subcategoria encontrada: ID {subcategoria_comissao.id}"
                )

            conta_taxa = ContaPagar(
                descricao=f"Taxa de entrega - {entregador.nome} - Venda {venda.numero_venda}",
                fornecedor_id=venda.entregador_id,
                valor_original=venda.valor_taxa_entregador,
                valor_final=venda.valor_taxa_entregador,
                data_emissao=date.today(),
                data_vencimento=data_vencimento,
                status="pendente",
                user_id=user_id,
                tenant_id=tenant_id,
                canal=canal,
                dre_subcategoria_id=subcategoria_comissao.id
                if subcategoria_comissao
                else None,
                observacoes=f"Taxa de entrega ref. venda {venda.numero_venda} - {venda.percentual_taxa_entregador}% da taxa de R$ {venda.taxa_entrega} - Acerto semanal (segunda-feira {data_vencimento.strftime('%d/%m/%Y')})",
            )
            db.add(conta_taxa)
            db.flush()
            contas_criadas_ids.append(conta_taxa.id)
            valor_total += venda.valor_taxa_entregador
            detalhes.append(f"Taxa entregador: R$ {venda.valor_taxa_entregador:.2f}")
            logger.info(
                f"✅ Conta a pagar criada: Taxa entregador R$ {venda.valor_taxa_entregador:.2f}"
            )

        # 2️⃣ CONTA A PAGAR: Custo operacional (apenas fixo ou controla_rh)
        if entregador.custo_operacional_tipo in ["fixo", "controla_rh"]:
            if (
                entregador.custo_operacional_valor
                and float(entregador.custo_operacional_valor) > 0
            ):
                tipo_descricao = (
                    "Custo fixo"
                    if entregador.custo_operacional_tipo == "fixo"
                    else "Controla RH"
                )

                observacoes = f"Custo operacional ({entregador.custo_operacional_tipo}) ref. venda {venda.numero_venda} - Acerto semanal (segunda-feira {data_vencimento.strftime('%d/%m/%Y')})"
                if (
                    entregador.custo_operacional_tipo == "controla_rh"
                    and entregador.custo_operacional_controla_rh_id
                ):
                    observacoes += f" - ID Controla RH: {entregador.custo_operacional_controla_rh_id}"

                # Buscar subcategoria "Frete Operacional - {Canal}"
                from app.dre_plano_contas_models import DRESubcategoria

                subcategoria_frete_op = (
                    db.query(DRESubcategoria)
                    .filter(
                        DRESubcategoria.tenant_id == tenant_id,
                        DRESubcategoria.nome == f"Frete Operacional - {canal_nome}",
                    )
                    .first()
                )

                if not subcategoria_frete_op:
                    logger.warning(
                        f"❌ Subcategoria não encontrada: 'Frete Operacional - {canal_nome}' (tenant: {tenant_id})"
                    )
                else:
                    logger.info(
                        f"✅ Subcategoria encontrada: ID {subcategoria_frete_op.id}"
                    )

                conta_custo = ContaPagar(
                    descricao=f"{tipo_descricao} entrega - {entregador.nome} - Venda {venda.numero_venda}",
                    fornecedor_id=venda.entregador_id,
                    valor_original=entregador.custo_operacional_valor,
                    valor_final=entregador.custo_operacional_valor,
                    data_emissao=date.today(),
                    data_vencimento=data_vencimento,
                    status="pendente",
                    user_id=user_id,
                    tenant_id=tenant_id,
                    canal=canal,
                    dre_subcategoria_id=subcategoria_frete_op.id
                    if subcategoria_frete_op
                    else None,
                    observacoes=observacoes,
                )

                db.add(conta_custo)
                db.flush()
                contas_criadas_ids.append(conta_custo.id)
                valor_total += entregador.custo_operacional_valor
                detalhes.append(
                    f"{tipo_descricao}: R$ {entregador.custo_operacional_valor:.2f}"
                )
                logger.info(
                    f"✅ Conta a pagar criada: {tipo_descricao} R$ {entregador.custo_operacional_valor:.2f}"
                )

        # Nota: KM rodado será criado ao fechar a rota, não aqui
        if entregador.custo_operacional_tipo == "km_rodado":
            detalhes.append(
                f"Custo por KM (R$ {entregador.custo_operacional_valor:.2f}/km) - será criado ao fechar rota"
            )

        return {
            "success": True,
            "total_contas": len(contas_criadas_ids),
            "valor_total": float(valor_total),
            "contas_criadas": contas_criadas_ids,
            "detalhes": detalhes,
        }

    except Exception as e:
        logger.error(
            f"❌ Erro ao criar contas a pagar de entrega (venda {venda.id}): {str(e)}",
            exc_info=True,
        )
        return {"success": False, "error": str(e)}


def processar_contas_pagar_taxas(
    venda: "Venda", pagamentos: List[Any], user_id: int, tenant_id: str, db: Session
) -> Dict[str, Any]:
    """
    Cria contas a pagar para taxas de pagamento (operação pós-commit).

    Para cada pagamento da venda:
    1. Busca a forma de pagamento e suas taxas (taxa_percentual, taxa_fixa, taxas_por_parcela)
    2. Calcula o valor da taxa
    3. Identifica a subcategoria DRE apropriada (baseado no tipo e canal)
    4. Cria conta a pagar na DRE

    Tipos de taxa suportados:
    - Cartão de crédito (com ou sem parcelamento)
    - Cartão de débito
    - PIX
    - Transferência
    - Boleto

    Args:
        venda: Objeto Venda (já commitada)
        pagamentos: Lista de objetos de pagamento (VendaPagamento)
        user_id: ID do usuário
        tenant_id: UUID do tenant
        db: Sessão do SQLAlchemy

    Returns:
        Dict com resultado:
        {
            'success': bool,
            'total_contas': int,
            'valor_total': float,
            'contas_criadas': List[int],
            'detalhes': List[str]
        }
    """
    from app.financeiro_models import ContaPagar, FormaPagamento
    from app.financeiro.contas_pagar_classificacao import (
        aplicar_classificacao_aprendida_conta_pagar,
    )
    from app.dre_plano_contas_models import DRESubcategoria
    from datetime import date

    if not pagamentos:
        return {
            "success": True,
            "total_contas": 0,
            "valor_total": 0.0,
            "contas_criadas": [],
            "detalhes": ["Nenhum pagamento para processar"],
        }

    contas_criadas_ids = []
    valor_total = Decimal("0")
    detalhes = []

    try:
        # Mapear canal para determinar subcategoria DRE apropriada
        canal = venda.canal or "loja_fisica"

        # Mapear tipo de pagamento para nome da subcategoria DRE
        MAPA_SUBCATEGORIAS = {
            "cartao_credito": "Taxas de Cartao de Credito",
            "credito": "Taxas de Cartao de Credito",
            "Cartão Crédito": "Taxas de Cartao de Credito",
            "cartao_debito": "Taxas de Cartao de Debito",
            "debito": "Taxas de Cartao de Debito",
            "Cartão Débito": "Taxas de Cartao de Debito",
            "pix": "Taxa de PIX",
            "PIX": "Taxa de PIX",
            "Pix": "Taxa de PIX",
            "boleto": "Taxas de Boleto",
        }

        # Mapear canal para sufixo da subcategoria
        MAPA_CANAIS = {
            "loja_fisica": "Loja Fisica",
            "pdv": "Loja Fisica",  # PDV = Loja Fisica
            "ecommerce": "E-commerce",
            "mercado_livre": "Mercado Livre",
            "shopee": "Shopee",
            "amazon": "Amazon",
        }

        canal_sufixo = MAPA_CANAIS.get(canal, "Loja Fisica")  # Default: Loja Fisica

        # Processar cada pagamento
        for pagamento in pagamentos:
            # Pular formas de pagamento sem taxa (dinheiro, crédito cliente)
            forma_pag_nome = pagamento.forma_pagamento.lower()
            if "dinheiro" in forma_pag_nome or "credito_cliente" in forma_pag_nome:
                continue

            # Buscar configuração da forma de pagamento
            forma_pag = (
                db.query(FormaPagamento)
                .filter(
                    FormaPagamento.tenant_id == tenant_id,
                    FormaPagamento.ativo.is_(True),
                )
                .filter(
                    (FormaPagamento.nome == pagamento.forma_pagamento)
                    | (FormaPagamento.tipo == pagamento.forma_pagamento)
                    | (func.lower(FormaPagamento.nome).like(f"%{forma_pag_nome}%"))
                )
                .first()
            )

            if not forma_pag:
                logger.warning(
                    f"⚠️ Forma de pagamento não encontrada: {pagamento.forma_pagamento}"
                )
                continue

            # Verificar se tem taxa configurada
            taxa_percentual = Decimal(str(forma_pag.taxa_percentual or 0))
            taxa_fixa = Decimal(str(forma_pag.taxa_fixa or 0))

            if taxa_percentual == 0 and taxa_fixa == 0:
                logger.debug(f"✓ Forma de pagamento sem taxa: {forma_pag.nome}")
                continue

            # Verificar se tem taxa específica para número de parcelas
            num_parcelas = getattr(pagamento, "numero_parcelas", 1) or 1

            if num_parcelas > 1 and forma_pag.taxas_por_parcela:
                try:
                    taxas_por_parcela_dict = json.loads(forma_pag.taxas_por_parcela)
                    if str(num_parcelas) in taxas_por_parcela_dict:
                        taxa_parcela_config = taxas_por_parcela_dict[str(num_parcelas)]
                        taxa_percentual = Decimal(
                            str(
                                taxa_parcela_config.get(
                                    "taxa_percentual", taxa_percentual
                                )
                            )
                        )
                        taxa_fixa = Decimal(
                            str(taxa_parcela_config.get("taxa_fixa", taxa_fixa))
                        )
                        logger.info(
                            f"💳 Taxa específica para {num_parcelas}x: {taxa_percentual}% + R$ {taxa_fixa}"
                        )
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    logger.warning(f"⚠️ Erro ao processar taxas_por_parcela: {str(e)}")

            # Calcular valor da taxa
            valor_pagamento = Decimal(str(pagamento.valor))
            valor_taxa = (
                valor_pagamento * taxa_percentual / Decimal("100")
            ) + taxa_fixa

            if valor_taxa <= 0:
                continue

            # Determinar nome da subcategoria DRE
            tipo_pagamento_base = forma_pag.tipo or pagamento.forma_pagamento
            nome_subcategoria_base = MAPA_SUBCATEGORIAS.get(
                tipo_pagamento_base,
                MAPA_SUBCATEGORIAS.get(pagamento.forma_pagamento, None),
            )

            if not nome_subcategoria_base:
                logger.warning(
                    f"⚠️ Tipo de pagamento não mapeado: {tipo_pagamento_base}"
                )
                continue

            # Montar nome completo da subcategoria (com canal)
            nome_subcategoria = f"{nome_subcategoria_base} - {canal_sufixo}"

            # Buscar subcategoria DRE
            subcategoria_taxa = (
                db.query(DRESubcategoria)
                .filter(
                    DRESubcategoria.tenant_id == tenant_id,
                    DRESubcategoria.nome == nome_subcategoria,
                    DRESubcategoria.ativo.is_(True),
                )
                .first()
            )

            # Se não encontrar com canal, tentar genérico
            if not subcategoria_taxa:
                subcategoria_taxa = (
                    db.query(DRESubcategoria)
                    .filter(
                        DRESubcategoria.tenant_id == tenant_id,
                        DRESubcategoria.nome == nome_subcategoria_base,
                        DRESubcategoria.ativo.is_(True),
                    )
                    .first()
                )

            if not subcategoria_taxa:
                logger.warning(
                    f"❌ Subcategoria DRE não encontrada: {nome_subcategoria} (tentou também {nome_subcategoria_base})"
                )
                continue

            logger.info(
                f"✅ Subcategoria DRE encontrada: {subcategoria_taxa.nome} (ID: {subcategoria_taxa.id})"
            )

            # Criar conta a pagar
            descricao = f"Taxa {forma_pag.nome}"
            if num_parcelas > 1:
                descricao += f" {num_parcelas}x"
            descricao += f" - Venda {venda.numero_venda}"

            observacoes = f"Taxa de pagamento ref. venda {venda.numero_venda}"
            if taxa_percentual > 0 and taxa_fixa > 0:
                observacoes += (
                    f" - {taxa_percentual}% + R$ {taxa_fixa} sobre R$ {valor_pagamento}"
                )
            elif taxa_percentual > 0:
                observacoes += f" - {taxa_percentual}% sobre R$ {valor_pagamento}"
            else:
                observacoes += f" - Taxa fixa de R$ {taxa_fixa}"

            # Data de vencimento: assumindo 30 dias (pode ser ajustado pelo campo prazo_dias)
            prazo_dias = forma_pag.prazo_dias or forma_pag.prazo_recebimento or 30
            data_vencimento = date.today() + timedelta(days=prazo_dias)

            conta_taxa = ContaPagar(
                descricao=descricao,
                fornecedor_id=None,  # Taxa não tem fornecedor específico
                valor_original=valor_taxa,
                valor_final=valor_taxa,
                data_emissao=date.today(),
                data_vencimento=data_vencimento,
                status="pendente",
                user_id=user_id,
                tenant_id=tenant_id,
                canal=canal,
                dre_subcategoria_id=subcategoria_taxa.id,
                observacoes=observacoes,
            )
            aplicar_classificacao_aprendida_conta_pagar(db, tenant_id, conta_taxa)

            db.add(conta_taxa)
            db.flush()

            contas_criadas_ids.append(conta_taxa.id)
            valor_total += valor_taxa
            detalhes.append(f"{forma_pag.nome}: R$ {valor_taxa:.2f}")

            logger.info(
                f"✅ Conta a pagar criada: Taxa {forma_pag.nome} R$ {valor_taxa:.2f}"
            )

        return {
            "success": True,
            "total_contas": len(contas_criadas_ids),
            "valor_total": float(valor_total),
            "contas_criadas": contas_criadas_ids,
            "detalhes": detalhes,
        }

    except Exception as e:
        logger.error(
            f"❌ Erro ao criar contas a pagar de taxas (venda {venda.id}): {str(e)}",
            exc_info=True,
        )
        return {"success": False, "error": str(e)}
