from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Protocol

from gerar_seed_base_demo_marketing import build_seed_plan
from validar_base_demo_marketing import (
    load_payload,
    resolve_demo_json_path,
    validate_payload,
)


PRODUCTION_ENVIRONMENTS = {"prod", "production", "producao"}
SECTION_BANK_ACCOUNTS = "financeiro.bancos"
SECTION_PAYMENT_METHODS = "financeiro.formas_pagamento"
SECTION_FINANCIAL_CATEGORIES = "financeiro.categorias"

BANK_TYPE_MAP = {
    "conta corrente": "corrente",
    "corrente": "corrente",
    "poupanca": "poupanca",
    "caixa": "caixa_fisico",
    "caixa fisico": "caixa_fisico",
    "carteira digital": "carteira_digital",
}

PAYMENT_TYPE_BY_NAME = {
    "pix": "pix",
    "dinheiro": "dinheiro",
    "cartao credito": "cartao_credito",
    "cartao de credito": "cartao_credito",
    "credito": "cartao_credito",
    "cartao debito": "cartao_debito",
    "cartao de debito": "cartao_debito",
    "debito": "cartao_debito",
}

SKIPPED_SECTIONS = {
    "empresa",
    "usuarios",
    "financeiro.impostos",
    "compras",
    "ecommerce",
    "videos_prioritarios",
}


class SeedRepository(Protocol):
    def upsert(self, action: dict) -> dict:
        """Apply one idempotent seed action."""


def normalize_tenant_email(tenant_email: str | None) -> str:
    normalized = (tenant_email or "").strip().lower()
    if not normalized:
        raise ValueError("Email do tenant e obrigatorio para aplicacao real.")
    return normalized


def _load_user_model(user_model: object | None) -> object:
    if user_model is not None:
        return user_model

    backend_path = Path(__file__).resolve().parents[1] / "backend"
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))

    from app.models import User

    return User


def _load_seed_models(models: dict[str, Any] | None = None) -> dict[str, Any]:
    if models is not None:
        return models

    backend_path = Path(__file__).resolve().parents[1] / "backend"
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))

    from app.banho_tosa_model_parts.cadastros import BanhoTosaServico
    from app.financeiro.models_caixa import ContaBancaria
    from app.financeiro.models_catalogos import CategoriaFinanceira, FormaPagamento
    from app.models import Cliente, Pet
    from app.produtos_models import Categoria, Produto

    return {
        "ContaBancaria": ContaBancaria,
        "FormaPagamento": FormaPagamento,
        "CategoriaFinanceira": CategoriaFinanceira,
        "Cliente": Cliente,
        "Pet": Pet,
        "Categoria": Categoria,
        "Produto": Produto,
        "BanhoTosaServico": BanhoTosaServico,
    }


def resolve_tenant_context_by_email(
    db: object,
    tenant_email: str,
    user_model: object | None = None,
) -> dict:
    normalized_email = normalize_tenant_email(tenant_email)
    UserModel = _load_user_model(user_model)
    user = db.query(UserModel).filter(UserModel.email == normalized_email).first()
    if user is None:
        raise ValueError(f"Usuario do tenant nao encontrado: {normalized_email}")

    tenant_id = getattr(user, "tenant_id", None)
    if tenant_id is None or not str(tenant_id).strip():
        raise ValueError(f"Usuario {normalized_email} nao possui tenant vinculado.")

    user_id = getattr(user, "id", None)
    if user_id is None:
        raise ValueError(f"Usuario {normalized_email} nao possui id valido.")

    return {
        "tenant_email": normalized_email,
        "tenant_id": str(tenant_id),
        "user_id": int(user_id),
    }


def _clean_text(value: object) -> str:
    return str(value or "").strip()


def _clean_key(value: object) -> str:
    return _clean_text(value).lower()


