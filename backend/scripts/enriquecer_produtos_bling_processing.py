"""Orquestracao do enriquecimento Bling."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, List, Optional
from uuid import UUID

from enriquecer_produtos_bling_classification import (
    build_existing_classification_defaults,
    build_family_defaults,
)
from enriquecer_produtos_bling_loaders import load_bling_rows, load_kit_costs
from enriquecer_produtos_bling_types import FamilyDefaults
from enriquecer_produtos_bling_utils import (
    build_family_key,
    map_origem,
    normalize_key,
    normalize_text,
    only_digits,
)


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
            print(
                f"AVISO: CSV estrutura nao encontrado, seguindo sem custo de kit: {estrutura_csv}"
            )
            estrutura_csv = None

    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = repo_root / output_dir

    bling_rows = load_bling_rows(bling_csv)
    kit_costs = load_kit_costs(estrutura_csv)
    family_defaults = build_family_defaults(bling_rows)

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

    db = SessionLocal()
    try:
        tenant_id = (
            UUID(args.tenant_id) if args.tenant_id else detect_single_tenant_id(db)
        )
        user_id = find_user_id(db, tenant_id)

        produtos = (
            db.query(Produto)
            .filter(
                Produto.tenant_id == tenant_id,
                Produto.codigo.isnot(None),
                Produto.codigo != "",
            )
            .all()
        )
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
        family_dep_ids, family_cat_ids = build_existing_classification_defaults(
            produtos
        )

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
            resolved_descricao_curta = (
                row.descricao_curta or family_default.descricao_curta
            )
            resolved_descricao_complementar = (
                row.descricao_complementar or family_default.descricao_complementar
            )
            resolved_ncm = row.ncm or family_default.ncm
            resolved_cest = row.cest or family_default.cest
            resolved_origem = row.origem or family_default.origem
            resolved_perfil_tributario = (
                row.perfil_tributario or family_default.perfil_tributario
            )

            dep = get_or_create_departamento(
                db, tenant_id, user_id, dep_cache, resolved_departamento, args.apply
            )
            inferred_dep_id = dep.id if dep else family_dep_ids.get(family_key)
            cat = get_or_create_categoria(
                db,
                tenant_id,
                user_id,
                cat_cache,
                resolved_categoria,
                inferred_dep_id,
                args.apply,
            )
            inferred_cat_id = cat.id if cat else family_cat_ids.get(family_key)
            marca = get_or_create_marca(
                db, tenant_id, user_id, marca_cache, resolved_marca, args.apply
            )
            forn = get_or_create_fornecedor(
                db, tenant_id, user_id, forn_cache, resolved_fornecedor, args.apply
            )

            new_preco_custo = row.preco_custo
            kit_cost = kit_costs.get(sku_key)
            if kit_cost is not None:
                new_preco_custo = kit_cost
                kit_cost_applied += 1

            changes: List[str] = []

            # IMPORTANTE: nao mexer em preco_venda
            if new_preco_custo is not None and (produto.preco_custo or 0.0) != float(
                new_preco_custo
            ):
                changes.append(
                    f"preco_custo: {produto.preco_custo} -> {new_preco_custo}"
                )
                if args.apply:
                    produto.preco_custo = float(new_preco_custo)

            target_departamento_id = dep.id if dep else inferred_dep_id
            if (
                target_departamento_id
                and produto.departamento_id != target_departamento_id
            ):
                changes.append(
                    f"departamento_id: {produto.departamento_id} -> {target_departamento_id}"
                )
                if args.apply:
                    produto.departamento_id = target_departamento_id

            target_categoria_id = cat.id if cat else inferred_cat_id
            if target_categoria_id and produto.categoria_id != target_categoria_id:
                changes.append(
                    f"categoria_id: {produto.categoria_id} -> {target_categoria_id}"
                )
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
            if (
                codigo_barras_digits
                and normalize_text(produto.codigo_barras) != codigo_barras_digits
            ):
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

            if (
                resolved_perfil_tributario
                and normalize_text(produto.perfil_tributario)
                != resolved_perfil_tributario
            ):
                changes.append("perfil_tributario atualizado")
                if args.apply:
                    produto.perfil_tributario = resolved_perfil_tributario

            if (
                resolved_descricao_curta
                and normalize_text(produto.descricao_curta) != resolved_descricao_curta
            ):
                changes.append("descricao_curta atualizada")
                if args.apply:
                    produto.descricao_curta = resolved_descricao_curta

            if (
                resolved_descricao_complementar
                and normalize_text(produto.descricao_completa)
                != resolved_descricao_complementar
            ):
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
                sample_ids = {
                    int(r["produto_id"]) for r in update_rows if r.get("produto_id")
                }
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
                    produto = (
                        db.query(Produto).filter(Produto.id == candidates[0].id).first()
                    )
                    if not produto:
                        continue

                    family_key = build_family_key(row.nome or produto.nome)
                    family_default = family_defaults.get(family_key, FamilyDefaults())

                    resolved_departamento = (
                        row.departamento or family_default.departamento
                    )
                    resolved_categoria = row.categoria or family_default.categoria
                    resolved_marca = row.marca or family_default.marca
                    resolved_fornecedor = row.fornecedor or family_default.fornecedor
                    resolved_descricao_curta = (
                        row.descricao_curta or family_default.descricao_curta
                    )
                    resolved_descricao_complementar = (
                        row.descricao_complementar
                        or family_default.descricao_complementar
                    )
                    resolved_ncm = row.ncm or family_default.ncm
                    resolved_cest = row.cest or family_default.cest
                    resolved_origem = row.origem or family_default.origem
                    resolved_perfil_tributario = (
                        row.perfil_tributario or family_default.perfil_tributario
                    )

                    dep = get_or_create_departamento(
                        db, tenant_id, user_id, dep_cache, resolved_departamento, True
                    )
                    inferred_dep_id = dep.id if dep else family_dep_ids.get(family_key)
                    cat = get_or_create_categoria(
                        db,
                        tenant_id,
                        user_id,
                        cat_cache,
                        resolved_categoria,
                        inferred_dep_id,
                        True,
                    )
                    inferred_cat_id = cat.id if cat else family_cat_ids.get(family_key)
                    marca = get_or_create_marca(
                        db, tenant_id, user_id, marca_cache, resolved_marca, True
                    )
                    forn = get_or_create_fornecedor(
                        db, tenant_id, user_id, forn_cache, resolved_fornecedor, True
                    )

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
