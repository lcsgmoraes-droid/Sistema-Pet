"""Conversao controlada de clientes, produtos e estoque do JN Moura.

O arquivo exportado permanece fora do Git. Esta carga nao toca vendas, contas,
usuarios ou dados cadastrais do tenant de destino.
"""

from __future__ import annotations

import csv
import hashlib
import json
import unicodedata
from collections import Counter
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import UUID

from sqlalchemy import func, select

import app.db.base  # noqa: F401 - registra modelos relacionados
from app.models_cadastros import Cliente
from app.produtos_catalogo_models import Categoria, Produto
from importar_simplesvet_utils import gtin_valido


CLIENT_COLUMNS = {
    "source_id",
    "nome",
    "tipo_pessoa",
    "documento",
    "telefone",
    "telefone2",
    "celular",
    "email",
    "endereco",
    "numero",
    "bairro",
    "cep",
    "cidade",
    "uf",
    "inativo",
    "data_nascimento",
    "data_cadastro",
}
PRODUCT_COLUMNS = {
    "source_id",
    "nome",
    "grupo_id",
    "grupo_nome",
    "codigo_barras",
    "preco_venda",
    "preco_custo",
    "unidade",
    "inativo",
    "servico",
    "ncm",
    "estoque_minimo",
    "estoque_maximo",
    "estoque_raw",
    "data_cadastro",
}
GENERIC_NAMES = {
    "VARIADOS",
    "DIVERSOS",
    "PRODUTO GENERICO",
    "CLIENTE GENERICO",
    "CONSUMIDOR FINAL",
    "CLIENTE PADRAO",
    "SEM CADASTRO",
}
EXPECTED_FILES = {
    "clientes.csv": CLIENT_COLUMNS,
    "fornecedores.csv": CLIENT_COLUMNS,
    "produtos.csv": PRODUCT_COLUMNS,
}


class JnmImportError(ValueError):
    pass


def normalize_cnpj(value: object) -> str:
    return "".join(char for char in str(value or "") if char.isdigit())


def _normalized_name(value: str) -> str:
    folded = unicodedata.normalize("NFKD", value)
    without_accents = "".join(
        char for char in folded if not unicodedata.combining(char)
    )
    return " ".join(without_accents.upper().split())


def is_generic_name(value: str) -> bool:
    return _normalized_name(value) in GENERIC_NAMES


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_csv(path: Path, required: set[str]) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if set(reader.fieldnames or ()) != required:
            raise JnmImportError(f"Colunas inesperadas em {path.name}")
        rows = list(reader)
    if not rows:
        raise JnmImportError(f"Arquivo vazio: {path.name}")
    return rows


def load_source(
    source_dir: Path, expected_cnpj: str, expected_backup_sha256: str
) -> tuple[dict, dict[str, list[dict[str, str]]]]:
    source_dir = source_dir.resolve()
    manifest_path = source_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        manifest.get("schema_version") != 1
        or manifest.get("source_system") != "jn_moura"
    ):
        raise JnmImportError("Manifesto de origem invalido")
    if normalize_cnpj(manifest.get("source_cnpj")) != normalize_cnpj(expected_cnpj):
        raise JnmImportError("CNPJ de origem divergente")
    if manifest.get("backup_sha256", "").lower() != expected_backup_sha256.lower():
        raise JnmImportError("Hash do backup original divergente")
    if set(manifest.get("files", {})) != set(EXPECTED_FILES):
        raise JnmImportError("Conjunto de arquivos inesperado")
    source = {}
    for filename, columns in EXPECTED_FILES.items():
        path = source_dir / filename
        recorded = manifest["files"][filename]
        if path.stat().st_size != recorded.get("bytes") or _sha256_file(
            path
        ) != recorded.get("sha256"):
            raise JnmImportError(f"Arquivo alterado desde a exportacao: {filename}")
        rows = _read_csv(path, columns)
        if len(rows) != recorded.get("rows"):
            raise JnmImportError(f"Contagem alterada: {filename}")
        source[filename] = rows
    return manifest, source


