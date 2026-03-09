"""
Rotas para gerenciar Descontos Globais por Canal (Ecommerce / App).

Lógica de prioridade (de maior para menor):
  1. Promoção específica do produto no canal (preco_ecommerce_promo / preco_app_promo com data válida)
  2. Campanha global do canal (este módulo) — aplica % sobre o preço de venda padrão
  3. Preço normal do canal (preco_ecommerce / preco_app)
  4. Preço de venda padrão (preco_venda)
"""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session as get_db

router = APIRouter(prefix="/canal-descontos", tags=["canal-descontos"])


# ─────────────────────── Schemas ───────────────────────

class CanalDescontoCreate(BaseModel):
    canal: str  # 'ecommerce' | 'app'
    nome: str
    desconto_pct: float
    ativo: bool = True
    data_inicio: Optional[datetime] = None
    data_fim: Optional[datetime] = None


class CanalDescontoUpdate(BaseModel):
    nome: Optional[str] = None
    desconto_pct: Optional[float] = None
    ativo: Optional[bool] = None
    data_inicio: Optional[datetime] = None
    data_fim: Optional[datetime] = None


class CanalDescontoResponse(BaseModel):
    id: int
    canal: str
    nome: str
    desconto_pct: float
    ativo: bool
    data_inicio: Optional[datetime]
    data_fim: Optional[datetime]
    created_at: datetime


def _validar_periodo(data_inicio: Optional[datetime], data_fim: Optional[datetime]) -> None:
    """Valida período básico informado pelo usuário."""
    if data_inicio and data_fim and data_inicio > data_fim:
        raise HTTPException(status_code=422, detail="Data de início não pode ser maior que a data de fim.")


def _campanha_ativa_conflitante(
    db: Session,
    tenant_id: str,
    canal: str,
    data_inicio: Optional[datetime],
    data_fim: Optional[datetime],
    excluir_id: Optional[int] = None,
):
    """
    Busca campanha ativa conflitante no mesmo canal e período.
    Regras:
    - Período nulo é tratado como aberto (infinito).
    - Conflito existe quando os intervalos se sobrepõem.
    """
    return db.execute(
        text(
            """
            SELECT id, nome, data_inicio, data_fim
            FROM canal_descontos
            WHERE tenant_id = :tid
              AND canal = :canal
              AND ativo = TRUE
              AND (:excluir_id IS NULL OR id <> :excluir_id)
              AND COALESCE(data_inicio, '-infinity'::timestamp) <= COALESCE(:novo_fim, 'infinity'::timestamp)
              AND COALESCE(data_fim, 'infinity'::timestamp) >= COALESCE(:novo_inicio, '-infinity'::timestamp)
            ORDER BY created_at DESC
            LIMIT 1
            """
        ),
        {
            "tid": tenant_id,
            "canal": canal,
            "excluir_id": excluir_id,
            "novo_inicio": data_inicio,
            "novo_fim": data_fim,
        },
    ).fetchone()


def _validar_conflito_ativo(
    db: Session,
    tenant_id: str,
    canal: str,
    data_inicio: Optional[datetime],
    data_fim: Optional[datetime],
    excluir_id: Optional[int] = None,
):
    """Lança HTTP 409 quando houver sobreposição com campanha ativa no mesmo canal."""
    conflito = _campanha_ativa_conflitante(
        db=db,
        tenant_id=tenant_id,
        canal=canal,
        data_inicio=data_inicio,
        data_fim=data_fim,
        excluir_id=excluir_id,
    )
    if not conflito:
        return

    inicio = conflito.data_inicio.isoformat(sep=" ", timespec="minutes") if conflito.data_inicio else "sem início"
    fim = conflito.data_fim.isoformat(sep=" ", timespec="minutes") if conflito.data_fim else "sem fim"
    raise HTTPException(
        status_code=409,
        detail=(
            f"Já existe campanha ativa no canal '{canal}' neste período: "
            f"{conflito.nome} (ID {conflito.id}) de {inicio} até {fim}. "
            "Pause, edite ou exclua a campanha anterior antes de ativar outra no mesmo período."
        ),
    )


# ─────────────────────── Endpoints ───────────────────────

