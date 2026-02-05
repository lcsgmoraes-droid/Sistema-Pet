
from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.nota_fiscal_rateio_helper import validar_rateio_percentual
from app.nf_rateio_canal_models import NotaFiscalRateioCanal
from app.nota_fiscal_tipos import TipoNotaFiscal

router = APIRouter(prefix="/notas-fiscais", tags=["Notas Fiscais - Rateio"])

@router.post("/{nota_fiscal_id}/rateio")
def salvar_rateio_nf(
    nota_fiscal_id: str,
    rateios: list,
    db: Session = next(get_db())
):
    """
    Espera:
    [
      {"canal": "loja_fisica", "percentual": 70},
      {"canal": "mercado_livre", "percentual": 30}
    ]
    """

    # Validação percentual
    validar_rateio_percentual(rateios)

    # Remove rateios anteriores (idempotente)
    db.query(NotaFiscalRateioCanal).filter(
        NotaFiscalRateioCanal.nota_fiscal_id == nota_fiscal_id
    ).delete()

    for r in rateios:
        db.add(
            NotaFiscalRateioCanal(
                nota_fiscal_id=nota_fiscal_id,
                canal=r["canal"],
                percentual=r["percentual"]
            )
        )

    db.commit()

    return {"status": "ok", "message": "Rateio salvo com sucesso"}
