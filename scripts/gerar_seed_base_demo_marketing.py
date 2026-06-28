from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from validar_base_demo_marketing import (
    load_payload,
    resolve_demo_json_path,
    validate_payload,
)


SEED_NAME = "marketing_base_demo"


SECTION_ORDER = [
    "empresa",
    "usuarios",
    "financeiro.bancos",
    "financeiro.formas_pagamento",
    "financeiro.categorias",
    "financeiro.impostos",
    "fornecedores",
    "clientes",
    "pets",
    "produtos",
    "servicos",
    "compras",
    "ecommerce",
    "videos_prioritarios",
]


SECTION_LABELS = {
    "empresa": "Empresa",
    "usuarios": "Usuarios",
    "financeiro.bancos": "Bancos/contas",
    "financeiro.formas_pagamento": "Formas de pagamento",
    "financeiro.categorias": "Categorias financeiras",
    "financeiro.impostos": "Impostos/configuracao fiscal",
    "fornecedores": "Fornecedores",
    "clientes": "Clientes",
    "pets": "Pets",
    "produtos": "Produtos",
    "servicos": "Servicos",
    "compras": "Compras",
    "ecommerce": "Ecommerce/app",
    "videos_prioritarios": "Videos prioritarios",
}


def _section_payload(payload: dict[str, Any], section: str) -> Any:
    if section.startswith("financeiro."):
        key = section.split(".", maxsplit=1)[1]
        return payload.get("financeiro", {}).get(key, [])
    return payload.get(section)


def _count_items(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, list):
        return len(value)
    if isinstance(value, dict):
        return 1
    return 1


def _normalize_slug(value: str) -> str:
    return value.strip().lower().replace(" ", "_").replace("/", "_").replace("\\", "_")


def _build_action(
    section: str, payload: dict[str, Any], tenant_slug: str
) -> dict[str, Any]:
    section_data = _section_payload(payload, section)
    return {
        "key": f"{SEED_NAME}:{_normalize_slug(tenant_slug)}:{section}",
        "section": section,
        "label": SECTION_LABELS[section],
        "operation": "upsert",
        "items": _count_items(section_data),
        "payload": section_data,
        "notes": _action_notes(section),
    }


def _action_notes(section: str) -> list[str]:
    notes_by_section = {
        "empresa": [
            "Atualizar somente tenant/base demo.",
            "Nao sobrescrever tenant de producao.",
        ],
        "usuarios": [
            "Criar usuarios demo apenas se o ambiente permitir login ficticio.",
            "Nao criar senha real neste manifesto.",
        ],
        "financeiro.bancos": [
            "Criar antes de formas de pagamento que apontam para conta destino.",
        ],
        "financeiro.formas_pagamento": [
            "Criar antes de gravar venda PDV ou recebimento demo.",
        ],
        "financeiro.categorias": [
            "Classificar receitas e despesas para relatorios.",
        ],
        "financeiro.impostos": [
            "Usar apenas configuracao fiscal ficticia para explicacao de custo.",
        ],
        "fornecedores": [
            "Criar fornecedor antes de compras e produtos vinculados.",
        ],
        "clientes": [
            "Criar tutores antes dos pets.",
        ],
        "pets": [
            "Criar pets depois dos respectivos tutores.",
        ],
        "produtos": [
            "Criar produtos antes de PDV, ecommerce, compras e estoque.",
        ],
        "servicos": [
            "Criar servicos antes de agenda banho/tosa e veterinario.",
        ],
        "compras": [
            "Manter ao menos uma compra pendente para gravar antes/depois.",
        ],
        "ecommerce": [
            "Publicar somente produtos demo e nao expor chaves de integracao.",
        ],
        "videos_prioritarios": [
            "Usado para conferir se a base atende a primeira leva de gravacao.",
        ],
    }
    return notes_by_section.get(section, [])


def build_seed_plan(payload: dict[str, Any], tenant_slug: str) -> dict[str, Any]:
    actions = [
        _build_action(section, payload, tenant_slug)
        for section in SECTION_ORDER
        if _section_payload(payload, section) is not None
    ]
    counts = {action["section"]: action["items"] for action in actions}

    return {
        "metadata": {
            "seed_name": SEED_NAME,
            "source": payload.get("metadata", {}).get("nome", "Base Demo Sistema Pet"),
            "source_version": payload.get("metadata", {}).get("versao"),
            "tenant_slug": tenant_slug,
            "company": payload.get("empresa", {}).get("nome_fantasia"),
        },
        "safety": {
            "mode": "dry_run_manifest",
            "warning": (
                "Manifesto para preparacao de demo; nao executar em producao "
                "nem usar com dados reais."
            ),
            "requires_explicit_apply_step": True,
        },
        "summary": {
            "total_actions": len(actions),
            "counts": counts,
        },
        "actions": actions,
    }


def render_markdown(plan: dict[str, Any]) -> str:
    metadata = plan["metadata"]
    lines = [
        "# Manifesto de seed demo",
        "",
        f"Seed: `{metadata['seed_name']}`",
        f"Tenant alvo: `{metadata['tenant_slug']}`",
        f"Empresa: {metadata['company']}",
        f"Fonte: {metadata['source']} ({metadata['source_version']})",
        "",
        "## Seguranca",
        "",
        f"- Modo: `{plan['safety']['mode']}`",
        f"- Aviso: {plan['safety']['warning']}",
        "",
        "## Acoes",
        "",
        "| Ordem | Secao | Operacao | Itens |",
        "|---:|---|---|---:|",
    ]
    for index, action in enumerate(plan["actions"], start=1):
        lines.append(
            f"| {index} | {action['label']} | {action['operation']} | "
            f"{action['items']} |"
        )

    lines.extend(
        [
            "",
            "## Proximo passo",
            "",
            "Usar este manifesto como contrato para a etapa de aplicacao idempotente por tenant.",
        ]
    )
    return "\n".join(lines)


def write_output(content: str, output_path: Path | None) -> None:
    if output_path is None:
        print(content)
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Gera manifesto de seed para a base demo de marketing."
    )
    parser.add_argument(
        "--json", required=True, type=Path, help="Caminho do JSON da base demo."
    )
    parser.add_argument(
        "--tenant-slug",
        default="tenant_demo",
        help="Identificador legivel do tenant/base demo alvo.",
    )
    parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="markdown",
        help="Formato de saida.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Arquivo de saida opcional. Se omitido, imprime no console.",
    )
    args = parser.parse_args(argv)

    try:
        json_path = resolve_demo_json_path(args.json)
        payload = load_payload(json_path)
        errors = validate_payload(payload)
        if errors:
            raise ValueError("; ".join(errors))
    except ValueError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1

    plan = build_seed_plan(payload, tenant_slug=args.tenant_slug)
    if args.format == "json":
        content = json.dumps(plan, ensure_ascii=False, indent=2)
    else:
        content = render_markdown(plan)

    write_output(content, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
