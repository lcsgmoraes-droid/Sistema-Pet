
from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.nf_item_rateio_validator import validar_rateio_item
from app.nf_item_rateio_canal_models import NotaFiscalItemRateioCanal

router = APIRouter(
    prefix="/notas-fiscais/itens",
    tags=["Notas Fiscais - Rateio por Item"]
)

@router.post("/{item_id}/rateio")
def salvar_rateio_item(
    item_id: str,
    rateios: list,
    db: Session = next(get_db())
):
    """
    Recebe rateio por QUANTIDADE e calcula valor e percentual.
    """

    # 🔴 AQUI assumimos que você já tem:
    # - quantidade_total_item
    # - preco_unitario
    #
    # Ajuste este trecho se o nome do model do item for diferente.

    item = db.execute(
        "SELECT quantidade, preco_unitario FROM nota_fiscal_itens WHERE id = :id",
        {"id": item_id}
    ).fetchone()

    if not item:
        raise HTTPException(status_code=404, detail="Item da NF não encontrado")

    quantidade_total, preco_unitario = item

    # Validação + cálculo
    resultado = validar_rateio_item(
        rateios=rateios,
        quantidade_total_item=quantidade_total,
        preco_unitario=float(preco_unitario)
    )

    # Remove rateios anteriores
    db.query(NotaFiscalItemRateioCanal).filter(
        NotaFiscalItemRateioCanal.nota_fiscal_item_id == item_id
    ).delete()

    # Salva novos
    for r in resultado:
        db.add(
            NotaFiscalItemRateioCanal(
                nota_fiscal_item_id=item_id,
                canal=r["canal"],
                quantidade=r["quantidade"],
                valor_calculado=r["valor_calculado"],
                percentual_calculado=r["percentual_calculado"]
            )
        )

    db.commit()

    return {
        "status": "ok",
        "rateio": resultado
    }
