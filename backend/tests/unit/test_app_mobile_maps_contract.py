from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_app_entregador_usa_endereco_limpo_para_google_maps():
    screen = (
        REPO_ROOT / "app-mobile/src/screens/entregador/DetalheEntregaScreen.tsx"
    ).read_text(encoding="utf-8")
    helper = (REPO_ROOT / "app-mobile/src/utils/mapsAddress.ts").read_text(
        encoding="utf-8"
    )

    assert "limparEnderecoParaMaps" in helper
    assert "Apto" in helper
    assert "CEP" in helper
    assert 'import { limparEnderecoParaMaps } from "@/utils/mapsAddress";' in screen
    assert "const enderecoMaps = limparEnderecoParaMaps(endereco)" in screen
    assert "encodeURIComponent(enderecoMaps)" in screen
