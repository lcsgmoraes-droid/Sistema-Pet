import os
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace


os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from app.services.pessoa_duplicate_service import (
    _paginar_sugestoes,
    avaliar_par_duplicidade_pessoas,
    escolher_pessoa_principal,
    executar_fusoes_assistidas_pessoas_por_nome,
    normalizar_nome_pessoa,
    planejar_fusao_assistida_por_nome,
)
from app.clientes.duplicidades_routes import router as duplicidades_router


def _pessoa(**kwargs):
    defaults = {
        "id": 1,
        "nome": "Lucas Guerra de Moraes",
        "tipo_cadastro": "cliente",
        "tipo_pessoa": "PF",
        "cpf": None,
        "cnpj": None,
        "crmv": None,
        "email": None,
        "telefone": None,
        "celular": None,
        "codigo": None,
        "ativo": True,
        "is_entregador": False,
        "auth_user_id": None,
        "credito": 0,
        "endereco": None,
        "cidade": None,
        "estado": None,
        "cep": None,
        "numero": None,
        "data_nascimento": None,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_normalizar_nome_pessoa_ignora_acentos_caixa_e_espacos():
    assert (
        normalizar_nome_pessoa("  LUCAS   Guerra de Morães  ")
        == "lucas guerra de moraes"
    )


def test_avaliar_par_nao_funde_automaticamente_apenas_por_nome_igual():
    principal = _pessoa(id=10, nome="Teste Comissão", email="teste@example.com")
    duplicado = _pessoa(id=11, nome=" teste   comissao ", celular="11999998888")

    decisao = avaliar_par_duplicidade_pessoas(principal, duplicado)

    assert decisao.pode_fundir_automaticamente is False
    assert "sem_identidade_forte_compartilhada" in decisao.motivos_bloqueio


def test_avaliar_par_permite_fusao_automatica_com_cpf_valido_igual():
    principal = _pessoa(id=10, nome="Lucas Guerra", cpf="529.982.247-25")
    duplicado = _pessoa(id=11, nome="Lucas Guerra", cpf="52998224725")

    decisao = avaliar_par_duplicidade_pessoas(principal, duplicado)

    assert decisao.pode_fundir_automaticamente is True
    assert decisao.sinais_confirmacao == ["cpf"]


def test_avaliar_par_permite_fusao_automatica_com_cnpj_valido_igual():
    principal = _pessoa(id=10, nome="Fornecedor A", cnpj="11.222.333/0001-81")
    duplicado = _pessoa(id=11, nome="Fornecedor A", cnpj="11222333000181")

    decisao = avaliar_par_duplicidade_pessoas(principal, duplicado)

    assert decisao.pode_fundir_automaticamente is True
    assert decisao.sinais_confirmacao == ["cnpj"]


def test_crmv_sem_uf_nao_e_suficiente_para_fusao_automatica():
    principal = _pessoa(id=10, crmv="12345")
    duplicado = _pessoa(id=11, crmv="12345")

    decisao = avaliar_par_duplicidade_pessoas(principal, duplicado)

    assert decisao.pode_fundir_automaticamente is False


def test_avaliar_par_bloqueia_fusao_automatica_quando_documentos_conflitam():
    principal = _pessoa(id=10, nome="Buendia Distribuidora", cnpj="11.111.111/0001-11")
    duplicado = _pessoa(id=11, nome="buendia distribuidora", cnpj="22.222.222/0001-22")

    decisao = avaliar_par_duplicidade_pessoas(principal, duplicado)

    assert decisao.pode_fundir_automaticamente is False
    assert "cnpj_conflitante" in decisao.motivos_bloqueio


def test_avaliar_par_mantem_cliente_e_funcionario_para_revisao_sem_documento():
    cliente = _pessoa(id=10, nome="William", tipo_cadastro="cliente")
    funcionario = _pessoa(id=11, nome="william", tipo_cadastro="funcionario")

    decisao = avaliar_par_duplicidade_pessoas(cliente, funcionario)

    assert decisao.pode_fundir_automaticamente is False
    assert "sem_identidade_forte_compartilhada" in decisao.motivos_bloqueio


def test_avaliar_par_bloqueia_contas_app_diferentes_mesmo_com_cpf_igual():
    principal = _pessoa(id=10, cpf="52998224725", auth_user_id=7)
    duplicado = _pessoa(id=11, cpf="52998224725", auth_user_id=8)

    decisao = avaliar_par_duplicidade_pessoas(principal, duplicado)

    assert decisao.pode_fundir_automaticamente is False
    assert "contas_app_diferentes" in decisao.motivos_bloqueio


def test_escolher_pessoa_principal_prefere_funcionario_ativo_ao_cliente_ativo():
    cliente = _pessoa(
        id=10,
        nome="William",
        tipo_cadastro="cliente",
        email="william@example.com",
    )
    funcionario = _pessoa(
        id=11,
        nome="William",
        tipo_cadastro="funcionario",
        ativo=True,
    )

    principal = escolher_pessoa_principal(
        [cliente, funcionario],
        referencias_por_id={10: 20, 11: 0},
    )

    assert principal is funcionario


def test_escolher_pessoa_principal_prefere_ativo_com_historico_e_dados():
    incompleta = _pessoa(id=1, ativo=True, nome="Lucas Guerra")
    completa = _pessoa(
        id=2,
        ativo=True,
        nome="Lucas Guerra",
        cpf="12345678900",
        email="lucas@example.com",
        telefone="1133334444",
        endereco="Rua A",
    )

    principal = escolher_pessoa_principal(
        [incompleta, completa],
        referencias_por_id={1: 12, 2: 2},
    )

    assert principal.id == 1


def test_fusao_assistida_usa_telefone_do_cadastro_mais_recente_com_data_igual():
    antigo = _pessoa(
        id=10,
        nome="Andreia Goncalves do Carmo",
        data_nascimento="1990-05-12",
        celular="18999990000",
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    recente = _pessoa(
        id=20,
        nome="andreia goncalves do carmo",
        data_nascimento="1990-05-12",
        celular="18988880000",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    plano = planejar_fusao_assistida_por_nome(antigo, recente)

    assert plano.elegivel is True
    assert plano.pessoa_mais_recente_id == 20
    assert plano.decisoes_campos["celular"] == "duplicado"
    assert "data_nascimento" in plano.sinais_confirmacao


def test_fusao_assistida_nao_usa_apenas_nome_igual_com_telefones_diferentes():
    pessoa_a = _pessoa(id=10, nome="Amanda Silva", celular="18999990000")
    pessoa_b = _pessoa(
        id=20,
        nome="Amanda Silva",
        celular="18988880000",
        created_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
    )

    plano = planejar_fusao_assistida_por_nome(pessoa_a, pessoa_b)

    assert plano.elegivel is False
    assert "sem_evidencia_secundaria_compartilhada" in plano.motivos_bloqueio


def test_fusao_por_nome_confirmada_pelo_dono_aceita_telefones_diferentes():
    pessoa_a = _pessoa(id=10, nome="Amanda Silva", celular="18999990000")
    pessoa_b = _pessoa(
        id=20,
        nome="Amanda Silva",
        celular="18988880000",
        created_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
    )

    plano = planejar_fusao_assistida_por_nome(
        pessoa_a,
        pessoa_b,
        aceitar_nome_igual=True,
    )

    assert plano.elegivel is True
    assert plano.decisoes_campos["celular"] == "duplicado"
    assert "nome_igual_confirmado_pelo_dono" in plano.sinais_confirmacao


def test_fusao_por_nome_confirmada_mantem_conflitos_objetivos_bloqueados():
    pessoa_a = _pessoa(
        id=10,
        nome="Pessoa Completa",
        cpf="52998224725",
        auth_user_id=100,
    )
    pessoa_b = _pessoa(
        id=20,
        nome="Pessoa Completa",
        cpf="16899535009",
        auth_user_id=200,
    )

    plano = planejar_fusao_assistida_por_nome(
        pessoa_a,
        pessoa_b,
        aceitar_nome_igual=True,
    )

    assert plano.elegivel is False
    assert "cpf_conflitante" in plano.motivos_bloqueio
    assert "contas_app_diferentes" in plano.motivos_bloqueio


def test_fusao_assistida_bloqueia_email_e_data_nascimento_conflitantes():
    pessoa_a = _pessoa(
        id=10,
        nome="Pessoa Completa",
        email="a@example.com",
        data_nascimento="1990-01-01",
    )
    pessoa_b = _pessoa(
        id=20,
        nome="Pessoa Completa",
        email="b@example.com",
        data_nascimento="1991-01-01",
    )

    plano = planejar_fusao_assistida_por_nome(pessoa_a, pessoa_b)

    assert plano.elegivel is False
    assert "email_conflitante" in plano.motivos_bloqueio
    assert "data_nascimento_conflitante" in plano.motivos_bloqueio


def test_fusao_assistida_preserva_telefone_antigo_se_recente_esta_vazio():
    antigo = _pessoa(
        id=10,
        nome="Cliente Evidenciado",
        email="cliente@example.com",
        telefone="1833334444",
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    recente = _pessoa(
        id=20,
        nome="Cliente Evidenciado",
        email="cliente@example.com",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    plano = planejar_fusao_assistida_por_nome(antigo, recente)

    assert plano.elegivel is True
    assert "telefone" not in plano.decisoes_campos
    assert "celular" not in plano.decisoes_campos


def test_fusao_assistida_aceita_telefone_compartilhado_entre_campos():
    antigo = _pessoa(
        id=10,
        nome="Contato Cruzado",
        telefone="18 3333-4444",
    )
    recente = _pessoa(
        id=20,
        nome="Contato Cruzado",
        celular="1833334444",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    plano = planejar_fusao_assistida_por_nome(antigo, recente)

    assert plano.elegivel is True
    assert "telefone_compartilhado" in plano.sinais_confirmacao
    assert plano.decisoes_campos["celular"] == "duplicado"


def test_simulacao_assistida_nao_altera_dados_e_separa_bloqueadas(monkeypatch):
    elegivel_antigo = _pessoa(
        id=10,
        nome="Cliente Evidenciado",
        email="cliente@example.com",
        celular="18999990000",
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    elegivel_recente = _pessoa(
        id=20,
        nome="Cliente Evidenciado",
        email="cliente@example.com",
        celular="18988880000",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    ambigua_a = _pessoa(id=30, nome="Amanda Silva", celular="18977770000")
    ambigua_b = _pessoa(id=40, nome="Amanda Silva", celular="18966660000")
    pessoas = [elegivel_antigo, elegivel_recente, ambigua_a, ambigua_b]

    class QueryFake:
        def filter(self, *_args, **_kwargs):
            return self

        def order_by(self, *_args, **_kwargs):
            return self

        def all(self):
            return pessoas

    class DbFake:
        def query(self, *_args, **_kwargs):
            return QueryFake()

    def falhar_se_fundir(*_args, **_kwargs):
        raise AssertionError("dry-run nao pode executar fusao")

    monkeypatch.setattr(
        "app.services.pessoa_duplicate_service.executar_fusao_pessoas",
        falhar_se_fundir,
    )

    resultado = executar_fusoes_assistidas_pessoas_por_nome(
        DbFake(),
        tenant_id="tenant-teste",
        user_id=1,
        confirmar=False,
    )

    assert resultado["simulacao"] is True
    assert resultado["total_elegiveis"] == 1
    assert resultado["total_bloqueadas"] == 1
    assert resultado["total_fundidas"] == 0


def test_clientes_router_expoe_endpoints_de_duplicidade():
    paths = {
        route.path for route in duplicidades_router.routes if hasattr(route, "path")
    }

    assert "/duplicidades/sugestoes" in paths
    assert "/duplicidades/fundir-automaticas" in paths
    assert "/duplicidades/fundir-assistidas-nome" in paths
    assert "/duplicidades/historico" in paths


def test_paginar_sugestoes_permite_revisar_todos_os_alertas_em_lotes():
    sugestoes = list(range(60))

    assert _paginar_sugestoes(sugestoes, skip=0, limit=25) == list(range(25))
    assert _paginar_sugestoes(sugestoes, skip=25, limit=25) == list(range(25, 50))
    assert _paginar_sugestoes(sugestoes, skip=50, limit=25) == list(range(50, 60))


def test_migration_separa_conta_e_protege_auditoria_por_tenant():
    migration = (
        Path(__file__).resolve().parents[2]
        / "alembic/versions/zwp20260731a1_pessoa_auth_merge_safety.py"
    ).read_text(encoding="utf-8")

    assert '"auth_user_id"' in migration
    assert '"merged_into_id"' in migration
    assert '"pessoa_merge_logs"' in migration
    assert "ENABLE ROW LEVEL SECURITY" in migration
    assert "uq_clientes_tenant_auth_user_ativo" in migration
