from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from app.financeiro.fluxo_caixa_routes import get_fluxo_caixa
from app.financeiro_models import LancamentoManual
from app.ia.aba5_models import FluxoCaixa
from app.tenancy.context import set_current_tenant


ROOT = Path(__file__).resolve().parents[2]


def test_fluxo_caixa_routes_exige_filtros_explicitos_de_tenant():
    source = (ROOT / "app" / "financeiro" / "fluxo_caixa_routes.py").read_text(
        encoding="utf-8"
    )

    assert "LancamentoManual.tenant_id == tenant_id" in source
    assert "ContaPagar.tenant_id == tenant_id" in source
    assert "ContaReceber.tenant_id == tenant_id" in source
    assert "FluxoCaixa.tenant_id == tenant_id" in source


def _criar_lancamento_manual(
    db_session,
    *,
    tenant_id,
    user_id: int,
    descricao: str,
    valor: str,
    status: str,
) -> LancamentoManual:
    set_current_tenant(UUID(str(tenant_id)))
    lancamento = LancamentoManual(
        tenant_id=UUID(str(tenant_id)),
        user_id=user_id,
        tipo="entrada",
        valor=Decimal(valor),
        descricao=descricao,
        data_lancamento=date(2026, 6, 10),
        status=status,
    )
    db_session.add(lancamento)
    db_session.flush()
    return lancamento


def test_fluxo_caixa_filtra_lancamentos_manuais_pelo_tenant(
    db_session, tenant_factory, user_factory
):
    FluxoCaixa.__table__.create(bind=db_session.get_bind(), checkfirst=True)

    tenant_atacadao = tenant_factory(nome="Atacadao")
    usuario_atacadao = user_factory(
        tenant_id=tenant_atacadao.id, email="atacadao.test@example.com"
    )
    funcionario_atacadao = user_factory(
        tenant_id=tenant_atacadao.id, email="funcionario.atacadao.test@example.com"
    )
    tenant_clinica = tenant_factory(nome="Clinica Sao Jose")
    usuario_clinica = user_factory(
        tenant_id=tenant_clinica.id, email="clinica.test@example.com"
    )

    _criar_lancamento_manual(
        db_session,
        tenant_id=tenant_atacadao.id,
        user_id=usuario_atacadao.id,
        descricao="Entrada Atacadao realizada",
        valor="100.00",
        status="realizado",
    )
    _criar_lancamento_manual(
        db_session,
        tenant_id=tenant_atacadao.id,
        user_id=usuario_atacadao.id,
        descricao="Entrada Atacadao prevista",
        valor="50.00",
        status="previsto",
    )
    _criar_lancamento_manual(
        db_session,
        tenant_id=tenant_atacadao.id,
        user_id=funcionario_atacadao.id,
        descricao="Entrada funcionario Atacadao",
        valor="25.00",
        status="realizado",
    )
    _criar_lancamento_manual(
        db_session,
        tenant_id=tenant_clinica.id,
        user_id=usuario_clinica.id,
        descricao="Entrada Clinica realizada",
        valor="999.00",
        status="realizado",
    )
    _criar_lancamento_manual(
        db_session,
        tenant_id=tenant_clinica.id,
        user_id=usuario_clinica.id,
        descricao="Entrada Clinica prevista",
        valor="77.00",
        status="previsto",
    )

    set_current_tenant(UUID(str(tenant_atacadao.id)))
    resposta = get_fluxo_caixa(
        data_inicio="2026-06-01",
        data_fim="2026-06-30",
        db=db_session,
        current_user_and_tenant=(usuario_atacadao, UUID(str(tenant_atacadao.id))),
    )

    descricoes = {mov.descricao for mov in resposta.movimentacoes}

    assert "Entrada Atacadao realizada" in descricoes
    assert "Entrada Atacadao prevista" in descricoes
    assert "Entrada funcionario Atacadao" in descricoes
    assert "Entrada Clinica realizada" not in descricoes
    assert "Entrada Clinica prevista" not in descricoes
    assert resposta.total_realizado_entradas == 125.0
    assert resposta.total_previsto_entradas == 50.0
