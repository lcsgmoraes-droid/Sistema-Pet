"""Importacao reutiliza fornecedor compartilhado apenas no grupo autorizado."""

from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.grupo_comercial_models import GrupoComercial, GrupoComercialMembro
from app.models import Cliente, Tenant, User
from app.notas_entrada import fornecedores
from app.notas_entrada.upload_routes_parts import common
from app.tenancy import filters as tenant_filters
from app.tenancy.context import clear_current_tenant, set_current_tenant
from app.veterinario_models import VetPartnerLink


ORIGEM = UUID("71111111-1111-1111-1111-111111111111")
DESTINO = UUID("72222222-2222-2222-2222-222222222222")
EXTERNA = UUID("73333333-3333-3333-3333-333333333333")
CNPJ = "12345678000199"
DADOS = {
    "fornecedor_cnpj": CNPJ,
    "fornecedor_nome": "Fornecedor no XML",
    "fornecedor_telefone": "11999990000",
}


@pytest.fixture()
def db_grupo(monkeypatch):
    clear_current_tenant()
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(
        engine,
        tables=[
            Tenant.__table__,
            User.__table__,
            Cliente.__table__,
            GrupoComercial.__table__,
            GrupoComercialMembro.__table__,
            VetPartnerLink.__table__,
        ],
    )
    with Session(engine, expire_on_commit=False) as db:
        db.execute(
            Tenant.__table__.insert(),
            [
                {"id": str(empresa), "name": nome, "name_normalized": nome.lower()}
                for empresa, nome in [
                    (ORIGEM, "Origem"),
                    (DESTINO, "Destino"),
                    (EXTERNA, "Externa"),
                ]
            ],
        )
        db.execute(
            GrupoComercial.__table__.insert(),
            {
                "id": 1,
                "nome": "Grupo",
                "criado_por_empresa_id": str(ORIGEM),
                "criado_por_usuario_id": 1,
                "status": "ativo",
            },
        )
        db.execute(
            GrupoComercialMembro.__table__.insert(),
            [
                {"grupo_id": 1, "empresa_id": str(empresa), "status": "ativo"}
                for empresa in [ORIGEM, DESTINO]
            ],
        )
        db.execute(
            Cliente.__table__.insert(),
            {
                "id": 20,
                "tenant_id": ORIGEM,
                "origem_tenant_id": ORIGEM,
                "user_id": 1,
                "nome": "Fornecedor original",
                "cnpj": CNPJ,
                "telefone": "19999990000",
                "codigo": "100",
                "tipo_pessoa": "PJ",
                "ativo": True,
                "is_fornecedor": True,
            },
        )
        db.commit()
        set_current_tenant(DESTINO)
        # SQLite normalmente usa escopo simples. Exercitar o predicado real
        # de producao, incluindo grupo ativo, origem e participacoes ativas.
        monkeypatch.setattr(
            tenant_filters, "_supports_partner_read_filter", lambda _db: True
        )
        yield db
    clear_current_tenant()
    engine.dispose()


def _buscar_upload(db, somente_ativos=True):
    return common.buscar_ou_criar_fornecedor_nfe(
        db,
        dados_nfe=DADOS,
        current_user=SimpleNamespace(id=1),
        tenant_id=DESTINO,
        somente_ativos=somente_ativos,
    )


@pytest.mark.parametrize("somente_ativos", [True, False])
def test_upload_reutiliza_id_do_grupo_sem_alterar_cadastro(db_grupo, somente_ativos):
    fornecedor, criado = _buscar_upload(db_grupo, somente_ativos)
    assert (fornecedor.id, criado) == (20, False)
    assert fornecedor.nome == "Fornecedor original"
    assert fornecedor.telefone == "19999990000"
    assert fornecedor.cnpj == CNPJ
    assert fornecedor.tenant_id == ORIGEM
    assert fornecedor.origem_tenant_id == ORIGEM
    assert not db_grupo.dirty and not db_grupo.new


