from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO
from typing import Any, Dict, List, Optional
from urllib.parse import quote
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import desc
from sqlalchemy.orm import Session, joinedload

from .auth.dependencies import get_current_user_and_tenant
from .compras_pendencias_models import (
    CompraPendenciaFornecedor,
    CompraPendenciaFornecedorHistorico,
    CompraPendenciaFornecedorItem,
)
from .db import get_session
from .models import Cliente
from .produtos_models import (
    NotaEntrada,
    NotaEntradaItem,
    PedidoCompra,
    PedidoCompraNotaEntrada,
)
from .services.email_service import is_email_configured, send_email


router = APIRouter(prefix="/compras-pendencias", tags=["Compras - Pendencias"])

UNIT_PRECISION = Decimal("0.0001")
PENDENCIA_STATUS_ABERTA = "aberta"
PENDENCIA_STATUS_AGUARDANDO = "aguardando_fornecedor"
PENDENCIA_STATUS_TRATATIVA = "em_tratativa"
PENDENCIA_STATUS_RESOLVIDA = "resolvida"
PENDENCIA_STATUS_CANCELADA = "cancelada"
PENDENCIA_STATUS_VALIDOS = {
    PENDENCIA_STATUS_ABERTA,
    PENDENCIA_STATUS_AGUARDANDO,
    PENDENCIA_STATUS_TRATATIVA,
    PENDENCIA_STATUS_RESOLVIDA,
    PENDENCIA_STATUS_CANCELADA,
}
PENDENCIA_STATUS_FINAIS = {PENDENCIA_STATUS_RESOLVIDA, PENDENCIA_STATUS_CANCELADA}


class CriarPendenciaNotaPayload(BaseModel):
    prazo_previsto: Optional[datetime] = None
    observacao: Optional[str] = None
    email_destinatario: Optional[str] = None
    email_assunto: Optional[str] = None
    email_mensagem: Optional[str] = None


class AtualizarPendenciaPayload(BaseModel):
    status: Optional[str] = None
    prazo_previsto: Optional[datetime] = None
    observacao: Optional[str] = None
    resolucao_observacao: Optional[str] = None


class RegistrarEmailPayload(BaseModel):
    email_destinatario: Optional[str] = None
    email_assunto: Optional[str] = None
    email_mensagem: str = Field(min_length=3)
    observacao: Optional[str] = None


def _normalizar_texto(valor: Optional[str]) -> Optional[str]:
    if valor is None:
        return None
    texto = str(valor).strip()
    return texto or None


def _round_quantity(value: Any) -> float:
    try:
        decimal_value = Decimal(str(value if value is not None else 0))
    except Exception:
        decimal_value = Decimal("0")
    return float(decimal_value.quantize(UNIT_PRECISION, rounding=ROUND_HALF_UP))


def _quantidades_conferencia_item(item: NotaEntradaItem) -> Dict[str, float]:
    quantidade_nf = _round_quantity(item.quantidade)
    quantidade_conferida = item.quantidade_conferida
    if quantidade_conferida is None:
        quantidade_conferida = quantidade_nf
    quantidade_conferida = max(
        0.0, min(_round_quantity(quantidade_conferida), quantidade_nf)
    )

    quantidade_avariada = max(0.0, _round_quantity(item.quantidade_avariada))
    max_avariada = max(quantidade_nf - quantidade_conferida, 0.0)
    quantidade_avariada = min(quantidade_avariada, max_avariada)
    quantidade_faltante = max(
        quantidade_nf - quantidade_conferida - quantidade_avariada, 0.0
    )

    return {
        "quantidade_nf": quantidade_nf,
        "quantidade_conferida": quantidade_conferida,
        "quantidade_avariada": quantidade_avariada,
        "quantidade_faltante": _round_quantity(quantidade_faltante),
    }


def _status_conferencia_item(quantidades: Dict[str, float]) -> str:
    tem_avaria = quantidades["quantidade_avariada"] > 0
    tem_falta = quantidades["quantidade_faltante"] > 0
    if tem_avaria and tem_falta:
        return "falta_avaria"
    if tem_avaria:
        return "avaria"
    if tem_falta:
        return "falta"
    return "ok"


