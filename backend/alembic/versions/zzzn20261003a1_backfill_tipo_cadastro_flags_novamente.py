"""re-roda o backfill de is_cliente/is_fornecedor/is_veterinario/is_funcionario

Revision ID: zzzn20261003a1
Revises: zzzm20261002a1
Create Date: 2026-10-03

Repete exatamente a mesma logica de zzzg20260922a1_backfill_tipo_cadastro_flags,
porque varios pontos de escrita ficaram sem gravar a flag correspondente entre
aquela migracao e a correcao feita nestes arquivos (funcionarios/base_routes.py,
notas_entrada/fornecedores.py, usuarios_routes.py, importacao_pessoas.py,
scripts/seed_banho_tosa_ux_support.py, scripts/seed_demo_operacional_support.py,
routes/ecommerce_auth_cliente.py, routes/app_mobile_funcionario_pdv/clientes.py,
estoque/transferencia_grupo_service.py) — pessoas criadas por esses caminhos no
meio tempo ficaram com as 4 flags falsas. Toda UPDATE aqui so acrescenta `true`
(nunca desliga uma flag), entao rodar de novo e seguro mesmo pra quem ja estava
correto.

Recomendado rodar em horario de baixo trafego: cada UPDATE varre a tabela
clientes inteira (todas as lojas), sem lotes — mesmo padrao ja usado em
zzzg20260922a1 e outras migrations deste repo.
"""

from typing import Sequence, Union

from alembic import op


revision: str = "zzzn20261003a1"
down_revision: Union[str, Sequence[str], None] = "zzzm20261002a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) Baseline a partir do tipo_cadastro atual.
    op.execute("UPDATE clientes SET is_cliente = true WHERE tipo_cadastro = 'cliente'")
    op.execute(
        "UPDATE clientes SET is_fornecedor = true WHERE tipo_cadastro = 'fornecedor'"
    )
    op.execute(
        "UPDATE clientes SET is_veterinario = true WHERE tipo_cadastro = 'veterinario'"
    )
    op.execute(
        "UPDATE clientes SET is_funcionario = true WHERE tipo_cadastro = 'funcionario'"
    )

    # 2) Historico de uso real, independente do tipo_cadastro cadastrado.
    op.execute(
        """
        UPDATE clientes SET is_cliente = true
        WHERE id IN (
            SELECT DISTINCT cliente_id FROM vendas WHERE cliente_id IS NOT NULL
        )
        """
    )
    op.execute(
        """
        UPDATE clientes SET is_funcionario = true
        WHERE id IN (
            SELECT DISTINCT funcionario_id FROM vendas WHERE funcionario_id IS NOT NULL
        )
        """
    )
    op.execute(
        """
        UPDATE clientes SET is_fornecedor = true
        WHERE id IN (
            SELECT DISTINCT fornecedor_id FROM notas_entrada WHERE fornecedor_id IS NOT NULL
            UNION
            SELECT DISTINCT fornecedor_id FROM pedidos_compra WHERE fornecedor_id IS NOT NULL
        )
        """
    )
    op.execute(
        """
        UPDATE clientes SET is_veterinario = true
        WHERE id IN (
            SELECT DISTINCT veterinario_id FROM vet_agendamentos WHERE veterinario_id IS NOT NULL
            UNION
            SELECT DISTINCT veterinario_id FROM vet_consultas WHERE veterinario_id IS NOT NULL
            UNION
            SELECT DISTINCT veterinario_id FROM vet_prescricoes WHERE veterinario_id IS NOT NULL
            UNION
            SELECT DISTINCT veterinario_id FROM vet_vacinas_registros WHERE veterinario_id IS NOT NULL
            UNION
            SELECT DISTINCT veterinario_id FROM vet_internacoes WHERE veterinario_id IS NOT NULL
            UNION
            SELECT DISTINCT veterinario_id FROM vet_orcamentos WHERE veterinario_id IS NOT NULL
        )
        """
    )

    # 3) Ninguem deve ficar com as 4 flags falsas.
    op.execute(
        """
        UPDATE clientes
        SET is_cliente = true
        WHERE NOT is_cliente AND NOT is_fornecedor AND NOT is_veterinario AND NOT is_funcionario
        """
    )


def downgrade() -> None:
    # As flags sao a fonte de verdade usada pela tela de Pessoa e por toda a
    # logica de negocio que esta migracao prepara; nao e seguro apagar essa
    # informacao ao reverter apenas esta versao.
    pass
