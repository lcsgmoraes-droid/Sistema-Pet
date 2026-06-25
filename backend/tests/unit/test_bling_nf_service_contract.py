from pathlib import Path

from app.services import bling_nf_service


REPO_ROOT = Path(__file__).resolve().parents[3]
SERVICE_SOURCE = "backend/app/services/bling_nf_service.py"
SERVICE_PACKAGE = "backend/app/services/bling_nf"
EXPECTED_MODULES = {
    "common.py",
    "estoque.py",
    "autocadastro.py",
    "desvinculo.py",
}
EXPECTED_PUBLIC_NAMES = {
    "AUTO_CADASTRO_BING_TAG",
    "buscar_produto_do_item",
    "produto_usa_composicao_virtual",
    "produto_ids_estoque_afetados",
    "consumir_movimentacoes_esperadas",
    "movimento_documentado_por_nf",
    "movimento_legado_pedido_para_nf",
    "desvincular_nf_de_pedido_incorreto",
    "baixar_estoque_item_integrado",
    "criar_produto_automatico_do_bling_por_item",
    "criar_produto_automatico_do_bling",
    "processar_nf_autorizada",
    "processar_nf_cancelada",
}


def test_bling_nf_service_public_api_stays_available():
    for name in EXPECTED_PUBLIC_NAMES:
        assert hasattr(bling_nf_service, name), name


def test_bling_nf_service_is_split_into_small_modules():
    service_path = REPO_ROOT / SERVICE_SOURCE
    package_dir = REPO_ROOT / SERVICE_PACKAGE

    assert package_dir.is_dir()
    assert len(service_path.read_text(encoding="utf-8").splitlines()) <= 700

    modules = {
        path.name: len(path.read_text(encoding="utf-8").splitlines())
        for path in package_dir.glob("*.py")
        if path.name != "__init__.py"
    }
    assert EXPECTED_MODULES <= set(modules)
    assert all(lines <= 700 for lines in modules.values())
