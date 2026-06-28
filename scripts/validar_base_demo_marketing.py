from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


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


def validate_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    for key in REQUIRED_TOP_LEVEL:
        if key not in payload:
            errors.append(f"Secao obrigatoria ausente: {key}")

    for key, minimum in MIN_COUNTS.items():
        value = payload.get(key, [])
        if not isinstance(value, list) or len(value) < minimum:
            errors.append(f"Secao {key} deve ter ao menos {minimum} itens")

    empresa = payload.get("empresa", {})
    if empresa.get("nome_fantasia") != "Pet Feliz Demo":
        errors.append("Empresa demo deve ser Pet Feliz Demo")

    products = payload.get("produtos", [])
    product_skus = {
        product.get("sku") for product in products if isinstance(product, dict)
    }
    for product in products:
        if not isinstance(product, dict):
            errors.append("Produto invalido encontrado")
            continue
        for field in [
            "sku",
            "nome",
            "categoria",
            "preco_venda",
            "custo",
            "estoque_inicial",
        ]:
            if field not in product:
                errors.append(f"Produto sem campo obrigatorio: {field}")

    ecommerce = payload.get("ecommerce", {})
    for sku in ecommerce.get("produtos_publicados", []):
        if sku not in product_skus:
            errors.append(f"SKU publicado no ecommerce nao existe em produtos: {sku}")

    first_video = (payload.get("videos_prioritarios") or [{}])[0]
    if first_video.get("titulo") != "Estoque que some":
        errors.append("Primeiro video prioritario deve ser Estoque que some")

    for text in iter_strings(payload):
        lowered = text.lower()
        if any(domain in lowered for domain in REAL_EMAIL_DOMAINS):
            errors.append(
                f"Email aparenta ser real e nao deve entrar na base demo: {text}"
            )
        if re.search(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b", text):
            errors.append(f"CPF aparente encontrado: {text}")

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

    payload = load_payload(args.json)
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
