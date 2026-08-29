from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.ofertas_estudio_routes import _status_publicacao
from app.ofertas_estudio_schemas import OfertaPublicacaoCreate
from app.services.ofertas_estudio_service import (
    produto_publicavel,
    serializar_produto_oferta,
)


def _lote(*, dias=10, quantidade=5, status="ativo", lote_id=1):
    validade = datetime.utcnow() + timedelta(days=dias)
    return SimpleNamespace(
        id=lote_id,
        nome_lote="L-001",
        data_validade=validade,
        quantidade_disponivel=quantidade,
        status=status,
        ordem_entrada=1,
        dias_para_vencer=dias,
    )


def _produto(**overrides):
    dados = {
        "id": 10,
        "codigo": "RAC-10",
        "nome": "Ração teste",
        "ativo": True,
        "situacao": True,
        "is_sellable": True,
        "estoque_atual": 12,
        "estoque_maximo": 20,
        "controle_lote": True,
        "data_validade": None,
        "lotes": [_lote()],
        "imagem_principal": "/uploads/produtos/racao.webp",
        "imagens": [],
        "preco_venda": 25,
        "preco_app": 24,
        "preco_ecommerce": 26,
        "preco_custo": 15,
        "unidade": "UN",
    }
    dados.update(overrides)
    return SimpleNamespace(**dados)


def test_produto_vencido_ou_sem_lote_valido_nao_pode_ser_publicado():
    assert produto_publicavel(_produto(lotes=[_lote(dias=-1)])) is False
    assert produto_publicavel(_produto(lotes=[_lote(quantidade=0)])) is False
    assert produto_publicavel(_produto(estoque_atual=0)) is False


def test_produto_valido_prioriza_preco_erp_e_expoe_divergencias():
    produto = _produto()

    item = serializar_produto_oferta(produto)

    assert item["preco_erp"] == 25
    assert item["preco_app"] == 24
    assert item["preco_ecommerce"] == 26
    assert item["precos_divergentes"] is True
    assert item["lote_validade"]["id"] == 1


def test_contrato_exige_preco_positivo_e_ao_menos_um_produto():
    base = {
        "titulo": "Ofertas da semana",
        "periodicidade": "semanal",
        "tipo_arte": "jornal",
        "formato": "quadrado",
        "inicio_em": datetime.now(timezone.utc),
        "fim_em": datetime.now(timezone.utc) + timedelta(days=7),
        "expira_em": datetime.now(timezone.utc) + timedelta(days=7),
        "produtos": [],
    }

    with pytest.raises(ValidationError):
        OfertaPublicacaoCreate.model_validate(base)

    base["produtos"] = [{"produto_id": 10, "preco_arte": 0}]
    with pytest.raises(ValidationError):
        OfertaPublicacaoCreate.model_validate(base)

    base["produtos"] = [{"produto_id": 10, "preco_arte": 20}]
    base["expira_em"] = datetime.utcnow() + timedelta(days=7)
    with pytest.raises(ValidationError):
        OfertaPublicacaoCreate.model_validate(base)


def test_status_da_publicacao_respeita_agendamento_expiracao_e_desativacao():
    agora = datetime.now(timezone.utc)
    publicacao = SimpleNamespace(
        inicio_em=agora + timedelta(hours=1),
        fim_em=agora + timedelta(days=1),
        expira_em=agora + timedelta(days=1),
        desativada_em=None,
    )
    assert _status_publicacao(publicacao) == "agendada"

    publicacao.desativada_em = agora
    assert _status_publicacao(publicacao) == "desativada"

    publicacao.desativada_em = None
    publicacao.fim_em = agora - timedelta(seconds=1)
    assert _status_publicacao(publicacao) == "expirada"