def _divergencia_item(item: NotaEntradaItem) -> Dict[str, Any]:
    quantidades = _quantidades_conferencia_item(item)
    status_conferencia = _status_conferencia_item(quantidades)
    valor_unitario = float(item.valor_unitario or 0)
    quantidade_divergente = (
        quantidades["quantidade_faltante"] + quantidades["quantidade_avariada"]
    )
    return {
        **quantidades,
        "status_conferencia": status_conferencia,
        "tem_divergencia": status_conferencia != "ok",
        "valor_unitario": valor_unitario,
        "valor_total_divergente": round(quantidade_divergente * valor_unitario, 2),
        "acao_sugerida": item.acao_sugerida
        or ("contatar_fornecedor" if status_conferencia != "ok" else "sem_acao"),
        "observacao": _normalizar_texto(item.observacao_conferencia),
    }


def _buscar_nota(db: Session, tenant_id, nota_id: int) -> NotaEntrada:
    nota = (
        db.query(NotaEntrada)
        .options(
            joinedload(NotaEntrada.itens).joinedload(NotaEntradaItem.produto),
            joinedload(NotaEntrada.pedidos_compra_vinculos).joinedload(
                PedidoCompraNotaEntrada.pedido
            ),
        )
        .filter(NotaEntrada.id == nota_id, NotaEntrada.tenant_id == tenant_id)
        .first()
    )
    if not nota:
        raise HTTPException(status_code=404, detail="NF de entrada nao encontrada.")
    return nota


def _pedido_principal_da_nota(
    db: Session, nota: NotaEntrada, tenant_id
) -> Optional[PedidoCompra]:
    vinculos = list(getattr(nota, "pedidos_compra_vinculos", []) or [])
    for vinculo in vinculos:
        if getattr(vinculo, "pedido", None):
            return vinculo.pedido

    if nota.id:
        return (
            db.query(PedidoCompra)
            .filter(
                PedidoCompra.nota_entrada_id == nota.id,
                PedidoCompra.tenant_id == tenant_id,
            )
            .order_by(desc(PedidoCompra.id))
            .first()
        )
    return None


def _buscar_fornecedor(db: Session, nota: NotaEntrada, tenant_id) -> Optional[Cliente]:
    if not nota.fornecedor_id:
        return None
    return (
        db.query(Cliente)
        .filter(Cliente.id == nota.fornecedor_id, Cliente.tenant_id == tenant_id)
        .first()
    )


def _itens_divergentes(nota: NotaEntrada) -> List[Dict[str, Any]]:
    itens = []
    for item in getattr(nota, "itens", []) or []:
        divergencia = _divergencia_item(item)
        if divergencia["tem_divergencia"]:
            itens.append({"item": item, "divergencia": divergencia})
    return itens


def _resumo_pendencia(itens: List[Dict[str, Any]]) -> Dict[str, Any]:
    total_faltante = sum(row["divergencia"]["quantidade_faltante"] for row in itens)
    total_avariada = sum(row["divergencia"]["quantidade_avariada"] for row in itens)
    valor = sum(row["divergencia"]["valor_total_divergente"] for row in itens)
    return {
        "itens": len(itens),
        "faltante": _round_quantity(total_faltante),
        "avariada": _round_quantity(total_avariada),
        "valor_estimado": round(valor, 2),
    }


def _formatar_qtd(valor: Any) -> str:
    numero = float(valor or 0)
    texto = f"{numero:.4f}".rstrip("0").rstrip(".")
    return texto or "0"


def _formatar_moeda(valor: Any) -> str:
    numero = float(valor or 0)
    return f"R$ {numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _montar_assunto(nota: NotaEntrada, pedido: Optional[PedidoCompra]) -> str:
    pedido_txt = f" - Pedido {pedido.numero_pedido}" if pedido else ""
    return f"Divergencias na NF {nota.numero_nota}{pedido_txt}"


