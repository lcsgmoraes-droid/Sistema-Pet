from app.veterinario_catalogo_routes import BULARIO_STATUS_IMPORTADO
from app.veterinario_models import MedicamentoCatalogo


def test_status_da_importacao_do_bulario_cabe_na_coluna():
    limite = MedicamentoCatalogo.__table__.c.verificacao_status.type.length

    assert len(BULARIO_STATUS_IMPORTADO) <= limite
    assert BULARIO_STATUS_IMPORTADO == "fonte_oficial_nao_revisado"
