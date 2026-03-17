"""
Importa fornecedores a partir de um CSV e associa aos produtos.

Uso recomendado (DEV):
python scripts/importar_fornecedores_produtos.py \
  --csv ../Fornecedor.csv \
  --database-url postgresql+psycopg2://postgres:postgres@localhost:5433/petshop_dev \
  --dry-run

Para aplicar de fato, use --apply.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from uuid import UUID

from sqlalchemy import BigInteger, create_engine, func
from sqlalchemy.orm import Session, sessionmaker

# Permite executar via "python scripts/..." sem depender de PYTHONPATH manual.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db import SessionLocal
from app.models import Cliente, User
from app.produtos_models import Produto, ProdutoFornecedor


def normalize_text(value: Optional[str]) -> str:
    if not value:
        return ""
    text = str(value).strip().lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"\s+", " ", text)
    return text


def first_not_empty(row: dict, keys: list[str]) -> str:
    for key in keys:
        if key in row and str(row[key]).strip():
            return str(row[key]).strip()
    return ""


def load_rows(csv_path: Path) -> list[dict]:
    encodings = ["utf-8-sig", "latin-1"]
    last_error = None
    for enc in encodings:
        try:
            with csv_path.open("r", encoding=enc, newline="") as fp:
                reader = csv.DictReader(fp, delimiter=";")
                return list(reader)
        except UnicodeDecodeError as exc:
            last_error = exc
    raise RuntimeError(f"Falha ao ler CSV: {last_error}")


@dataclass
class CsvItem:
    codigo: str
    produto_nome: str
    fornecedor_nome: str


def parse_items(rows: list[dict]) -> list[CsvItem]:
    items: list[CsvItem] = []
    seen = set()
    for row in rows:
        codigo = first_not_empty(row, ["Código", "Codigo", "codigo", "CODIGO"])
        produto_nome = first_not_empty(row, ["Produto", "produto", "NOME", "Nome"])
        fornecedor_nome = first_not_empty(row, ["Fornecedor", "fornecedor", "FORNECEDOR"])

        if not fornecedor_nome:
            continue
        if not codigo and not produto_nome:
            continue

        key = (codigo.strip(), normalize_text(produto_nome), normalize_text(fornecedor_nome))
        if key in seen:
            continue
        seen.add(key)

        items.append(
            CsvItem(
                codigo=codigo.strip(),
                produto_nome=produto_nome.strip(),
                fornecedor_nome=fornecedor_nome.strip(),
            )
        )
    return items


def detect_tenant_id(db: Session, items: list[CsvItem]) -> UUID:
    codigos = [i.codigo for i in items if i.codigo]
    codigos = list(dict.fromkeys(codigos))[:2000]
    if not codigos:
        raise RuntimeError("Nao foi possivel detectar tenant automaticamente sem codigos de produto no CSV.")

    rows = (
        db.query(Produto.tenant_id, func.count(Produto.id).label("qtd"))
        .filter(Produto.codigo.in_(codigos))
        .group_by(Produto.tenant_id)
        .order_by(func.count(Produto.id).desc())
        .all()
    )
    if not rows:
        raise RuntimeError("Nenhum tenant encontrado com os codigos informados no CSV.")

    if len(rows) > 1 and rows[0].qtd == rows[1].qtd:
        raise RuntimeError(
            "Deteccao de tenant ambigua. Informe --tenant-id explicitamente."
        )

    return rows[0].tenant_id


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


def resolve_session(database_url: Optional[str]) -> Session:
    if database_url:
        engine = create_engine(database_url, pool_pre_ping=True)
        local = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
        return local()
    return SessionLocal()


def run(args: argparse.Namespace) -> None:
    csv_path = Path(args.csv).resolve()
    if not csv_path.exists():
        raise RuntimeError(f"Arquivo CSV nao encontrado: {csv_path}")

    db = resolve_session(args.database_url)
    try:
        raw_rows = load_rows(csv_path)
        items = parse_items(raw_rows)
        if not items:
            raise RuntimeError("CSV sem dados validos para processamento.")

        tenant_id = UUID(args.tenant_id) if args.tenant_id else detect_tenant_id(db, items)

        user = (
            db.query(User)
            .filter(User.tenant_id == tenant_id)
            .order_by(User.id.asc())
            .first()
        )
        if not user:
            raise RuntimeError(f"Nenhum usuario encontrado para tenant {tenant_id}.")

        produtos = db.query(Produto).filter(Produto.tenant_id == tenant_id).all()
        by_code: dict[str, list[Produto]] = defaultdict(list)
        by_name: dict[str, list[Produto]] = defaultdict(list)
        for p in produtos:
            if p.codigo:
                by_code[str(p.codigo).strip()].append(p)
            by_name[normalize_text(p.nome)].append(p)

        fornecedores = (
            db.query(Cliente)
            .filter(
                Cliente.tenant_id == tenant_id,
                Cliente.tipo_cadastro == "fornecedor",
            )
            .all()
        )
        fornecedores_by_name = {normalize_text(f.nome): f for f in fornecedores if f.nome}

        produtos_resolvidos = []
        nao_encontrados = []
        for item in items:
            produto = None
            if item.codigo and item.codigo in by_code and len(by_code[item.codigo]) == 1:
                produto = by_code[item.codigo][0]
            elif item.produto_nome:
                key_nome = normalize_text(item.produto_nome)
                if key_nome in by_name and len(by_name[key_nome]) == 1:
                    produto = by_name[key_nome][0]

            if not produto:
                nao_encontrados.append(item)
                continue

            produtos_resolvidos.append((produto, item.fornecedor_nome))

        produto_ids = list({p.id for p, _ in produtos_resolvidos})
        associacoes = (
            db.query(ProdutoFornecedor)
            .filter(
                ProdutoFornecedor.tenant_id == tenant_id,
                ProdutoFornecedor.produto_id.in_(produto_ids) if produto_ids else False,
            )
            .all()
        )
        assoc_by_pair = {(a.produto_id, a.fornecedor_id): a for a in associacoes}
        principal_por_produto = defaultdict(bool)
        for a in associacoes:
            if a.e_principal and a.ativo:
                principal_por_produto[a.produto_id] = True

        created_suppliers = 0
        reused_suppliers = 0
        created_links = 0
        reactivated_links = 0
        updated_produto_fornecedor_id = 0

        for produto, fornecedor_nome in produtos_resolvidos:
            fornecedor_key = normalize_text(fornecedor_nome)
            fornecedor = fornecedores_by_name.get(fornecedor_key)

            if not fornecedor:
                fornecedor = Cliente(
                    tenant_id=tenant_id,
                    user_id=user.id,
                    codigo=get_next_supplier_code(db, tenant_id),
                    tipo_cadastro="fornecedor",
                    tipo_pessoa="PJ",
                    nome=fornecedor_nome.strip(),
                    razao_social=fornecedor_nome.strip(),
                    ativo=True,
                )
                db.add(fornecedor)
                db.flush()
                fornecedores_by_name[fornecedor_key] = fornecedor
                created_suppliers += 1
            else:
                reused_suppliers += 1

            pair = (produto.id, fornecedor.id)
            existente = assoc_by_pair.get(pair)

            if not existente:
                novo = ProdutoFornecedor(
                    tenant_id=tenant_id,
                    produto_id=produto.id,
                    fornecedor_id=fornecedor.id,
                    ativo=True,
                    e_principal=not principal_por_produto[produto.id],
                )
                db.add(novo)
                db.flush()
                assoc_by_pair[pair] = novo
                created_links += 1
                if novo.e_principal:
                    principal_por_produto[produto.id] = True
            else:
                if not existente.ativo:
                    existente.ativo = True
                    reactivated_links += 1

            if not produto.fornecedor_id:
                produto.fornecedor_id = fornecedor.id
                updated_produto_fornecedor_id += 1

        resumo = {
            "tenant_id": str(tenant_id),
            "linhas_csv": len(items),
            "produtos_resolvidos": len(produtos_resolvidos),
            "produtos_nao_encontrados": len(nao_encontrados),
            "fornecedores_criados": created_suppliers,
            "fornecedores_reutilizados": reused_suppliers,
            "vinculos_criados": created_links,
            "vinculos_reativados": reactivated_links,
            "produto_fornecedor_id_preenchido": updated_produto_fornecedor_id,
            "modo": "APPLY" if args.apply else "DRY-RUN",
        }

        if args.apply:
            db.commit()
        else:
            db.rollback()

        print("\n=== RESUMO IMPORTACAO FORNECEDORES x PRODUTOS ===")
        for k, v in resumo.items():
            print(f"{k}: {v}")

        if nao_encontrados:
            print("\n=== AMOSTRA PRODUTOS NAO ENCONTRADOS (max 20) ===")
            for item in nao_encontrados[:20]:
                print(f"codigo={item.codigo!r} | produto={item.produto_nome!r} | fornecedor={item.fornecedor_nome!r}")

    finally:
        db.close()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Importar fornecedores e associar aos produtos via CSV")
    parser.add_argument("--csv", required=True, help="Caminho do CSV (ex.: ../Fornecedor.csv)")
    parser.add_argument(
        "--tenant-id",
        required=False,
        help="Tenant UUID. Se omitido, tenta detectar automaticamente pelos codigos da planilha.",
    )
    parser.add_argument(
        "--database-url",
        required=False,
        help="URL de conexao do banco. Se omitido, usa configuracao padrao da app.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Aplica alteracoes no banco. Sem esta flag, roda em DRY-RUN.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mantido por compatibilidade. O padrao ja e dry-run.",
    )
    return parser


if __name__ == "__main__":
    args = build_arg_parser().parse_args()
    run(args)