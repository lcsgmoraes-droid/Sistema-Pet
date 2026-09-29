"""Referências e cuidados fiscais por UF.

As alíquotas abaixo são referências gerais para iniciar o cadastro da empresa.
Elas não substituem a tributação por NCM/CEST, origem e operação, que continua
sendo definida no cadastro fiscal de cada produto.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal


@dataclass(frozen=True)
class StateFiscalProfile:
    uf: str
    nome: str
    icms_interno_referencia: Decimal
    fcp_referencia: Decimal
    exige_cbenef_quando_aplicavel: bool
    requisitos_producao: tuple[str, ...]
    alertas: tuple[str, ...]


STATE_FISCAL_PROFILES = {
    "SP": StateFiscalProfile(
        uf="SP",
        nome="São Paulo",
        icms_interno_referencia=Decimal("18.00"),
        fcp_referencia=Decimal("0.00"),
        exige_cbenef_quando_aplicavel=True,
        requisitos_producao=(
            "IE ativa e credenciamento na SEFAZ-SP",
            "CSC por ambiente para NFC-e",
            "Série e numeração conferidas",
        ),
        alertas=("Validar benefícios fiscais e ICMS-ST por produto.",),
    ),
    "PR": StateFiscalProfile(
        uf="PR",
        nome="Paraná",
        icms_interno_referencia=Decimal("19.50"),
        fcp_referencia=Decimal("0.00"),
        exige_cbenef_quando_aplicavel=True,
        requisitos_producao=(
            "IE ativa na Receita/PR",
            "Pedido de Uso/UPD liberado para produção",
            "CSC por ambiente para NFC-e",
            "Série e numeração conferidas",
        ),
        alertas=(
            "Informar cBenef quando a operação usar benefício fiscal.",
            "Validar ICMS-ST por NCM/CEST; não usar 19,5% automaticamente em todos os produtos.",
        ),
    ),
    "RJ": StateFiscalProfile(
        uf="RJ",
        nome="Rio de Janeiro",
        icms_interno_referencia=Decimal("20.00"),
        fcp_referencia=Decimal("2.00"),
        exige_cbenef_quando_aplicavel=True,
        requisitos_producao=(
            "IE habilitada e credenciamento na SEFAZ-RJ",
            "CSC por ambiente para NFC-e",
            "Série e numeração conferidas",
        ),
        alertas=(
            "Configurar FCP somente nos produtos e operações em que ele incide.",
            "Informar cBenef e desoneração quando houver benefício fiscal.",
        ),
    ),
}


def normalize_uf(value: str | None) -> str:
    return str(value or "").strip().upper()[:2]


def state_profile(uf: str | None) -> StateFiscalProfile | None:
    return STATE_FISCAL_PROFILES.get(normalize_uf(uf))


def state_profile_payload(uf: str | None) -> dict:
    profile = state_profile(uf)
    if profile is None:
        normalized = normalize_uf(uf)
        return {
            "uf": normalized,
            "nome": normalized or "UF não informada",
            "icms_interno_referencia": None,
            "fcp_referencia": None,
            "exige_cbenef_quando_aplicavel": True,
            "requisitos_producao": (
                "Validar credenciamento, CSC, série e numeração com a SEFAZ da UF",
            ),
            "alertas": (
                "O CorePet não possui referência geral cadastrada para esta UF; confirme os parâmetros com a contabilidade.",
            ),
        }
    payload = asdict(profile)
    payload["icms_interno_referencia"] = float(profile.icms_interno_referencia)
    payload["fcp_referencia"] = float(profile.fcp_referencia)
    return payload


def default_company_fiscal_values(uf: str | None) -> dict:
    """Cria um rascunho seguro; produção continua bloqueada até confirmação."""

    normalized = normalize_uf(uf)
    profile = state_profile(normalized)
    return {
        "uf": normalized,
        "regime_tributario": "Simples Nacional",
        "contribuinte_icms": True,
        "icms_aliquota_interna": (
            profile.icms_interno_referencia if profile else Decimal("0.00")
        ),
        "icms_aliquota_interestadual": Decimal("12.00"),
        # Optante do Simples não recolhe o DIFAL de saída para consumidor final
        # não contribuinte separadamente. Aquisições e outros regimes são outro fluxo.
        "aplica_difal": False,
        "cfop_venda_interna": "5102",
        "cfop_venda_interestadual": "6102",
        "cfop_compra": "1102",
        "pis_cst_padrao": None,
        "pis_aliquota": Decimal("0.00"),
        "cofins_cst_padrao": None,
        "cofins_aliquota": Decimal("0.00"),
        "herdado_do_estado": True,
        "configuracao_confirmada": False,
    }


def production_fiscal_pending(tenant, config) -> list[str]:
    pending = []
    tenant_uf = normalize_uf(getattr(tenant, "uf", None))
    config_uf = normalize_uf(getattr(config, "uf", None)) if config else ""
    if not tenant_uf:
        pending.append("Informe a UF no cadastro da empresa.")
    if not str(getattr(tenant, "inscricao_estadual", None) or "").strip():
        pending.append("Informe a inscrição estadual da empresa.")
    if config is None:
        pending.append("Crie a configuração fiscal da empresa.")
    else:
        if tenant_uf and config_uf != tenant_uf:
            pending.append(
                f"A UF fiscal ({config_uf or 'vazia'}) difere da UF da empresa ({tenant_uf})."
            )
        if not bool(getattr(config, "configuracao_confirmada", False)):
            pending.append(
                "Confirme a configuração fiscal com a contabilidade antes de ativar produção."
            )
    return pending
