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

from sqlalchemy import BigInteger, create_engine, func, text
from sqlalchemy.orm import Session, sessionmaker

# Permite executar via "python scripts/..." sem depender de PYTHONPATH manual.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db import SessionLocal
from app.models import Cliente, User
from app.produtos_models import Marca, Produto, ProdutoFornecedor


PETS_MAR_MARCA = "Pets Mar"
PETS_MAR_FORNECEDOR = "PETS MAR DISTRIBUIDORA LTDA - EPP"
PETS_MAR_KEYWORDS = [
    "lolly",
    "birbo",
    "pipicat",
    "keldog",
    "kelcat",
    "land dog",
    "kidan",
]


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
    marca_nome: str


def parse_items(rows: list[dict]) -> list[CsvItem]:
    items: list[CsvItem] = []
    seen = set()
    for row in rows:
        codigo = first_not_empty(row, ["Código", "Codigo", "codigo", "CODIGO"])
        produto_nome = first_not_empty(row, ["Produto", "produto", "NOME", "Nome"])
        fornecedor_nome = first_not_empty(row, ["Fornecedor", "fornecedor", "FORNECEDOR"])
        marca_nome = first_not_empty(row, ["Marca", "marca", "MARCA"])

        if not fornecedor_nome and not marca_nome:
            continue
        if not codigo and not produto_nome:
            continue

        key = (
            codigo.strip(),
            normalize_text(produto_nome),
            normalize_text(fornecedor_nome),
            normalize_text(marca_nome),
        )
        if key in seen:
            continue
        seen.add(key)

        items.append(
            CsvItem(
                codigo=codigo.strip(),
                produto_nome=produto_nome.strip(),
                fornecedor_nome=fornecedor_nome.strip(),
                marca_nome=marca_nome.strip(),
            )
        )
    return items


def should_force_pets_mar_by_name(produto_nome: str) -> bool:
    nome = normalize_text(produto_nome)
    if not nome:
        return False
    return any(keyword in nome for keyword in PETS_MAR_KEYWORDS)


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


