from datetime import date
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import get_current_user_and_tenant
from app.banho_tosa_api.pacotes_helpers import (
    obter_pacote,
    query_creditos,
    validar_cliente_pet_credito,
    validar_nome_pacote_disponivel,
    validar_servico,
)
from app.banho_tosa_models import (
    BanhoTosaPacote,
    BanhoTosaPacoteCredito,
    BanhoTosaPacoteMovimento,
    BanhoTosaServico,
)
from app.banho_tosa_pacotes import (
    calcular_validade_pacote,
    consumir_credito_atendimento,
    estornar_consumo_atendimento,
)
from app.banho_tosa_pacotes_serializers import (
    serializar_credito,
    serializar_movimento,
    serializar_pacote,
)
from app.banho_tosa_schemas import (
    BanhoTosaPacoteConsumoInput,
    BanhoTosaPacoteConsumoResponse,
    BanhoTosaPacoteCreditoCreate,
    BanhoTosaPacoteCreditoResponse,
    BanhoTosaPacoteCreate,
    BanhoTosaPacoteEstornoInput,
    BanhoTosaPacoteResponse,
    BanhoTosaPacoteUpdate,
    BanhoTosaPacoteProrrogacaoInput,
    BanhoTosaPacoteEncerramentoInput,
    BanhoTosaPacoteMovimentoResponse,
)
from app.banho_tosa_pacotes import _obter_credito
from app.vendas_models import Venda
from app.vendas.service import VendaService
from app.db import get_session
from app.veterinario_core import _get_tenant


router = APIRouter()


