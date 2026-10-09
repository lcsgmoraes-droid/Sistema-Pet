"""
Rotas para o Sistema de Controle de Caixa
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, date, timezone
from pydantic import BaseModel, Field

from app.db import get_session
from app.auth.dependencies import get_current_user_and_tenant
from app.idempotency import idempotent  # ← IDEMPOTÊNCIA
from app.caixa_models import Caixa, MovimentacaoCaixa
from app.caixa.recebimentos import filtro_pagamentos_caixa
from app.caixa.auditoria import registrar_evento_caixa, snapshot_caixa
from app.caixa.auditoria_routes import router as auditoria_router
from app.utils.timezone import now_brasilia
from app.caixa.conferencia import (
    instante_fechamento_sql,
    indicadores_vendas_recebimentos,
    moeda,
    referencia_fechamento,
    snapshot_abertura,
    totais_dinheiro,
)
from app.caixa.escopo import (
    aplicar_escopo_caixa,
    buscar_caixa_aberto,
    buscar_caixa_acessivel,
    caixa_compartilhado_habilitado,
)
from app.financeiro_models import ContaPagar, TipoDespesa
from app.domain.dre.lancamento_dre_sync import atualizar_dre_por_lancamento
from app.pdf_caixa import gerar_pdf_fechamento_caixa

router = APIRouter(prefix="/caixas", tags=["caixas"])
router.include_router(auditoria_router)


# Schemas
class AbrirCaixaSchema(BaseModel):
    valor_abertura: float = Field(ge=0, allow_inf_nan=False)
    caixa_anterior_id: Optional[int] = None
    valor_fechamento_anterior: Optional[float] = Field(
        default=None, ge=0, allow_inf_nan=False
    )
    data_fechamento_anterior: Optional[datetime] = None
    conta_origem_id: Optional[int] = None
    conta_origem_nome: Optional[str] = None
    observacoes_abertura: Optional[str] = None


class FecharCaixaSchema(BaseModel):
    valor_informado: float = Field(ge=0, allow_inf_nan=False)
    observacoes_fechamento: Optional[str] = None


class ReabrirCaixaSchema(BaseModel):
    motivo: str = Field(min_length=10, max_length=1000)


class MovimentacaoSchema(BaseModel):
    tipo: str  # suprimento, sangria, despesa, transferencia, devolucao
    valor: float
    forma_pagamento: Optional[str] = None
    descricao: Optional[str] = None
    categoria: Optional[str] = None
    conta_origem_id: Optional[int] = None
    conta_origem_nome: Optional[str] = None
    conta_destino_id: Optional[int] = None
    conta_destino_nome: Optional[str] = None
    fornecedor_id: Optional[int] = None
    fornecedor_nome: Optional[str] = None
    documento: Optional[str] = None
    tipo_despesa_id: Optional[int] = None


def _ultimo_caixa_fechado(
    db: Session, *, tenant_id, usuario_id: int, compartilhado: bool = False
):
    query = aplicar_escopo_caixa(
        db.query(Caixa).filter(
            Caixa.status == "fechado",
            Caixa.valor_informado.is_not(None),
            Caixa.data_fechamento.is_not(None),
        ),
        tenant_id=tenant_id,
        usuario_id=usuario_id,
        compartilhado=compartilhado,
    )
    return query.order_by(
        instante_fechamento_sql().desc().nullslast(), Caixa.id.desc()
    ).first()


def _validar_referencia_abertura(dados: AbrirCaixaSchema, caixa_anterior) -> None:
    # Clientes antigos continuam compatíveis; o novo formulário envia a referência exibida.
    if "caixa_anterior_id" not in dados.model_fields_set:
        return
    atual = referencia_fechamento(caixa_anterior)
    esperado = (
        None
        if dados.caixa_anterior_id is None
        else {
            "caixa_id": dados.caixa_anterior_id,
            "valor_fechamento": dados.valor_fechamento_anterior,
            "data_fechamento": dados.data_fechamento_anterior.isoformat()
            if dados.data_fechamento_anterior
            else None,
        }
    )
    referencia = (
        {chave: atual[chave] for chave in esperado} if atual and esperado else atual
    )
    if referencia != esperado:
        raise HTTPException(
            status_code=409,
            detail="O último fechamento mudou. Confira a referência atualizada e tente abrir novamente.",
        )


def _serializar_caixa(caixa: Caixa, *, compartilhado: bool) -> dict:
    dados = caixa.to_dict()
    dados["compartilhado"] = compartilhado
    return dados


def _anexar_conferencia_abertura(
    observacoes: str | None, *, caixa_anterior: Caixa | None, valor_abertura: float
) -> str | None:
    if not caixa_anterior or caixa_anterior.valor_informado is None:
        return observacoes
    diferenca = float(valor_abertura) - float(caixa_anterior.valor_informado)
    conferencia = (
        f"[Conferencia de abertura] Caixa anterior #{caixa_anterior.numero_caixa}: "
        f"R$ {float(caixa_anterior.valor_informado):.2f}; abertura: "
        f"R$ {float(valor_abertura):.2f}; diferenca: R$ {diferenca:+.2f}."
    )
    return "\n".join(
        parte for parte in ((observacoes or "").strip(), conferencia) if parte
    )


# Rotas
@router.post("/abrir")
@idempotent()  # 🔒 IDEMPOTÊNCIA: evita abertura duplicada de caixa
async def abrir_caixa(
    dados: AbrirCaixaSchema,
    request: Request,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Abrir um novo caixa"""
    current_user, tenant_id = current_user_and_tenant

    # A trava na configuracao evita duas aberturas simultaneas no modo compartilhado.
    caixa_aberto, compartilhado = buscar_caixa_aberto(
        db,
        tenant_id=tenant_id,
        usuario_id=current_user.id,
        bloquear_config=True,
    )

    if caixa_aberto:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "A empresa já possui um caixa compartilhado aberto. Use o caixa existente."
                if compartilhado
                else "Você já possui um caixa aberto. Feche-o antes de abrir outro."
            ),
        )

    # Gerar número do caixa (próximo número disponível por tenant)
    caixa_anterior = _ultimo_caixa_fechado(
        db,
        tenant_id=tenant_id,
        usuario_id=current_user.id,
        compartilhado=compartilhado,
    )
    _validar_referencia_abertura(dados, caixa_anterior)
    ultimo_caixa = (
        db.query(func.max(Caixa.numero_caixa))
        .filter(Caixa.tenant_id == tenant_id)
        .scalar()
    )
    numero_caixa = (ultimo_caixa or 0) + 1

    # Nome do usuário (fallback para email se nome não estiver preenchido)
    usuario_nome = (
        current_user.nome
        or getattr(current_user, "username", None)
        or current_user.email
    )

    # Criar novo caixa
    novo_caixa = Caixa(
        numero_caixa=numero_caixa,
        usuario_id=current_user.id,
        usuario_nome=usuario_nome,
        valor_abertura=dados.valor_abertura,
        conferencia_abertura=snapshot_abertura(caixa_anterior, dados.valor_abertura),
        conta_origem_id=dados.conta_origem_id,
        conta_origem_nome=dados.conta_origem_nome,
        observacoes_abertura=_anexar_conferencia_abertura(
            dados.observacoes_abertura,
            caixa_anterior=caixa_anterior,
            valor_abertura=dados.valor_abertura,
        ),
        status="aberto",
        data_abertura=now_brasilia(),
        tenant_id=tenant_id,
    )

    db.add(novo_caixa)
    db.commit()
    db.refresh(novo_caixa)

    return _serializar_caixa(novo_caixa, compartilhado=compartilhado)


