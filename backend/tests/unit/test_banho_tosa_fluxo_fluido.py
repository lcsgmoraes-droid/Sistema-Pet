from types import SimpleNamespace

from app.banho_tosa_api import atendimentos_routes
from app.banho_tosa_relatorios import _completar_snapshots_ausentes
from app.banho_tosa_schema_parts.operacional import BanhoTosaMoverEtapaInput


class _QueryVazia:
    def filter(self, *args, **kwargs):
        return self

    def all(self):
        return []


class _DbFake:
    def __init__(self):
        self.commits = 0
        self.flushes = 0

    def query(self, *args, **kwargs):
        return _QueryVazia()

    def add(self, *args, **kwargs):
        return None

    def flush(self):
        self.flushes += 1

    def commit(self):
        self.commits += 1


def _preparar_rota(monkeypatch, atendimento):
    chamadas = {"recalculo": 0, "venda": 0}
    monkeypatch.setattr(
        atendimentos_routes,
        "_get_tenant",
        lambda current: (SimpleNamespace(id=91), "tenant-dev"),
    )
    monkeypatch.setattr(
        atendimentos_routes,
        "obter_atendimento_ou_404",
        lambda db, tenant_id, atendimento_id: atendimento,
    )
    monkeypatch.setattr(
        atendimentos_routes,
        "obter_ou_criar_configuracao",
        lambda db, tenant_id: SimpleNamespace(
            fluxo_etapas=["chegou", "banho", "secagem", "tosa", "pronto"]
        ),
    )
    monkeypatch.setattr(
        atendimentos_routes,
        "aplicar_status_atendimento",
        lambda db, tenant_id, item, status: setattr(item, "status", status),
    )
    monkeypatch.setattr(
        atendimentos_routes,
        "recalcular_snapshot_atendimento",
        lambda db, tenant_id, atendimento_id: chamadas.__setitem__(
            "recalculo", chamadas["recalculo"] + 1
        ),
    )
    monkeypatch.setattr(
        atendimentos_routes,
        "gerar_venda_atendimento",
        lambda db, tenant_id, user_id, atendimento_id: chamadas.__setitem__(
            "venda", chamadas["venda"] + 1
        ),
    )
    monkeypatch.setattr(
        atendimentos_routes,
        "serializar_atendimento",
        lambda item, config: {
            "status": item.status,
            "observacoes_saida": item.observacoes_saida,
        },
    )
    return chamadas


def test_mover_para_pronto_recalcula_snapshot_de_custo(monkeypatch):
    atendimento = SimpleNamespace(
        id=12,
        status="em_tosa",
        etapas=[],
        pacote_credito_id=None,
        observacoes_saida=None,
    )
    chamadas = _preparar_rota(monkeypatch, atendimento)
    db = _DbFake()

    resposta = atendimentos_routes.mover_etapa_atendimento(
        atendimento_id=12,
        body=BanhoTosaMoverEtapaInput(tipo="pronto", iniciar_timer=False),
        db=db,
        current=object(),
    )

    assert resposta["status"] == "pronto"
    assert chamadas["recalculo"] == 1
    assert chamadas["venda"] == 0
    assert db.flushes == 1
    assert db.commits == 1


def test_entrega_salva_observacao_gera_venda_e_recalcula(monkeypatch):
    atendimento = SimpleNamespace(
        id=13,
        status="pronto",
        etapas=[],
        pacote_credito_id=None,
        observacoes_saida=None,
    )
    chamadas = _preparar_rota(monkeypatch, atendimento)
    db = _DbFake()

    resposta = atendimentos_routes.mover_etapa_atendimento(
        atendimento_id=13,
        body=BanhoTosaMoverEtapaInput(
            tipo="entregue",
            iniciar_timer=False,
            observacoes_saida="Orientado sobre a escovação.",
        ),
        db=db,
        current=object(),
    )

    assert resposta == {
        "status": "entregue",
        "observacoes_saida": "Orientado sobre a escovação.",
    }
    assert chamadas["venda"] == 1
    assert chamadas["recalculo"] == 1


def test_relatorio_calcula_previa_quando_snapshot_historico_nao_existe(monkeypatch):
    atendimento = SimpleNamespace(id=22)
    snapshot = SimpleNamespace(as_dict=lambda: {"valor_cobrado": 90, "custo_total": 30})
    monkeypatch.setattr(
        "app.banho_tosa_relatorios.montar_snapshot_atendimento",
        lambda db, tenant_id, atendimento_id: (atendimento, snapshot, {}),
    )

    resultado = _completar_snapshots_ausentes(
        db=object(),
        tenant_id="tenant-dev",
        atendimentos=[atendimento],
        snapshots={},
    )

    assert resultado[22].valor_cobrado == 90
    assert resultado[22].custo_total == 30
