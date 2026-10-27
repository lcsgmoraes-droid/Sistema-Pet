"""Fila fiscal durável, sem criar venda, recebimento ou movimento de estoque."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from uuid import uuid4

from defusedxml import ElementTree as ET
from fastapi import HTTPException
from sqlalchemy import or_, update
from sqlalchemy.exc import IntegrityError

from app.audit_log import log_action
from app.ecommerceai_fiscal.models import FiscalAccount, ExternalFiscalOrder
from app.ecommerceai_fiscal.payload import (
    build_payload,
    PreparationBlocked,
    blocker,
    fold,
)
from app.intnfe.client import IntNFeError
from app.intnfe.emission import _access_token, _connection, DirectEmissionError
from app.intnfe.repository import get_tenant
from app.intnfe.xml_integrity import ensure_signed_xml

NS = {"n": "http://www.portalfiscal.inf.br/nfe"}  # NOSONAR - namespace identifier
STATUS = {
    1: "processing",
    2: "processing",
    3: "authorized",
    4: "rejected",
    5: "canceled",
    6: "rejected",
    7: "processing",
    8: "rejected",
}


def now():
    return datetime.now(timezone.utc)


def aware(value):
    return (
        value.replace(tzinfo=timezone.utc) if value and value.tzinfo is None else value
    )


def digest(value):
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
    ).hexdigest()


def fail(code, message, status=409, field=None):
    raise HTTPException(status, blocker(code, message, field))


def get_order(db, tenant_id, order_id, *, lock=False):
    query = db.query(ExternalFiscalOrder).filter(
        ExternalFiscalOrder.tenant_id == tenant_id, ExternalFiscalOrder.id == order_id
    )
    row = query.populate_existing().with_for_update().first() if lock else query.first()
    if row is None:
        fail("not_found", "Pedido fiscal não encontrado nesta empresa.", 404)
    return row


def account_for(db, tenant_id, channel, seller_id, *, lock=False):
    query = db.query(FiscalAccount).filter(
        FiscalAccount.tenant_id == tenant_id,
        FiscalAccount.channel == channel,
        FiscalAccount.seller_id == seller_id,
    )
    query = query.populate_existing()
    return query.with_for_update().first() if lock else query.first()


def view(row, *, details=False):
    result = {
        "id": row.id,
        "account_id": row.account_id,
        "channel": row.channel,
        "seller_id": row.seller_id,
        "external_order_id": row.external_order_id,
        "source_revision": row.source_revision,
        "payload_hash": row.payload_hash,
        "status": row.status,
        "blockers": row.blockers or [],
        "numero": row.numero,
        "chave": row.chave,
        "protocolo": row.protocolo,
        "xml_available": row.status == "authorized" and bool(row.xml),
        "danfe_available": row.status == "authorized" and bool(row.xml),
        "recipient_name": (row.source.get("recipient") or {}).get("name"),
        "total": (row.discount_audit or {}).get("effective_invoice_total")
        or row.source["totals"]["invoice_total"],
        "purchased_at": row.purchased_at,
        "historical_reviewed_at": row.historical_reviewed_at,
        "lease_until": row.lease_until,
        "recipient_document": re.sub(
            r"\D", "", str((row.source.get("recipient") or {}).get("document") or "")
        ),
        "totals": {
            "currency": "BRL",
            "products": row.source["totals"]["products"],
            "discount": (row.discount_audit or {}).get(
                "effective_discount", row.source["totals"]["discount"]
            ),
            "freight": row.source["totals"]["freight"],
            "invoice_total": (row.discount_audit or {}).get(
                "effective_invoice_total", row.source["totals"]["invoice_total"]
            ),
        },
    }
    result["totals"] = {
        key: (value if key == "currency" else format(Decimal(str(value)), ".2f"))
        for key, value in result["totals"].items()
    }
    if details:
        result.update(source=row.source, discount_audit=row.discount_audit)
    return result


def prepare_row(db, tenant_id, row, *, owned_lease=None):
    if row.idempotency_key or (
        row.lease_token
        and row.lease_token != owned_lease
        and aware(row.lease_until) > now()
    ):
        return row
    source = row.source
    account = account_for(db, tenant_id, row.channel, row.seller_id)
    row.payload = None
    row.payload_hash = None
    row.discount_audit = None
    errors = []
    if account is None or not account.active:
        errors.append(
            blocker(
                "account_not_configured",
                "Configure e autorize esta conta Amazon no CorePet.",
            )
        )
    else:
        row.account_id = account.id
        if account.marketplace_id != source["marketplace_id"]:
            errors.append(
                blocker(
                    "marketplace_mismatch", "O marketplace difere da conta autorizada."
                )
            )
        if not row.historical_reviewed_at and (
            not account.activated_at
            or aware(row.purchased_at) < aware(account.activated_at)
        ):
            errors.append(
                blocker(
                    "historical_order_requires_review",
                    "Pedido anterior à ativação exige revisão humana explícita ou vínculo fiscal existente.",
                    "purchased_at",
                )
            )
        try:
            tenant = get_tenant(db, tenant_id)
            connection = _connection(db, tenant_id)
            payload, audit = build_payload(db, tenant, connection, account, source)
            row.payload = payload
            row.payload_hash = digest(payload)
            row.discount_audit = audit
        except PreparationBlocked as exc:
            errors.extend(exc.blockers)
        except DirectEmissionError:
            errors.append(
                blocker(
                    "emitter_not_configured",
                    "Conclua a configuração fiscal IntNFe desta empresa.",
                )
            )
    row.blockers = errors
    row.status = "blocked" if errors else "ready"
    return row


def upsert(db, connection, source, *, _retried=False):
    tenant_id = connection.tenant_id
    source_hash = digest(source)
    row = (
        db.query(ExternalFiscalOrder)
        .filter(
            ExternalFiscalOrder.tenant_id == tenant_id,
            ExternalFiscalOrder.channel == source["channel"],
            ExternalFiscalOrder.seller_id == source["seller_id"],
            ExternalFiscalOrder.external_order_id == source["external_order_id"],
        )
        .populate_existing()
        .with_for_update()
        .first()
    )
    if row:
        if row.lease_token and row.lease_until and aware(row.lease_until) > now():
            if (
                source["source_revision"] == row.source_revision
                and source_hash == row.source_hash
            ):
                return view(row)
            fail(
                "fiscal_operation_in_progress",
                "O pedido está sendo processado; o snapshot foi preservado.",
            )
        if source["source_revision"] < row.source_revision or (
            source["source_revision"] == row.source_revision
            and source_hash != row.source_hash
        ):
            fail(
                "source_revision_conflict",
                "Revisão antiga ou reutilizada com conteúdo diferente.",
            )
        if source["source_revision"] > row.source_revision:
            if row.idempotency_key or row.status not in {"blocked", "ready"}:
                fail(
                    "snapshot_frozen",
                    "O pedido já teve envio fiscal; o snapshot está preservado.",
                )
            incoming_date = datetime.fromisoformat(
                source["purchased_at"].replace("Z", "+00:00")
            )
            if aware(row.purchased_at) != incoming_date:
                fail(
                    "order_identity_changed",
                    "A data original do pedido não pode ser alterada para contornar o corte de ativação.",
                )
            row.source_revision = source["source_revision"]
            row.source_hash = source_hash
            row.source = source
            row.purchased_at = datetime.fromisoformat(
                source["purchased_at"].replace("Z", "+00:00")
            )
            # A revisão humana é vinculada ao conteúdo revisado.
            row.historical_reviewed_at = None
            row.reviewed_by_user_id = None
        prepare_row(db, tenant_id, row)
        db.commit()
        return view(row)
    row = ExternalFiscalOrder(
        tenant_id=tenant_id,
        connection_id=connection.id,
        channel=source["channel"],
        seller_id=source["seller_id"],
        external_order_id=source["external_order_id"],
        source_revision=source["source_revision"],
        source_hash=source_hash,
        source=source,
        purchased_at=datetime.fromisoformat(
            source["purchased_at"].replace("Z", "+00:00")
        ),
    )
    db.add(row)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        # The database identity handles reconnects and concurrent first imports.
        existing = (
            db.query(ExternalFiscalOrder.id)
            .filter(
                ExternalFiscalOrder.tenant_id == tenant_id,
                ExternalFiscalOrder.channel == source["channel"],
                ExternalFiscalOrder.seller_id == source["seller_id"],
                ExternalFiscalOrder.external_order_id == source["external_order_id"],
            )
            .first()
        )
        if not existing or _retried:
            fail(
                "storage_conflict",
                "Não foi possível preservar a identidade fiscal. Tente novamente sem criar outra nota.",
                503,
            )
        return upsert(db, connection, source, _retried=True)
    prepare_row(db, tenant_id, row)
    db.commit()
    return view(row)


def review(db, tenant_id, order_id, user_id):
    row = get_order(db, tenant_id, order_id, lock=True)
    if row.idempotency_key:
        fail("snapshot_frozen", "O envio existente não pode ser revisado ou repetido.")
    row.historical_reviewed_at = now()
    row.reviewed_by_user_id = user_id
    prepare_row(db, tenant_id, row)
    log_action(
        db,
        user_id,
        "eai_fiscal_review",
        "external_fiscal_order",
        row.id,
        tenant_id=tenant_id,
        new_value={"source_revision": row.source_revision},
        commit=False,
    )
    db.commit()
    return view(row, details=True)


def _claim(db, row):
    token = str(uuid4())
    claim_time = now()
    result = db.execute(
        update(ExternalFiscalOrder)
        .where(
            ExternalFiscalOrder.id == row.id,
            ExternalFiscalOrder.tenant_id == row.tenant_id,
            or_(
                ExternalFiscalOrder.lease_until.is_(None),
                ExternalFiscalOrder.lease_until <= claim_time,
            ),
        )
        .values(lease_token=token, lease_until=claim_time + timedelta(seconds=120))
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        db.rollback()
        fail(
            "fiscal_operation_in_progress",
            "Outro processamento já possui este pedido. Consulte o estado.",
            409,
        )
    db.commit()
    return token


def _owned(db, tenant_id, order_id, token):
    row = get_order(db, tenant_id, order_id, lock=True)
    if row.lease_token != token:
        db.rollback()
        fail(
            "fiscal_lease_changed",
            "Outro processamento assumiu a consulta; consulte o estado.",
        )
    return row


def _release(row):
    row.lease_token = None
    row.lease_until = None


def verify_xml(row, content):
    """Preserva os bytes verificados e vincula também comprador/valores/pedido."""
    if not row.chave or len(row.chave) != 44 or not row.protocolo or not row.numero:
        raise IntNFeError("XmlInvalido")
    data = ensure_signed_xml(
        content,
        expected_cnpj=row.source["emitter_cnpj"],
        expected_key=row.chave,
        document_type="nfe",
    )
    root = ET.fromstring(data)

    def text(path):
        return root.findtext(path, namespaces=NS) or ""

    payload = row.payload
    recipient = payload["destinatario"]
    document = recipient.get("cpf") or recipient.get("cnpj")
    actual_doc = text(".//n:dest/n:CPF") or text(".//n:dest/n:CNPJ")
    expected_total = Decimal(str(row.discount_audit["effective_invoice_total"]))
    tests = [
        actual_doc == document,
        fold(text(".//n:dest/n:xNome")) == fold(recipient["razaoSocial"]),
        text(".//n:dest/n:enderDest/n:CEP") == recipient["endereco"]["cep"],
        text(".//n:dest/n:enderDest/n:cMun")
        == recipient["endereco"]["codigoMunicipio"],
        text(".//n:dest/n:enderDest/n:UF") == recipient["endereco"]["uf"],
        fold(text(".//n:dest/n:enderDest/n:xLgr"))
        == fold(recipient["endereco"]["logradouro"]),
        fold(text(".//n:dest/n:enderDest/n:nro"))
        == fold(recipient["endereco"]["numero"]),
        fold(text(".//n:dest/n:enderDest/n:xBairro"))
        == fold(recipient["endereco"]["bairro"]),
        fold(text(".//n:dest/n:enderDest/n:xMun"))
        == fold(recipient["endereco"]["municipio"]),
        fold(text(".//n:dest/n:enderDest/n:xCpl"))
        == fold(recipient["endereco"].get("complemento")),
        text(".//n:ide/n:tpAmb") == str(payload["ambienteCodigo"]),
        int(text(".//n:ide/n:serie")) == int(payload["serie"]),
        int(text(".//n:ide/n:nNF")) == int(row.numero),
        text(".//n:infIntermed/n:CNPJ") == payload["intermediador"]["cnpj"],
        text(".//n:infIntermed/n:idCadIntTran") == row.seller_id,
        row.external_order_id in text(".//n:infAdic/n:infCpl"),
        text(".//n:infProt/n:nProt") == row.protocolo,
        Decimal(text(".//n:ICMSTot/n:vNF")) == expected_total,
        Decimal(text(".//n:ICMSTot/n:vProd"))
        == sum(Decimal(str(p["valorTotal"])) for p in payload["produtos"]),
        Decimal(text(".//n:ICMSTot/n:vDesc") or "0")
        == Decimal(row.discount_audit["effective_discount"]),
        Decimal(text(".//n:ICMSTot/n:vFrete") or "0")
        == Decimal(str(payload["frete"]["valor"])),
        text(".//n:ide/n:indPres") == "2",
        text(".//n:ide/n:indIntermed") == "1",
    ]
    actual_products = root.findall(".//n:det/n:prod", NS)
    actual_payments = root.findall(".//n:pag/n:detPag", NS)
    tests.extend(
        (
            len(actual_products) == len(payload["produtos"]),
            len(actual_payments) == len(payload["pagamentos"]),
        )
    )
    for actual, expected in zip(actual_products, payload["produtos"]):
        tests.extend(
            (
                actual.findtext("n:cProd", namespaces=NS)
                == str(expected["codigoProduto"]),
                Decimal(actual.findtext("n:qCom", namespaces=NS))
                == Decimal(str(expected["quantidade"])),
                Decimal(actual.findtext("n:vProd", namespaces=NS))
                == Decimal(str(expected["valorTotal"])),
                Decimal(actual.findtext("n:vUnCom", namespaces=NS))
                == Decimal(str(expected["valorUnitario"])),
                Decimal(actual.findtext("n:vDesc", default="0", namespaces=NS))
                == Decimal(str(expected.get("desconto", 0))),
                fold(actual.findtext("n:xProd", namespaces=NS))
                == fold(expected["descricao"]),
            )
        )
    for actual, expected in zip(actual_payments, payload["pagamentos"]):
        tests.extend(
            (
                actual.findtext("n:tPag", namespaces=NS) == expected["formaPagamento"],
                Decimal(actual.findtext("n:vPag", namespaces=NS))
                == Decimal(str(expected["valor"])),
            )
        )
        if expected.get("tipoIntegracao"):
            tests.append(
                actual.findtext("n:card/n:tpIntegra", namespaces=NS)
                == expected["tipoIntegracao"]
            )
    if not all(tests):
        raise IntNFeError("XmlInvalido")
    return data


def _fetch_status(db, row, api, token):
    connection = _connection(db, row.tenant_id, require_enabled=False)
    access = _access_token(api, connection, row.payload["ambienteCodigo"])
    result = api.document_status(access, "nfe", row.correlation_id)
    status = STATUS.get(int(result["status"]), "unknown")
    order_id, tenant_id = row.id, row.tenant_id
    row = _owned(db, tenant_id, order_id, token)
    # Nunca regredir um documento terminal por uma resposta atrasada.
    if row.status != "canceled" and not (
        row.status == "authorized" and status in {"processing", "unknown"}
    ):
        row.status = status
    if result.get("numero") is not None:
        row.numero = str(result["numero"])
    row.chave = result.get("chaveAcesso") or row.chave
    row.protocolo = result.get("protocolo") or row.protocolo
    row.blockers = (
        []
        if row.status in {"authorized", "processing"}
        else [
            blocker(
                "provider_" + row.status,
                "Consulte o resultado fiscal antes de qualquer nova emissão.",
            )
        ]
    )
    db.commit()
    if row.status == "authorized":
        try:
            content = row.xml or api.document_xml(access, "nfe", row.correlation_id)
            content = verify_xml(row, content)
            row = _owned(db, tenant_id, order_id, token)
            row.xml = content
            row.xml_sha256 = hashlib.sha256(content).hexdigest()
            row.blockers = []
        except (IntNFeError, ValueError, TypeError, InvalidOperation, ET.ParseError):
            row = _owned(db, tenant_id, order_id, token)
            row.blockers = [
                blocker(
                    "xml_not_verified",
                    "Nota autorizada; o XML ainda precisa passar na conferência de integridade e dos dados.",
                )
            ]
    from app.ecommerceai_fiscal.central import sync_note

    sync_note(db, row)
    _release(row)
    db.commit()
    return view(row, details=True)


def _provider_attempt(db, row, api, token):
    order_id, tenant_id = row.id, row.tenant_id
    try:
        connection = _connection(db, tenant_id, require_enabled=False)
        access = _access_token(api, connection, row.payload["ambienteCodigo"])
        if not row.correlation_id:
            result = api.issue_document(access, "nfe", row.payload, row.idempotency_key)
            row = _owned(db, tenant_id, order_id, token)
            row.correlation_id = result["correlationId"]
            row.status = "processing"
            db.commit()
        return _fetch_status(db, row, api, token)
    except (IntNFeError, DirectEmissionError) as exc:
        row = _owned(db, tenant_id, order_id, token)
        # A chave pode já ter produzido uma NF. Nunca liberar a revisão/chave.
        if row.status not in {"authorized", "canceled"}:
            row.status = (
                "unknown"
                if getattr(exc, "uncertain", False)
                or row.correlation_id
                or getattr(exc, "status", None) not in {400, 401, 403, 404, 422}
                else "rejected"
            )
        row.blockers = [
            blocker(
                "provider_" + row.status,
                "O emissor ainda não confirmou o resultado; o envio e a chave original foram preservados."
                if row.status == "unknown"
                else "O emissor recusou os dados. Revise a rejeição sem criar outra nota.",
            )
        ]
        _release(row)
        db.commit()
        return view(row, details=True)


def issue(
    db,
    tenant_id,
    order_id,
    expected_revision,
    expected_payload_hash,
    api,
    *,
    machine=True,
    user_id=None,
):
    row = get_order(db, tenant_id, order_id, lock=True)
    if (
        row.source_revision != expected_revision
        or row.payload_hash != expected_payload_hash
    ):
        fail(
            "snapshot_conflict",
            "A revisão ou fotografia fiscal mudou; prepare novamente.",
        )
    if row.idempotency_key:
        db.commit()
        return consult(db, tenant_id, order_id, api)
    prepare_row(db, tenant_id, row)
    if row.payload_hash != expected_payload_hash:
        db.commit()
        fail(
            "snapshot_conflict",
            "Cadastro fiscal, política ou mapeamento mudou; revise a fotografia atual.",
        )
    if row.status != "ready":
        db.commit()
        fail("order_blocked", "Resolva os bloqueios antes de emitir.")
    account = account_for(db, tenant_id, row.channel, row.seller_id)
    if machine and not account.auto_issue_enabled:
        fail(
            "automatic_emission_disabled",
            "A emissão automática desta conta ainda não foi autorizada.",
            403,
        )
    token = _claim(db, row)
    row = _owned(db, tenant_id, order_id, token)
    if row.idempotency_key:
        _release(row)
        db.commit()
        return consult(db, tenant_id, order_id, api)
    # Account writes and SKU mapping writes take this same account lock. Recheck
    # consent/cutoff and the exact payload after the claim commit and keep the
    # account locked until the intent/idempotency key is durably frozen.
    account = account_for(db, tenant_id, row.channel, row.seller_id, lock=True)
    prepare_row(db, tenant_id, row, owned_lease=token)
    if (
        row.status != "ready"
        or row.payload_hash != expected_payload_hash
        or not account
        or not account.active
        or (machine and not account.auto_issue_enabled)
    ):
        _release(row)
        db.commit()
        fail(
            "snapshot_conflict",
            "A conta, corte de ativação ou fotografia fiscal mudou antes do envio. Revise novamente.",
        )
    row.idempotency_key = f"corepet-eai-{row.tenant_id}-{row.id}-{uuid4().hex}"
    row.submitted_at = now()
    row.status = "processing"
    # Persistir snapshot/chave/lease ANTES de qualquer requisição de emissão.
    if user_id:
        log_action(
            db,
            user_id,
            "eai_fiscal_issue",
            "external_fiscal_order",
            row.id,
            tenant_id=tenant_id,
            new_value={
                "source_revision": row.source_revision,
                "payload_hash": row.payload_hash,
            },
            commit=False,
        )
    db.commit()
    return _provider_attempt(db, row, api, token)


def consult(db, tenant_id, order_id, api):
    row = get_order(db, tenant_id, order_id)
    if not row.idempotency_key or row.status in {
        "blocked",
        "ready",
        "rejected",
        "canceled",
    }:
        return view(row, details=True)
    if not row.correlation_id:
        age = now() - aware(row.submitted_at)
        if age < timedelta(minutes=2):
            return view(row, details=True)
        if age >= timedelta(hours=23):
            row.blockers = [
                blocker(
                    "idempotency_window_expired",
                    "O prazo de recuperação segura terminou. Preserve a nota; não renove a chave nem reenvie.",
                )
            ]
            row.status = "unknown"
            db.commit()
            return view(row, details=True)
    token = _claim(db, row)
    row = _owned(db, tenant_id, order_id, token)
    return _provider_attempt(db, row, api, token)


def xml_document(db, tenant_id, order_id):
    row = get_order(db, tenant_id, order_id)
    if row.status != "authorized" or not row.xml:
        fail(
            "xml_not_available",
            "O XML conferido fica disponível após a autorização.",
            409,
        )
    try:
        content = verify_xml(row, row.xml)
    except (IntNFeError, ValueError, TypeError, InvalidOperation, ET.ParseError):
        fail(
            "xml_not_verified",
            "O XML não passou na conferência de integridade e dos dados.",
            502,
        )
    return row, content
