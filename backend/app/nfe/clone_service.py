"""Clonagem fiscal sem venda, recebimento ou movimento de estoque adicional."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from uuid import uuid4

from fastapi import HTTPException

from app.audit_log import log_action
from app.intnfe.client import IntNFeError
from app.intnfe.commercial_context import CommercialContextError, context_data
from app.intnfe.cancellation import (
    data_evento,
    motivo_seguro,
    resultado_cancelamento,
    ultimo_cancelamento,
)
from app.intnfe.emission import (
    STATUS_NAMES,
    _access_token,
    _connection,
    download_document,
)
from app.intnfe.numbering import NumberingError, read_numbering
from app.intnfe.repository import get_tenant
from app.intnfe.xml_integrity import INVALID_MESSAGE, ensure_signed_xml
from app.nfe.clone_models import NotaFiscalClone
from app.nfe.clone_xml import NS, payload_from_xml
from app.nfe.danfe_nfce import validar_xml_nota
from app.nfe.documentos import obter_nota_documento, obter_xml_documento
from app.tenancy.context import tenant_context
from app.vendas_models import Venda
from defusedxml import ElementTree as ET

CENT = Decimal("0.01")


def money(value):
    try:
        result = Decimal(str(value))
        if not result.is_finite() or result < 0:
            raise InvalidOperation
        return result.quantize(CENT, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        raise HTTPException(
            422, "Informe valores numéricos válidos e não negativos."
        ) from None


def source_xml(db, tenant_id, api, origin):
    provider = origin.get("provedor")
    if provider == "intnfe":
        sale = (
            db.query(Venda)
            .filter(Venda.tenant_id == tenant_id, Venda.id == origin.get("venda_id"))
            .first()
        )
        if sale is None or sale.nfe_provider != "intnfe" or not sale.nfe_correlation_id:
            raise HTTPException(404, "Nota original não encontrada nesta empresa.")
        xml = sale.nfe_xml
        if not xml:
            xml = download_document(db, sale, api, "xml")
        if not sale.nfe_chave:
            raise HTTPException(
                422, "A nota original ainda não possui chave fiscal confirmada."
            )
        tenant = get_tenant(db, tenant_id)
        try:
            xml = ensure_signed_xml(
                xml,
                expected_cnpj="".join(filter(str.isdigit, str(tenant.cnpj or ""))),
                expected_key=sale.nfe_chave,
                document_type=sale.nfe_tipo,
            )
        except IntNFeError:
            raise HTTPException(502, INVALID_MESSAGE) from None
        xml = xml.decode("utf-8-sig")
        validar_xml_nota(xml.encode("utf-8"), sale.nfe_chave, int(sale.nfe_modelo))
        identity = {
            "provedor": provider,
            "id": sale.nfe_correlation_id,
            "venda_id": sale.id,
            "numero": str(sale.nfe_numero or ""),
            "serie": str(sale.nfe_serie or ""),
            "modelo": int(sale.nfe_modelo),
            "status": sale.nfe_status,
        }
    elif provider == "bling":
        try:
            note_id = int(origin.get("nfe_id") or origin.get("id"))
        except (ValueError, TypeError):
            raise HTTPException(
                422, "Identificador da nota original inválido."
            ) from None
        try:
            with tenant_context(tenant_id):
                detail, model, _sale = obter_nota_documento(db, tenant_id, note_id)
                xml = obter_xml_documento(detail, model).decode("utf-8-sig")
        except HTTPException as exc:
            raise HTTPException(
                exc.status_code,
                motivo_seguro(exc.detail)
                or "Não foi possível obter o documento original no Bling. Tente novamente em instantes.",
            ) from None
        except (ValueError, UnicodeDecodeError):
            raise
        except Exception:
            # O cliente legado do Bling embrulha HTTPError em Exception e
            # pode incluir páginas HTML de proxy. Nunca devolver esse corpo.
            raise HTTPException(
                502,
                "Não foi possível obter o documento original no Bling. Tente novamente em instantes.",
            ) from None
        from app.nfe.listagem_normalizacao import _status_nota_bling

        identity = {
            "provedor": provider,
            "id": str(note_id),
            "nfe_id": str(note_id),
            "numero": str(detail.get("numero") or ""),
            "serie": str(detail.get("serie") or ""),
            "modelo": model,
            "status": _status_nota_bling(detail),
        }
    else:
        raise HTTPException(422, "Escolha uma nota original do CorePet ou do Bling.")
    return xml, identity


def prepare(db, tenant_id, api, origin):
    tenant = get_tenant(db, tenant_id)
    connection = _connection(db, tenant_id)
    xml, identity = source_xml(db, tenant_id, api, origin)
    data, model = payload_from_xml(
        xml,
        cnpj="".join(filter(str.isdigit, str(tenant.cnpj or ""))),
        environment=connection.emission_environment,
    )
    return {
        "origem": identity,
        "dados": data,
        "modelo": model,
        "numero": None,
        "serie": data["serie"],
        "numeracao_automatica": True,
        "avisos": ["A numeração será atribuída pelo emissor ao confirmar a emissão."],
        "bloqueios": [],
    }, xml


def _normalize_commercial_fields(result, original, model):
    fields = ("indicadorPresenca", "intermediador")
    if model != 55:
        if any(result.get(key) != original.get(key) for key in fields):
            raise HTTPException(
                422,
                "A revisão de presença e intermediador está disponível somente para NF-e (55).",
            )
        return
    raw_presence = result.get("indicadorPresenca", "1")
    if type(raw_presence) not in (str, int):
        raise HTTPException(
            422, "Informe um indicador de presença válido para a operação."
        )
    presence = str(raw_presence).strip()
    if presence not in {"0", "1", "2", "3", "4", "5", "9"}:
        raise HTTPException(
            422, "Informe um indicador de presença válido para a operação."
        )
    result["indicadorPresenca"] = presence
    intermediary = result.get("intermediador")
    if intermediary is None:
        result.pop("intermediador", None)
        return
    if not isinstance(intermediary, dict) or set(intermediary) != {
        "cnpj",
        "identificadorCadastro",
    }:
        raise HTTPException(
            422, "Informe somente CNPJ e identificação de cadastro do intermediador."
        )
    try:
        commercial = context_data(
            None,
            override={
                "canal": "venda_direta_online",
                "intermediador_cnpj": intermediary["cnpj"],
                "intermediador_identificacao": intermediary["identificadorCadastro"],
            },
        )
    except CommercialContextError as exc:
        raise HTTPException(422, str(exc)) from None
    if (
        not commercial["intermediador_cnpj"]
        or not commercial["intermediador_identificacao"]
    ):
        raise HTTPException(
            422,
            "Complete o CNPJ e a identificação da loja ou vendedor no intermediador.",
        )
    if presence != "2":
        raise HTTPException(
            422, "Uma operação intermediada deve usar presença pela internet (2)."
        )
    result["intermediador"] = {
        "cnpj": commercial["intermediador_cnpj"],
        "identificadorCadastro": commercial["intermediador_identificacao"],
    }


def normalize_data(data, original, *, previous=None, modelo=55):
    """Permite revisão comercial sem alterar identidade, ambiente ou tributação."""
    if not isinstance(data, dict):
        raise HTTPException(422, "Os dados da nota são inválidos.")
    result = deepcopy(data)
    if any(
        result.get(key) != original.get(key)
        for key in (
            "emitente",
            "serie",
            "ambienteCodigo",
            "tipoOperacao",
            "finalidade",
            "documentosReferenciados",
        )
    ):
        raise HTTPException(
            422, "Preserve emitente, série, ambiente e finalidade da nota clonada."
        )
    if set(result) - set(original) - {"intermediador", "indicadorPresenca"}:
        raise HTTPException(
            422, "A nota contém campos desconhecidos. Reabra o rascunho."
        )
    _normalize_commercial_fields(result, original, modelo)
    products = result.get("produtos")
    if not isinstance(products, list) or len(products) != len(original["produtos"]):
        raise HTTPException(422, "Preserve todos os itens da nota original.")
    total = Decimal("0")
    for index, (item, old) in enumerate(zip(products, original["produtos"])):
        editable = {
            "descricao",
            "quantidade",
            "valorUnitario",
            "valorTotal",
            "desconto",
            "impostos",
        }
        if not isinstance(item, dict) or {
            key: value for key, value in item.items() if key not in editable
        } != {key: value for key, value in old.items() if key not in editable}:
            raise HTTPException(
                422, "Preserve a identificação e a classificação de todos os produtos."
            )
        if (
            not isinstance(item.get("descricao"), str)
            or not 1 <= len(item["descricao"].strip()) <= 120
        ):
            raise HTTPException(
                422, "Informe a descrição dos produtos com até 120 caracteres."
            )
        try:
            quantity = Decimal(str(item.get("quantidade", 0)))
            price = Decimal(str(item.get("valorUnitario", 0)))
            if (
                not quantity.is_finite()
                or not price.is_finite()
                or quantity <= 0
                or price < 0
            ):
                raise InvalidOperation
        except (InvalidOperation, ValueError, TypeError):
            raise HTTPException(
                422, "Confira quantidade e preço dos produtos."
            ) from None
        gross = money(quantity * price)
        discount = money(item.get("desconto", 0))
        if discount > gross:
            raise HTTPException(422, "O desconto não pode superar o valor do produto.")
        old_base = (
            money(old["valorTotal"])
            - money(old.get("desconto", 0))
            + money(old.get("frete", 0))
        )
        base = gross - discount + money(item.get("frete", 0))
        taxes = deepcopy(old["impostos"])
        accepted_taxes = [old["impostos"]]
        if previous is not None:
            accepted_taxes.append(previous["produtos"][index]["impostos"])
        if item.get("impostos") not in accepted_taxes:
            raise HTTPException(
                422,
                "A tributação da nota original é preservada. Ajustes fiscais exigem revisão específica.",
            )
        if base != old_base:
            for name, tax in taxes.items():
                if (
                    any(
                        money(tax.get(key, 0)) > 0
                        for key in (
                            "baseCalculoSt",
                            "valorSt",
                            "baseCalculoStRetido",
                            "valorStRetido",
                        )
                    )
                    or name == "ibsCbs"
                ):
                    raise HTTPException(
                        422,
                        "Esta nota possui tributação especial. Os valores dos itens precisam ser preservados na clonagem.",
                    )
                for group in [tax, tax.get("fcp")]:
                    if not group:
                        continue
                    if money(group.get("valor", 0)) > 0 and "aliquota" not in group:
                        raise HTTPException(
                            422,
                            "O imposto original não possui alíquota suficiente para recalcular os valores.",
                        )
                    if "baseCalculo" in group:
                        group["baseCalculo"] = (
                            float(
                                money(
                                    base * Decimal(str(group["baseCalculo"])) / old_base
                                )
                            )
                            if old_base
                            else float(base)
                        )
                    if "valor" in group or money(group.get("aliquota", 0)):
                        taxable = Decimal(str(group.get("baseCalculo", base)))
                        reduction = Decimal(str(group.get("percentualReducaoBc", 0)))
                        group["valor"] = float(
                            money(
                                taxable
                                * (1 - reduction / 100)
                                * Decimal(str(group.get("aliquota", 0)))
                                / 100
                            )
                        )
        item["valorTotal"] = float(gross)
        item["impostos"] = taxes
        total += gross - discount + money(taxes.get("ipi", {}).get("valor", 0))
    freight = result.get("frete", {})
    if freight != original.get("frete", {}):
        raise HTTPException(
            422,
            "O frete original é preservado para manter o rateio e os impostos corretos.",
        )
    total += money(freight.get("valor", 0))
    payments = result.get("pagamentos")
    if (
        not isinstance(payments, list)
        or not payments
        or any(not isinstance(payment, dict) for payment in payments)
    ):
        raise HTTPException(422, "Informe os pagamentos da nota.")
    if (
        sum((money(payment.get("valor", 0)) for payment in payments), Decimal("0"))
        != total
    ):
        raise HTTPException(
            422, "A soma dos pagamentos deve ser igual ao total da nota."
        )
    if (
        not isinstance(result.get("naturezaOperacao"), str)
        or not 1 <= len(result["naturezaOperacao"].strip()) <= 60
    ):
        raise HTTPException(
            422, "Informe a natureza da operação com até 60 caracteres."
        )
    return result


def view(row):
    total = sum(
        (
            money(item["valorTotal"])
            - money(item.get("desconto", 0))
            + money(item.get("impostos", {}).get("ipi", {}).get("valor", 0))
            for item in row.dados["produtos"]
        ),
        Decimal("0"),
    ) + money(row.dados.get("frete", {}).get("valor", 0))
    cancellation_started = data_evento(row.cancelamento_solicitado_em)
    can_retry_cancellation = (
        row.status == "autorizada"
        and row.cancelamento_status == "pendente"
        and cancellation_started is not None
        and datetime.now(timezone.utc) - cancellation_started >= timedelta(minutes=2)
    )
    return {
        "id": row.id,
        "status": row.status,
        "origem": row.origem,
        "dados": row.dados,
        "modelo": row.modelo,
        "serie": row.dados["serie"],
        "numero": row.numero,
        "chave": row.chave,
        "protocolo": row.protocolo,
        "motivo": row.motivo,
        "numeracao_automatica": True,
        "correlation_id": row.correlation_id,
        "total": float(total),
        "cancelamento_status": row.cancelamento_status,
        "cancelamento_codigo": row.cancelamento_codigo,
        "cancelamento_motivo": row.cancelamento_motivo,
        "cancelamento_solicitado_em": cancellation_started.isoformat()
        if cancellation_started
        else None,
        "pode_tentar_cancelamento": can_retry_cancellation,
    }


def get_clone(db, tenant_id, clone_id, *, lock=False):
    query = db.query(NotaFiscalClone).filter(
        NotaFiscalClone.tenant_id == tenant_id, NotaFiscalClone.id == clone_id
    )
    row = (query.populate_existing().with_for_update() if lock else query).first()
    if row is None:
        raise HTTPException(404, "Nota clonada não encontrada nesta empresa.")
    return row


def create(db, tenant_id, user_id, api, origin, data):
    prepared, xml = prepare(db, tenant_id, api, origin)
    row = NotaFiscalClone(
        tenant_id=tenant_id,
        origem=prepared["origem"],
        dados=normalize_data(data, prepared["dados"], modelo=prepared["modelo"]),
        xml_origem=xml,
        modelo=prepared["modelo"],
        status="rascunho",
    )
    db.add(row)
    db.flush()
    log_action(
        db,
        user_id,
        "nfe_clonar_rascunho",
        "nota_fiscal_clone",
        row.id,
        new_value={"origem": row.origem, "modelo": row.modelo},
        tenant_id=tenant_id,
        commit=False,
    )
    db.commit()
    return view(row)


def update(db, tenant_id, user_id, clone_id, data):
    row = get_clone(db, tenant_id, clone_id, lock=True)
    if row.status != "rascunho" or row.idempotency_key or row.correlation_id:
        raise HTTPException(409, "Somente rascunhos sem envio podem ser alterados.")
    original, _ = payload_from_xml(
        row.xml_origem,
        cnpj=row.dados["emitente"]["cnpj"],
        environment=row.dados["ambienteCodigo"],
    )
    row.dados = normalize_data(data, original, previous=row.dados, modelo=row.modelo)
    log_action(
        db,
        user_id,
        "nfe_clonar_editar",
        "nota_fiscal_clone",
        row.id,
        tenant_id=tenant_id,
        commit=False,
    )
    db.commit()
    return view(row)


def consult(db, tenant_id, clone_id, api):
    row = get_clone(db, tenant_id, clone_id)
    if not row.correlation_id:
        if not row.idempotency_key or row.status not in {"enviando", "inconclusiva"}:
            return view(row)
        age = datetime.now(timezone.utc) - data_evento(row.enviado_em)
        if age < timedelta(minutes=2):
            return view(row)
        if age >= timedelta(hours=23):
            row.motivo = "O prazo para recuperar o envio com segurança terminou. Consulte o suporte; não emita uma segunda nota."
            db.commit()
            return view(row)
        # A consulta recupera a resposta perdida usando EXATAMENTE a mesma
        # chave e corpo dentro da janela documentada de 24h. Não há nova NF.
        row = get_clone(db, tenant_id, clone_id, lock=True)
        if row.correlation_id:
            db.commit()
            return consult(db, tenant_id, clone_id, api)
        age = datetime.now(timezone.utc) - data_evento(row.enviado_em)
        if age >= timedelta(hours=23) or row.status not in {"enviando", "inconclusiva"}:
            return view(row)
        connection = _connection(db, tenant_id, require_enabled=False)
        token = _access_token(api, connection, row.dados["ambienteCodigo"])
        try:
            result = api.issue_document(
                token,
                "nfe" if row.modelo == 55 else "nfce",
                row.dados,
                row.idempotency_key,
            )
        except IntNFeError:
            db.rollback()
            raise HTTPException(
                503,
                "A recuperação do envio ainda não foi confirmada. A mesma chave de segurança foi preservada.",
            ) from None
        row.correlation_id = result["correlationId"]
        row.status = "processando"
        db.commit()
    connection = _connection(db, tenant_id, require_enabled=False)
    token = _access_token(api, connection, row.dados["ambienteCodigo"])
    try:
        result = api.document_status(
            token, "nfe" if row.modelo == 55 else "nfce", row.correlation_id
        )
        observed = STATUS_NAMES[int(result["status"])]
        events = None
        downloaded_xml = None
        if row.cancelamento_status:
            try:
                events = api.document_events(
                    token, "nfe" if row.modelo == 55 else "nfce", row.correlation_id
                )
            except IntNFeError:
                pass
        if observed == "autorizada" and not row.xml:
            try:
                downloaded_xml = api.document_xml(
                    token, "nfe" if row.modelo == 55 else "nfce", row.correlation_id
                ).decode("utf-8-sig")
            except (IntNFeError, UnicodeDecodeError):
                pass
        # Releitura travada após a rede: uma consulta antiga não sobrescreve
        # um cancelamento confirmado em outra sessão durante a espera.
        row = get_clone(db, tenant_id, clone_id, lock=True)
        if row.status != "cancelada" and not (
            row.status == "autorizada"
            and observed in {"aguardando", "processando", "contingencia"}
        ):
            row.status = observed
        row.numero = str(result.get("numero") or row.numero or "") or None
        row.chave = result.get("chaveAcesso") or row.chave
        row.protocolo = result.get("protocolo") or row.protocolo
        row.motivo = motivo_seguro(result.get("motivoRejeicao"))
        if events is not None:
            cancellation = ultimo_cancelamento(
                events, solicitado_em=row.cancelamento_solicitado_em
            )
            if cancellation and row.cancelamento_status != "confirmado":
                row.cancelamento_status = cancellation["status"]
                row.cancelamento_codigo = cancellation.get("codigo")
                row.cancelamento_motivo = cancellation.get("motivo")
        if row.status == "cancelada" or row.cancelamento_status == "confirmado":
            row.status = "cancelada"
            row.cancelamento_status = "confirmado"
        if downloaded_xml and not row.xml:
            row.xml = downloaded_xml
        db.commit()
        return view(row)
    except IntNFeError:
        raise HTTPException(
            503,
            "Não foi possível consultar a nota clonada. O envio existente foi preservado.",
        ) from None


def issue(db, tenant_id, user_id, clone_id, api):
    row = get_clone(db, tenant_id, clone_id, lock=True)
    if row.correlation_id:
        db.commit()
        return consult(db, tenant_id, clone_id, api)
    if row.idempotency_key and row.status in {"enviando", "inconclusiva"}:
        db.commit()
        return consult(db, tenant_id, clone_id, api)
    if row.idempotency_key or row.status != "rascunho":
        raise HTTPException(
            409,
            "Este rascunho já teve um envio. Consulte a situação; não crie outra nota para repetir a tentativa.",
        )
    connection = _connection(db, tenant_id)
    if connection.emission_environment != row.dados["ambienteCodigo"]:
        raise HTTPException(
            409,
            "O ambiente fiscal mudou. Revise a integração antes de emitir este rascunho.",
        )
    # Confirma o piso remoto, sem reservar/copiar o número da nota anterior.
    try:
        numbering = read_numbering(db, tenant_id, api)
    except NumberingError as exc:
        raise HTTPException(exc.status, str(exc)) from None
    current = next(
        (
            entry
            for entry in numbering.series
            if entry.modelo == row.modelo
            and entry.ambienteCodigo == row.dados["ambienteCodigo"]
            and int(entry.serie) == int(row.dados["serie"])
        ),
        None,
    )
    root = ET.fromstring(row.xml_origem)
    source_env = root.findtext(".//n:ide/n:tpAmb", namespaces=NS)
    source_number = (
        int(row.origem.get("numero") or 0)
        if str(row.origem.get("numero") or "").isdigit()
        else 0
    )
    if (
        source_env == str(row.dados["ambienteCodigo"])
        and (current.ultimoNumero if current else 0) < source_number
    ):
        raise HTTPException(
            409,
            "A numeração do emissor está atrás da nota original. Atualize a sequência em Configurações > IntNFe antes de emitir.",
        )
    token = _access_token(api, connection, row.dados["ambienteCodigo"])
    row.idempotency_key = f"corepet-clone-{tenant_id}-{row.id}-{uuid4().hex}"
    row.enviado_em = datetime.now(timezone.utc)
    row.status = "enviando"
    log_action(
        db,
        user_id,
        "nfe_clonar_emitir",
        "nota_fiscal_clone",
        row.id,
        new_value={
            "modelo": row.modelo,
            "serie": row.dados["serie"],
            "ambiente": row.dados["ambienteCodigo"],
        },
        tenant_id=tenant_id,
        commit=False,
    )
    db.commit()
    try:
        result = api.issue_document(
            token, "nfe" if row.modelo == 55 else "nfce", row.dados, row.idempotency_key
        )
    except IntNFeError as exc:
        row.status = "inconclusiva" if exc.uncertain else "rejeitada"
        row.motivo = (
            "Envio sem confirmação. Consulte o suporte antes de qualquer nova tentativa."
            if exc.uncertain
            else "O emissor recusou o envio: "
            + " | ".join(exc.validation_errors or [exc.code])
        )
        db.commit()
        return view(row)
    row.correlation_id = result["correlationId"]
    row.status = "processando"
    db.commit()
    return consult(db, tenant_id, clone_id, api)


def cancel(db, tenant_id, user_id, clone_id, api, justification):
    justification = str(justification or "").strip()
    if not 15 <= len(justification) <= 255:
        raise HTTPException(422, "A justificativa deve conter de 15 a 255 caracteres.")
    row = get_clone(db, tenant_id, clone_id, lock=True)
    if row.status != "autorizada" or not row.correlation_id:
        raise HTTPException(409, "Somente uma nota autorizada pode ser cancelada.")
    if row.cancelamento_status in {"pendente", "solicitado"}:
        db.commit()
        observed = consult(db, tenant_id, clone_id, api)
        if not observed["pode_tentar_cancelamento"]:
            return observed
        # Repetição somente por clique explícito, depois de consulta e do
        # intervalo de proteção. Eventos aceitos continuam só em consulta.
        row = get_clone(db, tenant_id, clone_id, lock=True)
        if row.status != "autorizada" or row.cancelamento_status != "pendente":
            return view(row)
    connection = _connection(db, tenant_id, require_enabled=False)
    token = _access_token(api, connection, row.dados["ambienteCodigo"])
    row.cancelamento_status = "pendente"
    row.cancelamento_solicitado_em = datetime.now(timezone.utc)
    started = row.cancelamento_solicitado_em
    log_action(
        db,
        user_id,
        "nfe_clone_cancelamento_solicitado",
        "nota_fiscal_clone",
        row.id,
        tenant_id=tenant_id,
        commit=False,
    )
    db.commit()
    try:
        result = api.cancel_document(
            token,
            "nfe" if row.modelo == 55 else "nfce",
            row.correlation_id,
            justification,
        )
        outcome = resultado_cancelamento(result) or {
            "status": "solicitado",
            "codigo": None,
            "motivo": None,
        }
    except IntNFeError as exc:
        outcome = {
            "status": "pendente" if exc.uncertain else "recusado",
            "codigo": exc.code,
            "motivo": exc.provider_message
            or "O cancelamento ainda não foi confirmado. Consulte a situação da nota.",
        }
    row = get_clone(db, tenant_id, clone_id, lock=True)
    if (
        row.status != "cancelada"
        and row.cancelamento_status != "confirmado"
        and data_evento(row.cancelamento_solicitado_em) == data_evento(started)
    ):
        row.cancelamento_status = outcome["status"]
        row.cancelamento_codigo = outcome.get("codigo")
        row.cancelamento_motivo = outcome.get("motivo")
        if outcome["status"] == "confirmado":
            row.status = "cancelada"
    db.commit()
    try:
        return consult(db, tenant_id, clone_id, api)
    except HTTPException:
        return view(row)
