from types import SimpleNamespace

from app.nfe.listagem_normalizacao import _normalizar_nota_venda_local
from app.nfe.listagem_sync import _aplicar_cliente_venda_em_nota


def test_normalizacao_local_expoe_diagnostico_da_intnfe():
    venda = SimpleNamespace(
        id=1116549,
        nfe_correlation_id="correlation-id",
        nfe_bling_id=None,
        nfe_numero="17842",
        nfe_serie=2,
        nfe_modelo=55,
        nfe_chave="1" * 44,
        nfe_status="rejeitada",
        nfe_codigo_erro="999",
        nfe_motivo_rejeicao="Motivo fiscal retornado pelo emissor",
        nfe_protocolo=None,
        nfe_ambiente=1,
        nfe_data_emissao=None,
        nfe_provider="intnfe",
        total=159.89,
        cliente=SimpleNamespace(
            id=321, codigo="C-987", nome="Pessoa fictícia", cpf=None, cnpj=None
        ),
        canal="pdv",
        loja_origem="Loja física",
        numero_venda="202609120005",
        tipo_documento_fiscal="nfe",
    )

    nota = _normalizar_nota_venda_local(venda)

    assert nota["provedor"] == "intnfe"
    assert nota["venda_id"] == 1116549
    assert nota["correlation_id"] == "correlation-id"
    assert nota["codigo_erro"] == "999"
    assert nota["motivo_rejeicao"] == "Motivo fiscal retornado pelo emissor"
    assert nota["ambiente_codigo"] == 1
    assert nota["cliente"]["codigo"] == "C-987"
    assert nota["cliente"]["id"] == 321


def test_cache_fiscal_enriquecido_com_codigo_publico_do_cliente_local():
    nota = {"cliente": {"id": "id-do-provedor", "nome": "Pessoa no provedor"}}
    venda = SimpleNamespace(
        cliente=SimpleNamespace(
            id=321, codigo="C-987", nome="Pessoa local", cpf=None, cnpj=None
        )
    )

    _aplicar_cliente_venda_em_nota(nota, venda)

    assert nota["cliente"]["codigo"] == "C-987"
    assert nota["cliente"]["id"] == "id-do-provedor"
    assert nota["cliente"]["nome"] == "Pessoa no provedor"
