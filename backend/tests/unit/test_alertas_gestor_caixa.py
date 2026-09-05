import asyncio
from datetime import date, datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.alertas_gestor_routes import listar_alertas_gestor, router
from app.auth.dependencies import get_current_user_and_tenant
from app.caixa.conferencia import (
    referencia_fechamento,
    snapshot_abertura,
    totais_dinheiro,
)
from app.caixa_models import Caixa, MovimentacaoCaixa
from app.caixa_routes import (
    AbrirCaixaSchema,
    _ultimo_caixa_fechado,
    _validar_referencia_abertura,
)
from app.db import get_session
from app.caixa_routes import (
    abrir_caixa,
    fechar_caixa,
    obter_resumo_caixa,
    FecharCaixaSchema,
)
from app.empresa_config_geral_models import EmpresaConfigGeral
from app import (  # noqa: F401
    produtos_models,
    dre_plano_contas_models,
    ecommerceai_integration_models,
    ofertas_estudio_models,
)
from app.models import User, UserTenant
from app.vendas_models import Venda, VendaPagamento
from app.tenancy.context import set_current_tenant, clear_current_tenant

UTC = timezone.utc


@pytest.fixture
def dados_caixa():
    engine = create_engine("sqlite://")
    for model in (
        Caixa,
        User,
        UserTenant,
        Venda,
        MovimentacaoCaixa,
        VendaPagamento,
        EmpresaConfigGeral,
    ):
        model.__table__.create(engine)
    tenant = uuid4()
    outro = uuid4()
    set_current_tenant(tenant)
    with Session(engine) as db:
        yield db, tenant, outro
    clear_current_tenant()
    engine.dispose()


def inserir_caixa(db, tenant, id_, numero, usuario=10, **campos):
    values = dict(
        id=id_,
        tenant_id=tenant,
        numero_caixa=numero,
        usuario_id=usuario,
        usuario_nome=f"Operador {usuario}",
        data_abertura=datetime(2026, 9, 4, 9),
        data_fechamento=datetime(2026, 9, 4, 17),
        status="fechado",
        valor_abertura=100,
        valor_esperado=100,
        valor_informado=100,
        created_at=datetime(2026, 9, 4, 12, tzinfo=UTC),
        updated_at=datetime(2026, 9, 4, 20, tzinfo=UTC),
    )
    values.update(campos)
    db.execute(Caixa.__table__.insert().values(**values))
    return db.query(Caixa).filter(Caixa.id == id_).first()


def test_ultimo_fechamento_com_horarios_mistos_reproduz_incidente(dados_caixa):
    db, tenant, outro = dados_caixa
    inserir_caixa(
        db,
        tenant,
        1,
        1,
        usuario=62,
        valor_informado=539.65,
        data_fechamento=datetime(2026, 9, 4, 19, 59),
        updated_at=datetime(2026, 9, 4, 19, 59, tzinfo=UTC),
    )
    inserir_caixa(
        db,
        tenant,
        8,
        8,
        usuario=58,
        valor_informado=646.95,
        data_fechamento=datetime(2026, 9, 4, 17, 58),
        updated_at=datetime(2026, 9, 4, 20, 58, tzinfo=UTC),
    )
    inserir_caixa(
        db,
        outro,
        99,
        99,
        valor_informado=999,
        updated_at=datetime(2026, 9, 4, 23, tzinfo=UTC),
    )
    ultimo = _ultimo_caixa_fechado(
        db, tenant_id=tenant, usuario_id=49, compartilhado=True
    )
    assert ultimo.numero_caixa == 8
    assert referencia_fechamento(ultimo)["valor_fechamento"] == 646.95
    assert snapshot_abertura(ultimo, 647.45)["diferenca"] == 0.5
    assert (
        _ultimo_caixa_fechado(db, tenant_id=tenant, usuario_id=49, compartilhado=False)
        is None
    )


def test_instante_explicito_nao_muda_quando_metadado_e_atualizado(dados_caixa):
    db, tenant, _ = dados_caixa
    inserir_caixa(
        db,
        tenant,
        1,
        1,
        fechamento_em=datetime(2026, 9, 4, 19, tzinfo=UTC),
        updated_at=datetime(2026, 9, 5, 22, tzinfo=UTC),
    )
    inserir_caixa(db, tenant, 8, 8, fechamento_em=datetime(2026, 9, 4, 21, tzinfo=UTC))
    assert _ultimo_caixa_fechado(db, tenant_id=tenant, usuario_id=10).id == 8


