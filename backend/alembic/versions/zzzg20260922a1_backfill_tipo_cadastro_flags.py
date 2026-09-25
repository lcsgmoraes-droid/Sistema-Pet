"""backfill multi-tipo cadastro flags on clientes

Revision ID: zzzg20260922a1
Revises: zzzf20260922a1
Create Date: 2026-09-22

Preenche is_cliente/is_fornecedor/is_veterinario/is_funcionario a partir de
duas fontes:
1. Baseline: o tipo_cadastro atual de cada pessoa (quem era "funcionario"
   continua com is_funcionario=true, etc.).
2. Historico de uso: mesmo que o tipo_cadastro nunca tenha sido esse, quem
   ja apareceu numa venda (como cliente ou como funcionario/vendedor), numa
   nota de entrada/pedido de compra (como fornecedor) ou em algum processo
   veterinario (como veterinario) recebe a flag correspondente.

Recomendado rodar em horario de baixo trafego: cada UPDATE varre a tabela
clientes inteira (todas as lojas), sem lotes — mesmo padrao ja usado em
outras migrations deste repo (ver zwr20260801a1, mn20260503a1).
"""

from typing import Sequence, Union

from alembic import op


revision: str = "zzzg20260922a1"
down_revision: Union[str, Sequence[str], None] = "zzzf20260922a1"
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

    # 3) Ninguem deve ficar com as 4 flags falsas: quem sobrar sem nenhum
    # sinal de uso historico e sem tipo_cadastro reconhecido volta ao
    # baseline minimo (cliente), preservando a garantia de "pelo menos um
    # tipo marcado" que a tela e o backend passam a exigir dai em diante.
    op.execute(
        """
        UPDATE clientes
        SET is_cliente = true
        WHERE NOT is_cliente AND NOT is_fornecedor AND NOT is_veterinario AND NOT is_funcionario
        """
    )


def downgrade() -> None:
    # As flags passam a ser a fonte de verdade usada pela tela de Pessoa;
    # nao e seguro apagar essa informacao ao reverter apenas esta versao.
    pass
