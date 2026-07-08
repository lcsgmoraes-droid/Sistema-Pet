from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from app.financeiro.fluxo_caixa_routes import get_fluxo_caixa
from app.financeiro_models import ContaPagar, ContaReceber, LancamentoManual
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


def _criar_conta_pagar_pendente(
    db_session,
    *,
    tenant_id,
    user_id: int,
    descricao: str,
    valor: str,
) -> ContaPagar:
    set_current_tenant(UUID(str(tenant_id)))
    conta = ContaPagar(
        tenant_id=UUID(str(tenant_id)),
        user_id=user_id,
        descricao=descricao,
        valor_original=Decimal(valor),
        valor_pago=Decimal("0.00"),
        valor_desconto=Decimal("0.00"),
        valor_juros=Decimal("0.00"),
        valor_multa=Decimal("0.00"),
        valor_final=Decimal(valor),
        data_emissao=date(2026, 6, 1),
        data_vencimento=date(2026, 6, 20),
        status="pendente",
    )
    db_session.add(conta)
    db_session.flush()
    return conta


def _criar_conta_receber_pendente(
    db_session,
    *,
    tenant_id,
    user_id: int,
    descricao: str,
    valor_final: str,
    valor_recebido: str = "0.00",
    status: str = "pendente",
) -> ContaReceber:
    set_current_tenant(UUID(str(tenant_id)))
    conta = ContaReceber(
        tenant_id=UUID(str(tenant_id)),
        user_id=user_id,
        descricao=descricao,
        cliente_id=None,
        categoria_id=None,
        dre_subcategoria_id=1,
        canal="loja_fisica",
        valor_original=Decimal(valor_final),
        valor_recebido=Decimal(valor_recebido),
        valor_desconto=Decimal("0.00"),
        valor_juros=Decimal("0.00"),
        valor_multa=Decimal("0.00"),
        valor_final=Decimal(valor_final),
        data_emissao=date(2026, 6, 1),
        data_vencimento=date(2026, 6, 18),
        status=status,
    )
    db_session.add(conta)
    db_session.flush()
    return conta


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


def test_fluxo_caixa_inclui_contas_pagar_do_tenant_mesmo_de_outro_usuario(
    db_session, tenant_factory, user_factory
):
    FluxoCaixa.__table__.create(bind=db_session.get_bind(), checkfirst=True)

    tenant = tenant_factory(nome="Atacadao")
    gestor = user_factory(tenant_id=tenant.id, email="gestor.fluxo@test.com")
    financeiro = user_factory(tenant_id=tenant.id, email="financeiro.fluxo@test.com")
    outro_tenant = tenant_factory(nome="Clinica Sao Jose")
    usuario_outro = user_factory(
        tenant_id=outro_tenant.id, email="financeiro.outro@test.com"
    )

    conta_tenant = _criar_conta_pagar_pendente(
        db_session,
        tenant_id=tenant.id,
        user_id=financeiro.id,
        descricao="Fornecedor do Atacadao",
        valor="321.45",
    )
    _criar_conta_pagar_pendente(
        db_session,
        tenant_id=outro_tenant.id,
        user_id=usuario_outro.id,
        descricao="Fornecedor de outro tenant",
        valor="999.99",
    )

    set_current_tenant(UUID(str(tenant.id)))
    resposta = get_fluxo_caixa(
        data_inicio="2026-06-01",
        data_fim="2026-06-30",
        db=db_session,
        current_user_and_tenant=(gestor, UUID(str(tenant.id))),
    )

    movimentos_por_origem = {
        (mov.origem_tipo, mov.origem_id): mov for mov in resposta.movimentacoes
    }

    assert ("conta_pagar", conta_tenant.id) in movimentos_por_origem
    assert movimentos_por_origem[("conta_pagar", conta_tenant.id)].valor == 321.45
    assert all(mov.valor != 999.99 for mov in resposta.movimentacoes)


def test_fluxo_caixa_inclui_contas_receber_abertas_sem_duplicar_fluxo_previsto(
    db_session, tenant_factory, user_factory
):
    FluxoCaixa.__table__.create(bind=db_session.get_bind(), checkfirst=True)

    tenant = tenant_factory(nome="Atacadao")
    gestor = user_factory(tenant_id=tenant.id, email="gestor.receber.fluxo@test.com")
    financeiro = user_factory(
        tenant_id=tenant.id, email="financeiro.receber.fluxo@test.com"
    )
    outro_tenant = tenant_factory(nome="Clinica Sao Jose")
    usuario_outro = user_factory(
        tenant_id=outro_tenant.id, email="financeiro.receber.outro@test.com"
    )

    conta_tenant = _criar_conta_receber_pendente(
        db_session,
        tenant_id=tenant.id,
        user_id=financeiro.id,
        descricao="Cliente Atacadao parcial",
        valor_final="210.00",
        valor_recebido="60.00",
        status="parcial",
    )
    conta_ja_lancada = _criar_conta_receber_pendente(
        db_session,
        tenant_id=tenant.id,
        user_id=financeiro.id,
        descricao="Cliente Atacadao ja no fluxo",
        valor_final="50.00",
    )
    _criar_conta_receber_pendente(
        db_session,
        tenant_id=outro_tenant.id,
        user_id=usuario_outro.id,
        descricao="Cliente de outro tenant",
        valor_final="999.99",
    )

    set_current_tenant(UUID(str(tenant.id)))
    db_session.add(
        FluxoCaixa(
            tenant_id=UUID(str(tenant.id)),
            usuario_id=financeiro.id,
            tipo="entrada",
            categoria="Recebimentos",
            descricao="Previsao ja existente",
            valor=50.0,
            data_prevista=datetime(2026, 6, 18, 10, 0, 0),
            status="previsto",
            origem_tipo="conta_receber",
            origem_id=conta_ja_lancada.id,
        )
    )
    db_session.flush()

    set_current_tenant(UUID(str(tenant.id)))
    resposta = get_fluxo_caixa(
        data_inicio="2026-06-01",
        data_fim="2026-06-30",
        db=db_session,
        current_user_and_tenant=(gestor, UUID(str(tenant.id))),
    )

    movimentos_por_origem = [
        mov for mov in resposta.movimentacoes if mov.origem_tipo == "conta_receber"
    ]
    movimentos_chave = {
        (mov.origem_tipo, mov.origem_id): mov for mov in movimentos_por_origem
    }

    assert ("conta_receber", conta_tenant.id) in movimentos_chave
    assert movimentos_chave[("conta_receber", conta_tenant.id)].valor == 150.0
    assert movimentos_chave[("conta_receber", conta_tenant.id)].status == "previsto"
    assert movimentos_chave[("conta_receber", conta_tenant.id)].tipo == "entrada"
    assert (
        sum(1 for mov in movimentos_por_origem if mov.origem_id == conta_ja_lancada.id)
        == 1
    )
    assert all(mov.valor != 999.99 for mov in resposta.movimentacoes)