def test_referencia_alterada_exige_nova_conferencia(dados_caixa):
    db, tenant, _ = dados_caixa
    caixa = inserir_caixa(db, tenant, 8, 8, valor_informado=646.95)
    ref = referencia_fechamento(caixa)
    dados = AbrirCaixaSchema(
        valor_abertura=647.45,
        caixa_anterior_id=8,
        valor_fechamento_anterior=646.95,
        data_fechamento_anterior=ref["data_fechamento"],
    )
    _validar_referencia_abertura(dados, caixa)
    caixa.valor_informado = 650
    with pytest.raises(HTTPException) as exc:
        _validar_referencia_abertura(dados, caixa)
    assert exc.value.status_code == 409
    with pytest.raises(HTTPException):
        _validar_referencia_abertura(
            AbrirCaixaSchema(valor_abertura=10, caixa_anterior_id=None), caixa
        )


def test_snapshot_preserva_contagem_apos_reabertura(dados_caixa):
    db, tenant, _ = dados_caixa
    caixa = inserir_caixa(db, tenant, 8, 8, valor_informado=646.95)
    snapshot = snapshot_abertura(caixa, 647.45)
    caixa.valor_informado = None
    assert snapshot["valor_fechamento"] == 646.95
    assert snapshot["diferenca"] == 0.5


def test_dinheiro_exclui_pix_e_cartao_e_subtrai_devolucao():
    movimentos = [
        SimpleNamespace(tipo=tipo, valor=valor, forma_pagamento=forma)
        for tipo, valor, forma in (
            ("venda", 100, "Dinheiro"),
            ("venda", 900, "PIX"),
            ("venda", 50, "Cartão"),
            ("suprimento", 10, None),
            ("sangria", 20, "Dinheiro"),
            ("despesa", 15, "Dinheiro"),
            ("transferencia", 5, "Dinheiro"),
            ("devolucao", 30, "Dinheiro"),
            ("despesa", 200, "PIX"),
        )
    ]
    totais = totais_dinheiro(50, movimentos)
    assert totais["saldo_atual"] == 90
    assert totais["vendas"] == 100
    assert totais["devolucoes"] == 30


def consultar(db, tenant, **filtros):
    return listar_alertas_gestor(
        data_inicio=date(2026, 9, 4),
        data_fim=date(2026, 9, 4),
        pagina=1,
        por_pagina=30,
        db=db,
        user_and_tenant=(SimpleNamespace(id=10), tenant),
        **filtros,
    )


def test_alertas_filtram_empresa_operador_tipo_e_fim_do_dia(dados_caixa):
    db, tenant, outro = dados_caixa
    inserir_caixa(
        db,
        tenant,
        8,
        8,
        valor_informado=101,
        usuario_fechamento_id=20,
        usuario_fechamento_nome="Gestora",
        updated_at=datetime(2026, 9, 5, 2, 59, tzinfo=UTC),
    )
    inserir_caixa(db, outro, 88, 88, valor_informado=900)
    inserir_caixa(
        db,
        tenant,
        9,
        9,
        status="aberto",
        data_fechamento=None,
        conferencia_abertura={
            "numero_caixa": 8,
            "valor_fechamento": 646.95,
            "valor_abertura": 647.45,
            "diferenca": 0.5,
        },
    )
    inserir_caixa(
        db,
        tenant,
        10,
        10,
        valor_informado=200,
        updated_at=datetime(2026, 9, 5, 3, 0, tzinfo=UTC),
    )
    response = consultar(db, tenant)
    assert response["total"] == 2
    assert response["resumo"]["diferenca_abertura"] == 1
    response = consultar(db, tenant, operador_id=20, tipo="diferenca_fechamento")
    assert response["total"] == 1
    assert response["itens"][0]["operador"] == "Gestora"
    assert response["itens"][0]["diferenca"] == 1


def test_historico_preserva_a_referencia_exibida_na_epoca(dados_caixa):
    db, tenant, _ = dados_caixa
    inserir_caixa(
        db,
        tenant,
        9,
        9,
        status="aberto",
        data_fechamento=None,
        observacoes_abertura="[Conferencia de abertura] Caixa anterior #1: R$ 539.65; abertura: R$ 647.45; diferenca: R$ +107.80.",
    )
    evento = consultar(db, tenant)["itens"][0]
    assert evento["origem"] == "observacao_historica"
    assert evento["valor_referencia"] == 539.65


