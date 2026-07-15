from decimal import Decimal

from app.dre_canais.base import (
    _classificar_conta_dre,
    _eh_folha_funcionarios_dre,
    _normalizar_texto_dre,
)
from app.dre_canais.folha import _calcular_complemento_folha


def test_classifica_pro_labore_e_beneficios_como_despesa_de_pessoal():
    assert _classificar_conta_dre("Pro Labore Sócios") == "despesas_pessoal"
    assert (
        _classificar_conta_dre("Plano Odontológico Unimed")
        == "despesas_pessoal"
    )
    assert _classificar_conta_dre("Despesas com Pessoal") == "despesas_pessoal"


def test_classifica_software_e_escritorio_como_administrativo():
    assert (
        _classificar_conta_dre("Softwares e Sistemas - ERP")
        == "despesas_administrativas"
    )
    assert _classificar_conta_dre("Escritório") == "despesas_administrativas"


def test_normalizacao_remove_acentos_e_separadores():
    assert _normalizar_texto_dre("Pró-Labore / SÓCIOS") == "pro labore socios"


def test_pro_labore_nao_abate_folha_estimada_de_funcionarios():
    assert _eh_folha_funcionarios_dre("Pro Labore Sócios") is False
    assert _eh_folha_funcionarios_dre("Folha de Pagamento") is True


def test_complemento_desconta_contas_e_provisoes_sem_ficar_negativo():
    assert _calcular_complemento_folha(
        Decimal("8540.26"), Decimal("2000"), Decimal("500")
    ) == Decimal("6040.26")
    assert _calcular_complemento_folha(
        Decimal("8540.26"), Decimal("9000"), Decimal("0")
    ) == Decimal("0.00")
