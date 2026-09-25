"""Backfill: copia nome/celular/e-mail da Pessoa (Cliente) para o Usuario
(User) vinculado via auth_user_id, e marca is_funcionario=true para quem ja
tem login no sistema.

Contexto: ate agora, vincular ou criar um login para uma Pessoa so
acontecia pelo card "Acesso ao app" dentro da tela de Pessoa (removido -
ver .claude/skills/pessoas/SKILL.md). Esse fluxo nunca sincronizava os
dados de contato de volta para o User. Agora que a tela Usuarios passa a
ser o lugar central para gerenciar acesso, este script reconcilia o que
ja existe: para cada Cliente com auth_user_id preenchido, preenche as
lacunas (nunca sobrescreve o que o User ja tem) em nome/telefone/email, e
marca a Pessoa como funcionaria (quem tem login e, por definicao, alguem
da equipe da loja).

Seguro por padrao: roda em modo dry-run (so mostra o que faria) a menos
que --apply seja passado. Idempotente: rodar de novo sem mudancas no
banco nao produz nenhum efeito adicional.

Uso:
    docker compose -f docker-compose.local-dev.yml run --rm backend \
        python scripts/backfill_dados_usuario_de_pessoa.py [--tenant-id UUID] [--apply]
"""

from __future__ import annotations

import argparse
import json
from uuid import UUID

import app.main  # noqa: F401  (registra todos os models no mapper do SQLAlchemy)
from app.db import SessionLocal
from app.models import Cliente, Tenant, User
from app.tenancy.context import tenant_context


def _preencher_lacuna(destino: str | None, origem: str | None) -> str | None:
    """Só usa o valor de origem quando o destino está vazio — nunca sobrescreve."""
    return destino if destino else (origem or destino)


def _backfill_um_tenant(db, *, tenant_id: UUID, marcar_funcionario: bool) -> list[dict]:
    tocados: list[dict] = []
    with tenant_context(tenant_id):
        pessoas = (
            db.query(Cliente)
            .filter(Cliente.tenant_id == tenant_id, Cliente.auth_user_id.isnot(None))
            .all()
        )
        for pessoa in pessoas:
            user = db.query(User).filter(User.id == pessoa.auth_user_id).first()
            if not user:
                continue

            alteracoes = {}

            novo_nome = _preencher_lacuna(user.nome, pessoa.nome)
            if novo_nome != user.nome:
                alteracoes["nome"] = {"de": user.nome, "para": novo_nome}
                user.nome = novo_nome

            novo_telefone = _preencher_lacuna(user.telefone, pessoa.celular)
            if novo_telefone != user.telefone:
                alteracoes["telefone"] = {"de": user.telefone, "para": novo_telefone}
                user.telefone = novo_telefone

            novo_email = _preencher_lacuna(user.email, pessoa.email)
            if novo_email != user.email:
                alteracoes["email"] = {"de": user.email, "para": novo_email}
                user.email = novo_email

            if marcar_funcionario and not pessoa.is_funcionario:
                alteracoes["is_funcionario"] = {"de": False, "para": True}
                pessoa.is_funcionario = True

            if alteracoes:
                tocados.append(
                    {
                        "pessoa_id": pessoa.id,
                        "pessoa_nome": pessoa.nome,
                        "user_id": user.id,
                        "tenant_id": str(tenant_id),
                        "alteracoes": alteracoes,
                    }
                )
    return tocados


def backfill_dados_usuario_de_pessoa(
    db,
    *,
    tenant_id: UUID | None = None,
    marcar_funcionario: bool = True,
) -> list[dict]:
    # clientes/users sao TenantScoped: toda query ORM exige tenant no contexto.
    # tenant_id=None => itera todos os tenants (tabela tenants e global/whitelist),
    # com contexto proprio por iteracao — mesmo padrao de loyalty_service.py /
    # coupon_service.py (backfill_loyalty_reward_consumption_meta).
    if tenant_id is not None:
        return _backfill_um_tenant(db, tenant_id=tenant_id, marcar_funcionario=marcar_funcionario)

    tocados: list[dict] = []
    for (tid_raw,) in db.query(Tenant.id).all():
        try:
            tid = UUID(str(tid_raw))
        except (TypeError, ValueError):
            continue
        tocados.extend(
            _backfill_um_tenant(db, tenant_id=tid, marcar_funcionario=marcar_funcionario)
        )
    return tocados


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tenant-id",
        dest="tenant_id",
        default=None,
        help="UUID do tenant. Se omitido, processa todos os tenants.",
    )
    parser.add_argument(
        "--apply",
        dest="apply_changes",
        action="store_true",
        help="Grava as mudancas. Sem esta flag, so mostra o que seria feito (dry-run).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    tenant_id = UUID(args.tenant_id) if args.tenant_id else None

    db = SessionLocal()
    try:
        tocados = backfill_dados_usuario_de_pessoa(db, tenant_id=tenant_id)

        if args.apply_changes:
            db.commit()
        else:
            db.rollback()

        print(
            json.dumps(
                {
                    "modo": "apply" if args.apply_changes else "dry_run",
                    "tenant_id": str(tenant_id) if tenant_id else None,
                    "total_pessoas_tocadas": len(tocados),
                    "detalhes": tocados,
                },
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
