"""
Guard contra os typos de atributo de alíquota do Simples (corrigidos em 2026-06-09).

Bugs originais — ``AttributeError`` em runtime, agora que a tabela existe em prod:
- ``projecao_caixa_service`` usava ``simples.aliquota_vigente`` — ``SimplesNacionalMensal``
  só tem ``aliquota_efetiva`` / ``aliquota_sugerida``.
- ``fechamento`` / ``provisao`` / ``reconciliacao`` usavam ``config.simples_aliquota_vigente``
  — ``EmpresaConfigFiscal`` tem ``aliquota_simples_vigente`` (nomes trocados).

Estes testes são leves (sem banco) e falhariam no código antigo.
"""
import os
import pathlib

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-min-32-chars-long-for-security")

SERVICOS = pathlib.Path(__file__).resolve().parents[2] / "app" / "services"


def test_modelos_tem_os_atributos_que_os_servicos_usam():
    """Se uma destas colunas for renomeada, os serviços do Simples precisam acompanhar."""
    from app.empresa_config_fiscal_models import EmpresaConfigFiscal
    from app.simples_nacional_models import SimplesNacionalMensal

    assert hasattr(EmpresaConfigFiscal, "aliquota_simples_vigente")
    assert hasattr(SimplesNacionalMensal, "aliquota_efetiva")
    assert hasattr(SimplesNacionalMensal, "aliquota_sugerida")


def test_servicos_do_simples_nao_referenciam_atributos_inexistentes():
    """Barra a reintrodução exata dos typos corrigidos."""
    arquivos = [
        "projecao_caixa_service.py",
        "fechamento_simples_service.py",
        "provisao_simples_service.py",
        "reconciliacao_simples_service.py",
    ]
    for nome in arquivos:
        texto = (SERVICOS / nome).read_text(encoding="utf-8")
        assert "simples_aliquota_vigente" not in texto, (
            f"{nome}: EmpresaConfigFiscal tem 'aliquota_simples_vigente', nao 'simples_aliquota_vigente'"
        )
        assert ".aliquota_vigente" not in texto, (
            f"{nome}: SimplesNacionalMensal nao tem 'aliquota_vigente' "
            "(use aliquota_efetiva/aliquota_sugerida)"
        )
