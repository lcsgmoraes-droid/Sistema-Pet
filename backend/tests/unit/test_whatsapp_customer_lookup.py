"""Identificacao do tutor pelo telefone do WhatsApp (servico unico)."""

from types import SimpleNamespace

import pytest

from app.whatsapp import customer_context_service as contexto
from app.whatsapp import customer_lookup as lookup

TENANT = "11111111-1111-1111-1111-111111111111"


@pytest.mark.parametrize(
    "a,b",
    [
        ("5511999998888", "(11) 99999-8888"),
        ("11 9999-8888", "5511999998888"),  # sem o 9o digito
        ("(11) 99999-8888", "11999998888"),
        ("99999-8888", "5511999998888"),  # cadastro sem DDD
        ("5555999998888", "(55) 99999-8888"),  # DDD 55 com codigo do pais
    ],
)
def test_formatos_diferentes_do_mesmo_numero_sao_compativeis(a, b):
    assert lookup.telefones_compativeis(a, b)


@pytest.mark.parametrize(
    "a,b",
    [
        ("5511999998888", "5521999998888"),  # mesmo final, DDD diferente
        ("5511999998888", "5511999997777"),
        ("5511999998888", ""),
        ("266915104710838@lid", "5511999998888"),  # id interno nao e telefone
        ("1234567", "1234567"),  # curto demais
    ],
)
def test_numeros_diferentes_ou_invalidos_nao_sao_compativeis(a, b):
    assert not lookup.telefones_compativeis(a, b)


def test_chave_do_telefone_extrai_ddd_e_ultimos_oito_digitos():
    assert lookup.chave_telefone("+55 (11) 99999-8888") == ("11", "99998888")
    assert lookup.chave_telefone("99999-8888") == (None, "99998888")
    assert lookup.chave_telefone("123") is None
    assert lookup.chave_telefone("266915104710838@lid") is None


class _Consulta:
    def __init__(self, linhas):
        self.linhas = linhas

    def filter(self, *_args, **_kwargs):
        return self

    def limit(self, _n):
        return self

    def all(self):
        return self.linhas


class _DB:
    def __init__(self, linhas):
        self.linhas = linhas

    def query(self, *_cols):
        return _Consulta(self.linhas)


def _linha(id_, celular=None, telefone=None):
    return SimpleNamespace(id=id_, celular=celular, telefone=telefone)


def test_um_cadastro_compativel_identifica_o_tutor():
    db = _DB([_linha(10, "(11) 99999-8888"), _linha(11, "(21) 99999-8888")])

    r = lookup.resolver_tutor_por_telefone(db, TENANT, "5511999998888")

    assert r.situacao == lookup.SITUACAO_UNICO
    assert r.cliente_id == 10


def test_dois_cadastros_com_o_mesmo_numero_e_ambiguo_e_nao_escolhe():
    db = _DB([_linha(10, "(11) 99999-8888"), _linha(12, telefone="11 99999-8888")])

    r = lookup.resolver_tutor_por_telefone(db, TENANT, "5511999998888")

    assert r.situacao == lookup.SITUACAO_AMBIGUO
    assert r.cliente_id is None
    assert r.candidatos == (10, 12)


def test_mesmo_cadastro_com_celular_e_telefone_iguais_nao_e_ambiguo():
    db = _DB([_linha(10, "(11) 99999-8888", "11 99999-8888")])

    r = lookup.resolver_tutor_por_telefone(db, TENANT, "5511999998888")

    assert r.situacao == lookup.SITUACAO_UNICO


def test_nenhum_cadastro_compativel():
    db = _DB([_linha(10, "(21) 99999-8888")])

    r = lookup.resolver_tutor_por_telefone(db, TENANT, "5511999998888")

    assert r.situacao == lookup.SITUACAO_NENHUM
    assert r.cliente_id is None


def test_identificador_que_nao_e_telefone_e_invalido():
    r = lookup.resolver_tutor_por_telefone(_DB([]), TENANT, "266915104710838@lid")

    assert r.situacao == lookup.SITUACAO_INVALIDO


# ---------------------------------------------------------------------------
# Contexto do atendimento: vinculo antigo errado nao vale mais
# ---------------------------------------------------------------------------


class _ClienteQuery:
    def __init__(self, cliente):
        self.cliente = cliente

    def filter(self, *_a, **_k):
        return self

    def first(self):
        return self.cliente


class _ContextoDB:
    def __init__(self, cliente):
        self.cliente = cliente

    def query(self, *_cols):
        return _ClienteQuery(self.cliente)


def _sessao(cliente_id, telefone="5511999998888"):
    return SimpleNamespace(cliente_id=cliente_id, phone_number=telefone)


def test_vinculo_da_sessao_com_telefone_correspondente_e_mantido(monkeypatch):
    monkeypatch.setattr(contexto, "remote_data_enabled", lambda: False)
    cliente = SimpleNamespace(id=5, celular="(11) 99999-8888", telefone=None)

    r = contexto.resolve_session_customer(
        _ContextoDB(cliente), tenant_id=TENANT, session=_sessao(5)
    )

    assert r is cliente


def test_vinculo_antigo_com_telefone_diferente_e_ignorado(monkeypatch):
    monkeypatch.setattr(contexto, "remote_data_enabled", lambda: False)
    monkeypatch.setattr(
        contexto,
        "resolver_tutor_por_telefone",
        lambda *_a, **_k: lookup.ResolucaoTutor(lookup.SITUACAO_NENHUM),
    )
    # Vinculo gravado pela regra frouxa antiga: o cadastro tem OUTRO telefone.
    cliente_errado = SimpleNamespace(id=5, celular="(21) 98888-7777", telefone=None)

    r = contexto.resolve_session_customer(
        _ContextoDB(cliente_errado), tenant_id=TENANT, session=_sessao(5)
    )

    assert r is None


def test_sem_vinculo_usa_a_regra_unica(monkeypatch):
    monkeypatch.setattr(contexto, "remote_data_enabled", lambda: False)
    encontrado = SimpleNamespace(id=9, celular="(11) 99999-8888", telefone=None)
    monkeypatch.setattr(
        contexto,
        "resolver_tutor_por_telefone",
        lambda *_a, **_k: lookup.ResolucaoTutor(lookup.SITUACAO_UNICO, 9, (9,)),
    )

    r = contexto.resolve_session_customer(
        _ContextoDB(encontrado), tenant_id=TENANT, session=_sessao(None)
    )

    assert r is encontrado
