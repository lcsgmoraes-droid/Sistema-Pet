import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.schema import CreateTable

from app.caixa.auditoria import assinatura_item, incluir_composicao_comercial
from app.caixa.auditoria_routes import (
    ConferenciaItemSchema,
    conferir_item_caixa,
    obter_auditoria_caixa,
)
from app.models import AuditLog
from app.financeiro_models import ContaReceber, FormaPagamento, Recebimento
from app.vendas_models import Venda
from tests.unit.test_caixa_recebimentos_auditoria import (  # noqa: F401
    caixa_session,
    recebimentos,
)


@pytest.fixture
def caso(request):
    return request.getfixturevalue("recebimentos")


def consultar(caso):
    return obter_auditoria_caixa(caso.atual.id, caso.db, caso.auth)


def gravar(caso, tipo, item, estado, observacao=None):
    return conferir_item_caixa(
        caso.atual.id,
        ConferenciaItemSchema(
            tipo_item=tipo,
            item_id=item["id"],
            assinatura=item["assinatura"],
            estado=estado,
            conferido=estado == "ok",
            observacao=observacao,
        ),
        caso.db,
        caso.auth,
    )


@pytest.mark.parametrize(
    ("tipo", "lista"),
    [
        ("venda", "vendas"),
        ("pagamento", "pagamentos"),
        ("movimentacao", "movimentacoes"),
    ],
)
def test_tres_estados_persistem_historico_sem_mudar_valores(caso, tipo, lista):
    inicial = consultar(caso)
    item = inicial[lista][0]
    assert item["estado_conferencia"] == "pendente"
    assert not item["conferido"]
    assert not item["conferencia_alterada"]

    for estado in ["ok", "divergencia", "pendente"]:
        observacao = (
            "  Valor do comprovante diferente do registrado  "
            if estado == "divergencia"
            else None
        )
        resposta = gravar(caso, tipo, item, estado, observacao)
        assert resposta == {
            "success": True,
            "estado": estado,
            "conferido": estado == "ok",
        }
        atual = consultar(caso)
        item = atual[lista][0]
        assert item["estado_conferencia"] == estado
        assert item["conferido"] == (estado == "ok")
        assert not item["conferencia_alterada"]
        assert assinatura_item(item) == item["assinatura"]
        registro = item["conferencia"]
        assert registro["dados"]["estado"] == estado
        assert registro["dados"]["conferido"] == (estado == "ok")
        assert registro["observacao"] == (observacao.strip() if observacao else None)
        assert registro["dados"]["observacao"] == registro["observacao"]
        assert registro["usuario_id"] == caso.auth[0].id
        assert registro["usuario_nome"] == caso.auth[0].nome
        assert datetime.fromisoformat(registro["data"])
        assert atual["resumo"] == inicial["resumo"]

    assert [evento["dados"]["estado"] for evento in atual["historico"]] == [
        "pendente",
        "divergencia",
        "ok",
    ]
    assert caso.pagamentos[1].valor == 40
    assert caso.pagamentos[1].forma_pagamento == "PIX"
    assert caso.movimento.valor == 20
    assert caso.venda.total == 90


@pytest.mark.parametrize("conferido", [False, True])
def test_post_legado_apenas_booleano_deriva_estado(caso, conferido):
    item = consultar(caso)["pagamentos"][0]
    dados = ConferenciaItemSchema(
        tipo_item="pagamento",
        item_id=item["id"],
        assinatura=item["assinatura"],
        conferido=conferido,
    )
    conferir_item_caixa(caso.atual.id, dados, caso.db, caso.auth)
    atual = consultar(caso)["pagamentos"][0]
    assert atual["estado_conferencia"] == ("ok" if conferido else "pendente")
    assert atual["conferido"] == conferido
    assert not atual["conferencia_alterada"]


@pytest.mark.parametrize("conferido", [False, True])
def test_get_mapeia_auditoria_antiga_sem_regravar_historico(caso, conferido):
    item = consultar(caso)["pagamentos"][0]
    salvo = json.dumps(
        {
            "tipo_item": "pagamento",
            "item_id": item["id"],
            "assinatura": item["assinatura"],
            "conferido": conferido,
            "usuario_nome": "Operador legado",
        }
    )
    evento = AuditLog(
        tenant_id=caso.auth[1],
        user_id=caso.auth[0].id,
        action="caixa_conferencia",
        entity_type="caixa",
        entity_id=caso.atual.id,
        timestamp=datetime.now(timezone.utc),
        new_value=salvo,
        details="Conferência anterior",
    )
    caso.db.add(evento)
    caso.db.flush()
    atual = consultar(caso)["pagamentos"][0]
    esperado = "ok" if conferido else "pendente"
    assert atual["estado_conferencia"] == esperado
    assert atual["conferencia"]["dados"]["estado"] == esperado
    assert atual["conferido"] == conferido
    assert atual["conferencia"]["observacao"] == "Conferência anterior"
    assert not atual["conferencia_alterada"]
    assert evento.new_value == salvo
    assert not caso.db.dirty


