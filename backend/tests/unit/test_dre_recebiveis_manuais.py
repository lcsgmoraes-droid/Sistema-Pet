from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.dre_canais.agregacao import agregar_contas_receber_manuais_por_canal
from app.dre_canais.detalhes import _detalhes_recebiveis_manuais
from app.dre_canais.linhas import montar_linhas_dre_competencia
from app.dre_plano_contas_models import DRECategoria, DRESubcategoria, NaturezaDRE
from app.financeiro_models import ContaReceber
from app.tenancy.context import clear_current_tenant, set_current_tenant


def test_dre_inclui_recebivel_manual_sem_duplicar_venda():
    tenant_id = UUID("11111111-1111-1111-1111-111111111111")
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            DRECategoria.__table__,
            DRESubcategoria.__table__,
            ContaReceber.__table__,
        ],
    )
    db = sessionmaker(bind=engine)()
    set_current_tenant(tenant_id)
    try:
        receita = DRECategoria(
            id=1, tenant_id=tenant_id, nome="Receita", natureza=NaturezaDRE.RECEITA
        )
        despesa = DRECategoria(
            id=2, tenant_id=tenant_id, nome="Despesa", natureza=NaturezaDRE.DESPESA
        )
        db.add_all([receita, despesa])
        db.flush()
        db.add_all(
            [
                DRESubcategoria(
                    id=1,
                    tenant_id=tenant_id,
                    categoria_id=1,
                    nome="Outras receitas",
                    tipo_custo="DIRETO",
                    escopo_rateio="AMBOS",
                ),
                DRESubcategoria(
                    id=2,
                    tenant_id=tenant_id,
                    categoria_id=2,
                    nome="Energia",
                    tipo_custo="DIRETO",
                    escopo_rateio="AMBOS",
                ),
            ]
        )
        db.flush()

        def conta(id, subcategoria_id=1, **kwargs):
            return ContaReceber(
                id=id,
                tenant_id=tenant_id,
                user_id=1,
                descricao=f"Conta {id}",
                dre_subcategoria_id=subcategoria_id,
                canal="loja_fisica",
                valor_original=Decimal("20"),
                valor_final=kwargs.pop("valor_final", Decimal("20")),
                data_emissao=date(2026, 10, 5),
                data_vencimento=date(2026, 10, 10),
                status=kwargs.pop("status", "pendente"),
                **kwargs,
            )

        db.add_all(
            [
                conta(1, valor_final=Decimal("23")),
                conta(2, venda_id=123),
                conta(3, status="cancelado"),
                conta(4, status="parcelado"),
                conta(5, subcategoria_id=2),
                conta(6, status="cancelada"),
            ]
        )
        db.commit()

        dados = {}
        agregar_contas_receber_manuais_por_canal(db, 10, 2026, tenant_id, dados)
        linhas, totais = montar_linhas_dre_competencia(dados)

        assert dados["loja_fisica"]["receita_outras"] == Decimal("20")
        assert totais["receita_bruta"] == 20.0
        assert (
            next(linha for linha in linhas if linha.campo == "receita_outras").valor
            == 20.0
        )
        detalhes = _detalhes_recebiveis_manuais(db, 10, 2026, tenant_id, "loja_fisica")
        assert [(item.id, item.valor) for item in detalhes] == [
            ("conta-receber-1", 20.0)
        ]
    finally:
        clear_current_tenant()
        db.close()
        engine.dispose()
