"""Fronteiras da vigencia no PostgreSQL local/CI, sempre com rollback."""

from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import os
from threading import Event
import time
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app import caixa_models, financeiro_models, produto_identidade_models  # noqa: F401
from app.comissoes_config_service import (
    buscar_configuracao_comissao,
    calcular_comissao_fixa_parcela,
)
from app.comissoes_models import ComissaoConfiguracao
from app.models import Cliente, Tenant, User
from app.produtos_models import Produto
from app.services.pessoa_merge_service import executar_fusao_pessoas
from app.tenancy.context import clear_current_tenant, set_current_tenant
from app.vendas_models import Venda


@pytest.fixture
def caso():
    url_ci = os.getenv("COMISSOES_VIGENCIA_TEST_POSTGRES_URL")
    url = url_ci or os.getenv("COREPET_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Informe COREPET_TEST_POSTGRES_URL de um PostgreSQL DEV local")
    destino = make_url(url)
    assert destino.get_backend_name() == "postgresql"
    assert destino.host in {"localhost", "127.0.0.1", "::1"}
    if url_ci:
        assert os.getenv("ENVIRONMENT", "").lower() in {"test", "testing"}
        nome_banco = str(destino.database)
        assert nome_banco.endswith(("_test", "_ci")) or nome_banco.startswith(
            "petshop_migration_smoke_"
        )
    else:
        assert str(destino.database).endswith("_dev")
    engine = create_engine(url)
    try:
        if not inspect(engine).has_table("comissoes_configuracao_versoes"):
            if url_ci:
                pytest.fail("Banco efemero CI precisa estar migrado ate A4")
            pytest.skip("Aplique A4 no DEV antes do ensaio de vigencia")
        with Session(engine) as db:
            try:
                tenant = uuid4()
                set_current_tenant(tenant)
                sufixo = uuid4().hex[:10]
                empresa = Tenant(
                    id=str(tenant),
                    name=f"Ensaio vigencia {sufixo}",
                    name_normalized=f"ensaio vigencia {sufixo}",
                )
                usuario = User(
                    tenant_id=tenant,
                    username=f"vigencia-{sufixo}",
                    nome="Operador ficticio",
                    is_active=True,
                )
                db.add(empresa)
                db.flush()
                db.add(usuario)
                db.flush()
                funcionario = Cliente(
                    tenant_id=tenant,
                    user_id=usuario.id,
                    codigo=f"VG-{sufixo}",
                    nome="Comissionado ficticio",
                    ativo=True,
                    is_funcionario=True,
                    parceiro_ativo=True,
                )
                produto = Produto(
                    tenant_id=tenant,
                    user_id=usuario.id,
                    codigo=f"VP-{sufixo}",
                    nome="Produto ficticio vigencia",
                    tipo_produto="SIMPLES",
                )
                db.add_all([funcionario, produto])
                db.flush()
                yield SimpleNamespace(
                    db=db,
                    tenant=tenant,
                    usuario=usuario,
                    funcionario=funcionario,
                    produto=produto,
                    sufixo=sufixo,
                )
            finally:
                db.rollback()
                clear_current_tenant()
        with engine.connect() as connection:
            assert (
                connection.execute(
                    text("SELECT count(*) FROM clientes WHERE codigo=:codigo"),
                    {"codigo": f"VG-{sufixo}"},
                ).scalar_one()
                == 0
            )
    finally:
        engine.dispose()


def _configurar(caso, valor, *, geral=False):
    config = ComissaoConfiguracao(
        tenant_id=caso.tenant,
        funcionario_id=caso.funcionario.id,
        tipo="geral" if geral else "produto",
        referencia_id=0 if geral else caso.produto.id,
        tipo_calculo="fixo",
        percentual=0,
        valor_fixo=valor,
        ativo=True,
    )
    caso.db.add(config)
    caso.db.flush()
    return config


def _venda(caso, numero, data_comercial, *, ancora_forjada=None):
    venda = Venda(
        tenant_id=caso.tenant,
        user_id=caso.usuario.id,
        vendedor_id=caso.usuario.id,
        funcionario_id=caso.funcionario.id,
        numero_venda=f"VG-{caso.sufixo}-{numero}",
        subtotal=10,
        total=10,
        status="aberta",
        data_venda=data_comercial,
    )
    if ancora_forjada is not None:
        venda.comissao_ancora_em = ancora_forjada
    caso.db.add(venda)
    caso.db.flush()
    caso.db.refresh(venda)
    assert venda.comissao_ancora_em.tzinfo is not None
    return venda


