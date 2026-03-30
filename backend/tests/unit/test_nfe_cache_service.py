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

    primeiro = upsert_nota_cache(db, tenant_id, nota, source="bling_api", resumo_payload=nota)
    segundo = upsert_nota_cache(db, tenant_id, nota, source="bling_api", resumo_payload=nota)

    assert primeiro is segundo
    assert len(db.new) == 1
