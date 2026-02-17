from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_session as get_db
from app.services.fiscal_sugestao_service import sugerir_fiscal_por_descricao

router = APIRouter(prefix="/fiscal/sugestao", tags=["Fiscal"])


@router.post("/produto")
def sugestao_fiscal_produto(
    descricao: str,
    db: Session = Depends(get_db)
):
    """
    Endpoint de sugestão fiscal por descrição de produto.
    Apenas sugere, não grava.
    """
    sugestoes = sugerir_fiscal_por_descricao(db, descricao)
    return {"sugestoes": sugestoes}
