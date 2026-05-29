import os

os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL") or "sqlite:///./test.db"
os.environ["DEBUG"] = "false"

from app.produtos_routes import _resolver_filtro_ativo_produtos  # noqa: E402


def test_resolver_filtro_ativo_mantem_compatibilidade_padrao():
    assert _resolver_filtro_ativo_produtos(True, None) is True
    assert _resolver_filtro_ativo_produtos(False, None) is False


def test_resolver_filtro_ativo_permite_todos_explicitamente():
    assert _resolver_filtro_ativo_produtos(True, "todos") is None
    assert _resolver_filtro_ativo_produtos(False, "ativos_e_inativos") is None


def test_resolver_filtro_ativo_aceita_status_textuais():
    assert _resolver_filtro_ativo_produtos(None, "ativos") is True
    assert _resolver_filtro_ativo_produtos(None, "inativos") is False
