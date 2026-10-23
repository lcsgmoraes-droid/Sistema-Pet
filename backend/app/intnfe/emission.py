"""Montagem, envio idempotente e reconciliação de documentos na IntNFe."""

from __future__ import annotations

import re
import unicodedata
import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID, uuid4
from types import SimpleNamespace

from app.bling_integration_fiscal import (
    CSOSN_VALIDOS,
    CST_ICMS_VALIDOS,
    _resolver_fiscal_item_nfe,
    pendencias_cfop_csosn_nfce,
)
from app.financeiro.crediario_parcelamento import montar_plano_crediario
from app.intnfe.client import IntNFeError
from app.intnfe.cancellation import (
    aplicar_resultado_cancelamento,
    campos_cancelamento,
    campos_cancelamento_com_aliases,
    resultado_cancelamento,
    ultimo_cancelamento,
    data_evento,
)
from app.audit_log import log_action
from app.intnfe.delivery_address import DeliveryAddressError, resolver_endereco_entrega
from app.intnfe.fiscal_profile import local_profile
from app.intnfe.models import IntNFeConnection, IntNFeEmissionSequence
from app.intnfe.rejection_diagnostics import (
    enrich_validation_items,
    message_corrections,
    rejection_diagnostics,
)
from app.produtos_estoque_models import EstoqueMovimentacao, ProdutoLote
from app.services.venda_descontos import (
    bruto_compativel_com_quantidade,
    ratear_centavos,
    ratear_descontos_venda,
)
from app.services.xml_contabilidade_hook import tentar_enfileirar_documento
from app.vendas.fiscal_status import sincronizar_venda_apos_cancelamento_fiscal
from app.utils.timezone import as_brasilia_naive

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
    def __init__(
        self,
        message,
        *,
        status=422,
        code=None,
        correlation=None,
        validation=None,
        cancelamento=None,
    ):
        super().__init__(message)
        self.status = status
        self.code = code
        self.correlation = correlation
        self.validation = validation
        self.cancelamento = cancelamento


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


def _legacy_quantity_rounding(venda, item, gross):
    """Reconhece o subtotal antigo com quantidade calculada em 4 e salva em 3 casas."""
    if (
        getattr(venda, "desconto_venda_valor", None) is not None
        or getattr(item, "subtotal", None) is None
    ):
        return False
    quantity = Decimal(str(item.quantidade or 0))
    unit_price = Decimal(str(item.preco_unitario or 0))
    if (
        not quantity.is_finite()
        or not unit_price.is_finite()
        or quantity <= 0
        or unit_price <= 0
        or quantity == quantity.to_integral()
        or quantity != quantity.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
        or gross <= 0
    ):
        return False
    previous_quantity = (gross / unit_price).quantize(
        Decimal("0.0001"), rounding=ROUND_HALF_UP
    )
    return (
        abs(previous_quantity - quantity) <= Decimal("0.0005")
        and previous_quantity.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
        == quantity
        and _money(previous_quantity * unit_price) == gross
    )


def _quantity_rounding(venda, item, gross):
    if getattr(venda, "desconto_venda_valor", None) is not None:
        return bruto_compativel_com_quantidade(item, gross)
    return _legacy_quantity_rounding(venda, item, gross)


def _legacy_aggregate_gross(venda):
    """Reproduz apenas a soma legada crua, conservando os descontos salvos.

    O rateio existe somente no payload. Cada linha deve estar coerente antes
    dele e o bruto agregado deve reproduzir exatamente o total persistido.
    """
    if getattr(venda, "desconto_venda_valor", None) is not None:
        return {}
    items = list(venda.itens or [])
    sale_discount = _money(venda.desconto_valor)
    if len(items) < 2 or sale_discount <= 0:
        return {}
    raw_grosses, saved_grosses, discounts, quantities = [], [], [], []
    for item in items:
        if _ascii(item.tipo) != "produto" or getattr(item, "subtotal", None) is None:
            return {}
        quantity = Decimal(str(item.quantidade or 0))
        unit_price = Decimal(str(item.preco_unitario or 0))
        if (
            not quantity.is_finite()
            or not unit_price.is_finite()
            or quantity <= 0
            or unit_price < 0
        ):
            return {}
        discount = _money(item.desconto_item)
        gross = _money(item.subtotal) + discount
        raw = quantity * unit_price
        if discount < 0 or discount > gross or gross != _money(raw):
            return {}
        raw_grosses.append(raw)
        saved_grosses.append(gross)
        discounts.append(discount)
        quantities.append(quantity)
    if sum(discounts, Decimal("0")) != sale_discount or all(
        quantity == quantity.to_integral() for quantity in quantities
    ):
        return {}
    freight = _money(venda.taxa_entrega if venda.tem_entrega else 0)
    target = _money(venda.total) + sale_discount - freight
    saved_total = sum(saved_grosses, Decimal("0"))
    if (
        target <= 0
        or target == saved_total
        or target != _money(sum(raw_grosses, Decimal("0")))
        or abs(saved_total - target) > CENT * (len(items) - 1)
    ):
        return {}
    allocated = ratear_centavos(target, raw_grosses)
    if any(
        gross < discount or abs(gross - saved) > CENT
        for gross, discount, saved in zip(allocated, discounts, saved_grosses)
    ):
        return {}
    return {id(item): gross for item, gross in zip(items, allocated)}


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
    if "cashback" in name:
        return "19"
    if "pix" in name:
        return "17"
    if "boleto" in name:
        return "15"
    if "crediario" in name or "credito_loja" in name or "credito_cliente" in name:
        return "05"
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


def _is_crediario_payment(value):
    name = re.sub(r"[^a-z0-9]+", "_", _ascii(value)).strip("_")
    return "crediario" in name or "credito_loja" in name


def _date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _crediario_accounts(venda):
    accounts = []
    for account in getattr(venda, "contas_receber", None) or []:
        due_date = _date(getattr(account, "data_vencimento", None))
        if due_date is None or _ascii(getattr(account, "status", None)) in {
            "cancelado",
            "cancelada",
        }:
            continue
        payment_type = _ascii(
            getattr(getattr(account, "forma_pagamento", None), "tipo", None)
        )
        description = _ascii(getattr(account, "descricao", None))
        if payment_type == "crediario" or "crediario" in description:
            accounts.append(account)

    if not accounts:
        credit_payments = [
            payment
            for payment in (getattr(venda, "pagamentos", None) or [])
            if _is_crediario_payment(getattr(payment, "forma_pagamento", None))
        ]
        other_payments = [
            payment
            for payment in (getattr(venda, "pagamentos", None) or [])
            if not _is_crediario_payment(getattr(payment, "forma_pagamento", None))
        ]
        if credit_payments and not other_payments:
            accounts = [
                account
                for account in (getattr(venda, "contas_receber", None) or [])
                if _date(getattr(account, "data_vencimento", None)) is not None
                and _ascii(getattr(account, "status", None))
                not in {"cancelado", "cancelada"}
            ]

    return sorted(
        accounts,
        key=lambda account: (
            _date(getattr(account, "data_vencimento", None)),
            int(getattr(account, "numero_parcela", None) or 0),
            int(getattr(account, "id", None) or 0),
        ),
    )


