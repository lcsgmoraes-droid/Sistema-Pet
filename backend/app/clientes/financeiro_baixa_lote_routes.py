"""Rotas de baixa financeira em lote de clientes."""

import logging
from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.auth.dependencies import get_current_user_and_tenant
from app.clientes.common import _validar_tenant_e_obter_usuario
from app.clientes.baixa_lote_pagamento import registrar_pagamento_lote
from app.clientes.baixa_lote_comissoes import completar_comissoes_lote
from app.db import get_session
from app.financeiro_models import ContaReceber
from app.utils.timezone import now_brasilia
from app.services.venda_rentabilidade_snapshot_service import (
    get_or_build_venda_rentabilidade_snapshot,
)
from app.clientes.baixas_lote_service import (
    atualizar_previsao,
    auditar_lote,
    buscar_repeticao,
    normalizar_requisicao,
    preparar_lote,
    registrar_item,
)
from app.clientes.financeiro_baixa_lote_historico_routes import (
    router as historico_router,
)


logger = logging.getLogger(__name__)
router = APIRouter()
router.include_router(historico_router)

__all__ = ["baixar_vendas_lote", "router"]

CENT = Decimal("0.01")


def _money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(CENT, rounding=ROUND_HALF_UP)


def _saldo_venda(venda) -> tuple[Decimal, Decimal]:
    valor_pago = sum((_money(p.valor) for p in venda.pagamentos or []), Decimal("0.00"))
    return valor_pago, _money(venda.total) - valor_pago


def _validar_valor_baixa(valor_total: Decimal, saldo_total: Decimal) -> None:
    if valor_total <= 0:
        raise HTTPException(status_code=400, detail="Informe um valor maior que zero")
    if valor_total > saldo_total:
        raise HTTPException(
            status_code=400,
            detail=f"Valor do pagamento (R$ {valor_total:.2f}) excede o saldo devedor total (R$ {saldo_total:.2f})",
        )


def _date_only(value):
    if hasattr(value, "date"):
        return value.date()
    return value


def _status_conta_receber(valor_total: Decimal, valor_recebido: Decimal) -> str:
    if valor_recebido <= Decimal("0.00"):
        return "pendente"
    if abs(valor_total - valor_recebido) < CENT:
        return "recebido"
    return "parcial"


def _criar_conta_receber_faltante_baixa_lote(
    *,
    db: Session,
    venda,
    current_user,
    tenant_id,
    valor_ja_recebido,
    data_referencia,
):
    valor_total = _money(venda.total)
    valor_recebido = _money(valor_ja_recebido)
    data_ref = _date_only(data_referencia)
    data_emissao = _date_only(venda.data_venda) or data_ref

    conta = ContaReceber(
        descricao=f"Venda {venda.numero_venda} - baixa em lote",
        cliente_id=venda.cliente_id,
        forma_pagamento_id=None,
        dre_subcategoria_id=1,
        canal=venda.canal or "loja_fisica",
        valor_original=valor_total,
        valor_recebido=valor_recebido,
        valor_desconto=Decimal("0.00"),
        valor_juros=Decimal("0.00"),
        valor_multa=Decimal("0.00"),
        valor_final=valor_total,
        data_emissao=data_emissao,
        data_vencimento=data_ref,
        data_recebimento=data_ref if valor_recebido > Decimal("0.00") else None,
        status=_status_conta_receber(valor_total, valor_recebido),
        eh_parcelado=False,
        venda_id=venda.id,
        documento=f"VENDA-{venda.id}",
        observacoes=(
            "Criada automaticamente pela baixa em lote para manter "
            "venda, recebimento e financeiro conciliados."
        ),
        user_id=current_user.id,
        tenant_id=tenant_id,
    )
    db.add(conta)
    db.flush()
    return conta


