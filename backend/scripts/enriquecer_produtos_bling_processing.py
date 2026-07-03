"""Orquestracao do enriquecimento Bling."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID

from enriquecer_produtos_bling_classification import (
    build_existing_classification_defaults,
    build_family_defaults,
)
from enriquecer_produtos_bling_loaders import load_bling_rows, load_kit_costs
from enriquecer_produtos_bling_types import BlingRow, FamilyDefaults
from enriquecer_produtos_bling_utils import (
    build_family_key,
    map_origem,
    normalize_key,
    normalize_text,
    only_digits,
)


@dataclass
class RunPaths:
    bling_csv: Path
    estrutura_csv: Optional[Path]
    output_dir: Path


@dataclass
class DbDependencies:
    Categoria: Any
    Cliente: Any
    Departamento: Any
    Marca: Any
    Produto: Any
    SessionLocal: Callable[[], Any]
    detect_single_tenant_id: Callable[..., UUID]
    find_user_id: Callable[..., int]
    get_or_create_categoria: Callable[..., Any]
    get_or_create_departamento: Callable[..., Any]
    get_or_create_fornecedor: Callable[..., Any]
    get_or_create_marca: Callable[..., Any]


@dataclass
class RelatedCaches:
    marcas: Dict[str, Any] = field(default_factory=dict)
    departamentos: Dict[str, Any] = field(default_factory=dict)
    categorias: Dict[str, Any] = field(default_factory=dict)
    fornecedores: Dict[str, Any] = field(default_factory=dict)

    def clear(self) -> None:
        self.marcas.clear()
        self.departamentos.clear()
        self.categorias.clear()
        self.fornecedores.clear()


@dataclass
class ProcessingCounters:
    matched: int = 0
    updated: int = 0
    skipped_multiple: int = 0
    skipped_not_found: int = 0
    kit_cost_applied: int = 0


@dataclass
class ResolvedFields:
    family_key: str
    departamento: str
    categoria: str
    marca: str
    fornecedor: str
    descricao_curta: str
    descricao_complementar: str
    ncm: str
    cest: str
    origem: str
    perfil_tributario: str


@dataclass
class RelatedEntities:
    departamento_id: Optional[int]
    categoria_id: Optional[int]
    marca: Any
    fornecedor: Any


@dataclass
class ProcessingContext:
    db: Any
    dbx: DbDependencies
    tenant_id: UUID
    user_id: int
    by_sku: Dict[str, List[Any]]
    family_defaults: Dict[str, FamilyDefaults]
    family_dep_ids: Dict[str, Optional[int]]
    family_cat_ids: Dict[str, Optional[int]]
    kit_costs: Dict[str, float]
    apply_mode: bool
    caches: RelatedCaches = field(default_factory=RelatedCaches)


def _csv_candidate(repo_root: Path, raw_path: str, label: str) -> Path:
    raw_text = normalize_text(raw_path)
    if not raw_text:
        raise ValueError(f"{label} nao informado.")

    path = Path(raw_text)
    candidate = path if path.is_absolute() else repo_root / path
    resolved = candidate.resolve(strict=False)
    _ensure_inside_repo(repo_root, resolved, label)
    if resolved.suffix.lower() != ".csv":
        raise ValueError(f"{label} deve apontar para um arquivo .csv: {resolved}")
    return resolved


def _ensure_inside_repo(repo_root: Path, path: Path, label: str) -> None:
    root = repo_root.resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError(
            f"{label} fora da raiz permitida do repositorio: {path}"
        ) from exc


def resolve_existing_csv_path(repo_root: Path, raw_path: str, label: str) -> Path:
    csv_path = _csv_candidate(repo_root, raw_path, label)
    if not csv_path.exists():
        raise FileNotFoundError(f"{label} nao encontrado: {csv_path}")
    if not csv_path.is_file():
        raise ValueError(f"{label} nao e um arquivo: {csv_path}")
    return csv_path


def resolve_optional_csv_path(
    repo_root: Path, raw_path: Optional[str], label: str
) -> tuple[Optional[Path], Optional[str]]:
    if not raw_path:
        return None, None

    csv_path = _csv_candidate(repo_root, raw_path, label)
    if not csv_path.exists():
        warning = (
            f"AVISO: {label} nao encontrado, seguindo sem custo de kit: {csv_path}"
        )
        return None, warning
    if not csv_path.is_file():
        raise ValueError(f"{label} nao e um arquivo: {csv_path}")
    return csv_path, None


def resolve_output_dir(repo_root: Path, raw_path: str) -> Path:
    raw_text = normalize_text(raw_path)
    output_dir = (
        Path(raw_text) if raw_text else Path("data/imports/bling_enriquecimento")
    )
    resolved = (
        output_dir if output_dir.is_absolute() else repo_root / output_dir
    ).resolve(strict=False)
    _ensure_inside_repo(repo_root, resolved, "Pasta de saida")
    return resolved


def resolve_run_paths(args: argparse.Namespace, repo_root: Path) -> RunPaths:
    bling_csv = resolve_existing_csv_path(repo_root, args.bling_csv, "CSV Bling")
    estrutura_csv, warning = resolve_optional_csv_path(
        repo_root, args.estrutura_csv, "CSV estrutura"
    )
    if warning:
        print(warning)
    return RunPaths(
        bling_csv=bling_csv,
        estrutura_csv=estrutura_csv,
        output_dir=resolve_output_dir(repo_root, args.output_dir),
    )


def load_db_dependencies() -> DbDependencies:
    from enriquecer_produtos_bling_db import (
        Categoria,
        Cliente,
        Departamento,
        Marca,
        Produto,
        SessionLocal,
        detect_single_tenant_id,
        find_user_id,
        get_or_create_categoria,
        get_or_create_departamento,
        get_or_create_fornecedor,
        get_or_create_marca,
    )

    return DbDependencies(
        Categoria=Categoria,
        Cliente=Cliente,
        Departamento=Departamento,
        Marca=Marca,
        Produto=Produto,
        SessionLocal=SessionLocal,
        detect_single_tenant_id=detect_single_tenant_id,
        find_user_id=find_user_id,
        get_or_create_categoria=get_or_create_categoria,
        get_or_create_departamento=get_or_create_departamento,
        get_or_create_fornecedor=get_or_create_fornecedor,
        get_or_create_marca=get_or_create_marca,
    )


def write_csv(path: Path, rows: List[Dict[str, object]], headers: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, delimiter=";")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def build_product_index(produtos: List[Any]) -> Dict[str, List[Any]]:
    by_sku: Dict[str, List[Any]] = {}
    for produto in produtos:
        key = normalize_key(produto.codigo)
        if key:
            by_sku.setdefault(key, []).append(produto)
    return by_sku


def build_context(
    db: Any,
    dbx: DbDependencies,
    args: argparse.Namespace,
    family_defaults: Dict[str, FamilyDefaults],
    kit_costs: Dict[str, float],
) -> tuple[ProcessingContext, List[Any]]:
    tenant_id = (
        UUID(args.tenant_id) if args.tenant_id else dbx.detect_single_tenant_id(db)
    )
    user_id = dbx.find_user_id(db, tenant_id)
    produtos = (
        db.query(dbx.Produto)
        .filter(
            dbx.Produto.tenant_id == tenant_id,
            dbx.Produto.codigo.isnot(None),
            dbx.Produto.codigo != "",
        )
        .all()
    )
    family_dep_ids, family_cat_ids = build_existing_classification_defaults(produtos)
    context = ProcessingContext(
        db=db,
        dbx=dbx,
        tenant_id=tenant_id,
        user_id=user_id,
        by_sku=build_product_index(produtos),
        family_defaults=family_defaults,
        family_dep_ids=family_dep_ids,
        family_cat_ids=family_cat_ids,
        kit_costs=kit_costs,
        apply_mode=args.apply,
    )
    return context, produtos


def resolve_fields(
    row: BlingRow,
    produto: Any,
    family_defaults: Dict[str, FamilyDefaults],
) -> ResolvedFields:
    family_key = build_family_key(row.nome or produto.nome)
    family_default = family_defaults.get(family_key, FamilyDefaults())
    return ResolvedFields(
        family_key=family_key,
        departamento=row.departamento or family_default.departamento,
        categoria=row.categoria or family_default.categoria,
        marca=row.marca or family_default.marca,
        fornecedor=row.fornecedor or family_default.fornecedor,
        descricao_curta=row.descricao_curta or family_default.descricao_curta,
        descricao_complementar=(
            row.descricao_complementar or family_default.descricao_complementar
        ),
        ncm=row.ncm or family_default.ncm,
        cest=row.cest or family_default.cest,
        origem=row.origem or family_default.origem,
        perfil_tributario=(row.perfil_tributario or family_default.perfil_tributario),
    )


def resolve_related_entities(
    ctx: ProcessingContext,
    fields: ResolvedFields,
    apply_mode: bool,
) -> RelatedEntities:
    dep = ctx.dbx.get_or_create_departamento(
        ctx.db,
        ctx.tenant_id,
        ctx.user_id,
        ctx.caches.departamentos,
        fields.departamento,
        apply_mode,
    )
    departamento_id = dep.id if dep else ctx.family_dep_ids.get(fields.family_key)
    cat = ctx.dbx.get_or_create_categoria(
        ctx.db,
        ctx.tenant_id,
        ctx.user_id,
        ctx.caches.categorias,
        fields.categoria,
        departamento_id,
        apply_mode,
    )
    categoria_id = cat.id if cat else ctx.family_cat_ids.get(fields.family_key)
    marca = ctx.dbx.get_or_create_marca(
        ctx.db,
        ctx.tenant_id,
        ctx.user_id,
        ctx.caches.marcas,
        fields.marca,
        apply_mode,
    )
    fornecedor = ctx.dbx.get_or_create_fornecedor(
        ctx.db,
        ctx.tenant_id,
        ctx.user_id,
        ctx.caches.fornecedores,
        fields.fornecedor,
        apply_mode,
    )
    return RelatedEntities(
        departamento_id=departamento_id,
        categoria_id=categoria_id,
        marca=marca,
        fornecedor=fornecedor,
    )


def _set_cost_if_changed(
    produto: Any,
    new_preco_custo: Optional[float],
    changes: List[str],
    apply_mode: bool,
) -> None:
    if new_preco_custo is None:
        return

    new_value = float(new_preco_custo)
    if (produto.preco_custo or 0.0) == new_value:
        return

    changes.append(f"preco_custo: {produto.preco_custo} -> {new_preco_custo}")
    if apply_mode:
        produto.preco_custo = new_value


def _set_attr_if_changed(
    produto: Any,
    attr: str,
    target: Any,
    changes: List[str],
    detail: str | Callable[[Any, Any], str],
    apply_mode: bool,
    normalizer: Optional[Callable[[Any], Any]] = None,
) -> None:
    if target is None or target == "":
        return

    current = getattr(produto, attr)
    current_value = normalizer(current) if normalizer else current
    target_value = normalizer(target) if normalizer else target
    if current_value == target_value:
        return

    changes.append(detail(current, target) if callable(detail) else detail)
    if apply_mode:
        setattr(produto, attr, target)


def collect_product_changes(
    ctx: ProcessingContext,
    row: BlingRow,
    produto: Any,
    fields: ResolvedFields,
    entities: RelatedEntities,
    sku_key: str,
    apply_mode: bool,
    count_kit: bool,
) -> tuple[List[str], int]:
    changes: List[str] = []
    new_preco_custo = row.preco_custo
    kit_cost = ctx.kit_costs.get(sku_key)
    kit_applied = 0
    if kit_cost is not None:
        new_preco_custo = kit_cost
        kit_applied = 1 if count_kit else 0

    # IMPORTANTE: nao mexer em preco_venda
    _set_cost_if_changed(produto, new_preco_custo, changes, apply_mode)
    _set_attr_if_changed(
        produto,
        "departamento_id",
        entities.departamento_id,
        changes,
        lambda current, target: f"departamento_id: {current} -> {target}",
        apply_mode,
    )
    _set_attr_if_changed(
        produto,
        "categoria_id",
        entities.categoria_id,
        changes,
        lambda current, target: f"categoria_id: {current} -> {target}",
        apply_mode,
    )
    _set_attr_if_changed(
        produto,
        "marca_id",
        entities.marca.id if entities.marca else None,
        changes,
        lambda current, target: f"marca_id: {current} -> {target}",
        apply_mode,
    )
    _set_attr_if_changed(
        produto,
        "fornecedor_id",
        entities.fornecedor.id if entities.fornecedor else None,
        changes,
        lambda current, target: f"fornecedor_id: {current} -> {target}",
        apply_mode,
    )
    _set_attr_if_changed(
        produto,
        "codigo_barras",
        only_digits(row.codigo_barras)[:13],
        changes,
        "codigo_barras atualizado",
        apply_mode,
        normalize_text,
    )
    _set_attr_if_changed(
        produto,
        "ncm",
        only_digits(fields.ncm)[:8],
        changes,
        "ncm atualizado",
        apply_mode,
        normalize_text,
    )
    _set_attr_if_changed(
        produto,
        "cest",
        only_digits(fields.cest)[:7],
        changes,
        "cest atualizado",
        apply_mode,
        normalize_text,
    )
    _set_attr_if_changed(
        produto,
        "origem",
        map_origem(fields.origem),
        changes,
        "origem atualizada",
        apply_mode,
        normalize_text,
    )
    _set_attr_if_changed(
        produto,
        "perfil_tributario",
        fields.perfil_tributario,
        changes,
        "perfil_tributario atualizado",
        apply_mode,
        normalize_text,
    )
    _set_attr_if_changed(
        produto,
        "descricao_curta",
        fields.descricao_curta,
        changes,
        "descricao_curta atualizada",
        apply_mode,
        normalize_text,
    )
    _set_attr_if_changed(
        produto,
        "descricao_completa",
        fields.descricao_complementar,
        changes,
        "descricao_completa atualizada",
        apply_mode,
        normalize_text,
    )
    return changes, kit_applied


def apply_product_row(
    ctx: ProcessingContext,
    row: BlingRow,
    produto: Any,
    apply_mode: bool,
    count_kit: bool,
) -> tuple[List[str], int]:
    sku_key = normalize_key(row.sku)
    fields = resolve_fields(row, produto, ctx.family_defaults)
    entities = resolve_related_entities(ctx, fields, apply_mode)
    return collect_product_changes(
        ctx,
        row,
        produto,
        fields,
        entities,
        sku_key,
        apply_mode,
        count_kit,
    )


def append_preview(
    rows: List[Dict[str, object]],
    row: BlingRow,
    produto: Optional[Any],
    status: str,
    detalhes: str,
) -> None:
    rows.append(
        {
            "sku": row.sku,
            "produto_id": produto.id if produto else "",
            "produto_nome": produto.nome if produto else "",
            "status": status,
            "detalhes": detalhes,
        }
    )


def append_update(
    rows: List[Dict[str, object]],
    row: BlingRow,
    produto: Any,
    detalhes: str,
) -> None:
    rows.append(
        {
            "sku": row.sku,
            "produto_id": produto.id,
            "produto_nome": produto.nome,
            "detalhes": detalhes,
        }
    )


def process_bling_row(
    ctx: ProcessingContext,
    row: BlingRow,
    preview_rows: List[Dict[str, object]],
    update_rows: List[Dict[str, object]],
    counters: ProcessingCounters,
) -> None:
    candidates = ctx.by_sku.get(normalize_key(row.sku), [])
    if not candidates:
        counters.skipped_not_found += 1
        append_preview(
            preview_rows, row, None, "SEM_MATCH", "SKU nao encontrado no sistema"
        )
        return

    if len(candidates) > 1:
        counters.skipped_multiple += 1
        detalhes = f"SKU com {len(candidates)} produtos no sistema"
        append_preview(preview_rows, row, None, "AMBIGUO", detalhes)
        return

    produto = candidates[0]
    counters.matched += 1
    changes, kit_count = apply_product_row(ctx, row, produto, ctx.apply_mode, True)
    counters.kit_cost_applied += kit_count
    detalhes = " | ".join(changes)
    status = "SEM_ALTERACAO"
    if changes:
        counters.updated += 1
        status = "ATUALIZAR" if not ctx.apply_mode else "ATUALIZADO"
        append_update(update_rows, row, produto, detalhes)
    append_preview(preview_rows, row, produto, status, detalhes)


def process_rows(
    ctx: ProcessingContext,
    bling_rows: List[BlingRow],
) -> tuple[List[Dict[str, object]], List[Dict[str, object]], ProcessingCounters]:
    counters = ProcessingCounters()
    preview_rows: List[Dict[str, object]] = []
    update_rows: List[Dict[str, object]] = []
    for row in bling_rows:
        process_bling_row(ctx, row, preview_rows, update_rows, counters)
    return preview_rows, update_rows, counters


def _find_sample_product(ctx: ProcessingContext, row: BlingRow) -> Optional[Any]:
    candidates = ctx.by_sku.get(normalize_key(row.sku), [])
    if len(candidates) != 1:
        return None
    return (
        ctx.db.query(ctx.dbx.Produto)
        .filter(ctx.dbx.Produto.id == candidates[0].id)
        .first()
    )


def reapply_sample_rows(
    ctx: ProcessingContext,
    bling_rows: List[BlingRow],
    update_rows: List[Dict[str, object]],
) -> None:
    ctx.caches.clear()
    sample_skus = {normalize_key(str(row["sku"])) for row in update_rows}
    for row in bling_rows:
        if normalize_key(row.sku) not in sample_skus:
            continue
        produto = _find_sample_product(ctx, row)
        if produto:
            apply_product_row(ctx, row, produto, True, False)


def apply_sample_limit(
    ctx: ProcessingContext,
    produtos: List[Any],
    bling_rows: List[BlingRow],
    update_rows: List[Dict[str, object]],
    sample_limit: Optional[int],
) -> List[Dict[str, object]]:
    if not sample_limit or sample_limit <= 0:
        return update_rows

    limited_rows = update_rows[:sample_limit]
    sample_ids = {
        int(row["produto_id"]) for row in limited_rows if row.get("produto_id")
    }
    for produto in produtos:
        if produto.id not in sample_ids:
            ctx.db.expire(produto)

    ctx.db.rollback()
    reapply_sample_rows(ctx, bling_rows, limited_rows)
    return limited_rows


def build_summary(
    paths: RunPaths,
    ctx: ProcessingContext,
    bling_rows: List[BlingRow],
    counters: ProcessingCounters,
    sample_limit: Optional[int],
) -> List[str]:
    return [
        f"bling_csv={paths.bling_csv}",
        f"estrutura_csv={paths.estrutura_csv or ''}",
        f"tenant_id={ctx.tenant_id}",
        f"modo_apply={ctx.apply_mode}",
        f"sample_limit={sample_limit}",
        f"total_bling={len(bling_rows)}",
        f"match_por_sku={counters.matched}",
        f"sem_match={counters.skipped_not_found}",
        f"sku_ambiguo={counters.skipped_multiple}",
        f"produtos_com_alteracoes={counters.updated}",
        f"custo_kit_aplicado={counters.kit_cost_applied}",
        "regra_preco_venda=NAO_ALTERAR",
    ]


def write_reports(
    paths: RunPaths,
    preview_rows: List[Dict[str, object]],
    update_rows: List[Dict[str, object]],
    summary: List[str],
) -> None:
    write_csv(
        paths.output_dir / "preview_enriquecimento.csv",
        preview_rows,
        ["sku", "produto_id", "produto_nome", "status", "detalhes"],
    )
    write_csv(
        paths.output_dir / "alteracoes_planejadas.csv",
        update_rows,
        ["sku", "produto_id", "produto_nome", "detalhes"],
    )
    (paths.output_dir / "resumo.txt").write_text("\n".join(summary), encoding="utf-8")


def print_summary(paths: RunPaths, summary: List[str]) -> None:
    print("Processamento concluido.")
    print(f"Relatorios: {paths.output_dir}")
    for line in summary[5:]:
        print(f"- {line}")


def run(args: argparse.Namespace) -> int:
    repo_root = Path(__file__).resolve().parents[2]
    try:
        paths = resolve_run_paths(args, repo_root)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERRO: {exc}")
        return 1

    bling_rows = load_bling_rows(paths.bling_csv, repo_root)
    kit_costs = load_kit_costs(paths.estrutura_csv, repo_root)
    family_defaults = build_family_defaults(bling_rows)
    dbx = load_db_dependencies()

    db = dbx.SessionLocal()
    try:
        ctx, produtos = build_context(db, dbx, args, family_defaults, kit_costs)
        preview_rows, update_rows, counters = process_rows(ctx, bling_rows)
        if args.apply:
            update_rows = apply_sample_limit(
                ctx,
                produtos,
                bling_rows,
                update_rows,
                args.sample_limit,
            )
            db.commit()

        summary = build_summary(paths, ctx, bling_rows, counters, args.sample_limit)
        write_reports(paths, preview_rows, update_rows, summary)
        print_summary(paths, summary)
    finally:
        db.close()

    return 0
