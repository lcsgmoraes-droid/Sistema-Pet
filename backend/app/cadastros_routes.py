"""
Routes para gerenciamento de Espécies e Raças
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
import logging

from app.db import get_session
from app.models import User, Especie, Raca
from app.auth import get_current_user
from app.auth.dependencies import get_current_user_and_tenant
from app.audit_log import log_create, log_update, log_delete

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cadastros", tags=["cadastros"])


def ensure_especies_racas_tables_exist(db: Session) -> None:
    """Cria tabelas de espécies/raças automaticamente em ambientes sem migration."""
    Especie.__table__.create(bind=db.get_bind(), checkfirst=True)
    Raca.__table__.create(bind=db.get_bind(), checkfirst=True)
    # Compatibilidade com schema legado de racas (coluna `especie` textual).
    db.execute(text("ALTER TABLE racas ADD COLUMN IF NOT EXISTS especie_id INTEGER"))
    db.execute(text("ALTER TABLE racas ADD COLUMN IF NOT EXISTS tenant_id UUID"))
    db.execute(text("ALTER TABLE racas ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()"))
    db.execute(text("""
        UPDATE racas r
        SET especie_id = e.id
        FROM especies e
        WHERE r.especie_id IS NULL
          AND COALESCE(r.especie, '') <> ''
          AND lower(trim(r.especie)) = lower(trim(e.nome))
    """))
    db.execute(text("""
        UPDATE racas r
        SET tenant_id = e.tenant_id
        FROM especies e
        WHERE r.tenant_id IS NULL
          AND r.especie_id = e.id
    """))
    db.execute(text("CREATE INDEX IF NOT EXISTS ix_racas_especie_id ON racas (especie_id)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS ix_racas_tenant_id ON racas (tenant_id)"))
    db.commit()


# ========== SCHEMAS ==========

class EspecieCreate(BaseModel):
    nome: str
    ativo: bool = True


class EspecieUpdate(BaseModel):
    nome: Optional[str] = None
    ativo: Optional[bool] = None


class EspecieResponse(BaseModel):
    id: int
    nome: str
    ativo: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class RacaCreate(BaseModel):
    nome: str
    especie_id: int
    ativo: bool = True


class RacaUpdate(BaseModel):
    nome: Optional[str] = None
    especie_id: Optional[int] = None
    ativo: Optional[bool] = None


class RacaResponse(BaseModel):
    id: int
    nome: str
    especie_id: int
    especie_nome: Optional[str] = None
    ativo: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


# ========== ESPECIES - CRUD ==========

@router.get("/especies", response_model=List[EspecieResponse])
def listar_especies(
    ativo: Optional[bool] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Listar todas as espécies cadastradas"""
    current_user, tenant_id = user_and_tenant
    ensure_especies_racas_tables_exist(db)
    
    query = db.query(Especie).filter(Especie.tenant_id == tenant_id)
    
    if ativo is not None:
        query = query.filter(Especie.ativo == ativo)
    
    if search:
        query = query.filter(Especie.nome.ilike(f"%{search}%"))
    
    especies = query.order_by(Especie.nome).all()
    return especies


@router.get("/especies/{especie_id}", response_model=EspecieResponse)
def obter_especie(
    especie_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Obter uma espécie por ID"""
    current_user, tenant_id = user_and_tenant
    ensure_especies_racas_tables_exist(db)
    
    especie = db.query(Especie).filter(
        Especie.id == especie_id,
        Especie.tenant_id == tenant_id
    ).first()
    
    if not especie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Espécie não encontrada"
        )
    
    return especie


@router.post("/especies", response_model=EspecieResponse, status_code=status.HTTP_201_CREATED)
def criar_especie(
    especie_data: EspecieCreate,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Criar uma nova espécie"""
    current_user, tenant_id = user_and_tenant
    ensure_especies_racas_tables_exist(db)
    
    # Verificar duplicação
    existe = db.query(Especie).filter(
        Especie.tenant_id == tenant_id,
        Especie.nome.ilike(especie_data.nome)
    ).first()
    
    if existe:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Já existe uma espécie com o nome '{especie_data.nome}'"
        )
    
    # Criar espécie
    nova_especie = Especie(
        tenant_id=tenant_id,
        nome=especie_data.nome,
        ativo=especie_data.ativo
    )
    
    db.add(nova_especie)
    db.commit()
    db.refresh(nova_especie)
    
    # Audit log
    log_create(
        db=db,
        user_id=current_user.id,
        entity_type="especie",
        entity_id=nova_especie.id,
        data={"nome": nova_especie.nome, "ativo": nova_especie.ativo}
    )
    
    return nova_especie