@router.post(
    "/{cliente_id}/baixar-vendas-lote",
    responses={
        400: {
            "description": (
                "Recebimento inválido: valor fora do saldo disponível, vendas "
                "que não estão em aberto, ausência ou falta de seleção do caixa, "
                "banco ou forma de pagamento inválidos, ou dados de cartão "
                "inconsistentes."
            )
        }
    },
)
async def baixar_vendas_lote(
    cliente_id: int,
    dados: dict,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Dá baixa em múltiplas vendas de uma vez, gerando movimentações no caixa e contas a receber"""
    try:
        current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

        logger.info("\n=== BAIXAR VENDAS LOTE ===")
        logger.info(f"Cliente ID: {cliente_id}")
        logger.info(f"Dados recebidos: {dados}")

        from app.vendas_models import Venda
        from app.caixa_models import MovimentacaoCaixa
        from app.caixa.escopo import buscar_caixa_para_recebimento
        from app.financeiro_models import Recebimento
        from app.ia.aba5_models import FluxoCaixa

        # Extrair dados do body
        request_id, requisicao = normalizar_requisicao(dados)
        vendas_ids = requisicao["vendas_ids"]
        valor_total = _money(requisicao["valor_total"])
        forma_pagamento = requisicao["forma_pagamento"]
        numero_transacao = requisicao["numero_transacao"]
        repeticao = buscar_repeticao(
            db,
            tenant_id=tenant_id,
            cliente_id=cliente_id,
            request_id=request_id,
            requisicao=requisicao,
        )
        if repeticao:
            return completar_comissoes_lote(db, repeticao)
        instante_recebimento = now_brasilia()

        logger.info(f"Vendas IDs: {vendas_ids}")
        logger.info(f"Valor total: {valor_total}")
        logger.info(f"Forma pagamento: {forma_pagamento}")

        # Validar se há caixa aberto
        caixa_aberto, _ = buscar_caixa_para_recebimento(
            db,
            tenant_id=tenant_id,
            usuario_id=current_user.id,
            caixa_id=requisicao.get("caixa_id"),
            bloquear_caixa=True,
        )

        logger.info(f"Caixa aberto: {caixa_aberto}")

        if not caixa_aberto:
            raise HTTPException(
                status_code=400,
                detail="Não há caixa aberto. Abra o caixa antes de dar baixa nas vendas.",
            )

        banco = None
        if requisicao.get("conta_bancaria_id"):
            from app.financeiro_models import ContaBancaria

            banco = (
                db.query(ContaBancaria)
                .filter(
                    ContaBancaria.id == requisicao["conta_bancaria_id"],
                    ContaBancaria.tenant_id == tenant_id,
                    ContaBancaria.ativa.is_(True),
                )
                .populate_existing()
                .with_for_update()
                .first()
            )
            if not banco:
                raise HTTPException(400, "Conta bancária inexistente ou inativa.")

        lote, repetido = preparar_lote(
            db,
            tenant_id=tenant_id,
            cliente_id=cliente_id,
            current_user=current_user,
            caixa=caixa_aberto,
            request_id=request_id,
            requisicao=requisicao,
        )
        if repetido:
            return completar_comissoes_lote(db, lote)
        instante_recebimento = lote.data

        # Buscar vendas ordenadas da mais antiga para a mais nova
        vendas = (
            db.query(Venda)
            .filter(
                Venda.id.in_(vendas_ids),
                Venda.cliente_id == cliente_id,
                Venda.tenant_id == tenant_id,
                Venda.status.in_(["aberta", "baixa_parcial"]),
            )
            .order_by(Venda.id)
            .populate_existing()
            .with_for_update()
            .all()
        )  # Ordenar das mais antigas para as mais novas

        logger.info(f"Vendas encontradas: {len(vendas)}")

        if not vendas:
            raise HTTPException(status_code=404, detail="Nenhuma venda encontrada")

        if len(vendas) != len(vendas_ids):
            raise HTTPException(
                status_code=400,
                detail="Algumas vendas não foram encontradas ou não estão em aberto",
            )
        # Trava por ID para não inverter locks; aplica da mais antiga para a nova.
        vendas.sort(key=lambda v: (v.data_venda, v.id))

        # Calcular saldo devedor de cada venda
        vendas_com_saldo = []
        total_saldo_devedor = Decimal("0.00")

        for venda in vendas:
            valor_ja_pago, saldo_devedor = _saldo_venda(venda)

            logger.info(
                f"Venda {venda.id}: Total={venda.total}, Pago={valor_ja_pago}, Saldo={saldo_devedor}"
            )

            if saldo_devedor > 0:
                vendas_com_saldo.append(
                    {
                        "venda": venda,
                        "saldo_devedor": saldo_devedor,
                        "valor_ja_pago": valor_ja_pago,
                    }
                )
                total_saldo_devedor += saldo_devedor

        logger.info(
            f"Vendas com saldo: {len(vendas_com_saldo)}, Total saldo: {total_saldo_devedor}"
        )

        if not vendas_com_saldo:
            raise HTTPException(
                status_code=400, detail="Todas as vendas já estão quitadas"
            )

        _validar_valor_baixa(valor_total, total_saldo_devedor)

        # Distribuir o valor proporcionalmente entre as vendas
        valor_restante = valor_total
        vendas_quitadas = []
        vendas_parciais = []
        eventos_campanha_enfileirados = 0
        taxa_total_lote = None
        taxa_distribuida = Decimal("0.00")

        for item in vendas_com_saldo:
            venda = item["venda"]
            saldo_devedor = item["saldo_devedor"]

            # Calcular quanto aplicar nesta venda (proporcional ao saldo)
            if valor_restante <= 0:
                break

            valor_aplicar = min(valor_restante, saldo_devedor)
            status_anterior = venda.status
            evento = None
            movimentacao = None

            logger.info(f"Aplicando {valor_aplicar} na venda {venda.id}")

            # Criar pagamento
            # 🔒 ISOLAMENTO MULTI-TENANT: tenant_id obrigatório
            pagamento, dados_cartao, taxa_total_lote, taxa_distribuida = (
                registrar_pagamento_lote(
                    db=db,
                    venda=venda,
                    requisicao=requisicao,
                    valor_aplicar=valor_aplicar,
                    valor_total=valor_total,
                    valor_restante=valor_restante,
                    taxa_total_lote=taxa_total_lote,
                    taxa_distribuida=taxa_distribuida,
                    caixa_aberto=caixa_aberto,
                    lote=lote,
                    current_user=current_user,
                    tenant_id=tenant_id,
                    instante_recebimento=instante_recebimento,
                    forma_pagamento=forma_pagamento,
                    numero_transacao=numero_transacao,
                )
            )

            # Atualizar status da venda
            novo_valor_pago = item["valor_ja_pago"] + valor_aplicar
            novo_saldo = _money(venda.total) - novo_valor_pago

            if novo_saldo <= 0:  # Quitada
                venda.status = "finalizada"
                vendas_quitadas.append(
                    {
                        "id": venda.id,
                        "numero_venda": venda.numero_venda,
                        "valor_baixado": valor_aplicar,
                        "saldo_anterior": saldo_devedor,
                    }
                )
                if venda.cliente_id and not venda.nao_gerar_beneficios:
                    from app.campaigns.models import CampaignEventQueue, EventOriginEnum
                    from app.campaigns.baixa_lote_reversal import (
                        snapshot_beneficios_baixa_lote,
                    )

                    beneficios_anteriores = snapshot_beneficios_baixa_lote(
                        db, tenant_id, venda.id
                    )
                    evento = CampaignEventQueue(
                        tenant_id=tenant_id,
                        event_type="purchase_completed",
                        event_origin=EventOriginEnum.user_action,
                        event_depth=0,
                        payload={
                            "customer_id": venda.cliente_id,
                            "venda_id": venda.id,
                            "venda_total": float(venda.total or 0),
                            "canal": venda.canal or "loja_fisica",
                            "baixa_lote_id": lote.id,
                            "baixa_lote_beneficios_anteriores": beneficios_anteriores,
                        },
                    )
                    db.add(evento)
                    eventos_campanha_enfileirados += 1
            else:  # Baixa parcial
                venda.status = "baixa_parcial"
                vendas_parciais.append(
                    {
                        "id": venda.id,
                        "numero_venda": venda.numero_venda,
                        "valor_baixado": valor_aplicar,
                        "saldo_restante": novo_saldo,
                        "saldo_anterior": saldo_devedor,
                    }
                )

            get_or_build_venda_rentabilidade_snapshot(
                venda,
                db,
                tenant_id,
                persist_if_missing=True,
                force_refresh=True,
            )

            # PIX/cartão são auditados pelo pagamento associado, sem espelho físico.
            if str(forma_pagamento).strip().casefold() == "dinheiro":
                # 🔒 ISOLAMENTO MULTI-TENANT: tenant_id obrigatório
                movimentacao = MovimentacaoCaixa(
                    caixa_id=caixa_aberto.id,
                    tipo="venda",
                    categoria="venda",
                    valor=valor_aplicar,
                    forma_pagamento=forma_pagamento,
                    descricao=f"Baixa venda #{venda.id} - {venda.cliente.nome if venda.cliente else 'Cliente avulso'}",
                    venda_id=venda.id,
                    usuario_id=current_user.id,
                    usuario_nome=current_user.nome
                    or getattr(current_user, "username", None)
                    or current_user.email,
                    data_movimento=instante_recebimento,
                    tenant_id=tenant_id,  # ✅ Garantir isolamento entre empresas
                )
                db.add(movimentacao)

            # Dar baixa no contas a receber (se existir)
            conta_receber = (
                db.query(ContaReceber)
                .filter(
                    ContaReceber.venda_id == venda.id,
                    ContaReceber.tenant_id == tenant_id,
                    ContaReceber.status.in_(
                        ["pendente", "baixa_parcial", "parcial", "vencido", "vencida"]
                    ),
                )
                .populate_existing()
                .with_for_update()
                .first()
            )

            if not conta_receber:
                outras_contas = (
                    db.query(ContaReceber.id)
                    .filter(
                        ContaReceber.venda_id == venda.id,
                        ContaReceber.tenant_id == tenant_id,
                        ContaReceber.status.notin_(["cancelado", "cancelada"]),
                    )
                    .first()
                )
                if outras_contas:
                    raise HTTPException(
                        409,
                        "O financeiro da venda diverge de seu saldo. Confira as contas a receber antes da baixa.",
                    )
                conta_receber = _criar_conta_receber_faltante_baixa_lote(
                    db=db,
                    venda=venda,
                    current_user=current_user,
                    tenant_id=tenant_id,
                    valor_ja_recebido=item["valor_ja_pago"],
                    data_referencia=instante_recebimento,
                )

            if conta_receber:
                if (
                    _money(conta_receber.valor_final)
                    - _money(conta_receber.valor_recebido)
                    < valor_aplicar
                ):
                    raise HTTPException(
                        409,
                        "A venda tem parcelas ou saldo financeiro diferente. Registre o recebimento nas contas a receber para conferir o rateio.",
                    )
                valor_ja_recebido = _money(conta_receber.valor_recebido)
                novo_valor_recebido = valor_ja_recebido + valor_aplicar

                conta_receber.valor_recebido = novo_valor_recebido
                conta_receber.data_recebimento = instante_recebimento.date()

                if _money(conta_receber.valor_final) <= novo_valor_recebido:
                    conta_receber.status = "recebido"
                else:
                    conta_receber.status = "parcial"

                # 🆕 Criar registro de recebimento
                recebimento = Recebimento(
                    conta_receber_id=conta_receber.id,
                    valor_recebido=valor_aplicar,
                    data_recebimento=instante_recebimento.date(),
                    observacoes="\n".join(
                        parte
                        for parte in (
                            f"Baixa em lote #{lote.id} - {forma_pagamento}",
                            requisicao.get("observacoes"),
                        )
                        if parte
                    ),
                    user_id=current_user.id,
                    tenant_id=tenant_id,  # ✅ Garantir isolamento multi-tenant
                    caixa_id=caixa_aberto.id,
                    conta_bancaria_id=banco.id if banco else None,
                    forma_pagamento_id=requisicao.get("forma_pagamento_id"),
                    numero_parcelas=requisicao.get("numero_parcelas", 1),
                    operadora_id=pagamento.operadora_id,
                    bandeira=pagamento.bandeira,
                    nsu_cartao=pagamento.nsu_cartao,
                )
                db.add(recebimento)
                db.flush()
                repasse_ids = []
                if (
                    banco
                    and str(forma_pagamento).strip().casefold() != "dinheiro"
                    and not dados_cartao
                ):
                    from app.financeiro_models import MovimentacaoFinanceira

                    db.add(
                        MovimentacaoFinanceira(
                            tenant_id=tenant_id,
                            user_id=current_user.id,
                            conta_bancaria_id=banco.id,
                            forma_pagamento_id=requisicao.get("forma_pagamento_id"),
                            tipo="entrada",
                            status="realizado",
                            valor=valor_aplicar,
                            data_movimento=instante_recebimento,
                            origem_tipo="recebimento",
                            origem_id=recebimento.id,
                            documento=f"RECEBIMENTO-{recebimento.id}",
                            descricao=f"Baixa em lote #{lote.id} - {conta_receber.descricao}",
                            observacoes=recebimento.observacoes,
                        )
                    )
                    banco.saldo_atual = _money(banco.saldo_atual) + valor_aplicar
                if dados_cartao:
                    from app.financeiro import ContasReceberService

                    criacao_repasse = ContasReceberService.criar_de_venda(
                        venda=venda,
                        pagamentos=[pagamento],
                        user_id=current_user.id,
                        db=db,
                        manter_repasses_pendentes=True,
                    )
                    repasse_ids = criacao_repasse["contas_criadas"]
                    for repasse in (
                        db.query(ContaReceber)
                        .filter(
                            ContaReceber.tenant_id == tenant_id,
                            ContaReceber.id.in_(repasse_ids),
                        )
                        .all()
                    ):
                        atualizar_previsao(
                            db,
                            tenant_id=tenant_id,
                            conta=repasse,
                            user_id=current_user.id,
                            instante=instante_recebimento,
                        )

                # 🆕 CRIAR LANÇAMENTO REALIZADO NO FLUXO DE CAIXA
                fluxo_realizado = FluxoCaixa(
                    usuario_id=current_user.id,
                    tipo="entrada",
                    categoria="Recebimento de Venda",
                    descricao=f"Baixa venda #{venda.numero_venda} - {venda.cliente.nome if venda.cliente else 'Cliente avulso'}",
                    valor=valor_aplicar,
                    data_movimentacao=instante_recebimento,
                    data_prevista=None,
                    status="realizado",
                    origem_tipo="conta_receber",
                    origem_id=conta_receber.id,
                )
                if dados_cartao:
                    # O cliente pagou, mas o dinheiro só entra no repasse da operadora.
                    fluxo_realizado = None
                else:
                    db.add(fluxo_realizado)
                    fluxo_realizado.tenant_id = tenant_id

                logger.info(
                    f"✅ Fluxo de caixa REALIZADO criado: R$ {valor_aplicar:.2f}"
                )

                fluxo_previsto = atualizar_previsao(
                    db,
                    tenant_id=tenant_id,
                    conta=conta_receber,
                    user_id=current_user.id,
                    instante=instante_recebimento,
                )
                registrar_item(
                    db,
                    lote=lote,
                    venda=venda,
                    pagamento=pagamento,
                    conta=conta_receber,
                    recebimento=recebimento,
                    movimento=movimentacao,
                    fluxo=fluxo_realizado,
                    previsao=fluxo_previsto,
                    evento=evento,
                    status_anterior=status_anterior,
                    repasse_ids=repasse_ids,
                )

            valor_restante -= valor_aplicar

        if eventos_campanha_enfileirados:
            logger.info(
                "[Campanhas] %d purchase_completed enfileirado(s) pela baixa em lote",
                eventos_campanha_enfileirados,
            )

        resultado = {
            "success": True,
            "lote_id": lote.id,
            "total_vendas_afetadas": len(vendas_quitadas) + len(vendas_parciais),
            "vendas_quitadas": [
                {
                    chave: float(valor) if isinstance(valor, Decimal) else valor
                    for chave, valor in item.items()
                }
                for item in vendas_quitadas
            ],
            "vendas_parciais": [
                {
                    chave: float(valor) if isinstance(valor, Decimal) else valor
                    for chave, valor in item.items()
                }
                for item in vendas_parciais
            ],
            "valor_total_baixado": float(valor_total),
            "valor_restante": float(valor_restante),
            "message": f"Baixa realizada com sucesso! {len(vendas_quitadas)} vendas quitadas, {len(vendas_parciais)} com baixa parcial.",
        }
        lote.resultado = resultado
        auditar_lote(db, lote, current_user, "registrar_baixa_lote")
        db.commit()
        return completar_comissoes_lote(db, lote)
    except IntegrityError:
        db.rollback()
        # Dois caixas podem reenviar a mesma chave ao mesmo tempo. A restrição
        # única escolhe o vencedor; o segundo devolve o resultado já confirmado.
        repeticao = buscar_repeticao(
            db,
            tenant_id=tenant_id,
            cliente_id=cliente_id,
            request_id=request_id,
            requisicao=requisicao,
        )
        if repeticao and repeticao.resultado:
            return completar_comissoes_lote(db, repeticao)
        logger.exception("Falha de integridade ao registrar baixa em lote")
        raise HTTPException(
            409,
            "Não foi possível registrar a baixa. Atualize os saldos e tente novamente. Nenhum valor foi alterado.",
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        logger.info(f"ERRO NO PROCESSAMENTO: {str(e)}")
        import traceback

        traceback.print_exc()
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Erro ao processar baixa: {str(e)}"
        )
