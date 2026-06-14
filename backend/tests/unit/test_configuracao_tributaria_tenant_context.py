from inspect import signature
from pathlib import Path
from types import SimpleNamespace

import sqlalchemy as sa

from app.ia.aba7_extrato_models import ConfiguracaoTributaria
from app.ia.aba7_tributacao import CalculadoraTributaria


TRIBUTACAO_SOURCE = Path("app/ia/aba7_tributacao.py").read_text(encoding="utf-8")
ROUTES_SOURCE = Path("app/tributacao_routes.py").read_text(encoding="utf-8")
DRE_SOURCES = (
    Path("app/ia/aba7_dre.py").read_text(encoding="utf-8"),
    Path("app/ia/aba7_dre_canal.py").read_text(encoding="utf-8"),
    Path("app/ia/aba7_dre_detalhada_service.py").read_text(encoding="utf-8"),
)


def _parameters(callable_obj):
    return set(signature(callable_obj).parameters)


def _unique_constraints_for_model():
    constraints = []
    for constraint in ConfiguracaoTributaria.__table__.constraints:
        if isinstance(constraint, sa.UniqueConstraint):
            constraints.append(
                (constraint.name, tuple(column.name for column in constraint.columns))
            )
    return constraints


def test_configuracao_tributaria_exige_tenant_id_nos_fluxos_publicos():
    assert "tenant_id" in _parameters(CalculadoraTributaria.obter_configuracao)
    assert "tenant_id" in _parameters(CalculadoraTributaria.calcular_impostos)
    assert "tenant_id" in _parameters(CalculadoraTributaria.salvar_configuracao)
    assert "tenant_id" in _parameters(CalculadoraTributaria.estimar_economia_regime)
    assert "user_id" in _parameters(CalculadoraTributaria.salvar_configuracao)


def test_configuracao_tributaria_filtra_e_grava_por_tenant():
    for fragment in (
        "ConfiguracaoTributaria.tenant_id == tenant_id",
        "tenant_id=tenant_id",
        "usuario_id=user_id",
    ):
        assert fragment in TRIBUTACAO_SOURCE

    assert "ConfiguracaoTributaria.usuario_id == usuario_id" not in TRIBUTACAO_SOURCE


def test_rotas_de_tributacao_repassam_usuario_e_tenant_explicitamente():
    for fragment in (
        "calculadora.obter_configuracao(tenant_id=tenant_id)",
        "tenant_id=tenant_id",
        "user_id=current_user.id",
    ):
        assert fragment in ROUTES_SOURCE


def test_calculos_dre_resolvem_tenant_ativo_antes_de_calcular_impostos():
    expected = "tenant_id=tenant_id_para_escrita_dre(self.db, usuario_id)"
    for source in DRE_SOURCES:
        assert expected in source


def test_modelo_configuracao_tributaria_declara_unicidade_por_tenant():
    assert ConfiguracaoTributaria.__table__.c.usuario_id.unique is not True
    assert ("uq_configuracao_tributaria_tenant_id", ("tenant_id",)) in (
        _unique_constraints_for_model()
    )


class _FakeQuery:
    def __init__(self, config):
        self.config = config

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return self.config


class _FakeDb:
    def __init__(self, config):
        self.config = config

    def query(self, *_args, **_kwargs):
        return _FakeQuery(self.config)


def test_estimar_economia_regime_nao_muta_configuracao_persistida():
    config = SimpleNamespace(
        tenant_id="11111111-1111-1111-1111-111111111111",
        usuario_id=7,
        regime="simples_nacional",
        anexo_simples="Anexo I",
        faixa_simples="Faixa 1",
        aliquota_efetiva_simples=8.54,
        presuncao_lucro_percentual=8.0,
        aliquota_irpj=0.15,
        aliquota_adicional_irpj=0.10,
        aliquota_csll=0.09,
        aliquota_pis=0.0065,
        aliquota_cofins=0.03,
        incluir_icms_dre=False,
        incluir_iss_dre=False,
        aliquota_icms=None,
        aliquota_iss=None,
    )

    resultado = CalculadoraTributaria(_FakeDb(config)).estimar_economia_regime(
        tenant_id=config.tenant_id,
        receita_bruta=10000,
        lucro_operacional=2000,
    )

    assert config.regime == "simples_nacional"
    assert resultado["regime_atual"] == "simples_nacional"
