from pathlib import Path

from app import conciliacao_services
from app import conciliacao_services_importacao
from app import conciliacao_services_recebimentos
from app import conciliacao_services_stone


BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _line_count(*parts: str) -> int:
    return len((BACKEND_ROOT / Path(*parts)).read_text(encoding="utf-8").splitlines())


def test_conciliacao_services_preserva_reexports_legados() -> None:
    assert (
        conciliacao_services.importar_arquivo_operadora
        is conciliacao_services_importacao.importar_arquivo_operadora
    )
    assert (
        conciliacao_services.validar_importacao_cascata
        is conciliacao_services_importacao.validar_importacao_cascata
    )
    assert (
        conciliacao_services.processar_conciliacao
        is conciliacao_services_importacao.processar_conciliacao
    )
    assert (
        conciliacao_services.reverter_conciliacao
        is conciliacao_services_importacao.reverter_conciliacao
    )
    assert (
        conciliacao_services.conciliar_vendas_stone
        is conciliacao_services_stone.conciliar_vendas_stone
    )
    assert (
        conciliacao_services.processar_upload_conciliacao_vendas
        is conciliacao_services_stone.processar_upload_conciliacao_vendas
    )
    assert (
        conciliacao_services.validar_recebimentos_cascata_v2
        is conciliacao_services_recebimentos.validar_recebimentos_cascata_v2
    )
    assert (
        conciliacao_services.amarrar_recebimentos_vendas
        is conciliacao_services_recebimentos.amarrar_recebimentos_vendas
    )


def test_conciliacao_services_permanece_como_fachada_fina() -> None:
    assert _line_count("app", "conciliacao_services.py") < 80
    assert _line_count("app", "conciliacao_services_importacao.py") < 900
    assert _line_count("app", "conciliacao_services_stone.py") < 650
    assert _line_count("app", "conciliacao_services_recebimentos.py") < 550
