from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Dict, Iterable

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.cargo_models import Cargo
from app.dre_canais.base import (
    _conta_valor,
    _decimal,
    _eh_folha_funcionarios_dre,
    _normalizar_canal,
    _texto_conta,
)
from app.ia.aba7_dre_detalhada_models import DREDetalheCanal
from app.models import Cliente
from app.services.remuneracao_service import calcular_composicao_remuneracao


def _periodo_datas(mes: int, ano: int) -> tuple[date, date]:
    inicio = date(ano, mes, 1)
    fim = date(ano + 1, 1, 1) if mes == 12 else date(ano, mes + 1, 1)
    return inicio, fim


def canal_provisao_folha(provisao: DREDetalheCanal) -> str:
    canal = str(getattr(provisao, "canal", "") or "").strip().lower()
    return "loja_fisica" if canal == "provisao" else _normalizar_canal(canal)


def _calcular_complemento_folha(
    total_estimado: Decimal,
    total_lancado: Decimal,
    total_provisoes: Decimal,
) -> Decimal:
    return max(
        Decimal("0"),
        _decimal(total_estimado) - _decimal(total_lancado) - _decimal(total_provisoes),
    ).quantize(Decimal("0.01"))


def _folha_gerencial_estimada(db: Session, tenant_id: str) -> dict:
    funcionarios = (
        db.query(Cliente, Cargo)
        .join(Cargo, Cliente.cargo_id == Cargo.id)
        .filter(
            Cliente.tenant_id == tenant_id,
            Cliente.tipo_cadastro == "funcionario",
            Cliente.ativo.is_(True),
            Cliente.cargo_id.isnot(None),
            Cargo.tenant_id == tenant_id,
            Cargo.ativo.is_(True),
        )
        .all()
    )

    total = sum(
        (
            _decimal(
                calcular_composicao_remuneracao(cargo, funcionario).get(
                    "custo_total_empresa", 0
                )
            )
            for funcionario, cargo in funcionarios
        ),
        Decimal("0"),
    )
    return {"total": total.quantize(Decimal("0.01")), "quantidade": len(funcionarios)}


def calcular_resumo_folha_gerencial(
    db: Session,
    mes: int,
    ano: int,
    tenant_id: str,
    contas: Iterable,
    subcategorias: Dict,
) -> dict:
    """Concilia contas, provisoes e cadastro de funcionarios sem duplicar valores."""
    folha_lancada_por_canal = defaultdict(lambda: Decimal("0"))
    for conta in contas:
        subcategoria = subcategorias.get(getattr(conta, "dre_subcategoria_id", None))
        texto = _texto_conta(conta, subcategoria)
        if _eh_folha_funcionarios_dre(texto):
            canal = _normalizar_canal(getattr(conta, "canal", None))
            folha_lancada_por_canal[canal] += _conta_valor(conta)

    inicio, fim_exclusivo = _periodo_datas(mes, ano)
    provisoes = (
        db.query(DREDetalheCanal)
        .filter(
            DREDetalheCanal.tenant_id == tenant_id,
            DREDetalheCanal.data_inicio < fim_exclusivo,
            DREDetalheCanal.data_fim >= inicio,
            or_(
                DREDetalheCanal.origem == "PROVISAO",
                DREDetalheCanal.canal == "provisao",
            ),
        )
        .all()
    )
    provisoes_por_canal = defaultdict(lambda: Decimal("0"))
    for provisao in provisoes:
        provisoes_por_canal[canal_provisao_folha(provisao)] += _decimal(
            getattr(provisao, "despesas_pessoal", 0)
        )

    estimativa = _folha_gerencial_estimada(db, tenant_id)
    complemento_loja = _calcular_complemento_folha(
        estimativa["total"],
        folha_lancada_por_canal["loja_fisica"],
        provisoes_por_canal["loja_fisica"],
    )
    ajustes_por_canal = dict(provisoes_por_canal)
    ajustes_por_canal["loja_fisica"] = (
        provisoes_por_canal["loja_fisica"] + complemento_loja
    )

    return {
        "estimado": estimativa["total"],
        "quantidade_funcionarios": estimativa["quantidade"],
        "folha_lancada_por_canal": dict(folha_lancada_por_canal),
        "provisoes_por_canal": dict(provisoes_por_canal),
        "provisoes": provisoes,
        "complemento_loja_fisica": complemento_loja,
        "ajustes_por_canal": ajustes_por_canal,
    }
