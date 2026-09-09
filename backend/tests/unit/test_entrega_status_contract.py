import inspect
import pytest
from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

from app.api.endpoints import (
    rotas_entrega_core_routes,
    rotas_entrega_criacao_routes,
    rotas_entrega_otimizacao_routes,
)
from app.api.endpoints.rotas_entrega import (
    DeliveryActor,
    marcar_parada_nao_entregue,
    _sincronizar_venda_entregue_por_parada,
)
from app.routes import ecommerce_entregador
from app.rotas_entrega_models import RotaEntrega, RotaEntregaParada
from app.vendas.entrega_filters import filtros_venda_entrega_operacional
from app.vendas_models import Venda
from app.vendas_routes import _resolver_status_entrega_atualizacao


def test_atualizacao_de_venda_preserva_status_entrega_concluido():
    assert _resolver_status_entrega_atualizacao(True, "entregue") == "entregue"
    assert _resolver_status_entrega_atualizacao(True, "em_rota") == "em_rota"
    assert _resolver_status_entrega_atualizacao(True, "cancelada") == "cancelada"


def test_atualizacao_de_venda_define_pendente_apenas_para_entrega_nova():
    assert _resolver_status_entrega_atualizacao(True, None) == "pendente"
    assert _resolver_status_entrega_atualizacao(False, "entregue") is None


def test_entregas_abertas_incluem_pedido_online_pronto_para_rota():
    assert '"pronto"' in inspect.getsource(filtros_venda_entrega_operacional)

    funcoes = [
        rotas_entrega_core_routes.listar_vendas_pendentes_entrega,
        rotas_entrega_criacao_routes.criar_rota,
        ecommerce_entregador.listar_entregas_abertas,
        ecommerce_entregador.otimizar_entregas_selecionadas,
        ecommerce_entregador.criar_rota_por_entregador,
    ]

    for funcao in funcoes:
        source = inspect.getsource(funcao)
        assert "filtros_venda_entrega_operacional" in source


def test_fluxos_operacionais_nao_reaproveitam_vendas_canceladas():
    assert 'Venda.status != "cancelada"' in inspect.getsource(
        filtros_venda_entrega_operacional
    )

    funcoes = [
        rotas_entrega_core_routes.listar_vendas_pendentes_entrega,
        rotas_entrega_otimizacao_routes.otimizar_vendas_pendentes,
        rotas_entrega_otimizacao_routes.otimizar_vendas_selecionadas,
        ecommerce_entregador.listar_entregas_abertas,
        ecommerce_entregador.otimizar_entregas_selecionadas,
        ecommerce_entregador.criar_rota_por_entregador,
    ]

    for funcao in funcoes:
        assert "filtros_venda_entrega_operacional" in inspect.getsource(funcao)

    source_criar_rota = inspect.getsource(rotas_entrega_criacao_routes.criar_rota)
    assert source_criar_rota.count("filtros_venda_entrega_operacional") == 2


def test_retirada_na_loja_exige_nome_de_quem_retirou():
    from fastapi import HTTPException

    from app.vendas_routes import _resolver_retirado_por_conclusao

    venda_retirada = SimpleNamespace(tem_entrega=False)
    venda_entrega = SimpleNamespace(tem_entrega=True)

    assert _resolver_retirado_por_conclusao(venda_retirada, "  Osvaldo  ") == "Osvaldo"
    assert _resolver_retirado_por_conclusao(venda_entrega, "") is None

    try:
        _resolver_retirado_por_conclusao(venda_retirada, "")
    except HTTPException as exc:
        assert exc.status_code == 400
        assert "Informe quem retirou" in exc.detail
    else:
        raise AssertionError("Retirada sem nome deveria falhar")


def test_sincronizar_parada_entregue_atualiza_venda_para_pdv():
    entrega_em = datetime(2026, 4, 24, 10, 30)
    parada = SimpleNamespace(venda_id=10, status="pendente", data_entrega=None)
    venda = SimpleNamespace(
        id=10, tenant_id="tenant-1", status_entrega="em_rota", data_entrega=None
    )

    class QueryFake:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return venda

    class DbFake:
        def query(self, _model):
            return QueryFake()

    retorno = _sincronizar_venda_entregue_por_parada(
        DbFake(), parada, "tenant-1", entrega_em
    )

    assert retorno is venda
    assert parada.status == "entregue"
    assert parada.data_entrega == entrega_em
    assert venda.status_entrega == "entregue"
    assert venda.data_entrega == entrega_em


class _EntregaQueryFake:
    def __init__(self, db, model):
        self.db = db
        self.model = model

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        if self.model is RotaEntrega:
            return self.db.rota
        if self.model is RotaEntregaParada:
            return self.db.parada
        if self.model is Venda:
            return self.db.venda
        return None

    def count(self):
        if self.model is RotaEntregaParada:
            return len(self.db.paradas_restantes)
        return 0

    def order_by(self, *args):
        return self

    def all(self):
        return sorted(
            self.db.paradas_restantes, key=lambda parada: (parada.ordem, parada.id)
        )


