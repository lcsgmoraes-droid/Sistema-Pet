from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_consultas_de_fechamento_usam_marcador_tenant_valido_por_alias():
    for relative_path in (
        "backend/app/comissoes_demonstrativo_historico_routes.py",
        "backend/app/comissoes_demonstrativo_routes.py",
    ):
        source = (ROOT / relative_path).read_text(encoding="utf-8")
        assert "{tenant_filter_p}" not in source
        assert "{tenant_filter_v}" not in source
        assert "{tenant_filter_ci}" not in source
        assert "p.{tenant_filter}" in source
        assert "v.{tenant_filter}" in source
        assert "ci.{tenant_filter}" in source


def test_detalhe_preserva_campos_consumidos_pela_tela():
    source = (
        ROOT / "backend/app/comissoes_demonstrativo_historico_routes.py"
    ).read_text(encoding="utf-8")

    for field in (
        '"valor_venda_snapshot"',
        '"percentual_snapshot"',
        '"valor_comissao"',
        '"observacao_pagamento"',
        '"periodo_vendas"',
    ):
        assert field in source
