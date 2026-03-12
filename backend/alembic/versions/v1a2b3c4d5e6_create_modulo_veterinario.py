"""Cria tabelas do modulo veterinario

Revision ID: v1a2b3c4d5e6
Revises: p4q5r6s7t8u9
Create Date: 2026-03-12 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from alembic import op

revision: str = "v1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "p4q5r6s7t8u9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # vet_medicamentos_catalogo
    op.create_table(
        "vet_medicamentos_catalogo",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("nome", sa.String(255), nullable=False),
        sa.Column("nome_comercial", sa.String(255), nullable=True),
        sa.Column("principio_ativo", sa.String(255), nullable=True),
        sa.Column("fabricante", sa.String(255), nullable=True),
        sa.Column("forma_farmaceutica", sa.String(100), nullable=True),
        sa.Column("concentracao", sa.String(100), nullable=True),
        sa.Column("especies_indicadas", sa.JSON(), nullable=True),
        sa.Column("indicacoes", sa.Text(), nullable=True),
        sa.Column("contraindicacoes", sa.Text(), nullable=True),
        sa.Column("interacoes", sa.Text(), nullable=True),
        sa.Column("posologia_referencia", sa.Text(), nullable=True),
        sa.Column("dose_min_mgkg", sa.Float(), nullable=True),
        sa.Column("dose_max_mgkg", sa.Float(), nullable=True),
        sa.Column("eh_antibiotico", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("eh_controlado", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vet_medicamentos_catalogo_tenant_id", "vet_medicamentos_catalogo", ["tenant_id"])
    op.create_index("ix_vet_medicamentos_catalogo_nome", "vet_medicamentos_catalogo", ["nome"])
    op.create_index("ix_vet_medicamentos_catalogo_principio_ativo", "vet_medicamentos_catalogo", ["principio_ativo"])

    # vet_protocolos_vacinas
    op.create_table(
        "vet_protocolos_vacinas",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("nome", sa.String(255), nullable=False),
        sa.Column("especie", sa.String(50), nullable=True),
        sa.Column("dose_inicial_semanas", sa.Integer(), nullable=True),
        sa.Column("reforco_anual", sa.Boolean(), server_default="true"),
        sa.Column("intervalo_doses_dias", sa.Integer(), nullable=True),
        sa.Column("numero_doses_serie", sa.Integer(), server_default="1"),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vet_protocolos_vacinas_tenant_id", "vet_protocolos_vacinas", ["tenant_id"])

    # vet_consultas (sem FK para agendamentos ainda — criada depois)
    op.create_table(
        "vet_consultas",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("pet_id", sa.Integer(), sa.ForeignKey("pets.id"), nullable=False),
        sa.Column("cliente_id", sa.Integer(), sa.ForeignKey("clientes.id"), nullable=False),
        sa.Column("veterinario_id", sa.Integer(), sa.ForeignKey("clientes.id"), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("inicio_atendimento", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fim_atendimento", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tipo", sa.String(50), nullable=False, server_default="consulta"),
        sa.Column("status", sa.String(30), nullable=False, server_default="em_andamento"),
        sa.Column("queixa_principal", sa.Text(), nullable=True),
        sa.Column("historia_clinica", sa.Text(), nullable=True),
        sa.Column("peso_consulta", sa.Float(), nullable=True),
        sa.Column("temperatura", sa.Float(), nullable=True),
        sa.Column("frequencia_cardiaca", sa.Integer(), nullable=True),
        sa.Column("frequencia_respiratoria", sa.Integer(), nullable=True),
        sa.Column("tpc", sa.String(20), nullable=True),
        sa.Column("mucosas", sa.String(100), nullable=True),
        sa.Column("hidratacao", sa.String(50), nullable=True),
        sa.Column("nivel_dor", sa.Integer(), nullable=True),
        sa.Column("saturacao_o2", sa.Float(), nullable=True),
        sa.Column("pressao_sistolica", sa.Integer(), nullable=True),
        sa.Column("pressao_diastolica", sa.Integer(), nullable=True),
        sa.Column("glicemia", sa.Float(), nullable=True),
        sa.Column("exame_fisico", sa.Text(), nullable=True),
        sa.Column("hipotese_diagnostica", sa.Text(), nullable=True),
        sa.Column("diagnostico", sa.Text(), nullable=True),
        sa.Column("diagnostico_simples", sa.Text(), nullable=True),
        sa.Column("conduta", sa.Text(), nullable=True),
        sa.Column("retorno_em_dias", sa.Integer(), nullable=True),
        sa.Column("data_retorno", sa.Date(), nullable=True),
        sa.Column("asa_score", sa.Integer(), nullable=True),
        sa.Column("asa_justificativa", sa.Text(), nullable=True),
        sa.Column("observacoes_internas", sa.Text(), nullable=True),
        sa.Column("observacoes_tutor", sa.Text(), nullable=True),
        sa.Column("hash_prontuario", sa.String(64), nullable=True),
        sa.Column("finalizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finalizado_por_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vet_consultas_tenant_id", "vet_consultas", ["tenant_id"])
    op.create_index("ix_vet_consultas_pet_id", "vet_consultas", ["pet_id"])
    op.create_index("ix_vet_consultas_status", "vet_consultas", ["status"])

    # vet_agendamentos
    op.create_table(
        "vet_agendamentos",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("pet_id", sa.Integer(), sa.ForeignKey("pets.id"), nullable=False),
        sa.Column("cliente_id", sa.Integer(), sa.ForeignKey("clientes.id"), nullable=False),
        sa.Column("veterinario_id", sa.Integer(), sa.ForeignKey("clientes.id"), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("data_hora", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duracao_minutos", sa.Integer(), server_default="30"),
        sa.Column("tipo", sa.String(50), nullable=False, server_default="consulta"),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="agendado"),
        sa.Column("pretriagem", sa.JSON(), nullable=True),
        sa.Column("is_emergencia", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("sintoma_emergencia", sa.String(255), nullable=True),
        sa.Column("consulta_id", sa.Integer(), sa.ForeignKey("vet_consultas.id"), nullable=True),
        sa.Column("inicio_atendimento", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fim_atendimento", sa.DateTime(timezone=True), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vet_agendamentos_tenant_id", "vet_agendamentos", ["tenant_id"])
    op.create_index("ix_vet_agendamentos_data_hora", "vet_agendamentos", ["data_hora"])
    op.create_index("ix_vet_agendamentos_status", "vet_agendamentos", ["status"])
    op.create_index("ix_vet_agendamentos_pet_id", "vet_agendamentos", ["pet_id"])

    # vet_prescricoes
    op.create_table(
        "vet_prescricoes",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("consulta_id", sa.Integer(), sa.ForeignKey("vet_consultas.id"), nullable=False),
        sa.Column("pet_id", sa.Integer(), sa.ForeignKey("pets.id"), nullable=False),
        sa.Column("veterinario_id", sa.Integer(), sa.ForeignKey("clientes.id"), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("numero", sa.String(50), nullable=True),
        sa.Column("data_emissao", sa.Date(), nullable=False),
        sa.Column("tipo_receituario", sa.String(30), server_default="simples"),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("hash_receita", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vet_prescricoes_tenant_id", "vet_prescricoes", ["tenant_id"])
    op.create_index("ix_vet_prescricoes_consulta_id", "vet_prescricoes", ["consulta_id"])

    # vet_itens_prescricao
    op.create_table(
        "vet_itens_prescricao",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("prescricao_id", sa.Integer(), sa.ForeignKey("vet_prescricoes.id"), nullable=False),
        sa.Column("medicamento_catalogo_id", sa.Integer(), sa.ForeignKey("vet_medicamentos_catalogo.id"), nullable=True),
        sa.Column("nome_medicamento", sa.String(255), nullable=False),
        sa.Column("concentracao", sa.String(100), nullable=True),
        sa.Column("forma_farmaceutica", sa.String(100), nullable=True),
        sa.Column("quantidade", sa.String(100), nullable=True),
        sa.Column("posologia", sa.Text(), nullable=False),
        sa.Column("via_administracao", sa.String(50), nullable=True),
        sa.Column("duracao_dias", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vet_itens_prescricao_tenant_id", "vet_itens_prescricao", ["tenant_id"])

    # vet_vacinas_registros
    op.create_table(
        "vet_vacinas_registros",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("pet_id", sa.Integer(), sa.ForeignKey("pets.id"), nullable=False),
        sa.Column("consulta_id", sa.Integer(), sa.ForeignKey("vet_consultas.id"), nullable=True),
        sa.Column("veterinario_id", sa.Integer(), sa.ForeignKey("clientes.id"), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("protocolo_id", sa.Integer(), sa.ForeignKey("vet_protocolos_vacinas.id"), nullable=True),
        sa.Column("nome_vacina", sa.String(255), nullable=False),
        sa.Column("fabricante", sa.String(255), nullable=True),
        sa.Column("lote", sa.String(100), nullable=True),
        sa.Column("data_aplicacao", sa.Date(), nullable=False),
        sa.Column("data_proxima_dose", sa.Date(), nullable=True),
        sa.Column("numero_dose", sa.Integer(), server_default="1"),
        sa.Column("via_administracao", sa.String(50), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vet_vacinas_registros_tenant_id", "vet_vacinas_registros", ["tenant_id"])
    op.create_index("ix_vet_vacinas_registros_pet_id", "vet_vacinas_registros", ["pet_id"])
    op.create_index("ix_vet_vacinas_registros_data_proxima_dose", "vet_vacinas_registros", ["data_proxima_dose"])

    # vet_exames
    op.create_table(
        "vet_exames",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("pet_id", sa.Integer(), sa.ForeignKey("pets.id"), nullable=False),
        sa.Column("consulta_id", sa.Integer(), sa.ForeignKey("vet_consultas.id"), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("tipo", sa.String(50), nullable=False),
        sa.Column("nome", sa.String(255), nullable=False),
        sa.Column("data_solicitacao", sa.Date(), nullable=True),
        sa.Column("data_resultado", sa.Date(), nullable=True),
        sa.Column("status", sa.String(30), server_default="solicitado"),
        sa.Column("laboratorio", sa.String(255), nullable=True),
        sa.Column("resultado_texto", sa.Text(), nullable=True),
        sa.Column("resultado_json", sa.JSON(), nullable=True),
        sa.Column("interpretacao", sa.Text(), nullable=True),
        sa.Column("interpretacao_ia", sa.Text(), nullable=True),
        sa.Column("arquivo_url", sa.String(500), nullable=True),
        sa.Column("arquivo_nome", sa.String(255), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vet_exames_tenant_id", "vet_exames", ["tenant_id"])
    op.create_index("ix_vet_exames_pet_id", "vet_exames", ["pet_id"])
    op.create_index("ix_vet_exames_tipo", "vet_exames", ["tipo"])

    # vet_catalogo_procedimentos
    op.create_table(
        "vet_catalogo_procedimentos",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("nome", sa.String(255), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("categoria", sa.String(100), nullable=True),
        sa.Column("valor_padrao", sa.Numeric(10, 2), nullable=True),
        sa.Column("duracao_minutos", sa.Integer(), nullable=True),
        sa.Column("requer_anestesia", sa.Boolean(), server_default="false"),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vet_catalogo_procedimentos_tenant_id", "vet_catalogo_procedimentos", ["tenant_id"])

    # vet_procedimentos_consulta
    op.create_table(
        "vet_procedimentos_consulta",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("consulta_id", sa.Integer(), sa.ForeignKey("vet_consultas.id"), nullable=False),
        sa.Column("catalogo_id", sa.Integer(), sa.ForeignKey("vet_catalogo_procedimentos.id"), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("nome", sa.String(255), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("valor", sa.Numeric(10, 2), nullable=True),
        sa.Column("realizado", sa.Boolean(), server_default="true"),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vet_procedimentos_consulta_tenant_id", "vet_procedimentos_consulta", ["tenant_id"])

    # vet_internacoes
    op.create_table(
        "vet_internacoes",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("pet_id", sa.Integer(), sa.ForeignKey("pets.id"), nullable=False),
        sa.Column("consulta_id", sa.Integer(), sa.ForeignKey("vet_consultas.id"), nullable=True),
        sa.Column("veterinario_id", sa.Integer(), sa.ForeignKey("clientes.id"), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("data_entrada", sa.DateTime(timezone=True), nullable=False),
        sa.Column("data_saida", sa.DateTime(timezone=True), nullable=True),
        sa.Column("motivo", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), server_default="internado"),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vet_internacoes_tenant_id", "vet_internacoes", ["tenant_id"])
    op.create_index("ix_vet_internacoes_pet_id", "vet_internacoes", ["pet_id"])
    op.create_index("ix_vet_internacoes_status", "vet_internacoes", ["status"])

    # vet_evolucoes_internacao
    op.create_table(
        "vet_evolucoes_internacao",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("internacao_id", sa.Integer(), sa.ForeignKey("vet_internacoes.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("data_hora", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("temperatura", sa.Float(), nullable=True),
        sa.Column("frequencia_cardiaca", sa.Integer(), nullable=True),
        sa.Column("frequencia_respiratoria", sa.Integer(), nullable=True),
        sa.Column("nivel_dor", sa.Integer(), nullable=True),
        sa.Column("pressao_sistolica", sa.Integer(), nullable=True),
        sa.Column("glicemia", sa.Float(), nullable=True),
        sa.Column("peso", sa.Float(), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vet_evolucoes_internacao_tenant_id", "vet_evolucoes_internacao", ["tenant_id"])
    op.create_index("ix_vet_evolucoes_internacao_internacao_id", "vet_evolucoes_internacao", ["internacao_id"])

    # vet_peso_registros
    op.create_table(
        "vet_peso_registros",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("pet_id", sa.Integer(), sa.ForeignKey("pets.id"), nullable=False),
        sa.Column("consulta_id", sa.Integer(), sa.ForeignKey("vet_consultas.id"), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("peso_kg", sa.Float(), nullable=False),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vet_peso_registros_tenant_id", "vet_peso_registros", ["tenant_id"])
    op.create_index("ix_vet_peso_registros_pet_id", "vet_peso_registros", ["pet_id"])

    # vet_fotos_clinicas
    op.create_table(
        "vet_fotos_clinicas",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("consulta_id", sa.Integer(), sa.ForeignKey("vet_consultas.id"), nullable=False),
        sa.Column("pet_id", sa.Integer(), sa.ForeignKey("pets.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("nome_arquivo", sa.String(255), nullable=True),
        sa.Column("tipo", sa.String(50), nullable=True),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("data_foto", sa.Date(), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vet_fotos_clinicas_tenant_id", "vet_fotos_clinicas", ["tenant_id"])

    # vet_perfil_comportamental
    op.create_table(
        "vet_perfil_comportamental",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("pet_id", sa.Integer(), sa.ForeignKey("pets.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("temperamento", sa.String(50), nullable=True),
        sa.Column("reacao_animais", sa.String(50), nullable=True),
        sa.Column("reacao_pessoas", sa.String(50), nullable=True),
        sa.Column("medo_secador", sa.String(50), nullable=True),
        sa.Column("medo_tesoura", sa.String(50), nullable=True),
        sa.Column("aceita_focinheira", sa.String(50), nullable=True),
        sa.Column("comportamento_carro", sa.String(50), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pet_id", name="uq_vet_perfil_comportamental_pet_id"),
    )
    op.create_index("ix_vet_perfil_comportamental_tenant_id", "vet_perfil_comportamental", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("vet_perfil_comportamental")
    op.drop_table("vet_fotos_clinicas")
    op.drop_table("vet_peso_registros")
    op.drop_table("vet_evolucoes_internacao")
    op.drop_table("vet_internacoes")
    op.drop_table("vet_procedimentos_consulta")
    op.drop_table("vet_catalogo_procedimentos")
    op.drop_table("vet_exames")
    op.drop_table("vet_vacinas_registros")
    op.drop_table("vet_itens_prescricao")
    op.drop_table("vet_prescricoes")
    op.drop_table("vet_agendamentos")
    op.drop_table("vet_consultas")
    op.drop_table("vet_protocolos_vacinas")
    op.drop_table("vet_medicamentos_catalogo")
