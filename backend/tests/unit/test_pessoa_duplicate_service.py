import os
from pathlib import Path
from types import SimpleNamespace


os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from app.services.pessoa_duplicate_service import (
    avaliar_par_duplicidade_pessoas,
    escolher_pessoa_principal,
    normalizar_nome_pessoa,
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


def test_clientes_router_expoe_endpoints_de_duplicidade():
    paths = {route.path for route in duplicidades_router.routes if hasattr(route, "path")}

    assert "/duplicidades/sugestoes" in paths
    assert "/duplicidades/fundir-automaticas" in paths
    assert "/duplicidades/historico" in paths


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
