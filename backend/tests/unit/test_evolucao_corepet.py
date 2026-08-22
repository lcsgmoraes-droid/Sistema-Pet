from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.evolucao_corepet import (
    ITENS_EVOLUCAO,
    STATUS_DISPONIVEIS,
    listar_evolucao_corepet,
    registrar_uso_funcionalidade,
    validar_catalogo_evolucao,
)
from app.evolucao_models import EvolucaoFuncionalidadeUso


def _session_metricas():
    engine = create_engine("sqlite:///:memory:")
    EvolucaoFuncionalidadeUso.__table__.create(engine)
    return sessionmaker(bind=engine)()


def test_catalogo_evolucao_respeita_contrato_de_publicacao():
    validar_catalogo_evolucao()

    ids = [item["id"] for item in ITENS_EVOLUCAO]
    assert len(ids) == len(set(ids))
    for item in ITENS_EVOLUCAO:
        if item["status"] in STATUS_DISPONIVEIS:
            assert item["publicado_em"]
            assert item["caminho_ajuda"]


def test_catalogo_filtra_projetos_por_canal_sem_expor_item_interno():
    erp = listar_evolucao_corepet("erp")
    cliente = listar_evolucao_corepet("app_cliente")

    ids_erp = {item["id"] for item in erp["itens"]}
    ids_cliente = {item["id"] for item in cliente["itens"]}

    assert "grupos-empresas-transferencia-integrada" in ids_erp
    assert "grupos-empresas-transferencia-integrada" not in ids_cliente
    assert "avaliacao-entrega-app" in ids_cliente
    assert erp["total_disponivel"] >= 1


def test_catalogo_nao_anuncia_granel_de_farmacia_descartado():
    ids = {item["id"] for item in ITENS_EVOLUCAO}

    assert "fracionamento-produtos-farmacia" not in ids


def test_funcao_liberada_aparece_como_disponivel_em_fase_de_teste():
    resultado = listar_evolucao_corepet(
        "app_cliente",
        agora=datetime(2026, 8, 22, 12, tzinfo=timezone.utc),
    )
    avaliacao = next(
        item for item in resultado["itens"] if item["id"] == "avaliacao-entrega-app"
    )

    assert avaliacao["status"] == "disponivel"
    assert avaliacao["fase_disponibilidade"] == "teste"
    assert avaliacao["status_label"] == "Disponível — em fase de teste"


def test_promove_para_implantado_depois_do_tempo_e_quantidade_de_usos():
    db = _session_metricas()
    momento_uso = datetime(2026, 9, 1, 10, tzinfo=timezone.utc)
    for _ in range(10):
        assert registrar_uso_funcionalidade(
            db, "avaliacao-entrega-app", agora=momento_uso
        )

    resultado = listar_evolucao_corepet(
        "app_cliente",
        db,
        agora=datetime(2026, 9, 5, 12, tzinfo=timezone.utc),
    )
    avaliacao = next(
        item for item in resultado["itens"] if item["id"] == "avaliacao-entrega-app"
    )

    assert avaliacao["status"] == "disponivel"
    assert avaliacao["fase_disponibilidade"] == "implantado"
    assert avaliacao["implantado_em"] == "2026-09-05"
    assert avaliacao["novidade_ate"] == "2026-10-05"


def test_novidade_some_depois_do_periodo_sem_remover_outros_projetos():
    db = _session_metricas()
    for _ in range(10):
        registrar_uso_funcionalidade(
            db,
            "avaliacao-entrega-app",
            agora=datetime(2026, 9, 1, tzinfo=timezone.utc),
        )

    resultado = listar_evolucao_corepet(
        "erp",
        db,
        agora=datetime(2026, 10, 6, tzinfo=timezone.utc),
    )
    ids = {item["id"] for item in resultado["itens"]}

    assert "avaliacao-entrega-app" not in ids
    assert "grupos-empresas-transferencia-integrada" in ids


def test_metrica_de_uso_e_global_e_nao_guarda_empresa_cliente_ou_usuario():
    assert set(EvolucaoFuncionalidadeUso.__table__.columns.keys()) == {
        "item_id",
        "usos_total",
        "primeiro_uso_em",
        "ultimo_uso_em",
        "limiar_teste_atingido_em",
    }


def test_catalogo_rejeita_canal_desconhecido():
    try:
        listar_evolucao_corepet("canal_inexistente")
    except ValueError as exc:
        assert "Canal de evolucao invalido" in str(exc)
    else:
        raise AssertionError("Canal desconhecido deveria ser rejeitado")
