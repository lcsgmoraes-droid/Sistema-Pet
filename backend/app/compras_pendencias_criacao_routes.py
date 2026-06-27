"""Rotas de criacao de pendencias de compras."""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session, joinedload

from .auth.dependencies import get_current_user_and_tenant
from .compras_pendencias_constants import (
    PENDENCIA_STATUS_ABERTA,
    PENDENCIA_STATUS_FINAIS,
)
from .compras_pendencias_models import CompraPendenciaFornecedor
from .compras_pendencias_notas import (
    _buscar_fornecedor,
    _buscar_nota,
    _itens_divergentes,
    _montar_assunto,
    _montar_mensagem,
    _pedido_principal_da_nota,
    _resumo_pendencia,
)
from .compras_pendencias_schemas import CriarPendenciaNotaPayload
from .compras_pendencias_serializacao import (
    _adicionar_historico,
    _buscar_pendencia,
    _serializar_pendencia,
    _sincronizar_itens_pendencia,
)
from .compras_pendencias_utils import _normalizar_texto
from .compras_pendencias_utils import _formatar_moeda, _formatar_qtd
from .db import get_session

router = APIRouter()


@router.post("/notas/{nota_id}")
def criar_pendencia_por_nota(
    nota_id: int,
    payload: CriarPendenciaNotaPayload,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = current_user_and_tenant
    nota = _buscar_nota(db, tenant_id, nota_id)
    itens = _itens_divergentes(nota)
    if not itens:
        raise HTTPException(
            status_code=400,
            detail="Esta NF nao possui divergencias de conferencia para gerar pendencia.",
        )

    pedido = _pedido_principal_da_nota(db, nota, tenant_id)
    fornecedor = _buscar_fornecedor(db, nota, tenant_id)

    pendencia = (
        db.query(CompraPendenciaFornecedor)
        .options(joinedload(CompraPendenciaFornecedor.itens))
        .filter(
            CompraPendenciaFornecedor.tenant_id == tenant_id,
            CompraPendenciaFornecedor.nota_entrada_id == nota.id,
            ~CompraPendenciaFornecedor.status.in_(PENDENCIA_STATUS_FINAIS),
        )
        .order_by(desc(CompraPendenciaFornecedor.id))
        .first()
    )
    nova = pendencia is None
    prazo = payload.prazo_previsto or (datetime.utcnow() + timedelta(days=7))
    assunto = _normalizar_texto(payload.email_assunto) or _montar_assunto(nota, pedido)
    mensagem = _normalizar_texto(payload.email_mensagem) or _montar_mensagem(
        nota, pedido, itens, prazo
    )
    resumo = _resumo_pendencia(itens)
    resumo_txt = (
        f"{resumo['itens']} item(ns) com divergencia: "
        f"{_formatar_qtd(resumo['faltante'])} faltante(s), "
        f"{_formatar_qtd(resumo['avariada'])} avariada(s), "
        f"{_formatar_moeda(resumo['valor_estimado'])} estimado."
    )

    if nova:
        pendencia = CompraPendenciaFornecedor(
            tenant_id=tenant_id,
            status=PENDENCIA_STATUS_ABERTA,
            fornecedor_id=nota.fornecedor_id,
            fornecedor_nome=nota.fornecedor_nome,
            fornecedor_cnpj=nota.fornecedor_cnpj,
            nota_entrada_id=nota.id,
            pedido_compra_id=pedido.id if pedido else None,
            numero_nota=nota.numero_nota,
            numero_pedido=pedido.numero_pedido if pedido else None,
            titulo=f"NF {nota.numero_nota} - {nota.fornecedor_nome}",
            user_id=current_user.id,
        )
        db.add(pendencia)
    else:
        pendencia.fornecedor_id = nota.fornecedor_id
        pendencia.fornecedor_nome = nota.fornecedor_nome
        pendencia.fornecedor_cnpj = nota.fornecedor_cnpj
        pendencia.pedido_compra_id = pedido.id if pedido else pendencia.pedido_compra_id
        pendencia.numero_pedido = (
            pedido.numero_pedido if pedido else pendencia.numero_pedido
        )

    pendencia.resumo = resumo_txt
    pendencia.prazo_previsto = prazo
    pendencia.email_destinatario = _normalizar_texto(
        payload.email_destinatario
    ) or getattr(fornecedor, "email", None)
    pendencia.email_assunto = assunto
    pendencia.email_mensagem = mensagem
    pendencia.updated_at = datetime.utcnow()
    db.flush()

    if not pendencia.codigo:
        pendencia.codigo = (
            f"CPF-{datetime.utcnow().strftime('%Y%m%d')}-{pendencia.id:05d}"
        )

    _sincronizar_itens_pendencia(db, pendencia, itens)
    _adicionar_historico(
        pendencia,
        "criada" if nova else "atualizada",
        current_user.id,
        payload.observacao or "Pendencia gerada a partir das divergencias da NF.",
        None,
        pendencia.status,
    )
    db.commit()
    pendencia = _buscar_pendencia(db, tenant_id, pendencia.id)
    return _serializar_pendencia(pendencia, incluir_itens=True, incluir_historico=True)
