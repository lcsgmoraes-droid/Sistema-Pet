"""Rotas de transferencia de estoque para parceiro."""

from datetime import date, datetime
from decimal import Decimal
import io
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session

from .auth.dependencies import get_current_user_and_tenant
from .bling_estoque_sync import sincronizar_bling_background
from .db import get_session
from .estoque.transferencia_parceiro_documents import (
    _gerar_pdf_transferencia_parceiro_bytes,
    _gerar_pdf_transferencias_parceiro_consolidado_bytes,
    _montar_email_transferencia_parceiro,
    _saldo_conta_receber,
    _status_transferencia_parceiro,
)
from .estoque.transferencia_parceiro_schemas import (
    TransferenciaParceiroContaPagarCompensacaoItem,
    TransferenciaParceiroContaPagarCompensacaoResponse,
    TransferenciaParceiroEnviarEmailRequest,
    TransferenciaParceiroHistoricoItem,
    TransferenciaParceiroHistoricoMovItem,
    TransferenciaParceiroHistoricoResponse,
    TransferenciaParceiroHistoricoTotais,
    TransferenciaParceiroItemRequest,
    TransferenciaParceiroPdfConsolidadoRequest,
    TransferenciaParceiroRecebimentoRequest,
    TransferenciaParceiroRequest,
)
from .estoque.transferencia_parceiro_support import (
    _MOTIVO_TRANSFERENCIA_PARCEIRO_EDICAO,
    _MOTIVO_TRANSFERENCIA_PARCEIRO_ESTOQUE,
    _REFERENCIA_TRANSFERENCIA_PARCEIRO_EDICAO,
    _buscar_conta_transferencia_parceiro,
    _buscar_transferencias_parceiro_filtradas,
    _detectar_modo_baixa_transferencia,
    _gerar_codigo_transferencia_parceiro,
    _listar_itens_por_conta_transferencia_parceiro,
    _listar_itens_transferencia_parceiro,
    _montar_observacoes_transferencia_parceiro,
    _obter_dre_subcategoria_receita_padrao,
    _obter_ou_criar_categoria_financeira_transferencia,
    _obter_ultimo_recebimento_transferencia,
    _preparar_itens_transferencia_parceiro,
    _restaurar_lotes_consumidos_transferencia,
    _texto_limpo,
)
from .estoque.transferencia_parceiro_baixa_routes import (
    router as transferencia_parceiro_baixa_router,
)
from .estoque.transferencia_parceiro_baixa_lote_routes import (
    router as transferencia_parceiro_baixa_lote_router,
)
from .estoque.service import EstoqueService
from .financeiro_models import ContaReceber
from .models import Cliente
from .produtos_models import EstoqueMovimentacao
from .security.permissions_decorator import require_permission
from .services.email_service import is_email_configured, send_email
import logging


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/estoque", tags=["Estoque - Transferencia Parceiro"])

__all__ = [
    "TransferenciaParceiroContaPagarCompensacaoItem",
    "TransferenciaParceiroContaPagarCompensacaoResponse",
    "TransferenciaParceiroEnviarEmailRequest",
    "TransferenciaParceiroHistoricoItem",
    "TransferenciaParceiroHistoricoMovItem",
    "TransferenciaParceiroHistoricoResponse",
    "TransferenciaParceiroHistoricoTotais",
    "TransferenciaParceiroItemRequest",
    "TransferenciaParceiroPdfConsolidadoRequest",
    "TransferenciaParceiroRecebimentoRequest",
    "TransferenciaParceiroRequest",
    "_gerar_pdf_transferencia_parceiro_bytes",
    "_gerar_pdf_transferencias_parceiro_consolidado_bytes",
    "_montar_email_transferencia_parceiro",
    "_status_transferencia_parceiro",
    "router",
]


