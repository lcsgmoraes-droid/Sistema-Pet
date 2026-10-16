"""Resolve o endereco de entrega escolhido no PDV sem interpretar texto livre."""

import json
import re
import unicodedata


class DeliveryAddressError(ValueError):
    def __init__(self, message, *, field="entrega.endereco"):
        super().__init__(message)
        self.field = field


_UFS = {
    "AC",
    "AL",
    "AP",
    "AM",
    "BA",
    "CE",
    "DF",
    "ES",
    "GO",
    "MA",
    "MT",
    "MS",
    "MG",
    "PA",
    "PB",
    "PR",
    "PE",
    "PI",
    "RJ",
    "RN",
    "RS",
    "RO",
    "RR",
    "SC",
    "SP",
    "SE",
    "TO",
}
_FIELDS = {
    "logradouro": ("endereco", "logradouro"),
    "numero": ("numero",),
    "complemento": ("complemento",),
    "bairro": ("bairro",),
    "municipio": ("cidade", "municipio"),
    "codigoMunicipio": ("codigo_municipio", "codigoMunicipio"),
    "uf": ("estado", "uf"),
    "cep": ("cep",),
}


def _value(source, name):
    value = (
        source.get(name) if isinstance(source, dict) else getattr(source, name, None)
    )
    return str(value).strip() if value is not None else ""


def _normalized(value):
    value = unicodedata.normalize("NFKD", str(value or "").casefold())
    return " ".join("".join(c for c in value if not unicodedata.combining(c)).split())


def _address(source):
    address = {
        field: next(
            (_value(source, name) for name in names if _value(source, name)), ""
        )
        for field, names in _FIELDS.items()
    }
    address["uf"] = address["uf"].upper()
    return address


def _pdv_labels(address):
    # O principal omite a virgula do numero ausente; os adicionais a mantem.
    # Ambos mantem o complemento: nao igualar apartamento/casa diferentes.
    street = address["logradouro"]
    number = address["numero"]
    complement = f" - {address['complemento']}" if address["complemento"] else ""
    locality = f", {address['bairro']}, {address['municipio']}/{address['uf']}"
    return {
        _normalized(f"{street}{', ' + number if number else ''}{complement}{locality}"),
        _normalized(f"{street}, {number}{complement}{locality}"),
    }


def _additional_addresses(customer):
    addresses = getattr(customer, "enderecos_adicionais", None)
    if isinstance(addresses, str):
        try:
            addresses = json.loads(addresses)
        except (ValueError, TypeError):
            return []
    return (
        [address for address in addresses if isinstance(address, dict)]
        if isinstance(addresses, list)
        else []
    )


def _validated(address):
    labels = {
        "logradouro": "logradouro",
        "numero": "numero (use S/N somente se esse for o dado informado)",
        "bairro": "bairro",
        "municipio": "cidade",
        "codigoMunicipio": "codigo IBGE do municipio",
        "uf": "UF",
        "cep": "CEP",
    }
    for field, label in labels.items():
        if not address[field]:
            raise DeliveryAddressError(
                f"Preencha {label} no endereco de entrega selecionado.",
                field=f"entrega.endereco.{field}",
            )
    if address["uf"] not in _UFS:
        raise DeliveryAddressError(
            "Confira a UF de duas letras do endereco de entrega selecionado.",
            field="entrega.endereco.uf",
        )
    if not re.fullmatch(r"\d{7}", address["codigoMunicipio"], flags=re.ASCII):
        raise DeliveryAddressError(
            "Confira o codigo IBGE de sete digitos do endereco de entrega selecionado.",
            field="entrega.endereco.codigoMunicipio",
        )
    cep = re.sub(r"[\s.-]", "", address["cep"])
    if not re.fullmatch(r"\d{8}", cep, flags=re.ASCII):
        raise DeliveryAddressError(
            "Confira o CEP de oito digitos do endereco de entrega selecionado.",
            field="entrega.endereco.cep",
        )
    result = {field: value for field, value in address.items() if value}
    result["cep"] = cep
    return result


def resolver_endereco_entrega(venda):
    """Retorna consumidor.endereco para o cadastro unico escolhido na venda.

    A venda guarda apenas a representacao textual selecionada no PDV. O texto
    precisa corresponder ao principal ou a um adicional estruturado do cliente.
    CEP e IBGE pertencem ao candidato, sem heranca de outro endereco. Este
    contrato de entrega NFC-e exige CEP; nao altera o contrato legado de NF-e.
    """
    selected = _normalized(getattr(venda, "endereco_entrega", None))
    if not selected:
        raise DeliveryAddressError(
            "Selecione o endereco de entrega desta venda antes de emitir."
        )
    customer = getattr(venda, "cliente", None)
    if customer is None:
        raise DeliveryAddressError(
            "Vincule um cliente com endereco de entrega estruturado a esta venda."
        )

    matches = {}
    for source in [customer, *_additional_addresses(customer)]:
        address = _address(source)
        canonical_match = selected in _pdv_labels(address)
        complete_label = _normalized(_value(source, "endereco_completo"))
        if not canonical_match and selected != complete_label:
            continue
        identity = tuple(
            re.sub(r"[\s.-]", "", address[field])
            if field == "cep"
            else _normalized(address[field])
            for field in _FIELDS
        )
        previous = matches.get(identity)
        matches[identity] = (address, canonical_match or bool(previous and previous[1]))

    if not matches:
        raise DeliveryAddressError(
            "O endereco escolhido na venda nao corresponde a um endereco estruturado do cliente. Revise o cadastro e selecione novamente o endereco de entrega."
        )
    if len(matches) != 1:
        raise DeliveryAddressError(
            "O endereco escolhido corresponde a cadastros com dados diferentes. Confira qual endereco de entrega deve ser usado nesta venda."
        )
    address, canonical_match = next(iter(matches.values()))
    validated = _validated(address)
    if not canonical_match:
        raise DeliveryAddressError(
            "O texto do endereco de entrega diverge dos dados estruturados desse cadastro. Revise o endereco e selecione novamente antes de emitir."
        )
    return validated
