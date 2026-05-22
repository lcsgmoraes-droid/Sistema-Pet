import os


os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from app.contas_pagar_routes import _normalizar_texto_busca


def test_busca_contas_pagar_normaliza_acentos_e_separadores():
    assert _normalizar_texto_busca("Pr\u00f3-Labore") == "pro labore"
    assert _normalizar_texto_busca("Pro-labore") == "pro labore"
    assert _normalizar_texto_busca("  PR\u00d3   LABORE  ") == "pro labore"
