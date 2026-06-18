"""add ean tributario to notas entrada itens

Revision ID: pg20260604a1
Revises: pf20260603a1
Create Date: 2026-06-04 14:30:00.000000
"""

from typing import Sequence, Union
import re
import xml.etree.ElementTree as ET

from alembic import op
import sqlalchemy as sa


revision: str = "pg20260604a1"
down_revision: Union[str, None] = "pf20260603a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _codigo_barras_valido(valor: str | None) -> str:
    texto = str(valor or "").strip()
    if not texto or texto.upper().replace(" ", "") == "SEMGTIN":
        return ""
    return re.sub(r"\D", "", texto)


def _extrair_codigos_barras_por_item(xml_content: str | None) -> dict[int, dict[str, str]]:
    if not xml_content:
        return {}

    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError:
        return {}

    ns = {"nfe": "http://www.portalfiscal.inf.br/nfe"}
    codigos_por_item: dict[int, dict[str, str]] = {}

    for det in root.findall(".//nfe:det", ns):
        try:
            numero_item = int(det.get("nItem") or 0)
        except (TypeError, ValueError):
            continue

        prod = det.find("nfe:prod", ns)
        if prod is None or numero_item <= 0:
            continue

        ean = _codigo_barras_valido(prod.findtext("nfe:cEAN", default="", namespaces=ns))
        ean_tributario = _codigo_barras_valido(
            prod.findtext("nfe:cEANTrib", default="", namespaces=ns)
        )

        if ean or ean_tributario:
            codigos_por_item[numero_item] = {
                "ean": ean,
                "ean_tributario": ean_tributario,
                "principal": ean_tributario or ean,
            }

    return codigos_por_item


def _preencher_codigos_existentes() -> None:
    conn = op.get_bind()
    notas = conn.execute(
        sa.text("SELECT id, xml_content FROM notas_entrada WHERE xml_content IS NOT NULL")
    ).mappings()

    for nota in notas:
        codigos_por_item = _extrair_codigos_barras_por_item(nota["xml_content"])
        if not codigos_por_item:
            continue

        for numero_item, codigos in codigos_por_item.items():
            conn.execute(
                sa.text(
                    """
                    UPDATE notas_entrada_itens
                       SET ean_tributario = :ean_tributario
                     WHERE nota_entrada_id = :nota_id
                       AND numero_item = :numero_item
                       AND COALESCE(ean_tributario, '') = ''
                    """
                ),
                {
                    "ean_tributario": codigos["ean_tributario"] or None,
                    "nota_id": nota["id"],
                    "numero_item": numero_item,
                },
            )

            itens = conn.execute(
                sa.text(
                    """
                    SELECT produto_id
                      FROM notas_entrada_itens
                     WHERE nota_entrada_id = :nota_id
                       AND numero_item = :numero_item
                       AND produto_id IS NOT NULL
                    """
                ),
                {"nota_id": nota["id"], "numero_item": numero_item},
            ).mappings()

            for item in itens:
                produto_id = item["produto_id"]
                if codigos["ean"]:
                    conn.execute(
                        sa.text(
                            """
                            UPDATE produtos
                               SET gtin_ean = :ean
                             WHERE id = :produto_id
                               AND COALESCE(gtin_ean, '') = ''
                            """
                        ),
                        {"ean": codigos["ean"], "produto_id": produto_id},
                    )
                if codigos["ean_tributario"]:
                    conn.execute(
                        sa.text(
                            """
                            UPDATE produtos
                               SET gtin_ean_tributario = :ean_tributario
                             WHERE id = :produto_id
                               AND COALESCE(gtin_ean_tributario, '') = ''
                            """
                        ),
                        {"ean_tributario": codigos["ean_tributario"], "produto_id": produto_id},
                    )
                if codigos["principal"]:
                    conn.execute(
                        sa.text(
                            """
                            UPDATE produtos
                               SET codigo_barras = :principal
                             WHERE id = :produto_id
                               AND COALESCE(codigo_barras, '') = ''
                            """
                        ),
                        {"principal": codigos["principal"], "produto_id": produto_id},
                    )


def upgrade() -> None:
    op.add_column(
        "notas_entrada_itens",
        sa.Column("ean_tributario", sa.String(length=14), nullable=True),
    )
    op.alter_column(
        "produtos",
        "gtin_ean",
        existing_type=sa.String(length=13),
        type_=sa.String(length=20),
        existing_nullable=True,
    )
    op.alter_column(
        "produtos",
        "gtin_ean_tributario",
        existing_type=sa.String(length=13),
        type_=sa.String(length=20),
        existing_nullable=True,
    )
    _preencher_codigos_existentes()


def downgrade() -> None:
    op.alter_column(
        "produtos",
        "gtin_ean_tributario",
        existing_type=sa.String(length=20),
        type_=sa.String(length=13),
        existing_nullable=True,
    )
    op.alter_column(
        "produtos",
        "gtin_ean",
        existing_type=sa.String(length=20),
        type_=sa.String(length=13),
        existing_nullable=True,
    )
    op.drop_column("notas_entrada_itens", "ean_tributario")
