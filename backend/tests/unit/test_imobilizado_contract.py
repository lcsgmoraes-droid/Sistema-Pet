from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.financeiro.imobilizado_schemas import BemImobilizadoCreate


ROOT = Path(__file__).resolve().parents[3]


def _payload(**overrides):
    dados = {
        "nome": "Balcao principal",
        "categoria": "moveis_utensilios",
        "data_aquisicao": date(2026, 1, 1),
        "valor_aquisicao": Decimal("5000.00"),
        "valor_residual": Decimal("500.00"),
        "vida_util_meses": 60,
    }
    dados.update(overrides)
    return dados


def test_schema_rejeita_residual_maior_que_aquisicao():
    with pytest.raises(ValidationError, match="valor residual"):
        BemImobilizadoCreate(**_payload(valor_residual=Decimal("6000.00")))


def test_schema_exige_data_quando_bem_e_baixado():
    with pytest.raises(ValidationError, match="data da baixa"):
        BemImobilizadoCreate(**_payload(status="baixado"))


def test_tela_e_menu_publicam_imobilizado_em_financeiro():
    menu = (ROOT / "frontend/src/components/layout/menuConfig.js").read_text(
        encoding="utf-8"
    )
    routes = (ROOT / "frontend/src/app/routes/FinanceRoutes.jsx").read_text(
        encoding="utf-8"
    )
    agregador = (ROOT / "backend/app/financeiro_routes.py").read_text(encoding="utf-8")

    assert 'path: "/financeiro/imobilizado"' in menu
    assert 'path="financeiro/imobilizado"' in routes
    assert "router.include_router(imobilizado_router)" in agregador
