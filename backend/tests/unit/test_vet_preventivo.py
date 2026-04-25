import os
from types import SimpleNamespace

os.environ["DEBUG"] = "false"

from app.veterinario_preventivo import (
    _normalizar_especie_calendario,
    montar_calendario_preventivo,
)


class _FakeQuery:
    def __init__(self, items):
        self.items = items

    def filter(self, *args, **kwargs):
        return self

    def all(self):
        return self.items


class _FakeDb:
    def __init__(self, protocolos):
        self.protocolos = protocolos

    def query(self, model):
        return _FakeQuery(self.protocolos)


def test_normalizar_especie_calendario_aliases():
    assert _normalizar_especie_calendario("canino") == "cão"
    assert _normalizar_especie_calendario("cao") == "cão"
    assert _normalizar_especie_calendario("felino") == "gato"


def test_montar_calendario_preventivo_mescla_base_e_personalizado_canino():
    db = _FakeDb([
        SimpleNamespace(
            id=5,
            nome="V10 personalizada",
            especie="cao",
            dose_inicial_semanas=8,
            intervalo_doses_dias=21,
            numero_doses_serie=3,
            reforco_anual=True,
            observacoes="Protocolo da clinica",
        )
    ])

    calendario = montar_calendario_preventivo(db, "tenant-a", "canino")

    assert calendario["especie_filtro"] == "cão"
    assert calendario["total"] > 1
    assert any(item["fonte"] == "padrao" and item["especie"] == "cão" for item in calendario["items"])
    assert any(item["fonte"] == "personalizado" and item["vacina"] == "V10 personalizada" for item in calendario["items"])