def _as_float(value: object, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    return float(value)


def _normalize_bank_type(value: object) -> str:
    return BANK_TYPE_MAP.get(_clean_key(value), "corrente")


def _normalize_payment_type(name: object, value: object) -> str:
    name_key = _clean_key(name)
    if name_key in PAYMENT_TYPE_BY_NAME:
        return PAYMENT_TYPE_BY_NAME[name_key]
    return PAYMENT_TYPE_BY_NAME.get(_clean_key(value), "dinheiro")


def _financial_category_type(name: str) -> str:
    return "receita" if _clean_key(name).startswith("venda") else "despesa"


class SQLAlchemyDemoSeedRepository:
    def __init__(
        self,
        db: object,
        tenant_id: str,
        user_id: int,
        models: dict[str, Any] | None = None,
    ) -> None:
        self.db = db
        self.tenant_id = str(tenant_id)
        self.user_id = int(user_id)
        self.models = _load_seed_models(models)

    def upsert(self, action: dict) -> dict:
        section = action["section"]
        handlers = {
            SECTION_BANK_ACCOUNTS: self._upsert_bank_accounts,
            SECTION_PAYMENT_METHODS: self._upsert_payment_methods,
            SECTION_FINANCIAL_CATEGORIES: self._upsert_financial_categories,
            "fornecedores": self._upsert_suppliers,
            "clientes": self._upsert_clients,
            "pets": self._upsert_pets,
            "produtos": self._upsert_products,
            "servicos": self._upsert_services,
        }
        handler = handlers.get(section)
        if handler is None or section in SKIPPED_SECTIONS:
            return self._section_result(action, status="skipped", skipped=action["items"])
        stats = handler(action.get("payload") or [])
        return self._section_result(action, status="applied", **stats)

    def _model(self, name: str) -> Any:
        return self.models[name]

    def _find(self, model_name: str, **filters: object) -> object | None:
        return self.db.query(self._model(model_name)).filter_by(**filters).first()

    def _upsert_record(
        self,
        model_name: str,
        lookup: dict[str, object],
        values: dict[str, object],
    ) -> tuple[str, object]:
        existing = self._find(model_name, **lookup)
        if existing is not None:
            for key, value in values.items():
                setattr(existing, key, value)
            return "updated", existing

        record = self._model(model_name)(**lookup, **values)
        self.db.add(record)
        self.db.flush()
        return "created", record

    def _count_status(self, status: str, stats: dict[str, int]) -> None:
        stats[status] += 1

    def _upsert_bank_accounts(self, payload: list[dict]) -> dict[str, int]:
        stats = self._empty_stats()
        for item in payload:
            status, _record = self._upsert_record(
                "ContaBancaria",
                {"tenant_id": self.tenant_id, "nome": item["nome"]},
                {
                    "tipo": _normalize_bank_type(item.get("tipo")),
                    "saldo_inicial": _as_float(item.get("saldo_inicial")),
                    "saldo_atual": _as_float(item.get("saldo_inicial")),
                    "ativa": True,
                    "user_id": self.user_id,
                },
            )
            self._count_status(status, stats)
        return stats

    def _upsert_payment_methods(self, payload: list[dict]) -> dict[str, int]:
        stats = self._empty_stats()
        for item in payload:
            payment_type = _normalize_payment_type(item.get("nome"), item.get("tipo"))
            status, _record = self._upsert_record(
                "FormaPagamento",
                {"tenant_id": self.tenant_id, "nome": item["nome"]},
                {
                    "tipo": payment_type,
                    "gera_contas_receber": True,
                    "ativo": True,
                    "permite_parcelamento": payment_type == "cartao_credito",
                    "max_parcelas": 6 if payment_type == "cartao_credito" else 1,
                    "parcelas_maximas": 6 if payment_type == "cartao_credito" else 1,
                    "user_id": self.user_id,
                },
            )
            self._count_status(status, stats)
        return stats

    def _upsert_financial_categories(self, payload: list[str]) -> dict[str, int]:
        stats = self._empty_stats()
        for name in payload:
            status, _record = self._upsert_record(
                "CategoriaFinanceira",
                {"tenant_id": self.tenant_id, "nome": name},
                {
                    "tipo": _financial_category_type(name),
                    "ativo": True,
                    "user_id": self.user_id,
                },
            )
            self._count_status(status, stats)
        return stats

    def _upsert_suppliers(self, payload: list[dict]) -> dict[str, int]:
        return self._upsert_people(payload, tipo_cadastro="fornecedor", tipo_pessoa="PJ")

    def _upsert_clients(self, payload: list[dict]) -> dict[str, int]:
        return self._upsert_people(payload, tipo_cadastro="cliente", tipo_pessoa="PF")

    def _upsert_people(
        self, payload: list[dict], tipo_cadastro: str, tipo_pessoa: str
    ) -> dict[str, int]:
        stats = self._empty_stats()
        for index, item in enumerate(payload, start=1):
            prefix = "FOR" if tipo_cadastro == "fornecedor" else "CLI"
            status, _record = self._upsert_record(
                "Cliente",
                {"tenant_id": self.tenant_id, "email": item["email"]},
                {
                    "user_id": self.user_id,
                    "codigo": f"DEMO-{prefix}-{index:03d}",
                    "nome": item["nome"],
                    "telefone": item.get("telefone"),
                    "celular": item.get("telefone"),
                    "tipo_cadastro": tipo_cadastro,
                    "tipo_pessoa": tipo_pessoa,
                    "ativo": True,
                    "controla_dre": tipo_cadastro != "fornecedor",
                },
            )
            self._count_status(status, stats)
        return stats

    def _upsert_pets(self, payload: list[dict]) -> dict[str, int]:
        stats = self._empty_stats()
        for index, item in enumerate(payload, start=1):
            tutor = self._find(
                "Cliente",
                tenant_id=self.tenant_id,
                nome=item["tutor"],
                tipo_cadastro="cliente",
            )
            if tutor is None:
                stats["skipped"] += 1
                continue
            status, _record = self._upsert_record(
                "Pet",
                {
                    "tenant_id": self.tenant_id,
                    "cliente_id": getattr(tutor, "id"),
                    "nome": item["nome"],
                },
                {
                    "user_id": self.user_id,
                    "codigo": f"DEMO-PET-{index:03d}",
                    "especie": item["especie"],
                    "raca": item.get("raca"),
                    "ativo": True,
                    "observacoes": item.get("uso"),
                },
            )
            self._count_status(status, stats)
        return stats

    def _upsert_products(self, payload: list[dict]) -> dict[str, int]:
        stats = self._empty_stats()
        for item in payload:
            category = self._ensure_product_category(item["categoria"])
            status, _record = self._upsert_record(
                "Produto",
                {"tenant_id": self.tenant_id, "codigo": item["sku"]},
                {
                    "user_id": self.user_id,
                    "nome": item["nome"],
                    "categoria_id": getattr(category, "id"),
                    "tipo": "produto",
                    "tipo_produto": "SIMPLES",
                    "is_parent": False,
                    "is_sellable": True,
                    "situacao": True,
                    "ativo": True,
                    "unidade": "UN",
                    "preco_custo": _as_float(item.get("custo")),
                    "preco_venda": _as_float(item.get("preco_venda")),
                    "estoque_atual": _as_float(item.get("estoque_inicial")),
                    "estoque_fisico": _as_float(item.get("estoque_inicial")),
                    "estoque_ecommerce": _as_float(item.get("estoque_inicial")),
                    "descricao_curta": "Produto demo para gravacao do Sistema Pet.",
                },
            )
            self._count_status(status, stats)
        return stats

    def _ensure_product_category(self, name: str) -> object:
        _status, category = self._upsert_record(
            "Categoria",
            {"tenant_id": self.tenant_id, "nome": name},
            {"user_id": self.user_id, "ativo": True},
        )
        return category

    def _upsert_services(self, payload: list[dict]) -> dict[str, int]:
        stats = self._empty_stats()
        for item in payload:
            if item.get("modulo") != "banho_tosa":
                stats["skipped"] += 1
                continue
            status, _record = self._upsert_record(
                "BanhoTosaServico",
                {"tenant_id": self.tenant_id, "nome": item["nome"]},
                {
                    "categoria": self._bath_service_category(item["nome"]),
                    "duracao_padrao_minutos": int(item.get("duracao_minutos") or 60),
                    "preco_base": _as_float(item.get("preco")),
                    "requer_banho": "banho" in _clean_key(item["nome"]),
                    "requer_tosa": "tosa" in _clean_key(item["nome"]),
                    "requer_secagem": True,
                    "permite_pacote": True,
                    "ativo": True,
                },
            )
            self._count_status(status, stats)
        return stats

    def _bath_service_category(self, name: str) -> str:
        return "tosa" if "tosa" in _clean_key(name) else "banho"

    def _empty_stats(self) -> dict[str, int]:
        return {"created": 0, "updated": 0, "skipped": 0}

    def _section_result(
        self,
        action: dict,
        status: str,
        created: int = 0,
        updated: int = 0,
        skipped: int = 0,
    ) -> dict:
        return {
            "section": action["section"],
            "operation": action["operation"],
            "items": action["items"],
            "status": status,
            "created": created,
            "updated": updated,
            "skipped": skipped,
        }


def _load_session_factory(session_factory: object | None) -> object:
    if session_factory is not None:
        return session_factory

    backend_path = Path(__file__).resolve().parents[1] / "backend"
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))

    from app.db import SessionLocal

    return SessionLocal