def _crediario_installments(venda):
    """Retorna os vencimentos reais; usa o plano somente se ainda não houver contas."""
    accounts = _crediario_accounts(venda)
    if accounts:
        total_accounts = len(accounts)
        return [
            {
                "numero": int(getattr(account, "numero_parcela", None) or index),
                "total_parcelas": int(
                    getattr(account, "total_parcelas", None) or total_accounts
                ),
                "data_vencimento": _date(account.data_vencimento),
                "valor": _money(
                    getattr(account, "valor_original", None)
                    or getattr(account, "valor_final", None)
                ),
            }
            for index, account in enumerate(accounts, start=1)
        ]

    installments = []
    for payment in getattr(venda, "pagamentos", None) or []:
        if not _is_crediario_payment(getattr(payment, "forma_pagamento", None)):
            continue
        first_due_date = _date(getattr(payment, "data_recebimento_prevista", None))
        if first_due_date is None:
            continue
        try:
            count = max(1, int(getattr(payment, "numero_parcelas", None) or 1))
            plan = montar_plano_crediario(
                valor_total=_money(getattr(payment, "valor", None)),
                numero_parcelas=count,
                primeira_data=first_due_date,
                intervalo=getattr(payment, "intervalo_crediario", None),
            )
        except (TypeError, ValueError):
            continue
        installments.extend(plan)
    return installments


def _format_brl(value):
    formatted = f"{_money(value):,.2f}"
    return formatted.replace(",", "_").replace(".", ",").replace("_", ".")


def _additional_information(venda, installments):
    parts = [f"Venda {venda.numero_venda}"]
    observation = _text(getattr(venda, "observacoes", None))
    if observation:
        parts.append(f"Observacoes da venda: {' '.join(observation.split())}")
    if installments:
        schedule = "; ".join(
            (
                f"{item['numero']}/{item['total_parcelas']} vence em "
                f"{item['data_vencimento'].strftime('%d/%m/%Y')} - "
                f"R$ {_format_brl(item['valor'])}"
            )
            for item in installments
        )
        parts.append(f"Crediario: {schedule}")
    return " | ".join(parts)[:5000]


def _recipient(
    cliente,
    environment,
    document_type,
    *,
    require_identity=False,
    require_address=False,
):
    if cliente is None:
        if document_type == "nfe":
            raise DirectEmissionError("A NF-e exige um cliente cadastrado.")
        if require_identity:
            raise DirectEmissionError(
                "Esta NFC-e exige um consumidor identificado com CPF ou CNPJ."
            )
        return None
    document = _digits(getattr(cliente, "cnpj", None) or getattr(cliente, "cpf", None))
    if len(document) not in {11, 14}:
        if document_type == "nfce" and not require_identity:
            return None
        raise DirectEmissionError(
            "Informe um CPF ou CNPJ válido no cadastro do cliente."
        )

    email = _text(getattr(cliente, "email", None))
    if document_type == "nfce":
        consumer = {
            "nome": (
                "NF-E EMITIDA EM AMBIENTE DE HOMOLOGACAO - SEM VALOR FISCAL"
                if environment == 2
                else _text(getattr(cliente, "razao_social", None))
                or _text(cliente.nome)
            )
        }
        if len(document) == 14:
            consumer["cnpj"] = document
        else:
            consumer["cpf"] = document
        if email:
            consumer["email"] = email
        return consumer

    address = {
        "logradouro": _text(cliente.endereco),
        "numero": _text(cliente.numero),
        "bairro": _text(cliente.bairro),
        "municipio": _text(cliente.cidade),
        "codigoMunicipio": _digits(getattr(cliente, "codigo_municipio", None)),
        "uf": (_text(cliente.estado) or "").upper(),
    }
    missing = [name for name, value in address.items() if not value]
    if missing and (document_type == "nfe" or require_address):
        raise DirectEmissionError(
            "Complete endereço, número, bairro, cidade, UF e código IBGE do cliente."
        )
    if not missing and len(address["codigoMunicipio"]) != 7:
        raise DirectEmissionError("Confira o código IBGE do município do cliente.")
    cep = _digits(getattr(cliente, "cep", None))
    if len(cep) == 8:
        address["cep"] = cep

    recipient = {
        "razaoSocial": (
            "NF-E EMITIDA EM AMBIENTE DE HOMOLOGACAO - SEM VALOR FISCAL"
            if environment == 2
            else _text(getattr(cliente, "razao_social", None)) or _text(cliente.nome)
        ),
        "indicadorIe": (
            "1" if _text(getattr(cliente, "inscricao_estadual", None)) else "9"
        ),
    }
    if not missing:
        recipient["endereco"] = address
    if len(document) == 14:
        recipient["cnpj"] = document
    else:
        recipient["cpf"] = document
    ie = _text(getattr(cliente, "inscricao_estadual", None))
    if ie:
        recipient["inscricaoEstadual"] = ie
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
    normalized_cst = str(cst)
    result = {"cst": normalized_cst}
    if rate is None and normalized_cst.isdigit() and 49 <= int(normalized_cst) <= 99:
        # A IntNFe espera a aliquota explicita inclusive nos grupos de saida
        # sem destaque, como o CST 49 usado pelo Simples Nacional.
        rate = 0
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


def _product_taxes(fiscal, origin, taxable):
    return {
        "icms": _tax(fiscal["cst_icms"], origin, fiscal.get("icms_aliquota"), taxable),
        "pis": _contribution(fiscal["pis_cst"], fiscal.get("pis_aliquota"), taxable),
        "cofins": _contribution(
            fiscal["cofins_cst"], fiscal.get("cofins_aliquota"), taxable
        ),
    }


def _delivery_freight(products, tax_contexts, freight):
    """Envia rateio manual documentado para manter frete e bases coerentes.

    A IntNFe aceita produtos[].frete numerico e conserva os valores manuais.
    Usamos o bruto fiscal de cada linha como peso, com maior resto em centavos.
    Nao dependemos de recálculo de bases/tributos explicitos pelo provedor.
    """
    if not freight:
        return
    weights = [_money(product["valorTotal"]) for product in products]
    if not any(weights):
        weights = [Decimal(str(product["quantidade"])) for product in products]
    portions = ratear_centavos(freight, weights)
    for product, (fiscal, origin, taxable), portion in zip(
        products, tax_contexts, portions
    ):
        product["frete"] = float(portion)
        product["impostos"] = _product_taxes(fiscal, origin, taxable + portion)