@router.get("/aberto")
def obter_caixa_aberto(
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Obter o caixa aberto acessivel ao usuario atual."""
    current_user, tenant_id = current_user_and_tenant

    caixa, compartilhado = buscar_caixa_aberto(
        db, tenant_id=tenant_id, usuario_id=current_user.id
    )

    if not caixa:
        return None

    return _serializar_caixa(caixa, compartilhado=compartilhado)


@router.get("/conferencia-abertura")
def obter_conferencia_abertura(
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Informa o ultimo fechamento aplicavel para conferir a proxima abertura."""
    current_user, tenant_id = current_user_and_tenant
    compartilhado = caixa_compartilhado_habilitado(db, tenant_id)
    caixa = _ultimo_caixa_fechado(
        db,
        tenant_id=tenant_id,
        usuario_id=current_user.id,
        compartilhado=compartilhado,
    )
    if not caixa:
        return None
    return referencia_fechamento(caixa)


@router.get("")
def listar_caixas(
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Listar caixas acessiveis ao usuario conforme a configuracao da empresa."""
    current_user, tenant_id = current_user_and_tenant

    compartilhado = caixa_compartilhado_habilitado(db, tenant_id)
    query = aplicar_escopo_caixa(
        db.query(Caixa),
        tenant_id=tenant_id,
        usuario_id=current_user.id,
        compartilhado=compartilhado,
    )

    if data_inicio:
        query = query.filter(Caixa.data_abertura >= datetime.fromisoformat(data_inicio))

    if data_fim:
        query = query.filter(Caixa.data_abertura <= datetime.fromisoformat(data_fim))

    if status_filter:
        query = query.filter(Caixa.status == status_filter)

    caixas = query.order_by(Caixa.data_abertura.desc()).all()

    return [_serializar_caixa(caixa, compartilhado=compartilhado) for caixa in caixas]


@router.get("/{caixa_id}")
def obter_caixa(
    caixa_id: int,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Obter detalhes de um caixa específico"""
    current_user, tenant_id = current_user_and_tenant

    caixa, compartilhado = buscar_caixa_acessivel(
        db, caixa_id=caixa_id, tenant_id=tenant_id, usuario_id=current_user.id
    )

    if not caixa:
        raise HTTPException(status_code=404, detail="Caixa não encontrado")

    return _serializar_caixa(caixa, compartilhado=compartilhado)


@router.post("/{caixa_id}/movimentacao")
@idempotent()  # 🔒 IDEMPOTÊNCIA: evita movimentações duplicadas
async def criar_movimentacao(
    caixa_id: int,
    dados: MovimentacaoSchema,
    request: Request,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Adicionar movimentação ao caixa"""
    current_user, tenant_id = current_user_and_tenant

    caixa, _ = buscar_caixa_acessivel(
        db,
        caixa_id=caixa_id,
        tenant_id=tenant_id,
        usuario_id=current_user.id,
        bloquear_caixa=True,
    )

    if not caixa:
        raise HTTPException(status_code=404, detail="Caixa não encontrado")

    if caixa.status != "aberto":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Caixa não está aberto"
        )

    # Nome do usuário (fallback para email se nome não estiver preenchido)
    usuario_nome = (
        current_user.nome
        or getattr(current_user, "username", None)
        or current_user.email
    )

    # Criar movimentação
    movimentacao = MovimentacaoCaixa(
        caixa_id=caixa_id,
        tipo=dados.tipo,
        valor=dados.valor,
        forma_pagamento=dados.forma_pagamento,
        descricao=dados.descricao,
        categoria=dados.categoria,
        conta_origem_id=dados.conta_origem_id,
        conta_origem_nome=dados.conta_origem_nome,
        conta_destino_id=dados.conta_destino_id,
        conta_destino_nome=dados.conta_destino_nome,
        fornecedor_id=dados.fornecedor_id,
        fornecedor_nome=dados.fornecedor_nome,
        documento=dados.documento,
        usuario_id=current_user.id,
        usuario_nome=usuario_nome,
        tenant_id=tenant_id,
        data_movimento=now_brasilia(),
    )

    db.add(movimentacao)

    conta_pagar_gerada = None
    if dados.tipo == "despesa":
        hoje = date.today()
        descricao_cp = dados.descricao or dados.categoria or "Despesa lançada no caixa"
        dre_subcategoria_id = 2

        if dados.tipo_despesa_id is not None:
            tipo_despesa = (
                db.query(TipoDespesa)
                .filter(
                    TipoDespesa.id == dados.tipo_despesa_id,
                    TipoDespesa.tenant_id == tenant_id,
                    TipoDespesa.ativo.is_(True),
                )
                .first()
            )
            if not tipo_despesa:
                raise HTTPException(status_code=400, detail="Tipo de despesa inválido")
            dre_subcategoria_id = tipo_despesa.dre_subcategoria_id or 2

        conta_pagar_gerada = ContaPagar(
            descricao=descricao_cp,
            fornecedor_id=dados.fornecedor_id,
            tipo_despesa_id=dados.tipo_despesa_id,
            valor_original=dados.valor,
            valor_pago=dados.valor,
            valor_final=dados.valor,
            data_emissao=hoje,
            data_vencimento=hoje,
            data_pagamento=hoje,
            status="pago",
            dre_subcategoria_id=dre_subcategoria_id,
            canal="loja_fisica",
            documento=dados.documento,
            observacoes=f"Gerada automaticamente pelo PDV (Caixa #{caixa.numero_caixa})",
            user_id=current_user.id,
            tenant_id=tenant_id,
        )
        db.add(conta_pagar_gerada)

    db.commit()
    db.refresh(movimentacao)

    retorno = movimentacao.to_dict()
    if conta_pagar_gerada is not None:
        db.refresh(conta_pagar_gerada)
        atualizar_dre_por_lancamento(
            db=db,
            tenant_id=tenant_id,
            dre_subcategoria_id=conta_pagar_gerada.dre_subcategoria_id,
            canal=conta_pagar_gerada.canal,
            valor=conta_pagar_gerada.valor_original,
            data_lancamento=conta_pagar_gerada.data_pagamento,
            tipo_movimentacao="DESPESA",
        )
        db.commit()
        retorno["conta_pagar_id"] = conta_pagar_gerada.id
        retorno["conta_pagar_status"] = conta_pagar_gerada.status

    return retorno


@router.post("/{caixa_id}/fechar")
@idempotent()  # 🔒 IDEMPOTÊNCIA: evita fechamento duplicado de caixa
async def fechar_caixa(
    caixa_id: int,
    dados: FecharCaixaSchema,
    request: Request,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Fechar caixa"""
    current_user, tenant_id = current_user_and_tenant

    caixa, compartilhado = buscar_caixa_acessivel(
        db,
        caixa_id=caixa_id,
        tenant_id=tenant_id,
        usuario_id=current_user.id,
        bloquear_caixa=True,
    )

    if not caixa:
        raise HTTPException(status_code=404, detail="Caixa não encontrado")

    if caixa.status != "aberto":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Caixa já está fechado"
        )

    # Calcular valor esperado
    movimentacoes = (
        db.query(MovimentacaoCaixa)
        .filter(
            MovimentacaoCaixa.caixa_id == caixa_id,
            MovimentacaoCaixa.tenant_id == tenant_id,
        )
        .all()
    )

    valor_esperado = totais_dinheiro(caixa.valor_abertura, movimentacoes)["saldo_atual"]

    # Calcular diferença (registrada no banco para auditoria)
    diferenca = float(moeda(dados.valor_informado) - moeda(valor_esperado))

    # Atualizar caixa
    caixa.data_fechamento = now_brasilia()
    caixa.fechamento_em = datetime.now(timezone.utc)
    caixa.valor_esperado = valor_esperado
    caixa.valor_informado = dados.valor_informado
    caixa.diferenca = diferenca
    caixa.observacoes_fechamento = dados.observacoes_fechamento
    caixa.usuario_fechamento_id = current_user.id
    caixa.usuario_fechamento_nome = (
        current_user.nome
        or getattr(current_user, "username", None)
        or current_user.email
    )
    caixa.status = "fechado"

    registrar_evento_caixa(
        db,
        caixa_id=caixa.id,
        usuario=current_user,
        tenant_id=tenant_id,
        acao="caixa_fechado",
        novo=snapshot_caixa(db, caixa.id, current_user_and_tenant),
        motivo=dados.observacoes_fechamento,
    )

    db.commit()
    db.refresh(caixa)

    return _serializar_caixa(caixa, compartilhado=compartilhado)


@router.post("/{caixa_id}/reabrir")
def reabrir_caixa(
    caixa_id: int,
    dados: ReabrirCaixaSchema,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Reabrir um caixa fechado"""
    current_user, tenant_id = current_user_and_tenant
    if len(dados.motivo.strip()) < 10:
        raise HTTPException(
            400, "Descreva o motivo da reabertura com pelo menos 10 caracteres."
        )

    caixa_aberto, compartilhado = buscar_caixa_aberto(
        db,
        tenant_id=tenant_id,
        usuario_id=current_user.id,
        bloquear_config=True,
    )

    if caixa_aberto:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "A empresa já possui um caixa compartilhado aberto. Feche-o antes de reabrir outro."
                if compartilhado
                else "Você já possui um caixa aberto. Feche-o antes de reabrir outro."
            ),
        )

    caixa, _ = buscar_caixa_acessivel(
        db,
        caixa_id=caixa_id,
        tenant_id=tenant_id,
        usuario_id=current_user.id,
        bloquear_caixa=True,
    )

    if not caixa:
        raise HTTPException(status_code=404, detail="Caixa não encontrado")

    if caixa.status != "fechado":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Apenas caixas fechados podem ser reabertos",
        )

    registrar_evento_caixa(
        db,
        caixa_id=caixa.id,
        usuario=current_user,
        tenant_id=tenant_id,
        acao="caixa_reaberto",
        motivo=dados.motivo.strip(),
        anterior=snapshot_caixa(db, caixa.id, current_user_and_tenant),
        novo={"status": "aberto"},
    )
    # O fechamento completo foi preservado antes de iniciar outro ciclo.
    caixa.status = "aberto"
    caixa.data_fechamento = None
    caixa.fechamento_em = None
    caixa.valor_esperado = None
    caixa.valor_informado = None
    caixa.diferenca = None
    caixa.observacoes_fechamento = None
    caixa.usuario_fechamento_id = None
    caixa.usuario_fechamento_nome = None

    db.commit()
    db.refresh(caixa)

    return _serializar_caixa(caixa, compartilhado=compartilhado)


@router.get("/{caixa_id}/resumo")
def obter_resumo_caixa(
    caixa_id: int,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Obter resumo do caixa com totais"""
    current_user, tenant_id = current_user_and_tenant

    caixa, compartilhado = buscar_caixa_acessivel(
        db, caixa_id=caixa_id, tenant_id=tenant_id, usuario_id=current_user.id
    )

    if not caixa:
        raise HTTPException(status_code=404, detail="Caixa não encontrado")

    # Calcular totais
    movimentacoes = (
        db.query(MovimentacaoCaixa)
        .filter(
            MovimentacaoCaixa.caixa_id == caixa_id,
            MovimentacaoCaixa.tenant_id == tenant_id,
        )
        .all()
    )

    totais = totais_dinheiro(caixa.valor_abertura, movimentacoes)

    # Dinheiro deve vir dos mesmos lançamentos que compõem o saldo físico.
    # Uma venda pode ter mudado para pago_nf depois de receber o pagamento.
    from app.vendas_models import Venda, VendaPagamento
    from sqlalchemy import func

    entradas_dinheiro = [
        mov
        for mov in movimentacoes
        if mov.tipo == "venda"
        and str(mov.forma_pagamento or "").strip().casefold() == "dinheiro"
    ]

    data_da_venda = func.date(Venda.data_venda)
    pagamentos_query = (
        db.query(
            data_da_venda.label("data_venda"),
            VendaPagamento.forma_pagamento,
            func.count(VendaPagamento.id).label("quantidade"),
            func.sum(VendaPagamento.valor).label("total"),
        )
        .join(Venda, VendaPagamento.venda_id == Venda.id)
        .filter(
            filtro_pagamentos_caixa(caixa),
            Venda.tenant_id == tenant_id,
            VendaPagamento.tenant_id == tenant_id,
            func.lower(func.trim(VendaPagamento.forma_pagamento)) != "dinheiro",
        )
    )
    pagamentos_por_data = pagamentos_query.group_by(
        data_da_venda, VendaPagamento.forma_pagamento
    ).all()

    vendas_por_forma = {}
    recebimentos_por_data_venda = {}

    def somar_recebimento(data_venda, forma, quantidade, valor, tipo_contagem):
        data_chave = str(data_venda) if data_venda else "sem_venda"
        por_forma = recebimentos_por_data_venda.setdefault(data_chave, {})
        for destino in (vendas_por_forma, por_forma):
            item = destino.setdefault(
                forma, {"quantidade": 0, "total": 0.0, "tipo_contagem": tipo_contagem}
            )
            item["quantidade"] += int(quantidade)
            item["total"] = float(moeda(item["total"]) + moeda(valor))

    venda_ids_dinheiro = {mov.venda_id for mov in entradas_dinheiro if mov.venda_id}
    datas_vendas_dinheiro = (
        dict(
            db.query(Venda.id, Venda.data_venda)
            .filter(Venda.id.in_(venda_ids_dinheiro), Venda.tenant_id == tenant_id)
            .all()
        )
        if venda_ids_dinheiro
        else {}
    )
    for mov in entradas_dinheiro:
        data_venda = datas_vendas_dinheiro.get(mov.venda_id)
        somar_recebimento(
            data_venda.date().isoformat() if data_venda else None,
            "Dinheiro",
            1,
            mov.valor,
            "lançamento",
        )
    for data_venda, forma, quantidade, total in pagamentos_por_data:
        somar_recebimento(data_venda, forma, quantidade, total, "pagamento")

    total_vendido = (
        db.query(func.sum(Venda.total))
        .filter(
            Venda.caixa_id == caixa_id,
            Venda.tenant_id == tenant_id,
            Venda.status.in_(["finalizada", "baixa_parcial", "pago_nf"]),
        )
        .scalar()
    )
    indicadores = indicadores_vendas_recebimentos(total_vendido, vendas_por_forma)

    return {
        "caixa": _serializar_caixa(caixa, compartilhado=compartilhado),
        "totais": totais,
        "vendas_por_forma_pagamento": vendas_por_forma,
        "recebimentos_por_data_venda": recebimentos_por_data_venda,
        **indicadores,
    }


@router.get("/{caixa_id}/movimentacoes")
def listar_movimentacoes_caixa(
    caixa_id: int,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lista todas as movimentações de um caixa (extrato completo)"""
    current_user, tenant_id = current_user_and_tenant

    caixa, _ = buscar_caixa_acessivel(
        db, caixa_id=caixa_id, tenant_id=tenant_id, usuario_id=current_user.id
    )

    if not caixa:
        raise HTTPException(status_code=404, detail="Caixa não encontrado")

    # Buscar todas as movimentações ordenadas por data (mais recentes primeiro)
    movimentacoes = (
        db.query(MovimentacaoCaixa)
        .filter(
            MovimentacaoCaixa.caixa_id == caixa_id,
            MovimentacaoCaixa.tenant_id == tenant_id,
        )
        .order_by(MovimentacaoCaixa.data_movimento.desc())
        .all()
    )

    # Converter para dicionário com informações extras
    resultado = []
    for mov in movimentacoes:
        mov_dict = mov.to_dict()

        # Adicionar emoji e cor baseado no tipo
        if mov.tipo == "venda":
            mov_dict["emoji"] = "💰"
            mov_dict["cor"] = "green"
            mov_dict["natureza"] = "entrada"
        elif mov.tipo == "suprimento":
            mov_dict["emoji"] = "➕"
            mov_dict["cor"] = "blue"
            mov_dict["natureza"] = "entrada"
        elif mov.tipo == "sangria":
            mov_dict["emoji"] = "➖"
            mov_dict["cor"] = "orange"
            mov_dict["natureza"] = "saida"
        elif mov.tipo == "despesa":
            mov_dict["emoji"] = "💸"
            mov_dict["cor"] = "red"
            mov_dict["natureza"] = "saida"
        elif mov.tipo == "devolucao":
            mov_dict["emoji"] = "🔄"
            mov_dict["cor"] = "purple"
            mov_dict["natureza"] = "saida"
        elif mov.tipo == "transferencia":
            mov_dict["emoji"] = "🔁"
            mov_dict["cor"] = "gray"
            mov_dict["natureza"] = "saida"
        else:
            mov_dict["emoji"] = "📝"
            mov_dict["cor"] = "gray"
            mov_dict["natureza"] = "neutro"

        resultado.append(mov_dict)

    return {
        "caixa": {
            "id": caixa.id,
            "numero_caixa": caixa.numero_caixa,
            "usuario_nome": caixa.usuario_nome,
            "status": caixa.status,
            "valor_abertura": float(caixa.valor_abertura),
        },
        "movimentacoes": resultado,
        "total_movimentacoes": len(resultado),
    }


@router.get("/{caixa_id}/vendas")
def listar_vendas_caixa(
    caixa_id: int,
    forma_pagamento: str = None,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lista as vendas de um caixa, opcionalmente filtradas por forma de pagamento"""
    current_user, tenant_id = current_user_and_tenant

    caixa, _ = buscar_caixa_acessivel(
        db, caixa_id=caixa_id, tenant_id=tenant_id, usuario_id=current_user.id
    )
    if not caixa:
        raise HTTPException(status_code=404, detail="Caixa não encontrado")

    from app.vendas_models import Venda, VendaPagamento

    if forma_pagamento and forma_pagamento.strip().casefold() == "dinheiro":
        movimentos = (
            db.query(MovimentacaoCaixa)
            .filter(
                MovimentacaoCaixa.caixa_id == caixa_id,
                MovimentacaoCaixa.tenant_id == tenant_id,
                MovimentacaoCaixa.tipo == "venda",
                func.lower(func.trim(MovimentacaoCaixa.forma_pagamento)) == "dinheiro",
            )
            .order_by(MovimentacaoCaixa.data_movimento.desc())
            .all()
        )
        return [
            {
                "id": mov.id,
                "venda_id": mov.venda_id,
                "movimentacao_id": mov.id,
                "numero_venda": mov.venda.numero_venda if mov.venda else None,
                "cliente_nome": mov.venda.cliente.nome
                if mov.venda and mov.venda.cliente
                else "Consumidor",
                "total": float(mov.valor),
                "valor_nesta_forma": float(mov.valor),
                "hora_venda": mov.data_movimento.strftime("%H:%M")
                if mov.data_movimento
                else None,
                "data_venda": mov.venda.data_venda.date().isoformat()
                if mov.venda and mov.venda.data_venda
                else None,
                "data_recebimento": mov.data_movimento.isoformat(),
            }
            for mov in movimentos
        ]

    if not forma_pagamento:
        from sqlalchemy import or_

        pagamentos_caixa = (
            db.query(VendaPagamento)
            .join(Venda, VendaPagamento.venda_id == Venda.id)
            .filter(
                filtro_pagamentos_caixa(caixa),
                Venda.tenant_id == tenant_id,
                VendaPagamento.tenant_id == tenant_id,
                func.lower(func.trim(VendaPagamento.forma_pagamento)) != "dinheiro",
            )
            .all()
        )
        dinheiro_caixa = (
            db.query(MovimentacaoCaixa)
            .filter(
                MovimentacaoCaixa.caixa_id == caixa_id,
                MovimentacaoCaixa.tenant_id == tenant_id,
                MovimentacaoCaixa.tipo == "venda",
                func.lower(func.trim(MovimentacaoCaixa.forma_pagamento)) == "dinheiro",
            )
            .all()
        )
        recebimentos = {}
        for pagamento in pagamentos_caixa:
            recebimentos.setdefault(pagamento.venda_id, []).append(
                {
                    "id": pagamento.id,
                    "tipo": "pagamento",
                    "forma_pagamento": pagamento.forma_pagamento,
                    "valor": float(moeda(pagamento.valor)),
                    "data_recebimento": pagamento.data_pagamento.isoformat()
                    if pagamento.data_pagamento
                    else None,
                }
            )
        for movimento in dinheiro_caixa:
            if movimento.venda_id:
                recebimentos.setdefault(movimento.venda_id, []).append(
                    {
                        "id": movimento.id,
                        "tipo": "movimentacao",
                        "forma_pagamento": "Dinheiro",
                        "valor": float(moeda(movimento.valor)),
                        "data_recebimento": movimento.data_movimento.isoformat(),
                    }
                )
        vendas = (
            db.query(Venda)
            .filter(
                Venda.tenant_id == tenant_id,
                or_(Venda.caixa_id == caixa_id, Venda.id.in_(list(recebimentos))),
            )
            .order_by(Venda.data_venda.desc())
            .all()
        )
        return [
            {
                "id": venda.id,
                "venda_id": venda.id,
                "numero_venda": venda.numero_venda,
                "cliente_nome": venda.cliente.nome if venda.cliente else "Consumidor",
                "total": float(venda.total),
                "valor_nesta_forma": float(
                    sum(
                        (
                            moeda(item["valor"])
                            for item in recebimentos.get(venda.id, [])
                        ),
                        moeda(0),
                    )
                ),
                "data_venda": venda.data_venda.date().isoformat()
                if venda.data_venda
                else None,
                "status": venda.status,
                "caixa_origem_id": venda.caixa_id,
                "recebimentos": recebimentos.get(venda.id, []),
                "itens": [
                    {
                        "id": item.id,
                        "produto_nome": item.produto.nome
                        if item.produto
                        else item.servico_descricao,
                        "quantidade": float(item.quantidade),
                        "subtotal": float(item.subtotal),
                    }
                    for item in venda.itens
                ],
                "hora_venda": venda.data_venda.strftime("%H:%M")
                if venda.data_venda
                else None,
            }
            for venda in vendas
        ]

    # Consultar pagamentos diretamente evita DISTINCT em Venda, que contém coluna JSON
    # e causa erro 500 no PostgreSQL ao abrir o detalhe.
    pagamentos = (
        db.query(VendaPagamento)
        .join(Venda, VendaPagamento.venda_id == Venda.id)
        .filter(
            filtro_pagamentos_caixa(caixa),
            Venda.tenant_id == tenant_id,
            VendaPagamento.tenant_id == tenant_id,
            VendaPagamento.forma_pagamento == forma_pagamento,
        )
        .order_by(VendaPagamento.data_pagamento.desc())
        .all()
    )
    return [
        {
            "id": pagamento.id,
            "venda_id": pagamento.venda_id,
            "pagamento_id": pagamento.id,
            "numero_venda": pagamento.venda.numero_venda,
            "cliente_nome": pagamento.venda.cliente.nome
            if pagamento.venda.cliente
            else "Consumidor",
            "total": float(pagamento.venda.total),
            "valor_nesta_forma": float(pagamento.valor),
            "hora_venda": pagamento.data_pagamento.strftime("%H:%M")
            if pagamento.data_pagamento
            else None,
            "data_venda": pagamento.venda.data_venda.date().isoformat()
            if pagamento.venda.data_venda
            else None,
            "data_recebimento": pagamento.data_pagamento.isoformat()
            if pagamento.data_pagamento
            else None,
        }
        for pagamento in pagamentos
    ]


@router.get("/{caixa_id}/pdf")
def gerar_pdf_caixa(
    caixa_id: int,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Gera PDF do fechamento de caixa
    """
    current_user, tenant_id = current_user_and_tenant

    caixa, _ = buscar_caixa_acessivel(
        db, caixa_id=caixa_id, tenant_id=tenant_id, usuario_id=current_user.id
    )

    if not caixa:
        raise HTTPException(status_code=404, detail="Caixa não encontrado")

    # Buscar movimentações
    movimentacoes = (
        db.query(MovimentacaoCaixa)
        .filter_by(caixa_id=caixa_id, tenant_id=tenant_id)
        .order_by(MovimentacaoCaixa.created_at)
        .all()
    )

    resumo = obter_resumo_caixa(caixa_id, db, current_user_and_tenant)
    # Preparar dados do caixa
    caixa_data = {
        "numero_caixa": caixa.numero_caixa,
        "data_abertura": caixa.data_abertura,
        "data_fechamento": caixa.data_fechamento,
        "responsavel": caixa.usuario_nome,
        "status": caixa.status,
        "saldo_inicial": float(caixa.valor_abertura),
        "total_vendido": resumo["total_vendido"],
        "total_recebido": resumo["total_recebido"],
        "vendas_por_forma_pagamento": resumo["vendas_por_forma_pagamento"],
        "recebimentos_por_forma_pagamento": resumo["recebimentos_por_forma_pagamento"],
        "totais": resumo["totais"],
        "saldo_fechamento": float(caixa.valor_informado)
        if caixa.valor_informado is not None
        else None,
        "diferenca": float(caixa.diferenca) if caixa.diferenca is not None else None,
    }

    # Preparar dados das movimentações
    mov_list = []
    for mov in movimentacoes:
        mov_list.append(
            {
                "created_at": mov.data_movimento or mov.created_at,
                "tipo": mov.tipo,
                "descricao": mov.descricao,
                "forma_pagamento_nome": mov.forma_pagamento,
                "valor": float(mov.valor),
            }
        )

    # Gerar PDF
    pdf_buffer = gerar_pdf_fechamento_caixa(caixa_data, mov_list)

    # Retornar PDF
    filename = (
        f"Caixa_{caixa.numero_caixa}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    )

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
