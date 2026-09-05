from io import BytesIO

import pytest
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.produtos_models import Produto, ProdutoImagem
from app.routes import app_mobile_funcionario_produto_imagens as fotos_routes
from app.services import product_image_storage as storage
from tests.unit.test_app_mobile_produto_rapido import (
    TENANT_A,
    TENANT_B,
    ambiente as ambiente,
    cadastrar,
    consultar,
)


@pytest.fixture
def db_session(db_engine):
    # Cada request pode commitar/rollback sem desfazer o produto salvo antes.
    # O savepoint permite testar a recuperacao de upload com a transacao real.
    with db_engine.connect() as connection:
        transaction = connection.begin()
        if connection.dialect.name == "sqlite":
            connection.exec_driver_sql("BEGIN")
        with Session(
            bind=connection, join_transaction_mode="create_savepoint"
        ) as session:
            yield session
        transaction.rollback()


def consultar_sku(client, codigo):
    return client.get(
        "/app/funcionario/produtos/consultar-sku", params={"codigo": codigo}
    )


def test_sku_manual_e_descricao_sao_salvos_no_cadastro_normal(ambiente):
    client, db, _ = ambiente
    assert consultar_sku(client, " sku-123 ").json() == {
        "codigo": "SKU-123",
        "disponivel": True,
        "produto": None,
    }
    criado = cadastrar(
        client, codigo=" sku-123 ", descricao_curta="  Ração sabor frango.  "
    )
    assert criado.status_code == 201, criado.text
    assert criado.json()["codigo"] == "SKU-123"
    assert criado.json()["descricao_curta"] == "Ração sabor frango."
    produto = db.execute(select(Produto.__table__)).mappings().one()
    assert produto["descricao_curta"] == "Ração sabor frango."
    assert consultar_sku(client, "sKu-123").json()["disponivel"] is False


def test_sku_ocupado_por_inativo_rejeita_sem_sobrescrever_produto(ambiente):
    client, db, _ = ambiente
    db.execute(
        Produto.__table__.insert().values(
            tenant_id=TENANT_A,
            user_id=1,
            codigo=" SKU-ANTIGO ",
            nome="Antigo",
            ativo=False,
        )
    )
    db.commit()
    assert consultar_sku(client, "sku-antigo").json()["disponivel"] is False
    resposta = cadastrar(client, codigo="sku-antigo")
    assert resposta.status_code == 409
    assert resposta.json()["detail"]["campo"] == "codigo"
    assert len(db.execute(select(Produto.__table__)).all()) == 1


def test_sku_e_conferido_novamente_mesmo_depois_de_consulta_livre(ambiente):
    client, _, _ = ambiente
    assert consultar_sku(client, "SKU-1").json()["disponivel"] is True
    assert (
        cadastrar(client, codigo="SKU-1", codigo_barras="1234567890123").status_code
        == 201
    )
    assert cadastrar(client, codigo="sku-1").status_code == 409


def test_sku_em_outra_empresa_nao_impede_cadastro(ambiente):
    client, db, _ = ambiente
    db.execute(
        Produto.__table__.insert().values(
            tenant_id=TENANT_B,
            user_id=1,
            codigo="SKU-1",
            nome="Outra loja",
        )
    )
    db.commit()
    assert consultar_sku(client, "SKU-1").json()["disponivel"] is True
    assert cadastrar(client, codigo="SKU-1").status_code == 201


@pytest.mark.parametrize("codigo", [None, "", "   "])
def test_sku_vazio_gera_automaticamente(ambiente, codigo):
    client, _, _ = ambiente
    resposta = cadastrar(client, codigo=codigo)
    assert resposta.status_code == 201, resposta.text
    assert resposta.json()["codigo"].startswith("APP-")


@pytest.mark.parametrize(
    "payload", [{"codigo": "X" * 51}, {"descricao_curta": "X" * 1001}]
)
def test_respeita_tamanho_do_sku_e_descricao(ambiente, payload):
    client, _, _ = ambiente
    assert cadastrar(client, **payload).status_code == 422


@pytest.fixture
def storage_fotos(tmp_path, monkeypatch):
    pasta = tmp_path / "uploads" / "produtos"
    monkeypatch.setattr(storage, "_local_base_dir", lambda: pasta)
    monkeypatch.setattr(storage, "_local_public_prefix", lambda: "/uploads/produtos")
    monkeypatch.setattr(storage.settings, "PRODUCT_IMAGE_STORAGE_BACKEND", "local")
    return pasta


def foto_png(cor="red"):
    buffer = BytesIO()
    Image.new("RGB", (32, 32), cor).save(buffer, format="PNG")
    return buffer.getvalue()


def enviar_foto(client, produto_id, conteudo=None, mime="image/png"):
    return client.post(
        f"/app/funcionario/produtos/{produto_id}/imagens",
        files={
            "file": ("foto.png", foto_png() if conteudo is None else conteudo, mime),
        },
    )