def _third_party_delivery(venda):
    courier = getattr(venda, "entregador", None)
    return courier is not None and (
        bool(getattr(courier, "is_terceirizado", False))
        or _ascii(getattr(courier, "tipo_vinculo_entrega", None)) == "terceirizado"
    )


def _lot_from_recorded_fifo(db, venda, item):
    """Recupera o lote fiscal de vendas antigas que não salvaram ``lote_id``.

    O vínculo só é inferido quando a movimentação FIFO aponta para exatamente
    um lote. Mais de um lote exige revisão porque os snapshots fiscais podem
    divergir e uma única linha da NF não deve escolher um deles arbitrariamente.
    """
    if (
        db is None
        or getattr(item, "lote_id", None)
        or getattr(item, "estoque_origem_tenant_id", None)
    ):
        return None

    rows = (
        db.query(EstoqueMovimentacao.lotes_consumidos)
        .filter(
            EstoqueMovimentacao.tenant_id == venda.tenant_id,
            EstoqueMovimentacao.produto_id == item.produto_id,
            EstoqueMovimentacao.referencia_id == venda.id,
            EstoqueMovimentacao.referencia_tipo == "venda",
            EstoqueMovimentacao.status != "cancelado",
            EstoqueMovimentacao.lotes_consumidos.isnot(None),
        )
        .all()
    )
    lot_ids = set()
    for row in rows:
        raw = row[0] if isinstance(row, tuple) else row.lotes_consumidos
        try:
            consumed = json.loads(raw) if isinstance(raw, str) else raw
        except (TypeError, ValueError):
            continue
        for lot in consumed or []:
            lot_id = lot.get("lote_id") if isinstance(lot, dict) else None
            if lot_id is not None:
                lot_ids.add(int(lot_id))

    if len(lot_ids) > 1:
        raise DirectEmissionError(
            f"Produto {item.produto.nome}: a venda consumiu mais de um lote. "
            "Revise os dados fiscais dos lotes antes de transmitir a nota."
        )
    if not lot_ids:
        return None
    return (
        db.query(ProdutoLote)
        .filter(
            ProdutoLote.id == next(iter(lot_ids)),
            ProdutoLote.tenant_id == venda.tenant_id,
        )
        .first()
    )


