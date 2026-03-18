#!/usr/bin/env python
"""Cria no sistema os produtos do SimplesVet que ficaram sem match.

Fluxo seguro:
1) Rodar sem --apply para gerar preview
2) Conferir os relatórios em backend/reports/simplesvet_match/cadastro_missing
3) Rodar com --apply para criar de fato os produtos faltantes
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from uuid import UUID

from sqlalchemy import BigInteger, create_engine, func, text
from sqlalchemy.orm import Session, sessionmaker

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db import SessionLocal
from app.models import Cliente, User
from app.produtos_models import Categoria, Marca, Produto, ProdutoFornecedor


@dataclass
class ProdutoOrigem:
    codigo: str
    nome: str
    grupo: str
    marca: str
    unidade: str
    codigo_barras: Optional[str]
    fornecedor: str
    custo: Optional[float]
    venda: Optional[float]
    minimo: Optional[float]
    maximo: Optional[float]
    controlar_estoque: bool
    situacao: str


def normalize_text(value: Optional[str]) -> str:
    if not value:
        return ""
    text = str(value).strip().lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text)


def parse_decimal(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def parse_bool_sim(value: Optional[str]) -> bool:
    return normalize_text(value) == "sim"


def clean_barcode(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if "e+" in text.lower():
        return None
    digits = re.sub(r"\D", "", text)
    if not digits:
        return None
    return digits[:20]


def load_rows(csv_path: Path) -> list[dict]:
    encodings = ["utf-8-sig", "latin-1"]
    last_error = None
    for encoding in encodings:
        try:
            with csv_path.open("r", encoding=encoding, newline="") as handle:
                return list(csv.DictReader(handle, delimiter=";"))
        except UnicodeDecodeError as exc:
            last_error = exc
    raise RuntimeError(f"Falha ao ler CSV: {last_error}")


def resolve_session(database_url: Optional[str]) -> Session:
    if database_url:
        engine = create_engine(database_url, pool_pre_ping=True)
        local = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
        return local()
    return SessionLocal()


def sync_sequence(db: Session, table_name: str) -> None:
    allowed_tables = {"clientes", "marcas", "produtos", "produto_fornecedores"}
    if table_name not in allowed_tables:
        raise RuntimeError(f"Tabela nao permitida para sync de sequence: {table_name}")

    db.execute(
        text(
            f"""
            SELECT setval(
              pg_get_serial_sequence('{table_name}', 'id'),
              COALESCE((SELECT MAX(id) FROM {table_name}), 1),
              true
            )
            """
        )
    )


def get_next_supplier_code(db: Session, tenant_id: UUID) -> str:
    last_code = (
        db.query(func.max(Cliente.codigo.cast(BigInteger)))
        .filter(
            Cliente.tenant_id == tenant_id,
            Cliente.codigo.op("~")("^[0-9]+$"),
        )
        .scalar()
    )
    next_code = (last_code or 10000) + 1
    return str(next_code)


def detect_single_tenant_id(db: Session) -> UUID:
    tenants = [row[0] for row in db.query(User.tenant_id).distinct().all() if row[0]]
    if len(tenants) != 1:
        raise RuntimeError("Ambiente com mais de um tenant. Informe --tenant-id explicitamente.")
    return tenants[0]


def load_missing_codes(csv_path: Path) -> list[str]:
    rows = load_rows(csv_path)
    codes: list[str] = []
    for row in rows:
      code = str(row.get("codigo") or "").strip()
      if code:
          codes.append(code)
    return codes


def load_source_products(csv_path: Path, target_codes: set[str]) -> dict[str, ProdutoOrigem]:
    products: dict[str, ProdutoOrigem] = {}
    for row in load_rows(csv_path):
        codigo = str(row.get("Código") or "").strip()
        if not codigo or codigo not in target_codes:
            continue

        products[codigo] = ProdutoOrigem(
            codigo=codigo,
            nome=str(row.get("Produto") or "").strip(),
            grupo=str(row.get("Grupo") or "").strip(),
            marca=str(row.get("Marca") or "").strip(),
            unidade=str(row.get("Unidade") or "").strip() or "UN",
            codigo_barras=clean_barcode(row.get("Código Barra")),
            fornecedor=str(row.get("Fornecedor") or "").strip(),
            custo=parse_decimal(row.get("Custo")),
            venda=parse_decimal(row.get("Venda")),
            minimo=parse_decimal(row.get("Minimo")),
            maximo=parse_decimal(row.get("Máximo")),
            controlar_estoque=parse_bool_sim(row.get("Controla Estoque")),
            situacao=str(row.get("Situação tributária") or row.get("Lista de Preço") or "").strip(),
        )
    return products


def ensure_reports_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_csv(path: Path, rows: list[dict], headers: list[str]) -> None:
    ensure_reports_dir(path.parent)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, delimiter=";")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_summary(path: Path, content: str) -> None:
    ensure_reports_dir(path.parent)
    path.write_text(content, encoding="utf-8")


def run(args: argparse.Namespace) -> None:
    report_csv = Path(args.report_csv).resolve()
    source_csv = Path(args.source_csv).resolve()

    if not report_csv.exists():
        raise RuntimeError(f"Arquivo de sem match nao encontrado: {report_csv}")
    if not source_csv.exists():
        raise RuntimeError(f"Arquivo origem nao encontrado: {source_csv}")

    missing_codes = load_missing_codes(report_csv)
    if not missing_codes:
        raise RuntimeError("Nenhum codigo encontrado no CSV de sem match.")

    source_products = load_source_products(source_csv, set(missing_codes))
    missing_in_source = [code for code in missing_codes if code not in source_products]
    if missing_in_source:
        raise RuntimeError(
            "Nao foi possivel localizar todos os codigos no arquivo origem: " + ", ".join(missing_in_source)
        )

    output_dir = Path(args.output_dir).resolve()
    db = resolve_session(args.database_url)
    created_rows: list[dict] = []
    skipped_rows: list[dict] = []

    try:
        tenant_id = UUID(args.tenant_id) if args.tenant_id else detect_single_tenant_id(db)

        user = (
            db.query(User)
            .filter(User.tenant_id == tenant_id)
            .order_by(User.id.asc())
            .first()
        )
        if not user:
            raise RuntimeError(f"Nenhum usuario encontrado para tenant {tenant_id}.")

        sync_sequence(db, "clientes")
        sync_sequence(db, "marcas")
        sync_sequence(db, "produtos")
        sync_sequence(db, "produto_fornecedores")

        existing_products = {
            str(produto.codigo).strip(): produto
            for produto in db.query(Produto).filter(Produto.tenant_id == tenant_id).all()
            if produto.codigo
        }
        fornecedores_by_name = {
            normalize_text(fornecedor.nome): fornecedor
            for fornecedor in db.query(Cliente)
            .filter(Cliente.tenant_id == tenant_id, Cliente.tipo_cadastro == "fornecedor")
            .all()
            if fornecedor.nome
        }
        marcas_by_name = {
            normalize_text(marca.nome): marca
            for marca in db.query(Marca).filter(Marca.tenant_id == tenant_id).all()
            if marca.nome
        }
        categorias_by_name = {
            normalize_text(categoria.nome): categoria
            for categoria in db.query(Categoria).filter(Categoria.tenant_id == tenant_id).all()
            if categoria.nome
        }

        def ensure_fornecedor(nome_fornecedor: str) -> Optional[Cliente]:
            if not nome_fornecedor:
                return None
            key = normalize_text(nome_fornecedor)
            fornecedor = fornecedores_by_name.get(key)
            if fornecedor:
                return fornecedor

            fornecedor = Cliente(
                tenant_id=tenant_id,
                user_id=user.id,
                codigo=get_next_supplier_code(db, tenant_id),
                tipo_cadastro="fornecedor",
                tipo_pessoa="PJ",
                nome=nome_fornecedor,
                razao_social=nome_fornecedor,
                ativo=True,
            )
            db.add(fornecedor)
            db.flush()
            fornecedores_by_name[key] = fornecedor
            return fornecedor

        def ensure_marca(nome_marca: str) -> Optional[Marca]:
            if not nome_marca:
                return None
            key = normalize_text(nome_marca)
            marca = marcas_by_name.get(key)
            if marca:
                return marca

            marca = Marca(
                tenant_id=tenant_id,
                user_id=user.id,
                nome=nome_marca,
                ativo=True,
            )
            db.add(marca)
            db.flush()
            marcas_by_name[key] = marca
            return marca

        for codigo in missing_codes:
            origem = source_products[codigo]
            if codigo in existing_products:
                skipped_rows.append(
                    {
                        "codigo": codigo,
                        "nome": origem.nome,
                        "motivo": "JA_EXISTE_NO_SISTEMA",
                    }
                )
                continue

            fornecedor = ensure_fornecedor(origem.fornecedor)
            marca = ensure_marca(origem.marca)
            categoria = categorias_by_name.get(normalize_text(origem.grupo))

            preco_venda = origem.venda if origem.venda and origem.venda > 0 else None
            if preco_venda is None:
                skipped_rows.append(
                    {
                        "codigo": codigo,
                        "nome": origem.nome,
                        "motivo": "SEM_PRECO_VENDA_VALIDO",
                    }
                )
                continue

            produto = Produto(
                tenant_id=tenant_id,
                user_id=user.id,
                codigo=origem.codigo,
                nome=origem.nome,
                tipo="produto",
                situacao=True,
                ativo=True,
                tipo_produto="SIMPLES",
                categoria_id=categoria.id if categoria else None,
                marca_id=marca.id if marca else None,
                fornecedor_id=fornecedor.id if fornecedor else None,
                preco_custo=origem.custo or 0,
                preco_venda=preco_venda,
                codigo_barras=origem.codigo_barras,
                estoque_atual=0,
                estoque_fisico=0,
                estoque_minimo=origem.minimo or 0,
                estoque_maximo=origem.maximo or 0,
                unidade=origem.unidade or "UN",
                controle_lote=True,
            )
            db.add(produto)
            db.flush()

            if fornecedor:
                db.add(
                    ProdutoFornecedor(
                        tenant_id=tenant_id,
                        produto_id=produto.id,
                        fornecedor_id=fornecedor.id,
                        preco_custo=origem.custo,
                        e_principal=True,
                        ativo=True,
                    )
                )

            existing_products[codigo] = produto
            created_rows.append(
                {
                    "codigo": origem.codigo,
                    "nome": origem.nome,
                    "categoria": categoria.nome if categoria else "",
                    "marca": marca.nome if marca else "",
                    "fornecedor": fornecedor.nome if fornecedor else "",
                    "preco_custo": origem.custo or 0,
                    "preco_venda": preco_venda,
                    "estoque_inicial": 0,
                    "modo": "apply" if args.apply else "preview",
                }
            )

        if args.apply:
            db.commit()
        else:
            db.rollback()

        write_csv(
            output_dir / "produtos_para_criar.csv",
            created_rows,
            ["codigo", "nome", "categoria", "marca", "fornecedor", "preco_custo", "preco_venda", "estoque_inicial", "modo"],
        )
        write_csv(
            output_dir / "produtos_pulados.csv",
            skipped_rows,
            ["codigo", "nome", "motivo"],
        )
        write_summary(
            output_dir / "resumo.txt",
            "\n".join(
                [
                    f"report_csv={report_csv}",
                    f"source_csv={source_csv}",
                    f"tenant_id={tenant_id}",
                    f"modo_apply={args.apply}",
                    f"produtos_previstos_para_criar={len(created_rows)}",
                    f"produtos_pulados={len(skipped_rows)}",
                ]
            ),
        )

        print(f"Tenant: {tenant_id}")
        print(f"Modo apply: {args.apply}")
        print(f"Produtos previstos para criar: {len(created_rows)}")
        print(f"Produtos pulados: {len(skipped_rows)}")
        print(f"Relatorios em: {output_dir}")
    finally:
        db.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cria produtos do SimplesVet que ficaram sem match")
    parser.add_argument(
        "--report-csv",
        default="backend/reports/simplesvet_match/producao/simplesvet_sem_match.csv",
        help="CSV com os produtos sem match gerado no preview",
    )
    parser.add_argument(
        "--source-csv",
        default="Fornecedor.csv",
        help="CSV completo com dados dos produtos para cadastro",
    )
    parser.add_argument(
        "--output-dir",
        default="backend/reports/simplesvet_match/cadastro_missing",
        help="Pasta de saída dos relatórios",
    )
    parser.add_argument("--tenant-id", default="", help="Tenant alvo (UUID)")
    parser.add_argument("--database-url", default="", help="Database URL opcional")
    parser.add_argument("--apply", action="store_true", help="Cria de fato os produtos no banco")
    return parser


if __name__ == "__main__":
    run(build_parser().parse_args())