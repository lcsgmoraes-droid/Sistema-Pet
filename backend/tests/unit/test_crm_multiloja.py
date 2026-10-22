"""Etapa 1.5 do CRM: o usuario so ve as lojas a que tem direito."""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.crm import lojas as mod
from app.tenancy.context import get_current_tenant

ATUAL, B, C, D = (uuid4() for _ in range(4))
USUARIO = SimpleNamespace(id=7)


def _preparar(monkeypatch, *, permissoes, vinculos, com_modulo, ver_crm):
    """permissoes: perms na loja atual; ver_crm: lojas onde tem crm.visualizar."""
    monkeypatch.setattr(mod, "sync_rls_tenant", lambda *_a, **_k: None)
    monkeypatch.setattr(mod, "sync_rls_auth_user", lambda *_a, **_k: None)
    monkeypatch.setattr(mod, "_lojas_vinculadas", lambda *_a: list(vinculos))
    monkeypatch.setattr(mod, "_nome_da_loja", lambda _db, tid: f"Loja {str(tid)[:4]}")
    monkeypatch.setattr(
        mod,
        "tenant_has_active_module",
        lambda _db, tid, _m: UUID_STR(tid) in com_modulo,
    )

    def _perms(_db, _uid, tid):
        if tid == ATUAL:
            return set(permissoes)
        return {mod.PERM_VISUALIZAR} if tid in ver_crm else set()

    monkeypatch.setattr(mod, "get_user_permissions", _perms)


def UUID_STR(valor):
    return str(valor)


def test_sem_todas_lojas_so_a_loja_atual(monkeypatch):
    _preparar(
        monkeypatch,
        permissoes={mod.PERM_VISUALIZAR},
        vinculos=[ATUAL, B],
        com_modulo={str(B)},
        ver_crm={B},
    )

    lojas = mod.lojas_permitidas(object(), USUARIO, ATUAL)

    assert [loja.id for loja in lojas] == [ATUAL]


def test_com_todas_lojas_inclui_so_as_que_tem_modulo_e_permissao(monkeypatch):
    _preparar(
        monkeypatch,
        permissoes={mod.PERM_VISUALIZAR, mod.PERM_TODAS_LOJAS},
        vinculos=[ATUAL, B, C, D],
        com_modulo={str(B), str(C)},  # D nao contratou o CRM
        ver_crm={B, D},  # C: sem crm.visualizar
    )

    lojas = mod.lojas_permitidas(object(), USUARIO, ATUAL)

    assert [loja.id for loja in lojas] == [ATUAL, B]  # atual sempre primeiro


def test_filtro_vazio_devolve_todas_e_filtro_restringe():
    from app.crm.lojas import Loja

    permitidas = [Loja(ATUAL, "A"), Loja(B, "B")]

    assert mod.resolver_lojas(permitidas, None) == permitidas
    assert mod.resolver_lojas(permitidas, [str(B)]) == [permitidas[1]]
    assert mod.resolver_lojas(permitidas, [str(B), str(B)]) == [permitidas[1]]


def test_filtro_com_loja_nao_permitida_e_negado():
    from app.crm.lojas import Loja

    with pytest.raises(HTTPException) as erro:
        mod.resolver_lojas([Loja(ATUAL, "A")], [str(C)])

    assert erro.value.status_code == 403


def test_consulta_roda_no_contexto_de_cada_loja_e_marca_a_origem(monkeypatch):
    from app.crm.lojas import Loja

    monkeypatch.setattr(mod, "sync_rls_tenant", lambda *_a, **_k: None)
    contextos = []

    def _consulta(loja):
        contextos.append(get_current_tenant())
        return [{"lead": f"de-{loja.nome}"}]

    itens = mod.consultar_por_loja(
        object(), [Loja(ATUAL, "A"), Loja(B, "B")], _consulta, ATUAL
    )

    assert contextos == [ATUAL, B]
    assert itens[0]["loja_nome"] == "A" and itens[1]["loja_id"] == str(B)
    assert get_current_tenant() is None  # contexto restaurado


def test_rota_de_lojas_exige_modulo_e_permissao():
    from pathlib import Path

    raiz = Path(__file__).resolve().parents[2] / "app"
    rotas = (raiz / "crm/routes.py").read_text(encoding="utf-8")
    montagem = (raiz / "main_routers.py").read_text(encoding="utf-8")

    assert 'require_permission_dependency("crm.visualizar")' in rotas
    assert (
        'include_router(crm_router, dependencies=_module_dependencies("crm"))'
        in montagem
    )
