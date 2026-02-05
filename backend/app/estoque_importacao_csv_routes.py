
from fastapi import APIRouter, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
import csv
import io

from app.database.session import get_db
from app.estoque_transferencia_service import EstoqueTransferenciaService
from app.local_estoque_models import LocalEstoque

router = APIRouter(
    prefix="/estoque/importacao",
    tags=["Estoque - Importação CSV"]
)

@router.post("/csv")
async def importar_csv(
    file: UploadFile = File(...),
    local_destino_id: str = None,
    db: Session = next(get_db())
):
    if not local_destino_id:
        raise HTTPException(status_code=400, detail="Local de destino obrigatório")

    origem = db.query(LocalEstoque).filter(
        LocalEstoque.origem_padrao == True
    ).first()

    if not origem:
        raise HTTPException(status_code=400, detail="Local de origem padrão não configurado")

    content = await file.read()
    decoded = content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(decoded))

    resultados = {
        "sucesso": [],
        "erros": []
    }

    for i, row in enumerate(reader, start=1):
        try:
            sku = row.get("sku")
            quantidade = int(row.get("quantidade", 0))

            if not sku or quantidade <= 0:
                raise ValueError("Linha inválida")

            resultado = EstoqueTransferenciaService.transferir(
                db=db,
                sku=sku,
                local_origem_id=origem.id,
                local_destino_id=local_destino_id,
                quantidade=quantidade,
                documento="CSV_FULL",
                observacao=f"Linha {i}"
            )

            resultados["sucesso"].append(resultado)

        except Exception as e:
            resultados["erros"].append({
                "linha": i,
                "erro": str(e),
                "dados": row
            })

    return resultados
