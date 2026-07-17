from decimal import Decimal

from app.services.dashboard_entregas_metrics import calcular_medias_por_entrega


def test_medias_usam_quantidade_de_entregas_e_nao_quantidade_de_rotas():
    custo_medio, taxa_media = calcular_medias_por_entrega(
        total_entregas=5,
        custo_total=Decimal("50"),
        taxa_total=Decimal("75"),
    )

    assert custo_medio == 10
    assert taxa_media == 15


def test_medias_sem_entregas_retornam_zero():
    assert calcular_medias_por_entrega(0, Decimal("20"), Decimal("30")) == (0, 0)
