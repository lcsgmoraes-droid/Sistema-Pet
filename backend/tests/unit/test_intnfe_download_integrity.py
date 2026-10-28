"""Atualização auditada do cache após um download verificado pelo cliente."""

import hashlib
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.intnfe import emission
from app.intnfe.client import IntNFeError


@pytest.fixture
def download_context(monkeypatch):
    sale = SimpleNamespace(
        id=42,
        tenant_id="11111111-1111-1111-1111-111111111111",
        nfe_provider="intnfe",
        nfe_correlation_id="existing-document",
        nfe_tipo="nfe",
        nfe_ambiente=1,
        nfe_xml="cached-source",
    )
    db = SimpleNamespace(commit=Mock())
    api = SimpleNamespace(document_xml=Mock(return_value=b"verified-source"))
    audit = Mock()
    monkeypatch.setattr(emission, "_connection", lambda *args, **kwargs: object())
    monkeypatch.setattr(emission, "_access_token", lambda *args: "test-token")
    monkeypatch.setattr(emission, "log_action", audit)
    return sale, db, api, audit


def test_verified_download_replaces_stale_cache_with_hash_only_audit(download_context):
    sale, db, api, audit = download_context

    result = emission.download_document(db, sale, api, "xml")

    assert result == b"verified-source"
    assert sale.nfe_xml == "verified-source"
    db.commit.assert_called_once_with()
    metadata = audit.call_args.kwargs
    assert metadata["tenant_id"] == sale.tenant_id
    assert metadata["entity_id"] == sale.id
    assert metadata["old_value"] == {
        "sha256": hashlib.sha256(b"cached-source").hexdigest()
    }
    assert metadata["new_value"] == {
        "sha256": hashlib.sha256(b"verified-source").hexdigest()
    }
    assert metadata["commit"] is False


def test_unchanged_verified_download_does_not_rewrite_cache(download_context):
    sale, db, api, audit = download_context
    sale.nfe_xml = "verified-source"

    assert emission.download_document(db, sale, api, "xml") == b"verified-source"

    db.commit.assert_not_called()
    audit.assert_not_called()


def test_invalid_signature_cannot_replace_cache_or_escape_as_file(download_context):
    sale, db, api, audit = download_context
    api.document_xml.side_effect = IntNFeError("XmlInvalido")

    with pytest.raises(emission.DirectEmissionError) as failure:
        emission.download_document(db, sale, api, "xml")

    assert failure.value.status == 502
    assert failure.value.code == "XmlInvalido"
    assert sale.nfe_xml == "cached-source"
    db.commit.assert_not_called()
    audit.assert_not_called()


def test_verified_non_utf8_bytes_are_preserved_without_reencoding(download_context):
    sale, db, api, audit = download_context
    verified_bytes = "verified-source".encode("utf-16")
    api.document_xml.return_value = verified_bytes

    assert emission.download_document(db, sale, api, "xml") == verified_bytes

    assert sale.nfe_xml == "cached-source"
    db.commit.assert_not_called()
    audit.assert_not_called()
