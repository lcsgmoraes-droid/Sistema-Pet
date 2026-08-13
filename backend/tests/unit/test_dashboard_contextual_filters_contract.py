from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _source(relative_path: str) -> str:
    return (BACKEND_ROOT / relative_path).read_text(encoding="utf-8")


def test_contas_pagar_aceita_filtros_contextuais_do_dashboard():
    source = _source("app/financeiro/contas_pagar_consulta_routes.py")

    assert 'status_normalizado == "em_aberto"' in source
    assert "ContaPagar.status.in_(STATUS_CONTAS_PAGAR_EM_ABERTO)" in source
    assert "ContaPagar.data_vencimento < hoje" in source
    assert "ContaPagar.data_vencimento == hoje" in source
    assert "hoje = now_brasilia().date()" in source


def test_contas_receber_aceita_filtros_contextuais_do_dashboard():
    source = _source("app/contas_receber_consulta_routes.py")

    assert 'status_normalizado == "em_aberto"' in source
    assert "ContaReceber.status.in_(STATUS_CONTAS_RECEBER_EM_ABERTO)" in source
    assert "ContaReceber.data_vencimento < hoje" in source
    assert "hoje = now_brasilia().date()" in source


def test_clientes_aceita_visoes_contextuais_do_dashboard():
    source = _source("app/clientes/crud_routes.py")

    assert 'visao_dashboard == "vip_em_risco"' in source
    assert 'visao_dashboard == "inativos_90_dias"' in source
    assert 'visao_dashboard == "novos_promissores"' in source
    assert 'visao_dashboard == "sem_whatsapp"' in source
    assert 'ClienteSegmento.segmento == "VIP"' in source
    assert "timedelta(days=90)" in source
