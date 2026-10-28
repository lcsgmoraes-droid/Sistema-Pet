"""Integridade do XML NF-e; nunca assina ou altera dados fiscais.

O provedor pode reconstruir textos com acentos depois de assinar sua forma
sem diacriticos. Essa unica representacao alternativa so e aceita quando a
assinatura original inteira a comprova. Nao valida cadeia ICP-Brasil, CRL ou
o estado fiscal atual, que continuam dependendo do emissor/SEFAZ.
Uso restrito ao emissor autenticado e ao cache interno; o certificado embutido
nao torna este helper uma autorizacao para uploads ou operacoes financeiras.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
import unicodedata
from datetime import datetime

from cryptography import x509
from cryptography.exceptions import InvalidSignature, UnsupportedAlgorithm
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import NameOID, ObjectIdentifier
from lxml import etree

# These HTTP URIs are protocol identifiers, never network destinations.
NFE = "http://www.portalfiscal.inf.br/nfe"  # NOSONAR - namespace, no network I/O
DS = "http://www.w3.org/2000/09/xmldsig#"  # NOSONAR - namespace, no network I/O
C14N = (
    "http://www.w3.org/TR/2001/REC-xml-c14n-20010315"  # NOSONAR - algorithm identifier
)
ENVELOPED = DS + "enveloped-signature"
MAX_XML_BYTES = 5 * 1024 * 1024
INVALID_MESSAGE = (
    "O XML recebido do emissor não passou na verificação de integridade. "
    "Consulte novamente antes de usar o documento."
)
_DIGESTS = {
    DS
    + "sha1": hashlib.sha1,  # NOSONAR - verification of existing NF-e legacy signatures
    "http://www.w3.org/2001/04/xmlenc#sha256": hashlib.sha256,  # NOSONAR - algorithm identifier
}
_SIGNATURES = {
    DS + "rsa-sha1": hashes.SHA1,  # NOSONAR - verifies existing signatures; never signs
    "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256": hashes.SHA256,  # NOSONAR - identifier
}


class _InvalidXml(ValueError):
    pass


def _require(condition):
    if not condition:
        raise _InvalidXml


def _one(parent, tag):
    elements = parent.findall(tag)
    _require(len(elements) == 1)
    return elements[0]


def _text(parent, tag):
    node = _one(parent, tag)
    _require(len(node) == 0 and node.text is not None)
    return node.text.strip()


def _children(node):
    return [child.tag for child in node if isinstance(child.tag, str)]


def _parse(content):
    parser = etree.XMLParser(
        resolve_entities=False,
        load_dtd=False,
        no_network=True,
        recover=False,
        remove_blank_text=False,
        strip_cdata=False,
        huge_tree=False,
    )
    root = etree.fromstring(content, parser)
    _require(not root.getroottree().docinfo.doctype)
    _require(not any(isinstance(node, etree._Entity) for node in root.iter()))
    _require(sum(1 for _ in root.iter()) <= 30000)
    return root


def _canonical(element):
    # Reparse preserves inherited namespace declarations. Direct subtree C14N
    # in some libxml2 versions creates incorrect xmlns="" resets (tested against
    # .NET SignedXml). Ancestor xml:* attributes are excluded by the profile.
    isolated = _parse(etree.tostring(element, with_tail=False))
    return etree.tostring(isolated, method="c14n", exclusive=False, with_comments=False)


def _base64(text):
    return base64.b64decode(re.sub(r"[ \t\r\n]", "", text), validate=True)


def _valid_cnpj(value):
    if not re.fullmatch(r"[0-9]{14}", value) or len(set(value)) == 1:
        return False
    digits = [int(char) for char in value]
    for size, weights in (
        (12, (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)),
        (13, (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)),
    ):
        remainder = sum(a * b for a, b in zip(digits[:size], weights)) % 11
        if digits[size] != (0 if remainder < 2 else 11 - remainder):
            return False
    return True


def _certificate_cnpj(certificate, issuer):
    candidates = set()
    for name in certificate.subject.get_attributes_for_oid(NameOID.COMMON_NAME):
        match = re.search(r":([0-9]{14})$", name.value)
        if match:
            candidates.add(match[1])
    try:
        names = certificate.extensions.get_extension_for_class(
            x509.SubjectAlternativeName
        ).value
    except x509.ExtensionNotFound:
        names = []
    for name in names:
        if isinstance(name, x509.OtherName) and name.type_id == ObjectIdentifier(
            "2.16.76.1.3.3"
        ):
            # ICP-Brasil e-CNPJ OtherName: DER UTF8/Printable/IA5/OCTET STRING.
            value = name.value
            _require(
                len(value) == 16
                and value[0] in {0x0C, 0x13, 0x16, 0x04}
                and value[1] == 14
            )
            candidates.add(value[2:].decode("ascii"))
    _require(len(candidates) == 1)
    cnpj = candidates.pop()
    _require(_valid_cnpj(cnpj) and cnpj[:8] == issuer[:8])


def _identity(info, protocol, *, expected_cnpj, expected_key, document_type):
    identity = info.get("Id", "")
    _require(re.fullmatch(r"NFe[0-9]{44}", identity) is not None)
    key = identity[3:]
    subtotal = sum(
        int(digit) * (2 + index % 8) for index, digit in enumerate(reversed(key[:43]))
    )
    remainder = subtotal % 11
    _require(int(key[43]) == (0 if remainder < 2 else 11 - remainder))
    if expected_key is not None:
        _require(key == str(expected_key))
    ide = _one(info, f"{{{NFE}}}ide")
    emit = _one(info, f"{{{NFE}}}emit")
    issuer = _text(emit, f"{{{NFE}}}CNPJ")
    _require(_valid_cnpj(issuer) and issuer == key[6:20])
    if expected_cnpj is not None:
        _require(issuer == re.sub(r"[\s./-]", "", str(expected_cnpj)))
    issued = datetime.fromisoformat(_text(ide, f"{{{NFE}}}dhEmi"))
    _require(issued.tzinfo is not None and key[2:6] == issued.strftime("%y%m"))
    for tag, start, end, width in (
        ("cUF", 0, 2, 2),
        ("mod", 20, 22, 2),
        ("serie", 22, 25, 3),
        ("nNF", 25, 34, 9),
        ("tpEmis", 34, 35, 1),
        ("cNF", 35, 43, 8),
        ("cDV", 43, 44, 1),
    ):
        value = _text(ide, f"{{{NFE}}}{tag}")
        _require(re.fullmatch(r"[0-9]{1," + str(width) + "}", value) is not None)
        _require(value.zfill(width) == key[start:end])
    _require(key[20:22] in {"55", "65"})
    if document_type is not None:
        _require(document_type in {"nfe", "nfce"})
        _require(key[20:22] == {"nfe": "55", "nfce": "65"}[document_type])
    _require(_text(protocol, f"{{{NFE}}}chNFe") == key)
    environment = _text(ide, f"{{{NFE}}}tpAmb")
    _require(
        environment in {"1", "2"} and _text(protocol, f"{{{NFE}}}tpAmb") == environment
    )
    _require(_text(protocol, f"{{{NFE}}}cStat") in {"100", "150"})
    _require(re.fullmatch(r"[0-9]{15}", _text(protocol, f"{{{NFE}}}nProt")) is not None)
    return issuer, issued


def _verified(root, *, expected_cnpj, expected_key, document_type):
    _require(root.tag == f"{{{NFE}}}nfeProc" and root.attrib == {"versao": "4.00"})
    _require(_children(root) == [f"{{{NFE}}}NFe", f"{{{NFE}}}protNFe"])
    nfe = _one(root, f"{{{NFE}}}NFe")
    _require(not nfe.attrib)
    info = _one(nfe, f"{{{NFE}}}infNFe")
    _require(info.get("versao") == "4.00" and set(info.attrib) == {"Id", "versao"})
    signature = _one(nfe, f"{{{DS}}}Signature")
    _require(set(signature.attrib) <= {"Id"})
    allowed_children = [f"{{{NFE}}}infNFe", f"{{{DS}}}Signature"]
    _require(
        _children(nfe)
        in (
            allowed_children,
            [allowed_children[0], f"{{{NFE}}}infNFeSupl", allowed_children[1]],
        )
    )
    for tag in (
        f"{{{NFE}}}NFe",
        f"{{{NFE}}}infNFe",
        f"{{{DS}}}Signature",
        f"{{{DS}}}Reference",
    ):
        _require(sum(node.tag == tag for node in root.iter()) == 1)
    identifiers = []
    for node in root.iter():
        for name, value in node.attrib.items():
            if etree.QName(name).localname in {"Id", "ID", "id"}:
                identifiers.append(value)
    _require(len(identifiers) == len(set(identifiers)))
    prot = _one(root, f"{{{NFE}}}protNFe")
    _require(_children(prot) == [f"{{{NFE}}}infProt"])
    protocol = _one(prot, f"{{{NFE}}}infProt")
    issuer, issued = _identity(
        info,
        protocol,
        expected_cnpj=expected_cnpj,
        expected_key=expected_key,
        document_type=document_type,
    )
    _require(
        _children(signature)
        == [f"{{{DS}}}SignedInfo", f"{{{DS}}}SignatureValue", f"{{{DS}}}KeyInfo"]
    )
    signed_info = _one(signature, f"{{{DS}}}SignedInfo")
    _require(not signed_info.attrib)
    _require(
        _children(signed_info)
        == [
            f"{{{DS}}}CanonicalizationMethod",
            f"{{{DS}}}SignatureMethod",
            f"{{{DS}}}Reference",
        ]
    )
    canonicalization = _one(signed_info, f"{{{DS}}}CanonicalizationMethod")
    _require(
        canonicalization.attrib == {"Algorithm": C14N} and len(canonicalization) == 0
    )
    method = _one(signed_info, f"{{{DS}}}SignatureMethod")
    _require(set(method.attrib) == {"Algorithm"} and len(method) == 0)
    _require(method.get("Algorithm") in _SIGNATURES)
    reference = _one(signed_info, f"{{{DS}}}Reference")
    _require(reference.attrib == {"URI": "#" + info.get("Id")})
    _require(
        _children(reference)
        == [f"{{{DS}}}Transforms", f"{{{DS}}}DigestMethod", f"{{{DS}}}DigestValue"]
    )
    transforms = _one(reference, f"{{{DS}}}Transforms")
    _require(len(transforms) == 2)
    for transform, algorithm in zip(transforms, (ENVELOPED, C14N)):
        _require(
            transform.tag == f"{{{DS}}}Transform"
            and transform.attrib == {"Algorithm": algorithm}
            and len(transform) == 0
        )
    digest_method = _one(reference, f"{{{DS}}}DigestMethod")
    _require(set(digest_method.attrib) == {"Algorithm"} and len(digest_method) == 0)
    _require(digest_method.get("Algorithm") in _DIGESTS)
    signed_digest = _base64(_text(reference, f"{{{DS}}}DigestValue"))
    _require(
        hmac.compare_digest(signed_digest, _base64(_text(protocol, f"{{{NFE}}}digVal")))
    )
    key_info = _one(signature, f"{{{DS}}}KeyInfo")
    _require(_children(key_info) == [f"{{{DS}}}X509Data"])
    certificate_data = _one(key_info, f"{{{DS}}}X509Data")
    _require(_children(certificate_data) == [f"{{{DS}}}X509Certificate"])
    certificate = x509.load_der_x509_certificate(
        _base64(_text(certificate_data, f"{{{DS}}}X509Certificate"))
    )
    _certificate_cnpj(certificate, issuer)
    _require(
        certificate.not_valid_before_utc <= issued <= certificate.not_valid_after_utc
    )
    public_key = certificate.public_key()
    _require(
        isinstance(public_key, rsa.RSAPublicKey) and 2048 <= public_key.key_size <= 8192
    )
    public_key.verify(
        _base64(_text(signature, f"{{{DS}}}SignatureValue")),
        _canonical(signed_info),
        padding.PKCS1v15(),
        _SIGNATURES[method.get("Algorithm")](),
    )
    digest = _DIGESTS[digest_method.get("Algorithm")](_canonical(info)).digest()
    return info, hmac.compare_digest(digest, signed_digest)


def ensure_signed_xml(
    content, *, expected_cnpj=None, expected_key=None, document_type=None
):
    """Retorna bytes intactos ou representacao comprovada pela assinatura original.

    Falha com IntNFeError('XmlInvalido'), sem incluir dados ou XML externo no erro.
    expected_cnpj/key vinculam o documento ao registro de origem do consumidor.
    """
    try:
        if isinstance(content, str):
            content = content.encode("utf-8")
        _require(isinstance(content, bytes) and 0 < len(content) <= MAX_XML_BYTES)
        root = _parse(content)
        arguments = dict(
            expected_cnpj=expected_cnpj,
            expected_key=expected_key,
            document_type=document_type,
        )
        info, valid = _verified(root, **arguments)
        if valid:
            return content
        changed = False
        for node in info.iter():
            if not isinstance(node.tag, str):
                continue
            for field in ("text", "tail") if node is not info else ("text",):
                value = getattr(node, field)
                if value is not None:
                    candidate = "".join(
                        char
                        for char in unicodedata.normalize("NFD", value)
                        if not unicodedata.combining(char)
                    )
                    if candidate != value:
                        setattr(node, field, candidate)
                        changed = True
        _require(changed)
        candidate_bytes = etree.tostring(root, encoding="utf-8", xml_declaration=True)
        # Verify the exact bytes being returned, including namespace context after
        # serialization. SignedInfo, signature, attributes and protocol are untouched.
        _, valid = _verified(_parse(candidate_bytes), **arguments)
        _require(valid)
        return candidate_bytes
    except (
        ValueError,
        TypeError,
        OverflowError,
        etree.LxmlError,
        InvalidSignature,
        UnsupportedAlgorithm,
        x509.DuplicateExtension,
        x509.UnsupportedGeneralNameType,
    ):
        from app.intnfe.client import IntNFeError

        raise IntNFeError(
            "XmlInvalido",
            validation_errors=[INVALID_MESSAGE],
            provider_message=INVALID_MESSAGE,
        ) from None
