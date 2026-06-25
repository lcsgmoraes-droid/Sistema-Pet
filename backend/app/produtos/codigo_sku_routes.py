"""Rotas de codigo de barras e SKU de produtos."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.produtos.codigo_barras import (
    gerar_codigo_barras_ean13,
    validar_codigo_barras_ean13,
)
from app.produtos.core import _normalizar_sku_produto
from app.produtos.schemas import GerarCodigoBarrasRequest, GerarCodigoBarrasResponse
from app.produtos.validators import _validar_tenant_e_obter_usuario
from app.produtos_models import Produto

router = APIRouter()


@router.post("/gerar-codigo-barras", response_model=GerarCodigoBarrasResponse)
def gerar_codigo_barras(
    request: GerarCodigoBarrasRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Gera cÃ³digo de barras EAN-13 Ãºnico
    Formato: 789-XXXXX-SKUU-C
    - 789: Prefixo Brasil
    - XXXXX: 5 dÃ­gitos aleatÃ³rios
    - SKUU: 4 Ãºltimos dÃ­gitos do SKU
    - C: DÃ­gito verificador
    """
    current_user, tenant_id = user_and_tenant

    max_tentativas = 10
    tentativa = 0

    while tentativa < max_tentativas:
        # Gerar cÃ³digo
        codigo = gerar_codigo_barras_ean13(request.sku)

        # Verificar se já existe globalmente (constraint é global, não por tenant)
        existe = db.query(Produto).filter(Produto.codigo_barras == codigo).first()

        if not existe:
            return GerarCodigoBarrasResponse(
                codigo_barras=codigo,
                sku_usado=request.sku,
                formato="789-XXXXX-SKUU-C (EAN-13)",
                valido=True,
            )

        tentativa += 1

    raise HTTPException(
        status_code=500,
        detail="NÃ£o foi possÃ­vel gerar cÃ³digo de barras Ãºnico apÃ³s mÃºltiplas tentativas",
    )


@router.get("/validar-codigo-barras/{codigo}")
def validar_codigo_barras(
    codigo: str,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Valida um cÃ³digo de barras EAN-13"""

    _, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    resultado_validacao = validar_codigo_barras_ean13(codigo)
    if not resultado_validacao["valido"]:
        return {
            "valido": False,
            "erro": resultado_validacao["erro"],
        }

    codigo_limpo = resultado_validacao["codigo_limpo"]

    # Verificar se jÃ¡ existe no banco
    existe = (
        db.query(Produto)
        .filter(Produto.codigo_barras == codigo_limpo, Produto.tenant_id == tenant_id)
        .first()
    )

    if existe:
        return {
            "valido": True,
            "existe_no_banco": True,
            "produto_id": existe.id,
            "produto_nome": existe.nome,
            "aviso": "CÃ³digo de barras jÃ¡ cadastrado para outro produto",
        }

    return {
        "valido": True,
        "existe_no_banco": False,
        "mensagem": "CÃ³digo de barras vÃ¡lido e disponÃ­vel",
    }


@router.post("/gerar-sku")
def gerar_sku(
    prefixo: str = "PROD",
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Gera um SKU Ãºnico automaticamente
    Formato: {PREFIXO}-{NÃšMERO_SEQUENCIAL}
    Exemplo: PROD-00001
    """
    _, tenant_id = user_and_tenant
    prefixo = _normalizar_sku_produto(prefixo).upper()

    # Buscar maior numero ja usado com esse prefixo dentro do tenant atual.
    ultimo_produto = (
        db.query(Produto)
        .filter(Produto.tenant_id == tenant_id, Produto.codigo.ilike(f"{prefixo}-%"))
        .order_by(Produto.id.desc())
        .first()
    )

    if ultimo_produto:
        # Extrair número do último SKU
        try:
            ultimo_numero = int(ultimo_produto.codigo.split("-")[-1])
            proximo_numero = ultimo_numero + 1
        except ValueError:
            proximo_numero = 1
    else:
        proximo_numero = 1

    # Gerar novo SKU
    novo_sku = f"{prefixo}-{proximo_numero:05d}"

    existe = (
        db.query(Produto)
        .filter(
            Produto.tenant_id == tenant_id,
            func.lower(Produto.codigo) == novo_sku.lower(),
        )
        .first()
    )

    if existe:
        novo_sku = f"{prefixo}-{proximo_numero + 1:05d}"

    return {
        "sku": novo_sku,
        "prefixo": prefixo,
        "numero": proximo_numero,
        "disponivel": True,
    }