def test_vendas_justificadas_e_paginacao(dados_caixa):
    db, tenant, outro = dados_caixa
    for id_, tenant_id, observacao, status in (
        (
            1,
            tenant,
            "JUSTIFICATIVA (Margem Critica): Desconto autorizado pela gerente",
            "finalizada",
        ),
        (2, tenant, "Entregar no endereço cadastrado", "finalizada"),
        (3, outro, "JUSTIFICATIVA (Margem Critica): Outra empresa", "finalizada"),
        (4, tenant, "JUSTIFICATIVA (Margem Critica): Venda ainda aberta", "aberta"),
    ):
        db.execute(
            Venda.__table__.insert().values(
                id=id_,
                tenant_id=tenant_id,
                numero_venda=str(id_),
                vendedor_id=10,
                user_id=10,
                subtotal=100,
                total=90,
                desconto_valor=10,
                data_venda=datetime(2026, 9, 4, 23, 59),
                status=status,
                observacoes=observacao,
            )
        )
    response = consultar(db, tenant, tipo="venda_justificada")
    assert response["total"] == 1
    assert response["itens"][0]["observacoes"] == "Desconto autorizado pela gerente"
    assert response["itens"][0]["valor_informado"] == 90


def test_rota_bloqueia_usuario_sem_permissao(monkeypatch):
    app = FastAPI()
    app.include_router(router)
    tenant = uuid4()
    app.dependency_overrides[get_current_user_and_tenant] = lambda: (
        SimpleNamespace(id=10),
        tenant,
    )
    app.dependency_overrides[get_session] = lambda: SimpleNamespace()
    chamadas = []

    def negar(db, user_id, permissao, tenant_id, **kwargs):
        chamadas.append((permissao, tenant_id))
        raise HTTPException(403, "Permissão negada")

    monkeypatch.setattr("app.security.permissions_decorator.check_permission", negar)
    with TestClient(app) as client:
        assert client.get("/alertas-gestor").status_code == 403
    assert chamadas == [("relatorios.gerencial", tenant)]


def test_resumo_fechamento_e_nova_abertura_preservam_o_mesmo_dinheiro(dados_caixa):
    db, tenant, _ = dados_caixa
    caixa = inserir_caixa(
        db,
        tenant,
        1,
        1,
        status="aberto",
        data_fechamento=None,
        valor_esperado=None,
        valor_informado=None,
    )
    for id_, tipo, valor, forma in (
        (1, "venda", 50, "Dinheiro"),
        (2, "venda", 500, "PIX"),
        (3, "devolucao", 10, "Dinheiro"),
    ):
        db.execute(
            MovimentacaoCaixa.__table__.insert().values(
                id=id_,
                tenant_id=tenant,
                caixa_id=caixa.id,
                tipo=tipo,
                valor=valor,
                forma_pagamento=forma,
                usuario_id=10,
                usuario_nome="Operador",
            )
        )
    user = SimpleNamespace(id=10, nome="Operador")
    resumo = obter_resumo_caixa(caixa.id, db=db, current_user_and_tenant=(user, tenant))
    assert resumo["totais"]["saldo_atual"] == 140
    resultado = asyncio.run(
        fechar_caixa.__wrapped__(
            caixa.id,
            FecharCaixaSchema(valor_informado=140),
            Request({"type": "http"}),
            db=db,
            current_user_and_tenant=(user, tenant),
        )
    )
    assert resultado["valor_esperado"] == 140
    assert resultado["diferenca"] == 0
    assert caixa.fechamento_em is not None
    novo = asyncio.run(
        abrir_caixa.__wrapped__(
            AbrirCaixaSchema(valor_abertura=141),
            Request({"type": "http"}),
            db=db,
            current_user_and_tenant=(user, tenant),
        )
    )
    assert novo["conferencia_abertura"]["caixa_id"] == 1
    assert novo["conferencia_abertura"]["valor_fechamento"] == 140
    assert novo["conferencia_abertura"]["diferenca"] == 1


def test_periodo_invalido_e_paginacao_sem_perder_totais(dados_caixa):
    db, tenant, _ = dados_caixa
    with pytest.raises(HTTPException) as erro:
        listar_alertas_gestor(
            data_inicio=date(2026, 1, 1),
            data_fim=date(2026, 9, 4),
            db=db,
            user_and_tenant=(SimpleNamespace(id=10), tenant),
        )
    assert erro.value.status_code == 422
    for id_ in range(1, 4):
        inserir_caixa(db, tenant, id_, id_, valor_informado=101)
    resultado = listar_alertas_gestor(
        data_inicio=date(2026, 9, 4),
        data_fim=date(2026, 9, 4),
        pagina=2,
        por_pagina=2,
        db=db,
        user_and_tenant=(SimpleNamespace(id=10), tenant),
    )
    assert resultado["total"] == 3
    assert len(resultado["itens"]) == 1
    assert resultado["resumo"]["diferenca_fechamento"] == 3
