# -*- coding: utf-8 -*-
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
    from decimal import Decimal
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
    from decimal import Decimal
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