def build_payload(db, tenant, connection, venda, document_type):
    emitter, emitter_pending = local_profile(db, tenant.id)
    emitter_cnpj = _digits(getattr(tenant, "cnpj", None))
    if len(emitter_cnpj) == 14:
        emitter["cnpj"] = emitter_cnpj
    elif len(_digits(emitter.get("cnpj"))) != 14:
        emitter_pending.append("Informe um CNPJ válido nos dados da empresa.")
    if emitter_pending:
        raise DirectEmissionError(" ".join(emitter_pending))
    environment = 1 if connection.emission_environment == 1 else 2
    sale_total = _money(venda.total)
    nfce_delivery = document_type == "nfce" and bool(venda.tem_entrega)
    if nfce_delivery and _third_party_delivery(venda):
        raise DirectEmissionError(
            "Esta integração de NFC-e está habilitada para entrega própria. "
            "O entregador selecionado está cadastrado como terceirizado; "
            "confira o vínculo e a modalidade de transporte antes de emitir."
        )
    nfce_requires_recipient = document_type == "nfce" and (
        bool(getattr(venda, "tem_entrega", False)) or sale_total >= Decimal("10000")
    )
    cpf_avulso = _digits(getattr(venda, "nfe_consumidor_cpf", None))
    if document_type == "nfce" and not venda.cliente and cpf_avulso:
        if len(cpf_avulso) != 11:
            raise DirectEmissionError("O CPF informado para esta NFC-e é inválido.")
        recipient = {"cpf": cpf_avulso}
        if environment == 2:
            recipient["nome"] = (
                "NF-E EMITIDA EM AMBIENTE DE HOMOLOGACAO - SEM VALOR FISCAL"
            )
    else:
        recipient = _recipient(
            venda.cliente,
            environment,
            document_type,
            require_identity=nfce_requires_recipient,
            require_address=document_type == "nfe",
        )
    if nfce_delivery:
        try:
            delivery_address = resolver_endereco_entrega(venda)
        except DeliveryAddressError as exc:
            raise DirectEmissionError(
                str(exc),
                code="nfce_delivery_address_required",
                validation={
                    "success": True,
                    "pode_emitir": False,
                    "requer_autorizacao": False,
                    "correcoes": [],
                    "bloqueios": [{"campo": exc.field, "mensagem": str(exc)}],
                },
            ) from exc
        if delivery_address["uf"] != emitter["endereco"]["uf"]:
            raise DirectEmissionError(
                "A entrega em NFC-e deve ocorrer dentro do estado do emitente. "
                "Confira a UF do endereço selecionado para a entrega."
            )
        recipient["endereco"] = delivery_address
    destination_uf = (
        recipient.get("endereco", {}).get("uf") or emitter["endereco"]["uf"]
        if recipient and document_type == "nfe"
        else emitter["endereco"]["uf"]
    )
    # NFC-e representa operação interna, mesmo quando o consumidor foi identificado.
    interstate = document_type == "nfe" and (
        destination_uf != emitter["endereco"]["uf"]
    )

    products = []
    fiscal_pending = []
    product_total = Decimal("0")
    item_discount_total = Decimal("0")
    tax_contexts = []
    legacy_grosses = _legacy_aggregate_gross(venda)
    descontos_fiscais = (
        {
            id(item): parte["total"]
            for item, parte in zip(venda.itens or [], ratear_descontos_venda(venda))
        }
        if getattr(venda, "desconto_venda_valor", None) is not None
        else {}
    )
    for item_numero, item in enumerate(venda.itens or [], start=1):
        if _ascii(item.tipo) != "produto" or not item.produto:
            raise DirectEmissionError(
                "A emissão direta atual aceita somente itens de produto vinculados ao cadastro."
            )
        fiscal_item = item
        inferred_lot = _lot_from_recorded_fifo(db, venda, item)
        if inferred_lot is not None:
            fiscal_item = SimpleNamespace(produto=item.produto, lote=inferred_lot)
        fiscal = _resolver_fiscal_item_nfe(db, venda, fiscal_item)
        ncm = _digits(fiscal.get("ncm"))
        origin = _text(fiscal.get("origem_mercadoria"))
        destinatario_nao_contribuinte = bool(
            recipient and recipient.get("indicadorIe") == "9"
        )
        if interstate and destinatario_nao_contribuinte:
            cfop = _text(fiscal.get("cfop_interestadual_nao_contribuinte"))
        else:
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
            fiscal_pending.extend(
                {
                    "produto_id": item.produto.id,
                    "produto_nome": item.produto.nome,
                    "produto_tipo": getattr(item.produto, "tipo_produto", None),
                    "sku": _text(item.produto.codigo)
                    or _text(item.produto.codigo_barras)
                    or str(item.produto.id),
                    "campo": campo,
                    "mensagem": f"{label} nao informado. Preencha para continuar.",
                }
                for campo, label, value in (
                    ("ncm", "NCM", ncm if len(ncm) == 8 else None),
                    ("origem_mercadoria", "Origem", origin),
                    ("cfop", "CFOP", cfop if cfop and len(cfop) == 4 else None),
                    ("cst_icms", "CSOSN/CST de ICMS", fiscal.get("cst_icms")),
                    ("pis_cst", "CST de PIS", fiscal.get("pis_cst")),
                    ("cofins_cst", "CST de COFINS", fiscal.get("cofins_cst")),
                )
                if not value
            )
            continue
        cst_icms = str(fiscal.get("cst_icms") or "").strip()
        codigos_validos = (
            CSOSN_VALIDOS if emitter.get("crt") == "1" else CST_ICMS_VALIDOS
        )
        if cst_icms not in codigos_validos:
            tipo_codigo = "CSOSN" if emitter.get("crt") == "1" else "CST"
            mensagem = (
                f"Produto {item.produto.nome}: {tipo_codigo} {cst_icms} não é válido "
                "para o regime da empresa. Confira a classificação fiscal do produto."
            )
            raise DirectEmissionError(
                mensagem,
                validation={
                    "success": True,
                    "pode_emitir": False,
                    "requer_autorizacao": False,
                    "correcoes": [],
                    "bloqueios": [
                        {
                            "produto_id": item.produto.id,
                            "produto_nome": item.produto.nome,
                            "produto_tipo": getattr(item.produto, "tipo_produto", None),
                            "sku": _text(getattr(item.produto, "codigo", None))
                            or str(item.produto.id),
                            "campo": "cst_icms",
                            "valor_atual": cst_icms,
                            "valor_invalido": True,
                            "mensagem": mensagem,
                        }
                    ],
                },
            )
        if document_type == "nfce" and emitter.get("crt") == "1":
            pendencias_cfop_csosn = pendencias_cfop_csosn_nfce(
                fiscal,
                {
                    "produto_id": item.produto.id,
                    "produto_nome": item.produto.nome,
                    "produto_tipo": getattr(item.produto, "tipo_produto", None),
                    "sku": _text(getattr(item.produto, "codigo", None))
                    or str(item.produto.id),
                },
                emitter["endereco"]["uf"],
                item_numero,
            )
            if pendencias_cfop_csosn:
                raise DirectEmissionError(
                    f"Item {item_numero}: CFOP não permitido para o CSOSN informado.",
                    validation={
                        "success": True,
                        "pode_emitir": False,
                        "requer_autorizacao": False,
                        "correcoes": [],
                        "bloqueios": pendencias_cfop_csosn,
                    },
                )
        if (
            emitter.get("crt") == "1"
            and destinatario_nao_contribuinte
            and cst_icms not in {"102", "103", "300", "400", "500"}
        ):
            raise DirectEmissionError(
                f"Produto {item.produto.nome}: o CSOSN {cst_icms} não é aceito "
                "para consumidor não contribuinte. Revise a tributação antes de transmitir.",
                validation={
                    "success": True,
                    "pode_emitir": False,
                    "requer_autorizacao": False,
                    "correcoes": [],
                    "bloqueios": [
                        {
                            "produto_id": item.produto.id,
                            "produto_nome": item.produto.nome,
                            "produto_tipo": getattr(item.produto, "tipo_produto", None),
                            "sku": _text(getattr(item.produto, "codigo", None))
                            or _text(getattr(item.produto, "codigo_barras", None))
                            or str(item.produto.id),
                            "campo": "cst_icms",
                            "valor_atual": cst_icms,
                            "valor_invalido": True,
                            "mensagem": (
                                f"O CSOSN {cst_icms} nao e aceito para consumidor nao contribuinte. "
                                "Escolha a classificacao correta para esta operacao."
                            ),
                        }
                    ],
                },
            )
        quantity = Decimal(str(item.quantidade or 0))
        unit_price = Decimal(str(item.preco_unitario or 0))
        desconto_manual_item = _money(item.desconto_item)
        discount = descontos_fiscais.get(id(item), desconto_manual_item)
        calculated_gross = (quantity * unit_price).quantize(
            CENT, rounding=ROUND_HALF_UP
        )
        stored_subtotal = getattr(item, "subtotal", None)
        gross = (
            _money(stored_subtotal) + desconto_manual_item
            if stored_subtotal is not None
            else calculated_gross
        )
        gross = legacy_grosses.get(id(item), gross)
        if quantity <= 0 or unit_price < 0 or discount < 0 or discount > gross:
            raise DirectEmissionError(
                f"Produto {item.produto.nome}: confira quantidade, preço e desconto."
            )
        if abs(gross - calculated_gross) > CENT and not _quantity_rounding(
            venda, item, gross
        ):
            raise DirectEmissionError(
                f"Produto {item.produto.nome}: o subtotal salvo difere da quantidade e do preço."
            )
        fiscal_unit_price = unit_price
        if gross != calculated_gross:
            fiscal_unit_price = (gross / quantity).quantize(
                Decimal("0.0000000001"), rounding=ROUND_HALF_UP
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
            "valorUnitario": float(fiscal_unit_price),
            "valorTotal": float(gross),
            "impostos": _product_taxes(fiscal, origin, taxable),
        }
        cest = _digits(fiscal.get("cest"))
        if cest:
            product["cest"] = cest
        if discount:
            product["desconto"] = float(discount)
        products.append(product)
        tax_contexts.append((fiscal, origin, taxable))
        product_total += gross
        item_discount_total += discount

    if fiscal_pending:
        raise DirectEmissionError(
            "Existem dados fiscais de produtos para completar antes da emissao.",
            validation={
                "success": True,
                "pode_emitir": False,
                "requer_autorizacao": False,
                "correcoes": [],
                "bloqueios": fiscal_pending,
            },
        )

    if not products:
        raise DirectEmissionError("A venda não possui produtos para emitir a nota.")

    sale_discount = _money(venda.desconto_valor)
    total_discount = item_discount_total if item_discount_total > 0 else sale_discount
    if sale_discount and item_discount_total and sale_discount != item_discount_total:
        raise DirectEmissionError(
            "O desconto da venda difere da soma dos descontos dos itens."
        )
    freight = _money(venda.taxa_entrega if venda.tem_entrega else 0)
    if nfce_delivery:
        if freight < 0:
            raise DirectEmissionError("A taxa de entrega não pode ser negativa.")
        _delivery_freight(products, tax_contexts, freight)
    calculated_total = product_total - total_discount + freight
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
    credit_installments = _crediario_installments(venda)

    channel = re.sub(r"[^a-z0-9]+", "_", _ascii(venda.canal)).strip("_")
    if channel in MARKETPLACE_CHANNELS:
        raise DirectEmissionError(
            "A emissão direta está disponível apenas para vendas do PDV do ERP. "
            "Pedidos de marketplace não podem ser emitidos por este fluxo."
        )

    presence = "1" if channel == "loja_fisica" else "9"
    if nfce_delivery:
        presence = "4"
    payload = {
        "serie": (
            connection.nfe_series if document_type == "nfe" else connection.nfce_series
        ),
        "ambienteCodigo": environment,
        "naturezaOperacao": "Venda de mercadoria",
        "emitente": emitter,
        "produtos": products,
        "pagamentos": payments,
        "informacoesAdicionais": _additional_information(venda, credit_installments),
        "indicadorPresenca": presence,
    }
    if document_type == "nfe":
        payload["frete"] = {"modalidade": "9", "valor": float(freight)}
        payload["documentosReferenciados"] = []
    elif nfce_delivery:
        payload["frete"] = {"modalidade": "3", "valor": float(freight)}
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
                "frete": item.get("frete", 0),
                "ncm": item["ncm"],
                "cfop": item["cfop"],
                "icms": item["impostos"]["icms"]["cst"],
                "pis": item["impostos"]["pis"]["cst"],
                "cofins": item["impostos"]["cofins"]["cst"],
            }
            for item in payload["produtos"]
        ],
        "pagamentos": payload["pagamentos"],
        "vencimentos_crediario": [
            {
                "numero": item["numero"],
                "total_parcelas": item["total_parcelas"],
                "data_vencimento": item["data_vencimento"].isoformat(),
                "valor": float(_money(item["valor"])),
            }
            for item in _crediario_installments(venda)
        ],
        "informacoes_adicionais": payload["informacoesAdicionais"],
        "frete": payload.get("frete", {}).get("valor", 0),
        "indicador_presenca": payload["indicadorPresenca"],
        "modalidade_frete": payload.get("frete", {}).get("modalidade"),
        "total": float(_money(venda.total)),
    }


