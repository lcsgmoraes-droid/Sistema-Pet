"""cria catalogo mestre global de produtos

Revision ID: zxn20260829a1
Revises: zxm20260829a1
Create Date: 2026-08-29
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "zxn20260829a1"
down_revision = "zxm20260829a1"
branch_labels = None
depends_on = None


def _has_table(table_name: str, *, offline_default: bool) -> bool:
    """Permite validar/gerar SQL offline sem perder idempotencia online."""

    try:
        return sa.inspect(op.get_bind()).has_table(table_name)
    except sa.exc.NoInspectionAvailable:
        return offline_default


def upgrade() -> None:
    if not _has_table("catalogo_mestre_produtos", offline_default=False):
        op.create_table(
            "catalogo_mestre_produtos",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column(
                "status",
                sa.String(length=30),
                nullable=False,
                server_default="em_curadoria",
            ),
            sa.Column(
                "ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")
            ),
            sa.Column(
                "fonte_primaria",
                sa.String(length=50),
                nullable=False,
                server_default="tenant_produto",
            ),
            sa.Column(
                "origem_tenant_id",
                postgresql.UUID(as_uuid=True),
                nullable=False,
            ),
            sa.Column("origem_produto_id", sa.Integer(), nullable=False),
            sa.Column(
                "origem_atualizado_em", sa.DateTime(timezone=True), nullable=True
            ),
            sa.Column("codigo_origem", sa.String(length=100), nullable=True),
            sa.Column("nome", sa.String(length=500), nullable=False),
            sa.Column(
                "tipo_catalogo",
                sa.String(length=30),
                nullable=False,
                server_default="outro",
            ),
            sa.Column("gtin", sa.String(length=14), nullable=True),
            sa.Column(
                "gtin_status",
                sa.String(length=30),
                nullable=False,
                server_default="ausente",
            ),
            sa.Column("codigos_barras", sa.JSON(), nullable=True),
            sa.Column("marca", sa.String(length=255), nullable=True),
            sa.Column("categoria", sa.String(length=255), nullable=True),
            sa.Column("departamento", sa.String(length=255), nullable=True),
            sa.Column("subcategoria", sa.String(length=255), nullable=True),
            sa.Column("descricao_curta", sa.Text(), nullable=True),
            sa.Column("descricao_completa", sa.Text(), nullable=True),
            sa.Column("tags", sa.JSON(), nullable=True),
            sa.Column("unidade", sa.String(length=20), nullable=True),
            sa.Column("ncm", sa.String(length=10), nullable=True),
            sa.Column("cest", sa.String(length=10), nullable=True),
            sa.Column("origem_mercadoria", sa.String(length=2), nullable=True),
            sa.Column("dados_fiscais_referencia", sa.JSON(), nullable=True),
            sa.Column("dados_fisicos", sa.JSON(), nullable=True),
            sa.Column("dados_racao", sa.JSON(), nullable=True),
            sa.Column("registro_mapa", sa.String(length=120), nullable=True),
            sa.Column("principio_ativo", sa.Text(), nullable=True),
            sa.Column("fabricante", sa.String(length=255), nullable=True),
            sa.Column("forma_farmaceutica", sa.String(length=150), nullable=True),
            sa.Column("especies_indicadas", sa.JSON(), nullable=True),
            sa.Column("bula_url", sa.String(length=1000), nullable=True),
            sa.Column("bula_conteudo", sa.JSON(), nullable=True),
            sa.Column("posologia", sa.JSON(), nullable=True),
            sa.Column(
                "conteudo_veterinario_status",
                sa.String(length=30),
                nullable=False,
                server_default="nao_verificado",
            ),
            sa.Column(
                "imagem_quantidade", sa.Integer(), nullable=False, server_default="0"
            ),
            sa.Column(
                "imagem_meta_quantidade",
                sa.Integer(),
                nullable=False,
                server_default="5",
            ),
            sa.Column(
                "imagem_faltantes", sa.Integer(), nullable=False, server_default="5"
            ),
            sa.Column(
                "qualidade_percentual",
                sa.Float(),
                nullable=False,
                server_default="0",
            ),
            sa.Column("lacunas", sa.JSON(), nullable=True),
            sa.Column("proveniencia", sa.JSON(), nullable=False),
            sa.Column("snapshot_origem", sa.JSON(), nullable=False),
            sa.Column("snapshot_origem_hash", sa.String(length=64), nullable=False),
            sa.Column(
                "ultima_sincronizacao_em", sa.DateTime(timezone=True), nullable=False
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "origem_tenant_id",
                "origem_produto_id",
                name="uq_catalogo_mestre_produtos_origem",
            ),
            sa.CheckConstraint(
                "imagem_meta_quantidade >= 1",
                name="ck_catalogo_mestre_produtos_imagem_meta_positiva",
            ),
            sa.CheckConstraint(
                "imagem_quantidade >= 0 AND imagem_faltantes >= 0",
                name="ck_catalogo_mestre_produtos_imagens_nao_negativas",
            ),
            sa.CheckConstraint(
                "qualidade_percentual >= 0 AND qualidade_percentual <= 100",
                name="ck_catalogo_mestre_produtos_qualidade_intervalo",
            ),
        )
        for name, columns in (
            ("ix_catalogo_mestre_produtos_status", ["status"]),
            ("ix_catalogo_mestre_produtos_ativo", ["ativo"]),
            ("ix_catalogo_mestre_produtos_origem_tenant_id", ["origem_tenant_id"]),
            ("ix_catalogo_mestre_produtos_nome", ["nome"]),
            ("ix_catalogo_mestre_produtos_tipo_catalogo", ["tipo_catalogo"]),
            ("ix_catalogo_mestre_produtos_gtin", ["gtin"]),
            ("ix_catalogo_mestre_produtos_gtin_status", ["gtin_status"]),
            ("ix_catalogo_mestre_produtos_marca", ["marca"]),
            ("ix_catalogo_mestre_produtos_categoria", ["categoria"]),
            ("ix_catalogo_mestre_produtos_departamento", ["departamento"]),
            ("ix_catalogo_mestre_produtos_ncm", ["ncm"]),
            ("ix_catalogo_mestre_produtos_cest", ["cest"]),
            ("ix_catalogo_mestre_produtos_registro_mapa", ["registro_mapa"]),
            (
                "ix_catalogo_mestre_produtos_conteudo_veterinario_status",
                ["conteudo_veterinario_status"],
            ),
            ("ix_catalogo_mestre_produtos_imagem_faltantes", ["imagem_faltantes"]),
            (
                "ix_catalogo_mestre_produtos_snapshot_origem_hash",
                ["snapshot_origem_hash"],
            ),
            (
                "ix_catalogo_mestre_produtos_fila",
                ["status", "imagem_faltantes", "qualidade_percentual"],
            ),
        ):
            op.create_index(name, "catalogo_mestre_produtos", columns, unique=False)

    if not _has_table("catalogo_mestre_imagens", offline_default=False):
        op.create_table(
            "catalogo_mestre_imagens",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("produto_id", sa.Integer(), nullable=False),
            sa.Column("tipo_origem", sa.String(length=40), nullable=False),
            sa.Column("url_origem", sa.String(length=1000), nullable=True),
            sa.Column("arquivo_url", sa.String(length=1000), nullable=True),
            sa.Column("hash_arquivo", sa.String(length=64), nullable=True),
            sa.Column("ordem", sa.Integer(), nullable=False, server_default="0"),
            sa.Column(
                "e_principal",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
            sa.Column(
                "gerada_por_ia",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
            sa.Column("modelo_geracao", sa.String(length=120), nullable=True),
            sa.Column("versao_prompt", sa.String(length=120), nullable=True),
            sa.Column(
                "direitos_uso_status",
                sa.String(length=30),
                nullable=False,
                server_default="nao_verificado",
            ),
            sa.Column(
                "status_revisao",
                sa.String(length=30),
                nullable=False,
                server_default="pendente",
            ),
            sa.Column("revisada_por_id", sa.Integer(), nullable=True),
            sa.Column("revisada_em", sa.DateTime(timezone=True), nullable=True),
            sa.Column("largura", sa.Integer(), nullable=True),
            sa.Column("altura", sa.Integer(), nullable=True),
            sa.Column("tamanho_bytes", sa.Integer(), nullable=True),
            sa.Column("metadados", sa.JSON(), nullable=True),
            sa.Column(
                "ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.ForeignKeyConstraint(
                ["produto_id"], ["catalogo_mestre_produtos.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "produto_id",
                "url_origem",
                name="uq_catalogo_mestre_imagens_produto_url_origem",
            ),
            sa.CheckConstraint("ordem >= 0", name="ck_catalogo_mestre_imagens_ordem"),
        )
        for name, columns in (
            ("ix_catalogo_mestre_imagens_produto_id", ["produto_id"]),
            ("ix_catalogo_mestre_imagens_hash_arquivo", ["hash_arquivo"]),
            ("ix_catalogo_mestre_imagens_gerada_por_ia", ["gerada_por_ia"]),
            ("ix_catalogo_mestre_imagens_direitos_uso_status", ["direitos_uso_status"]),
            ("ix_catalogo_mestre_imagens_status_revisao", ["status_revisao"]),
            ("ix_catalogo_mestre_imagens_ativo", ["ativo"]),
            (
                "ix_catalogo_mestre_imagens_revisao",
                ["status_revisao", "direitos_uso_status"],
            ),
        ):
            op.create_index(name, "catalogo_mestre_imagens", columns, unique=False)

    if not _has_table("catalogo_mestre_pendencias", offline_default=False):
        op.create_table(
            "catalogo_mestre_pendencias",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("produto_id", sa.Integer(), nullable=False),
            sa.Column("tipo", sa.String(length=50), nullable=False),
            sa.Column("posicao_alvo", sa.Integer(), nullable=False, server_default="0"),
            sa.Column(
                "status",
                sa.String(length=30),
                nullable=False,
                server_default="pendente",
            ),
            sa.Column("prioridade", sa.Integer(), nullable=False, server_default="100"),
            sa.Column("origem_preferida", sa.String(length=50), nullable=True),
            sa.Column("detalhes", sa.JSON(), nullable=True),
            sa.Column("tentativas", sa.Integer(), nullable=False, server_default="0"),
            sa.Column(
                "proxima_tentativa_em", sa.DateTime(timezone=True), nullable=True
            ),
            sa.Column("ultimo_erro", sa.Text(), nullable=True),
            sa.Column("resolvida_em", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.ForeignKeyConstraint(
                ["produto_id"], ["catalogo_mestre_produtos.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "produto_id",
                "tipo",
                "posicao_alvo",
                name="uq_catalogo_mestre_pendencias_produto_tipo_posicao",
            ),
            sa.CheckConstraint(
                "posicao_alvo >= 0",
                name="ck_catalogo_mestre_pendencias_posicao_nao_negativa",
            ),
        )
        for name, columns in (
            ("ix_catalogo_mestre_pendencias_produto_id", ["produto_id"]),
            ("ix_catalogo_mestre_pendencias_tipo", ["tipo"]),
            ("ix_catalogo_mestre_pendencias_status", ["status"]),
            ("ix_catalogo_mestre_pendencias_prioridade", ["prioridade"]),
            (
                "ix_catalogo_mestre_pendencias_proxima_tentativa_em",
                ["proxima_tentativa_em"],
            ),
            (
                "ix_catalogo_mestre_pendencias_fila",
                ["status", "prioridade", "tipo"],
            ),
        ):
            op.create_index(name, "catalogo_mestre_pendencias", columns, unique=False)

    if not _has_table("catalogo_mestre_sincronizacoes", offline_default=False):
        op.create_table(
            "catalogo_mestre_sincronizacoes",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column(
                "origem_tenant_id",
                postgresql.UUID(as_uuid=True),
                nullable=False,
            ),
            sa.Column("origem_identificador", sa.String(length=255), nullable=True),
            sa.Column(
                "modo", sa.String(length=20), nullable=False, server_default="apply"
            ),
            sa.Column(
                "status",
                sa.String(length=30),
                nullable=False,
                server_default="executando",
            ),
            sa.Column(
                "imagem_meta_quantidade",
                sa.Integer(),
                nullable=False,
                server_default="5",
            ),
            sa.Column("resumo", sa.JSON(), nullable=True),
            sa.Column("erro", sa.Text(), nullable=True),
            sa.Column(
                "iniciada_em",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column("concluida_em", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        for name, columns in (
            (
                "ix_catalogo_mestre_sincronizacoes_origem_tenant_id",
                ["origem_tenant_id"],
            ),
            ("ix_catalogo_mestre_sincronizacoes_status", ["status"]),
            (
                "ix_catalogo_mestre_sincronizacoes_origem_inicio",
                ["origem_tenant_id", "iniciada_em"],
            ),
        ):
            op.create_index(
                name, "catalogo_mestre_sincronizacoes", columns, unique=False
            )


def downgrade() -> None:
    for table_name in (
        "catalogo_mestre_sincronizacoes",
        "catalogo_mestre_pendencias",
        "catalogo_mestre_imagens",
        "catalogo_mestre_produtos",
    ):
        if _has_table(table_name, offline_default=True):
            op.drop_table(table_name)
