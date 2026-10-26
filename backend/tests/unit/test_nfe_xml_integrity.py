"""Fixtures fiscais ficticias assinadas em RAM, sem certificado ou PII reais."""

from copy import deepcopy
from unittest.mock import Mock
from xml.etree.ElementTree import canonicalize

import pytest
from cryptography import x509
from lxml import etree
from pydantic import SecretStr

from app.config import settings
from app.intnfe.client import IntNFeClient, IntNFeError
from app.intnfe.xml_integrity import INVALID_MESSAGE, ensure_signed_xml
from tests.helpers.signed_nfe import make_key, sign_nfe

NS = {
    "n": "http://www.portalfiscal.inf.br/nfe",  # NOSONAR - XML namespace, no network
    "ds": "http://www.w3.org/2000/09/xmldsig#",  # NOSONAR - XML namespace, no network
}
CNPJ = "11222333000181"
KEY = make_key("352610" + CNPJ + "55001000001650112345678")


def raw_nfe(*, street="Condominio Ficticio"):
    return f'''<nfeProc xmlns="{NS["n"]}" versao="4.00"><NFe>
<infNFe versao="4.00" Id="NFe{KEY}"><ide><cUF>35</cUF><cNF>12345678</cNF>
<mod>55</mod><serie>1</serie><nNF>1650</nNF><dhEmi>2026-10-26T10:00:00-03:00</dhEmi>
<tpEmis>1</tpEmis><cDV>{KEY[-1]}</cDV><tpAmb>2</tpAmb></ide>
<emit><CNPJ>{CNPJ}</CNPJ><xNome>Empresa Ficticia</xNome></emit>
<dest><xNome>Cliente Ficticio</xNome><enderDest><xLgr>{street}</xLgr>
<xBairro>Bairro Botanico</xBairro><xMun>Cidade Ficticia</xMun></enderDest></dest>
<det nItem="1"><prod><cProd>FICTICIO</cProd><qCom>1.0000</qCom><vProd>145.90</vProd></prod></det>
<total><ICMSTot><vNF>145.90</vNF></ICMSTot></total><infAdic><infCpl>Pedido ficticio</infCpl></infAdic>
</infNFe></NFe><protNFe versao="4.00"><infProt><tpAmb>2</tpAmb><chNFe>{KEY}</chNFe>
<dhRecbto>2026-10-26T10:00:01-03:00</dhRecbto><nProt>123456789012345</nProt><digVal/>
<cStat>100</cStat><xMotivo>Autorizado o uso da NF-e</xMotivo></infProt></protNFe></nfeProc>'''.encode()


@pytest.fixture(scope="module")
def signed_xml():
    return sign_nfe(raw_nfe())


def changed_xml(content, change):
    root = etree.fromstring(content)
    change(root)
    return etree.tostring(root, encoding="utf-8", xml_declaration=True)


def find(root, path):
    return root.find(path, NS)


def canonical_part(content, path):
    # Independent stdlib canonicalizer; fixtures use no unused namespaces.
    return canonicalize(etree.tostring(find(etree.fromstring(content), path))).encode()


def assert_invalid(content, **kwargs):
    with pytest.raises(IntNFeError) as error:
        ensure_signed_xml(content, **kwargs)
    assert error.value.code == "XmlInvalido"
    assert error.value.validation_errors == [INVALID_MESSAGE]
    assert error.value.provider_message == INVALID_MESSAGE
    assert "Cliente Ficticio" not in str(error.value)


@pytest.mark.parametrize("encoding", ["utf-8", "utf-16"])
def test_valid_original_keeps_every_byte(signed_xml, encoding):
    raw = etree.tostring(
        etree.fromstring(signed_xml), encoding=encoding, xml_declaration=True
    )
    if encoding == "utf-8":
        raw = b"\xef\xbb\xbf" + raw.replace(b"?>", b"?>\n", 1)
    assert (
        ensure_signed_xml(
            raw, expected_cnpj=CNPJ, expected_key=KEY, document_type="nfe"
        )
        is raw
    )


@pytest.mark.parametrize("sha256", [False, True])
def test_already_signed_accents_are_preserved(sha256):
    raw = sign_nfe(raw_nfe(street="Condomínio Fictício"), sha256=sha256)
    assert ensure_signed_xml(raw) == raw


def test_valid_nfce_with_supplementary_qr_code_is_supported():
    key = make_key("352610" + CNPJ + "65001000001650112345678")
    raw = raw_nfe().replace(KEY.encode(), key.encode())
    raw = raw.replace(
        b"</NFe>",
        b"<infNFeSupl><qrCode>https://example.invalid/ficticio</qrCode></infNFeSupl></NFe>",
    )
    signed = sign_nfe(raw)
    assert ensure_signed_xml(signed, document_type="nfce", expected_key=key) == signed