def emission_fingerprint(db, tenant, venda, document_type):
    """Identifica os dados que seriam transmitidos sem criar um documento."""
    connection = _connection(db, tenant.id)
    payload = build_payload(db, tenant, connection, venda, document_type)
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def local_document_details(db, tenant, venda):
    """Monta os detalhes da nota a partir da venda salva no CorePet.

    A consulta não depende de XML/DANFE nem de uma nova chamada à IntNFe. Isso
    permite explicar uma rejeição usando os mesmos produtos e dados fiscais que
    permanecem vinculados à venda.
    """
    cliente = venda.cliente
    nfce_delivery = bool(venda.tem_entrega) and (
        venda.nfe_tipo == "nfce" or str(getattr(venda, "nfe_modelo", "")) == "65"
    )
    own_delivery = nfce_delivery and not _third_party_delivery(venda)
    delivery_address = {}
    if nfce_delivery:
        try:
            delivery_address = resolver_endereco_entrega(venda)
        except DeliveryAddressError:
            # A consulta de uma tentativa rejeitada precisa continuar exibindo
            # o texto salvo, inclusive quando o endereco ainda exige revisao.
            pass
    emitter_uf = (_text(getattr(tenant, "uf", None)) or "").upper()
    destination_uf = (
        (_text(getattr(cliente, "estado", None)) or emitter_uf).upper()
        if cliente
        else emitter_uf
    )
    interstate = venda.nfe_tipo == "nfe" and bool(
        emitter_uf and destination_uf and emitter_uf != destination_uf
    )
    recipient_non_taxpayer = cliente is not None and not _text(
        getattr(cliente, "inscricao_estadual", None)
    )

    items = []
    product_total = Decimal("0")
    item_discount_total = Decimal("0")
    legacy_grosses = _legacy_aggregate_gross(venda)
    descontos_fiscais = (
        {
            id(item): parte["total"]
            for item, parte in zip(venda.itens or [], ratear_descontos_venda(venda))
        }
        if getattr(venda, "desconto_venda_valor", None) is not None
        else {}
    )
    for item_numero, sale_item in enumerate(venda.itens or [], start=1):
        product = getattr(sale_item, "produto", None)
        quantity = Decimal(str(getattr(sale_item, "quantidade", 0) or 0))
        unit_price = Decimal(str(getattr(sale_item, "preco_unitario", 0) or 0))
        desconto_manual_item = _money(getattr(sale_item, "desconto_item", 0))
        discount = descontos_fiscais.get(id(sale_item), desconto_manual_item)
        subtotal = _money(getattr(sale_item, "subtotal", 0))
        gross = subtotal + desconto_manual_item
        if gross == 0 and quantity:
            gross = (quantity * unit_price).quantize(CENT, rounding=ROUND_HALF_UP)
        gross = legacy_grosses.get(id(sale_item), gross)
        calculated_gross = _money(quantity * unit_price)
        fiscal_unit_price = unit_price
        if (
            quantity > 0
            and gross != calculated_gross
            and (
                abs(gross - calculated_gross) <= CENT
                or _quantity_rounding(venda, sale_item, gross)
            )
        ):
            fiscal_unit_price = (gross / quantity).quantize(
                Decimal("0.0000000001"), rounding=ROUND_HALF_UP
            )

        fiscal = {}
        lot = getattr(sale_item, "lote", None)
        if product and _ascii(getattr(sale_item, "tipo", None)) == "produto":
            try:
                inferred_lot = _lot_from_recorded_fifo(db, venda, sale_item)
                if inferred_lot is not None:
                    lot = inferred_lot
                fiscal_item = SimpleNamespace(produto=product, lote=lot)
                fiscal = _resolver_fiscal_item_nfe(db, venda, fiscal_item) or {}
            except Exception:
                # O item precisa continuar visível mesmo se seu cadastro fiscal
                # tiver sido alterado ou estiver incompleto depois da emissão.
                fiscal = {}

        if interstate and recipient_non_taxpayer:
            cfop = fiscal.get("cfop_interestadual_nao_contribuinte")
        else:
            cfop = (
                fiscal.get("cfop_interestadual")
                if interstate
                else fiscal.get("cfop_interno")
            )
        items.append(
            {
                "item_id": getattr(sale_item, "id", None),
                "item_numero": item_numero,
                "lote_id": getattr(lot, "id", None),
                "produto_id": getattr(sale_item, "produto_id", None),
                "codigo": (
                    _text(getattr(product, "codigo", None))
                    or _text(getattr(product, "codigo_barras", None))
                    or (str(getattr(product, "id", "")) if product else None)
                ),
                "descricao": (
                    _text(getattr(product, "nome", None))
                    or _text(getattr(sale_item, "servico_descricao", None))
                ),
                "unidade": _text(getattr(product, "unidade", None)) or "UN",
                "quantidade": _number(quantity),
                "valor_unitario": float(fiscal_unit_price),
                "valor_total": float(gross),
                "desconto": float(discount),
                "ncm": _digits(fiscal.get("ncm")) or None,
                "cest": _digits(fiscal.get("cest")) or None,
                "origem_mercadoria": _text(fiscal.get("origem_mercadoria")),
                "cfop": _text(cfop),
                "icms": _text(fiscal.get("cst_icms")),
                "pis": _text(fiscal.get("pis_cst")),
                "cofins": _text(fiscal.get("cofins_cst")),
            }
        )
        product_total += gross
        item_discount_total += discount

    sale_discount = _money(getattr(venda, "desconto_valor", 0))
    total_discount = item_discount_total if item_discount_total else sale_discount
    freight = _money(venda.taxa_entrega if venda.tem_entrega else 0)
    issue_at = getattr(venda, "nfe_data_emissao", None)
    channel = re.sub(r"[^a-z0-9]+", "_", _ascii(venda.canal)).strip("_")

    customer_document = None
    if cliente:
        customer_document = _digits(
            getattr(cliente, "cnpj", None) or getattr(cliente, "cpf", None)
        )
    elif venda.nfe_tipo == "nfce":
        customer_document = _digits(getattr(venda, "nfe_consumidor_cpf", None)) or None

    credit_installments = _crediario_installments(venda)
    payment_rows = []
    credit_rows_added = False
    for payment in venda.pagamentos or []:
        if _is_crediario_payment(getattr(payment, "forma_pagamento", None)):
            if credit_installments and not credit_rows_added:
                payment_rows.extend(
                    {
                        "dias": None,
                        "data": item["data_vencimento"].isoformat(),
                        "valor": float(_money(item["valor"])),
                        "forma": payment.forma_pagamento,
                        "observacao": (
                            f"Parcela {item['numero']}/{item['total_parcelas']}"
                        ),
                    }
                    for item in credit_installments
                )
                credit_rows_added = True
                continue
        payment_rows.append(
            {
                "dias": getattr(payment, "prazo_recebimento_dias", None),
                "data": (
                    payment.data_recebimento_prevista.isoformat()
                    if getattr(payment, "data_recebimento_prevista", None)
                    else None
                ),
                "valor": float(_money(payment.valor)),
                "forma": payment.forma_pagamento,
                "observacao": getattr(payment, "numero_transacao", None),
            }
        )

    presence_label = (
        "1 - Operação presencial" if channel == "loja_fisica" else "9 - Outros"
    )
    transport_type = "Entrega local" if venda.tem_entrega else "Sem transporte"
    freight_account = "9 - Sem ocorrência de transporte"
    if nfce_delivery:
        presence_label = "4 - NFC-e com entrega a domicílio"
    if own_delivery:
        transport_type = "Entrega própria"
        freight_account = "3 - Transporte próprio por conta do remetente"
    details = {
        "id": venda.id,
        "numero": venda.nfe_numero,
        "serie": venda.nfe_serie,
        "modelo": int(venda.nfe_modelo or (55 if venda.nfe_tipo == "nfe" else 65)),
        "tipo": venda.nfe_tipo or "nfe",
        "chave": venda.nfe_chave,
        "status": venda.nfe_status,
        "venda_status": getattr(venda, "status", None),
        **campos_cancelamento_com_aliases(venda),
        "provedor": "intnfe",
        "codigo_erro": venda.nfe_codigo_erro,
        "motivo_rejeicao": venda.nfe_motivo_rejeicao,
        "protocolo": venda.nfe_protocolo,
        "ambiente_codigo": venda.nfe_ambiente,
        "data_emissao": issue_at.isoformat() if issue_at else None,
        "hora_emissao": issue_at.strftime("%H:%M:%S") if issue_at else None,
        "natureza_operacao": "Venda de mercadoria",
        "finalidade": "1 - NF-e normal",
        "indicador_presenca": presence_label,
        "cliente": (
            {
                "id": getattr(cliente, "id", None),
                "codigo": getattr(cliente, "codigo", None),
                "nome": getattr(cliente, "nome", None),
                "tipo_pessoa": getattr(cliente, "tipo_pessoa", None),
                "cpf_cnpj": customer_document,
                "vendedor": getattr(getattr(venda, "vendedor", None), "nome", None),
                "consumidor_final": True,
                "telefone": (
                    getattr(cliente, "celular", None)
                    or getattr(cliente, "telefone", None)
                    if cliente
                    else None
                ),
                "email": getattr(cliente, "email", None),
                "cep": getattr(cliente, "cep", None),
                "uf": getattr(cliente, "estado", None),
                "municipio": getattr(cliente, "cidade", None),
                "bairro": getattr(cliente, "bairro", None),
                "endereco": getattr(cliente, "endereco", None),
                "numero": getattr(cliente, "numero", None),
                "complemento": getattr(cliente, "complemento", None),
                "codigo_municipio": getattr(cliente, "codigo_municipio", None),
                "inscricao_estadual": getattr(cliente, "inscricao_estadual", None),
            }
            if cliente
            else (
                {"id": None, "nome": None, "cpf_cnpj": customer_document}
                if customer_document
                else {}
            )
        ),
        "canal": venda.canal,
        "canal_label": {
            "loja_fisica": "PDV / Loja física",
            "mercado_livre": "Mercado Livre",
            "shopee": "Shopee",
            "amazon": "Amazon",
            "tiktok_shop": "TikTok Shop",
        }.get(channel, venda.canal),
        "itens": items,
        "totais": {
            "valor_produtos": float(product_total),
            "valor_frete": float(freight),
            "valor_seguro": 0,
            "outras_despesas": 0,
            "valor_desconto": float(total_discount),
            "valor_total": float(_money(venda.total)),
        },
        "transporte": {"tipo": transport_type, "frete_por_conta": freight_account},
        "endereco_entrega": {
            "nome": getattr(cliente, "nome", None) if venda.tem_entrega else None,
            "endereco": venda.endereco_entrega if venda.tem_entrega else None,
        },
        "pagamento": {
            "condicao": ", ".join(
                dict.fromkeys(
                    str(payment.forma_pagamento)
                    for payment in (venda.pagamentos or [])
                    if getattr(payment, "forma_pagamento", None)
                )
            )
            or None,
            "parcelas": payment_rows,
        },
        "intermediador": {},
        "informacoes_adicionais": {
            "numero_pedido_loja": venda.numero_venda,
            "origem_canal_venda": venda.canal,
            "informacoes_complementares": _additional_information(
                venda, credit_installments
            ),
        },
        "pessoas_autorizadas_xml": [],
    }
    if delivery_address:
        selected_fields = {
            "endereco": delivery_address["logradouro"],
            "numero": delivery_address["numero"],
            "complemento": delivery_address.get("complemento"),
            "bairro": delivery_address["bairro"],
            "municipio": delivery_address["municipio"],
            "uf": delivery_address["uf"],
            "cep": delivery_address["cep"],
            "codigo_municipio": delivery_address["codigoMunicipio"],
        }
        details["cliente"].update(selected_fields)
        details["endereco_entrega"].update(selected_fields)
    details["diagnostico_rejeicao"] = rejection_diagnostics(venda, db=db, items=items)
    return details


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


