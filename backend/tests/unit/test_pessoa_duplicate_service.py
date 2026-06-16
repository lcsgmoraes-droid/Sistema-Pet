import os
from types import SimpleNamespace


os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from app.services.pessoa_duplicate_service import (
    avaliar_par_duplicidade_pessoas,
    escolher_pessoa_principal,
    normalizar_nome_pessoa,
)
from app.clientes_routes import router as clientes_router


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


def test_avaliar_par_permite_fusao_automatica_com_nome_igual_e_sem_conflitos():
    principal = _pessoa(id=10, nome="Teste Comissão", email="teste@example.com")
    duplicado = _pessoa(id=11, nome=" teste   comissao ", celular="11999998888")

    decisao = avaliar_par_duplicidade_pessoas(principal, duplicado)

    assert decisao.pode_fundir_automaticamente is True
    assert decisao.motivos_bloqueio == []


def test_avaliar_par_bloqueia_fusao_automatica_quando_documentos_conflitam():
    principal = _pessoa(id=10, nome="Buendia Distribuidora", cnpj="11.111.111/0001-11")
    duplicado = _pessoa(id=11, nome="buendia distribuidora", cnpj="22.222.222/0001-22")

    decisao = avaliar_par_duplicidade_pessoas(principal, duplicado)

    assert decisao.pode_fundir_automaticamente is False
    assert "cnpj_conflitante" in decisao.motivos_bloqueio


def test_avaliar_par_permite_fusao_automatica_entre_cliente_e_funcionario_sem_conflitos():
    cliente = _pessoa(id=10, nome="William", tipo_cadastro="cliente")
    funcionario = _pessoa(id=11, nome="william", tipo_cadastro="funcionario")

    decisao = avaliar_par_duplicidade_pessoas(cliente, funcionario)

    assert decisao.pode_fundir_automaticamente is True
    assert decisao.motivos_bloqueio == []


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
    paths = {route.path for route in clientes_router.routes}

    assert "/clientes/duplicidades/sugestoes" in paths
    assert "/clientes/duplicidades/fundir-automaticas" in paths
