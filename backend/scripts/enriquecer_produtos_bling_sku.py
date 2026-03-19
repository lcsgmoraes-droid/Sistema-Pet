#!/usr/bin/env python
"""Enriquece produtos do Sistema Pet com dados do Bling por SKU.

Regra importante (pedido do usuario):
- NUNCA atualiza preco_venda
- Atualiza apenas preco_custo e demais metadados

Fontes:
- CSV de produtos do Bling (dados fiscais, marca, fornecedor, categoria, departamento etc)
- CSV de estrutura/composicao (custo de kits: quantidade * custo unitario)

Fluxo recomendado:
1) Rodar preview (sem --apply)
2) Validar relatorios em backend/reports/enriquecimento_bling
3) Rodar com --apply em DEV (amostra)
4) Validar
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
from uuid import UUID

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db import SessionLocal
from app.models import Cliente, User
from app.produtos_models import Categoria, Departamento, Marca, Produto


def normalize_text(value: Optional[str]) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).strip())


def normalize_key(value: Optional[str]) -> str:
    text = normalize_text(value).upper()
    return re.sub(r"[^A-Z0-9]", "", text)


def parse_decimal(value: Optional[str]) -> Optional[float]:
    text = normalize_text(value)
    if not text:
        return None
    text = text.replace("R$", "").replace(" ", "")
    # Heuristica segura para pt-BR / en-US
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    else:
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def only_digits(value: Optional[str]) -> str:
    return re.sub(r"\D", "", normalize_text(value))


def build_family_key(value: Optional[str]) -> str:
    text = normalize_text(value).upper()
    if not text:
        return ""
    text = re.sub(r"\bQUANTIDADE\s*:\s*\d+\s*UNIDADES?\b", "", text)
    text = re.sub(r"\bPAI\b", "", text)
    return normalize_text(text)


def map_origem(value: Optional[str]) -> Optional[str]:
    text = normalize_text(value)
    if not text:
        return None
    if text.isdigit() and len(text) == 1 and text in {"0", "1", "2", "3", "4", "5", "6", "7", "8"}:
        return text
    upper = text.upper()
    if "NACIONAL" in upper:
        return "0"
    if "ESTRANGEIRA" in upper:
        return "1"
    return None


def pick(row: Dict[str, str], keys: Iterable[str]) -> str:
    for key in keys:
        if key in row and normalize_text(row.get(key)):
            return normalize_text(row.get(key))
    return ""


@dataclass
class BlingRow:
    sku: str
    nome: str
    descricao_curta: str
    descricao_complementar: str
    marca: str
    fornecedor: str
    categoria: str
    departamento: str
    codigo_barras: str
    ncm: str
    cest: str
    origem: str
    perfil_tributario: str
    preco_custo: Optional[float]


@dataclass
class UpdateResult:
    sku: str
    produto_id: Optional[int]
    produto_nome: str
    acao: str
    detalhes: str


@dataclass
class FamilyDefaults:
    marca: str = ""
    fornecedor: str = ""
    categoria: str = ""
    departamento: str = ""
    descricao_curta: str = ""
    descricao_complementar: str = ""
    ncm: str = ""
    cest: str = ""
    origem: str = ""
    perfil_tributario: str = ""


def choose_most_common_text(values: Dict[str, int]) -> str:
    if not values:
        return ""
    return sorted(values.items(), key=lambda item: (-item[1], -len(item[0]), item[0]))[0][0]


def choose_most_common_int(values: Dict[int, int]) -> Optional[int]:
    if not values:
        return None
    return sorted(values.items(), key=lambda item: (-item[1], item[0]))[0][0]


def build_family_defaults(rows: List[BlingRow]) -> Dict[str, FamilyDefaults]:
    counters: Dict[str, Dict[str, Dict[str, int]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    fields = [
        "marca",
        "fornecedor",
        "categoria",
        "departamento",
        "descricao_curta",
        "descricao_complementar",
        "ncm",
        "cest",
        "origem",
        "perfil_tributario",
    ]

    for row in rows:
        family_key = build_family_key(row.nome)
        if not family_key:
            continue
        for field in fields:
            value = normalize_text(getattr(row, field))
            if value:
                counters[family_key][field][value] += 1

    defaults: Dict[str, FamilyDefaults] = {}
    for family_key, field_counts in counters.items():
        defaults[family_key] = FamilyDefaults(
            marca=choose_most_common_text(field_counts["marca"]),
            fornecedor=choose_most_common_text(field_counts["fornecedor"]),
            categoria=choose_most_common_text(field_counts["categoria"]),
            departamento=choose_most_common_text(field_counts["departamento"]),
            descricao_curta=choose_most_common_text(field_counts["descricao_curta"]),
            descricao_complementar=choose_most_common_text(field_counts["descricao_complementar"]),
            ncm=choose_most_common_text(field_counts["ncm"]),
            cest=choose_most_common_text(field_counts["cest"]),
            origem=choose_most_common_text(field_counts["origem"]),
            perfil_tributario=choose_most_common_text(field_counts["perfil_tributario"]),
        )
    return defaults


def build_existing_classification_defaults(produtos: List[Produto]) -> Tuple[Dict[str, Optional[int]], Dict[str, Optional[int]]]:
    department_counts: Dict[str, Dict[int, int]] = defaultdict(lambda: defaultdict(int))
    category_counts: Dict[str, Dict[int, int]] = defaultdict(lambda: defaultdict(int))

    for produto in produtos:
        family_key = build_family_key(produto.nome)
        if not family_key:
            continue
        if produto.departamento_id:
            department_counts[family_key][int(produto.departamento_id)] += 1
        if produto.categoria_id:
            category_counts[family_key][int(produto.categoria_id)] += 1

    department_defaults = {
        family_key: choose_most_common_int(counts)
        for family_key, counts in department_counts.items()
    }
    category_defaults = {
        family_key: choose_most_common_int(counts)
        for family_key, counts in category_counts.items()
    }
    return department_defaults, category_defaults


def load_bling_rows(csv_path: Path) -> List[BlingRow]:
    rows: List[BlingRow] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        for raw in reader:
            sku = pick(raw, ["Código", "Codigo", "codigo"]) 
            if not normalize_key(sku):
                continue
            rows.append(
                BlingRow(
                    sku=sku,
                    nome=pick(raw, ["Descrição", "Descricao", "descricao"]),
                    descricao_curta=pick(raw, ["Descrição Curta", "Descricao Curta"]),
                    descricao_complementar=pick(raw, ["Descrição Complementar", "Descricao Complementar", "Observações", "Observacoes"]),
                    marca=pick(raw, ["Marca", "marca"]),
                    fornecedor=pick(raw, ["Fornecedor", "fornecedor"]),
                    categoria=pick(raw, ["Categoria do produto", "Grupo de produtos", "Grupo", "grupo"]),
                    departamento=pick(raw, ["Departamento", "departamento"]),
                    codigo_barras=pick(raw, ["GTIN/EAN", "Código Barra", "Codigo Barra", "codigo_barras"]),
                    ncm=pick(raw, ["NCM", "Código NCM", "Codigo NCM"]),
                    cest=pick(raw, ["CEST"]),
                    origem=pick(raw, ["Origem", "Origem da mercadoria"]),
                    perfil_tributario=pick(raw, ["Tributos", "Perfil Tributário", "Perfil Tributario"]),
                    preco_custo=(
                        parse_decimal(pick(raw, ["Preço de custo", "Preco de custo", "Preço de Compra", "Preco de Compra", "Custo"]))
                    ),
                )
            )
    return rows


def load_kit_costs(csv_path: Optional[Path]) -> Dict[str, float]:
    if not csv_path or not csv_path.exists():
        return {}

    costs: Dict[str, float] = {}
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        for raw in reader:
            comp_code = normalize_text(raw.get("Código da composição"))
            if not normalize_key(comp_code):
                continue

            qty = parse_decimal(raw.get("Quantidade do Componente"))
            unit_cost = parse_decimal(raw.get("Custo unitário"))
            if qty is None or unit_cost is None:
                continue

            key = normalize_key(comp_code)
            costs[key] = costs.get(key, 0.0) + (qty * unit_cost)

    return costs


def detect_single_tenant_id(db) -> UUID:
    tenant_ids = [row[0] for row in db.query(User.tenant_id).distinct().all() if row[0]]
    if len(tenant_ids) != 1:
        raise RuntimeError("Ambiente com mais de um tenant. Informe --tenant-id.")
    return tenant_ids[0]


def find_user_id(db, tenant_id: UUID) -> int:
    user = db.query(User).filter(User.tenant_id == tenant_id).order_by(User.id.asc()).first()
    if user:
        return user.id

    produto_user = (
        db.query(Produto.user_id)
        .filter(Produto.tenant_id == tenant_id, Produto.user_id.isnot(None))
        .order_by(Produto.user_id.asc())
        .first()
    )
    if produto_user and produto_user[0]:
        return int(produto_user[0])

    raise RuntimeError(f"Nenhum usuario encontrado para tenant {tenant_id}")


def get_or_create_marca(db, tenant_id: UUID, user_id: int, cache: Dict[str, Marca], nome: str, apply_mode: bool) -> Optional[Marca]:
    nome = normalize_text(nome)
    if not nome:
        return None

    key = nome.upper()
    if key in cache:
        return cache[key]

    marca = db.query(Marca).filter(Marca.tenant_id == tenant_id, Marca.nome.ilike(nome)).first()
    if not marca and apply_mode:
        marca = Marca(nome=nome, tenant_id=tenant_id, user_id=user_id, ativo=True)
        db.add(marca)
        db.flush()
    if marca:
        cache[key] = marca
    return marca


def get_or_create_departamento(db, tenant_id: UUID, user_id: int, cache: Dict[str, Departamento], nome: str, apply_mode: bool) -> Optional[Departamento]:
    nome = normalize_text(nome)
    if not nome:
        return None

    key = nome.upper()
    if key in cache:
        return cache[key]

    dep = db.query(Departamento).filter(Departamento.tenant_id == tenant_id, Departamento.nome.ilike(nome)).first()
    if not dep and apply_mode:
        dep = Departamento(nome=nome, tenant_id=tenant_id, user_id=user_id, ativo=True)
        db.add(dep)
        db.flush()
    if dep:
        cache[key] = dep
    return dep


def get_or_create_categoria(
    db,
    tenant_id: UUID,
    user_id: int,
    cache: Dict[str, Categoria],
    nome: str,
    departamento_id: Optional[int],
    apply_mode: bool,
) -> Optional[Categoria]:
    nome = normalize_text(nome)
    if not nome:
        return None

    key = f"{nome.upper()}|{departamento_id or 0}"
    if key in cache:
        return cache[key]

    query = db.query(Categoria).filter(Categoria.tenant_id == tenant_id, Categoria.nome.ilike(nome))
    if departamento_id:
        query = query.filter((Categoria.departamento_id == departamento_id) | (Categoria.departamento_id.is_(None)))
    cat = query.order_by(Categoria.id.asc()).first()

    if not cat and apply_mode:
        cat = Categoria(
            nome=nome,
            tenant_id=tenant_id,
            user_id=user_id,
            ativo=True,
            departamento_id=departamento_id,
        )
        db.add(cat)
        db.flush()

    if cat:
        if apply_mode and departamento_id and cat.departamento_id is None:
            cat.departamento_id = departamento_id
        cache[key] = cat
    return cat


def get_or_create_fornecedor(db, tenant_id: UUID, user_id: int, cache: Dict[str, Cliente], nome: str, apply_mode: bool) -> Optional[Cliente]:
    nome = normalize_text(nome)
    if not nome:
        return None

    key = nome.upper()
    if key in cache:
        return cache[key]

    forn = (
        db.query(Cliente)
        .filter(Cliente.tenant_id == tenant_id, Cliente.tipo_cadastro == "fornecedor", Cliente.nome.ilike(nome))
        .first()
    )

    if not forn and apply_mode:
        forn = Cliente(
            tenant_id=tenant_id,
            user_id=user_id,
            tipo_cadastro="fornecedor",
            tipo_pessoa="PJ",
            nome=nome,
            ativo=True,
        )
        db.add(forn)
        db.flush()

    if forn:
        cache[key] = forn
    return forn


def write_csv(path: Path, rows: List[Dict[str, object]], headers: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, delimiter=";")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def run(args: argparse.Namespace) -> int:
    repo_root = Path(__file__).resolve().parents[2]

    bling_csv = Path(args.bling_csv)
    if not bling_csv.is_absolute():
        bling_csv = repo_root / bling_csv
    if not bling_csv.exists():
        print(f"ERRO: CSV Bling nao encontrado: {bling_csv}")
        return 1

    estrutura_csv: Optional[Path] = None
    if args.estrutura_csv:
        estrutura_csv = Path(args.estrutura_csv)
        if not estrutura_csv.is_absolute():
            estrutura_csv = repo_root / estrutura_csv
        if not estrutura_csv.exists():
            print(f"AVISO: CSV estrutura nao encontrado, seguindo sem custo de kit: {estrutura_csv}")
            estrutura_csv = None

    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = repo_root / output_dir

    bling_rows = load_bling_rows(bling_csv)
    kit_costs = load_kit_costs(estrutura_csv)
    family_defaults = build_family_defaults(bling_rows)

    db = SessionLocal()
    try:
        tenant_id = UUID(args.tenant_id) if args.tenant_id else detect_single_tenant_id(db)
        user_id = find_user_id(db, tenant_id)

        produtos = db.query(Produto).filter(Produto.tenant_id == tenant_id, Produto.codigo.isnot(None), Produto.codigo != "").all()
        by_sku: Dict[str, List[Produto]] = {}
        for p in produtos:
            key = normalize_key(p.codigo)
            if not key:
                continue
            by_sku.setdefault(key, []).append(p)

        marca_cache: Dict[str, Marca] = {}
        dep_cache: Dict[str, Departamento] = {}
        cat_cache: Dict[str, Categoria] = {}
        forn_cache: Dict[str, Cliente] = {}
        family_dep_ids, family_cat_ids = build_existing_classification_defaults(produtos)

        preview_rows: List[Dict[str, object]] = []
        update_rows: List[Dict[str, object]] = []

        matched = 0
        updated = 0
        skipped_multiple = 0
        skipped_not_found = 0
        kit_cost_applied = 0

        for row in bling_rows:
            sku_key = normalize_key(row.sku)
            candidates = by_sku.get(sku_key, [])
            if not candidates:
                skipped_not_found += 1
                preview_rows.append(
                    {
                        "sku": row.sku,
                        "produto_id": "",
                        "produto_nome": "",
                        "status": "SEM_MATCH",
                        "detalhes": "SKU nao encontrado no sistema",
                    }
                )
                continue

            if len(candidates) > 1:
                skipped_multiple += 1
                preview_rows.append(
                    {
                        "sku": row.sku,
                        "produto_id": "",
                        "produto_nome": "",
                        "status": "AMBIGUO",
                        "detalhes": f"SKU com {len(candidates)} produtos no sistema",
                    }
                )
                continue

            produto = candidates[0]
            matched += 1

            family_key = build_family_key(row.nome or produto.nome)
            family_default = family_defaults.get(family_key, FamilyDefaults())

            resolved_departamento = row.departamento or family_default.departamento
            resolved_categoria = row.categoria or family_default.categoria
            resolved_marca = row.marca or family_default.marca
            resolved_fornecedor = row.fornecedor or family_default.fornecedor
            resolved_descricao_curta = row.descricao_curta or family_default.descricao_curta
            resolved_descricao_complementar = row.descricao_complementar or family_default.descricao_complementar
            resolved_ncm = row.ncm or family_default.ncm
            resolved_cest = row.cest or family_default.cest
            resolved_origem = row.origem or family_default.origem
            resolved_perfil_tributario = row.perfil_tributario or family_default.perfil_tributario

            dep = get_or_create_departamento(db, tenant_id, user_id, dep_cache, resolved_departamento, args.apply)
            inferred_dep_id = dep.id if dep else family_dep_ids.get(family_key)
            cat = get_or_create_categoria(db, tenant_id, user_id, cat_cache, resolved_categoria, inferred_dep_id, args.apply)
            inferred_cat_id = cat.id if cat else family_cat_ids.get(family_key)
            marca = get_or_create_marca(db, tenant_id, user_id, marca_cache, resolved_marca, args.apply)
            forn = get_or_create_fornecedor(db, tenant_id, user_id, forn_cache, resolved_fornecedor, args.apply)

            new_preco_custo = row.preco_custo
            kit_cost = kit_costs.get(sku_key)
            if kit_cost is not None:
                new_preco_custo = kit_cost
                kit_cost_applied += 1

            changes: List[str] = []

            # IMPORTANTE: nao mexer em preco_venda
            if new_preco_custo is not None and (produto.preco_custo or 0.0) != float(new_preco_custo):
                changes.append(f"preco_custo: {produto.preco_custo} -> {new_preco_custo}")
                if args.apply:
                    produto.preco_custo = float(new_preco_custo)

            target_departamento_id = dep.id if dep else inferred_dep_id
            if target_departamento_id and produto.departamento_id != target_departamento_id:
                changes.append(f"departamento_id: {produto.departamento_id} -> {target_departamento_id}")
                if args.apply:
                    produto.departamento_id = target_departamento_id

            target_categoria_id = cat.id if cat else inferred_cat_id
            if target_categoria_id and produto.categoria_id != target_categoria_id:
                changes.append(f"categoria_id: {produto.categoria_id} -> {target_categoria_id}")
                if args.apply:
                    produto.categoria_id = target_categoria_id

            if marca and produto.marca_id != marca.id:
                changes.append(f"marca_id: {produto.marca_id} -> {marca.id}")
                if args.apply:
                    produto.marca_id = marca.id

            if forn and produto.fornecedor_id != forn.id:
                changes.append(f"fornecedor_id: {produto.fornecedor_id} -> {forn.id}")
                if args.apply:
                    produto.fornecedor_id = forn.id

            codigo_barras_digits = only_digits(row.codigo_barras)[:13]
            if codigo_barras_digits and normalize_text(produto.codigo_barras) != codigo_barras_digits:
                changes.append("codigo_barras atualizado")
                if args.apply:
                    produto.codigo_barras = codigo_barras_digits

            ncm_digits = only_digits(resolved_ncm)[:8]
            if ncm_digits and normalize_text(produto.ncm) != ncm_digits:
                changes.append("ncm atualizado")
                if args.apply:
                    produto.ncm = ncm_digits

            cest_digits = only_digits(resolved_cest)[:7]
            if cest_digits and normalize_text(produto.cest) != cest_digits:
                changes.append("cest atualizado")
                if args.apply:
                    produto.cest = cest_digits

            origem = map_origem(resolved_origem)
            if origem and normalize_text(produto.origem) != origem:
                changes.append("origem atualizada")
                if args.apply:
                    produto.origem = origem

            if resolved_perfil_tributario and normalize_text(produto.perfil_tributario) != resolved_perfil_tributario:
                changes.append("perfil_tributario atualizado")
                if args.apply:
                    produto.perfil_tributario = resolved_perfil_tributario

            if resolved_descricao_curta and normalize_text(produto.descricao_curta) != resolved_descricao_curta:
                changes.append("descricao_curta atualizada")
                if args.apply:
                    produto.descricao_curta = resolved_descricao_curta

            if resolved_descricao_complementar and normalize_text(produto.descricao_completa) != resolved_descricao_complementar:
                changes.append("descricao_completa atualizada")
                if args.apply:
                    produto.descricao_completa = resolved_descricao_complementar

            status = "SEM_ALTERACAO"
            details = ""
            if changes:
                updated += 1
                status = "ATUALIZAR" if not args.apply else "ATUALIZADO"
                details = " | ".join(changes)
                update_rows.append(
                    {
                        "sku": row.sku,
                        "produto_id": produto.id,
                        "produto_nome": produto.nome,
                        "detalhes": details,
                    }
                )

            preview_rows.append(
                {
                    "sku": row.sku,
                    "produto_id": produto.id,
                    "produto_nome": produto.nome,
                    "status": status,
                    "detalhes": details,
                }
            )

        if args.sample_limit and args.sample_limit > 0:
            update_rows = update_rows[: args.sample_limit]

        if args.apply:
            if args.sample_limit and args.sample_limit > 0:
                sample_ids = {int(r["produto_id"]) for r in update_rows if r.get("produto_id")}
                # rollback parcial: aplica somente amostra
                for produto in produtos:
                    if produto.id not in sample_ids:
                        db.expire(produto)
                # Reaplicar somente amostra a partir do preview (sem mexer em preco_venda)
                db.rollback()

                # Segunda passada para amostra, simples e deterministica
                marca_cache.clear()
                dep_cache.clear()
                cat_cache.clear()
                forn_cache.clear()
                sample_skus = {normalize_key(r["sku"]) for r in update_rows}

                for row in bling_rows:
                    if normalize_key(row.sku) not in sample_skus:
                        continue
                    candidates = by_sku.get(normalize_key(row.sku), [])
                    if len(candidates) != 1:
                        continue
                    produto = db.query(Produto).filter(Produto.id == candidates[0].id).first()
                    if not produto:
                        continue

                    family_key = build_family_key(row.nome or produto.nome)
                    family_default = family_defaults.get(family_key, FamilyDefaults())

                    resolved_departamento = row.departamento or family_default.departamento
                    resolved_categoria = row.categoria or family_default.categoria
                    resolved_marca = row.marca or family_default.marca
                    resolved_fornecedor = row.fornecedor or family_default.fornecedor
                    resolved_descricao_curta = row.descricao_curta or family_default.descricao_curta
                    resolved_descricao_complementar = row.descricao_complementar or family_default.descricao_complementar
                    resolved_ncm = row.ncm or family_default.ncm
                    resolved_cest = row.cest or family_default.cest
                    resolved_origem = row.origem or family_default.origem
                    resolved_perfil_tributario = row.perfil_tributario or family_default.perfil_tributario

                    dep = get_or_create_departamento(db, tenant_id, user_id, dep_cache, resolved_departamento, True)
                    inferred_dep_id = dep.id if dep else family_dep_ids.get(family_key)
                    cat = get_or_create_categoria(db, tenant_id, user_id, cat_cache, resolved_categoria, inferred_dep_id, True)
                    inferred_cat_id = cat.id if cat else family_cat_ids.get(family_key)
                    marca = get_or_create_marca(db, tenant_id, user_id, marca_cache, resolved_marca, True)
                    forn = get_or_create_fornecedor(db, tenant_id, user_id, forn_cache, resolved_fornecedor, True)

                    new_preco_custo = row.preco_custo
                    kit_cost = kit_costs.get(normalize_key(row.sku))
                    if kit_cost is not None:
                        new_preco_custo = kit_cost

                    if new_preco_custo is not None:
                        produto.preco_custo = float(new_preco_custo)
                    if dep:
                        produto.departamento_id = dep.id
                    elif inferred_dep_id:
                        produto.departamento_id = inferred_dep_id
                    if cat:
                        produto.categoria_id = cat.id
                    elif inferred_cat_id:
                        produto.categoria_id = inferred_cat_id
                    if marca:
                        produto.marca_id = marca.id
                    if forn:
                        produto.fornecedor_id = forn.id

                    codigo_barras_digits = only_digits(row.codigo_barras)[:13]
                    if codigo_barras_digits:
                        produto.codigo_barras = codigo_barras_digits

                    ncm_digits = only_digits(resolved_ncm)[:8]
                    if ncm_digits:
                        produto.ncm = ncm_digits

                    cest_digits = only_digits(resolved_cest)[:7]
                    if cest_digits:
                        produto.cest = cest_digits

                    origem = map_origem(resolved_origem)
                    if origem:
                        produto.origem = origem

                    if resolved_perfil_tributario:
                        produto.perfil_tributario = resolved_perfil_tributario
                    if resolved_descricao_curta:
                        produto.descricao_curta = resolved_descricao_curta
                    if resolved_descricao_complementar:
                        produto.descricao_completa = resolved_descricao_complementar

            db.commit()

        write_csv(
            output_dir / "preview_enriquecimento.csv",
            preview_rows,
            ["sku", "produto_id", "produto_nome", "status", "detalhes"],
        )
        write_csv(
            output_dir / "alteracoes_planejadas.csv",
            update_rows,
            ["sku", "produto_id", "produto_nome", "detalhes"],
        )

        resumo = [
            f"bling_csv={bling_csv}",
            f"estrutura_csv={estrutura_csv or ''}",
            f"tenant_id={tenant_id}",
            f"modo_apply={args.apply}",
            f"sample_limit={args.sample_limit}",
            f"total_bling={len(bling_rows)}",
            f"match_por_sku={matched}",
            f"sem_match={skipped_not_found}",
            f"sku_ambiguo={skipped_multiple}",
            f"produtos_com_alteracoes={updated}",
            f"custo_kit_aplicado={kit_cost_applied}",
            "regra_preco_venda=NAO_ALTERAR",
        ]
        (output_dir / "resumo.txt").write_text("\n".join(resumo), encoding="utf-8")

        print("Processamento concluido.")
        print(f"Relatorios: {output_dir}")
        for line in resumo[5:]:
            print(f"- {line}")

    finally:
        db.close()

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Enriquecer produtos por SKU a partir do Bling")
    parser.add_argument(
        "--bling-csv",
        type=str,
        default="PRODUTOS BLING/produtos_2026-03-18-17-11-13.csv",
        help="CSV de produtos exportado do Bling",
    )
    parser.add_argument(
        "--estrutura-csv",
        type=str,
        default="PRODUTOS BLING/produtos_estrutura_2026-03-18-17-09-07.csv",
        help="CSV de estrutura/composicao para custo de kit",
    )
    parser.add_argument("--tenant-id", type=str, default="", help="Tenant alvo")
    parser.add_argument("--apply", action="store_true", help="Aplica alteracoes no banco")
    parser.add_argument(
        "--sample-limit",
        type=int,
        default=0,
        help="Limita aplicacao a N produtos (somente com --apply)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="backend/reports/enriquecimento_bling",
        help="Pasta de saida dos relatorios",
    )
    args = parser.parse_args()
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
