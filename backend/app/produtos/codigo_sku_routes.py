"""Rotas de codigo de barras e SKU de produtos."""

from collections.abc import Iterable

from fastapi import APIRouter, Depends, HTTPException
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


def _proximo_sku_disponivel(prefixo: str, codigos_existentes: Iterable[str]):
    """Continua a sequencia recente e pula todos os SKUs ja ocupados."""
    marcador = f"{prefixo}-"
    numeros_ocupados = set()
    ultimo_numero = None
    for codigo in codigos_existentes:
        codigo_normalizado = str(codigo or "").strip().upper()
        if not codigo_normalizado.startswith(marcador):
            continue

        sufixo = codigo_normalizado[len(marcador) :]
        if sufixo.isdigit():
            numero = int(sufixo)
            numeros_ocupados.add(numero)
            if ultimo_numero is None:
                ultimo_numero = numero

    proximo_numero = (ultimo_numero or 0) + 1
    while proximo_numero in numeros_ocupados:
        proximo_numero += 1

    return f"{prefixo}-{proximo_numero:05d}", proximo_numero


@router.post("/gerar-codigo-barras", response_model=GerarCodigoBarrasResponse)
def gerar_codigo_barras(
    request: GerarCodigoBarrasRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Gera código de barras EAN-13 único
    Formato: 789-XXXXX-SKUU-C
    - 789: Prefixo Brasil
    - XXXXX: 5 dígitos aleatórios
    - SKUU: 4 últimos dígitos do SKU
    - C: Dígito verificador
    """
    current_user, tenant_id = user_and_tenant

    max_tentativas = 10
    tentativa = 0

    while tentativa < max_tentativas:
        # Gerar código
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
        detail="Não foi possível gerar código de barras único após múltiplas tentativas",
    )


@router.get("/validar-codigo-barras/{codigo}")
def validar_codigo_barras(
    codigo: str,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Valida um código de barras EAN-13"""

    _, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    resultado_validacao = validar_codigo_barras_ean13(codigo)
    if not resultado_validacao["valido"]:
        return {
            "valido": False,
            "erro": resultado_validacao["erro"],
        }

    codigo_limpo = resultado_validacao["codigo_limpo"]

    # Verificar se já existe no banco
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
            "aviso": "Código de barras já cadastrado para outro produto",
        }

    return {
        "valido": True,
        "existe_no_banco": False,
        "mensagem": "Código de barras válido e disponível",
    }


@router.post("/gerar-sku")
def gerar_sku(
    prefixo: str = "PROD",
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Gera um SKU único automaticamente
    Formato: {PREFIXO}-{NÚMERO_SEQUENCIAL}
    Exemplo: PROD-00001
    """
    _, tenant_id = user_and_tenant
    prefixo = _normalizar_sku_produto(prefixo).upper()

    # Os codigos chegam do mais recente para o mais antigo. A sequencia continua
    # do ultimo sufixo numerico e pula quantos codigos ocupados forem necessarios.
    registros = (
        db.query(Produto.codigo)
        .filter(Produto.tenant_id == tenant_id, Produto.codigo.ilike(f"{prefixo}-%"))
        .order_by(Produto.id.desc())
        .all()
    )
    novo_sku, proximo_numero = _proximo_sku_disponivel(
        prefixo,
        [registro[0] for registro in registros],
    )

    return {
        "sku": novo_sku,
        "prefixo": prefixo,
        "numero": proximo_numero,
        "disponivel": True,
    }