@pytest.mark.parametrize(
    "campos",
    [
        {"conferido": False, "estado": "ok"},
        {"conferido": True, "estado": "pendente"},
        {"conferido": True, "estado": "divergencia", "observacao": "Diferença"},
        {"conferido": False, "estado": "divergencia"},
        {"conferido": False, "estado": "divergencia", "observacao": " \n\t "},
        {"conferido": False, "estado": "desconhecido"},
    ],
)
def test_validacao_rejeita_estado_incoerente_ou_divergencia_sem_observacao(campos):
    with pytest.raises(ValidationError):
        ConferenciaItemSchema(
            tipo_item="pagamento", item_id=1, assinatura="a" * 64, **campos
        )


@pytest.mark.parametrize(
    ("tipo", "lista"), [("venda", "vendas"), ("pagamento", "pagamentos")]
)
@pytest.mark.parametrize(
    "campo,valor", [("valor", 35), ("forma_pagamento", "Cartão de débito")]
)
def test_alteracao_invalida_estado_e_exige_nova_assinatura(
    caso, tipo, lista, campo, valor
):
    item = consultar(caso)[lista][0]
    gravar(caso, tipo, item, "divergencia", "Comprovante a conferir")
    assinatura_anterior = item["assinatura"]
    setattr(caso.pagamentos[1], campo, valor)
    caso.db.flush()
    atual = consultar(caso)[lista][0]
    assert atual["assinatura"] != assinatura_anterior
    assert assinatura_item(atual) == atual["assinatura"]
    assert atual["estado_conferencia"] == "pendente"
    assert not atual["conferido"]
    assert atual["conferencia_alterada"]
    assert atual["conferencia"]["dados"]["estado"] == "divergencia"
    assert atual["conferencia"]["observacao"] == "Comprovante a conferir"

    with pytest.raises(HTTPException) as erro:
        gravar(caso, tipo, item, "ok")
    assert erro.value.status_code == 409
    assert len(consultar(caso)["historico"]) == 1
    gravar(caso, tipo, atual, "ok")
    revisado = consultar(caso)
    assert revisado[lista][0]["estado_conferencia"] == "ok"
    assert revisado[lista][0]["conferido"]
    assert not revisado[lista][0]["conferencia_alterada"]
    assert len(revisado["historico"]) == 2
    assert revisado["historico"][-1]["dados"]["estado"] == "divergencia"


def test_conferencia_respeita_tenant_usuario_e_caixa_de_origem(caso):
    item = consultar(caso)["pagamentos"][0]
    gravar(caso, "pagamento", item, "ok")
    # Mesmo item/caixa em outro tenant nao pode substituir a ultima revisao.
    caso.db.execute(
        AuditLog.__table__.insert(),
        {
            "tenant_id": uuid4(),
            "user_id": 91,
            "action": "caixa_conferencia",
            "entity_type": "caixa",
            "entity_id": caso.atual.id,
            "timestamp": datetime.now(timezone.utc) + timedelta(days=1),
            "new_value": json.dumps(
                {
                    "tipo_item": "pagamento",
                    "item_id": item["id"],
                    "assinatura": item["assinatura"],
                    "estado": "divergencia",
                    "conferido": False,
                }
            ),
        },
    )
    atual = consultar(caso)
    assert atual["pagamentos"][0]["estado_conferencia"] == "ok"
    assert len(atual["historico"]) == 1
    dados = ConferenciaItemSchema(
        tipo_item="pagamento",
        item_id=item["id"],
        assinatura=item["assinatura"],
        conferido=False,
        estado="divergencia",
        observacao="Não permitido",
    )
    for auth in [
        (caso.auth[0], uuid4()),
        (SimpleNamespace(id=92, nome="Outro operador"), caso.auth[1]),
    ]:
        with pytest.raises(HTTPException) as erro:
            conferir_item_caixa(caso.atual.id, dados, caso.db, auth)
        assert erro.value.status_code == 404
    with pytest.raises(HTTPException) as erro:
        conferir_item_caixa(
            caso.atual.id,
            ConferenciaItemSchema(
                tipo_item="pagamento",
                item_id=caso.pagamentos[0].id,
                assinatura="a" * 64,
                conferido=True,
                estado="ok",
            ),
            caso.db,
            caso.auth,
        )
    assert erro.value.status_code == 404
    assert len(consultar(caso)["historico"]) == 1