class _EntregaDbFake:
    def __init__(self, rota, parada, venda, paradas_restantes):
        self.rota = rota
        self.parada = parada
        self.venda = venda
        self.paradas_restantes = list(paradas_restantes)
        self.deleted = []
        self.pending_delete = []
        self.commits = 0

    def query(self, model):
        return _EntregaQueryFake(self, model)

    def delete(self, obj):
        self.deleted.append(obj)
        self.pending_delete.append(obj)

    def flush(self):
        for obj in self.pending_delete:
            if obj in self.paradas_restantes:
                self.paradas_restantes.remove(obj)
        self.pending_delete.clear()

    def commit(self):
        self.commits += 1


def _actor(tenant_id):
    return DeliveryActor(user=SimpleNamespace(id=1), tenant_id=tenant_id)


def test_nao_entregue_remove_rota_quando_ultima_parada_fica_fora_da_rota():
    tenant_id = uuid4()
    rota = SimpleNamespace(id=292, tenant_id=tenant_id, status="em_rota")
    parada = SimpleNamespace(
        id=10,
        rota_id=rota.id,
        venda_id=20,
        tenant_id=tenant_id,
        observacoes=None,
    )
    venda = SimpleNamespace(
        id=20, tenant_id=tenant_id, status_entrega="em_rota", observacoes_entrega=None
    )
    db = _EntregaDbFake(
        rota=rota, parada=parada, venda=venda, paradas_restantes=[parada]
    )

    resposta = marcar_parada_nao_entregue(
        rota_id=str(rota.id),
        parada_id=parada.id,
        motivo="cliente ausente",
        db=db,
        actor=_actor(tenant_id),
    )

    assert venda.status_entrega == "pendente"
    assert parada in db.deleted
    assert rota in db.deleted
    assert resposta["rota_removida"] is True


def test_nao_entregue_preserva_rota_quando_ainda_tem_paradas():
    tenant_id = uuid4()
    rota = SimpleNamespace(id=298, tenant_id=tenant_id, status="em_rota")
    parada_removida = SimpleNamespace(
        id=11,
        rota_id=rota.id,
        venda_id=21,
        tenant_id=tenant_id,
        observacoes=None,
    )
    parada_restante = SimpleNamespace(
        id=12,
        rota_id=rota.id,
        venda_id=22,
        tenant_id=tenant_id,
        observacoes=None,
        ordem=3,
    )
    venda = SimpleNamespace(
        id=21, tenant_id=tenant_id, status_entrega="em_rota", observacoes_entrega=None
    )
    db = _EntregaDbFake(
        rota=rota,
        parada=parada_removida,
        venda=venda,
        paradas_restantes=[parada_removida, parada_restante],
    )

    resposta = marcar_parada_nao_entregue(
        rota_id=str(rota.id),
        parada_id=parada_removida.id,
        motivo="cliente ausente",
        db=db,
        actor=_actor(tenant_id),
    )

    assert parada_removida in db.deleted
    assert rota not in db.deleted
    assert resposta["rota_removida"] is False
    assert parada_restante.ordem == 1
    assert "cliente ausente" in venda.observacoes_entrega


@pytest.mark.parametrize("ultima_parada", [False, True])
@pytest.mark.parametrize("usar_payload", [False, True])
def test_app_nao_entregue_preserva_motivo_e_reorganiza_rota(
    monkeypatch, ultima_parada, usar_payload
):
    from app.api.endpoints import rotas_entrega

    monkeypatch.setattr(rotas_entrega, "ensure_rotas_entrega_schema", lambda db: None)
    tenant_id = uuid4()
    cliente = SimpleNamespace(id=100, auth_user_id=1, tenant_id=tenant_id)
    rota = SimpleNamespace(id=600, tenant_id=tenant_id, status="em_rota")
    parada = SimpleNamespace(
        id=11, rota_id=600, venda_id=21, ordem=2, tenant_id=tenant_id
    )
    outras = (
        []
        if ultima_parada
        else [
            SimpleNamespace(id=12, ordem=3),
            SimpleNamespace(id=10, ordem=1),
        ]
    )
    venda = SimpleNamespace(
        id=21, status_entrega="em_rota", observacoes_entrega="Entregar na portaria"
    )
    db = _EntregaDbFake(rota, parada, venda, [*outras, parada])
    motivo = "  TESTE cliente ausente  "

    resposta = ecommerce_entregador.marcar_parada_nao_entregue_entregador(
        rota_id="600",
        parada_id=11,
        motivo=None if usar_payload else motivo,
        payload=ecommerce_entregador.NaoEntreguePayload(motivo=motivo)
        if usar_payload
        else None,
        cliente=cliente,
        db=db,
    )

    assert venda.status_entrega == "pendente"
    assert venda.observacoes_entrega.startswith("Entregar na portaria\n")
    assert "Não entregue (rota 600): TESTE cliente ausente" in venda.observacoes_entrega
    assert parada in db.deleted
    assert resposta["rota_removida"] is ultima_parada
    assert resposta["paradas_restantes"] == len(outras)
    assert sorted(p.ordem for p in outras) == list(range(1, len(outras) + 1))
    assert db.commits == 1


@pytest.mark.parametrize("status", ["concluida", "cancelada"])
def test_nao_entregue_nao_altera_rota_encerrada(status):
    from fastapi import HTTPException

    tenant_id = uuid4()
    db = _EntregaDbFake(SimpleNamespace(id=600, status=status), None, None, [])
    with pytest.raises(HTTPException) as erro:
        marcar_parada_nao_entregue("600", 11, "cliente ausente", db, _actor(tenant_id))
    assert erro.value.status_code == 400
    assert db.deleted == []
    assert db.commits == 0