def _clean(value: str | None, *, max_length: int | None = None) -> str | None:
    clean = " ".join(str(value or "").strip().split())
    if not clean:
        return None
    if max_length and len(clean) > max_length:
        raise JnmImportError("Texto de origem excede o limite do cadastro")
    return clean


def _amount(value: str | None, *, allow_negative: bool = False) -> Decimal:
    try:
        amount = Decimal(str(value or "0").strip() or "0")
    except InvalidOperation as exc:
        raise JnmImportError("Numero invalido na origem") from exc
    if not amount.is_finite() or (amount < 0 and not allow_negative):
        raise JnmImportError("Valor monetario ou limite de estoque invalido")
    return amount


def _date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise JnmImportError("Data invalida na origem") from exc


def _source_id(row: dict[str, str]) -> str:
    value = (row.get("source_id") or "").strip()
    if not value.isdigit() or len(value) > 20:
        raise JnmImportError("Identificador da origem invalido")
    return value


def prepare_rows(
    source: dict[str, list[dict[str, str]]],
) -> tuple[list[dict], list[dict], dict]:
    clients: list[dict] = []
    products: list[dict] = []
    metrics = Counter()
    person_ids: set[str] = set()
    product_ids: set[str] = set()
    barcode_counts = Counter(
        _clean(row["codigo_barras"], max_length=20)
        for row in source["produtos.csv"]
        if not is_generic_name(row["nome"])
    )

    for filename, kind, generic_metric in (
        ("clientes.csv", "cliente", "clientes_genericos_excluidos"),
        ("fornecedores.csv", "fornecedor", "fornecedores_genericos_excluidos"),
    ):
        for row in source[filename]:
            source_id = _source_id(row)
            record_id = f"F-{source_id}" if kind == "fornecedor" else source_id
            if record_id in person_ids:
                raise JnmImportError("Codigo de cadastro repetido na origem")
            person_ids.add(record_id)
            name = _clean(row["nome"], max_length=255)
            if not name:
                raise JnmImportError("Cadastro sem nome na origem")
            if is_generic_name(name):
                metrics[generic_metric] += 1
                continue
            person_type = "PJ" if row["tipo_pessoa"].upper() == "J" else "PF"
            doc = normalize_cnpj(row["documento"])
            clients.append(
                {
                    "codigo": record_id,
                    "tipo_cadastro": kind,
                    "nome": name,
                    "tipo_pessoa": person_type,
                    "cpf": doc if person_type == "PF" and len(doc) == 11 else None,
                    "cnpj": doc if person_type == "PJ" and len(doc) == 14 else None,
                    "telefone": _clean(
                        row["telefone"] or row["telefone2"], max_length=50
                    ),
                    "celular": _clean(row["celular"], max_length=50),
                    "email": _clean(row["email"], max_length=255),
                    "endereco": _clean(row["endereco"]),
                    "numero": _clean(row["numero"], max_length=20),
                    "bairro": _clean(row["bairro"], max_length=100),
                    "cep": _clean(row["cep"], max_length=10),
                    "cidade": _clean(row["cidade"], max_length=100),
                    "estado": _clean(row["uf"], max_length=2),
                    "ativo": row["inativo"].upper() != "S",
                    "data_nascimento": _date(row["data_nascimento"]),
                    "created_at": _date(row["data_cadastro"]),
                }
            )

    for row in source["produtos.csv"]:
        source_id = _source_id(row)
        if source_id in product_ids:
            raise JnmImportError("Codigo de produto repetido na origem")
        product_ids.add(source_id)
        name = _clean(row["nome"], max_length=200)
        if not name:
            raise JnmImportError("Produto sem nome na origem")
        if is_generic_name(name):
            metrics["produtos_genericos_excluidos"] += 1
            continue
        service = row["servico"].upper() == "S"
        raw_stock = _amount(row["estoque_raw"], allow_negative=True)
        if raw_stock < 0:
            metrics["estoques_negativos_zerados"] += 1
        stock = Decimal("0") if service or raw_stock < 0 else raw_stock
        barcode = _clean(row["codigo_barras"], max_length=20)
        if barcode and barcode_counts[barcode] > 1:
            barcode = None
            metrics["codigos_barras_duplicados_limpos"] += 1
        ncm = normalize_cnpj(row["ncm"])
        products.append(
            {
                "codigo": source_id,
                "nome": name,
                "tipo": "servico" if service else "produto",
                "situacao": row["inativo"].upper() != "S",
                "grupo_nome": _clean(row["grupo_nome"], max_length=100),
                "codigo_barras": barcode,
                "gtin_ean": barcode if gtin_valido(barcode) else None,
                "preco_venda": _amount(row["preco_venda"]),
                "preco_custo": _amount(row["preco_custo"]),
                "unidade": _clean(row["unidade"], max_length=10) or "UN",
                "ncm": ncm if len(ncm) == 8 else None,
                "estoque_atual": stock,
                "estoque_minimo": _amount(row["estoque_minimo"]),
                "estoque_maximo": _amount(row["estoque_maximo"]),
                "created_at": _date(row["data_cadastro"]),
            }
        )

    metrics.update(
        {
            "clientes_origem": len(source["clientes.csv"]),
            "clientes_importaveis": sum(
                c["tipo_cadastro"] == "cliente" for c in clients
            ),
            "fornecedores_origem": len(source["fornecedores.csv"]),
            "fornecedores_importaveis": sum(
                c["tipo_cadastro"] == "fornecedor" for c in clients
            ),
            "produtos_origem": len(source["produtos.csv"]),
            "produtos_importaveis": len(products),
            "categorias_importaveis": len(
                {p["grupo_nome"].casefold() for p in products if p["grupo_nome"]}
            ),
            "produtos_com_estoque_positivo": sum(
                p["estoque_atual"] > 0 for p in products
            ),
        }
    )
    metrics["saldo_estoque_importavel"] = str(
        sum((p["estoque_atual"] for p in products), Decimal("0"))
    )
    return clients, products, dict(metrics)


