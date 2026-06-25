"""Financeiro/DRE da baixa FULL por NF."""

from datetime import date
from decimal import Decimal
from typing import Optional
import re

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..domain.dre.lancamento_dre_sync import atualizar_dre_por_lancamento
from ..dre_plano_contas_models import DRECategoria, DRESubcategoria, NaturezaDRE
from ..financeiro_models import CategoriaFinanceira, ContaPagar, LancamentoManual
from ..models import User
from .common import _CANAL_LABELS, _texto_limpo


def _resolver_classificacao_tarifa_full_nf(
    db: Session,
    tenant_id,
    *,
    categoria_tarifa_id: Optional[int],
    dre_subcategoria_tarifa_id: Optional[int],
):
    if not categoria_tarifa_id:
        raise HTTPException(
            status_code=400,
            detail=(
                "Para lancar tarifa de envio no financeiro, selecione uma categoria de despesa "
                "vinculada a DRE. Sem essa classificacao a conta a pagar nao pode ser gerada."
            ),
        )

    categoria = (
        db.query(CategoriaFinanceira)
        .filter(
            CategoriaFinanceira.id == categoria_tarifa_id,
            CategoriaFinanceira.tenant_id == tenant_id,
            CategoriaFinanceira.tipo == "despesa",
            CategoriaFinanceira.ativo.is_(True),
        )
        .first()
    )
    if not categoria:
        raise HTTPException(
            status_code=400,
            detail="Categoria de despesa invalida ou nao pertence a este tenant.",
        )

    subcategoria_id = dre_subcategoria_tarifa_id or categoria.dre_subcategoria_id
    if not subcategoria_id:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Categoria de despesa '{categoria.nome}' nao possui vinculo com DRE. "
                "Ajuste a categoria financeira antes de baixar a NF com tarifa."
            ),
        )

    subcategoria = (
        db.query(DRESubcategoria)
        .join(DRECategoria, DRECategoria.id == DRESubcategoria.categoria_id)
        .filter(
            DRESubcategoria.id == subcategoria_id,
            DRESubcategoria.tenant_id == tenant_id,
            DRESubcategoria.ativo.is_(True),
            DRECategoria.tenant_id == tenant_id,
            DRECategoria.ativo.is_(True),
            DRECategoria.natureza == NaturezaDRE.DESPESA,
        )
        .first()
    )
    if not subcategoria:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Subcategoria DRE vinculada a '{categoria.nome}' e invalida, inativa "
                "ou nao e de despesa."
            ),
        )

    return categoria, subcategoria


def _criar_conta_pagar_tarifa_full_nf(
    db: Session,
    *,
    tenant_id,
    current_user: User,
    payload,
    categoria: CategoriaFinanceira,
    subcategoria: DRESubcategoria,
):
    valor = float(payload.tarifa_envio or 0)
    if valor <= 0:
        return None

    hoje = date.today()
    vencimento = payload.data_vencimento_tarifa or hoje
    canal = (payload.plataforma or "full").strip().lower() or "full"
    plataforma_label = _CANAL_LABELS.get(canal, payload.plataforma or "FULL")
    descricao = f"Tarifa envio FULL NF {payload.numero_nf}"
    observacoes = (
        f"Tarifa da operacao FULL ({plataforma_label}). "
        "Gerado na baixa de estoque por NF."
    )

    conta = ContaPagar(
        descricao=descricao,
        categoria_id=categoria.id,
        dre_subcategoria_id=subcategoria.id,
        canal=canal,
        valor_original=valor,
        valor_final=valor,
        data_emissao=hoje,
        data_vencimento=vencimento,
        status="pendente",
        documento=payload.numero_nf,
        observacoes=observacoes,
        user_id=current_user.id,
        tenant_id=tenant_id,
    )
    db.add(conta)
    db.flush()

    lancamento = LancamentoManual(
        tipo="saida",
        valor=valor,
        descricao=descricao,
        data_lancamento=hoje,
        data_competencia=vencimento,
        categoria_id=categoria.id,
        conta_bancaria_id=None,
        status="previsto",
        documento=payload.numero_nf,
        observacoes=f"Gerado automaticamente da conta a pagar #{conta.id}",
        gerado_automaticamente=True,
        confianca_ia=None,
        user_id=current_user.id,
        tenant_id=tenant_id,
    )
    db.add(lancamento)

    atualizar_dre_por_lancamento(
        db=db,
        tenant_id=tenant_id,
        dre_subcategoria_id=subcategoria.id,
        canal=canal,
        valor=Decimal(str(valor)),
        data_lancamento=vencimento,
        tipo_movimentacao="DESPESA",
    )

    return conta


def _observacao_conta_tarifa_full_nf_com_canal(
    observacoes: Optional[str],
    plataforma_label: str,
) -> str:
    texto = _texto_limpo(observacoes)
    novo_prefixo = f"Tarifa da operacao FULL ({plataforma_label})."
    if not texto:
        return f"{novo_prefixo} Gerado na baixa de estoque por NF."
    if re.search(r"Tarifa da operacao FULL \([^)]+\)\.", texto, flags=re.IGNORECASE):
        return re.sub(
            r"Tarifa da operacao FULL \([^)]+\)\.",
            novo_prefixo,
            texto,
            count=1,
            flags=re.IGNORECASE,
        )
    return f"{novo_prefixo} {texto}"


def _buscar_conta_tarifa_full_nf(db: Session, tenant_id, numero_nf: str):
    return (
        db.query(ContaPagar)
        .filter(
            ContaPagar.tenant_id == tenant_id,
            ContaPagar.documento == numero_nf,
            ContaPagar.descricao == f"Tarifa envio FULL NF {numero_nf}",
        )
        .first()
    )
