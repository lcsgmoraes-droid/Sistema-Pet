"""Helpers financeiros para notas de entrada."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.financeiro.contas_pagar_classificacao import aplicar_classificacao_aprendida_conta_pagar
from app.financeiro_models import ContaPagar, TipoDespesa
from app.produtos_models import NotaEntrada

logger = logging.getLogger(__name__)


def _obter_tipo_produto_revenda_id(db: Session, tenant_id) -> Optional[int]:
    nomes_prioritarios = [
        "Produto para Revenda",
        "Fornecedor de Produto para Revenda",
    ]
    for nome in nomes_prioritarios:
        tipo = db.query(TipoDespesa).filter(
            TipoDespesa.tenant_id == tenant_id,
            func.lower(TipoDespesa.nome) == nome.lower(),
            TipoDespesa.ativo.is_(True),
        ).first()
        if tipo:
            return tipo.id

    tipo = db.query(TipoDespesa).filter(
        TipoDespesa.tenant_id == tenant_id,
        TipoDespesa.nome.ilike("%produto%revenda%"),
        TipoDespesa.ativo.is_(True),
    ).order_by(TipoDespesa.nome.asc()).first()
    return tipo.id if tipo else None


def criar_contas_pagar_da_nota(nota: NotaEntrada, dados_xml: dict, db: Session, user_id: int, tenant_id: str) -> List[int]:
    """
    Cria contas a pagar automaticamente com base nas duplicatas do XML.

    Retorna lista de IDs das contas criadas.
    """
    logger.info("Gerando contas a pagar para nota %s...", nota.numero_nota)

    contas_criadas = []
    duplicatas = dados_xml.get("duplicatas", [])

    if not duplicatas:
        logger.info("Sem duplicatas no XML, criando conta unica com vencimento +30 dias")
        duplicatas = [{
            "numero": f"{nota.numero_nota}-1",
            "vencimento": datetime.now() + timedelta(days=30),
            "valor": nota.valor_total,
        }]

    total_duplicatas = len(duplicatas)
    eh_parcelado = total_duplicatas > 1
    tipo_produto_revenda_id = _obter_tipo_produto_revenda_id(db, tenant_id)

    for idx, dup in enumerate(duplicatas, 1):
        try:
            valor_reais = Decimal(str(dup["valor"]))

            conta = ContaPagar(
                fornecedor_id=nota.fornecedor_id,
                tipo_despesa_id=tipo_produto_revenda_id,
                descricao=f"NF-e {nota.numero_nota} - Parcela {dup['numero']}",
                valor_original=valor_reais,
                valor_final=valor_reais,
                valor_pago=Decimal("0"),
                data_emissao=nota.data_emissao,
                data_vencimento=dup["vencimento"],
                status="pendente",
                eh_parcelado=eh_parcelado,
                numero_parcela=idx if eh_parcelado else None,
                total_parcelas=total_duplicatas if eh_parcelado else None,
                nota_entrada_id=nota.id,
                nfe_numero=str(nota.numero_nota),
                documento=dup.get("numero", ""),
                percentual_online=nota.percentual_online or 0,
                percentual_loja=nota.percentual_loja or 100,
                user_id=user_id,
                tenant_id=tenant_id,
            )
            aplicar_classificacao_aprendida_conta_pagar(db, tenant_id, conta)

            db.add(conta)
            db.flush()

            contas_criadas.append(conta.id)

            logger.info(
                "Conta criada: %s - R$ %.2f - Venc: %s",
                dup["numero"],
                dup["valor"],
                dup["vencimento"].strftime("%d/%m/%Y"),
            )
        except Exception as exc:
            logger.error("Erro ao criar conta da duplicata %s: %s", dup.get("numero"), exc)
            raise

    logger.info("Total de contas criadas: %s", len(contas_criadas))
    return contas_criadas
