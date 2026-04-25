"""Rotas de procedimentos, catalogos e apoio clinico veterinario."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import or_
from sqlalchemy.orm import Session

from .auth.dependencies import get_current_user_and_tenant
from .db import get_session
from .produtos_models import Produto
from .veterinario_clinico import (
    _bloquear_lancamento_em_consulta_finalizada,
    _consulta_or_404,
    _montar_alertas_pet,
    _pet_or_404,
    _status_vacinal_pet,
)
from .veterinario_core import _get_tenant
from .veterinario_financeiro import (
    _aplicar_baixa_estoque_procedimento,
    _enriquecer_insumos_com_custos,
    _normalizar_insumos,
    _round_money,
    _serializar_catalogo,
    _serializar_procedimento,
    _sincronizar_financeiro_procedimento,
)
from .veterinario_models import (
    CatalogoProcedimento,
    ConsultaVet,
    ExameVet,
    MedicamentoCatalogo,
    ProcedimentoConsulta,
    ProtocoloVacina,
)
from .veterinario_schemas import (
    CatalogoCreate,
    CatalogoResponse,
    CatalogoUpdate,
    MedicamentoCreate,
    MedicamentoUpdate,
    ProcedimentoCreate,
    ProcedimentoResponse,
    ProtocoloVacinaUpdate,
)

router = APIRouter()


@router.get("/consultas/{consulta_id}/procedimentos", response_model=List[ProcedimentoResponse])
def listar_procedimentos_consulta(
    consulta_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    procedimentos = db.query(ProcedimentoConsulta).filter(
        ProcedimentoConsulta.consulta_id == consulta_id,
        ProcedimentoConsulta.tenant_id == tenant_id,
    ).order_by(ProcedimentoConsulta.created_at.desc()).all()
    return [_serializar_procedimento(procedimento, db, tenant_id) for procedimento in procedimentos]


@router.post("/procedimentos", response_model=ProcedimentoResponse, status_code=201)
def adicionar_procedimento(
    body: ProcedimentoCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    consulta = _consulta_or_404(db, body.consulta_id, tenant_id)
    _bloquear_lancamento_em_consulta_finalizada(consulta, "novo procedimento vinculado")

    catalogo = None
    if body.catalogo_id:
        catalogo = db.query(CatalogoProcedimento).filter(
            CatalogoProcedimento.id == body.catalogo_id,
            CatalogoProcedimento.tenant_id == tenant_id,
        ).first()
        if not catalogo:
            raise HTTPException(status_code=404, detail="Procedimento de catálogo não encontrado")

    insumos = _normalizar_insumos(body.insumos or [])
    if not insumos and catalogo and isinstance(catalogo.insumos, list):
        insumos = _normalizar_insumos(catalogo.insumos)
    insumos = _enriquecer_insumos_com_custos(db, tenant_id, insumos)

    p = ProcedimentoConsulta(
        tenant_id=tenant_id,
        consulta_id=body.consulta_id,
        catalogo_id=body.catalogo_id,
        user_id=user.id,
        nome=body.nome or (catalogo.nome if catalogo else "Procedimento"),
        descricao=body.descricao if body.descricao is not None else (catalogo.descricao if catalogo else None),
        valor=body.valor if body.valor is not None else (float(catalogo.valor_padrao) if catalogo and catalogo.valor_padrao is not None else None),
        realizado=body.realizado,
        observacoes=body.observacoes,
        insumos=insumos,
    )
    db.add(p)
    db.flush()
    if body.baixar_estoque:
        _aplicar_baixa_estoque_procedimento(db, p, tenant_id, user.id)
    _sincronizar_financeiro_procedimento(db, p, tenant_id, user.id)
    db.commit()
    db.refresh(p)
    return _serializar_procedimento(p, db, tenant_id)


@router.get("/catalogo/procedimentos", response_model=List[CatalogoResponse])
def listar_catalogo_procedimentos(
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    catalogos = db.query(CatalogoProcedimento).filter(
        CatalogoProcedimento.tenant_id == tenant_id,
        CatalogoProcedimento.ativo == True,  # noqa
    ).order_by(CatalogoProcedimento.nome).all()
    return [_serializar_catalogo(catalogo, db, tenant_id) for catalogo in catalogos]


@router.post("/catalogo/procedimentos", response_model=CatalogoResponse, status_code=201)
def criar_catalogo_procedimento(
    body: CatalogoCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    p = CatalogoProcedimento(
        tenant_id=tenant_id,
        nome=body.nome,
        descricao=body.descricao,
        categoria=body.categoria,
        valor_padrao=body.valor_padrao,
        duracao_minutos=body.duracao_minutos,
        requer_anestesia=body.requer_anestesia,
        observacoes=body.observacoes,
        insumos=_normalizar_insumos(body.insumos),
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return _serializar_catalogo(p, db, tenant_id)


@router.patch("/catalogo/procedimentos/{catalogo_id}", response_model=CatalogoResponse)
def atualizar_catalogo_procedimento(
    catalogo_id: int,
    body: CatalogoUpdate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    catalogo = db.query(CatalogoProcedimento).filter(
        CatalogoProcedimento.id == catalogo_id,
        CatalogoProcedimento.tenant_id == tenant_id,
        CatalogoProcedimento.ativo == True,  # noqa
    ).first()
    if not catalogo:
        raise HTTPException(404, "Procedimento de catálogo não encontrado")

    payload = body.model_dump(exclude_unset=True)
    if "insumos" in payload:
        catalogo.insumos = _normalizar_insumos(payload.pop("insumos"))
    for campo, valor in payload.items():
        setattr(catalogo, campo, valor)

    db.commit()
    db.refresh(catalogo)
    return _serializar_catalogo(catalogo, db, tenant_id)


@router.delete("/catalogo/procedimentos/{catalogo_id}", status_code=204)
def remover_catalogo_procedimento(
    catalogo_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    catalogo = db.query(CatalogoProcedimento).filter(
        CatalogoProcedimento.id == catalogo_id,
        CatalogoProcedimento.tenant_id == tenant_id,
        CatalogoProcedimento.ativo == True,  # noqa
    ).first()
    if not catalogo:
        raise HTTPException(404, "Procedimento de catálogo não encontrado")

    catalogo.ativo = False
    db.commit()
    return Response(status_code=204)


@router.get("/catalogo/produtos-estoque")
def listar_produtos_estoque(
    busca: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    q = db.query(Produto).filter(
        Produto.tenant_id == str(tenant_id),
        Produto.ativo == True,
        Produto.situacao == True,
    )
    if busca:
        termo = f"%{busca}%"
        q = q.filter(or_(Produto.nome.ilike(termo), Produto.codigo.ilike(termo)))
    produtos = q.order_by(Produto.nome).limit(limit).all()
    return [
        {
            "id": produto.id,
            "codigo": produto.codigo,
            "nome": produto.nome,
            "unidade": produto.unidade,
            "estoque_atual": float(produto.estoque_atual or 0),
            "preco_custo": _round_money(produto.preco_custo),
        }
        for produto in produtos
    ]


@router.get("/pets/{pet_id}/alertas")
def listar_alertas_pet(
    pet_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    pet = _pet_or_404(db, pet_id, tenant_id)
    return {
        "pet_id": pet.id,
        "alertas": _montar_alertas_pet(db, pet, tenant_id),
        "status_vacinal": _status_vacinal_pet(db, pet, tenant_id),
    }


@router.get("/pets/{pet_id}/carteirinha")
def obter_carteirinha_pet(
    pet_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    pet = _pet_or_404(db, pet_id, tenant_id)
    status_vacinal = _status_vacinal_pet(db, pet, tenant_id)
    exames = db.query(ExameVet).filter(
        ExameVet.pet_id == pet.id,
        ExameVet.tenant_id == tenant_id,
    ).order_by(ExameVet.created_at.desc()).limit(10).all()
    consultas = db.query(ConsultaVet).filter(
        ConsultaVet.pet_id == pet.id,
        ConsultaVet.tenant_id == tenant_id,
    ).order_by(ConsultaVet.created_at.desc()).limit(10).all()

    return {
        "pet": {
            "id": pet.id,
            "nome": pet.nome,
            "especie": pet.especie,
            "raca": pet.raca,
            "peso": float(pet.peso) if pet.peso is not None else None,
            "foto_url": pet.foto_url,
            "tipo_sanguineo": getattr(pet, "tipo_sanguineo", None),
            "alergias": getattr(pet, "alergias_lista", None) or ([pet.alergias] if pet.alergias else []),
            "restricoes_alimentares": getattr(pet, "restricoes_alimentares_lista", None) or [],
            "medicamentos_continuos": getattr(pet, "medicamentos_continuos_lista", None) or [],
            "condicoes_cronicas": getattr(pet, "condicoes_cronicas_lista", None) or [],
        },
        "alertas": _montar_alertas_pet(db, pet, tenant_id),
        "status_vacinal": status_vacinal,
        "consultas": [
            {
                "id": consulta.id,
                "data": consulta.created_at.date().isoformat() if consulta.created_at else None,
                "tipo": consulta.tipo,
                "status": consulta.status,
                "diagnostico": consulta.diagnostico,
                "observacoes_tutor": consulta.observacoes_tutor,
            }
            for consulta in consultas
        ],
        "exames": [
            {
                "id": exame.id,
                "nome": exame.nome,
                "tipo": exame.tipo,
                "status": exame.status,
                "data_resultado": exame.data_resultado.isoformat() if exame.data_resultado else None,
                "interpretacao_ia_resumo": exame.interpretacao_ia_resumo,
                "arquivo_url": exame.arquivo_url,
            }
            for exame in exames
        ],
    }


@router.get("/catalogo/medicamentos")
def listar_medicamentos(
    busca: Optional[str] = None,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    q = db.query(MedicamentoCatalogo).filter(
        MedicamentoCatalogo.tenant_id == tenant_id,
        MedicamentoCatalogo.ativo == True,  # noqa
    )
    if busca:
        termo = f"%{busca}%"
        q = q.filter(
            or_(
                MedicamentoCatalogo.nome.ilike(termo),
                MedicamentoCatalogo.principio_ativo.ilike(termo),
                MedicamentoCatalogo.nome_comercial.ilike(termo),
            )
        )
    return q.order_by(MedicamentoCatalogo.nome).limit(50).all()


@router.post("/catalogo/medicamentos", status_code=201)
def criar_medicamento(
    body: MedicamentoCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    m = MedicamentoCatalogo(tenant_id=tenant_id, **body.model_dump())
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


@router.patch("/catalogo/medicamentos/{medicamento_id}")
def atualizar_medicamento(
    medicamento_id: int,
    body: MedicamentoUpdate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    medicamento = db.query(MedicamentoCatalogo).filter(
        MedicamentoCatalogo.id == medicamento_id,
        MedicamentoCatalogo.tenant_id == tenant_id,
        MedicamentoCatalogo.ativo == True,  # noqa
    ).first()
    if not medicamento:
        raise HTTPException(404, "Medicamento não encontrado")

    for campo, valor in body.model_dump(exclude_unset=True).items():
        setattr(medicamento, campo, valor)

    db.commit()
    db.refresh(medicamento)
    return medicamento


@router.delete("/catalogo/medicamentos/{medicamento_id}", status_code=204)
def remover_medicamento(
    medicamento_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    medicamento = db.query(MedicamentoCatalogo).filter(
        MedicamentoCatalogo.id == medicamento_id,
        MedicamentoCatalogo.tenant_id == tenant_id,
        MedicamentoCatalogo.ativo == True,  # noqa
    ).first()
    if not medicamento:
        raise HTTPException(404, "Medicamento não encontrado")

    medicamento.ativo = False
    db.commit()
    return Response(status_code=204)


@router.get("/catalogo/protocolos-vacinas")
def listar_protocolos_vacinas(
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    return db.query(ProtocoloVacina).filter(
        ProtocoloVacina.tenant_id == tenant_id,
        ProtocoloVacina.ativo == True,  # noqa
    ).order_by(ProtocoloVacina.nome).all()


@router.post("/catalogo/protocolos-vacinas", status_code=201)
def criar_protocolo_vacina(
    nome: str,
    especie: Optional[str] = None,
    dose_inicial_semanas: Optional[int] = None,
    reforco_anual: bool = True,
    numero_doses_serie: int = 1,
    intervalo_doses_dias: Optional[int] = None,
    observacoes: Optional[str] = None,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    p = ProtocoloVacina(
        tenant_id=tenant_id,
        nome=nome,
        especie=especie,
        dose_inicial_semanas=dose_inicial_semanas,
        reforco_anual=reforco_anual,
        numero_doses_serie=numero_doses_serie,
        intervalo_doses_dias=intervalo_doses_dias,
        observacoes=observacoes,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@router.patch("/catalogo/protocolos-vacinas/{protocolo_id}")
def atualizar_protocolo_vacina(
    protocolo_id: int,
    body: ProtocoloVacinaUpdate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    protocolo = db.query(ProtocoloVacina).filter(
        ProtocoloVacina.id == protocolo_id,
        ProtocoloVacina.tenant_id == tenant_id,
        ProtocoloVacina.ativo == True,  # noqa
    ).first()
    if not protocolo:
        raise HTTPException(404, "Protocolo de vacina não encontrado")

    for campo, valor in body.model_dump(exclude_unset=True).items():
        setattr(protocolo, campo, valor)

    db.commit()
    db.refresh(protocolo)
    return protocolo


@router.delete("/catalogo/protocolos-vacinas/{protocolo_id}", status_code=204)
def remover_protocolo_vacina(
    protocolo_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    protocolo = db.query(ProtocoloVacina).filter(
        ProtocoloVacina.id == protocolo_id,
        ProtocoloVacina.tenant_id == tenant_id,
        ProtocoloVacina.ativo == True,  # noqa
    ).first()
    if not protocolo:
        raise HTTPException(404, "Protocolo de vacina não encontrado")

    protocolo.ativo = False
    db.commit()
    return Response(status_code=204)