def _provider_validation(venda, messages):
    if not messages:
        return None

    blocks = []
    for message in messages:
        for block in message_corrections(venda, message):
            blocks.append({**block, "origem": "intnfe", "historico": False})
    return enrich_validation_items(
        venda,
        {
            "success": True,
            "pode_emitir": False,
            "requer_autorizacao": False,
            "correcoes": [],
            "bloqueios": blocks,
        },
    )


def issue(db, tenant, venda, document_type, api):
    connection = _connection(db, tenant.id)
    db.refresh(venda, with_for_update=True)
    if venda.nfe_correlation_id:
        return reconcile(db, venda, api, connection=connection)
    if venda.status == "cancelada":
        raise DirectEmissionError(
            "Uma venda cancelada não pode emitir uma nova nota fiscal.", status=409
        )
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
        validation = _provider_validation(venda, exc.validation_errors)
        venda.nfe_status = "inconclusiva" if exc.uncertain else "rejeitada"
        venda.nfe_codigo_erro = exc.code[:20] if exc.code else None
        if not exc.uncertain and exc.status:
            venda.nfe_motivo_rejeicao = (
                " | ".join(exc.validation_errors)
                if exc.validation_errors
                else f"IntNFe HTTP {exc.status}"
            )
        if not exc.uncertain:
            venda.nfe_idempotency_key = None
            venda.nfe_payload_hash = None
            venda.nfe_data_emissao = None
        db.commit()
        raise DirectEmissionError(
            (
                "O envio ficou sem confirmação; não crie outra nota para esta venda."
                if exc.uncertain
                else "A IntNFe recusou o envio antes do processamento."
            ),
            status=(
                503
                if exc.uncertain
                else (422 if exc.status and 400 <= exc.status < 500 else 503)
            ),
            code=exc.code,
            correlation=exc.correlation,
            validation=validation,
        ) from None
    venda.nfe_correlation_id = result["correlationId"]
    venda.nfe_status = "processando"
    with db.no_autoflush:
        db.refresh(venda, attribute_names=["status"], with_for_update=True)
        if venda.status != "cancelada":
            venda.status = "pago_nf"
    db.commit()
    return reconcile(db, venda, api, connection=connection, token=token)


