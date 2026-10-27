"""Montagem fiscal a partir de fatos próprios do pedido, sem Venda ou XML anterior."""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
import re
import unicodedata
from uuid import UUID

import requests
from app.bling_integration_fiscal import (
    _resolver_fiscal_item_nfe,
    CSOSN_VALIDOS,
    CST_ICMS_VALIDOS,
)
from app.intnfe.emission import _product_taxes, _delivery_freight
from app.intnfe.fiscal_profile import local_profile
from app.intnfe.presentation import valid_cnpj
from app.produtos_models import Produto
from app.services.pessoa_duplicate_service import _cpf_valido
from app.services.venda_descontos import ratear_centavos
from app.ecommerceai_fiscal.models import FiscalSkuMapping

CENT = Decimal("0.01")
UF_CODES = dict(
    zip(
        (
            "RO",
            "AC",
            "AM",
            "RR",
            "PA",
            "AP",
            "TO",
            "MA",
            "PI",
            "CE",
            "RN",
            "PB",
            "PE",
            "AL",
            "SE",
            "BA",
            "MG",
            "ES",
            "RJ",
            "SP",
            "PR",
            "SC",
            "RS",
            "MS",
            "MT",
            "GO",
            "DF",
        ),
        (
            "11",
            "12",
            "13",
            "14",
            "15",
            "16",
            "17",
            "21",
            "22",
            "23",
            "24",
            "25",
            "26",
            "27",
            "28",
            "29",
            "31",
            "32",
            "33",
            "35",
            "41",
            "42",
            "43",
            "50",
            "51",
            "52",
            "53",
        ),
    )
)
PAYMENT_CODES = {
    "01",
    "02",
    "03",
    "04",
    "05",
    "10",
    "11",
    "12",
    "13",
    "15",
    "16",
    "17",
    "18",
    "19",
    "20",
    "21",
    "22",
}


def blocker(code, message, field=None):
    return {"code": code, "message": message, **({"field": field} if field else {})}


class PreparationBlocked(Exception):
    def __init__(self, blockers):
        self.blockers = blockers


def blocked(code, message, field=None):
    raise PreparationBlocked([blocker(code, message, field)])


def money(value):
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


def fold(value):
    return " ".join(
        "".join(
            c
            for c in unicodedata.normalize("NFD", str(value or ""))
            if not unicodedata.combining(c)
        )
        .casefold()
        .split()
    )


def complete_geography(address):
    """CEP apenas confirma geografia; não inventa logradouro ou número."""
    address = dict(address)
    postal = re.sub(r"[-\s]", "", address.get("postal_code") or "")
    state = (address.get("state") or "").upper()
    code = address.get("municipality_code") or ""
    if not re.fullmatch(r"[0-9]{8}", postal) or state not in UF_CODES:
        blocked(
            "geography_missing",
            "Confira CEP e UF do destinatário.",
            "recipient.address",
        )
    # Validate the explicit IBGE/UF binding. Missing geography is completed only
    # from the fixed public CEP service and after matching city/state of origin.
    if code:
        if not re.fullmatch(r"[0-9]{7}", code) or not code.startswith(UF_CODES[state]):
            blocked(
                "geography_mismatch",
                "O município IBGE não corresponde à UF.",
                "recipient.address.municipality_code",
            )
    try:
        response = requests.get(
            f"https://viacep.com.br/ws/{postal}/json/",
            timeout=(3, 6),
            allow_redirects=False,
        )
        if response.status_code != 200:
            raise ValueError
        geo = response.json()
        if not isinstance(geo, dict) or geo.get("erro"):
            raise ValueError
    except (requests.RequestException, ValueError):
        blocked(
            "geography_missing",
            "Não foi possível confirmar o município pelo CEP. Informe o código IBGE e confira cidade/UF.",
            "recipient.address.municipality_code",
        )
    if (
        fold(geo.get("localidade")) != fold(address.get("city"))
        or geo.get("uf") != state
    ):
        blocked(
            "geography_mismatch",
            "CEP, cidade e UF da origem divergem; revise o endereço.",
            "recipient.address",
        )
    resolved = str(geo.get("ibge") or "")
    if code and code != resolved:
        blocked(
            "geography_mismatch",
            "O CEP e o código IBGE informado não correspondem.",
            "recipient.address.municipality_code",
        )
    code = resolved
    if not re.fullmatch(r"[0-9]{7}", code) or not code.startswith(UF_CODES[state]):
        blocked(
            "geography_missing",
            "O CEP não confirmou um código IBGE válido.",
            "recipient.address.municipality_code",
        )
    address.update(postal_code=postal, state=state, municipality_code=code)
    return address