def _montar_mensagem(
    nota: NotaEntrada,
    pedido: Optional[PedidoCompra],
    itens: List[Dict[str, Any]],
    prazo_previsto: Optional[datetime] = None,
) -> str:
    resumo = _resumo_pendencia(itens)
    linhas = [
        f"Ola, {nota.fornecedor_nome}.",
        "",
        "Identificamos divergencias durante a conferencia da mercadoria.",
        f"NF: {nota.numero_nota} | Emissao: {nota.data_emissao.strftime('%d/%m/%Y') if nota.data_emissao else '-'}",
    ]
    if pedido:
        linhas.append(f"Pedido de compra: {pedido.numero_pedido}")
    linhas.extend(
        [
            f"Itens com divergencia: {resumo['itens']}",
            f"Quantidade faltante: {_formatar_qtd(resumo['faltante'])}",
            f"Quantidade avariada: {_formatar_qtd(resumo['avariada'])}",
            f"Valor estimado das divergencias: {_formatar_moeda(resumo['valor_estimado'])}",
            "",
            "Itens:",
        ]
    )
    for row in itens:
        item = row["item"]
        div = row["divergencia"]
        linhas.append(
            "- "
            f"{item.descricao} | NF: {_formatar_qtd(div['quantidade_nf'])} | "
            f"recebido: {_formatar_qtd(div['quantidade_conferida'])} | "
            f"faltante: {_formatar_qtd(div['quantidade_faltante'])} | "
            f"avariado: {_formatar_qtd(div['quantidade_avariada'])}"
        )
        if div.get("observacao"):
            linhas.append(f"  Observacao: {div['observacao']}")
    linhas.extend(
        [
            "",
            "Pode nos orientar como devemos proceder para resolver essa pendencia?",
        ]
    )
    if prazo_previsto:
        linhas.append(
            f"Prazo interno previsto para retorno: {prazo_previsto.strftime('%d/%m/%Y')}."
        )
    linhas.extend(["", "Obrigado."])
    return "\n".join(linhas)


def _adicionar_historico(
    pendencia: CompraPendenciaFornecedor,
    tipo: str,
    user_id: int,
    observacao: Optional[str] = None,
    status_anterior: Optional[str] = None,
    status_novo: Optional[str] = None,
) -> None:
    pendencia.historico.append(
        CompraPendenciaFornecedorHistorico(
            tenant_id=pendencia.tenant_id,
            tipo=tipo,
            observacao=_normalizar_texto(observacao),
            status_anterior=status_anterior,
            status_novo=status_novo,
            user_id=user_id,
        )
    )


def _sincronizar_itens_pendencia(
    db: Session,
    pendencia: CompraPendenciaFornecedor,
    itens: List[Dict[str, Any]],
) -> None:
    if pendencia.id:
        db.query(CompraPendenciaFornecedorItem).filter(
            CompraPendenciaFornecedorItem.pendencia_id == pendencia.id,
            CompraPendenciaFornecedorItem.tenant_id == pendencia.tenant_id,
        ).delete(synchronize_session=False)

    for row in itens:
        item = row["item"]
        div = row["divergencia"]
        pendencia.itens.append(
            CompraPendenciaFornecedorItem(
                tenant_id=pendencia.tenant_id,
                nota_entrada_item_id=item.id,
                produto_id=item.produto_id,
                codigo_produto=item.codigo_produto,
                descricao=item.descricao,
                unidade=item.unidade,
                quantidade_nf=div["quantidade_nf"],
                quantidade_recebida=div["quantidade_conferida"],
                quantidade_faltante=div["quantidade_faltante"],
                quantidade_avariada=div["quantidade_avariada"],
                valor_unitario=div["valor_unitario"],
                valor_total_divergente=div["valor_total_divergente"],
                status_conferencia=div["status_conferencia"],
                acao_sugerida=div["acao_sugerida"],
                observacao=div["observacao"],
            )
        )


def _serializar_historico(item: CompraPendenciaFornecedorHistorico) -> Dict[str, Any]:
    usuario = getattr(item, "user", None)
    return {
        "id": item.id,
        "tipo": item.tipo,
        "observacao": item.observacao,
        "status_anterior": item.status_anterior,
        "status_novo": item.status_novo,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "usuario": getattr(usuario, "nome", None) or getattr(usuario, "email", None),
    }


