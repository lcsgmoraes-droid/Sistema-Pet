"""Cadastros de apoio para o seed local de Banho & Tosa."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text


MARKER = "[UX-BT-20260828]"


def one(db, sql: str, params: dict[str, Any]) -> dict[str, Any] | None:
    row = db.execute(text(sql), params).mappings().first()
    return dict(row) if row else None


def ensure_person(
    db,
    *,
    tenant_id: str,
    user_id: int,
    codigo: str,
    nome: str,
    tipo: str,
    is_entregador: bool = False,
) -> int:
    return int(
        db.execute(
            text(
                """
                INSERT INTO clientes (
                    tenant_id, user_id, codigo, tipo_cadastro, tipo_pessoa, nome,
                    telefone, endereco, numero, bairro, cidade, estado, cep,
                    is_entregador, is_terceirizado, recebe_repasse,
                    gera_conta_pagar, recebe_comissao_entrega, entregador_ativo,
                    entregador_padrao, controla_rh, gera_conta_pagar_custo_entrega,
                    moto_propria, controla_dre, complemento_modo,
                    complemento_fixo_valor, parceiro_ativo, parceiro_tipo_acerto,
                    parceiro_dia_acerto, parceiro_notificar, ativo, credito
                ) VALUES (
                    :tenant_id, :user_id, :codigo, :tipo, 'PF', :nome,
                    '(11) 90000-0000', 'Rua das Acacias', '120', 'Centro',
                    'Sao Paulo', 'SP', '01001-000', :is_entregador, false,
                    :is_entregador, :is_entregador, :is_entregador,
                    true, :is_entregador, false, :is_entregador, true, true,
                    'automatico', 0, false, 'mensal', 1, true, true, 0
                )
                ON CONFLICT (tenant_id, codigo) DO UPDATE SET
                    nome = EXCLUDED.nome,
                    tipo_cadastro = EXCLUDED.tipo_cadastro,
                    is_entregador = EXCLUDED.is_entregador,
                    entregador_ativo = true,
                    ativo = true,
                    updated_at = now()
                RETURNING id
                """
            ),
            {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "codigo": codigo,
                "nome": nome,
                "tipo": tipo,
                "is_entregador": is_entregador,
            },
        ).scalar_one()
    )


def grant_profile(
    db, *, tenant_id: str, user_id: int, cliente_id: int, profile_type: str
) -> None:
    db.execute(
        text(
            """
            INSERT INTO app_access_profiles (
                tenant_id, user_id, cliente_id, profile_type, is_active,
                granted_by_user_id, notes
            ) VALUES (
                :tenant_id, :user_id, :cliente_id, :profile_type, true,
                :user_id, :notes
            )
            ON CONFLICT (tenant_id, cliente_id, profile_type) DO UPDATE SET
                user_id = EXCLUDED.user_id,
                is_active = true,
                notes = EXCLUDED.notes,
                updated_at = now()
            """
        ),
        {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "cliente_id": cliente_id,
            "profile_type": profile_type,
            "notes": f"{MARKER} acesso local para teste",
        },
    )


def ensure_pet(
    db,
    *,
    tenant_id: str,
    user_id: int,
    cliente_id: int,
    codigo: str,
    nome: str,
    raca: str,
    porte: str,
    index: int,
) -> int:
    existing = one(
        db,
        "SELECT id FROM pets WHERE tenant_id = :tenant_id AND codigo = :codigo LIMIT 1",
        {"tenant_id": tenant_id, "codigo": codigo},
    )
    params = {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "cliente_id": cliente_id,
        "codigo": codigo,
        "nome": nome,
        "raca": raca,
        "porte": porte,
        "peso": 4.5 + (index * 2.2),
        "sexo": "macho" if index % 2 == 0 else "femea",
        "cor": ("caramelo", "branco", "preto", "dourado")[index % 4],
    }
    if existing:
        db.execute(
            text(
                """
                UPDATE pets SET cliente_id = :cliente_id, nome = :nome, raca = :raca,
                    porte = :porte, peso = :peso, sexo = :sexo, cor = :cor,
                    especie = 'Cao', ativo = true, updated_at = now()
                WHERE id = :id AND tenant_id = :tenant_id
                """
            ),
            {**params, "id": existing["id"]},
        )
        return int(existing["id"])
    return int(
        db.execute(
            text(
                """
                INSERT INTO pets (
                    tenant_id, user_id, cliente_id, codigo, nome, especie, raca,
                    sexo, castrado, peso, cor, cor_pelagem, porte, observacoes, ativo
                ) VALUES (
                    :tenant_id, :user_id, :cliente_id, :codigo, :nome, 'Cao',
                    :raca, :sexo, true, :peso, :cor, :cor, :porte,
                    :observacoes, true
                ) RETURNING id
                """
            ),
            {**params, "observacoes": f"{MARKER} pet ficticio para homologacao"},
        ).scalar_one()
    )
