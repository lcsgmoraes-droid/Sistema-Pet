from app.nfe_cache_models import BlingNotaFiscalCache
from app.services.nfe_cache_service import upsert_nota_cache


class _FakeQuery:
    def __init__(self, db):
        self.db = db

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.db.persistido


class _FakeDB:
    def __init__(self, persistido=None):
        self.persistido = persistido
        self.new = set()

    def query(self, model):
        return _FakeQuery(self)

    def add(self, obj):
        self.new.add(obj)


def test_upsert_nota_cache_reaproveita_registro_pendente_na_mesma_sessao():
    db = _FakeDB()
    tenant_id = "tenant-1"
    nota = {
        "id": "25441090209",
        "modelo": 55,
        "tipo": "nfe",
        "numero": "011084",
        "status": "Autorizada",
    }

    primeiro = upsert_nota_cache(
        db, tenant_id, nota, source="bling_api", resumo_payload=nota
    )
    segundo = upsert_nota_cache(
        db, tenant_id, nota, source="bling_api", resumo_payload=nota
    )

    assert primeiro is segundo
    assert len(db.new) == 1


def test_upsert_nota_cache_nao_rebaixa_autorizada_do_bling_para_pendente_do_pedido():
    persistido = BlingNotaFiscalCache(
        tenant_id="tenant-1",
        bling_id="25461868579",
        modelo=55,
        tipo="nfe",
        numero="011149",
        status="Autorizada",
        source="bling_api",
    )
    db = _FakeDB(persistido=persistido)

    nota = {
        "id": "25461868579",
        "modelo": 55,
        "tipo": "nfe",
        "numero": "011149",
        "status": "Pendente",
    }

    registro = upsert_nota_cache(
        db, "tenant-1", nota, source="pedido_integrado", resumo_payload=nota
    )

    assert registro is persistido
    assert registro.status == "Autorizada"
    assert registro.source == "bling_api"


def test_upsert_nota_cache_permite_upgrade_de_pendente_para_autorizada():
    persistido = BlingNotaFiscalCache(
        tenant_id="tenant-1",
        bling_id="25461868579",
        modelo=55,
        tipo="nfe",
        numero="011149",
        status="Pendente",
        source="pedido_integrado",
    )
    db = _FakeDB(persistido=persistido)

    nota = {
        "id": "25461868579",
        "modelo": 55,
        "tipo": "nfe",
        "numero": "011149",
        "status": "Autorizada",
    }

    registro = upsert_nota_cache(
        db, "tenant-1", nota, source="bling_api", resumo_payload=nota
    )

    assert registro is persistido
    assert registro.status == "Autorizada"
    assert registro.source == "bling_api"


def test_upsert_local_preserva_enriquecimento_para_tenant_dono_do_bling():
    persistido = BlingNotaFiscalCache(
        tenant_id="tenant-1",
        bling_id="25461868579",
        modelo=55,
        tipo="nfe",
        numero="011149",
        status="Autorizada",
        source="bling_detail",
    )
    db = _FakeDB(persistido=persistido)

    nota_local = {
        "id": "25461868579",
        "modelo": 55,
        "tipo": "nfe",
        "numero": "011149",
        "status": "Pendente",
    }

    registro = upsert_nota_cache(
        db, "tenant-1", nota_local, source="local_venda", resumo_payload=nota_local
    )

    assert registro.status == "Autorizada"
    assert registro.source == "bling_detail"


def test_upsert_local_remove_dados_remotos_para_tenant_sem_bling():
    persistido = BlingNotaFiscalCache(
        tenant_id="tenant-1",
        bling_id="25461868579",
        modelo=55,
        tipo="nfe",
        numero="nota-de-outra-empresa",
        status="Autorizada",
        source="bling_detail",
        cliente={"nome": "Cliente de outra empresa"},
        detalhe_payload={"dado": "remoto"},
    )
    db = _FakeDB(persistido=persistido)
    nota_local = {
        "id": "25461868579",
        "modelo": 55,
        "tipo": "nfe",
        "numero": "nota-local",
        "status": "Pendente",
        "cliente": {"nome": "Cliente local"},
    }

    registro = upsert_nota_cache(
        db,
        "tenant-1",
        nota_local,
        source="local_venda",
        resumo_payload=nota_local,
        substituir_origem_remota=True,
    )

    assert registro.numero == "nota-local"
    assert registro.status == "Pendente"
    assert registro.source == "local_venda"
    assert registro.cliente == {"nome": "Cliente local"}
    assert registro.detalhe_payload is None
