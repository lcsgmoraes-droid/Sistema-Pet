
from fastapi import APIRouter, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
import re
import io
import pdfplumber

from app.database.session import get_db
from app.estoque_transferencia_service import EstoqueTransferenciaService
from app.local_estoque_models import LocalEstoque

router = APIRouter(
    prefix="/estoque/importacao",
    tags=["Estoque - Importação PDF"]
)

SKU_REGEX = re.compile(r"SKU[:\s]+([A-Z0-9\-_.]+)", re.IGNORECASE)
QTD_REGEX = re.compile(r"(QTD|QUANTIDADE)[:\s]+(\d+)", re.IGNORECASE)

@router.post("/pdf")
async def importar_pdf(
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

    pdf_bytes = await file.read()

    resultados = {
        "sucesso": [],
        "erros": []
    }

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        texto = ""
        for page in pdf.pages:
            texto += page.extract_text() or ""

    linhas = texto.splitlines()

    atual = {}

    for linha in linhas:
        sku_match = SKU_REGEX.search(linha)
        qtd_match = QTD_REGEX.search(linha)

        if sku_match:
            atual["sku"] = sku_match.group(1)

        if qtd_match:
            atual["quantidade"] = int(qtd_match.group(2))

        if "sku" in atual and "quantidade" in atual:
            try:
                resultado = EstoqueTransferenciaService.transferir(
                    db=db,
                    sku=atual["sku"],
                    local_origem_id=origem.id,
                    local_destino_id=local_destino_id,
                    quantidade=atual["quantidade"],
                    documento="PDF_FULL",
                    observacao="Importação PDF"
                )
                resultados["sucesso"].append(resultado)
            except Exception as e:
                resultados["erros"].append({
                    "sku": atual["sku"],
                    "quantidade": atual["quantidade"],
                    "erro": str(e)
                })
            atual = {}

    return resultados
