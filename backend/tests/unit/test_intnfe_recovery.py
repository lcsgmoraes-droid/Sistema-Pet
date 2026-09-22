from types import SimpleNamespace

import pytest

from app.intnfe import recovery
from app.intnfe.emission import DirectEmissionError


class FakeDb:
    def __init__(self):
        self.commits = 0

    def commit(self):
        self.commits += 1

    def refresh(self, _sale, **_kwargs):
        return None


def rejected_sale(code="600"):
    return SimpleNamespace(
        id=42,
        tenant_id="11111111-1111-1111-1111-111111111111",
        status="pago_nf",
        nfe_tipo="nfe",
        nfe_modelo="55",
        nfe_numero=17842,
        nfe_serie=2,
        nfe_chave=None,
        nfe_status="rejeitada",
        nfe_xml=None,
        nfe_data_emissao=None,
        nfe_data_autorizacao=None,
        nfe_motivo_rejeicao="Rejeição fiscal",
        nfe_bling_id=None,
        nfe_provider="intnfe",
        nfe_correlation_id="corr-rejeitada",
        nfe_protocolo=None,
        nfe_ambiente=1,
        nfe_codigo_erro=code,
        nfe_idempotency_key=None,
        nfe_payload_hash="payload-anterior",
    )


def test_repair_only_clears_after_current_payload_passes_preview(monkeypatch):
    db = FakeDb()
    sale = rejected_sale()
    tenant = SimpleNamespace(id=sale.tenant_id)
    calls = []

    monkeypatch.setattr(
        recovery,
        "emission_fingerprint",
        lambda *_args: calls.append("preview") or "payload-corrigido",
    )
    monkeypatch.setattr(
        recovery,
        "issue",
        lambda *_args: {
            "success": True,
            "processando": False,
            "provedor": "intnfe",
            "numero": 17843,
        },
    )

    result = recovery.repair_and_retry(
        db,
        tenant,
        sale,
        object(),
        reset_audit=lambda old, new: calls.append((old, new)),
        numbering_audit=lambda *_args: None,
    )

    assert result["success"] is True
    assert calls[0] == "preview"
    assert calls[1][0]["codigo_erro"] == "600"
    assert sale.nfe_correlation_id is None
    assert sale.status == "finalizada"
    assert db.commits == 1


def test_invalid_current_payload_keeps_rejected_attempt_untouched(monkeypatch):
    db = FakeDb()
    sale = rejected_sale()
    before = vars(sale).copy()

    def block(*_args):
        raise DirectEmissionError("Produto sem NCM")

    monkeypatch.setattr(recovery, "emission_fingerprint", block)
    monkeypatch.setattr(
        recovery, "issue", lambda *_args: pytest.fail("não deve emitir")
    )

    with pytest.raises(DirectEmissionError, match="sem NCM"):
        recovery.repair_and_retry(
            db,
            SimpleNamespace(id=sale.tenant_id),
            sale,
            object(),
            reset_audit=lambda *_args: pytest.fail("não deve limpar"),
            numbering_audit=lambda *_args: None,
        )

    assert vars(sale) == before
    assert db.commits == 0


def test_unknown_rejection_is_not_retried_when_payload_did_not_change(monkeypatch):
    db = FakeDb()
    sale = rejected_sale("999")
    monkeypatch.setattr(
        recovery,
        "emission_fingerprint",
        lambda *_args: sale.nfe_payload_hash,
    )
    monkeypatch.setattr(
        recovery, "issue", lambda *_args: pytest.fail("não deve emitir")
    )

    with pytest.raises(DirectEmissionError) as raised:
        recovery.repair_and_retry(
            db,
            SimpleNamespace(id=sale.tenant_id),
            sale,
            object(),
            reset_audit=lambda *_args: pytest.fail("não deve limpar"),
            numbering_audit=lambda *_args: None,
        )

    assert raised.value.code == "CorrecaoAutomaticaIndisponivel"
    assert sale.nfe_status == "rejeitada"


def test_provider_rejection_963_can_retry_after_emitter_fix_without_payload_change(
    monkeypatch,
):
    db = FakeDb()
    sale = rejected_sale("963")
    issued = []
    monkeypatch.setattr(
        recovery,
        "emission_fingerprint",
        lambda *_args: sale.nfe_payload_hash,
    )
    monkeypatch.setattr(
        recovery,
        "issue",
        lambda *_args: (
            issued.append(True)
            or {
                "success": True,
                "processando": False,
                "provedor": "intnfe",
                "numero": 17843,
            }
        ),
    )

    result = recovery.repair_and_retry(
        db,
        SimpleNamespace(id=sale.tenant_id),
        sale,
        object(),
        reset_audit=lambda *_args: None,
        numbering_audit=lambda *_args: None,
    )

    assert result["success"] is True
    assert issued == [True]
    assert any("rejeição 963" in item for item in result["correcoes_aplicadas"])
    assert sale.nfe_status is None
    assert db.commits == 1


def test_pending_result_is_reconciled_without_creating_another_note(monkeypatch):
    db = FakeDb()
    sale = rejected_sale()
    sale.nfe_status = "processando"
    calls = []
    monkeypatch.setattr(
        recovery,
        "reconcile",
        lambda *_args: (
            calls.append("reconcile") or {"success": False, "processando": True}
        ),
    )
    monkeypatch.setattr(
        recovery, "issue", lambda *_args: pytest.fail("não deve emitir")
    )

    with pytest.raises(DirectEmissionError) as raised:
        recovery.repair_and_retry(
            db,
            SimpleNamespace(id=sale.tenant_id),
            sale,
            object(),
            reset_audit=lambda *_args: None,
            numbering_audit=lambda *_args: None,
        )

    assert raised.value.code == "ResultadoNaoConfirmado"
    assert calls == ["reconcile"]