def recipient_payload(source, environment):
    customer = source.get("recipient") or {}
    document = str(customer.get("document") or "")
    if not document:
        blocked(
            "recipient_document_missing",
            "O pedido precisa do CPF/CNPJ fiscal do comprador.",
            "recipient.document",
        )
    if re.search(r"[^0-9.\s/\-]", document):
        blocked(
            "recipient_document_invalid",
            "O documento fiscal está mascarado ou inválido.",
            "recipient.document",
        )
    document = re.sub(r"\D", "", document)
    if not (
        (len(document) == 11 and _cpf_valido(document))
        or (len(document) == 14 and valid_cnpj(document))
    ):
        blocked(
            "recipient_document_invalid",
            "Confira os dígitos verificadores do CPF/CNPJ.",
            "recipient.document",
        )
    name = str(customer.get("name") or "").strip()
    address = customer.get("address") or {}
    if not name or "*" in name:
        blocked(
            "recipient_name_missing",
            "Informe o nome fiscal completo do comprador.",
            "recipient.name",
        )
    for field in ("street", "number", "district", "city", "state", "postal_code"):
        if not str(address.get(field) or "").strip() or "*" in str(address.get(field)):
            blocked(
                "address_missing",
                "Complete o endereço fiscal sem dados mascarados.",
                "recipient.address." + field,
            )
    address = complete_geography(address)
    result = {
        "cpf" if len(document) == 11 else "cnpj": document,
        "razaoSocial": name
        if environment == 1
        else "NF-E EMITIDA EM AMBIENTE DE HOMOLOGACAO - SEM VALOR FISCAL",
        "indicadorIe": customer.get("ie_status", "9"),
        "endereco": {
            "logradouro": address["street"],
            "numero": address["number"],
            "bairro": address["district"],
            "municipio": address["city"],
            "codigoMunicipio": address["municipality_code"],
            "uf": address["state"],
            "cep": address["postal_code"],
        },
    }
    if address.get("complement"):
        result["endereco"]["complemento"] = address["complement"]
    if result["indicadorIe"] == "1":
        ie = customer.get("state_registration")
        if not ie or not re.fullmatch(r"[0-9]{2,14}", ie):
            blocked(
                "recipient_ie_missing",
                "Informe a inscrição estadual do contribuinte.",
                "recipient.state_registration",
            )
        result["inscricaoEstadual"] = ie
    return result


@dataclass(frozen=True)
class FiscalTenantContext:
    tenant_id: object


@dataclass(frozen=True)
class FiscalProductContext:
    produto: object
    lote: object = None


