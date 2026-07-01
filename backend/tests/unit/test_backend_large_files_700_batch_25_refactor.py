import os
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from app import bling_integration as facade
from app.bling_integration_parts import api, catalogo, core, notas
from app import bling_integration_fiscal


def test_bling_integration_preserva_reexports_publicos():
    assert facade.BlingAPI is api.BlingAPI
    assert facade.BlingAPI.__mro__[1] is notas.BlingNotasMixin
    assert facade.BlingAPI.__mro__[2] is catalogo.BlingCatalogoMixin
    assert facade.BlingAPI.__mro__[3] is core.BlingAPIBase

    assert facade.BLING_API_BASE_URL == core.BLING_API_BASE_URL
    assert facade.BLING_NFE_SERIE_PADRAO == core.BLING_NFE_SERIE_PADRAO
    assert facade.BLING_NFCE_SERIE_PADRAO == core.BLING_NFCE_SERIE_PADRAO
    assert facade.TOKEN_CONTROL_FILE is core.TOKEN_CONTROL_FILE
    assert facade.ENV_PATHS is core.ENV_PATHS

    assert facade._montar_url_bling is core._montar_url_bling
    assert facade._erro_rate_limit_bling is core._erro_rate_limit_bling
    assert facade._load_bling_runtime_config is core._load_bling_runtime_config
    assert facade._aguardar_slot_bling is core._aguardar_slot_bling
    assert facade._tempo_espera_rate_limit_bling is (
        core._tempo_espera_rate_limit_bling
    )

    assert facade.prevalidar_fiscal_venda is (
        bling_integration_fiscal.prevalidar_fiscal_venda
    )
    assert facade.aplicar_correcoes_fiscais_venda is (
        bling_integration_fiscal.aplicar_correcoes_fiscais_venda
    )


def test_bling_api_metodos_ficam_nos_modulos_especializados():
    assert facade.BlingAPI._request is core.BlingAPIBase._request
    assert (
        facade.BlingAPI.renovar_access_token is core.BlingAPIBase.renovar_access_token
    )
    assert facade.BlingAPI.emitir_nota_fiscal is (
        notas.BlingNotasMixin.emitir_nota_fiscal
    )
    assert facade.BlingAPI._montar_payload is notas.BlingNotasMixin._montar_payload
    assert facade.BlingAPI.baixar_danfe is notas.BlingNotasMixin.baixar_danfe
    assert (
        facade.BlingAPI.listar_produtos is catalogo.BlingCatalogoMixin.listar_produtos
    )
    assert facade.BlingAPI.atualizar_estoque_produto is (
        catalogo.BlingCatalogoMixin.atualizar_estoque_produto
    )
    assert (
        facade.BlingAPI.consultar_pedido is catalogo.BlingCatalogoMixin.consultar_pedido
    )


def test_bling_integration_fachada_e_modulos_abaixo_de_700_linhas():
    files = [
        Path(facade.__file__),
        Path(api.__file__),
        Path(core.__file__),
        Path(notas.__file__),
        Path(catalogo.__file__),
    ]

    for path in files:
        assert len(path.read_text(encoding="utf-8").splitlines()) < 700

    facade_source = Path(facade.__file__).read_text(encoding="utf-8")
    assert "class BlingAPI" not in facade_source
    assert "def _request(" not in facade_source
    assert "def emitir_nota_fiscal(" not in facade_source
    assert "bling_integration_parts" in facade_source