def _load_tenant_context_functions(
    set_tenant_context: object | None,
    clear_tenant_context: object | None,
) -> tuple[object, object]:
    if set_tenant_context is not None and clear_tenant_context is not None:
        return set_tenant_context, clear_tenant_context

    backend_path = Path(__file__).resolve().parents[1] / "backend"
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))

    from app.tenancy.context import clear_tenant_context as clear_context
    from app.tenancy.context import set_tenant_context as set_context

    return set_context, clear_context


def _tenant_context_value(tenant_id: str) -> object:
    try:
        from uuid import UUID

        return UUID(str(tenant_id))
    except ValueError:
        return tenant_id


def apply_seed_plan_for_tenant_email(
    plan: dict,
    tenant_email: str,
    session_factory: object | None = None,
    environment: str | None = None,
    models: dict[str, Any] | None = None,
    user_model: object | None = None,
    set_tenant_context: object | None = None,
    clear_tenant_context: object | None = None,
) -> dict:
    assert_safe_seed_environment(environment)
    normalized_email = normalize_tenant_email(tenant_email)
    factory = _load_session_factory(session_factory)
    set_context, clear_context = _load_tenant_context_functions(
        set_tenant_context,
        clear_tenant_context,
    )

    db = factory()
    tenant_context_started = False
    try:
        context = resolve_tenant_context_by_email(
            db,
            normalized_email,
            user_model=user_model,
        )
        set_context(_tenant_context_value(context["tenant_id"]))
        tenant_context_started = True
        repository = SQLAlchemyDemoSeedRepository(
            db,
            tenant_id=context["tenant_id"],
            user_id=context["user_id"],
            models=models,
        )
        result = apply_seed_plan(
            plan,
            repository=repository,
            dry_run=False,
            environment=environment,
            tenant_email=context["tenant_email"],
        )
        result["tenant_id"] = context["tenant_id"]
        result["user_id"] = context["user_id"]
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise
    finally:
        if tenant_context_started:
            clear_context()
        db.close()