def _serializar_item(item: CompraPendenciaFornecedorItem) -> Dict[str, Any]:
    return {
        "id": item.id,
        "nota_entrada_item_id": item.nota_entrada_item_id,
        "produto_id": item.produto_id,
        "codigo_produto": item.codigo_produto,
        "descricao": item.descricao,
        "unidade": item.unidade,
        "quantidade_nf": item.quantidade_nf,
        "quantidade_recebida": item.quantidade_recebida,
        "quantidade_faltante": item.quantidade_faltante,
        "quantidade_avariada": item.quantidade_avariada,
        "valor_unitario": item.valor_unitario,
        "valor_total_divergente": item.valor_total_divergente,
        "status_conferencia": item.status_conferencia,
        "acao_sugerida": item.acao_sugerida,
        "observacao": item.observacao,
        "resolvido": item.resolvido,
    }


def _serializar_pendencia(
    pendencia: CompraPendenciaFornecedor,
    incluir_itens: bool = False,
    incluir_historico: bool = False,
) -> Dict[str, Any]:
    itens = list(getattr(pendencia, "itens", []) or [])
    resumo = {
        "itens": len(itens),
        "faltante": _round_quantity(
            sum(float(item.quantidade_faltante or 0) for item in itens)
        ),
        "avariada": _round_quantity(
            sum(float(item.quantidade_avariada or 0) for item in itens)
        ),
        "valor_estimado": round(
            sum(float(item.valor_total_divergente or 0) for item in itens), 2
        ),
    }
    dados = {
        "id": pendencia.id,
        "codigo": pendencia.codigo,
        "status": pendencia.status,
        "origem": pendencia.origem,
        "tipo": pendencia.tipo,
        "titulo": pendencia.titulo,
        "resumo": pendencia.resumo,
        "resumo_numerico": resumo,
        "fornecedor_id": pendencia.fornecedor_id,
        "fornecedor_nome": pendencia.fornecedor_nome,
        "fornecedor_cnpj": pendencia.fornecedor_cnpj,
        "nota_entrada_id": pendencia.nota_entrada_id,
        "pedido_compra_id": pendencia.pedido_compra_id,
        "numero_nota": pendencia.numero_nota,
        "numero_pedido": pendencia.numero_pedido,
        "prazo_previsto": pendencia.prazo_previsto.isoformat()
        if pendencia.prazo_previsto
        else None,
        "email_destinatario": pendencia.email_destinatario,
        "email_assunto": pendencia.email_assunto,
        "email_mensagem": pendencia.email_mensagem,
        "email_enviado_em": pendencia.email_enviado_em.isoformat()
        if pendencia.email_enviado_em
        else None,
        "pdf_gerado_em": pendencia.pdf_gerado_em.isoformat()
        if pendencia.pdf_gerado_em
        else None,
        "resolvida_em": pendencia.resolvida_em.isoformat()
        if pendencia.resolvida_em
        else None,
        "resolucao_observacao": pendencia.resolucao_observacao,
        "created_at": pendencia.created_at.isoformat()
        if pendencia.created_at
        else None,
        "updated_at": pendencia.updated_at.isoformat()
        if pendencia.updated_at
        else None,
    }
    if incluir_itens:
        dados["itens"] = [_serializar_item(item) for item in itens]
    if incluir_historico:
        dados["historico"] = [
            _serializar_historico(item) for item in (pendencia.historico or [])
        ]
    return dados


def _buscar_pendencia(
    db: Session, tenant_id, pendencia_id: int
) -> CompraPendenciaFornecedor:
    pendencia = (
        db.query(CompraPendenciaFornecedor)
        .options(
            joinedload(CompraPendenciaFornecedor.itens),
            joinedload(CompraPendenciaFornecedor.historico).joinedload(
                CompraPendenciaFornecedorHistorico.user
            ),
        )
        .filter(
            CompraPendenciaFornecedor.id == pendencia_id,
            CompraPendenciaFornecedor.tenant_id == tenant_id,
        )
        .first()
    )
    if not pendencia:
        raise HTTPException(status_code=404, detail="Pendencia nao encontrada.")
    return pendencia


