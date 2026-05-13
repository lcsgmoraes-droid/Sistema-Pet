from app.models import Raca


def test_raca_model_mapeia_coluna_especie_legada():
    assert "especie" in Raca.__table__.columns

    raca = Raca(nome="SRD", especie="Cachorro", especie_id=1, tenant_id="tenant-teste")

    assert raca.especie == "Cachorro"
