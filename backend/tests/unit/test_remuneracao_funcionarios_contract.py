from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_calcula_complemento_liquido_com_base_no_holerite():
    from app.services.remuneracao_service import calcular_composicao_remuneracao

    cargo = SimpleNamespace(
        salario_base=Decimal("2098.00"),
        regime_remuneracao="clt",
        inss_funcionario_percentual=Decimal("0.00"),
        inss_funcionario_valor=Decimal("164.50"),
        desconto_transporte_valor=Decimal("0.00"),
        outros_descontos_valor=Decimal("0.00"),
        inss_patronal_percentual=Decimal("0.00"),
        fgts_percentual=Decimal("8.00"),
        gera_ferias=False,
        gera_decimo_terceiro=False,
    )
    funcionario = SimpleNamespace(
        salario_base_override=None,
        liquido_combinado=Decimal("2800.00"),
        complemento_modo="automatico",
        complemento_fixo_valor=Decimal("0.00"),
    )

    composicao = calcular_composicao_remuneracao(cargo, funcionario)

    assert composicao["salario_base"] == Decimal("2098.00")
    assert composicao["descontos_funcionario_total"] == Decimal("164.50")
    assert composicao["liquido_holerite"] == Decimal("1933.50")
    assert composicao["complemento_interno"] == Decimal("866.50")
    assert composicao["fgts_empresa"] == Decimal("167.84")
    assert composicao["custo_total_empresa"] == Decimal("3132.34")


def test_regime_sem_encargos_lanca_valor_direto():
    from app.services.remuneracao_service import calcular_composicao_remuneracao

    cargo = SimpleNamespace(
        salario_base=Decimal("1800.00"),
        regime_remuneracao="sem_encargos",
        inss_funcionario_percentual=Decimal("7.50"),
        inss_funcionario_valor=Decimal("100.00"),
        desconto_transporte_valor=Decimal("80.00"),
        outros_descontos_valor=Decimal("20.00"),
        inss_patronal_percentual=Decimal("20.00"),
        fgts_percentual=Decimal("8.00"),
        gera_ferias=True,
        gera_decimo_terceiro=True,
    )
    funcionario = SimpleNamespace(
        salario_base_override=None,
        liquido_combinado=None,
        complemento_modo="nenhum",
        complemento_fixo_valor=Decimal("0.00"),
    )

    composicao = calcular_composicao_remuneracao(cargo, funcionario)

    assert composicao["descontos_funcionario_total"] == Decimal("0.00")
    assert composicao["liquido_holerite"] == Decimal("1800.00")
    assert composicao["encargos_empresa_total"] == Decimal("0.00")
    assert composicao["provisoes_total"] == Decimal("0.00")
    assert composicao["custo_total_empresa"] == Decimal("1800.00")


def test_modelos_rotas_e_telas_expoem_composicao_remuneracao():
    cargo_model = (REPO_ROOT / "backend/app/cargo_models.py").read_text(
        encoding="utf-8"
    )
    cliente_model = (REPO_ROOT / "backend/app/models.py").read_text(encoding="utf-8")
    funcionarios_routes = (
        REPO_ROOT / "backend/app/funcionarios/base_routes.py"
    ).read_text(encoding="utf-8")
    cargos_page = (REPO_ROOT / "frontend/src/pages/Cadastros/Cargos.jsx").read_text(
        encoding="utf-8"
    )
    funcionarios_page = (
        REPO_ROOT / "frontend/src/pages/RH/Funcionarios.jsx"
    ).read_text(encoding="utf-8")

    assert "regime_remuneracao" in cargo_model
    assert "inss_funcionario_valor" in cargo_model
    assert "desconto_transporte_valor" in cargo_model
    assert "salario_base_override" in cliente_model
    assert "liquido_combinado" in cliente_model
    assert "complemento_modo" in cliente_model
    assert "/{funcionario_id}/remuneracao" in funcionarios_routes
    assert "Composicao de remuneracao" in cargos_page
    assert "Liquido combinado" in funcionarios_page
    assert "Complemento interno" in funcionarios_page