@router.get("/pacotes", response_model=List[BanhoTosaPacoteResponse])
def listar_pacotes(
    ativos_only: bool = Query(False),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    query = (
        db.query(BanhoTosaPacote)
        .options(joinedload(BanhoTosaPacote.servico))
        .filter(BanhoTosaPacote.tenant_id == tenant_id)
    )
    if ativos_only:
        query = query.filter(BanhoTosaPacote.ativo.is_(True))
    return [
        serializar_pacote(item)
        for item in query.order_by(BanhoTosaPacote.nome.asc()).all()
    ]


@router.post("/pacotes", response_model=BanhoTosaPacoteResponse, status_code=201)
def criar_pacote(
    body: BanhoTosaPacoteCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    nome = body.nome.strip()
    validar_nome_pacote_disponivel(db, tenant_id, nome)
    validar_servico(db, tenant_id, body.servico_id)
    payload = body.model_dump()
    payload["servicos"] = _normalizar_servicos(
        db,
        tenant_id,
        payload.get("servicos"),
        body.servico_id,
        body.quantidade_creditos,
    )
    if not payload["servicos"]:
        raise HTTPException(
            status_code=422, detail="Informe os serviços e quantidades do pacote."
        )
    if payload["servicos"]:
        payload["quantidade_creditos"] = sum(
            Decimal(str(i["quantidade_creditos"])) for i in payload["servicos"]
        )
        payload["servico_id"] = (
            payload["servicos"][0]["servico_id"]
            if len(payload["servicos"]) == 1
            else None
        )
    pacote = BanhoTosaPacote(tenant_id=tenant_id, **payload)
    pacote.nome = nome
    db.add(pacote)
    db.commit()
    db.refresh(pacote)
    return serializar_pacote(pacote)


@router.delete("/pacotes/{pacote_id}")
def excluir_pacote(
    pacote_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    pacote = obter_pacote(db, tenant_id, pacote_id)
    if _pacote_tem_creditos(db, tenant_id, pacote_id):
        pacote.ativo = False
        db.commit()
        return {
            "deleted": False,
            "deactivated": True,
            "message": "Pacote possui creditos emitidos e foi desativado para preservar o historico.",
        }

    db.delete(pacote)
    db.commit()
    return {
        "deleted": True,
        "deactivated": False,
        "message": "Pacote excluido.",
    }


@router.patch("/pacotes/{pacote_id}", response_model=BanhoTosaPacoteResponse)
def atualizar_pacote(
    pacote_id: int,
    body: BanhoTosaPacoteUpdate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    pacote = obter_pacote(db, tenant_id, pacote_id)
    payload = body.model_dump(exclude_unset=True)
    if "nome" in payload:
        payload["nome"] = (payload["nome"] or "").strip()
        validar_nome_pacote_disponivel(
            db, tenant_id, payload["nome"], ignorar_id=pacote.id
        )
    if "servico_id" in payload:
        validar_servico(db, tenant_id, payload["servico_id"])
    if any(k in payload for k in ("servicos", "servico_id", "quantidade_creditos")):
        composicao = _normalizar_servicos(
            db,
            tenant_id,
            payload.get("servicos"),
            payload.get("servico_id", pacote.servico_id),
            payload.get("quantidade_creditos", pacote.quantidade_creditos),
        )
        if not composicao:
            raise HTTPException(
                status_code=422, detail="Informe os serviços e quantidades do pacote."
            )
        payload["servicos"] = composicao
        payload["quantidade_creditos"] = sum(
            Decimal(str(i["quantidade_creditos"])) for i in composicao
        )
        payload["servico_id"] = (
            composicao[0]["servico_id"] if len(composicao) == 1 else None
        )
    for campo, valor in payload.items():
        setattr(pacote, campo, valor)
    db.commit()
    db.refresh(pacote)
    return serializar_pacote(pacote)


@router.get("/pacotes/creditos", response_model=List[BanhoTosaPacoteCreditoResponse])
def listar_creditos(
    cliente_id: Optional[int] = Query(None),
    pet_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    disponiveis_only: bool = Query(False),
    data_referencia: Optional[date] = Query(None),
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    query = query_creditos(db, tenant_id)
    if cliente_id:
        query = query.filter(BanhoTosaPacoteCredito.cliente_id == cliente_id)
    if pet_id:
        query = query.filter(
            or_(
                BanhoTosaPacoteCredito.pet_id == pet_id,
                BanhoTosaPacoteCredito.pet_id.is_(None),
            )
        )
    if status:
        query = query.filter(BanhoTosaPacoteCredito.status == status)
    if disponiveis_only:
        referencia = data_referencia or date.today()
        query = query.filter(
            BanhoTosaPacoteCredito.status == "ativo",
            BanhoTosaPacoteCredito.data_validade >= referencia,
            BanhoTosaPacoteCredito.data_inicio <= referencia,
            BanhoTosaPacoteCredito.creditos_total
            > BanhoTosaPacoteCredito.creditos_usados
            + BanhoTosaPacoteCredito.creditos_cancelados
            + BanhoTosaPacoteCredito.creditos_reservados,
        )
    creditos = (
        query.order_by(BanhoTosaPacoteCredito.data_validade.asc()).limit(limit).all()
    )
    return [serializar_credito(item) for item in creditos]


def _pacote_tem_creditos(db: Session, tenant_id, pacote_id: int) -> bool:
    return (
        db.query(BanhoTosaPacoteCredito.id)
        .filter(
            BanhoTosaPacoteCredito.tenant_id == tenant_id,
            BanhoTosaPacoteCredito.pacote_id == pacote_id,
        )
        .first()
        is not None
    )


@router.post(
    "/pacotes/creditos", response_model=BanhoTosaPacoteCreditoResponse, status_code=201
)
def criar_credito(
    body: BanhoTosaPacoteCreditoCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    pacote = obter_pacote(db, tenant_id, body.pacote_id, ativo=True)
    validar_cliente_pet_credito(db, tenant_id, body.cliente_id, body.pet_id)
    if body.venda_id:
        _validar_venda(db, tenant_id, body.venda_id, body.cliente_id)
    servicos = _normalizar_servicos(
        db, tenant_id, pacote.servicos, pacote.servico_id, pacote.quantidade_creditos
    )
    if not servicos:
        raise HTTPException(
            status_code=422,
            detail="Defina os serviços cobertos antes de contratar este pacote.",
        )
    data_inicio = body.data_inicio or date.today()
    data_validade = body.data_validade or calcular_validade_pacote(
        data_inicio, pacote.validade_dias
    )
    if data_validade < data_inicio:
        raise HTTPException(
            status_code=422,
            detail="Validade do pacote nao pode ser anterior ao inicio.",
        )
    credito = BanhoTosaPacoteCredito(
        tenant_id=tenant_id,
        pacote_id=pacote.id,
        cliente_id=body.cliente_id,
        pet_id=body.pet_id,
        venda_id=body.venda_id,
        status="ativo",
        creditos_total=pacote.quantidade_creditos,
        servicos=servicos,
        valor_pacote=pacote.preco,
        data_inicio=data_inicio,
        data_validade=data_validade,
        observacoes=body.observacoes,
    )
    db.add(credito)
    db.commit()
    db.refresh(credito)
    credito = (
        query_creditos(db, tenant_id)
        .filter(BanhoTosaPacoteCredito.id == credito.id)
        .first()
    )
    return serializar_credito(credito)


def _normalizar_servicos(db, tenant_id, servicos, servico_id=None, quantidade=1):
    itens = (
        servicos
        if servicos is not None
        else (
            [{"servico_id": servico_id, "quantidade_creditos": quantidade}]
            if servico_id
            else []
        )
    )
    ids = set()
    saida = []
    for item in itens:
        sid = item["servico_id"]
        qtd = Decimal(str(item["quantidade_creditos"]))
        if sid in ids or qtd <= 0:
            raise HTTPException(
                status_code=422,
                detail="Informe cada serviço uma vez, com quantidade positiva.",
            )
        servico = (
            db.query(BanhoTosaServico)
            .filter(BanhoTosaServico.id == sid, BanhoTosaServico.tenant_id == tenant_id)
            .first()
        )
        if not servico:
            raise HTTPException(
                status_code=404, detail="Serviço do pacote não encontrado."
            )
        if not servico.ativo or not servico.permite_pacote:
            raise HTTPException(
                status_code=422,
                detail="Selecione um serviço ativo que permita uso em pacotes.",
            )
        ids.add(sid)
        saida.append(
            {
                "servico_id": sid,
                "servico_nome": servico.nome,
                "quantidade_creditos": float(qtd),
            }
        )
    return saida


def _validar_venda(db, tenant_id, venda_id, cliente_id):
    venda = (
        db.query(Venda)
        .filter(
            Venda.id == venda_id,
            Venda.tenant_id == tenant_id,
            Venda.cliente_id == cliente_id,
        )
        .first()
    )
    if not venda or venda.status == "cancelada":
        raise HTTPException(
            status_code=422,
            detail="Selecione uma venda válida deste tutor e desta empresa.",
        )
    return venda


@router.get(
    "/pacotes/creditos/{credito_id}/movimentos",
    response_model=List[BanhoTosaPacoteMovimentoResponse],
)
def listar_movimentos_credito(
    credito_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    credito = _obter_credito(db, tenant_id, credito_id)
    return [
        serializar_movimento(m) for m in sorted(credito.movimentos, key=lambda m: m.id)
    ]


@router.post(
    "/pacotes/creditos/{credito_id}/prorrogar",
    response_model=BanhoTosaPacoteCreditoResponse,
)
def prorrogar_credito(
    credito_id: int,
    body: BanhoTosaPacoteProrrogacaoInput,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    credito = _obter_credito(db, tenant_id, credito_id)
    motivo = body.motivo.strip()
    if len(motivo) < 3:
        raise HTTPException(status_code=422, detail="Informe o motivo da prorrogação.")
    if (
        credito.status == "encerrado"
        or body.data_validade <= credito.data_validade
        or body.data_validade < date.today()
    ):
        raise HTTPException(
            status_code=422,
            detail="Informe uma validade futura maior que a atual para um pacote não encerrado.",
        )
    anterior = credito.data_validade
    credito.data_validade = body.data_validade
    db.add(
        BanhoTosaPacoteMovimento(
            tenant_id=tenant_id,
            credito_id=credito.id,
            tipo="prorrogacao",
            quantidade=0,
            saldo_apos=max(
                Decimal(str(credito.creditos_total))
                - Decimal(str(credito.creditos_usados))
                - Decimal(str(credito.creditos_cancelados))
                - Decimal(str(credito.creditos_reservados)),
                Decimal("0"),
            ),
            created_by=getattr(user, "id", None),
            observacoes=f"Validade {anterior} → {body.data_validade}: {motivo}",
        )
    )
    db.commit()
    return serializar_credito(
        query_creditos(db, tenant_id)
        .filter(BanhoTosaPacoteCredito.id == credito.id)
        .first()
    )


@router.post(
    "/pacotes/creditos/{credito_id}/encerrar",
    response_model=BanhoTosaPacoteCreditoResponse,
)
def encerrar_credito(
    credito_id: int,
    body: BanhoTosaPacoteEncerramentoInput,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    credito = _obter_credito(db, tenant_id, credito_id)
    motivo = body.motivo.strip()
    if len(motivo) < 3:
        raise HTTPException(status_code=422, detail="Informe o motivo do encerramento.")
    if credito.status == "encerrado":
        return serializar_credito(credito)
    if credito.creditos_reservados > 0:
        raise HTTPException(
            status_code=409,
            detail="Cancele os agendamentos reservados antes de encerrar o saldo.",
        )
    saldo = max(
        credito.creditos_total - credito.creditos_usados - credito.creditos_cancelados,
        Decimal("0"),
    )
    credito.creditos_cancelados += saldo
    credito.status = "encerrado"
    db.add(
        BanhoTosaPacoteMovimento(
            tenant_id=tenant_id,
            credito_id=credito.id,
            tipo="encerramento",
            quantidade=saldo,
            saldo_apos=0,
            created_by=getattr(user, "id", None),
            observacoes=motivo,
        )
    )
    db.commit()
    return serializar_credito(
        query_creditos(db, tenant_id)
        .filter(BanhoTosaPacoteCredito.id == credito.id)
        .first()
    )


@router.post("/pacotes/creditos/{credito_id}/gerar-venda")
def gerar_venda_credito(
    credito_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    credito = _obter_credito(db, tenant_id, credito_id)
    token = f"BT_PACOTE:{credito.id}|"
    venda = (
        db.query(Venda)
        .filter(Venda.tenant_id == tenant_id, Venda.id == credito.venda_id)
        .first()
        if credito.venda_id
        else None
    )
    if not venda:
        venda = (
            db.query(Venda)
            .filter(
                Venda.tenant_id == tenant_id,
                Venda.observacoes.contains(token),
                Venda.status != "cancelada",
            )
            .first()
        )
    ja_existia = bool(venda)
    if venda and venda.status == "cancelada":
        raise HTTPException(
            status_code=422,
            detail="A cobrança vinculada foi cancelada. Revise o histórico financeiro antes de gerar outra.",
        )
    if not venda:
        if credito.valor_pacote <= 0:
            raise HTTPException(
                status_code=422, detail="Pacote sem valor para cobrança no PDV."
            )
        valor = float(credito.valor_pacote)
        resultado = VendaService.criar_venda(
            payload={
                "cliente_id": credito.cliente_id,
                "vendedor_id": user.id,
                "itens": [
                    {
                        "tipo": "servico",
                        "servico_descricao": f"Pacote {credito.pacote.nome} - {credito.pet.nome}",
                        "quantidade": 1,
                        "preco_unitario": valor,
                        "desconto_item": 0,
                        "subtotal": valor,
                        "pet_id": credito.pet_id,
                    }
                ],
                "desconto_valor": 0,
                "desconto_percentual": 0,
                "observacoes": f"{token} Pacote contratado para o pet #{credito.pet_id}.",
                "tem_entrega": False,
                "taxa_entrega": 0,
                "canal": "banho_tosa",
                "tenant_id": tenant_id,
            },
            user_id=user.id,
            db=db,
        )
        venda = (
            db.query(Venda)
            .filter(Venda.id == resultado["id"], Venda.tenant_id == tenant_id)
            .one()
        )
    credito.venda_id = venda.id
    db.commit()
    return {
        "venda_id": venda.id,
        "numero_venda": venda.numero_venda,
        "pdv_url": f"/pdv?venda_id={venda.id}",
        "ja_existia": ja_existia,
    }


@router.post(
    "/pacotes/creditos/{credito_id}/consumir",
    response_model=BanhoTosaPacoteConsumoResponse,
)
def consumir_credito(
    credito_id: int,
    body: BanhoTosaPacoteConsumoInput,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = _get_tenant(current)
    credito, movimento, ja_existia = consumir_credito_atendimento(
        db,
        tenant_id,
        credito_id,
        body.atendimento_id,
        body.quantidade,
        user_id=getattr(current_user, "id", None),
        observacoes=body.observacoes,
    )
    credito = (
        query_creditos(db, tenant_id)
        .filter(BanhoTosaPacoteCredito.id == credito.id)
        .first()
    )
    return {
        "credito": serializar_credito(credito),
        "movimento": serializar_movimento(movimento),
        "ja_existia": ja_existia,
    }


@router.post(
    "/pacotes/creditos/{credito_id}/estornar",
    response_model=BanhoTosaPacoteConsumoResponse,
)
def estornar_credito(
    credito_id: int,
    body: BanhoTosaPacoteEstornoInput,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = _get_tenant(current)
    credito, movimento, ja_existia = estornar_consumo_atendimento(
        db,
        tenant_id,
        credito_id,
        atendimento_id=body.atendimento_id,
        movimento_id=body.movimento_id,
        user_id=getattr(current_user, "id", None),
        observacoes=body.observacoes,
    )
    credito = (
        query_creditos(db, tenant_id)
        .filter(BanhoTosaPacoteCredito.id == credito.id)
        .first()
    )
    return {
        "credito": serializar_credito(credito),
        "movimento": serializar_movimento(movimento),
        "ja_existia": ja_existia,
    }