@router.post("/transferencia-parceiro", status_code=status.HTTP_201_CREATED)
@require_permission("produtos.editar")
def transferir_estoque_para_parceiro(
    payload: TransferenciaParceiroRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Transfere estoque para um parceiro pelo custo.

    Regras:
    - baixa estoque via FIFO/lotes;
    - nao cria venda nem entra no faturamento do PDV;
    - gera um contas a receber separado para o ressarcimento do parceiro.
    """
    current_user, tenant_id = user_and_tenant

    parceiro = (
        db.query(Cliente)
        .filter(
            Cliente.id == payload.parceiro_id,
            Cliente.tenant_id == tenant_id,
            or_(Cliente.ativo.is_(True), Cliente.ativo.is_(None)),
        )
        .first()
    )
    if not parceiro:
        raise HTTPException(status_code=404, detail="Pessoa nao encontrada")

    itens_validos = [item for item in payload.itens if float(item.quantidade or 0) > 0]
    if not itens_validos:
        raise HTTPException(
            status_code=400,
            detail="Informe ao menos um item com quantidade maior que zero",
        )

    codigo_transferencia = (
        _texto_limpo(payload.documento) or _gerar_codigo_transferencia_parceiro()
    )
    conta_existente = (
        db.query(ContaReceber)
        .filter(
            ContaReceber.tenant_id == str(tenant_id),
            ContaReceber.documento == codigo_transferencia,
        )
        .first()
    )
    if conta_existente:
        raise HTTPException(
            status_code=400,
            detail="Ja existe um registro financeiro com este documento",
        )

    try:
        itens_processados, total_transferencia = _preparar_itens_transferencia_parceiro(
            db,
            tenant_id=tenant_id,
            itens_validos=itens_validos,
        )

        categoria_financeira = _obter_ou_criar_categoria_financeira_transferencia(
            db,
            tenant_id=tenant_id,
            user_id=current_user.id,
        )
        dre_subcategoria_id = (
            categoria_financeira.dre_subcategoria_id
            or _obter_dre_subcategoria_receita_padrao(db, tenant_id)
        )

        conta_receber = ContaReceber(
            tenant_id=str(tenant_id),
            descricao=f"Transferencia para parceiro - {parceiro.nome}",
            cliente_id=parceiro.id,
            categoria_id=categoria_financeira.id,
            dre_subcategoria_id=dre_subcategoria_id,
            canal="transferencia_parceiro",
            valor_original=total_transferencia,
            valor_recebido=Decimal("0"),
            valor_final=total_transferencia,
            data_emissao=date.today(),
            data_vencimento=payload.data_vencimento or date.today(),
            status="pendente",
            documento=codigo_transferencia,
            observacoes=_montar_observacoes_transferencia_parceiro(
                payload.observacao,
                itens_processados,
            ),
            user_id=current_user.id,
        )
        db.add(conta_receber)
        db.flush()

        for item in itens_processados:
            observacao_item = (
                f"Transferencia para parceiro {parceiro.nome} pelo custo. "
                f"Conta a receber #{conta_receber.id}."
            )
            if payload.observacao:
                observacao_item = f"{observacao_item} {payload.observacao}"

            resultado_baixa = EstoqueService.baixar_estoque(
                produto_id=item["produto_id"],
                quantidade=item["quantidade"],
                motivo=_MOTIVO_TRANSFERENCIA_PARCEIRO_ESTOQUE,
                referencia_id=conta_receber.id,
                referencia_tipo=_MOTIVO_TRANSFERENCIA_PARCEIRO_ESTOQUE,
                user_id=current_user.id,
                db=db,
                tenant_id=str(tenant_id),
                documento=codigo_transferencia,
                observacao=observacao_item,
                custo_unitario_override=item["custo_unitario"],
                valor_total_override=item["total_item"],
            )
            item["movimentacao_id"] = resultado_baixa["movimentacao_id"]
            item["estoque_novo"] = resultado_baixa["estoque_novo"]

        db.commit()

        for item in itens_processados:
            try:
                sincronizar_bling_background(
                    item["produto_id"],
                    item["estoque_novo"],
                    "transferencia_parceiro",
                )
            except Exception as e_sync:
                logger.warning(
                    f"[BLING-SYNC] Erro ao agendar sync (transferencia-parceiro): {e_sync}"
                )

        return {
            "sucesso": True,
            "documento": codigo_transferencia,
            "conta_receber_id": conta_receber.id,
            "parceiro": {
                "id": parceiro.id,
                "nome": parceiro.nome,
                "codigo": getattr(parceiro, "codigo", None),
                "email": getattr(parceiro, "email", None),
            },
            "data_vencimento": conta_receber.data_vencimento.isoformat()
            if conta_receber.data_vencimento
            else None,
            "total_ressarcimento": float(total_transferencia),
            "itens": itens_processados,
        }
    except HTTPException:
        db.rollback()
        raise
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        db.rollback()
        logger.exception("Erro ao registrar transferencia para parceiro: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Nao foi possivel registrar a transferencia para parceiro",
        )


@router.put("/transferencia-parceiro/{conta_receber_id}")
@require_permission("produtos.editar")
def editar_transferencia_parceiro(
    conta_receber_id: int,
    payload: TransferenciaParceiroRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Edita uma transferencia ainda sem baixa, preservando estoque e financeiro."""
    current_user, tenant_id = user_and_tenant
    conta = _buscar_conta_transferencia_parceiro(db, tenant_id, conta_receber_id)

    if float(conta.valor_recebido or 0) > 0:
        raise HTTPException(
            status_code=400,
            detail=(
                "Esta transferencia ja possui recebimento registrado. "
                "Remova ou trate a baixa financeira antes de editar o lancamento."
            ),
        )

    status_atual = str(getattr(conta, "status", "") or "").strip().lower()
    if status_atual in {"cancelado", "cancelada"}:
        raise HTTPException(
            status_code=400,
            detail="Transferencia cancelada nao pode ser editada.",
        )

    parceiro = (
        db.query(Cliente)
        .filter(
            Cliente.id == payload.parceiro_id,
            Cliente.tenant_id == tenant_id,
            or_(Cliente.ativo.is_(True), Cliente.ativo.is_(None)),
        )
        .first()
    )
    if not parceiro:
        raise HTTPException(status_code=404, detail="Pessoa nao encontrada")

    itens_validos = [item for item in payload.itens if float(item.quantidade or 0) > 0]
    if not itens_validos:
        raise HTTPException(
            status_code=400,
            detail="Informe ao menos um item com quantidade maior que zero",
        )

    codigo_transferencia = (
        _texto_limpo(payload.documento)
        or _texto_limpo(conta.documento)
        or _gerar_codigo_transferencia_parceiro()
    )
    conta_existente = (
        db.query(ContaReceber)
        .filter(
            ContaReceber.tenant_id == str(tenant_id),
            ContaReceber.documento == codigo_transferencia,
            ContaReceber.id != conta.id,
        )
        .first()
    )
    if conta_existente:
        raise HTTPException(
            status_code=400,
            detail="Ja existe um registro financeiro com este documento",
        )

    movimentacoes_anteriores = (
        db.query(EstoqueMovimentacao)
        .filter(
            EstoqueMovimentacao.tenant_id == str(tenant_id),
            EstoqueMovimentacao.referencia_id == conta.id,
            EstoqueMovimentacao.tipo == "saida",
            EstoqueMovimentacao.motivo.in_(
                [_MOTIVO_TRANSFERENCIA_PARCEIRO_ESTOQUE, "transferencia_parceiro"]
            ),
        )
        .order_by(EstoqueMovimentacao.id.asc())
        .all()
    )

    try:
        estoques_finais: dict[int, float] = {}
        produtos_tocados: set[int] = set()
        lotes_restaurados = 0

        for movimentacao in movimentacoes_anteriores:
            produtos_tocados.add(int(movimentacao.produto_id))
            lotes_restaurados += _restaurar_lotes_consumidos_transferencia(
                db, movimentacao
            )
            resultado_estorno = EstoqueService.estornar_estoque(
                produto_id=movimentacao.produto_id,
                quantidade=float(movimentacao.quantidade or 0),
                motivo=_MOTIVO_TRANSFERENCIA_PARCEIRO_EDICAO,
                referencia_id=conta.id,
                referencia_tipo=_REFERENCIA_TRANSFERENCIA_PARCEIRO_EDICAO,
                user_id=current_user.id,
                db=db,
                tenant_id=str(tenant_id),
                documento=conta.documento,
                observacao=(
                    f"Estorno temporario para edicao da transferencia "
                    f"{conta.documento or conta.id}"
                ),
                custo_unitario_override=float(movimentacao.custo_unitario or 0),
                valor_total_override=float(movimentacao.valor_total or 0),
            )
            estoques_finais[int(movimentacao.produto_id)] = resultado_estorno[
                "estoque_novo"
            ]
            db.delete(movimentacao)

        db.flush()

        itens_processados, total_transferencia = _preparar_itens_transferencia_parceiro(
            db,
            tenant_id=tenant_id,
            itens_validos=itens_validos,
        )

        categoria_financeira = None
        if not conta.categoria_id or not conta.dre_subcategoria_id:
            categoria_financeira = _obter_ou_criar_categoria_financeira_transferencia(
                db,
                tenant_id=tenant_id,
                user_id=current_user.id,
            )

        if not conta.categoria_id and categoria_financeira:
            conta.categoria_id = categoria_financeira.id
        if not conta.dre_subcategoria_id:
            conta.dre_subcategoria_id = (
                categoria_financeira.dre_subcategoria_id
                if categoria_financeira
                else None
            ) or _obter_dre_subcategoria_receita_padrao(db, tenant_id)

        conta.descricao = f"Transferencia para parceiro - {parceiro.nome}"
        conta.cliente_id = parceiro.id
        conta.canal = "transferencia_parceiro"
        conta.valor_original = total_transferencia
        conta.valor_final = total_transferencia
        conta.valor_recebido = Decimal("0")
        conta.data_vencimento = (
            payload.data_vencimento or conta.data_vencimento or date.today()
        )
        conta.status = "pendente"
        conta.documento = codigo_transferencia
        conta.observacoes = _montar_observacoes_transferencia_parceiro(
            payload.observacao,
            itens_processados,
        )
        db.add(conta)
        db.flush()

        for item in itens_processados:
            produtos_tocados.add(int(item["produto_id"]))
            observacao_item = (
                f"Transferencia para parceiro {parceiro.nome} pelo custo. "
                f"Conta a receber #{conta.id}. Editada."
            )
            if payload.observacao:
                observacao_item = f"{observacao_item} {payload.observacao}"

            resultado_baixa = EstoqueService.baixar_estoque(
                produto_id=item["produto_id"],
                quantidade=item["quantidade"],
                motivo=_MOTIVO_TRANSFERENCIA_PARCEIRO_ESTOQUE,
                referencia_id=conta.id,
                referencia_tipo=_MOTIVO_TRANSFERENCIA_PARCEIRO_ESTOQUE,
                user_id=current_user.id,
                db=db,
                tenant_id=str(tenant_id),
                documento=codigo_transferencia,
                observacao=observacao_item,
                custo_unitario_override=item["custo_unitario"],
                valor_total_override=item["total_item"],
            )
            item["movimentacao_id"] = resultado_baixa["movimentacao_id"]
            item["estoque_novo"] = resultado_baixa["estoque_novo"]
            estoques_finais[int(item["produto_id"])] = resultado_baixa["estoque_novo"]

        db.commit()

        for produto_id in produtos_tocados:
            estoque_novo = estoques_finais.get(produto_id)
            if estoque_novo is None:
                continue
            try:
                sincronizar_bling_background(
                    produto_id,
                    estoque_novo,
                    "transferencia_parceiro_edicao",
                )
            except Exception as e_sync:
                logger.warning(
                    f"[BLING-SYNC] Erro ao agendar sync (edicao transferencia-parceiro): {e_sync}"
                )

        return {
            "sucesso": True,
            "editado": True,
            "documento": codigo_transferencia,
            "conta_receber_id": conta.id,
            "parceiro": {
                "id": parceiro.id,
                "nome": parceiro.nome,
                "codigo": getattr(parceiro, "codigo", None),
                "email": getattr(parceiro, "email", None),
            },
            "data_vencimento": conta.data_vencimento.isoformat()
            if conta.data_vencimento
            else None,
            "total_ressarcimento": float(total_transferencia),
            "lotes_restaurados": lotes_restaurados,
            "itens": itens_processados,
        }
    except HTTPException:
        db.rollback()
        raise
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        db.rollback()
        logger.exception("Erro ao editar transferencia para parceiro: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Nao foi possivel editar a transferencia para parceiro",
        )


@router.get(
    "/transferencia-parceiro/historico",
    response_model=TransferenciaParceiroHistoricoResponse,
)
@require_permission("produtos.visualizar")
def listar_transferencias_para_parceiro(
    page: int = 1,
    page_size: int = 20,
    parceiro_id: Optional[int] = None,
    status_filtro: Optional[str] = None,
    busca: Optional[str] = None,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lista historico operacional e financeiro das transferencias para parceiro."""
    _current_user, tenant_id = user_and_tenant
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    contas = _buscar_transferencias_parceiro_filtradas(
        db,
        tenant_id=tenant_id,
        parceiro_id=parceiro_id,
        status_filtro=status_filtro,
        busca=busca,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )

    if not contas:
        return TransferenciaParceiroHistoricoResponse(
            items=[],
            totais=TransferenciaParceiroHistoricoTotais(),
            total=0,
            page=page,
            page_size=page_size,
            pages=0,
        )

    itens_por_conta = _listar_itens_por_conta_transferencia_parceiro(
        db,
        tenant_id,
        [conta.id for conta in contas],
        ordem_desc=True,
    )

    registros_filtrados: list[TransferenciaParceiroHistoricoItem] = []
    totais = {
        "total_registros": 0,
        "valor_total": 0.0,
        "valor_recebido": 0.0,
        "saldo_aberto": 0.0,
        "pendentes": 0,
        "recebidas": 0,
        "vencidas": 0,
    }

    for conta in contas:
        status_resolvido, status_label = _status_transferencia_parceiro(conta)
        valor_original = float(conta.valor_original or 0)
        valor_recebido = float(conta.valor_recebido or 0)
        saldo_aberto = _saldo_conta_receber(conta)

        totais["total_registros"] += 1
        totais["valor_total"] += valor_original
        totais["valor_recebido"] += valor_recebido
        totais["saldo_aberto"] += saldo_aberto
        if status_resolvido == "recebido":
            totais["recebidas"] += 1
        elif status_resolvido == "vencido":
            totais["vencidas"] += 1
        elif status_resolvido != "cancelado":
            totais["pendentes"] += 1

        cliente = conta.cliente
        ultimo_recebimento = _obter_ultimo_recebimento_transferencia(conta)
        modo_baixa, modo_baixa_label = _detectar_modo_baixa_transferencia(
            ultimo_recebimento
        )
        forma_pagamento = (
            getattr(ultimo_recebimento, "forma_pagamento", None)
            if ultimo_recebimento
            else None
        )
        registros_filtrados.append(
            TransferenciaParceiroHistoricoItem(
                conta_receber_id=conta.id,
                documento=conta.documento,
                parceiro_id=cliente.id if cliente else None,
                parceiro_nome=cliente.nome if cliente else "Parceiro nao encontrado",
                parceiro_codigo=getattr(cliente, "codigo", None) if cliente else None,
                parceiro_email=getattr(cliente, "email", None) if cliente else None,
                data_emissao=conta.data_emissao,
                data_vencimento=conta.data_vencimento,
                data_recebimento=conta.data_recebimento,
                status=status_resolvido,
                status_label=status_label,
                valor_original=valor_original,
                valor_recebido=valor_recebido,
                saldo_aberto=saldo_aberto,
                modo_baixa=modo_baixa,
                modo_baixa_label=modo_baixa_label,
                forma_pagamento_id=getattr(
                    ultimo_recebimento, "forma_pagamento_id", None
                ),
                forma_pagamento_nome=_texto_limpo(
                    getattr(forma_pagamento, "nome", None)
                ),
                observacoes=conta.observacoes,
                itens=itens_por_conta.get(conta.id, []),
            )
        )

    total = len(registros_filtrados)
    pages = (total + page_size - 1) // page_size if total else 0
    offset = (page - 1) * page_size
    pagina_items = registros_filtrados[offset : offset + page_size]

    return TransferenciaParceiroHistoricoResponse(
        items=pagina_items,
        totais=TransferenciaParceiroHistoricoTotais(
            total_registros=int(totais["total_registros"]),
            valor_total=float(totais["valor_total"]),
            valor_recebido=float(totais["valor_recebido"]),
            saldo_aberto=float(totais["saldo_aberto"]),
            pendentes=int(totais["pendentes"]),
            recebidas=int(totais["recebidas"]),
            vencidas=int(totais["vencidas"]),
        ),
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/transferencia-parceiro/{conta_receber_id}/pdf")
@require_permission("produtos.visualizar")
def gerar_pdf_transferencia_parceiro(
    conta_receber_id: int,
    mostrar_codigo: bool = True,
    mostrar_descricao: bool = True,
    mostrar_quantidade: bool = True,
    mostrar_custo_unitario: bool = True,
    mostrar_total_item: bool = True,
    mostrar_totais: bool = True,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Gera PDF operacional da transferencia com ressarcimento."""
    _current_user, tenant_id = user_and_tenant
    conta = _buscar_conta_transferencia_parceiro(db, tenant_id, conta_receber_id)
    parceiro = conta.cliente
    itens = _listar_itens_transferencia_parceiro(db, tenant_id, conta_receber_id)
    pdf_bytes = _gerar_pdf_transferencia_parceiro_bytes(
        conta,
        parceiro,
        itens,
        {
            "mostrar_codigo": mostrar_codigo,
            "mostrar_descricao": mostrar_descricao,
            "mostrar_quantidade": mostrar_quantidade,
            "mostrar_custo_unitario": mostrar_custo_unitario,
            "mostrar_total_item": mostrar_total_item,
            "mostrar_totais": mostrar_totais,
        },
    )
    nome_documento = (conta.documento or f"TRP-{conta.id:06d}").replace("/", "-")

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="transferencia_{nome_documento}.pdf"'
        },
    )