@router.put("/especies/{especie_id}", response_model=EspecieResponse)
def atualizar_especie(
    especie_id: int,
    especie_data: EspecieUpdate,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Atualizar uma espécie existente"""
    current_user, tenant_id = user_and_tenant
    ensure_especies_racas_tables_exist(db)
    
    especie = db.query(Especie).filter(
        Especie.id == especie_id,
        Especie.tenant_id == tenant_id
    ).first()
    
    if not especie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Espécie não encontrada"
        )
    
    # Salvar dados antigos para audit log
    old_data = {
        "nome": especie.nome,
        "ativo": especie.ativo
    }
    
    # Verificar duplicação de nome
    if especie_data.nome:
        existe = db.query(Especie).filter(
            Especie.tenant_id == tenant_id,
            Especie.nome.ilike(especie_data.nome),
            Especie.id != especie_id
        ).first()
        
        if existe:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Já existe outra espécie com o nome '{especie_data.nome}'"
            )
    
    # Atualizar campos
    if especie_data.nome is not None:
        especie.nome = especie_data.nome
    if especie_data.ativo is not None:
        especie.ativo = especie_data.ativo
    
    especie.updated_at = datetime.now()
    
    db.commit()
    db.refresh(especie)
    
    # Audit log
    log_update(
        db=db,
        user_id=current_user.id,
        entity_type="especie",
        entity_id=especie.id,
        old_data=old_data,
        new_data=especie_data.model_dump(exclude_unset=True)
    )
    
    return especie


@router.delete("/especies/{especie_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_especie(
    especie_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Deletar uma espécie (soft delete - desativa)"""
    current_user, tenant_id = user_and_tenant
    ensure_especies_racas_tables_exist(db)
    
    especie = db.query(Especie).filter(
        Especie.id == especie_id,
        Especie.tenant_id == tenant_id
    ).first()
    
    if not especie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Espécie não encontrada"
        )
    
    # Verificar se existem raças ativas vinculadas
    racas_ativas = db.query(Raca).filter(
        Raca.especie_id == especie_id,
        Raca.ativo == True
    ).count()
    
    if racas_ativas > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Não é possível excluir. Existem {racas_ativas} raça(s) ativa(s) vinculada(s) a esta espécie."
        )
    
    # Soft delete
    especie.ativo = False
    especie.updated_at = datetime.now()
    
    db.commit()
    
    # Audit log
    log_delete(
        db=db,
        user_id=current_user.id,
        entity_type="especie",
        entity_id=especie.id,
        data={"nome": especie.nome}
    )
    
    return None


# ========== RAÇAS - CRUD ==========

@router.get("/racas", response_model=List[RacaResponse])
def listar_racas(
    especie_id: Optional[int] = None,
    ativo: Optional[bool] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Listar todas as raças cadastradas (com filtro por espécie)"""
    current_user, tenant_id = user_and_tenant
    ensure_especies_racas_tables_exist(db)
    
    query = db.query(Raca).filter(Raca.tenant_id == tenant_id)
    
    if especie_id:
        query = query.filter(Raca.especie_id == especie_id)
    
    if ativo is not None:
        query = query.filter(Raca.ativo == ativo)
    
    if search:
        query = query.filter(Raca.nome.ilike(f"%{search}%"))
    
    racas = query.order_by(Raca.nome).all()
    
    # Adicionar nome da espécie
    resultado = []
    for raca in racas:
        raca_dict = {
            "id": raca.id,
            "nome": raca.nome,
            "especie_id": raca.especie_id,
            "especie_nome": raca.especie_obj.nome if raca.especie_obj else None,
            "ativo": raca.ativo,
            "created_at": raca.created_at,
            "updated_at": raca.updated_at
        }
        resultado.append(raca_dict)
    
    return resultado


@router.get("/racas/{raca_id}", response_model=RacaResponse)
def obter_raca(
    raca_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Obter uma raça por ID"""
    current_user, tenant_id = user_and_tenant
    ensure_especies_racas_tables_exist(db)
    
    raca = db.query(Raca).filter(
        Raca.id == raca_id,
        Raca.tenant_id == tenant_id
    ).first()
    
    if not raca:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Raça não encontrada"
        )
    
    return {
        "id": raca.id,
        "nome": raca.nome,
        "especie_id": raca.especie_id,
        "especie_nome": raca.especie_obj.nome if raca.especie_obj else None,
        "ativo": raca.ativo,
        "created_at": raca.created_at,
        "updated_at": raca.updated_at
    }


