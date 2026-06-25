"""Helpers compartilhados das rotas de contas a pagar."""

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
import re
import unicodedata

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.dre_plano_contas_models import DRESubcategoria
from app.financeiro_models import CategoriaFinanceira, ContaPagar, TipoDespesa


BUSCA_ACENTOS = "áàâãäéèêëíìîïóòôõöúùûüç"
BUSCA_SEM_ACENTOS = "aaaaaeeeeiiiiooooouuuuc"


def _normalizar_texto_busca(valor: Optional[str]) -> str:
    texto = str(valor or "").strip().lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    texto = texto.replace("-", " ")
    return re.sub(r"\s+", " ", texto).strip()


def _expressao_texto_busca(coluna):
    texto = func.coalesce(coluna, "")
    texto = func.replace(func.lower(texto), "-", " ")
    return func.translate(texto, BUSCA_ACENTOS, BUSCA_SEM_ACENTOS)


def _decimal_monetario(valor) -> Decimal:
    if valor is None:
        return Decimal("0.00")
    return Decimal(str(valor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _valor_reais_para_centavos(valor) -> Decimal:
    return (_decimal_monetario(valor) * Decimal("100")).quantize(
        Decimal("1"),
        rounding=ROUND_HALF_UP,
    )


def _registrar_observacao_operacao_conta_pagar(
    conta: ContaPagar,
    descricao_operacao: str,
    motivo: Optional[str] = None,
) -> None:
    momento = datetime.now().strftime("%d/%m/%Y %H:%M")
    linha = f"{descricao_operacao} em {momento}"
    motivo_limpo = (motivo or "").strip()
    if motivo_limpo:
        linha = f"{linha}. Motivo: {motivo_limpo}"

    observacoes_atuais = (conta.observacoes or "").strip()
    conta.observacoes = f"{observacoes_atuais}\n{linha}".strip()


# ============================================================================
# SCHEMAS
# ============================================================================
# Schemas movidos para app.financeiro.contas_pagar_schemas e reexportados abaixo.


def _obter_tipo_produto_revenda_id(db: Session, tenant_id) -> Optional[int]:
    nomes_prioritarios = [
        "Produto para Revenda",
        "Fornecedor de Produto para Revenda",
    ]
    for nome in nomes_prioritarios:
        tipo = (
            db.query(TipoDespesa)
            .filter(
                TipoDespesa.tenant_id == tenant_id,
                func.lower(TipoDespesa.nome) == nome.lower(),
                TipoDespesa.ativo.is_(True),
            )
            .first()
        )
        if tipo:
            return tipo.id

    tipo = (
        db.query(TipoDespesa)
        .filter(
            TipoDespesa.tenant_id == tenant_id,
            TipoDespesa.nome.ilike("%produto%revenda%"),
            TipoDespesa.ativo.is_(True),
        )
        .order_by(TipoDespesa.nome.asc())
        .first()
    )
    return tipo.id if tipo else None


def _resolver_dre_subcategoria_conta_pagar(
    db: Session,
    tenant_id,
    *,
    dre_subcategoria_id: Optional[int],
    categoria_id: Optional[int],
) -> int:
    if dre_subcategoria_id is not None:
        subcategoria = (
            db.query(DRESubcategoria)
            .filter(
                DRESubcategoria.id == dre_subcategoria_id,
                DRESubcategoria.tenant_id == tenant_id,
                DRESubcategoria.ativo.is_(True),
            )
            .first()
        )
        if not subcategoria:
            raise HTTPException(
                status_code=400,
                detail=f"Subcategoria DRE {dre_subcategoria_id} invalida ou nao pertence a este tenant",
            )
        return subcategoria.id

    if categoria_id is not None:
        categoria = (
            db.query(CategoriaFinanceira)
            .filter(
                CategoriaFinanceira.id == categoria_id,
                CategoriaFinanceira.tenant_id == tenant_id,
                CategoriaFinanceira.ativo.is_(True),
            )
            .first()
        )
        if not categoria:
            raise HTTPException(
                status_code=400,
                detail="Categoria financeira invalida ou nao pertence a este tenant",
            )
        if categoria and categoria.dre_subcategoria_id:
            return _resolver_dre_subcategoria_conta_pagar(
                db,
                tenant_id,
                dre_subcategoria_id=categoria.dre_subcategoria_id,
                categoria_id=None,
            )
        raise HTTPException(
            status_code=400,
            detail=(
                f"Categoria financeira '{categoria.nome}' nao possui vinculo com DRE. "
                "Vincule a categoria a uma subcategoria DRE antes de criar a conta a pagar."
            ),
        )

    raise HTTPException(
        status_code=400,
        detail=(
            "Informe uma categoria financeira vinculada a DRE ou uma subcategoria DRE valida "
            "para criar a conta a pagar."
        ),
    )


# ============================================================================