def test_fotos_salvas_no_erp_com_principal_miniatura_e_reenvio_sem_duplicar(
    ambiente, storage_fotos
):
    client, db, _ = ambiente
    produto = cadastrar(client).json()
    primeira = enviar_foto(client, produto["id"])
    assert primeira.status_code == 200, primeira.text
    assert primeira.json()["e_principal"] is True
    assert primeira.json()["thumbnail_url"].endswith(".webp")
    novamente = enviar_foto(client, produto["id"])
    assert novamente.json()["id"] == primeira.json()["id"]
    segunda = enviar_foto(client, produto["id"], foto_png("blue"))
    assert segunda.json()["e_principal"] is False
    assert segunda.json()["ordem"] == 2
    assert consultar(client).json()["imagem_principal"] == primeira.json()["url"]
    assert len(db.execute(select(ProdutoImagem.__table__)).all()) == 2
    assert len(list(storage_fotos.rglob("*.webp"))) == 4


def test_limite_de_cinco_fotos_ainda_permite_reenvio_da_mesma(ambiente, storage_fotos):
    client, _, _ = ambiente
    produto_id = cadastrar(client).json()["id"]
    for cor in ["red", "blue", "green", "white", "black"]:
        assert enviar_foto(client, produto_id, foto_png(cor)).status_code == 200
    assert enviar_foto(client, produto_id, foto_png("yellow")).status_code == 400
    assert enviar_foto(client, produto_id, foto_png("red")).status_code == 200


@pytest.mark.parametrize(
    "conteudo,mime",
    [
        (b"nao sou imagem", "image/jpeg"),
        (b"", "image/png"),
        (b"<svg/>", "image/svg+xml"),
    ],
)
def test_rejeita_foto_invalida_sem_apagar_o_produto(
    ambiente, storage_fotos, conteudo, mime
):
    client, db, _ = ambiente
    produto_id = cadastrar(client).json()["id"]
    assert enviar_foto(client, produto_id, conteudo, mime).status_code == 400
    assert len(db.execute(select(Produto.__table__)).all()) == 1
    assert len(db.execute(select(ProdutoImagem.__table__)).all()) == 0
    assert not list(storage_fotos.rglob("*.webp"))


def test_foto_grande_e_bloqueada_antes_do_storage(ambiente, storage_fotos, monkeypatch):
    client, _, _ = ambiente
    produto_id = cadastrar(client).json()["id"]
    monkeypatch.setattr(fotos_routes.settings, "PRODUCT_IMAGE_UPLOAD_MAX_BYTES", 10)
    assert enviar_foto(client, produto_id).status_code == 400
    assert not list(storage_fotos.rglob("*.webp"))


def test_cliente_nao_consulta_sku_nem_envia_fotos(ambiente, storage_fotos):
    client, _, user = ambiente
    produto_id = cadastrar(client).json()["id"]
    user.permitido = False
    assert consultar_sku(client, "SKU-1").status_code == 403
    assert enviar_foto(client, produto_id).status_code == 403


def test_nao_anexa_foto_ao_produto_de_outra_empresa(ambiente, storage_fotos):
    client, db, user = ambiente
    produto_id = cadastrar(client).json()["id"]
    user.tenant_id = TENANT_B
    assert enviar_foto(client, produto_id).status_code == 404
    assert len(db.execute(select(ProdutoImagem.__table__)).all()) == 0


def test_falha_no_storage_preserva_produto_e_permite_reenviar(
    ambiente, storage_fotos, monkeypatch
):
    client, db, _ = ambiente
    produto_id = cadastrar(client).json()["id"]
    original = fotos_routes.save_product_image_variants
    monkeypatch.setattr(
        fotos_routes,
        "save_product_image_variants",
        lambda **_: (_ for _ in ()).throw(OSError("storage indisponivel")),
    )
    assert enviar_foto(client, produto_id).status_code == 503
    assert len(db.execute(select(ProdutoImagem.__table__)).all()) == 0
    assert consultar(client).json()["id"] == produto_id
    monkeypatch.setattr(fotos_routes, "save_product_image_variants", original)
    assert enviar_foto(client, produto_id).status_code == 200


def test_falha_de_banco_remove_arquivo_orfao_sem_apagar_produto(
    ambiente, storage_fotos, monkeypatch
):
    client, db, _ = ambiente
    produto_id = cadastrar(client).json()["id"]
    original = db.flush

    def falhar_ao_gravar_imagem(*args, **kwargs):
        if any(isinstance(item, ProdutoImagem) for item in db.new):
            raise RuntimeError("Falha simulada de banco")
        return original(*args, **kwargs)

    monkeypatch.setattr(db, "flush", falhar_ao_gravar_imagem)
    assert enviar_foto(client, produto_id).status_code == 503
    assert not list(storage_fotos.rglob("*.webp"))
    assert consultar(client).json()["id"] == produto_id
    assert not db.execute(select(ProdutoImagem.__table__)).all()