def reconcile(
    db,
    venda,
    api,
    *,
    connection=None,
    token=None,
    commit=True,
    cancel_result=None,
    cancel_result_tentativa=None,
):
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
    tentativa_observada = data_evento(cancel_result_tentativa) or data_evento(
        getattr(venda, "nfe_cancelamento_solicitado_em", None)
    )
    eventos = None
    xml_autorizado = None
    if status_code in {AUTHORIZED_STATUS, 5} or getattr(
        venda, "nfe_cancelamento_status", None
    ):
        try:
            eventos = api.document_events(
                token, venda.nfe_tipo, venda.nfe_correlation_id
            )
            if not isinstance(eventos, list):
                raise IntNFeError("RespostaInvalida")
        except IntNFeError:
            # A situação autorizada permanece válida. A ausência de consulta
            # não transforma uma tentativa em cancelamento confirmado.
            eventos = None
    if status_code == AUTHORIZED_STATUS and not venda.nfe_xml:
        try:
            xml_autorizado = api.document_xml(
                token, venda.nfe_tipo, venda.nfe_correlation_id
            ).decode("utf-8-sig")
        except (IntNFeError, UnicodeDecodeError):
            pass
    # Nenhum lock é mantido enquanto aguardamos o emissor. A operação comercial
    # ou uma tentativa mais nova pode ter terminado durante essas consultas.
    with db.no_autoflush:
        db.refresh(
            venda,
            attribute_names=[
                "status",
                "nfe_status",
                "nfe_cancelamento_status",
                "nfe_cancelamento_codigo",
                "nfe_cancelamento_motivo",
                "nfe_cancelamento_solicitado_em",
            ],
            with_for_update=True,
        )
    antes = str(venda.nfe_status or "").lower()
    if antes in {"cancelada", "cancelado"}:
        status_code = 5
    elif antes == "autorizada" and status_code in {0, 1, 2, 7}:
        status_code = AUTHORIZED_STATUS
    atual = data_evento(getattr(venda, "nfe_cancelamento_solicitado_em", None))
    if isinstance(cancel_result, dict) and atual == tentativa_observada:
        aplicar_resultado_cancelamento(
            venda,
            resultado_cancelamento(cancel_result)
            or {
                "status": "solicitado",
                "codigo": None,
                "motivo": None,
            },
        )
    if eventos is not None:
        aplicar_resultado_cancelamento(
            venda, ultimo_cancelamento(eventos, solicitado_em=atual)
        )
    if getattr(venda, "nfe_cancelamento_status", None) == "confirmado":
        status_code = 5
    venda.nfe_status = STATUS_NAMES.get(status_code, "processando")
    if status_code == 5:
        venda.nfe_cancelamento_status = "confirmado"
    sincronizar_venda_apos_cancelamento_fiscal(db, venda)
    venda.nfe_numero = result.get("numero") or venda.nfe_numero
    if result.get("serie") is not None:
        venda.nfe_serie = int(result["serie"])
    venda.nfe_chave = result.get("chaveAcesso") or venda.nfe_chave
    venda.nfe_protocolo = result.get("protocolo") or venda.nfe_protocolo
    error_code = _text(result.get("codigoErro"))
    venda.nfe_codigo_erro = error_code[:20] if error_code else None
    venda.nfe_motivo_rejeicao = _text(result.get("motivoRejeicao"))
    if status_code == AUTHORIZED_STATUS:
        autorizada_em = data_evento(result.get("autorizadoEm"))
        if autorizada_em is not None:
            venda.nfe_data_autorizacao = as_brasilia_naive(autorizada_em)
        elif not getattr(venda, "nfe_data_autorizacao", None):
            venda.nfe_data_autorizacao = as_brasilia_naive(datetime.now(timezone.utc))
        _remember_sequence_start(db, venda)
        if not venda.nfe_xml:
            venda.nfe_xml = xml_autorizado
    if status_code in {AUTHORIZED_STATUS, 5}:
        tentar_enfileirar_documento(db, venda.tenant_id, "intnfe", venda.id)
    if commit:
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
        **campos_cancelamento(venda),
    }


