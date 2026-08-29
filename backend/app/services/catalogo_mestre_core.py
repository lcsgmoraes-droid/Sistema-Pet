"""Regras puras do catalogo mestre: identidade, qualidade e pendencias."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

DEFAULT_MASTER_CATALOG_SOURCE_EMAIL = "atacadaopetpp@gmail.com"
DEFAULT_IMAGE_TARGET = 5
VALID_GTIN_LENGTHS = {8, 12, 13, 14}
INITIAL_CATALOG_TYPES = frozenset(
    {"racao", "petisco", "medicamento", "areia_sanitaria"}
)

_LITTER_ACCESSORY_MARKERS = (
    "banheiro para gato",
    "caixa de areia",
    "pa coletora",
    "pa higienica",
    "pazinha",
    "tapete coletor",
    "tapete para caixa",
)
_LITTER_MARKERS = (
    "areia",
    "cristais de silica",
    "granulado higienico",
    "granulado sanitario",
    "pipicat",
    "silica sanitaria",
    "substrato higienico",
)


class CatalogoMestreError(RuntimeError):
    pass


@dataclass(frozen=True)
class PendenciaSpec:
    tipo: str
    posicao_alvo: int = 0
    prioridade: int = 100
    origem_preferida: str | None = None
    detalhes: dict[str, Any] = field(default_factory=dict)


@dataclass
class CatalogoMestreSyncResult:
    source_tenant_id: str
    dry_run: bool
    image_target: int
    source_products: int = 0
    operational_products: int = 0
    eligible_products: int = 0
    excluded_by_scope: int = 0
    skipped_products: int = 0
    created_products: int = 0
    updated_products: int = 0
    unchanged_products: int = 0
    would_create_products: int = 0
    would_update_products: int = 0
    source_images: int = 0
    imported_images: int = 0
    would_import_images: int = 0
    products_below_image_target: int = 0
    image_slots_missing: int = 0
    created_pending_tasks: int = 0
    would_create_pending_tasks: int = 0
    resolved_pending_tasks: int = 0
    valid_gtins: int = 0
    invalid_gtins: int = 0
    missing_gtins: int = 0
    duplicate_gtins: int = 0
    quality_average: float = 0.0
    types: dict[str, int] = field(default_factory=dict)
    excluded_types: dict[str, int] = field(default_factory=dict)
    pending_types: dict[str, int] = field(default_factory=dict)
    samples: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def bump(self, bucket: str, key: str, amount: int = 1) -> None:
        target = getattr(self, bucket)
        target[key] = int(target.get(key, 0)) + amount

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": not self.errors,
            "source_tenant_id": self.source_tenant_id,
            "dry_run": self.dry_run,
            "image_target": self.image_target,
            "source_products": self.source_products,
            "operational_products": self.operational_products,
            "eligible_products": self.eligible_products,
            "excluded_by_scope": self.excluded_by_scope,
            "skipped_products": self.skipped_products,
            "created_products": self.created_products,
            "updated_products": self.updated_products,
            "unchanged_products": self.unchanged_products,
            "would_create_products": self.would_create_products,
            "would_update_products": self.would_update_products,
            "source_images": self.source_images,
            "imported_images": self.imported_images,
            "would_import_images": self.would_import_images,
            "products_below_image_target": self.products_below_image_target,
            "image_slots_missing": self.image_slots_missing,
            "created_pending_tasks": self.created_pending_tasks,
            "would_create_pending_tasks": self.would_create_pending_tasks,
            "resolved_pending_tasks": self.resolved_pending_tasks,
            "valid_gtins": self.valid_gtins,
            "invalid_gtins": self.invalid_gtins,
            "missing_gtins": self.missing_gtins,
            "duplicate_gtins": self.duplicate_gtins,
            "quality_average": self.quality_average,
            "types": dict(sorted(self.types.items())),
            "excluded_types": dict(sorted(self.excluded_types.items())),
            "pending_types": dict(sorted(self.pending_types.items())),
            "samples": self.samples,
            "warnings": self.warnings,
            "errors": self.errors,
        }


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def ascii_key(value: Any) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    without_marks = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    return re.sub(r"[^a-z0-9]+", " ", without_marks.casefold()).strip()


def text_value(value: Any) -> str | None:
    normalized = str(value or "").strip()
    return normalized or None


def json_safe(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(item) for item in value]
    return value


def parse_jsonish(value: Any) -> Any:
    if value is None or value == "":
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return value
    return json_safe(value)


def compact_dict(values: dict[str, Any]) -> dict[str, Any]:
    return {
        key: json_safe(value)
        for key, value in values.items()
        if value is not None and value != "" and value != [] and value != {}
    }


def normalize_gtin(value: Any) -> str | None:
    raw = str(value or "").strip()
    if not raw or re.search(r"[A-Za-z]", raw):
        return None
    digits = re.sub(r"\D", "", raw)
    if len(digits) not in VALID_GTIN_LENGTHS:
        return None
    body = digits[:-1]
    weighted_sum = sum(
        int(digit) * (3 if index % 2 == 0 else 1)
        for index, digit in enumerate(reversed(body))
    )
    expected = (10 - (weighted_sum % 10)) % 10
    return digits if expected == int(digits[-1]) else None


def barcode_identity(product: dict[str, Any]) -> tuple[str | None, str, list[str]]:
    raw_codes: list[str] = []
    for field_name in ("codigo_barras", "gtin_ean", "gtin_ean_tributario"):
        value = text_value(product.get(field_name))
        if value and value not in raw_codes:
            raw_codes.append(value)
    alternatives = parse_jsonish(product.get("codigos_barras_alternativos"))
    if isinstance(alternatives, list):
        for value in alternatives:
            normalized = text_value(value)
            if normalized and normalized not in raw_codes:
                raw_codes.append(normalized)
    for raw_code in raw_codes:
        valid = normalize_gtin(raw_code)
        if valid:
            return valid, "valido", raw_codes
    return None, ("invalido" if raw_codes else "ausente"), raw_codes


def classify_product(
    product: dict[str, Any], category: str | None, department: str | None
) -> str:
    haystack = ascii_key(
        " ".join(
            filter(
                None,
                (
                    text_value(product.get("nome")),
                    category,
                    department,
                    text_value(product.get("subcategoria")),
                ),
            )
        )
    )
    if any(token in haystack for token in ("farmacia", "medicamento", "remedio")):
        return "medicamento"
    if any(token in haystack for token in ("petisco", "biscoito", "snack")):
        return "petisco"
    if any(token in haystack for token in ("racao", "racoes", "alimento completo")):
        return "racao"
    if not any(marker in haystack for marker in _LITTER_ACCESSORY_MARKERS) and any(
        marker in haystack for marker in _LITTER_MARKERS
    ):
        return "areia_sanitaria"
    return "outro"


def is_initial_catalog_type(tipo_catalogo: str) -> bool:
    """Limita a primeira fase a produtos padronizaveis e normalmente de marca."""

    return tipo_catalogo in INITIAL_CATALOG_TYPES


def source_image_urls(
    product: dict[str, Any], image_rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()

    primary = text_value(product.get("imagem_principal"))
    if primary:
        seen.add(primary)
        result.append(
            {
                "url": primary,
                "ordem": 0,
                "e_principal": True,
                "largura": None,
                "altura": None,
                "tamanho_bytes": None,
                "produto_imagem_id": None,
            }
        )

    ordered_rows = sorted(
        image_rows,
        key=lambda row: (
            0 if row.get("e_principal") else 1,
            int(row.get("ordem") or 0),
            int(row.get("id") or 0),
        ),
    )
    for row in ordered_rows:
        url = text_value(row.get("url"))
        if not url or url in seen:
            continue
        seen.add(url)
        result.append(
            {
                "url": url,
                "ordem": len(result),
                "e_principal": bool(row.get("e_principal")) or not result,
                "largura": row.get("largura"),
                "altura": row.get("altura"),
                "tamanho_bytes": row.get("tamanho"),
                "produto_imagem_id": row.get("id"),
            }
        )
    return result


def build_source_payload(
    *,
    product: dict[str, Any],
    source_tenant_id: str,
    brand: str | None,
    category: str | None,
    department: str | None,
    fiscal: dict[str, Any] | None,
    image_target: int,
    synced_at: datetime,
) -> dict[str, Any]:
    gtin, gtin_status, raw_codes = barcode_identity(product)
    fiscal = fiscal or {}
    tipo_catalogo = classify_product(product, category, department)

    ncm = text_value(fiscal.get("ncm")) or text_value(product.get("ncm"))
    cest = text_value(fiscal.get("cest")) or text_value(product.get("cest"))
    origem = text_value(fiscal.get("origem_mercadoria")) or text_value(
        product.get("origem")
    )
    fiscal_reference = compact_dict(
        {
            "ncm": ncm,
            "ncm_fonte": "produto_config_fiscal" if fiscal.get("ncm") else "produto",
            "cest": cest,
            "cest_fonte": "produto_config_fiscal" if fiscal.get("cest") else "produto",
            "origem_mercadoria": origem,
            "cfop_venda": fiscal.get("cfop_venda") or product.get("cfop"),
            "cfop_compra": fiscal.get("cfop_compra"),
            "cst_icms": fiscal.get("cst_icms"),
            "icms_aliquota": fiscal.get("icms_aliquota")
            or product.get("aliquota_icms"),
            "pis_cst": fiscal.get("pis_cst"),
            "pis_aliquota": fiscal.get("pis_aliquota") or product.get("aliquota_pis"),
            "cofins_cst": fiscal.get("cofins_cst"),
            "cofins_aliquota": fiscal.get("cofins_aliquota")
            or product.get("aliquota_cofins"),
            "observacao": (
                "Dados fiscais de referencia da origem; validar por regime, UF e operacao "
                "antes de aplicar em uma loja."
            ),
        }
    )
    physical_data = compact_dict(
        {
            "peso_liquido": product.get("peso_liquido"),
            "peso_bruto": product.get("peso_bruto"),
            "peso_embalagem": product.get("peso_embalagem"),
            "largura": product.get("largura"),
            "altura": product.get("altura"),
            "profundidade": product.get("profundidade"),
            "volume": product.get("volume"),
            "itens_por_caixa": product.get("itens_por_caixa"),
        }
    )
    ration_data = compact_dict(
        {
            "classificacao": product.get("classificacao_racao"),
            "categoria": product.get("categoria_racao"),
            "especie_compativel": product.get("especie_compativel"),
            "especies_indicadas": parse_jsonish(product.get("especies_indicadas")),
            "porte_animal": parse_jsonish(product.get("porte_animal")),
            "fase_publico": parse_jsonish(product.get("fase_publico")),
            "tipo_tratamento": parse_jsonish(product.get("tipo_tratamento")),
            "sabor_proteina": product.get("sabor_proteina"),
            "tabela_nutricional": parse_jsonish(product.get("tabela_nutricional")),
            "tabela_consumo": parse_jsonish(product.get("tabela_consumo")),
        }
    )

    canonical = {
        "status": "em_curadoria",
        "ativo": True,
        "fonte_primaria": "tenant_produto",
        "origem_tenant_id": source_tenant_id,
        "origem_produto_id": int(product["id"]),
        "origem_atualizado_em": product.get("updated_at"),
        "codigo_origem": text_value(product.get("codigo")),
        "nome": text_value(product.get("nome")) or f"Produto {product['id']}",
        "tipo_catalogo": tipo_catalogo,
        "gtin": gtin,
        "gtin_status": gtin_status,
        "codigos_barras": raw_codes or None,
        "marca": brand,
        "categoria": category,
        "departamento": department,
        "subcategoria": text_value(product.get("subcategoria")),
        "descricao_curta": text_value(product.get("descricao_curta")),
        "descricao_completa": text_value(product.get("descricao_completa")),
        "tags": parse_jsonish(product.get("tags")),
        "unidade": text_value(product.get("unidade")),
        "ncm": ncm,
        "cest": cest,
        "origem_mercadoria": origem,
        "dados_fiscais_referencia": fiscal_reference or None,
        "dados_fisicos": physical_data or None,
        "dados_racao": ration_data or None,
        "registro_mapa": text_value(product.get("registro_mapa")),
        "principio_ativo": text_value(product.get("principio_ativo")),
        "fabricante": text_value(product.get("fabricante")),
        "forma_farmaceutica": text_value(product.get("forma_farmaceutica")),
        "especies_indicadas": parse_jsonish(product.get("especies_indicadas")),
        "bula_url": text_value(product.get("bula_url")),
        "bula_conteudo": parse_jsonish(product.get("bula_conteudo")),
        "posologia": parse_jsonish(product.get("posologia")),
        "conteudo_veterinario_status": "nao_verificado",
        "imagem_quantidade": 0,
        "imagem_meta_quantidade": image_target,
        "imagem_faltantes": image_target,
        "qualidade_percentual": 0.0,
        "lacunas": [],
        "ultima_sincronizacao_em": synced_at,
    }
    refresh_source_snapshot(canonical)

    source_reference = {
        "tipo": "tenant_produto",
        "source_tenant_id": source_tenant_id,
        "source_product_id": int(product["id"]),
    }
    canonical["proveniencia"] = {
        "fonte_primaria": source_reference,
        "campos": {
            key: source_reference
            for key, value in canonical.items()
            if value is not None
            and key
            not in {
                "proveniencia",
                "ultima_sincronizacao_em",
                "qualidade_percentual",
                "lacunas",
                "imagem_quantidade",
                "imagem_faltantes",
            }
        },
    }
    return canonical


def refresh_source_snapshot(payload: dict[str, Any]) -> None:
    """Atualiza o snapshot/hash apos decisoes que dependem do lote, como EAN duplicado."""

    snapshot = json_safe(
        {
            key: value
            for key, value in payload.items()
            if key
            not in {
                "status",
                "ativo",
                "imagem_quantidade",
                "imagem_meta_quantidade",
                "imagem_faltantes",
                "qualidade_percentual",
                "lacunas",
                "ultima_sincronizacao_em",
                "proveniencia",
                "snapshot_origem",
                "snapshot_origem_hash",
            }
        }
    )
    snapshot_json = json.dumps(
        snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    payload["snapshot_origem"] = snapshot
    payload["snapshot_origem_hash"] = hashlib.sha256(
        snapshot_json.encode("utf-8")
    ).hexdigest()


def quality_and_gaps(
    payload: dict[str, Any], image_count: int, image_target: int
) -> tuple[float, list[str]]:
    checks = (
        ("nome", 10),
        ("codigo_origem", 3),
        ("gtin", 15),
        ("marca", 6),
        ("categoria", 6),
        ("departamento", 3),
        ("descricao_curta", 5),
        ("descricao_completa", 10),
        ("ncm", 7),
        ("cest", 3),
        ("origem_mercadoria", 2),
        ("dados_fisicos", 3),
        ("unidade", 2),
    )
    score = float(sum(weight for key, weight in checks if payload.get(key)))
    details_key = (
        "dados_racao"
        if payload.get("tipo_catalogo") == "racao"
        else (
            "principio_ativo"
            if payload.get("tipo_catalogo") == "medicamento"
            else "tags"
        )
    )
    if payload.get(details_key):
        score += 5
    score += 20 * min(max(image_count, 0), image_target) / image_target

    gaps = [key for key, _weight in checks if not payload.get(key)]
    if not payload.get(details_key):
        gaps.append(details_key)
    if image_count < image_target:
        gaps.append("imagens")
    if payload.get("tipo_catalogo") == "racao":
        ration = payload.get("dados_racao") or {}
        if not ration.get("tabela_nutricional"):
            gaps.append("tabela_nutricional")
        if not ration.get("tabela_consumo"):
            gaps.append("tabela_consumo")
    if payload.get("tipo_catalogo") == "medicamento":
        for key in ("bula_url", "bula_conteudo", "posologia", "registro_mapa"):
            if not payload.get(key):
                gaps.append(key)
    return round(min(score, 100.0), 2), list(dict.fromkeys(gaps))


def pending_specs(
    payload: dict[str, Any], image_count: int, image_target: int
) -> list[PendenciaSpec]:
    specs: list[PendenciaSpec] = []
    for position in range(image_count + 1, image_target + 1):
        specs.append(
            PendenciaSpec(
                tipo="imagem",
                posicao_alvo=position,
                prioridade=20 + position,
                origem_preferida="oficial_licenciada",
                detalhes={
                    "meta": image_target,
                    "permite_geracao_assistida": True,
                    "publicacao_automatica": False,
                },
            )
        )
    if not payload.get("gtin"):
        specs.append(
            PendenciaSpec("gtin", prioridade=10, origem_preferida="fabricante_gs1")
        )
    if not payload.get("descricao_completa"):
        specs.append(
            PendenciaSpec(
                "descricao_completa",
                prioridade=50,
                origem_preferida="fabricante",
            )
        )
    if not payload.get("ncm"):
        specs.append(
            PendenciaSpec("fiscal", prioridade=30, origem_preferida="fonte_oficial")
        )
    if payload.get("tipo_catalogo") == "racao":
        ration = payload.get("dados_racao") or {}
        if not ration.get("tabela_nutricional"):
            specs.append(
                PendenciaSpec(
                    "tabela_nutricional",
                    prioridade=35,
                    origem_preferida="rotulo_fabricante",
                )
            )
        if not ration.get("tabela_consumo"):
            specs.append(
                PendenciaSpec(
                    "tabela_consumo",
                    prioridade=45,
                    origem_preferida="rotulo_fabricante",
                )
            )
    if payload.get("tipo_catalogo") == "medicamento":
        if not payload.get("bula_url") or not payload.get("bula_conteudo"):
            specs.append(
                PendenciaSpec(
                    "bula",
                    prioridade=5,
                    origem_preferida="registro_oficial",
                    detalhes={"requer_revisao_veterinaria": True},
                )
            )
        if not payload.get("posologia"):
            specs.append(
                PendenciaSpec(
                    "posologia",
                    prioridade=5,
                    origem_preferida="bula_oficial",
                    detalhes={
                        "requer_revisao_veterinaria": True,
                        "publicacao_automatica": False,
                    },
                )
            )
    return specs