def _pdf_pendencia_bytes(pendencia: CompraPendenciaFornecedor) -> bytes:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError:
        raise HTTPException(
            status_code=500, detail="Biblioteca reportlab nao instalada."
        )

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, topMargin=14 * mm, bottomMargin=14 * mm
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title", parent=styles["Heading1"], fontSize=15, spaceAfter=8
    )
    small_style = ParagraphStyle(
        "Small", parent=styles["Normal"], fontSize=8, leading=10
    )

    def cell(valor: Any) -> Paragraph:
        return Paragraph(escape(str(valor if valor is not None else "-")), small_style)

    elements = [
        Paragraph("PENDENCIA DE FORNECEDOR", title_style),
        Paragraph(escape(pendencia.titulo or ""), styles["Normal"]),
        Spacer(1, 6),
    ]

    info = [
        ["Codigo", pendencia.codigo or "-", "Status", pendencia.status],
        [
            "Fornecedor",
            pendencia.fornecedor_nome,
            "CNPJ",
            pendencia.fornecedor_cnpj or "-",
        ],
        ["NF", pendencia.numero_nota or "-", "Pedido", pendencia.numero_pedido or "-"],
        [
            "Criada em",
            pendencia.created_at.strftime("%d/%m/%Y %H:%M")
            if pendencia.created_at
            else "-",
            "Prazo",
            pendencia.prazo_previsto.strftime("%d/%m/%Y")
            if pendencia.prazo_previsto
            else "-",
        ],
    ]
    info_table = Table(
        [[cell(col) for col in row] for row in info],
        colWidths=[28 * mm, 62 * mm, 28 * mm, 62 * mm],
    )
    info_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F1F5F9")),
                ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#F1F5F9")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    elements.append(info_table)
    elements.append(Spacer(1, 10))

    item_rows = [
        ["Produto", "Qtd NF", "Recebida", "Faltante", "Avariada", "Valor div."]
    ]
    for item in pendencia.itens or []:
        item_rows.append(
            [
                item.descricao,
                _formatar_qtd(item.quantidade_nf),
                _formatar_qtd(item.quantidade_recebida),
                _formatar_qtd(item.quantidade_faltante),
                _formatar_qtd(item.quantidade_avariada),
                _formatar_moeda(item.valor_total_divergente),
            ]
        )
    item_table = Table(
        [[cell(col) for col in row] for row in item_rows],
        colWidths=[70 * mm, 22 * mm, 22 * mm, 22 * mm, 22 * mm, 28 * mm],
        repeatRows=1,
    )
    item_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    elements.append(item_table)

    if pendencia.email_mensagem:
        elements.append(Spacer(1, 10))
        for linha in pendencia.email_mensagem.splitlines():
            elements.append(Paragraph(escape(linha or " "), small_style))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


def _html_email_pendencia(pendencia: CompraPendenciaFornecedor, mensagem: str) -> str:
    linhas = "<br>".join(escape(linha) for linha in (mensagem or "").splitlines())
    return f"""
    <html>
      <body style="font-family:Arial,sans-serif;color:#0f172a;line-height:1.5;">
        <div style="max-width:680px;margin:0 auto;border:1px solid #e2e8f0;border-radius:10px;overflow:hidden;">
          <div style="background:#f8fafc;padding:18px 22px;border-bottom:1px solid #e2e8f0;">
            <div style="font-size:12px;color:#2563eb;font-weight:700;text-transform:uppercase;">Pendencia de fornecedor</div>
            <h1 style="font-size:20px;margin:6px 0 0;">{escape(pendencia.titulo or pendencia.codigo or "Pendencia")}</h1>
          </div>
          <div style="padding:22px;">
            <p><strong>NF:</strong> {escape(str(pendencia.numero_nota or "-"))}</p>
            <p><strong>Pedido:</strong> {escape(str(pendencia.numero_pedido or "-"))}</p>
            <p><strong>Fornecedor:</strong> {escape(str(pendencia.fornecedor_nome or "-"))}</p>
            <div style="margin-top:18px;padding-top:18px;border-top:1px solid #e2e8f0;">{linhas}</div>
            <p style="margin-top:22px;color:#64748b;font-size:12px;">
              O relatorio em PDF segue anexo para conferencia dos itens divergentes.
            </p>
          </div>
        </div>
      </body>
    </html>
    """