def _vigente(caso, instante, *, tenant=None, funcionario_id=None):
    return buscar_configuracao_comissao(
        caso.db,
        funcionario_id or caso.funcionario.id,
        caso.produto.id,
        tenant_id=tenant or caso.tenant,
        criada_em=instante,
    )


def _ultimo_instante(caso, config):
    return caso.db.execute(
        text(
            "SELECT vigente_desde FROM comissoes_configuracao_versoes WHERE tenant_id=:tenant AND configuracao_id=:config ORDER BY vigente_desde DESC, id DESC LIMIT 1"
        ),
        {"tenant": caso.tenant, "config": config.id},
    ).scalar_one()


def test_criacao_tecnica_define_regra_em_fuso_local_e_todas_as_parcelas(caso):
    caso.db.execute(text("SET LOCAL TIME ZONE 'America/Sao_Paulo'"))
    config = _configurar(caso, 3)
    antiga = _venda(caso, 1, datetime(2035, 1, 1))
    corte_antigo = _ultimo_instante(caso, config)
    config.valor_fixo = 5
    caso.db.flush()
    corte_novo = _ultimo_instante(caso, config)
    nova = _venda(
        caso,
        2,
        datetime(2001, 1, 1),
        ancora_forjada=datetime(2000, 1, 1, tzinfo=timezone.utc),
    )
    assert corte_novo > corte_antigo, (
        "Escritas na mesma transacao precisam de instantes distintos"
    )
    assert antiga.comissao_ancora_em < corte_novo <= nova.comissao_ancora_em
    for instante in (
        antiga.comissao_ancora_em,
        antiga.comissao_ancora_em.astimezone(timezone.utc),
    ):
        assert Decimal(str(_vigente(caso, instante)["valor_fixo"])) == 3
    for deslocamento, esperado in ((-1, 3), (0, 5), (1, 5)):
        instante = corte_novo + timedelta(microseconds=deslocamento)
        assert Decimal(str(_vigente(caso, instante)["valor_fixo"])) == esperado
    config.valor_fixo = 7
    caso.db.flush()
    for venda, esperado in ((antiga, Decimal("3")), (nova, Decimal("5"))):
        parcelas = []
        for anterior in (0, 5):
            regra = _vigente(caso, venda.comissao_ancora_em)
            parcelas.append(
                calcular_comissao_fixa_parcela(regra["valor_fixo"], 5, 10, anterior)
            )
        assert sum(parcelas) == esperado
    # Nem a competencia comercial nem created_at legado alteram a ancora tecnica.
    ancora = antiga.comissao_ancora_em
    antiga.data_venda = datetime(1999, 1, 1)
    antiga.created_at = datetime(2099, 1, 1)
    caso.db.flush()
    caso.db.refresh(antiga)
    assert antiga.comissao_ancora_em == ancora
    assert Decimal(str(_vigente(caso, ancora)["valor_fixo"])) == 3
    with pytest.raises(DBAPIError) as erro:
        with caso.db.begin_nested():
            caso.db.execute(
                text(
                    "UPDATE vendas SET comissao_ancora_em=clock_timestamp() + interval '1 year' WHERE tenant_id=:tenant AND id=:id"
                ),
                {"tenant": caso.tenant, "id": antiga.id},
            )
    assert erro.value.orig.pgcode == "23514"
    caso.db.refresh(antiga)
    assert antiga.comissao_ancora_em == ancora


@pytest.mark.parametrize("excluir", [False, True])
def test_regra_removida_nao_apaga_historico_e_faz_fallback_hierarquico(caso, excluir):
    _configurar(caso, 1, geral=True)
    especifica = _configurar(caso, 3)
    anterior = _venda(caso, 1, datetime(2026, 1, 1))
    if excluir:
        caso.db.delete(especifica)
    else:
        especifica.ativo = False
    caso.db.flush()
    posterior = _venda(caso, 2, datetime(2020, 1, 1))
    assert Decimal(str(_vigente(caso, anterior.comissao_ancora_em)["valor_fixo"])) == 3
    assert Decimal(str(_vigente(caso, posterior.comissao_ancora_em)["valor_fixo"])) == 1


