from types import SimpleNamespace

from app.operadoras_models import OperadoraCartao
from app.services.card_operator_defaults import (
    DEFAULT_CARD_OPERATOR_PRESETS,
    ensure_card_operator_presets,
    operator_matches_preset,
)


class _FakeQuery:
    def __init__(self, records):
        self.records = records

    def filter(self, *_args, **_kwargs):
        return self

    def all(self):
        return list(self.records)


class _FakeSession:
    def __init__(self, records=None):
        self.records = list(records or [])

    def query(self, model):
        assert model is OperadoraCartao
        return _FakeQuery(self.records)

    def add(self, record):
        self.records.append(record)


def test_presets_sao_inativos_e_idempotentes_sem_duplicar_nome_personalizado():
    db = _FakeSession(
        [SimpleNamespace(nome="Stone - Loja Centro", codigo=None, tenant_id="tenant")]
    )

    first = ensure_card_operator_presets(db, tenant_id="tenant", user_id=7)
    second = ensure_card_operator_presets(db, tenant_id="tenant", user_id=7)

    assert first == {"created": len(DEFAULT_CARD_OPERATOR_PRESETS) - 1, "skipped": 1}
    assert second == {"created": 0, "skipped": len(DEFAULT_CARD_OPERATOR_PRESETS)}
    created = [record for record in db.records if isinstance(record, OperadoraCartao)]
    assert created
    assert all(record.ativo is False for record in created)
    assert all(record.padrao is False for record in created)
    assert all(record.taxa_debito is None for record in created)
    assert all(record.taxa_credito_vista is None for record in created)
    assert all(record.taxa_credito_parcelado is None for record in created)


def test_compara_codigo_antes_do_nome_da_operadora():
    existing = SimpleNamespace(nome="Maquininha principal", codigo="getnet")

    preset = next(
        item for item in DEFAULT_CARD_OPERATOR_PRESETS if item["codigo"] == "GETNET"
    )

    assert operator_matches_preset(existing, preset) is True
