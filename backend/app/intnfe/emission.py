"""Montagem, envio idempotente e reconciliação de documentos na IntNFe."""

from __future__ import annotations

import re
import unicodedata
import hashlib
import json
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID, uuid4

from app.bling_integration_fiscal import _resolver_fiscal_item_nfe
from app.intnfe.client import IntNFeError
from app.intnfe.fiscal_profile import local_profile
from app.intnfe.models import IntNFeConnection

CENT = Decimal("0.01")
AUTHORIZED_STATUS = 3
FINAL_STATUSES = {3, 4, 5, 6, 8}
STATUS_NAMES = {
    1: "aguardando",
    2: "processando",
    3: "autorizada",
    4: "rejeitada",
    5: "cancelada",
    6: "inutilizada",
    7: "contingencia",
    8: "denegada",
}
MARKETPLACE_CHANNELS = {
    "amazon",
    "mercado_livre",
    "mercadolivre",
    "ml",
    "shopee",
    "tiktok",
    "tiktok_shop",
}


class DirectEmissionError(Exception):
    def __init__(self, message, *, status=422, code=None, correlation=None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.correlation = correlation


def _digits(value):
    return re.sub(r"\D", "", str(value or ""))


def _text(value):
    normalized = str(value or "").strip()
    return normalized or None


def _money(value):
    return Decimal(str(value or 0)).quantize(CENT, rounding=ROUND_HALF_UP)


def _number(value):
    result = Decimal(str(value or 0))
    return int(result) if result == result.to_integral() else float(result)


def _ascii(value):
    normalized = unicodedata.normalize("NFKD", str(value or "").casefold())
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _connection(db, tenant_id, *, require_enabled=True):
    connection = (
        db.query(IntNFeConnection)
        .filter(IntNFeConnection.tenant_id == UUID(str(tenant_id)))
        .first()
    )
    if not connection or not connection.emitente_id:
        raise DirectEmissionError(
            "Conclua o vínculo com a IntNFe em Configurações > Integrações.", status=409
        )
    if require_enabled and not connection.emission_enabled:
        raise DirectEmissionError(
            "Escolha homologação ou produção na integração IntNFe antes de emitir.",
            status=409,
        )
    return connection


def direct_emission_enabled(db, tenant_id):
    if not hasattr(db, "query"):
        return False
    connection = (
        db.query(IntNFeConnection)
        .filter(IntNFeConnection.tenant_id == UUID(str(tenant_id)))
        .first()
    )
    return bool(connection and connection.emission_enabled)


def _emitter_credentials(connection, environment=None):
    selected = environment or connection.emission_environment
    if selected == 1:
        client_id = connection.production_client_id
        encrypted = connection.production_client_secret_encrypted
        secret = connection.production_client_secret if encrypted else None
    else:
        client_id = connection.client_id
        encrypted = connection.client_secret_encrypted
        secret = connection.client_secret if encrypted else None
    if not client_id or not secret:
        raise DirectEmissionError(
            "A credencial do ambiente escolhido ainda não está configurada.", status=409
        )
    return client_id, secret


def _payment_code(value):
    name = re.sub(r"[^a-z0-9]+", "_", _ascii(value)).strip("_")
    if "pix" in name:
        return "17"
    if "boleto" in name:
        return "15"
    if "deposit" in name or "transfer" in name:
        return "16"
    if "debito" in name:
        return "04"
    if "credito" in name or "cartao" in name:
        return "03"
    if "cheque" in name:
        return "02"
    if "dinheiro" in name:
        return "01"
    if "sem_pagamento" in name:
        return "90"
    return "99"


def _recipient(cliente, environment, document_type):
    if cliente is None:
        if document_type == "nfe":
            raise DirectEmissionError("A NF-e exige um cliente cadastrado.")
        return None
    document = _digits(getattr(cliente, "cnpj", None) or getattr(cliente, "cpf", None))
    if len(document) not in {11, 14}:
        if document_type == "nfce":
            return None
        raise DirectEmissionError(
            "Informe um CPF ou CNPJ válido no cadastro do cliente."
        )

    required = {
        "logradouro": _text(cliente.endereco),
        "numero": _text(cliente.numero),
        "bairro": _text(cliente.bairro),
        "municipio": _text(cliente.cidade),
        "codigoMunicipio": _digits(getattr(cliente, "codigo_municipio", None)),
        "uf": (_text(cliente.estado) or "").upper(),
        "cep": _digits(cliente.cep),
    }
    missing = [name for name, value in required.items() if not value]
    if missing and document_type == "nfe":
        raise DirectEmissionError(
            "Complete endereço, número, bairro, cidade, UF, CEP e código IBGE do cliente."
        )
    if not missing and (
        len(required["codigoMunicipio"]) != 7 or len(required["cep"]) != 8
    ):
        raise DirectEmissionError(
            "Confira o CEP e o código IBGE do município do cliente."
        )

    recipient = {
        "razaoSocial": (
            "NF-E EMITIDA EM AMBIENTE DE HOMOLOGACAO - SEM VALOR FISCAL"
            if environment == 2
            else _text(getattr(cliente, "razao_social", None)) or _text(cliente.nome)
        ),
        "indicadorIe": "1"
        if _text(getattr(cliente, "inscricao_estadual", None))
        else "9",
    }
    if not missing:
        recipient["endereco"] = required
    if len(document) == 14:
        recipient["cnpj"] = document
    else:
        recipient["cpf"] = document
    ie = _text(getattr(cliente, "inscricao_estadual", None))
    if ie:
        recipient["inscricaoEstadual"] = ie
    email = _text(getattr(cliente, "email", None))
    if email:
        recipient["email"] = email
    return recipient


def _tax(cst, origin, rate, taxable_amount):
    normalized_cst = str(cst)
    result = {"cst": normalized_cst, "origem": str(origin)}
    # CSOSN 102/500, entre outros, não recebem alíquota no grupo XML.
    if rate is not None and normalized_cst in {
        "00",
        "10",
        "20",
        "51",
        "70",
        "90",
        "900",
    }:
        normalized_rate = Decimal(str(rate))
        result["aliquota"] = float(normalized_rate)
        if normalized_rate > 0:
            result["valor"] = float(
                (taxable_amount * normalized_rate / Decimal("100")).quantize(
                    CENT, rounding=ROUND_HALF_UP
                )
            )
    return result


def _contribution(cst, rate, taxable_amount):
    result = {"cst": str(cst)}
    if rate is not None:
        normalized_rate = Decimal(str(rate))
        result["aliquota"] = float(normalized_rate)
        if normalized_rate > 0:
            result["baseCalculo"] = float(taxable_amount)
            result["valor"] = float(
                (taxable_amount * normalized_rate / Decimal("100")).quantize(
                    CENT, rounding=ROUND_HALF_UP
                )
            )
    return result


def build_payload(db, tenant, connection, venda, document_type):
    emitter, emitter_pending = local_profile(db, tenant.id)
    if emitter_pending:
        raise DirectEmissionError(" ".join(emitter_pending))
    environment = 1 if connection.emission_environment == 1 else 2
    recipient = _recipient(venda.cliente, environment, document_type)
    destination_uf = (
        recipient.get("endereco", {}).get("uf")
        if recipient
        else emitter["endereco"]["uf"]
    )
    interstate = destination_uf != emitter["endereco"]["uf"]

    products = []
    product_total = Decimal("0")
    item_discount_total = Decimal("0")
    for item in venda.itens or []:
        if _ascii(item.tipo) != "produto" or not item.produto:
            raise DirectEmissionError(
                "A emissão direta atual aceita somente itens de produto vinculados ao cadastro."
            )
        fiscal = _resolver_fiscal_item_nfe(db, venda, item)
        ncm = _digits(fiscal.get("ncm"))
        origin = _text(fiscal.get("origem_mercadoria"))
        cfop = _text(
            fiscal.get("cfop_interestadual")
            if interstate
            else fiscal.get("cfop_interno")
        )
        missing = [
            label
            for label, value in (
                ("NCM", ncm if len(ncm) == 8 else None),
                ("origem", origin),
                ("CFOP", cfop if cfop and len(cfop) == 4 else None),
                ("CSOSN/CST de ICMS", fiscal.get("cst_icms")),
                ("CST de PIS", fiscal.get("pis_cst")),
                ("CST de COFINS", fiscal.get("cofins_cst")),
            )
            if not value
        ]
        if missing:
            raise DirectEmissionError(
                f"Produto {item.produto.nome}: complete {', '.join(missing)} na aba Tributação."
            )
        quantity = Decimal(str(item.quantidade or 0))
        unit_price = Decimal(str(item.preco_unitario or 0))
        gross = (quantity * unit_price).quantize(CENT, rounding=ROUND_HALF_UP)
        discount = _money(item.desconto_item)
        if quantity <= 0 or unit_price < 0 or discount < 0 or discount > gross:
            raise DirectEmissionError(
                f"Produto {item.produto.nome}: confira quantidade, preço e desconto."
            )
        taxable = gross - discount
        product = {
            "codigoProduto": _text(item.produto.codigo)
            or _text(item.produto.codigo_barras)
            or str(item.produto.id),
            "descricao": _text(item.produto.nome),
            "ncm": ncm,
            "cfop": cfop,
            "unidade": _text(item.produto.unidade) or "UN",
            "quantidade": _number(quantity),
            "valorUnitario": float(unit_price),
            "valorTotal": float(gross),
            "impostos": {
                "icms": _tax(
                    fiscal["cst_icms"], origin, fiscal.get("icms_aliquota"), taxable
                ),
                "pis": _contribution(
                    fiscal["pis_cst"], fiscal.get("pis_aliquota"), taxable
                ),
                "cofins": _contribution(
                    fiscal["cofins_cst"], fiscal.get("cofins_aliquota"), taxable
                ),
            },
        }
        cest = _digits(fiscal.get("cest"))
        if cest:
            product["cest"] = cest
        if discount:
            product["desconto"] = float(discount)
        products.append(product)
        product_total += gross
        item_discount_total += discount

    if not products:
        raise DirectEmissionError("A venda não possui produtos para emitir a nota.")

    sale_discount = _money(venda.desconto_valor)
    total_discount = item_discount_total if item_discount_total > 0 else sale_discount
    if sale_discount and item_discount_total and sale_discount != item_discount_total:
        raise DirectEmissionError(
            "O desconto da venda difere da soma dos descontos dos itens."
        )
    freight = _money(venda.taxa_entrega if venda.tem_entrega else 0)
    calculated_total = product_total - total_discount + freight
    sale_total = _money(venda.total)
    if calculated_total != sale_total:
        raise DirectEmissionError(
            f"O total fiscal calculado (R$ {calculated_total}) difere do total da venda (R$ {sale_total})."
        )

    payments = []
    payment_total = Decimal("0")
    for payment in venda.pagamentos or []:
        value = _money(payment.valor)
        if value <= 0:
            continue
        code = _payment_code(payment.forma_pagamento)
        row = {"formaPagamento": code, "valor": float(value)}
        if code in {"03", "04"}:
            row["tipoIntegracao"] = "2"
        payments.append(row)
        payment_total += value
    if not payments or payment_total != sale_total:
        raise DirectEmissionError(
            "Confira as formas de pagamento: a soma precisa ser igual ao total da venda."
        )

    channel = re.sub(r"[^a-z0-9]+", "_", _ascii(venda.canal)).strip("_")
    if channel in MARKETPLACE_CHANNELS:
        raise DirectEmissionError(
            "Este pedido de marketplace ainda não contém no CorePet os dados do intermediador e da referência externa. Complete a importação antes de emitir."
        )

    payload = {
        "serie": connection.nfe_series
        if document_type == "nfe"
        else connection.nfce_series,
        "ambienteCodigo": environment,
        "naturezaOperacao": "Venda de mercadoria",
        "emitente": emitter,
        "produtos": products,
        "pagamentos": payments,
        "informacoesAdicionais": f"Venda {venda.numero_venda} - CorePet",
        "indicadorPresenca": "1" if channel == "loja_fisica" else "9",
        "frete": {"modalidade": "9", "valor": float(freight)},
        "documentosReferenciados": [],
    }
    if recipient:
        key = "destinatario" if document_type == "nfe" else "consumidor"
        payload[key] = recipient
    return payload


def preview(db, tenant, venda, document_type):
    connection = _connection(db, tenant.id)
    payload = build_payload(db, tenant, connection, venda, document_type)
    return {
        "provedor": "intnfe",
        "ambiente_codigo": payload["ambienteCodigo"],
        "ambiente": "produção" if payload["ambienteCodigo"] == 1 else "homologação",
        "modelo": 55 if document_type == "nfe" else 65,
        "serie": payload["serie"],
        "destinatario": payload.get("destinatario") or payload.get("consumidor"),
        "itens": [
            {
                "codigo": item["codigoProduto"],
                "descricao": item["descricao"],
                "quantidade": item["quantidade"],
                "valor_total": item["valorTotal"],
                "desconto": item.get("desconto", 0),
                "ncm": item["ncm"],
                "cfop": item["cfop"],
                "icms": item["impostos"]["icms"]["cst"],
                "pis": item["impostos"]["pis"]["cst"],
                "cofins": item["impostos"]["cofins"]["cst"],
            }
            for item in payload["produtos"]
        ],
        "pagamentos": payload["pagamentos"],
        "frete": payload["frete"]["valor"],
        "total": float(_money(venda.total)),
    }


def _access_token(api, connection, environment=None):
    client_id, secret = _emitter_credentials(connection, environment)
    try:
        return api.emitter_token(client_id, secret)
    except IntNFeError as exc:
        raise DirectEmissionError(
            "A IntNFe não aceitou a credencial do ambiente configurado.",
            status=503,
            code=exc.code,
            correlation=exc.correlation,
        ) from None


def issue(db, tenant, venda, document_type, api):
    connection = _connection(db, tenant.id)
    db.refresh(venda, with_for_update=True)
    if venda.nfe_correlation_id:
        return reconcile(db, venda, api, connection=connection)
    payload = build_payload(db, tenant, connection, venda, document_type)
    payload_hash = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if venda.nfe_idempotency_key:
        if (
            venda.nfe_status == "enviando"
            and venda.nfe_data_emissao
            and datetime.now() - venda.nfe_data_emissao < timedelta(minutes=2)
        ):
            raise DirectEmissionError(
                "Esta venda já está sendo enviada. Aguarde a confirmação.", status=409
            )
        if (
            venda.nfe_payload_hash != payload_hash
            or not venda.nfe_data_emissao
            or datetime.now() - venda.nfe_data_emissao >= timedelta(hours=23)
        ):
            raise DirectEmissionError(
                "Existe um envio sem confirmação e ele não pode ser repetido com segurança. Consulte o suporte.",
                status=409,
                code="ResultadoNaoConfirmado",
            )
        key = venda.nfe_idempotency_key
    else:
        key = f"corepet-{tenant.id}-{venda.id}-{uuid4().hex}"
        venda.nfe_provider = "intnfe"
        venda.nfe_tipo = document_type
        venda.nfe_modelo = "55" if document_type == "nfe" else "65"
        venda.nfe_ambiente = connection.emission_environment
        venda.nfe_serie = int(payload["serie"])
        venda.nfe_status = "enviando"
        venda.nfe_idempotency_key = key
        venda.nfe_payload_hash = payload_hash
        venda.nfe_data_emissao = datetime.now()
        db.commit()

    token = _access_token(api, connection)
    try:
        result = api.issue_document(token, document_type, payload, key)
    except IntNFeError as exc:
        venda.nfe_status = "inconclusiva" if exc.uncertain else "rejeitada"
        venda.nfe_codigo_erro = exc.code[:20] if exc.code else None
        if not exc.uncertain:
            venda.nfe_idempotency_key = None
            venda.nfe_payload_hash = None
            venda.nfe_data_emissao = None
        db.commit()
        raise DirectEmissionError(
            "O envio ficou sem confirmação; não crie outra nota para esta venda."
            if exc.uncertain
            else "A IntNFe recusou o envio antes do processamento.",
            status=503 if exc.uncertain else (422 if exc.status == 422 else 503),
            code=exc.code,
            correlation=exc.correlation,
        ) from None
    venda.nfe_correlation_id = result["correlationId"]
    venda.nfe_status = "processando"
    venda.status = "pago_nf"
    db.commit()
    return reconcile(db, venda, api, connection=connection, token=token)


def reconcile(db, venda, api, *, connection=None, token=None):
    if not venda.nfe_correlation_id:
        raise DirectEmissionError(
            "Esta venda ainda não possui identificador de emissão.", status=409
        )
    connection = connection or _connection(db, venda.tenant_id, require_enabled=False)
    token = token or _access_token(api, connection, venda.nfe_ambiente)
    try:
        result = api.document_status(token, venda.nfe_tipo, venda.nfe_correlation_id)
    except IntNFeError as exc:
        raise DirectEmissionError(
            "Não foi possível consultar o processamento da nota.",
            status=503,
            code=exc.code,
            correlation=exc.correlation,
        ) from None
    status_code = int(result.get("status") or 0)
    venda.nfe_status = STATUS_NAMES.get(status_code, "processando")
    venda.nfe_numero = result.get("numero") or venda.nfe_numero
    if result.get("serie") is not None:
        venda.nfe_serie = int(result["serie"])
    venda.nfe_chave = result.get("chaveAcesso") or venda.nfe_chave
    venda.nfe_protocolo = result.get("protocolo") or venda.nfe_protocolo
    error_code = _text(result.get("codigoErro"))
    venda.nfe_codigo_erro = error_code[:20] if error_code else None
    venda.nfe_motivo_rejeicao = _text(result.get("motivoRejeicao"))
    if status_code == AUTHORIZED_STATUS:
        venda.nfe_data_autorizacao = datetime.now()
        if not venda.nfe_xml:
            try:
                venda.nfe_xml = api.document_xml(
                    token, venda.nfe_tipo, venda.nfe_correlation_id
                ).decode("utf-8-sig")
            except (IntNFeError, UnicodeDecodeError):
                # A autorização continua válida; o XML pode ser buscado novamente.
                pass
    db.commit()
    return {
        "success": status_code == AUTHORIZED_STATUS,
        "processando": status_code not in FINAL_STATUSES,
        "provedor": "intnfe",
        "correlation_id": venda.nfe_correlation_id,
        "status_codigo": status_code,
        "situacao": venda.nfe_status,
        "numero": venda.nfe_numero,
        "serie": venda.nfe_serie,
        "chave_acesso": venda.nfe_chave,
        "protocolo": venda.nfe_protocolo,
        "codigo_erro": venda.nfe_codigo_erro,
        "motivo_rejeicao": venda.nfe_motivo_rejeicao,
        "ambiente_codigo": venda.nfe_ambiente,
    }


def download_document(db, venda, api, kind):
    if venda.nfe_provider != "intnfe" or not venda.nfe_correlation_id:
        raise DirectEmissionError(
            "A venda não possui documento emitido pela IntNFe.", status=404
        )
    connection = _connection(db, venda.tenant_id, require_enabled=False)
    token = _access_token(api, connection, venda.nfe_ambiente)
    try:
        if kind == "xml":
            content = api.document_xml(token, venda.nfe_tipo, venda.nfe_correlation_id)
            if not venda.nfe_xml:
                try:
                    venda.nfe_xml = content.decode("utf-8-sig")
                    db.commit()
                except UnicodeDecodeError:
                    pass
            return content
        return api.document_danfe(token, venda.nfe_tipo, venda.nfe_correlation_id)
    except IntNFeError as exc:
        raise DirectEmissionError(
            "O arquivo ainda não está disponível no emissor.",
            status=409 if exc.status in {404, 409} else 503,
            code=exc.code,
            correlation=exc.correlation,
        ) from None


def cancel(db, venda, api, justification):
    if len(str(justification or "").strip()) < 15:
        raise DirectEmissionError("A justificativa deve ter pelo menos 15 caracteres.")
    if venda.nfe_provider != "intnfe" or not venda.nfe_correlation_id:
        raise DirectEmissionError(
            "A venda não possui documento emitido pela IntNFe.", status=404
        )
    if venda.nfe_status != "autorizada":
        raise DirectEmissionError(
            "Somente uma nota autorizada pode ser cancelada.", status=409
        )
    connection = _connection(db, venda.tenant_id, require_enabled=False)
    token = _access_token(api, connection, venda.nfe_ambiente)
    try:
        api.cancel_document(
            token, venda.nfe_tipo, venda.nfe_correlation_id, justification.strip()
        )
    except IntNFeError as exc:
        raise DirectEmissionError(
            "O cancelamento não foi confirmado pela IntNFe.",
            status=503 if exc.uncertain else 422,
            code=exc.code,
            correlation=exc.correlation,
        ) from None
    result = reconcile(db, venda, api, connection=connection, token=token)
    result["cancelamento_solicitado"] = True
    return result