def test_versoes_isoladas_por_tenant_e_migradas_na_fusao_da_pessoa(caso):
    _configurar(caso, 3)
    venda = _venda(caso, 1, datetime(2026, 1, 1))
    outro_tenant = uuid4()
    set_current_tenant(outro_tenant)
    assert _vigente(caso, venda.comissao_ancora_em, tenant=outro_tenant) is None
    set_current_tenant(caso.tenant)
    principal = Cliente(
        tenant_id=caso.tenant,
        user_id=caso.usuario.id,
        codigo=f"VM-{caso.sufixo}",
        nome="Principal ficticio",
        ativo=True,
    )
    caso.db.add(principal)
    caso.db.flush()
    resultado = executar_fusao_pessoas(
        caso.db,
        tenant_id=caso.tenant,
        principal_id=principal.id,
        duplicado_id=caso.funcionario.id,
        decisoes_campos={},
        user_id=caso.usuario.id,
        commit=False,
    )
    assert resultado["success"]
    caso.db.refresh(venda)
    assert venda.funcionario_id == principal.id
    assert (
        Decimal(
            str(
                _vigente(caso, venda.comissao_ancora_em, funcionario_id=principal.id)[
                    "valor_fixo"
                ]
            )
        )
        == 3
    )
    assert (
        caso.db.execute(
            text(
                "SELECT count(*) FROM comissoes_configuracao_versoes WHERE tenant_id=:tenant AND funcionario_id=:duplicado"
            ),
            {"tenant": caso.tenant, "duplicado": caso.funcionario.id},
        ).scalar_one()
        == 0
    )
    seguranca = caso.db.execute(
        text(
            "SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE oid='comissoes_configuracao_versoes'::regclass"
        )
    ).one()
    assert seguranca == (True, True)
    politicas = caso.db.execute(
        text(
            "SELECT qual, with_check FROM pg_policies WHERE schemaname='public' AND tablename='comissoes_configuracao_versoes'"
        )
    ).all()
    assert politicas and all(
        "app.tenant_id" in (qual or "") and "app.tenant_id" in (check or "")
        for qual, check in politicas
    )


def _contexto_conexao(db, tenant):
    set_current_tenant(tenant)
    db.execute(
        text("SELECT set_config('app.tenant_id', :tenant, true)"),
        {"tenant": str(tenant)},
    )
    db.execute(text("SET LOCAL statement_timeout = '8s'"))


@pytest.fixture
def concorrente(caso):
    # Duas conexoes precisam enxergar o seed confirmado. Permitido somente nos
    # bancos descartaveis de teste; o caminho *_dev continua so com rollback.
    if not os.getenv("COMISSOES_VIGENCIA_TEST_POSTGRES_URL"):
        pytest.skip("Concorrencia exige URL explicita de banco efemero de teste")
    config_a = _configurar(caso, 3)
    dados_a = SimpleNamespace(
        tenant=caso.tenant,
        user_id=caso.usuario.id,
        funcionario_id=caso.funcionario.id,
        config_id=config_a.id,
        sufixo=caso.sufixo,
    )
    tenant_b = uuid4()
    _contexto_conexao(caso.db, tenant_b)
    empresa_b = Tenant(
        id=str(tenant_b),
        name=f"Outra vigencia {caso.sufixo}",
        name_normalized=f"outra vigencia {caso.sufixo}",
    )
    caso.db.add(empresa_b)
    caso.db.flush()
    user_b = User(
        tenant_id=tenant_b, username=f"concorrente-{caso.sufixo}", is_active=True
    )
    caso.db.add(user_b)
    caso.db.flush()
    pessoa_b = Cliente(
        tenant_id=tenant_b, user_id=user_b.id, nome="Outra pessoa ficticia", ativo=True
    )
    caso.db.add(pessoa_b)
    caso.db.flush()
    config_b = ComissaoConfiguracao(
        tenant_id=tenant_b,
        funcionario_id=pessoa_b.id,
        tipo="geral",
        referencia_id=0,
        tipo_calculo="fixo",
        percentual=0,
        valor_fixo=9,
        ativo=True,
    )
    caso.db.add(config_b)
    caso.db.flush()
    dados_b = SimpleNamespace(tenant=tenant_b, config_id=config_b.id)
    caso.db.commit()
    _contexto_conexao(caso.db, caso.tenant)
    try:
        yield SimpleNamespace(
            caso=caso, a=dados_a, b=dados_b, engine=caso.db.get_bind()
        )
    finally:
        caso.db.rollback()
        for tenant in (dados_a.tenant, dados_b.tenant):
            _contexto_conexao(caso.db, tenant)
            for tabela in (
                "vendas",
                "comissoes_configuracao",
                "comissoes_configuracao_versoes",
                "produtos",
                "clientes",
                "users",
            ):
                caso.db.execute(
                    text(f"DELETE FROM {tabela} WHERE tenant_id=:tenant"),
                    {"tenant": tenant},
                )
            caso.db.execute(
                text("DELETE FROM tenants WHERE id::text=:tenant"),
                {"tenant": str(tenant)},
            )
        caso.db.commit()


