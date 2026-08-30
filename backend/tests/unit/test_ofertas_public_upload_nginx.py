from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
NGINX_LOCATIONS = ROOT / "nginx" / "includes" / "app-server-locations.conf"


def test_artes_publicadas_sao_servidas_antes_do_bloqueio_generico_de_uploads():
    config = NGINX_LOCATIONS.read_text(encoding="utf-8")
    ofertas_location = "location ^~ /uploads/ofertas/ {"
    bloqueio_generico = "location ^~ /uploads/ {"

    assert ofertas_location in config
    assert "alias /app/uploads/ofertas/;" in config
    assert config.index(ofertas_location) < config.index(bloqueio_generico)