@router.get("", response_model=List[CanalDescontoResponse])
def listar_descontos(
    canal: Optional[str] = None,
    auth=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    """Lista todos os descontos de canal do tenant."""
    _, tenant_id = auth
    query = "SELECT * FROM canal_descontos WHERE tenant_id = :tid"
    params = {"tid": str(tenant_id)}
    if canal:
        query += " AND canal = :canal"
        params["canal"] = canal
    query += " ORDER BY canal, created_at DESC"
    rows = db.execute(text(query), params).fetchall()
    return [dict(r._mapping) for r in rows]


@router.post("", response_model=CanalDescontoResponse, status_code=201)
def criar_desconto(
    payload: CanalDescontoCreate,
    auth=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    """Cria um novo desconto global para um canal."""
    _, tenant_id = auth
    if payload.canal not in ("ecommerce", "app"):
        raise HTTPException(status_code=422, detail="Canal deve ser 'ecommerce' ou 'app'.")
    if not (0 <= payload.desconto_pct <= 100):
        raise HTTPException(status_code=422, detail="desconto_pct deve estar entre 0 e 100.")

    _validar_periodo(payload.data_inicio, payload.data_fim)

    if payload.ativo:
        _validar_conflito_ativo(
            db=db,
            tenant_id=str(tenant_id),
            canal=payload.canal,
            data_inicio=payload.data_inicio,
            data_fim=payload.data_fim,
        )

    row = db.execute(
        text("""
            INSERT INTO canal_descontos (tenant_id, canal, nome, desconto_pct, ativo, data_inicio, data_fim)
            VALUES (:tid, :canal, :nome, :pct, :ativo, :inicio, :fim)
            RETURNING *
        """),
        {
            "tid": str(tenant_id),
            "canal": payload.canal,
            "nome": payload.nome,
            "pct": payload.desconto_pct,
            "ativo": payload.ativo,
            "inicio": payload.data_inicio,
            "fim": payload.data_fim,
        },
    ).fetchone()
    db.commit()
    return dict(row._mapping)


@router.put("/{desconto_id}", response_model=CanalDescontoResponse)
def atualizar_desconto(
    desconto_id: int,
    payload: CanalDescontoUpdate,
    auth=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    """Atualiza um desconto existente."""
    _, tenant_id = auth
    existing = db.execute(
        text(
            """
            SELECT id, canal, ativo, data_inicio, data_fim
            FROM canal_descontos
            WHERE id = :id AND tenant_id = :tid
            """
        ),
        {"id": desconto_id, "tid": str(tenant_id)},
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Desconto não encontrado.")

    novo_ativo = payload.ativo if payload.ativo is not None else existing.ativo
    novo_inicio = payload.data_inicio if payload.data_inicio is not None else existing.data_inicio
    novo_fim = payload.data_fim if payload.data_fim is not None else existing.data_fim

    _validar_periodo(novo_inicio, novo_fim)

    if novo_ativo:
        _validar_conflito_ativo(
            db=db,
            tenant_id=str(tenant_id),
            canal=existing.canal,
            data_inicio=novo_inicio,
            data_fim=novo_fim,
            excluir_id=desconto_id,
        )

    sets = []
    params: dict = {"id": desconto_id, "tid": str(tenant_id), "now": datetime.now(timezone.utc)}
    if payload.nome is not None:
        sets.append("nome = :nome"); params["nome"] = payload.nome
    if payload.desconto_pct is not None:
        sets.append("desconto_pct = :pct"); params["pct"] = payload.desconto_pct
    if payload.ativo is not None:
        sets.append("ativo = :ativo"); params["ativo"] = payload.ativo
    if payload.data_inicio is not None:
        sets.append("data_inicio = :inicio"); params["inicio"] = payload.data_inicio
    if payload.data_fim is not None:
        sets.append("data_fim = :fim"); params["fim"] = payload.data_fim

    if not sets:
        raise HTTPException(status_code=422, detail="Nenhum campo para atualizar.")

    sets.append("updated_at = :now")
    row = db.execute(
        text(f"UPDATE canal_descontos SET {', '.join(sets)} WHERE id = :id AND tenant_id = :tid RETURNING *"),
        params,
    ).fetchone()
    db.commit()
    return dict(row._mapping)


@router.delete("/{desconto_id}", status_code=204)
def remover_desconto(
    desconto_id: int,
    auth=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    """Remove um desconto de canal."""
    _, tenant_id = auth
    result = db.execute(
        text("DELETE FROM canal_descontos WHERE id = :id AND tenant_id = :tid"),
        {"id": desconto_id, "tid": str(tenant_id)},
    )
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Desconto não encontrado.")


@router.get("/ativo/{canal}")
def desconto_ativo_canal(
    canal: str,
    auth=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    """
    Retorna o desconto global ativo para um canal agora.
    Usado pelo ecommerce/app para aplicar o desconto ao exibir preços.
    """
    _, tenant_id = auth
    agora = datetime.now(timezone.utc)
    row = db.execute(
        text("""
            SELECT desconto_pct, nome FROM canal_descontos
            WHERE tenant_id = :tid AND canal = :canal AND ativo = TRUE
              AND (data_inicio IS NULL OR data_inicio <= :agora)
              AND (data_fim IS NULL OR data_fim >= :agora)
            ORDER BY desconto_pct DESC
            LIMIT 1
        """),
        {"tid": str(tenant_id), "canal": canal, "agora": agora},
    ).fetchone()
    if not row:
        return {"tem_desconto": False, "desconto_pct": 0}
    return {"tem_desconto": True, "desconto_pct": row.desconto_pct, "nome": row.nome}