def test_assinatura_preserva_hash_legado_e_ignora_so_metadados_de_conferencia():
    item = {"id": 5, "valor": 12.34, "forma_pagamento": "PIX"}
    legado = hashlib.sha256(
        json.dumps(item, sort_keys=True, ensure_ascii=False, default=str).encode(
            "utf-8"
        )
    ).hexdigest()
    assert assinatura_item(item) == legado
    assert (
        assinatura_item(
            {
                **item,
                "assinatura": legado,
                "conferido": True,
                "estado_conferencia": "ok",
                "conferencia_alterada": False,
                "conferencia": {"dados": {"estado": "ok"}},
            }
        )
        == legado
    )
    assert assinatura_item({**item, "forma_pagamento": "Cartão"}) != legado


@pytest.mark.parametrize("campo,valor", [("desconto_valor", 5), ("taxa_entrega", 5)])
def test_composicao_comercial_invalida_ok_sem_mudanca_no_total_salvo(
    caso, campo, valor
):
    item = consultar(caso)["vendas"][0]
    gravar(caso, "venda", item, "ok")
    setattr(caso.venda, campo, valor)
    caso.db.flush()
    atual = consultar(caso)["vendas"][0]
    assert assinatura_item(
        {k: v for k, v in item.items() if k != "composicao_comercial"}
    ) == assinatura_item(
        {k: v for k, v in atual.items() if k != "composicao_comercial"}
    )
    assert atual["assinatura"] != item["assinatura"]
    assert atual["estado_conferencia"] == "pendente"
    assert atual["conferencia_alterada"]
    assert not atual["conferido"]
    assert atual["composicao_comercial"] != item["composicao_comercial"]
    # Composicao enviada pelo cliente nao substitui o calculo do servidor.
    dados = ConferenciaItemSchema(
        tipo_item="venda",
        item_id=item["id"],
        conferido=True,
        estado="ok",
        assinatura=item["assinatura"],
        composicao_comercial=item["composicao_comercial"],
    )
    assert "composicao_comercial" not in dados.model_dump()
    with pytest.raises(HTTPException) as erro:
        conferir_item_caixa(caso.atual.id, dados, caso.db, caso.auth)
    assert erro.value.status_code == 409


@pytest.fixture
def legado_com_conta(caso):
    # Tabelas adicionais so no banco/schema descartavel da fixture.
    with caso.db.get_bind().begin() as connection:
        for model in (FormaPagamento, Recebimento):
            connection.execute(
                CreateTable(model.__table__, include_foreign_key_constraints=[])
            )
    venda = Venda(
        tenant_id=caso.auth[1],
        numero_venda="LEGADO-CONTA",
        caixa_id=caso.atual.id,
        user_id=91,
        vendedor_id=91,
        subtotal=100,
        total=100,
        status="baixa_parcial",
        data_venda=datetime(2026, 10, 9, 12),
        canal="loja_fisica",
    )
    forma = FormaPagamento(tenant_id=caso.auth[1], nome="PIX", tipo="pix", user_id=91)
    caso.db.add_all([venda, forma])
    caso.db.flush()
    conta = ContaReceber(
        tenant_id=caso.auth[1],
        venda_id=venda.id,
        descricao="Parcela legada",
        valor_original=100,
        valor_final=100,
        valor_recebido=0,
        status="parcial",
        user_id=91,
        dre_subcategoria_id=1,
        canal="loja_fisica",
        data_emissao=date(2026, 10, 9),
        data_vencimento=date(2026, 11, 9),
    )
    caso.db.add(conta)
    caso.db.flush()
    return SimpleNamespace(caso=caso, venda=venda, conta=conta, forma=forma)


def venda_legada(legado):
    return next(
        item
        for item in consultar(legado.caso)["vendas"]
        if item["id"] == legado.venda.id
    )