def insert_catalog(
    db, *, tenant_id: str, user_id: int, clients: list[dict], products: list[dict]
) -> dict:
    tenant_uuid = UUID(tenant_id)
    if db.scalar(
        select(func.count())
        .select_from(Cliente)
        .where(Cliente.tenant_id == tenant_uuid)
    ):
        raise JnmImportError("Destino ja possui clientes")
    if db.scalar(
        select(func.count())
        .select_from(Produto)
        .where(Produto.tenant_id == tenant_uuid)
    ):
        raise JnmImportError("Destino ja possui produtos")

    categories = {
        category.nome.casefold(): category
        for category in db.scalars(
            select(Categoria).where(Categoria.tenant_id == tenant_uuid)
        ).all()
    }
    created_categories = 0
    for product in products:
        name = product["grupo_nome"]
        if name and name.casefold() not in categories:
            category = Categoria(
                tenant_id=tenant_uuid, user_id=user_id, nome=name, ativo=True
            )
            db.add(category)
            categories[name.casefold()] = category
            created_categories += 1
    db.flush()

    for row in clients:
        db.add(
            Cliente(
                tenant_id=tenant_uuid,
                user_id=user_id,
                origem_cliente="jn_moura",
                **{key: value for key, value in row.items() if value is not None},
            )
        )
    db.flush()
    for row in products:
        values = {
            key: value
            for key, value in row.items()
            if key != "grupo_nome" and value is not None
        }
        stock = float(values["estoque_atual"])
        for key in (
            "preco_venda",
            "preco_custo",
            "estoque_atual",
            "estoque_minimo",
            "estoque_maximo",
        ):
            values[key] = float(values[key])
        db.add(
            Produto(
                tenant_id=tenant_uuid,
                user_id=user_id,
                categoria_id=categories[row["grupo_nome"].casefold()].id
                if row["grupo_nome"]
                else None,
                estoque_fisico=stock,
                **values,
            )
        )
    db.flush()
    return {
        "categorias_criadas": created_categories,
        "clientes_criados": sum(c["tipo_cadastro"] == "cliente" for c in clients),
        "fornecedores_criados": sum(
            c["tipo_cadastro"] == "fornecedor" for c in clients
        ),
        "produtos_criados": len(products),
    }