@pytest.mark.parametrize("sha256", [False, True])
def test_only_original_signature_can_prove_restored_text(sha256):
    original = sign_nfe(raw_nfe(), sha256=sha256)
    damaged = original.replace(b"Condominio Ficticio", "Condomínio Fictício".encode())
    damaged = damaged.replace(b"Bairro Botanico", "Bairro Botânico".encode())
    assert damaged != original
    repaired = ensure_signed_xml(damaged, expected_cnpj=CNPJ, expected_key=KEY)
    assert canonical_part(repaired, "n:NFe/n:infNFe") == canonical_part(
        original, "n:NFe/n:infNFe"
    )
    assert canonical_part(repaired, "n:NFe/ds:Signature") == canonical_part(
        original, "n:NFe/ds:Signature"
    )
    assert canonical_part(repaired, "n:protNFe") == canonical_part(
        original, "n:protNFe"
    )
    assert ensure_signed_xml(repaired) is repaired
    assert "Condomínio".encode() in damaged


def test_text_outside_reference_is_not_normalized(signed_xml):
    damaged = signed_xml.replace(b"Condominio Ficticio", "Condomínio Fictício".encode())
    damaged = damaged.replace(
        b"</NFe>", "<!--Observação fora da referência--></NFe>".encode()
    )
    restored = ensure_signed_xml(damaged)
    assert "Observação fora da referência".encode() in restored


@pytest.mark.parametrize(
    "path,value",
    [
        ("n:NFe/n:infNFe/n:total/n:ICMSTot/n:vNF", "146.90"),
        ("n:NFe/n:infNFe/n:emit/n:CNPJ", "11444777000161"),
        ("n:NFe/n:infNFe/n:ide/n:nNF", "1651"),
        ("n:NFe/n:infNFe/n:dest/n:xNome", "Outro Cliente Ficticio"),
        ("n:protNFe/n:infProt/n:chNFe", "1" * 44),
        ("n:protNFe/n:infProt/n:digVal", "AAAAAAAAAAAAAAAAAAAAAAAAAAA="),
    ],
)
def test_value_identity_or_protocol_tampering_fails_closed(signed_xml, path, value):
    damaged = signed_xml.replace(b"Condominio Ficticio", "Condomínio Fictício".encode())
    assert_invalid(
        changed_xml(damaged, lambda root: setattr(find(root, path), "text", value))
    )


@pytest.mark.parametrize(
    "expectations",
    [
        {"expected_cnpj": "11444777000161"},
        {"expected_key": "1" * 44},
        {"document_type": "nfce"},
        {"document_type": "outra-rota"},
    ],
)
def test_source_binding_rejects_other_tenant_key_or_model(signed_xml, expectations):
    assert_invalid(signed_xml, **expectations)


def test_cnpj_formatting_is_accepted_for_expected_tenant(signed_xml):
    assert (
        ensure_signed_xml(signed_xml, expected_cnpj="11.222.333/0001-81") == signed_xml
    )


@pytest.mark.parametrize("target", ["n:NFe", "n:NFe/n:infNFe", "n:NFe/ds:Signature"])
def test_wrapped_or_duplicated_invoice_signature_is_rejected(signed_xml, target):
    def duplicate(root):
        node = find(root, target)
        node.getparent().append(deepcopy(node))

    assert_invalid(changed_xml(signed_xml, duplicate))


def test_duplicated_reference_is_rejected(signed_xml):
    def duplicate(root):
        node = find(root, "n:NFe/ds:Signature/ds:SignedInfo/ds:Reference")
        node.getparent().append(deepcopy(node))

    assert_invalid(changed_xml(signed_xml, duplicate))


def test_duplicated_id_outside_reference_is_rejected(signed_xml):
    def duplicate(root):
        find(root, "n:protNFe/n:infProt").set("Id", "NFe" + KEY)

    assert_invalid(changed_xml(signed_xml, duplicate))


@pytest.mark.parametrize(
    "uri", ["https://example.invalid/original.xml", "#outro-id", ""]
)
def test_reference_must_point_to_exact_invoice(signed_xml, uri):
    def change(root):
        find(root, "n:NFe/ds:Signature/ds:SignedInfo/ds:Reference").set("URI", uri)

    assert_invalid(changed_xml(signed_xml, change))


@pytest.mark.parametrize(
    "tag,algorithm",
    [
        ("ds:CanonicalizationMethod", "http://www.w3.org/2001/10/xml-exc-c14n#"),
        ("ds:SignatureMethod", "http://www.w3.org/2000/09/xmldsig#hmac-sha1"),
        ("ds:Reference/ds:DigestMethod", "http://www.w3.org/2001/04/xmldsig-more#md5"),
        (
            "ds:Reference/ds:Transforms/ds:Transform",
            "http://www.w3.org/TR/1999/REC-xslt-19991116",
        ),
    ],
)
def test_only_known_signature_algorithms_and_transforms_are_accepted(
    signed_xml, tag, algorithm
):
    def change(root):
        find(root, "n:NFe/ds:Signature/ds:SignedInfo/" + tag).set(
            "Algorithm", algorithm
        )

    assert_invalid(changed_xml(signed_xml, change))