def sync_sequence(db: Session, table_name: str) -> None:
    allowed_tables = {"clientes", "marcas", "produto_fornecedores"}
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

        # Protege contra ambiente com sequence defasada (evita erro de id duplicado ao criar marca/fornecedor).
        sync_sequence(db, "clientes")
        sync_sequence(db, "marcas")
        sync_sequence(db, "produto_fornecedores")

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

        marcas = db.query(Marca).filter(Marca.tenant_id == tenant_id).all()
        marcas_by_name = {normalize_text(m.nome): m for m in marcas if m.nome}

        produto_ids_tenant = [p.id for p in produtos]
        fornecedor_principal_ids = dict(
            db.query(Produto.id, Produto.fornecedor_id)
            .filter(
                Produto.tenant_id == tenant_id,
                Produto.id.in_(produto_ids_tenant) if produto_ids_tenant else False,
                Produto.fornecedor_id.isnot(None),
            )
            .all()
        )

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

            marca_csv = item.marca_nome.strip()
            forcar_pets_mar = should_force_pets_mar_by_name(item.produto_nome or produto.nome)
            marca_final = PETS_MAR_MARCA if forcar_pets_mar else marca_csv

            fornecedor_final = item.fornecedor_nome.strip()
            if normalize_text(marca_final) == normalize_text(PETS_MAR_MARCA):
                fornecedor_final = PETS_MAR_FORNECEDOR

            produtos_resolvidos.append((produto, fornecedor_final, marca_final))

        produto_ids_resolvidos = {p.id for p, _, _ in produtos_resolvidos}

        pets_mar_marca = marcas_by_name.get(normalize_text(PETS_MAR_MARCA))
        produto_ids_pets_mar_nome = {p.id for p in produtos if should_force_pets_mar_by_name(p.nome)}
        produto_ids_pets_mar_marca = {
            p.id
            for p in produtos
            if pets_mar_marca and p.marca_id == pets_mar_marca.id
        }

        produto_ids = list(produto_ids_resolvidos | produto_ids_pets_mar_nome | produto_ids_pets_mar_marca)
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
        created_brands = 0
        reused_brands = 0
        updated_produto_marca_id = 0
        created_links = 0
        reactivated_links = 0
        updated_produto_fornecedor_id = 0
        updated_produto_fornecedor_pets_mar = 0

        def ensure_fornecedor(nome_fornecedor: str) -> Cliente:
            nonlocal created_suppliers, reused_suppliers
            key = normalize_text(nome_fornecedor)
            fornecedor_local = fornecedores_by_name.get(key)
            if not fornecedor_local:
                fornecedor_local = Cliente(
                    tenant_id=tenant_id,
                    user_id=user.id,
                    codigo=get_next_supplier_code(db, tenant_id),
                    tipo_cadastro="fornecedor",
                    tipo_pessoa="PJ",
                    nome=nome_fornecedor.strip(),
                    razao_social=nome_fornecedor.strip(),
                    ativo=True,
                )
                db.add(fornecedor_local)
                db.flush()
                fornecedores_by_name[key] = fornecedor_local
                created_suppliers += 1
            else:
                reused_suppliers += 1
            return fornecedor_local

        def ensure_marca(nome_marca: str) -> Marca:
            nonlocal created_brands, reused_brands
            key = normalize_text(nome_marca)
            marca_local = marcas_by_name.get(key)
            if not marca_local:
                marca_local = Marca(
                    tenant_id=tenant_id,
                    user_id=user.id,
                    nome=nome_marca.strip(),
                    ativo=True,
                )
                db.add(marca_local)
                db.flush()
                marcas_by_name[key] = marca_local
                created_brands += 1
            else:
                reused_brands += 1
            return marca_local

        def ensure_vinculo(produto: Produto, fornecedor: Cliente) -> None:
            nonlocal created_links, reactivated_links
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
            elif not existente.ativo:
                existente.ativo = True
                reactivated_links += 1

        for produto, fornecedor_nome, marca_nome in produtos_resolvidos:
            if marca_nome:
                marca = ensure_marca(marca_nome)
                if produto.marca_id != marca.id:
                    produto.marca_id = marca.id
                    updated_produto_marca_id += 1

            if not fornecedor_nome:
                continue

            fornecedor = ensure_fornecedor(fornecedor_nome)
            ensure_vinculo(produto, fornecedor)

            if not produto.fornecedor_id:
                produto.fornecedor_id = fornecedor.id
                fornecedor_principal_ids[produto.id] = fornecedor.id
                updated_produto_fornecedor_id += 1

            marca_e_pets_mar = normalize_text(marca_nome) == normalize_text(PETS_MAR_MARCA)
            if marca_e_pets_mar and produto.fornecedor_id != fornecedor.id:
                produto.fornecedor_id = fornecedor.id
                fornecedor_principal_ids[produto.id] = fornecedor.id
                updated_produto_fornecedor_pets_mar += 1

        # Regra global: qualquer produto com nome de marca Pets Mar OU marca Pets Mar recebe marca/fornecedor Pets Mar.
        pets_mar_marca_obj = ensure_marca(PETS_MAR_MARCA)
        pets_mar_fornecedor_obj = ensure_fornecedor(PETS_MAR_FORNECEDOR)

        for produto in produtos:
            marcar_por_nome = should_force_pets_mar_by_name(produto.nome)
            ja_e_marca_pets_mar = produto.marca_id == pets_mar_marca_obj.id

            if not marcar_por_nome and not ja_e_marca_pets_mar:
                continue

            if produto.marca_id != pets_mar_marca_obj.id:
                produto.marca_id = pets_mar_marca_obj.id
                updated_produto_marca_id += 1

            ensure_vinculo(produto, pets_mar_fornecedor_obj)

            if produto.fornecedor_id != pets_mar_fornecedor_obj.id:
                if produto.fornecedor_id is None:
                    updated_produto_fornecedor_id += 1
                else:
                    updated_produto_fornecedor_pets_mar += 1
                produto.fornecedor_id = pets_mar_fornecedor_obj.id
                fornecedor_principal_ids[produto.id] = pets_mar_fornecedor_obj.id

        resumo = {
            "tenant_id": str(tenant_id),
            "linhas_csv": len(items),
            "produtos_resolvidos": len(produtos_resolvidos),
            "produtos_nao_encontrados": len(nao_encontrados),
            "fornecedores_criados": created_suppliers,
            "fornecedores_reutilizados": reused_suppliers,
            "marcas_criadas": created_brands,
            "marcas_reutilizadas": reused_brands,
            "produto_marca_id_preenchido": updated_produto_marca_id,
            "vinculos_criados": created_links,
            "vinculos_reativados": reactivated_links,
            "produto_fornecedor_id_preenchido": updated_produto_fornecedor_id,
            "produto_fornecedor_id_forcado_pets_mar": updated_produto_fornecedor_pets_mar,
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