def test_duplicate_number_is_advanced_and_retried_with_a_limit(monkeypatch):
    db = FakeDb()
    sale = rejected_sale("539")
    tenant = SimpleNamespace(id=sale.tenant_id)
    advances = []
    issues = []
    monkeypatch.setattr(
        recovery, "emission_fingerprint", lambda *_args: "payload-igual"
    )
    monkeypatch.setattr(
        recovery,
        "_advance_after_duplicate",
        lambda *_args: advances.append(sale.nfe_numero) or object(),
    )

    def issue(_db, _tenant, current, _document_type, _api):
        issues.append(True)
        if len(issues) == 1:
            current.nfe_tipo = "nfe"
            current.nfe_modelo = "55"
            current.nfe_numero = 17843
            current.nfe_serie = 2
            current.nfe_status = "rejeitada"
            current.nfe_provider = "intnfe"
            current.nfe_correlation_id = "corr-2"
            current.nfe_ambiente = 1
            current.nfe_codigo_erro = "539"
            return {
                "success": False,
                "processando": False,
                "provedor": "intnfe",
                "codigo_erro": "539",
                "correlation_id": "corr-2",
            }
        return {"success": True, "processando": False, "provedor": "intnfe"}

    monkeypatch.setattr(recovery, "issue", issue)
    result = recovery.repair_and_retry(
        db,
        tenant,
        sale,
        object(),
        reset_audit=lambda *_args: None,
        numbering_audit=lambda *_args: None,
    )

    assert result["success"] is True
    assert advances == [17842, 17843]
    assert len(issues) == 2


def test_duplicate_advances_remote_sequence_only_to_failed_number(monkeypatch):
    sale = rejected_sale("539")
    captured = []
    monkeypatch.setattr(
        recovery,
        "read_numbering",
        lambda *_args: SimpleNamespace(
            series=[
                SimpleNamespace(
                    serie="2", modelo=55, ambienteCodigo=1, ultimoNumero=17840
                )
            ]
        ),
    )
    monkeypatch.setattr(
        recovery,
        "advance_numbering",
        lambda _db, _tenant, _api, request, _audit: (
            captured.append(request) or object()
        ),
    )

    recovery._advance_after_duplicate(
        FakeDb(), sale.tenant_id, object(), sale, lambda *_args: None
    )

    assert captured[0].ultimo_numero_consultado == 17840
    assert captured[0].proximo_numero == 17843


def test_authorization_evidence_blocks_automatic_reset():
    sale = rejected_sale()
    sale.nfe_protocolo = "135000000000000"

    with pytest.raises(DirectEmissionError) as raised:
        recovery._clear_rejected_attempt(sale)

    assert raised.value.code == "ReemissaoNaoSegura"
    assert sale.nfe_correlation_id == "corr-rejeitada"


def test_discard_rejected_attempt_releases_sale_without_reissuing(monkeypatch):
    db = FakeDb()
    sale = rejected_sale("441")
    audit = []
    monkeypatch.setattr(
        recovery, "issue", lambda *_args: pytest.fail("não deve emitir")
    )

    result = recovery.discard_rejected_attempt(
        db,
        sale,
        reset_audit=lambda old, new: audit.append((old, new)),
    )

    assert result["success"] is True
    assert result["status_venda"] == "finalizada"
    assert sale.nfe_status is None
    assert sale.nfe_correlation_id is None
    assert sale.nfe_modelo is None
    assert audit[0][0]["codigo_erro"] == "441"
    assert audit[0][1]["resultado"] == "tentativa_rejeitada_descartada"
    assert db.commits == 1


def test_discard_rejected_attempt_refuses_other_provider():
    db = FakeDb()
    sale = rejected_sale()
    sale.nfe_provider = "bling"

    with pytest.raises(DirectEmissionError) as raised:
        recovery.discard_rejected_attempt(
            db,
            sale,
            reset_audit=lambda *_args: pytest.fail("não deve auditar"),
        )

    assert raised.value.code == "RejeicaoNaoEncontrada"
    assert sale.nfe_correlation_id == "corr-rejeitada"
    assert db.commits == 0


def test_changed_attempt_is_never_cleared_after_numbering_query(monkeypatch):
    sale = rejected_sale("539")

    class RacingDb(FakeDb):
        def __init__(self):
            super().__init__()
            self.refreshes = 0

        def refresh(self, current, **_kwargs):
            self.refreshes += 1
            if self.refreshes == 3:
                current.nfe_correlation_id = "corr-outra-requisicao"

    db = RacingDb()
    monkeypatch.setattr(
        recovery, "emission_fingerprint", lambda *_args: "payload-igual"
    )
    monkeypatch.setattr(recovery, "_advance_after_duplicate", lambda *_args: object())
    monkeypatch.setattr(
        recovery, "issue", lambda *_args: pytest.fail("não deve emitir")
    )

    with pytest.raises(DirectEmissionError) as raised:
        recovery.repair_and_retry(
            db,
            SimpleNamespace(id=sale.tenant_id),
            sale,
            object(),
            reset_audit=lambda *_args: pytest.fail("não deve limpar"),
            numbering_audit=lambda *_args: None,
        )

    assert raised.value.code == "SituacaoAlterada"
    assert sale.nfe_correlation_id == "corr-outra-requisicao"