def test_rsa_signature_is_required_even_when_digest_matches(signed_xml):
    def corrupt(root):
        node = find(root, "n:NFe/ds:Signature/ds:SignatureValue")
        node.text = ("B" if node.text[0] != "B" else "C") + node.text[1:]

    assert_invalid(changed_xml(signed_xml, corrupt))


@pytest.mark.parametrize("separator,valid", [("\n", True), ("\u00a0", False)])
def test_base64_allows_only_xml_ascii_whitespace(signed_xml, separator, valid):
    def wrap(root):
        node = find(root, "n:NFe/ds:Signature/ds:SignatureValue")
        node.text = node.text[:40] + separator + node.text[40:]

    raw = changed_xml(signed_xml, wrap)
    if valid:
        assert ensure_signed_xml(raw) == raw
    else:
        assert_invalid(raw)


def test_certificate_requires_same_issuer_cnpj_base():
    assert_invalid(sign_nfe(raw_nfe(), certificate_cnpj="11444777000161"))


def test_certificate_of_same_cnpj_base_is_accepted_for_branch():
    raw = sign_nfe(raw_nfe(), certificate_cnpj="11222333000262")
    assert ensure_signed_xml(raw, expected_cnpj=CNPJ) == raw


@pytest.mark.parametrize("path", [".", "n:NFe", "n:NFe/ds:Signature"])
@pytest.mark.parametrize(
    "attribute,value", [("lang", "pt-BR"), ("base", "urn:ficticio")]
)
def test_ancestor_xml_context_cannot_be_silently_discarded(
    signed_xml, path, attribute, value
):
    def change(root):
        node = root if path == "." else find(root, path)
        node.set(
            "{http://www.w3.org/XML/1998/namespace}" + attribute, value
        )  # NOSONAR - XML attribute identifier

    assert_invalid(changed_xml(signed_xml, change))


def test_unused_ancestor_namespace_still_belongs_to_inclusive_c14n(signed_xml):
    changed = signed_xml.replace(
        b"<nfeProc ", b'<nfeProc xmlns:extra="urn:ficticio" ', 1
    )
    assert changed != signed_xml
    assert_invalid(changed)


def test_conflicting_certificate_cnpj_claims_are_rejected():
    assert_invalid(sign_nfe(raw_nfe(), other_cnpj="11444777000161"))


def test_certificate_must_be_valid_at_issue_time():
    from datetime import datetime, timezone

    assert_invalid(
        sign_nfe(raw_nfe(), certificate_end=datetime(2026, 1, 1, tzinfo=timezone.utc))
    )


@pytest.mark.parametrize(
    "content",
    [
        b"",
        b"<html>502 Bad Gateway</html>",
        b"<nfeProc>",
        b'<!DOCTYPE nfeProc [<!ENTITY x "secret">]><nfeProc>&x;</nfeProc>',
        b'<!DOCTYPE nfeProc SYSTEM "file:///C:/secret.txt"><nfeProc/>',
    ],
)
def test_invalid_xml_html_and_dtd_entities_fail_safely(content):
    assert_invalid(content)


def test_even_unused_dtd_in_signed_document_is_rejected(signed_xml):
    content = signed_xml.replace(
        b"?>", b'?><!DOCTYPE nfeProc [<!ENTITY unused "secret">]>', 1
    )
    assert content != signed_xml
    assert_invalid(content)


def test_ambiguous_certificate_extension_errors_are_safe(signed_xml, monkeypatch):
    certificate = Mock()
    certificate.subject.get_attributes_for_oid.return_value = []
    type(certificate).extensions = property(
        lambda self: (_ for _ in ()).throw(
            x509.DuplicateExtension("private", x509.ObjectIdentifier("2.5.29.17"))
        )
    )
    monkeypatch.setattr(x509, "load_der_x509_certificate", lambda _raw: certificate)
    assert_invalid(signed_xml)


def test_client_checks_shared_xml_boundary_and_never_returns_html(
    monkeypatch, signed_xml
):
    monkeypatch.setattr(settings, "INTNFE_ACTIVATION_ENABLED", True)
    monkeypatch.setattr(settings, "INTNFE_INTEGRADOR_ID", "ficticio")
    monkeypatch.setattr(
        settings, "INTNFE_INTEGRADOR_SECRET", SecretStr("segredo-ficticio")
    )
    session = Mock()
    session.request.return_value = Mock(status_code=200, headers={}, content=signed_xml)
    api = IntNFeClient(session=session)
    assert (
        api.document_xml("token-ficticio", "nfe", "correlacao-ficticia") == signed_xml
    )
    session.request.return_value.content = b"<html>502 Bad Gateway</html>"
    with pytest.raises(IntNFeError, match="XmlInvalido"):
        api.document_xml("token-ficticio", "nfe", "correlacao-ficticia")
    assert session.request.call_count == 2
