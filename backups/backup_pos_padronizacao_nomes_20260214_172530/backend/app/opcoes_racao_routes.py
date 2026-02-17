# -*- coding: utf-8 -*-
"""
Routes para Opções de Classificação de Rações
CRUD para cadastros auxiliares: linhas, portes, fases, tratamentos, sabores, apresentações
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from app.db import get_session
from app.auth.dependencies import get_current_user_and_tenant
from app.opcoes_racao_models import (
    LinhaRacao, PorteAnimal, FasePublico, TipoTratamento, SaborProteina, ApresentacaoPeso
)

router = APIRouter(prefix="/opcoes-racao", tags=["Opções de Ração"])


# ==================== SCHEMAS ====================

class OpcaoBase(BaseModel):
    nome: str
    descricao: Optional[str] = None
    ordem: int = 0
    ativo: bool = True


class OpcaoResponse(OpcaoBase):
    id: int

    class Config:
        from_attributes = True


class ApresentacaoPesoBase(BaseModel):
    peso_kg: float
    descricao: Optional[str] = None
    ordem: int = 0
    ativo: bool = True


class ApresentacaoPesoResponse(ApresentacaoPesoBase):
    id: int

    class Config:
        from_attributes = True


# ==================== HELPERS ====================

def _validar_tenant_e_obter_usuario(user_and_tenant):
    """Desempacota e valida user_and_tenant"""
    current_user, tenant_id = user_and_tenant
    return current_user, tenant_id


def _verificar_duplicata(db: Session, model, tenant_id, nome: str, id_excluir: Optional[int] = None):
    """Verifica se já existe outro registro com o mesmo nome no tenant"""
    query = db.query(model).filter(
        model.tenant_id == tenant_id,
        model.nome.ilike(nome)  # Case insensitive
    )
    
    if id_excluir:
        query = query.filter(model.id != id_excluir)
    
    return query.first() is not None


# ==================== LINHAS DE RAÇÃO ====================

@router.get("/linhas", response_model=List[OpcaoResponse])
async def listar_linhas_racao(
    apenas_ativos: bool = True,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Lista todas as linhas de ração (Premium, Super Premium, etc.)"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    query = db.query(LinhaRacao).filter(LinhaRacao.tenant_id == tenant_id)
    
    if apenas_ativos:
        query = query.filter(LinhaRacao.ativo == True)
    
    return query.order_by(LinhaRacao.ordem, LinhaRacao.nome).all()


@router.post("/linhas", response_model=OpcaoResponse)
async def criar_linha_racao(
    dados: OpcaoBase,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Cria uma nova linha de ração"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    if _verificar_duplicata(db, LinhaRacao, tenant_id, dados.nome):
        raise HTTPException(status_code=400, detail=f"Já existe uma linha com o nome '{dados.nome}'")
    
    nova_linha = LinhaRacao(
        tenant_id=tenant_id,
        nome=dados.nome,
        descricao=dados.descricao,
        ordem=dados.ordem,
        ativo=dados.ativo
    )
    
    db.add(nova_linha)
    db.commit()
    db.refresh(nova_linha)
    
    return nova_linha


@router.put("/linhas/{linha_id}", response_model=OpcaoResponse)
async def atualizar_linha_racao(
    linha_id: int,
    dados: OpcaoBase,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Atualiza uma linha de ração existente"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    linha = db.query(LinhaRacao).filter(
        LinhaRacao.id == linha_id,
        LinhaRacao.tenant_id == tenant_id
    ).first()
    
    if not linha:
        raise HTTPException(status_code=404, detail="Linha não encontrada")
    
    if _verificar_duplicata(db, LinhaRacao, tenant_id, dados.nome, linha_id):
        raise HTTPException(status_code=400, detail=f"Já existe outra linha com o nome '{dados.nome}'")
    
    linha.nome = dados.nome
    linha.descricao = dados.descricao
    linha.ordem = dados.ordem
    linha.ativo = dados.ativo
    
    db.commit()
    db.refresh(linha)
    
    return linha


@router.delete("/linhas/{linha_id}")
async def deletar_linha_racao(
    linha_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Deleta (inativa) uma linha de ração"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    linha = db.query(LinhaRacao).filter(
        LinhaRacao.id == linha_id,
        LinhaRacao.tenant_id == tenant_id
    ).first()
    
    if not linha:
        raise HTTPException(status_code=404, detail="Linha não encontrada")
    
    linha.ativo = False
    db.commit()
    
    return {"success": True, "message": "Linha inativada com sucesso"}


# ==================== PORTES ====================

@router.get("/portes", response_model=List[OpcaoResponse])
async def listar_portes(
    apenas_ativos: bool = True,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Lista todos os portes de animal"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    query = db.query(PorteAnimal).filter(PorteAnimal.tenant_id == tenant_id)
    
    if apenas_ativos:
        query = query.filter(PorteAnimal.ativo == True)
    
    return query.order_by(PorteAnimal.ordem, PorteAnimal.nome).all()


@router.post("/portes", response_model=OpcaoResponse)
async def criar_porte(
    dados: OpcaoBase,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Cria um novo porte"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    if _verificar_duplicata(db, PorteAnimal, tenant_id, dados.nome):
        raise HTTPException(status_code=400, detail=f"Já existe um porte com o nome '{dados.nome}'")
    
    novo_porte = PorteAnimal(
        tenant_id=tenant_id,
        nome=dados.nome,
        descricao=dados.descricao,
        ordem=dados.ordem,
        ativo=dados.ativo
    )
    
    db.add(novo_porte)
    db.commit()
    db.refresh(novo_porte)
    
    return novo_porte


@router.put("/portes/{porte_id}", response_model=OpcaoResponse)
async def atualizar_porte(
    porte_id: int,
    dados: OpcaoBase,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Atualiza um porte existente"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    porte = db.query(PorteAnimal).filter(
        PorteAnimal.id == porte_id,
        PorteAnimal.tenant_id == tenant_id
    ).first()
    
    if not porte:
        raise HTTPException(status_code=404, detail="Porte não encontrado")
    
    if _verificar_duplicata(db, PorteAnimal, tenant_id, dados.nome, porte_id):
        raise HTTPException(status_code=400, detail=f"Já existe outro porte com o nome '{dados.nome}'")
    
    porte.nome = dados.nome
    porte.descricao = dados.descricao
    porte.ordem = dados.ordem
    porte.ativo = dados.ativo
    
    db.commit()
    db.refresh(porte)
    
    return porte


@router.delete("/portes/{porte_id}")
async def deletar_porte(
    porte_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Deleta (inativa) um porte"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    porte = db.query(PorteAnimal).filter(
        PorteAnimal.id == porte_id,
        PorteAnimal.tenant_id == tenant_id
    ).first()
    
    if not porte:
        raise HTTPException(status_code=404, detail="Porte não encontrado")
    
    porte.ativo = False
    db.commit()
    
    return {"success": True, "message": "Porte inativado com sucesso"}


# ==================== FASES/PÚBLICO ====================

@router.get("/fases", response_model=List[OpcaoResponse])
async def listar_fases(
    apenas_ativos: bool = True,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Lista todas as fases/público"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    query = db.query(FasePublico).filter(FasePublico.tenant_id == tenant_id)
    
    if apenas_ativos:
        query = query.filter(FasePublico.ativo == True)
    
    return query.order_by(FasePublico.ordem, FasePublico.nome).all()


@router.post("/fases", response_model=OpcaoResponse)
async def criar_fase(
    dados: OpcaoBase,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Cria uma nova fase/público"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    if _verificar_duplicata(db, FasePublico, tenant_id, dados.nome):
        raise HTTPException(status_code=400, detail=f"Já existe uma fase com o nome '{dados.nome}'")
    
    nova_fase = FasePublico(
        tenant_id=tenant_id,
        nome=dados.nome,
        descricao=dados.descricao,
        ordem=dados.ordem,
        ativo=dados.ativo
    )
    
    db.add(nova_fase)
    db.commit()
    db.refresh(nova_fase)
    
    return nova_fase


@router.put("/fases/{fase_id}", response_model=OpcaoResponse)
async def atualizar_fase(
    fase_id: int,
    dados: OpcaoBase,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Atualiza uma fase/público existente"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    fase = db.query(FasePublico).filter(
        FasePublico.id == fase_id,
        FasePublico.tenant_id == tenant_id
    ).first()
    
    if not fase:
        raise HTTPException(status_code=404, detail="Fase não encontrada")
    
    if _verificar_duplicata(db, FasePublico, tenant_id, dados.nome, fase_id):
        raise HTTPException(status_code=400, detail=f"Já existe outra fase com o nome '{dados.nome}'")
    
    fase.nome = dados.nome
    fase.descricao = dados.descricao
    fase.ordem = dados.ordem
    fase.ativo = dados.ativo
    
    db.commit()
    db.refresh(fase)
    
    return fase


@router.delete("/fases/{fase_id}")
async def deletar_fase(
    fase_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Deleta (inativa) uma fase/público"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    fase = db.query(FasePublico).filter(
        FasePublico.id == fase_id,
        FasePublico.tenant_id == tenant_id
    ).first()
    
    if not fase:
        raise HTTPException(status_code=404, detail="Fase não encontrada")
    
    fase.ativo = False
    db.commit()
    
    return {"success": True, "message": "Fase inativada com sucesso"}


# ==================== TIPOS DE TRATAMENTO ====================

@router.get("/tratamentos", response_model=List[OpcaoResponse])
async def listar_tratamentos(
    apenas_ativos: bool = True,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Lista todos os tipos de tratamento"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    query = db.query(TipoTratamento).filter(TipoTratamento.tenant_id == tenant_id)
    
    if apenas_ativos:
        query = query.filter(TipoTratamento.ativo == True)
    
    return query.order_by(TipoTratamento.ordem, TipoTratamento.nome).all()


@router.post("/tratamentos", response_model=OpcaoResponse)
async def criar_tratamento(
    dados: OpcaoBase,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Cria um novo tipo de tratamento"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    if _verificar_duplicata(db, TipoTratamento, tenant_id, dados.nome):
        raise HTTPException(status_code=400, detail=f"Já existe um tratamento com o nome '{dados.nome}'")
    
    novo_tratamento = TipoTratamento(
        tenant_id=tenant_id,
        nome=dados.nome,
        descricao=dados.descricao,
        ordem=dados.ordem,
        ativo=dados.ativo
    )
    
    db.add(novo_tratamento)
    db.commit()
    db.refresh(novo_tratamento)
    
    return novo_tratamento


@router.put("/tratamentos/{tratamento_id}", response_model=OpcaoResponse)
async def atualizar_tratamento(
    tratamento_id: int,
    dados: OpcaoBase,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Atualiza um tipo de tratamento existente"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    tratamento = db.query(TipoTratamento).filter(
        TipoTratamento.id == tratamento_id,
        TipoTratamento.tenant_id == tenant_id
    ).first()
    
    if not tratamento:
        raise HTTPException(status_code=404, detail="Tratamento não encontrado")
    
    if _verificar_duplicata(db, TipoTratamento, tenant_id, dados.nome, tratamento_id):
        raise HTTPException(status_code=400, detail=f"Já existe outro tratamento com o nome '{dados.nome}'")
    
    tratamento.nome = dados.nome
    tratamento.descricao = dados.descricao
    tratamento.ordem = dados.ordem
    tratamento.ativo = dados.ativo
    
    db.commit()
    db.refresh(tratamento)
    
    return tratamento


@router.delete("/tratamentos/{tratamento_id}")
async def deletar_tratamento(
    tratamento_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Deleta (inativa) um tipo de tratamento"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    tratamento = db.query(TipoTratamento).filter(
        TipoTratamento.id == tratamento_id,
        TipoTratamento.tenant_id == tenant_id
    ).first()
    
    if not tratamento:
        raise HTTPException(status_code=404, detail="Tratamento não encontrado")
    
    tratamento.ativo = False
    db.commit()
    
    return {"success": True, "message": "Tratamento inativado com sucesso"}


# ==================== SABORES/PROTEÍNAS ====================

@router.get("/sabores", response_model=List[OpcaoResponse])
async def listar_sabores(
    apenas_ativos: bool = True,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Lista todos os sabores/proteínas"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    query = db.query(SaborProteina).filter(SaborProteina.tenant_id == tenant_id)
    
    if apenas_ativos:
        query = query.filter(SaborProteina.ativo == True)
    
    return query.order_by(SaborProteina.ordem, SaborProteina.nome).all()


@router.post("/sabores", response_model=OpcaoResponse)
async def criar_sabor(
    dados: OpcaoBase,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Cria um novo sabor/proteína"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    if _verificar_duplicata(db, SaborProteina, tenant_id, dados.nome):
        raise HTTPException(status_code=400, detail=f"Já existe um sabor com o nome '{dados.nome}'")
    
    novo_sabor = SaborProteina(
        tenant_id=tenant_id,
        nome=dados.nome,
        descricao=dados.descricao,
        ordem=dados.ordem,
        ativo=dados.ativo
    )
    
    db.add(novo_sabor)
    db.commit()
    db.refresh(novo_sabor)
    
    return novo_sabor


@router.put("/sabores/{sabor_id}", response_model=OpcaoResponse)
async def atualizar_sabor(
    sabor_id: int,
    dados: OpcaoBase,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Atualiza um sabor/proteína existente"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    sabor = db.query(SaborProteina).filter(
        SaborProteina.id == sabor_id,
        SaborProteina.tenant_id == tenant_id
    ).first()
    
    if not sabor:
        raise HTTPException(status_code=404, detail="Sabor não encontrado")
    
    if _verificar_duplicata(db, SaborProteina, tenant_id, dados.nome, sabor_id):
        raise HTTPException(status_code=400, detail=f"Já existe outro sabor com o nome '{dados.nome}'")
    
    sabor.nome = dados.nome
    sabor.descricao = dados.descricao
    sabor.ordem = dados.ordem
    sabor.ativo = dados.ativo
    
    db.commit()
    db.refresh(sabor)
    
    return sabor


@router.delete("/sabores/{sabor_id}")
async def deletar_sabor(
    sabor_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Deleta (inativa) um sabor/proteína"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    sabor = db.query(SaborProteina).filter(
        SaborProteina.id == sabor_id,
        SaborProteina.tenant_id == tenant_id
    ).first()
    
    if not sabor:
        raise HTTPException(status_code=404, detail="Sabor não encontrado")
    
    sabor.ativo = False
    db.commit()
    
    return {"success": True, "message": "Sabor inativado com sucesso"}


# ==================== APRESENTAÇÕES (PESO) ====================

@router.get("/apresentacoes", response_model=List[ApresentacaoPesoResponse])
async def listar_apresentacoes(
    apenas_ativos: bool = True,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Lista todas as apresentações de peso"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    query = db.query(ApresentacaoPeso).filter(ApresentacaoPeso.tenant_id == tenant_id)
    
    if apenas_ativos:
        query = query.filter(ApresentacaoPeso.ativo == True)
    
    return query.order_by(ApresentacaoPeso.ordem, ApresentacaoPeso.peso_kg).all()


@router.post("/apresentacoes", response_model=ApresentacaoPesoResponse)
async def criar_apresentacao(
    dados: ApresentacaoPesoBase,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Cria uma nova apresentação de peso"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    # Verificar se já existe peso duplicado
    existe = db.query(ApresentacaoPeso).filter(
        ApresentacaoPeso.tenant_id == tenant_id,
        ApresentacaoPeso.peso_kg == dados.peso_kg
    ).first()
    
    if existe:
        raise HTTPException(status_code=400, detail=f"Já existe uma apresentação com {dados.peso_kg}kg")
    
    nova_apresentacao = ApresentacaoPeso(
        tenant_id=tenant_id,
        peso_kg=dados.peso_kg,
        descricao=dados.descricao or f"{dados.peso_kg}kg",
        ordem=dados.ordem,
        ativo=dados.ativo
    )
    
    db.add(nova_apresentacao)
    db.commit()
    db.refresh(nova_apresentacao)
    
    return nova_apresentacao


@router.put("/apresentacoes/{apresentacao_id}", response_model=ApresentacaoPesoResponse)
async def atualizar_apresentacao(
    apresentacao_id: int,
    dados: ApresentacaoPesoBase,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Atualiza uma apresentação de peso existente"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    apresentacao = db.query(ApresentacaoPeso).filter(
        ApresentacaoPeso.id == apresentacao_id,
        ApresentacaoPeso.tenant_id == tenant_id
    ).first()
    
    if not apresentacao:
        raise HTTPException(status_code=404, detail="Apresentação não encontrada")
    
    # Verificar duplicata de peso
    existe = db.query(ApresentacaoPeso).filter(
        ApresentacaoPeso.tenant_id == tenant_id,
        ApresentacaoPeso.peso_kg == dados.peso_kg,
        ApresentacaoPeso.id != apresentacao_id
    ).first()
    
    if existe:
        raise HTTPException(status_code=400, detail=f"Já existe outra apresentação com {dados.peso_kg}kg")
    
    apresentacao.peso_kg = dados.peso_kg
    apresentacao.descricao = dados.descricao or f"{dados.peso_kg}kg"
    apresentacao.ordem = dados.ordem
    apresentacao.ativo = dados.ativo
    
    db.commit()
    db.refresh(apresentacao)
    
    return apresentacao


@router.delete("/apresentacoes/{apresentacao_id}")
async def deletar_apresentacao(
    apresentacao_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Deleta (inativa) uma apresentação de peso"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    apresentacao = db.query(ApresentacaoPeso).filter(
        ApresentacaoPeso.id == apresentacao_id,
        ApresentacaoPeso.tenant_id == tenant_id
    ).first()
    
    if not apresentacao:
        raise HTTPException(status_code=404, detail="Apresentação não encontrada")
    
    apresentacao.ativo = False
    db.commit()
    
    return {"success": True, "message": "Apresentação inativada com sucesso"}