@router.post("/transferencia-parceiro/pdf-consolidado")
@require_permission("produtos.visualizar")
def gerar_pdf_transferencias_parceiro_consolidado(
    payload: TransferenciaParceiroPdfConsolidadoRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Gera um PDF unico com varias transferencias selecionadas ou filtradas."""
    _current_user, tenant_id = user_and_tenant
    contas = _buscar_transferencias_parceiro_filtradas(
        db,
        tenant_id=tenant_id,
        parceiro_id=payload.parceiro_id,
        status_filtro=payload.status_filtro,
        busca=payload.busca,
        data_inicio=payload.data_inicio,
        data_fim=payload.data_fim,
        conta_receber_ids=payload.conta_receber_ids or None,
    )

    if not contas:
        raise HTTPException(
            status_code=404,
            detail="Nenhuma transferencia encontrada para gerar o PDF consolidado",
        )

    itens_por_conta = _listar_itens_por_conta_transferencia_parceiro(
        db,
        tenant_id,
        [conta.id for conta in contas],
    )

    pdf_bytes = _gerar_pdf_transferencias_parceiro_consolidado_bytes(
        contas,
        itens_por_conta,
        {
            "mostrar_codigo": payload.mostrar_codigo,
            "mostrar_descricao": payload.mostrar_descricao,
            "mostrar_quantidade": payload.mostrar_quantidade,
            "mostrar_custo_unitario": payload.mostrar_custo_unitario,
            "mostrar_total_item": payload.mostrar_total_item,
            "mostrar_totais": payload.mostrar_totais,
        },
    )
    data_ref = datetime.now().strftime("%Y%m%d_%H%M%S")
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="transferencias_consolidadas_{data_ref}.pdf"'
        },
    )


@router.post("/transferencia-parceiro/{conta_receber_id}/enviar-email")
@require_permission("produtos.visualizar")
def enviar_email_transferencia_parceiro(
    conta_receber_id: int,
    payload: TransferenciaParceiroEnviarEmailRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Envia por e-mail o PDF da transferencia usando o cadastro da pessoa."""
    _current_user, tenant_id = user_and_tenant
    conta = _buscar_conta_transferencia_parceiro(db, tenant_id, conta_receber_id)
    parceiro = conta.cliente
    email_destino = _texto_limpo(payload.email) or _texto_limpo(
        getattr(parceiro, "email", None)
    )

    if not email_destino:
        raise HTTPException(
            status_code=400,
            detail="A pessoa selecionada nao possui e-mail cadastrado",
        )

    if not is_email_configured():
        raise HTTPException(
            status_code=503,
            detail="O envio de e-mail nao esta configurado no servidor",
        )

    itens = _listar_itens_transferencia_parceiro(db, tenant_id, conta_receber_id)
    opcoes_documento = {
        "mostrar_codigo": payload.mostrar_codigo,
        "mostrar_descricao": payload.mostrar_descricao,
        "mostrar_quantidade": payload.mostrar_quantidade,
        "mostrar_custo_unitario": payload.mostrar_custo_unitario,
        "mostrar_total_item": payload.mostrar_total_item,
        "mostrar_totais": payload.mostrar_totais,
    }
    pdf_bytes = _gerar_pdf_transferencia_parceiro_bytes(
        conta,
        parceiro,
        itens,
        opcoes_documento,
    )
    assunto_padrao, html_body, text_body = _montar_email_transferencia_parceiro(
        conta,
        parceiro,
        itens,
        mensagem_extra=payload.mensagem,
        opcoes_documento=opcoes_documento,
    )

    enviado = send_email(
        to=email_destino,
        subject=_texto_limpo(payload.assunto) or assunto_padrao,
        html_body=html_body,
        text_body=text_body,
        attachments=[
            {
                "filename": f"transferencia_{(conta.documento or f'TRP-{conta.id:06d}').replace('/', '-')}.pdf",
                "content": pdf_bytes,
                "mime_subtype": "pdf",
            }
        ],
        simulate_if_unconfigured=False,
    )

    if not enviado:
        raise HTTPException(
            status_code=502,
            detail="Nao foi possivel enviar o e-mail. Revise a configuracao SMTP.",
        )

    return {
        "sucesso": True,
        "email": email_destino,
        "documento": conta.documento or f"TRP-{conta.id:06d}",
    }


router.include_router(transferencia_parceiro_baixa_router)
router.include_router(transferencia_parceiro_baixa_lote_router)