def _operacao_concorrente(engine, dados, *, numero=None, sinal=None):
    with Session(engine) as db:
        try:
            _contexto_conexao(db, dados.tenant)
            if sinal:
                sinal.pid = db.execute(text("SELECT pg_backend_pid()")).scalar_one()
                sinal.iniciada.set()
            if numero is None:
                db.execute(
                    text(
                        "UPDATE comissoes_configuracao SET valor_fixo=5 WHERE tenant_id=:tenant AND id=:id"
                    ),
                    {"tenant": dados.tenant, "id": dados.config_id},
                )
                resultado = None
            else:
                venda = Venda(
                    tenant_id=dados.tenant,
                    user_id=dados.user_id,
                    vendedor_id=dados.user_id,
                    funcionario_id=dados.funcionario_id,
                    numero_venda=f"VC-{dados.sufixo}-{numero}",
                    subtotal=10,
                    total=10,
                    status="aberta",
                )
                db.add(venda)
                db.flush()
                resultado = venda.comissao_ancora_em
            db.commit()
            return resultado
        finally:
            if sinal:
                sinal.concluida.set()
            clear_current_tenant()


def _aguardar_advisory(engine, sinal):
    assert sinal.iniciada.wait(3), "Conexao de teste nao iniciou"
    limite = time.monotonic() + 3
    with engine.connect() as observador:
        while time.monotonic() < limite:
            bloqueado = observador.execute(
                text(
                    "SELECT EXISTS (SELECT 1 FROM pg_locks WHERE pid=:pid AND locktype='advisory' AND NOT granted)"
                ),
                {"pid": sinal.pid},
            ).scalar_one()
            if bloqueado:
                return
            if sinal.concluida.is_set():
                break
            time.sleep(0.01)
    pytest.fail("Operacao concorrente nao aguardou o commit sob lock advisory")


def test_configuracao_pendente_bloqueia_nova_venda_mas_nao_outro_tenant(concorrente):
    ctx = concorrente
    ctx.caso.db.execute(
        text(
            "UPDATE comissoes_configuracao SET valor_fixo=5 WHERE tenant_id=:tenant AND id=:id"
        ),
        {"tenant": ctx.a.tenant, "id": ctx.a.config_id},
    )
    sinal = SimpleNamespace(iniciada=Event(), concluida=Event(), pid=None)
    with ThreadPoolExecutor(max_workers=2) as pool:
        venda = pool.submit(
            _operacao_concorrente, ctx.engine, ctx.a, numero=1, sinal=sinal
        )
        try:
            _aguardar_advisory(ctx.engine, sinal)
            # Outra empresa nao participa do lock da configuracao A.
            pool.submit(_operacao_concorrente, ctx.engine, ctx.b).result(timeout=3)
            ctx.caso.db.commit()
            ancora = venda.result(timeout=5)
        finally:
            ctx.caso.db.rollback()
    assert Decimal(str(_vigente(ctx.caso, ancora)["valor_fixo"])) == 5


def test_venda_pendente_bloqueia_configuracao_mas_permite_vendas_paralelas(concorrente):
    ctx = concorrente
    antiga = _venda(ctx.caso, 1, datetime(2026, 1, 1))
    ancora_antiga = antiga.comissao_ancora_em
    sinal = SimpleNamespace(iniciada=Event(), concluida=Event(), pid=None)
    with ThreadPoolExecutor(max_workers=2) as pool:
        # Duas inclusoes de venda compartilham o lock, sem serializar vendas.
        outra_ancora = pool.submit(
            _operacao_concorrente, ctx.engine, ctx.a, numero=2
        ).result(timeout=3)
        alteracao = pool.submit(_operacao_concorrente, ctx.engine, ctx.a, sinal=sinal)
        try:
            _aguardar_advisory(ctx.engine, sinal)
            ctx.caso.db.commit()
            alteracao.result(timeout=5)
        finally:
            ctx.caso.db.rollback()
    assert Decimal(str(_vigente(ctx.caso, ancora_antiga)["valor_fixo"])) == 3
    assert Decimal(str(_vigente(ctx.caso, outra_ancora)["valor_fixo"])) == 3
