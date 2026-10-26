"""Assinaturas matemáticas fictícias para testes; não são documentos fiscais.

O certificado é autoassinado, gerado em memória e nunca salvo ou enviado.
O signatário usa C14N da biblioteca padrão, independente do guardião.
"""

import base64
from datetime import datetime, timezone
from functools import lru_cache
import hashlib
from xml.etree import ElementTree as ET

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import NameOID, ObjectIdentifier
from lxml import etree

NFE = "http://www.portalfiscal.inf.br/nfe"  # NOSONAR: identificador XML oficial, sem requisição.
DS = "http://www.w3.org/2000/09/xmldsig#"  # NOSONAR: identificador XML oficial.
C14N = "http://www.w3.org/TR/2001/REC-xml-c14n-20010315"  # NOSONAR: URI do algoritmo oficial.


def make_key(prefix43):
    prefix = str(prefix43)[:43]
    if len(prefix) != 43 or not prefix.isascii() or not prefix.isdigit():
        raise ValueError("A chave fictícia precisa de 43 dígitos.")
    remainder = (
        sum(
            int(digit) * (2 + index % 8) for index, digit in enumerate(reversed(prefix))
        )
        % 11
    )
    return prefix + str(0 if remainder < 2 else 11 - remainder)


@lru_cache(maxsize=1)
def _key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@lru_cache(maxsize=32)
def _certificate(cnpj, start, end, other_cnpj):
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, f"TESTE:{cnpj}")])
    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(_key().public_key())
        .serial_number(1)
        .not_valid_before(start)
        .not_valid_after(end)
    )
    if other_cnpj:
        value = other_cnpj.encode("ascii")
        builder = builder.add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.OtherName(
                        ObjectIdentifier("2.16.76.1.3.3"),
                        b"\x0c" + bytes([len(value)]) + value,
                    )
                ]
            ),
            critical=False,
        )
    return builder.sign(_key(), hashes.SHA256())


def _canonical(node):
    return ET.canonicalize(etree.tostring(node, with_tail=False).decode()).encode()


def sign_nfe(
    raw_xml,
    *,
    certificate_cnpj=None,
    sha256=False,
    certificate_start=None,
    certificate_end=None,
    other_cnpj=None,
):
    """Completa fixtures mínimas e assina sua identidade declarada, sem a mudar."""
    root = etree.fromstring(raw_xml.encode() if isinstance(raw_xml, str) else raw_xml)
    root.set("versao", "4.00")
    nfe = root.find(f"{{{NFE}}}NFe")
    info = nfe.find(f"{{{NFE}}}infNFe")
    info.set("versao", "4.00")
    key = info.get("Id")[3:]
    ide = info.find(f"{{{NFE}}}ide")

    def put(parent, name, value):
        node = parent.find(f"{{{NFE}}}{name}")
        if node is None:
            node = etree.SubElement(parent, f"{{{NFE}}}{name}")
        node.text = str(value)
        return node

    for tag, start, end in (
        ("cUF", 0, 2),
        ("mod", 20, 22),
        ("serie", 22, 25),
        ("nNF", 25, 34),
        ("tpEmis", 34, 35),
        ("cNF", 35, 43),
        ("cDV", 43, 44),
    ):
        put(ide, tag, int(key[start:end]))
    environment = ide.findtext(f"{{{NFE}}}tpAmb")
    protocol = root.find(f"{{{NFE}}}protNFe/{{{NFE}}}infProt")
    put(protocol, "tpAmb", environment)
    put(protocol, "nProt", "135260000000001")
    signature = etree.SubElement(nfe, f"{{{DS}}}Signature", nsmap={None: DS})
    signed_info = etree.SubElement(signature, f"{{{DS}}}SignedInfo")
    etree.SubElement(signed_info, f"{{{DS}}}CanonicalizationMethod", Algorithm=C14N)
    signature_algorithm = (
        "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"
        if sha256
        else DS + "rsa-sha1"  # NOSONAR: URI de algoritmo XMLDSig.
    )
    etree.SubElement(
        signed_info, f"{{{DS}}}SignatureMethod", Algorithm=signature_algorithm
    )
    reference = etree.SubElement(
        signed_info, f"{{{DS}}}Reference", URI="#" + info.get("Id")
    )
    transforms = etree.SubElement(reference, f"{{{DS}}}Transforms")
    for algorithm in (DS + "enveloped-signature", C14N):
        etree.SubElement(transforms, f"{{{DS}}}Transform", Algorithm=algorithm)
    digest_algorithm = (
        "http://www.w3.org/2001/04/xmlenc#sha256" if sha256 else DS + "sha1"
    )  # NOSONAR: URI XMLDSig.
    etree.SubElement(reference, f"{{{DS}}}DigestMethod", Algorithm=digest_algorithm)
    digest = (hashlib.sha256 if sha256 else hashlib.sha1)(
        _canonical(info)
    ).digest()  # NOSONAR: fixture do perfil legado NF-e, sem segurança real.
    encoded_digest = base64.b64encode(digest).decode()
    etree.SubElement(reference, f"{{{DS}}}DigestValue").text = encoded_digest
    put(protocol, "digVal", encoded_digest)
    signed = _key().sign(
        _canonical(signed_info),
        padding.PKCS1v15(),
        (hashes.SHA256 if sha256 else hashes.SHA1)(),
    )
    etree.SubElement(signature, f"{{{DS}}}SignatureValue").text = base64.b64encode(
        signed
    ).decode()
    key_info = etree.SubElement(signature, f"{{{DS}}}KeyInfo")
    certificate_data = etree.SubElement(key_info, f"{{{DS}}}X509Data")
    issuer = certificate_cnpj or info.findtext(f"{{{NFE}}}emit/{{{NFE}}}CNPJ")
    certificate = _certificate(
        issuer,
        certificate_start or datetime(2020, 1, 1, tzinfo=timezone.utc),
        certificate_end or datetime(2030, 1, 1, tzinfo=timezone.utc),
        other_cnpj,
    )
    etree.SubElement(
        certificate_data, f"{{{DS}}}X509Certificate"
    ).text = base64.b64encode(
        certificate.public_bytes(serialization.Encoding.DER)
    ).decode()
    return etree.tostring(root, encoding="utf-8", xml_declaration=True)
