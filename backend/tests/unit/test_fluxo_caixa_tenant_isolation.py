from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from app.financeiro.fluxo_caixa_routes import get_fluxo_caixa
from app.financeiro_models import LancamentoManual
from app.ia.aba5_models import FluxoCaixa
from app.tenancy.context import set_current_tenant
from app.vendas_models import Venda


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


def _criar_venda_finalizada(
    db_session,
    *,
    tenant_id,
    user_id: int,
    numero_venda: str,
    valor: str,
) -> Venda:
    set_current_tenant(UUID(str(tenant_id)))
    venda = Venda(
        tenant_id=UUID(str(tenant_id)),
        user_id=user_id,
        vendedor_id=user_id,
        numero_venda=numero_venda,
        subtotal=Decimal(valor),
        total=Decimal(valor),
        status="finalizada",
        data_venda=datetime(2026, 6, 10, 10, 0, 0),
        canal="loja_fisica",
    )
    db_session.add(venda)
    db_session.flush()
    return venda


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


def test_fluxo_caixa_nao_duplica_venda_quando_existe_lancamento_manual(
    db_session, tenant_factory, user_factory
):
    FluxoCaixa.__table__.create(bind=db_session.get_bind(), checkfirst=True)

    tenant = tenant_factory(nome="Atacadao")
    usuario = user_factory(tenant_id=tenant.id, email="fluxo.duplicidade@test.com")

    venda_com_lancamento = _criar_venda_finalizada(
        db_session,
        tenant_id=tenant.id,
        user_id=usuario.id,
        numero_venda="202606100001",
        valor="100.00",
    )
    _criar_lancamento_manual(
        db_session,
        tenant_id=tenant.id,
        user_id=usuario.id,
        descricao="Venda 202606100001 - A receber",
        valor="100.00",
        status="realizado",
    ).documento = f"VENDA-{venda_com_lancamento.id}"

    venda_sem_lancamento = _criar_venda_finalizada(
        db_session,
        tenant_id=tenant.id,
        user_id=usuario.id,
        numero_venda="202606100002",
        valor="80.00",
    )

    db_session.flush()
    set_current_tenant(UUID(str(tenant.id)))

    resposta = get_fluxo_caixa(
        data_inicio="2026-06-01",
        data_fim="2026-06-30",
        db=db_session,
        current_user_and_tenant=(usuario, UUID(str(tenant.id))),
    )

    movimentos_por_origem = {
        (mov.origem_tipo, mov.origem_id): mov for mov in resposta.movimentacoes
    }

    assert ("venda", venda_com_lancamento.id) not in movimentos_por_origem
    assert any(
        mov.origem_tipo == "lancamento_manual" and mov.valor == 100.0
        for mov in resposta.movimentacoes
    )
    assert ("venda", venda_sem_lancamento.id) in movimentos_por_origem
    assert resposta.total_realizado_entradas == 180.0