def build_payload(db, tenant, connection, account, source):
    tenant_id = UUID(str(tenant.id))
    emitter, pending = local_profile(db, tenant_id)
    cnpj = re.sub(r"\D", "", str(tenant.cnpj or ""))
    if (
        not valid_cnpj(cnpj)
        or cnpj != account.emitter_cnpj
        or cnpj != connection.cnpj
        or cnpj != source["emitter_cnpj"]
    ):
        blocked(
            "emitter_mismatch",
            "O CNPJ do pedido, conta, empresa e vínculo fiscal deve ser o mesmo.",
            "emitter_cnpj",
        )
    if pending:
        blocked(
            "emitter_fiscal_pending",
            "Complete o cadastro fiscal da empresa antes de emitir.",
            "emitter_cnpj",
        )
    for key in ("tax", "recipient", "payment"):
        if source["source_evidence"].get(key) != "available":
            blocked(
                "source_evidence_missing",
                "A origem não confirmou os dados fiscais, pessoais e de pagamento.",
                "source_evidence." + key,
            )
    if source["order_status"] not in {"Unshipped", "PartiallyShipped"}:
        blocked(
            "order_status_ineligible",
            "Somente pedido pendente de envio pode iniciar uma emissão.",
            "order_status",
        )
    emitter["cnpj"] = cnpj
    environment = connection.emission_environment
    if environment not in {1, 2}:
        blocked(
            "emitter_environment_missing", "Selecione o ambiente fiscal no CorePet."
        )
    recipient = recipient_payload(source, environment)
    lines = source["items"]
    if not lines or len({line["external_item_id"] for line in lines}) != len(lines):
        blocked("items_invalid", "Informe itens com identidade externa única.", "items")
    gross = [money(line["gross_amount"]) for line in lines]
    discounts = [money(line["discount_amount"]) for line in lines]
    for line, amount, discount in zip(lines, gross, discounts):
        quantity, unit = Decimal(line["quantity"]), Decimal(line["unit_price"])
        if (
            quantity <= 0
            or quantity * unit <= 0
            or money(quantity * unit) != amount
            or discount > amount
        ):
            blocked(
                "item_totals_mismatch",
                "Confira quantidade, preço, total e desconto do item.",
                "items",
            )
    totals = source["totals"]
    products_total, source_discount, freight, original_total = (
        money(totals[k]) for k in ("products", "discount", "freight", "invoice_total")
    )
    if (
        sum(gross) != products_total
        or source_discount < sum(discounts)
        or source_discount > products_total
        or products_total - source_discount + freight != original_total
    ):
        blocked(
            "totals_mismatch",
            "Os totais e descontos explícitos da origem não fecham.",
            "totals",
        )
    paid = (
        money(source["buyer_paid_total"])
        if source.get("buyer_paid_total") is not None
        else None
    )
    if paid is None or not source["payments"]:
        blocked(
            "payment_missing", "Falta o pagamento documentado do comprador.", "payments"
        )
    extra_discount = Decimal(0)
    if paid != original_total:
        if account.discount_policy != "buyer_payment_total" or paid > original_total:
            blocked(
                "payment_total_mismatch",
                "O pagamento difere do total; revise a política e os valores documentados.",
                "buyer_paid_total",
            )
        extra_discount = original_total - paid
    effective_discount = source_discount + extra_discount
    if effective_discount > products_total:
        blocked(
            "payment_total_mismatch",
            "O desconto resultaria em base comercial negativa.",
            "totals",
        )
    remaining = [amount - discount for amount, discount in zip(gross, discounts)]
    allocated = ratear_centavos(effective_discount - sum(discounts), remaining)
    discounts = [a + b for a, b in zip(discounts, allocated)]
    payments = []
    for payment in source["payments"]:
        code = payment["fiscal_method"]
        if code not in PAYMENT_CODES or money(payment["amount"]) <= 0:
            blocked(
                "payment_unknown",
                "Informe uma forma fiscal conhecida e valor positivo.",
                "payments",
            )
        item = {"formaPagamento": code, "valor": float(money(payment["amount"]))}
        if code in {"03", "04", "17"}:
            if payment.get("integration_type") != "2":
                blocked(
                    "payment_integration_incomplete",
                    "Confira o tipo de integração documentado do pagamento.",
                    "payments.integration_type",
                )
            item["tipoIntegracao"] = "2"
        payments.append(item)
    if sum(money(p["amount"]) for p in source["payments"]) != paid:
        blocked(
            "payment_total_mismatch",
            "A soma dos pagamentos precisa coincidir com o total fiscal.",
            "payments",
        )
    interstate = recipient["endereco"]["uf"] != emitter["endereco"]["uf"]
    products = []
    tax_contexts = []
    for line, amount, discount in zip(lines, gross, discounts):
        mapping = (
            db.query(FiscalSkuMapping)
            .filter(
                FiscalSkuMapping.tenant_id == tenant_id,
                FiscalSkuMapping.account_id == account.id,
                FiscalSkuMapping.seller_sku == line["seller_sku"],
                FiscalSkuMapping.active.is_(True),
            )
            .first()
        )
        product = (
            db.query(Produto)
            .filter(
                Produto.tenant_id == tenant_id,
                Produto.id == mapping.product_id,
                Produto.deleted_at.is_(None),
            )
            .first()
            if mapping
            else None
        )
        if product is None or not product.ativo or not product.situacao:
            blocked(
                "sku_unmapped",
                "Vincule o SKU exato a um produto/kit ativo desta empresa.",
                "items." + line["external_item_id"] + ".seller_sku",
            )
        if str(product.tipo_produto or "").upper() in {"SERVICO", "PAI"}:
            blocked(
                "product_ineligible",
                "O vínculo precisa identificar mercadoria vendável.",
                "items",
            )
        fiscal = _resolver_fiscal_item_nfe(
            db, FiscalTenantContext(tenant_id), FiscalProductContext(product)
        )
        cfop = (
            fiscal.get("cfop_interestadual_nao_contribuinte")
            if interstate and recipient["indicadorIe"] == "9"
            else fiscal.get("cfop_interestadual" if interstate else "cfop_interno")
        )
        ncm = re.sub(r"\D", "", fiscal.get("ncm") or "")
        cst = str(fiscal.get("cst_icms") or "")
        valid_codes = CSOSN_VALIDOS if emitter["crt"] == "1" else CST_ICMS_VALIDOS
        if not (
            len(ncm) == 8
            and str(fiscal.get("origem_mercadoria") or "") in set("012345678")
            and re.fullmatch(r"[56][0-9]{3}", str(cfop or ""))
            and cst in valid_codes
            and fiscal.get("pis_cst")
            and fiscal.get("cofins_cst")
        ):
            blocked(
                "fiscal_product_pending",
                "Complete NCM, origem, CFOP e tributos no cadastro CorePet.",
                "items." + line["external_item_id"],
            )
        if not str(cfop).startswith("6" if interstate else "5"):
            blocked(
                "fiscal_cfop_destination",
                "O CFOP não corresponde ao destino da operação.",
                "items",
            )
        if (
            emitter["crt"] == "1"
            and recipient["indicadorIe"] == "9"
            and cst not in {"102", "103", "300", "400", "500"}
        ):
            blocked(
                "fiscal_product_pending",
                "Revise o CSOSN para consumidor não contribuinte.",
                "items",
            )
        result = {
            "codigoProduto": product.codigo or str(product.id),
            "descricao": product.nome,
            "ncm": ncm,
            "cfop": cfop,
            "unidade": product.unidade or "UN",
            "quantidade": float(Decimal(line["quantity"])),
            "valorUnitario": float(Decimal(line["unit_price"])),
            "valorTotal": float(amount),
            "impostos": _product_taxes(
                fiscal, fiscal["origem_mercadoria"], amount - discount
            ),
        }
        if discount:
            result["desconto"] = float(discount)
        if fiscal.get("cest"):
            result["cest"] = re.sub(r"\D", "", fiscal["cest"])
        products.append(result)
        tax_contexts.append((fiscal, fiscal["origem_mercadoria"], amount - discount))
    _delivery_freight(products, tax_contexts, freight)
    info = f"Pedido Amazon: #{source['external_order_id']} | Canal de venda: Amazon | Seller ID: {source['seller_id']}"
    if len(info) > 5000:
        blocked(
            "additional_information_invalid", "A referência comercial excedeu o limite."
        )
    payload = {
        "serie": str(connection.nfe_series),
        "ambienteCodigo": environment,
        "naturezaOperacao": "Venda de mercadoria",
        "emitente": emitter,
        "destinatario": recipient,
        "produtos": products,
        "pagamentos": payments,
        "informacoesAdicionais": info,
        "indicadorPresenca": "2",
        "intermediador": {
            "cnpj": "15436940000103",
            "identificadorCadastro": account.seller_id,
        },
        "frete": {"modalidade": "9", "valor": float(freight)},
        "documentosReferenciados": [],
    }
    audit = {
        "policy": account.discount_policy,
        "approved_by_user_id": account.approved_by_user_id,
        "source_discount": str(source_discount),
        "extra_discount": str(extra_discount),
        "effective_discount": str(effective_discount),
        "source_invoice_total": str(original_total),
        "buyer_paid_total": str(paid),
        "effective_invoice_total": str(paid),
    }
    return payload, audit
