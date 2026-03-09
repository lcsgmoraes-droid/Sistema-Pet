"""
Rotas SEFAZ — Consulta de NF-e por chave de acesso.

ATENÇÃO: Este módulo é um scaffolding. A integração real com a SEFAZ
exige certificado digital A1/A3, credenciais IBPT e ambiente de produção.
Por enquanto retorna dados simulados para desenvolvimento e layout da tela.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db.session import get_db

router = APIRouter(prefix="/sefaz", tags=["sefaz"])


class ConsultaNFeRequest(BaseModel):
    chave_acesso: str  # 44 dígitos


class ItemNFe(BaseModel):
    numero_item: int
    codigo_produto: str
    descricao: str
    ncm: Optional[str] = None
    cfop: Optional[str] = None
    quantidade: float
    unidade: str
    valor_unitario: float
    valor_total: float


class ConsultaNFeResponse(BaseModel):
    chave_acesso: str
    numero_nf: str
    serie: str
    data_emissao: str
    emitente_cnpj: str
    emitente_nome: str
    destinatario_cnpj: Optional[str] = None
    destinatario_nome: Optional[str] = None
    valor_total_nf: float
    itens: List[ItemNFe]
    aviso: str


@router.post("/consultar", response_model=ConsultaNFeResponse)
async def consultar_nfe(
    payload: ConsultaNFeRequest,
    auth=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    """
    Consulta uma NF-e na SEFAZ pela chave de acesso (44 dígitos).

    MODO ATUAL: simulação para desenvolvimento.
    Para produção real é necessário:
    - Certificado digital A1 (.pfx) do estabelecimento
    - Credenciais de acesso ao webservice SEFAZ do estado
    - Biblioteca nfeio ou zeep configurada com o certificado
    """
    chave = payload.chave_acesso.replace(" ", "").replace(".", "")

    if len(chave) != 44 or not chave.isdigit():
        raise HTTPException(
            status_code=422,
            detail="Chave de acesso inválida. Deve conter exatamente 44 dígitos numéricos.",
        )

    # --- SIMULAÇÃO (remover quando integrar certificado real) ---
    return ConsultaNFeResponse(
        chave_acesso=chave,
        numero_nf="000123",
        serie="001",
        data_emissao="2025-01-15",
        emitente_cnpj="12.345.678/0001-90",
        emitente_nome="Fornecedor Simulado Ltda",
        destinatario_cnpj=None,
        destinatario_nome="Petshop (Destinatário)",
        valor_total_nf=1250.00,
        itens=[
            ItemNFe(
                numero_item=1,
                codigo_produto="PRD001",
                descricao="Ração Premium Cão Adulto 15kg",
                ncm="23091000",
                cfop="6102",
                quantidade=10.0,
                unidade="UN",
                valor_unitario=89.90,
                valor_total=899.00,
            ),
            ItemNFe(
                numero_item=2,
                codigo_produto="PRD002",
                descricao="Antipulgas Spot-On Cão 10-25kg",
                ncm="30049099",
                cfop="6102",
                quantidade=5.0,
                unidade="UN",
                valor_unitario=70.20,
                valor_total=351.00,
            ),
        ],
        aviso=(
            "⚠️ MODO DESENVOLVIMENTO: dados simulados. "
            "Para consultar NF-e reais configure o certificado digital A1 "
            "e as credenciais SEFAZ no arquivo .env."
        ),
    )
