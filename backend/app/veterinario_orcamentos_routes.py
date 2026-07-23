"""Rotas de orcamentos veterinarios."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from .auth.dependencies import get_current_user_and_tenant
from .db import get_session
from .models import Cliente, Pet
from .produtos_models import Produto
from .veterinario_core import _get_tenant
from .veterinario_internacao import _garantir_internacao_ativa
from .veterinario_models import (
    CatalogoProcedimento,
    ConsultaVet,
    InternacaoVet,
    OrcamentoVet,
    OrcamentoVetItem,
)
from .veterinario_orcamentos import (
    calcular_totais_orcamento,
    montar_item_orcamento_catalogo,
    montar_item_orcamento_manual,
    montar_item_orcamento_produto,
    serializar_orcamento,
)
from .veterinario_schemas import OrcamentoCreate, OrcamentoResponse, OrcamentoUpdate

router = APIRouter()


def _orcamento_or_404(db: Session, tenant_id, orcamento_id: int) -> OrcamentoVet:
    orcamento = (
        db.query(OrcamentoVet)
        .options(joinedload(OrcamentoVet.itens))
        .filter(OrcamentoVet.id == orcamento_id, OrcamentoVet.tenant_id == tenant_id)
        .first()
    )
    if not orcamento:
        raise HTTPException(
            status_code=404, detail="Orcamento veterinario nao encontrado"
        )
    return orcamento


def _consulta_or_none(
    db: Session, tenant_id, consulta_id: Optional[int]
) -> Optional[ConsultaVet]:
    if not consulta_id:
        return None
    consulta = (
        db.query(ConsultaVet)
        .filter(
            ConsultaVet.id == consulta_id,
            ConsultaVet.tenant_id == tenant_id,
        )
        .first()
    )
    if not consulta:
        raise HTTPException(
            status_code=404, detail="Consulta nao encontrada para o orcamento"
        )
    return consulta


def _internacao_or_none(
    db: Session, tenant_id, internacao_id: Optional[int]
) -> Optional[InternacaoVet]:
    if not internacao_id:
        return None
    internacao = (
        db.query(InternacaoVet)
        .filter(
            InternacaoVet.id == internacao_id,
            InternacaoVet.tenant_id == tenant_id,
        )
        .first()
    )
    if not internacao:
        raise HTTPException(
            status_code=404, detail="Internacao nao encontrada para o orcamento"
        )
    _garantir_internacao_ativa(internacao, "alterar orçamento")
    return internacao


def _validar_pet_cliente(
    db: Session, tenant_id, pet_id: Optional[int], cliente_id: Optional[int]
) -> None:
    if pet_id:
        pet = (
            db.query(Pet)
            .join(Cliente)
            .filter(
                Pet.id == pet_id,
                Cliente.tenant_id == tenant_id,
            )
            .first()
        )
        if not pet:
            raise HTTPException(
                status_code=404, detail="Pet nao encontrado para o orcamento"
            )

    if cliente_id:
        cliente = (
            db.query(Cliente)
            .filter(
                Cliente.id == cliente_id,
                Cliente.tenant_id == tenant_id,
            )
            .first()
        )
        if not cliente:
            raise HTTPException(
                status_code=404, detail="Cliente nao encontrado para o orcamento"
            )


def _resolver_vinculos(db: Session, tenant_id, payload: dict) -> dict:
    consulta = _consulta_or_none(db, tenant_id, payload.get("consulta_id"))
    internacao = _internacao_or_none(db, tenant_id, payload.get("internacao_id"))

    pet_id = payload.get("pet_id")
    cliente_id = payload.get("cliente_id")
    veterinario_id = payload.get("veterinario_id")

    if consulta:
        pet_id = pet_id or consulta.pet_id
        cliente_id = cliente_id or consulta.cliente_id
        veterinario_id = veterinario_id or consulta.veterinario_id

    if internacao:
        pet_id = pet_id or internacao.pet_id
        veterinario_id = veterinario_id or internacao.veterinario_id
        if not cliente_id and internacao.pet:
            cliente_id = getattr(internacao.pet, "cliente_id", None)

    _validar_pet_cliente(db, tenant_id, pet_id, cliente_id)

    if veterinario_id:
        veterinario = (
            db.query(Cliente)
            .filter(
                Cliente.id == veterinario_id,
                Cliente.tenant_id == tenant_id,
            )
            .first()
        )
        if not veterinario:
            raise HTTPException(
                status_code=404, detail="Veterinario nao encontrado para o orcamento"
            )

    return {
        "consulta_id": payload.get("consulta_id"),
        "internacao_id": payload.get("internacao_id"),
        "pet_id": pet_id,
        "cliente_id": cliente_id,
        "veterinario_id": veterinario_id,
    }


def _payload_item(item) -> dict:
    if hasattr(item, "model_dump"):
        return item.model_dump()
    return dict(item or {})


def _coletar_referencias(itens: list[dict]) -> tuple[set[int], set[int]]:
    catalogo_ids = {
        int(item["catalogo_id"]) for item in itens if item.get("catalogo_id")
    }
    produto_ids = {int(item["produto_id"]) for item in itens if item.get("produto_id")}
    for item in itens:
        for insumo in item.get("insumos") or []:
            if isinstance(insumo, dict) and insumo.get("produto_id"):
                produto_ids.add(int(insumo["produto_id"]))
    return catalogo_ids, produto_ids


def _buscar_catalogos(
    db: Session, tenant_id, catalogo_ids: set[int]
) -> dict[int, CatalogoProcedimento]:
    if not catalogo_ids:
        return {}
    catalogos = (
        db.query(CatalogoProcedimento)
        .filter(
            CatalogoProcedimento.tenant_id == tenant_id,
            CatalogoProcedimento.id.in_(catalogo_ids),
            CatalogoProcedimento.ativo.is_(True),
        )
        .all()
    )
    return {catalogo.id: catalogo for catalogo in catalogos}


def _buscar_produtos(
    db: Session, tenant_id, produto_ids: set[int]
) -> dict[int, Produto]:
    if not produto_ids:
        return {}
    produtos = (
        db.query(Produto)
        .filter(
            Produto.tenant_id == str(tenant_id),
            Produto.id.in_(produto_ids),
        )
        .all()
    )
    return {produto.id: produto for produto in produtos}


def _normalizar_itens_orcamento(db: Session, tenant_id, itens_raw) -> list[dict]:
    itens_payload = [_payload_item(item) for item in (itens_raw or [])]
    catalogo_ids, produto_ids = _coletar_referencias(itens_payload)
    catalogos = _buscar_catalogos(db, tenant_id, catalogo_ids)
    produtos = _buscar_produtos(db, tenant_id, produto_ids)

    itens = []
    for item in itens_payload:
        catalogo_id = item.get("catalogo_id")
        produto_id = item.get("produto_id")

        if catalogo_id:
            catalogo = catalogos.get(int(catalogo_id))
            if not catalogo:
                raise HTTPException(
                    status_code=404,
                    detail=f"Procedimento {catalogo_id} nao encontrado para o orcamento",
                )
            itens.append(
                montar_item_orcamento_catalogo(
                    catalogo,
                    produtos,
                    quantidade=item.get("quantidade", 1),
                    preco_unitario=item.get("preco_unitario"),
                    observacoes=item.get("observacoes"),
                )
            )
            continue

        if produto_id:
            produto = produtos.get(int(produto_id))
            if not produto:
                raise HTTPException(
                    status_code=404,
                    detail=f"Produto {produto_id} nao encontrado para o orcamento",
                )
            itens.append(
                montar_item_orcamento_produto(
                    produto,
                    quantidade=item.get("quantidade", 1),
                    preco_unitario=item.get("preco_unitario"),
                    observacoes=item.get("observacoes"),
                )
            )
            continue

        itens.append(montar_item_orcamento_manual(item))

    return itens


def _substituir_itens(
    db: Session, orcamento: OrcamentoVet, tenant_id, itens_payload: list[dict]
) -> None:
    for item_existente in list(orcamento.itens or []):
        db.delete(item_existente)
    db.flush()

    for ordem, item in enumerate(itens_payload, start=1):
        db.add(
            OrcamentoVetItem(
                tenant_id=tenant_id,
                orcamento_id=orcamento.id,
                origem=item["origem"],
                ordem=ordem,
                catalogo_id=item.get("catalogo_id"),
                produto_id=item.get("produto_id"),
                nome=item["nome"],
                descricao=item.get("descricao"),
                unidade=item.get("unidade"),
                quantidade=item["quantidade"],
                custo_unitario_estimado=item["custo_unitario_estimado"],
                preco_unitario_sugerido=item["preco_unitario_sugerido"],
                preco_unitario=item["preco_unitario"],
                custo_total_estimado=item["custo_total_estimado"],
                preco_total=item["preco_total"],
                margem_valor=item["margem_valor"],
                margem_percentual=item["margem_percentual"],
                insumos=item.get("insumos") or [],
                observacoes=item.get("observacoes"),
            )
        )

    totais = calcular_totais_orcamento(itens_payload)
    orcamento.custo_total_estimado = totais["custo_total_estimado"]
    orcamento.preco_total = totais["preco_total"]
    orcamento.margem_valor = totais["margem_valor"]
    orcamento.margem_percentual = totais["margem_percentual"]


@router.get("/orcamentos", response_model=list[OrcamentoResponse])
def listar_orcamentos(
    consulta_id: Optional[int] = Query(None),
    internacao_id: Optional[int] = Query(None),
    pet_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    query = (
        db.query(OrcamentoVet)
        .options(joinedload(OrcamentoVet.itens))
        .filter(OrcamentoVet.tenant_id == tenant_id)
    )
    if consulta_id:
        query = query.filter(OrcamentoVet.consulta_id == consulta_id)
    if internacao_id:
        query = query.filter(OrcamentoVet.internacao_id == internacao_id)
    if pet_id:
        query = query.filter(OrcamentoVet.pet_id == pet_id)
    if status:
        query = query.filter(OrcamentoVet.status == status)

    orcamentos = query.order_by(OrcamentoVet.created_at.desc()).limit(100).all()
    return [serializar_orcamento(orcamento) for orcamento in orcamentos]


@router.post("/orcamentos", response_model=OrcamentoResponse, status_code=201)
def criar_orcamento(
    body: OrcamentoCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    payload = body.model_dump()
    vinculos = _resolver_vinculos(db, tenant_id, payload)
    itens = _normalizar_itens_orcamento(db, tenant_id, body.itens)

    orcamento = OrcamentoVet(
        tenant_id=tenant_id,
        user_id=user.id,
        **vinculos,
        titulo=(body.titulo or "").strip() or "Orcamento veterinario",
        status=(body.status or "rascunho").strip().lower(),
        previsao_dias_internacao=body.previsao_dias_internacao,
        observacoes=body.observacoes,
    )
    db.add(orcamento)
    db.flush()
    _substituir_itens(db, orcamento, tenant_id, itens)
    db.commit()
    db.refresh(orcamento)
    return serializar_orcamento(_orcamento_or_404(db, tenant_id, orcamento.id))


@router.get("/orcamentos/{orcamento_id}", response_model=OrcamentoResponse)
def obter_orcamento(
    orcamento_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    return serializar_orcamento(_orcamento_or_404(db, tenant_id, orcamento_id))


@router.patch("/orcamentos/{orcamento_id}", response_model=OrcamentoResponse)
def atualizar_orcamento(
    orcamento_id: int,
    body: OrcamentoUpdate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    orcamento = _orcamento_or_404(db, tenant_id, orcamento_id)
    _internacao_or_none(db, tenant_id, orcamento.internacao_id)
    payload = body.model_dump(exclude_unset=True)

    if any(
        campo in payload
        for campo in {
            "consulta_id",
            "internacao_id",
            "pet_id",
            "cliente_id",
            "veterinario_id",
        }
    ):
        vinculos_payload = {
            "consulta_id": payload.get("consulta_id", orcamento.consulta_id),
            "internacao_id": payload.get("internacao_id", orcamento.internacao_id),
            "pet_id": payload.get("pet_id", orcamento.pet_id),
            "cliente_id": payload.get("cliente_id", orcamento.cliente_id),
            "veterinario_id": payload.get("veterinario_id", orcamento.veterinario_id),
        }
        for campo, valor in _resolver_vinculos(db, tenant_id, vinculos_payload).items():
            setattr(orcamento, campo, valor)

    for campo in ("titulo", "status", "previsao_dias_internacao", "observacoes"):
        if campo in payload:
            valor = payload[campo]
            if campo in {"titulo", "status"} and isinstance(valor, str):
                valor = valor.strip()
            if campo == "titulo" and not valor:
                valor = "Orcamento veterinario"
            if campo == "status" and not valor:
                valor = "rascunho"
            setattr(orcamento, campo, valor)

    if "itens" in payload:
        itens = _normalizar_itens_orcamento(db, tenant_id, body.itens or [])
        _substituir_itens(db, orcamento, tenant_id, itens)

    db.commit()
    return serializar_orcamento(_orcamento_or_404(db, tenant_id, orcamento.id))