@router.get("/")
def listar_pendencias(
    status: Optional[str] = Query(default=None),
    fornecedor: Optional[str] = Query(default=None),
    nota_id: Optional[int] = Query(default=None),
    incluir_finalizadas: bool = Query(default=True),
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    _, tenant_id = current_user_and_tenant
    query = (
        db.query(CompraPendenciaFornecedor)
        .options(joinedload(CompraPendenciaFornecedor.itens))
        .filter(CompraPendenciaFornecedor.tenant_id == tenant_id)
    )
    if status:
        query = query.filter(CompraPendenciaFornecedor.status == status)
    elif not incluir_finalizadas:
        query = query.filter(
            ~CompraPendenciaFornecedor.status.in_(PENDENCIA_STATUS_FINAIS)
        )
    if fornecedor:
        termo = f"%{fornecedor.strip()}%"
        query = query.filter(CompraPendenciaFornecedor.fornecedor_nome.ilike(termo))
    if nota_id:
        query = query.filter(CompraPendenciaFornecedor.nota_entrada_id == nota_id)

    pendencias = (
        query.order_by(
            desc(CompraPendenciaFornecedor.updated_at),
            desc(CompraPendenciaFornecedor.id),
        )
        .limit(200)
        .all()
    )
    return [_serializar_pendencia(item) for item in pendencias]


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


@router.get("/envio/status")
def status_envio_pendencias(
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    return {"email_configurado": is_email_configured()}


@router.get("/{pendencia_id}")
def obter_pendencia(
    pendencia_id: int,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    _, tenant_id = current_user_and_tenant
    pendencia = _buscar_pendencia(db, tenant_id, pendencia_id)
    return _serializar_pendencia(pendencia, incluir_itens=True, incluir_historico=True)


@router.patch("/{pendencia_id}")
def atualizar_pendencia(
    pendencia_id: int,
    payload: AtualizarPendenciaPayload,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = current_user_and_tenant
    pendencia = _buscar_pendencia(db, tenant_id, pendencia_id)
    status_anterior = pendencia.status

    if payload.status is not None:
        status_novo = payload.status.strip()
        if status_novo not in PENDENCIA_STATUS_VALIDOS:
            raise HTTPException(status_code=400, detail="Status de pendencia invalido.")
        pendencia.status = status_novo
        if status_novo == PENDENCIA_STATUS_RESOLVIDA:
            pendencia.resolvida_em = datetime.utcnow()
        elif status_anterior == PENDENCIA_STATUS_RESOLVIDA:
            pendencia.resolvida_em = None

    if payload.prazo_previsto is not None:
        pendencia.prazo_previsto = payload.prazo_previsto
    if payload.resolucao_observacao is not None:
        pendencia.resolucao_observacao = _normalizar_texto(payload.resolucao_observacao)
    pendencia.updated_at = datetime.utcnow()

    if payload.status is not None and status_anterior != pendencia.status:
        _adicionar_historico(
            pendencia,
            "status_alterado",
            current_user.id,
            payload.observacao,
            status_anterior,
            pendencia.status,
        )
    elif payload.observacao:
        _adicionar_historico(
            pendencia, "observacao", current_user.id, payload.observacao
        )

    db.commit()
    pendencia = _buscar_pendencia(db, tenant_id, pendencia_id)
    return _serializar_pendencia(pendencia, incluir_itens=True, incluir_historico=True)


@router.post("/{pendencia_id}/registrar-email")
def registrar_email_pendencia(
    pendencia_id: int,
    payload: RegistrarEmailPayload,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = current_user_and_tenant
    pendencia = _buscar_pendencia(db, tenant_id, pendencia_id)
    status_anterior = pendencia.status

    pendencia.email_destinatario = (
        _normalizar_texto(payload.email_destinatario) or pendencia.email_destinatario
    )
    pendencia.email_assunto = (
        _normalizar_texto(payload.email_assunto) or pendencia.email_assunto
    )
    pendencia.email_mensagem = payload.email_mensagem.strip()
    pendencia.email_enviado_em = datetime.utcnow()
    if pendencia.status not in PENDENCIA_STATUS_FINAIS:
        pendencia.status = PENDENCIA_STATUS_AGUARDANDO
    pendencia.updated_at = datetime.utcnow()

    _adicionar_historico(
        pendencia,
        "email_registrado",
        current_user.id,
        payload.observacao or "Contato com fornecedor registrado.",
        status_anterior,
        pendencia.status,
    )
    db.commit()
    pendencia = _buscar_pendencia(db, tenant_id, pendencia_id)
    return _serializar_pendencia(pendencia, incluir_itens=True, incluir_historico=True)


@router.post("/{pendencia_id}/enviar-email")
def enviar_email_pendencia(
    pendencia_id: int,
    payload: RegistrarEmailPayload,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = current_user_and_tenant
    pendencia = _buscar_pendencia(db, tenant_id, pendencia_id)

    email_destino = (
        _normalizar_texto(payload.email_destinatario) or pendencia.email_destinatario
    )
    assunto = _normalizar_texto(payload.email_assunto) or pendencia.email_assunto
    mensagem = payload.email_mensagem.strip()

    if not email_destino:
        raise HTTPException(status_code=400, detail="Informe o e-mail do fornecedor.")
    if not assunto:
        raise HTTPException(status_code=400, detail="Informe o assunto do e-mail.")
    if not is_email_configured():
        raise HTTPException(
            status_code=503,
            detail="O envio de e-mail nao esta configurado no servidor.",
        )

    pdf_content = _pdf_pendencia_bytes(pendencia)
    filename = f"pendencia_fornecedor_{pendencia.codigo or pendencia.id}.pdf"
    enviado = send_email(
        to=email_destino,
        subject=assunto,
        html_body=_html_email_pendencia(pendencia, mensagem),
        text_body=mensagem,
        attachments=[
            {
                "filename": filename,
                "content": pdf_content,
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

    status_anterior = pendencia.status
    pendencia.email_destinatario = email_destino
    pendencia.email_assunto = assunto
    pendencia.email_mensagem = mensagem
    pendencia.email_enviado_em = datetime.utcnow()
    pendencia.pdf_gerado_em = datetime.utcnow()
    if pendencia.status not in PENDENCIA_STATUS_FINAIS:
        pendencia.status = PENDENCIA_STATUS_AGUARDANDO
    pendencia.updated_at = datetime.utcnow()
    _adicionar_historico(
        pendencia,
        "email_enviado",
        current_user.id,
        payload.observacao or "E-mail enviado ao fornecedor com o PDF de divergencias.",
        status_anterior,
        pendencia.status,
    )
    db.commit()
    pendencia = _buscar_pendencia(db, tenant_id, pendencia_id)
    return _serializar_pendencia(pendencia, incluir_itens=True, incluir_historico=True)


@router.get("/{pendencia_id}/email-texto")
def obter_email_pendencia(
    pendencia_id: int,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    _, tenant_id = current_user_and_tenant
    pendencia = _buscar_pendencia(db, tenant_id, pendencia_id)
    return {
        "email_destinatario": pendencia.email_destinatario,
        "email_assunto": pendencia.email_assunto,
        "email_mensagem": pendencia.email_mensagem,
    }


@router.get("/{pendencia_id}/pdf")
def baixar_pdf_pendencia(
    pendencia_id: int,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    _, tenant_id = current_user_and_tenant
    pendencia = _buscar_pendencia(db, tenant_id, pendencia_id)
    content = _pdf_pendencia_bytes(pendencia)
    pendencia.pdf_gerado_em = datetime.utcnow()
    db.commit()

    filename = f"pendencia_fornecedor_{pendencia.codigo or pendencia.id}.pdf"
    return StreamingResponse(
        BytesIO(content),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"
        },
    )
