import base64
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app import ofertas_estudio_routes
from app.ofertas_estudio_routes import _serializar_publicacao, _status_publicacao
from app.ofertas_estudio_schemas import OfertaPublicacaoCreate
from app.routes.ecommerce_public import _publicacao_habilitada_no_canal
from app.services import ofertas_estudio_ai
from app.services.ofertas_estudio_ai import (
    _prompt,
    diretorio_storage_tenant,
    gerar_imagem_profissional,
    resolver_chave_openai_tenant,
    segmento_tenant_storage,
)
from app.services.ofertas_estudio_service import (
    produto_publicavel,
    resumir_navegacao_publicacao,
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


def test_produto_expoe_galeria_ordenada_sem_duplicar_a_principal():
    produto = _produto(
        imagens=[
            SimpleNamespace(
                id=3,
                url="/uploads/produtos/lateral.webp",
                ordem=2,
                e_principal=False,
            ),
            SimpleNamespace(
                id=2,
                url="/uploads/produtos/racao.webp",
                ordem=1,
                e_principal=True,
            ),
        ]
    )

    item = serializar_produto_oferta(produto)

    assert [imagem["url"] for imagem in item["imagens"]] == [
        "/uploads/produtos/racao.webp",
        "/uploads/produtos/lateral.webp",
    ]


def test_geracao_le_imagem_cadastrada_pelo_backend(monkeypatch):
    produto = _produto(
        imagem_principal=(
            "https://img.corepet.com.br/produtos/tenant/10/originais/racao.webp"
        )
    )
    imagem_lida = SimpleNamespace(content=b"imagem-webp", content_type="image/webp")
    monkeypatch.setattr(
        ofertas_estudio_routes,
        "read_product_image_by_public_url",
        lambda _url: imagem_lida,
    )

    content, content_type = ofertas_estudio_routes._ler_imagem_referencia_produto(
        produto,
        "12345678-1234-5678-1234-567812345678",
        produto.imagem_principal,
    )

    assert content == b"imagem-webp"
    assert content_type == "image/webp"


def test_geracao_rejeita_url_que_nao_pertence_ao_produto():
    produto = _produto()

    with pytest.raises(HTTPException) as exc_info:
        ofertas_estudio_routes._ler_imagem_referencia_produto(
            produto,
            "12345678-1234-5678-1234-567812345678",
            "https://exemplo.com/imagem-nao-cadastrada.webp",
        )

    assert getattr(exc_info.value, "status_code", None) == 400


def test_prompt_usuario_preserva_identidade_real_do_produto():
    prompt = _prompt(
        "Racao Premium",
        "profissional",
        "quadrada",
        "Colocar em uma bancada moderna com fundo verde",
    )

    assert "bancada moderna com fundo verde" in prompt
    assert "nunca pode alterar" in prompt
    assert "rotulo" in prompt


def test_gpt_image_2_nao_recebe_parametros_incompativeis(monkeypatch, tmp_path):
    chamadas = {}

    class FakeImages:
        def edit(self, **kwargs):
            chamadas.update(kwargs)
            return SimpleNamespace(
                data=[SimpleNamespace(b64_json=base64.b64encode(b"png").decode())]
            )

    class FakeOpenAI:
        def __init__(self, **kwargs):
            chamadas["client"] = kwargs
            self.images = FakeImages()

    import openai

    monkeypatch.setattr(openai, "OpenAI", FakeOpenAI)
    monkeypatch.setattr(ofertas_estudio_ai, "UPLOAD_DIR", tmp_path)

    url = gerar_imagem_profissional(
        api_key="chave-teste",
        tenant_id="12345678-1234-5678-1234-567812345678",
        produto_id=10,
        produto_nome="Racao Premium",
        file_bytes=b"imagem",
        content_type="image/png",
        estilo="profissional",
        orientacao="quadrada",
        prompt_usuario="fundo verde",
    )

    assert chamadas["model"] == "gpt-image-2"
    assert "input_fidelity" not in chamadas
    assert "response_format" not in chamadas
    assert chamadas["output_format"] == "png"
    assert url.startswith("/uploads/ofertas/12345678123456781234567812345678/ia/")


def test_chave_global_e_fallback_quando_empresa_nao_tem_chave(monkeypatch):
    class FakeDb:
        def query(self, _model):
            raise RuntimeError("tabela indisponivel")

    monkeypatch.setenv("OPENAI_API_KEY", "chave-global")

    assert resolver_chave_openai_tenant(FakeDb(), "tenant") == "chave-global"


def test_publicacao_so_aparece_nos_canais_marcados():
    configuracao = {"canais": {"app": True, "ecommerce": False}}

    assert _publicacao_habilitada_no_canal(configuracao, "app") is True
    assert _publicacao_habilitada_no_canal(configuracao, "ecommerce") is False
    assert _publicacao_habilitada_no_canal({}, "app") is False


def test_listagem_da_campanha_informa_os_canais_publicados():
    agora = datetime.now(timezone.utc)
    publicacao = SimpleNamespace(
        id=12,
        titulo="Jornal semanal",
        periodicidade="semanal",
        tipo_arte="jornal",
        formato="quadrado",
        inicio_em=agora,
        fim_em=agora + timedelta(days=7),
        expira_em=agora + timedelta(days=7),
        desativada_em=None,
        imagens_urls=["/uploads/ofertas/tenant/12/pagina.png"],
        produtos_snapshot=[{"produto_id": 1}],
        configuracao={"canais": {"app": True, "ecommerce": True}},
        indice_publico=SimpleNamespace(token="t" * 32),
        created_at=agora,
    )

    resultado = _serializar_publicacao(publicacao, incluir_snapshot=False)

    assert resultado["id"] == 12
    assert resultado["canais"] == {"app": True, "ecommerce": True}
    assert "configuracao" not in resultado


def test_resumo_de_navegacao_diferencia_jornal_e_produto_por_pagina():
    individual = resumir_navegacao_publicacao(
        "individual",
        ["/pagina-1.png", "/pagina-2.png", "/pagina-3.png"],
        [{"produto_id": 1}, {"produto_id": 2}, {"produto_id": 3}],
    )
    jornal = resumir_navegacao_publicacao(
        "jornal",
        ["/pagina-1.png", "/pagina-2.png"],
        [{"produto_id": 1}, {"produto_id": 2}, {"produto_id": 3}],
    )
    unica = resumir_navegacao_publicacao(
        "individual", ["/pagina-1.png"], [{"produto_id": 1}]
    )

    assert individual == {
        "total_paginas": 3,
        "total_produtos": 3,
        "modo_paginacao": "produto_por_pagina",
        "cta_label": "Ver jornal — 3 ofertas",
    }
    assert jornal["cta_label"] == "Ver jornal — 2 páginas"
    assert unica["cta_label"] == "Ver oferta"


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


def test_storage_normaliza_tenant_e_recusa_segmento_de_caminho():
    tenant = "12345678-1234-5678-1234-567812345678"

    assert segmento_tenant_storage(tenant) == "12345678123456781234567812345678"
    with pytest.raises(ValueError):
        diretorio_storage_tenant(tenant, "../fora")