def test_criador_automatico_reutiliza_fornecedor_do_grupo_sem_gerar_codigo(
    db_grupo, monkeypatch
):
    gerar_codigo = MagicMock(side_effect=AssertionError("Nao deve criar duplicado"))
    monkeypatch.setattr(fornecedores, "gerar_codigo_cliente", gerar_codigo)
    fornecedor, criado = fornecedores.criar_fornecedor_automatico(
        DADOS,
        db_grupo,
        SimpleNamespace(id=1),
        DESTINO,
    )
    assert (fornecedor.id, criado) == (20, False)
    assert not db_grupo.dirty and not db_grupo.new
    gerar_codigo.assert_not_called()


def test_fornecedor_local_tem_prioridade_sobre_mesmo_cnpj_no_grupo(db_grupo):
    db_grupo.execute(
        Cliente.__table__.insert(),
        {
            "id": 21,
            "tenant_id": DESTINO,
            "origem_tenant_id": DESTINO,
            "user_id": 1,
            "nome": "Local",
            "cnpj": CNPJ,
            "tipo_pessoa": "PJ",
            "ativo": True,
            "is_fornecedor": True,
        },
    )
    db_grupo.commit()
    fornecedor, criado = _buscar_upload(db_grupo)
    assert (fornecedor.id, criado) == (21, False)


def test_upload_reativa_local_inativo_antes_de_reutilizar_grupo(db_grupo):
    db_grupo.execute(
        Cliente.__table__.insert(),
        {
            "id": 21,
            "tenant_id": DESTINO,
            "origem_tenant_id": DESTINO,
            "user_id": 1,
            "nome": "Local inativo",
            "cnpj": CNPJ,
            "codigo": "200",
            "tipo_pessoa": "PJ",
            "ativo": False,
            "is_fornecedor": True,
        },
    )
    db_grupo.commit()
    fornecedor, reativado = _buscar_upload(db_grupo, somente_ativos=True)
    assert (fornecedor.id, reativado) == (21, True)
    assert fornecedor.ativo is True
    assert fornecedor.tenant_id == DESTINO
    assert fornecedor.codigo == "200"
    compartilhado = db_grupo.query(Cliente).filter(Cliente.id == 20).one()
    assert compartilhado.nome == "Fornecedor original"
    assert compartilhado.telefone == "19999990000"
    assert compartilhado.tenant_id == ORIGEM


@pytest.mark.parametrize(
    "alteracao",
    [
        "pessoa_inativa",
        "nao_fornecedor",
        "fora_grupo",
        "origem_fora_grupo",
        "grupo_inativo",
        "membro_origem_inativo",
        "membro_destino_inativo",
        "outro_cnpj",
    ],
)
def test_nao_reutiliza_fornecedor_sem_acesso_ou_ativo_comprovado(
    db_grupo, monkeypatch, alteracao
):
    tabela = Cliente.__table__
    if alteracao == "pessoa_inativa":
        db_grupo.execute(tabela.update().values(ativo=False))
    elif alteracao == "nao_fornecedor":
        db_grupo.execute(tabela.update().values(is_fornecedor=False))
    elif alteracao == "fora_grupo":
        db_grupo.execute(
            tabela.update().values(tenant_id=EXTERNA, origem_tenant_id=EXTERNA)
        )
    elif alteracao == "origem_fora_grupo":
        db_grupo.execute(tabela.update().values(origem_tenant_id=EXTERNA))
    elif alteracao == "grupo_inativo":
        db_grupo.execute(GrupoComercial.__table__.update().values(status="inativo"))
    elif alteracao in {"membro_origem_inativo", "membro_destino_inativo"}:
        empresa = ORIGEM if alteracao == "membro_origem_inativo" else DESTINO
        db_grupo.execute(
            GrupoComercialMembro.__table__.update()
            .where(GrupoComercialMembro.empresa_id == str(empresa))
            .values(status="inativo")
        )
    else:
        db_grupo.execute(tabela.update().values(cnpj="98765432000199"))
    db_grupo.commit()
    assert (
        fornecedores.buscar_fornecedor_ativo_no_grupo(
            db_grupo, cnpj=CNPJ, tenant_id=DESTINO
        )
        is None
    )
    criar = MagicMock(return_value=(None, False))
    monkeypatch.setattr(common, "criar_fornecedor_automatico", criar)
    assert _buscar_upload(db_grupo) == (None, False)
    criar.assert_called_once_with(DADOS, db_grupo, SimpleNamespace(id=1), DESTINO)
    assert not db_grupo.dirty and not db_grupo.new
