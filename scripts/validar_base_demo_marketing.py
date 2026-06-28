from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ALLOWED_DATA_DIR = ROOT / "docs" / "marketing" / "base-demo"


REQUIRED_TOP_LEVEL = [
    "metadata",
    "empresa",
    "usuarios",
    "financeiro",
    "fornecedores",
    "produtos",
    "clientes",
    "pets",
    "servicos",
    "compras",
    "ecommerce",
    "videos_prioritarios",
]


MIN_COUNTS = {
    "produtos": 4,
    "clientes": 3,
    "pets": 3,
    "servicos": 4,
    "videos_prioritarios": 6,
}


REAL_EMAIL_DOMAINS = (
    "@gmail.",
    "@hotmail.",
    "@outlook.",
    "@icloud.",
    "@yahoo.",
)


def resolve_demo_json_path(path: Path) -> Path:
    resolved = path.resolve()
    allowed_root = ALLOWED_DATA_DIR.resolve()
    if not resolved.is_relative_to(allowed_root):
        raise ValueError(
            f"Caminho do JSON fora do repositorio/base demo permitida: {resolved}"
        )
    if not resolved.is_file():
        raise ValueError(f"Arquivo JSON da base demo nao encontrado: {resolved}")
    return resolved


def load_payload(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON invalido em {path}: {exc}") from exc


def iter_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            result.extend(iter_strings(item))
        return result
    if isinstance(value, dict):
        result = []
        for item in value.values():
            result.extend(iter_strings(item))
        return result
    return []


def validate_required_sections(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in REQUIRED_TOP_LEVEL:
        if key not in payload:
            errors.append(f"Secao obrigatoria ausente: {key}")
    return errors


def validate_min_counts(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key, minimum in MIN_COUNTS.items():
        value = payload.get(key, [])
        if not isinstance(value, list) or len(value) < minimum:
            errors.append(f"Secao {key} deve ter ao menos {minimum} itens")
    return errors


def validate_empresa(payload: dict[str, Any]) -> list[str]:
    empresa = payload.get("empresa", {})
    if empresa.get("nome_fantasia") != "Pet Feliz Demo":
        return ["Empresa demo deve ser Pet Feliz Demo"]
    return []


def collect_product_skus(payload: dict[str, Any]) -> set[str]:
    products = payload.get("produtos", [])
    return {product.get("sku") for product in products if isinstance(product, dict)}


def validate_products(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_fields = [
        "sku",
        "nome",
        "categoria",
        "preco_venda",
        "custo",
        "estoque_inicial",
    ]
    products = payload.get("produtos", [])
    for product in products:
        if not isinstance(product, dict):
            errors.append("Produto invalido encontrado")
            continue
        for field in required_fields:
            if field not in product:
                errors.append(f"Produto sem campo obrigatorio: {field}")
    return errors


def validate_ecommerce(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    ecommerce = payload.get("ecommerce", {})
    product_skus = collect_product_skus(payload)
    for sku in ecommerce.get("produtos_publicados", []):
        if sku not in product_skus:
            errors.append(f"SKU publicado no ecommerce nao existe em produtos: {sku}")
    return errors


def validate_first_video(payload: dict[str, Any]) -> list[str]:
    first_video = (payload.get("videos_prioritarios") or [{}])[0]
    if first_video.get("titulo") != "Estoque que some":
        return ["Primeiro video prioritario deve ser Estoque que some"]
    return []


def validate_sensitive_strings(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for text in iter_strings(payload):
        lowered = text.lower()
        if any(domain in lowered for domain in REAL_EMAIL_DOMAINS):
            errors.append(
                f"Email aparenta ser real e nao deve entrar na base demo: {text}"
            )
        if re.search(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b", text):
            errors.append(f"CPF aparente encontrado: {text}")
    return errors


def validate_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    validators = [
        validate_required_sections,
        validate_min_counts,
        validate_empresa,
        validate_products,
        validate_ecommerce,
        validate_first_video,
        validate_sensitive_strings,
    ]
    for validator in validators:
        errors.extend(validator(payload))
    return errors


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Base demo validada",
        "",
        f"Empresa: {payload['empresa']['nome_fantasia']}",
        "",
        "Nenhum dado sensivel aparente foi encontrado pelo validador basico.",
        "",
        "## Volumes",
        "",
        "| Secao | Itens |",
        "|---|---:|",
    ]

    for key in ["produtos", "clientes", "pets", "servicos", "videos_prioritarios"]:
        lines.append(f"| {key} | {len(payload[key])} |")

    lines.extend(
        [
            "",
            "## Videos prioritarios",
            "",
            "| Ordem | Video | Tipo | Duracao | Formato |",
            "|---:|---|---|---:|---|",
        ]
    )
    for index, video in enumerate(payload["videos_prioritarios"], start=1):
        lines.append(
            f"| {index} | {video['titulo']} | {video['tipo']} | "
            f"{video['duracao_segundos']}s | {video['formato']} |"
        )

    lines.extend(
        [
            "",
            "## Proximo passo",
            "",
            "Usar estes dados para preparar o tenant/base de demonstracao antes de gravar.",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Valida a base demo de marketing do Sistema Pet."
    )
    parser.add_argument(
        "--json", required=True, type=Path, help="Caminho do JSON da base demo."
    )
    parser.add_argument(
        "--markdown", action="store_true", help="Imprime checklist em Markdown."
    )
    args = parser.parse_args(argv)

    try:
        json_path = resolve_demo_json_path(args.json)
        payload = load_payload(json_path)
    except ValueError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1

    errors = validate_payload(payload)
    if errors:
        for error in errors:
            print(f"ERRO: {error}", file=sys.stderr)
        return 1

    if args.markdown:
        print(render_markdown(payload))
    else:
        print("Base demo validada")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