def _remember_sequence_start(db, venda):
    """Guarda a primeira numeração realmente emitida pelo CorePet."""
    if not all(
        (
            venda.nfe_numero,
            venda.nfe_serie is not None,
            venda.nfe_ambiente in {1, 2},
            str(venda.nfe_modelo) in {"55", "65"},
        )
    ):
        return
    model = int(venda.nfe_modelo)
    series = str(int(venda.nfe_serie))
    saved = (
        db.query(IntNFeEmissionSequence)
        .filter(
            IntNFeEmissionSequence.tenant_id == venda.tenant_id,
            IntNFeEmissionSequence.ambiente_codigo == venda.nfe_ambiente,
            IntNFeEmissionSequence.modelo == model,
        )
        .one_or_none()
    )
    if saved is None:
        db.add(
            IntNFeEmissionSequence(
                tenant_id=venda.tenant_id,
                ambiente_codigo=venda.nfe_ambiente,
                modelo=model,
                serie=series,
                numero_inicial=venda.nfe_numero,
            )
        )


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


def _auditar_cancelamento(db, venda, user_id, etapa):
    log_action(
        db,
        user_id=user_id,
        tenant_id=venda.tenant_id,
        action=f"nfe_cancelamento_{etapa}",
        entity_type="vendas",
        entity_id=venda.id,
        new_value={"nfe_status": venda.nfe_status, **campos_cancelamento(venda)},
        details=f"Cancelamento fiscal da nota {venda.nfe_numero}: {etapa}",
        commit=False,
    )


def cancel(db, venda, api, justification, *, user_id=None):
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
    with db.no_autoflush:
        db.refresh(
            venda,
            attribute_names=[
                "status",
                "nfe_status",
                "nfe_cancelamento_status",
                "nfe_cancelamento_codigo",
                "nfe_cancelamento_motivo",
                "nfe_cancelamento_solicitado_em",
            ],
            with_for_update=True,
        )
    if venda.nfe_status != "autorizada":
        raise DirectEmissionError(
            "A situação fiscal mudou durante a consulta. Atualize a nota antes de cancelar.",
            status=409,
        )
    iniciada = data_evento(getattr(venda, "nfe_cancelamento_solicitado_em", None))
    estado = getattr(venda, "nfe_cancelamento_status", None)
    if estado == "solicitado" or (
        estado == "pendente"
        and iniciada is not None
        and datetime.now(timezone.utc) - iniciada < timedelta(minutes=2)
    ):
        raise DirectEmissionError(
            "Já existe um pedido de cancelamento em andamento. Atualize a situação antes de tentar novamente.",
            status=409,
            cancelamento=campos_cancelamento(venda),
        )
    venda.nfe_cancelamento_status = "pendente"
    venda.nfe_cancelamento_codigo = None
    venda.nfe_cancelamento_motivo = None
    tentativa = datetime.now(timezone.utc)
    venda.nfe_cancelamento_solicitado_em = tentativa
    _auditar_cancelamento(db, venda, user_id, "tentativa")
    db.commit()
    try:
        resposta = api.cancel_document(
            token, venda.nfe_tipo, venda.nfe_correlation_id, justification.strip()
        )
    except IntNFeError as exc:
        with db.no_autoflush:
            db.refresh(
                venda,
                attribute_names=[
                    "status",
                    "nfe_status",
                    "nfe_cancelamento_status",
                    "nfe_cancelamento_codigo",
                    "nfe_cancelamento_motivo",
                    "nfe_cancelamento_solicitado_em",
                ],
                with_for_update=True,
            )
        if (
            venda.nfe_cancelamento_status == "confirmado"
            or venda.nfe_status == "cancelada"
        ):
            venda.nfe_status = "cancelada"
            sincronizar_venda_apos_cancelamento_fiscal(db, venda)
            _auditar_cancelamento(db, venda, user_id, "resultado")
            db.commit()
            return {
                "success": True,
                "processando": False,
                "situacao": "cancelada",
                **campos_cancelamento(venda),
            }
        mensagem = exc.provider_message or (
            "Não foi possível confirmar o recebimento do cancelamento pelo emissor. Consulte a situação antes de tentar novamente."
            if exc.uncertain
            else "O emissor recusou a solicitação de cancelamento."
        )
        if data_evento(venda.nfe_cancelamento_solicitado_em) == tentativa:
            venda.nfe_cancelamento_status = "pendente" if exc.uncertain else "recusado"
            venda.nfe_cancelamento_codigo = exc.code
            venda.nfe_cancelamento_motivo = mensagem
        _auditar_cancelamento(db, venda, user_id, "resultado")
        db.commit()
        raise DirectEmissionError(
            mensagem,
            status=503 if exc.uncertain else 422,
            code=exc.code,
            correlation=exc.correlation,
            cancelamento=campos_cancelamento(venda),
        ) from None
    try:
        result = reconcile(
            db,
            venda,
            api,
            connection=connection,
            token=token,
            commit=False,
            cancel_result=resposta,
            cancel_result_tentativa=tentativa,
        )
    except DirectEmissionError as exc:
        with db.no_autoflush:
            db.refresh(
                venda,
                attribute_names=[
                    "status",
                    "nfe_status",
                    "nfe_cancelamento_status",
                    "nfe_cancelamento_codigo",
                    "nfe_cancelamento_motivo",
                    "nfe_cancelamento_solicitado_em",
                ],
                with_for_update=True,
            )
        if (
            data_evento(venda.nfe_cancelamento_solicitado_em) == tentativa
            and venda.nfe_cancelamento_status != "confirmado"
        ):
            aplicar_resultado_cancelamento(
                venda,
                resultado_cancelamento(resposta)
                or {
                    "status": "solicitado",
                    "codigo": None,
                    "motivo": None,
                },
            )
        if venda.nfe_cancelamento_status == "confirmado":
            venda.nfe_status = "cancelada"
            sincronizar_venda_apos_cancelamento_fiscal(db, venda)
        _auditar_cancelamento(db, venda, user_id, "resultado")
        db.commit()
        if venda.nfe_cancelamento_status in {"confirmado", "recusado"}:
            return {
                "success": venda.nfe_cancelamento_status == "confirmado",
                "processando": False,
                "situacao": venda.nfe_status,
                **campos_cancelamento(venda),
            }
        raise DirectEmissionError(
            "A solicitação foi enviada, mas não foi possível consultar o resultado fiscal. Atualize a situação antes de repetir.",
            status=503,
            code=exc.code,
            correlation=exc.correlation,
            cancelamento=campos_cancelamento(venda),
        ) from None
    _auditar_cancelamento(db, venda, user_id, "resultado")
    db.commit()
    result["success"] = result["cancelamento_status"] == "confirmado"
    result["processando"] = result["cancelamento_status"] in {"pendente", "solicitado"}
    return result