@pytest.mark.parametrize("origem", ["conta_legada", "recebimento"])
def test_baixa_sem_venda_pagamento_invalida_conferencia(legado_com_conta, origem):
    legado = legado_com_conta
    caso = legado.caso
    item = venda_legada(legado)
    assert item["composicao_comercial"]["valor_pago"] == 0
    gravar(caso, "venda", item, "ok")
    legado.conta.valor_recebido = 20
    if origem == "recebimento":
        caso.db.add(
            Recebimento(
                tenant_id=caso.auth[1],
                conta_receber_id=legado.conta.id,
                forma_pagamento_id=legado.forma.id,
                valor_recebido=20,
                data_recebimento=date(2026, 10, 9),
                user_id=91,
            )
        )
    caso.db.flush()
    atual = venda_legada(legado)
    assert atual["pagamentos"] == item["pagamentos"] == []
    assert atual["total"] == item["total"] == 100
    assert atual["composicao_comercial"]["valor_pago"] == 20
    assert atual["composicao_comercial"]["em_aberto"] == 80
    assert atual["estado_conferencia"] == "pendente"
    assert atual["conferencia_alterada"]
    assert not atual["conferido"]
    with pytest.raises(HTTPException) as erro:
        gravar(caso, "venda", item, "ok")
    assert erro.value.status_code == 409


@pytest.mark.parametrize("forma_nova", ["Cartao de debito", "Credito Cliente"])
def test_forma_e_beneficios_do_recebimento_legado_tambem_invalidam_ok(
    legado_com_conta, forma_nova
):
    legado = legado_com_conta
    caso = legado.caso
    legado.conta.valor_recebido = 20
    caso.db.add(
        Recebimento(
            tenant_id=caso.auth[1],
            conta_receber_id=legado.conta.id,
            forma_pagamento_id=legado.forma.id,
            valor_recebido=20,
            data_recebimento=date(2026, 10, 9),
            user_id=91,
        )
    )
    caso.db.flush()
    item = venda_legada(legado)
    gravar(caso, "venda", item, "ok")
    legado.forma.nome = forma_nova
    caso.db.flush()
    atual = venda_legada(legado)
    assert item["pagamentos"] == atual["pagamentos"] == []
    assert atual["estado_conferencia"] == "pendente"
    assert atual["conferencia_alterada"]
    assert (
        atual["composicao_comercial"]["pagamentos"][0]["forma_pagamento"] == forma_nova
    )
    assert atual["composicao_comercial"]["creditos_utilizados"] == (
        20 if forma_nova == "Credito Cliente" else 0
    )


def test_ok_legado_com_hash_incompleto_volta_pendente_sem_apagar_historico(caso):
    item = consultar(caso)["vendas"][0]
    assinatura_legada = assinatura_item(
        {k: v for k, v in item.items() if k != "composicao_comercial"}
    )
    salvo = json.dumps(
        {
            "tipo_item": "venda",
            "item_id": item["id"],
            "conferido": True,
            "assinatura": assinatura_legada,
            "usuario_nome": "Operador anterior",
        }
    )
    evento = AuditLog(
        tenant_id=caso.auth[1],
        user_id=91,
        action="caixa_conferencia",
        entity_type="caixa",
        entity_id=caso.atual.id,
        new_value=salvo,
        details="Conferencia legada preservada",
        timestamp=datetime.now(timezone.utc),
    )
    caso.db.add(evento)
    caso.db.flush()
    atual = consultar(caso)["vendas"][0]
    assert atual["estado_conferencia"] == "pendente"
    assert atual["conferencia_alterada"]
    assert not atual["conferido"]
    assert atual["conferencia"]["dados"]["estado"] == "ok"
    assert atual["conferencia"]["observacao"] == "Conferencia legada preservada"
    assert evento.new_value == salvo


def test_ordem_de_consulta_dos_pagamentos_comerciais_nao_altera_assinatura():
    pagamentos = [
        {"id": "recebimento-2", "origem": "recebimento", "valor": 20},
        {"id": 1, "origem": "pagamento", "valor": 30},
    ]
    resumo = {
        "vendas_periodo": {"detalhes": [{"venda_id": 1, "pagamentos": pagamentos}]}
    }
    primeira = incluir_composicao_comercial(
        None, vendas=[{"venda_id": 1}], resumo=resumo, tenant_id=uuid4()
    )[0]
    pagamentos.reverse()
    segunda = incluir_composicao_comercial(
        None, vendas=[{"venda_id": 1}], resumo=resumo, tenant_id=uuid4()
    )[0]
    assert assinatura_item(primeira) == assinatura_item(segunda)