def normalize_environment(environment: str | None) -> str:
    return (environment or "development").strip().lower()


def assert_safe_seed_environment(
    environment: str | None, allow_production: bool = False
) -> None:
    normalized = normalize_environment(environment)
    if normalized in PRODUCTION_ENVIRONMENTS and not allow_production:
        raise ValueError(
            "Seed demo bloqueado em producao. Use apenas tenant/base de demonstracao."
        )


def _dry_run_result(action: dict) -> dict:
    return {
        "section": action["section"],
        "operation": action["operation"],
        "items": action["items"],
        "status": "would_upsert",
    }


def apply_seed_plan(
    plan: dict,
    repository: SeedRepository,
    dry_run: bool,
    environment: str | None,
    tenant_email: str | None = None,
    allow_production: bool = False,
) -> dict:
    assert_safe_seed_environment(
        environment=environment,
        allow_production=allow_production,
    )

    results = []
    for action in plan["actions"]:
        if dry_run:
            results.append(_dry_run_result(action))
        else:
            results.append(repository.upsert(action))

    return {
        "seed_name": plan["metadata"]["seed_name"],
        "tenant_slug": plan["metadata"]["tenant_slug"],
        "tenant_email": tenant_email,
        "environment": normalize_environment(environment),
        "dry_run": dry_run,
        "total_actions": len(results),
        "results": results,
    }


class DryRunOnlyRepository:
    def upsert(self, action: dict) -> dict:
        raise RuntimeError(
            f"Repositorio real nao configurado para aplicar secao {action['section']}"
        )


def _load_plan(json_path: Path, tenant_slug: str) -> dict:
    resolved = resolve_demo_json_path(json_path)
    payload = load_payload(resolved)
    errors = validate_payload(payload)
    if errors:
        raise ValueError("; ".join(errors))
    return build_seed_plan(payload, tenant_slug=tenant_slug)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Aplica ou simula o manifesto de seed da base demo de marketing."
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
        "--tenant-email",
        default=None,
        help="Email do usuario principal do tenant alvo para o seed demo.",
    )
    parser.add_argument(
        "--environment",
        default=os.getenv("ENVIRONMENT") or os.getenv("APP_ENV") or "development",
        help="Ambiente de execucao usado para trava de seguranca.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simula a aplicacao sem chamar repositorio de banco.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Aplica o seed no tenant informado. Use somente em DEV/demo.",
    )
    args = parser.parse_args(argv)

    if args.dry_run and args.apply:
        print("ERRO: use apenas um modo: --dry-run ou --apply.", file=sys.stderr)
        return 1

    if not args.dry_run and not args.apply:
        print(
            "ERRO: informe um modo de execucao: --dry-run ou --apply.",
            file=sys.stderr,
        )
        return 1

    if args.apply and not args.tenant_email:
        print("ERRO: --apply exige --tenant-email.", file=sys.stderr)
        return 1

    try:
        plan = _load_plan(args.json, tenant_slug=args.tenant_slug)
        if args.dry_run:
            result = apply_seed_plan(
                plan,
                repository=DryRunOnlyRepository(),
                dry_run=True,
                environment=args.environment,
                tenant_email=args.tenant_email,
            )
        else:
            result = apply_seed_plan_for_tenant_email(
                plan,
                tenant_email=args.tenant_email,
                environment=args.environment,
            )
    except ValueError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"ERRO: falha ao aplicar seed demo: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