@router.post("/racas", response_model=RacaResponse, status_code=status.HTTP_201_CREATED)
def criar_raca(
    raca_data: RacaCreate,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Criar uma nova raça"""
    current_user, tenant_id = user_and_tenant
    ensure_especies_racas_tables_exist(db)
    
    # Verificar se a espécie existe
    especie = db.query(Especie).filter(
        Especie.id == raca_data.especie_id,
        Especie.tenant_id == tenant_id
    ).first()
    
    if not especie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Espécie não encontrada"
        )
    
    # Verificar duplicação
    existe = db.query(Raca).filter(
        Raca.tenant_id == tenant_id,
        Raca.especie_id == raca_data.especie_id,
        Raca.nome.ilike(raca_data.nome)
    ).first()
    
    if existe:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Já existe uma raça '{raca_data.nome}' para esta espécie"
        )
    
    # Criar raça
    nova_raca = Raca(
        tenant_id=tenant_id,
        nome=raca_data.nome,
        especie_id=raca_data.especie_id,
        ativo=raca_data.ativo
    )
    
    db.add(nova_raca)
    db.commit()
    db.refresh(nova_raca)
    
    # Audit log
    log_create(
        db=db,
        user_id=current_user.id,
        entity_type="raca",
        entity_id=nova_raca.id,
        data={"nome": nova_raca.nome, "especie_id": nova_raca.especie_id, "ativo": nova_raca.ativo}
    )
    
    return {
        "id": nova_raca.id,
        "nome": nova_raca.nome,
        "especie_id": nova_raca.especie_id,
        "especie_nome": especie.nome,
        "ativo": nova_raca.ativo,
        "created_at": nova_raca.created_at,
        "updated_at": nova_raca.updated_at
    }


@router.put("/racas/{raca_id}", response_model=RacaResponse)
def atualizar_raca(
    raca_id: int,
    raca_data: RacaUpdate,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Atualizar uma raça existente"""
    current_user, tenant_id = user_and_tenant
    ensure_especies_racas_tables_exist(db)
    
    raca = db.query(Raca).filter(
        Raca.id == raca_id,
        Raca.tenant_id == tenant_id
    ).first()
    
    if not raca:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Raça não encontrada"
        )
        # Salvar dados antigos para audit log
    old_data = {
        "nome": raca.nome,
        "especie_id": raca.especie_id,
        "ativo": raca.ativo
    }
        # Verificar se a espécie existe (se estiver sendo alterada)
    if raca_data.especie_id:
        especie = db.query(Especie).filter(
            Especie.id == raca_data.especie_id,
            Especie.tenant_id == tenant_id
        ).first()
        
        if not especie:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Espécie não encontrada"
            )
    
    # Verificar duplicação de nome
    if raca_data.nome:
        especie_id_verificacao = raca_data.especie_id or raca.especie_id
        
        existe = db.query(Raca).filter(
            Raca.tenant_id == tenant_id,
            Raca.especie_id == especie_id_verificacao,
            Raca.nome.ilike(raca_data.nome),
            Raca.id != raca_id
        ).first()
        
        if existe:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Já existe outra raça '{raca_data.nome}' para esta espécie"
            )
    
    # Atualizar campos
    if raca_data.nome is not None:
        raca.nome = raca_data.nome
    if raca_data.especie_id is not None:
        raca.especie_id = raca_data.especie_id
    if raca_data.ativo is not None:
        raca.ativo = raca_data.ativo
    
    raca.updated_at = datetime.now()
    
    db.commit()
    db.refresh(raca)
    
    # Audit log
    log_update(
        db=db,
        user_id=current_user.id,
        entity_type="raca",
        entity_id=raca.id,
        old_data=old_data,
        new_data=raca_data.model_dump(exclude_unset=True)
    )
    
    return {
        "id": raca.id,
        "nome": raca.nome,
        "especie_id": raca.especie_id,
        "especie_nome": raca.especie_obj.nome if raca.especie_obj else None,
        "ativo": raca.ativo,
        "created_at": raca.created_at,
        "updated_at": raca.updated_at
    }


@router.delete("/racas/{raca_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_raca(
    raca_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Deletar uma raça (soft delete - desativa)"""
    current_user, tenant_id = user_and_tenant
    ensure_especies_racas_tables_exist(db)
    
    raca = db.query(Raca).filter(
        Raca.id == raca_id,
        Raca.tenant_id == tenant_id
    ).first()
    
    if not raca:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Raça não encontrada"
        )
    
    # Soft delete
    raca.ativo = False
    raca.updated_at = datetime.now()
    
    db.commit()
    
    # Audit log
    log_delete(
        db=db,
        user_id=current_user.id,
        entity_type="raca",
        entity_id=raca.id,
        data={"nome": raca.nome}
    )
    
    return None
