"""Cria e administra os acessos do painel administrativo (adm.corepet.com.br).

Nao existe cadastro pela tela: os administradores so entram por aqui.

Exemplos (dentro do contêiner do backend):
  python scripts/criar_admin_plataforma.py listar
  python scripts/criar_admin_plataforma.py criar --email ana@corepet.com.br --nome "Ana"
  python scripts/criar_admin_plataforma.py criar --email admin@teste.com --senha admin1 \
      --permitir-senha-fraca              # só em desenvolvimento
  python scripts/criar_admin_plataforma.py liberar-painel --email antigo@corepet.com.br
  python scripts/criar_admin_plataforma.py nova-senha --email ana@corepet.com.br
  python scripts/criar_admin_plataforma.py desativar --email ana@corepet.com.br

Em produção a senha precisa cumprir a política do painel (12+ caracteres) e, por padrão, fica
"provisória": a pessoa é obrigada a trocá-la no primeiro acesso.
"""

from __future__ import annotations

import argparse
import getpass
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.db.base  # noqa: E402,F401  (carrega todos os modelos)
from app.adm_auth import _producao, validar_nova_senha  # noqa: E402
from app.auth.core import hash_password  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.platform_auth_models import PlatformAdmin, PlatformAdminSession  # noqa: E402


def _pedir_senha() -> str:
    primeira = getpass.getpass("Senha: ")
    if primeira != getpass.getpass("Repita a senha: "):
        raise SystemExit("As senhas não conferem.")
    return primeira


def _senha_valida(senha: str, email: str, permitir_fraca: bool) -> None:
    if permitir_fraca:
        if _producao():
            raise SystemExit("--permitir-senha-fraca não é aceito em produção.")
        if not senha:
            raise SystemExit("Informe a senha.")
        return
    erro = validar_nova_senha(senha, "", email)
    if erro:
        raise SystemExit(f"Senha recusada: {erro}")


def _admin(db, email: str) -> PlatformAdmin:
    admin = (
        db.query(PlatformAdmin)
        .filter(PlatformAdmin.email == email.strip().lower())
        .first()
    )
    if admin is None:
        raise SystemExit(f"Nenhum administrador com o e-mail {email}.")
    return admin


def _encerrar_sessoes(db, admin: PlatformAdmin, motivo: str) -> int:
    total = 0
    for sessao in db.query(PlatformAdminSession).filter(
        PlatformAdminSession.platform_admin_id == admin.id,
        PlatformAdminSession.revoked.is_(False),
    ):
        sessao.revoked = True
        sessao.revoked_at = datetime.now(timezone.utc)
        sessao.revoke_reason = motivo
        total += 1
    return total


def criar(args) -> None:
    email = args.email.strip().lower()
    senha = args.senha if args.senha is not None else _pedir_senha()
    _senha_valida(senha, email, args.permitir_senha_fraca)
    provisoria = args.provisoria or (not args.sem_troca and _producao())
    with SessionLocal() as db:
        existente = db.query(PlatformAdmin).filter(PlatformAdmin.email == email).first()
        if existente is not None:
            raise SystemExit(
                f"{email} já existe. Use 'nova-senha' para trocar a senha."
            )
        db.add(
            PlatformAdmin(
                email=email,
                name=args.nome or email.split("@", 1)[0],
                hashed_password=hash_password(senha),
                is_active=True,
                painel_adm_ativo=True,
                must_change_password=provisoria,
                password_changed_at=datetime.now(timezone.utc),
            )
        )
        db.commit()
    print(
        f"Administrador criado: {email} (troca de senha obrigatória: {'sim' if provisoria else 'não'})"
    )


def nova_senha(args) -> None:
    email = args.email.strip().lower()
    senha = args.senha if args.senha is not None else _pedir_senha()
    _senha_valida(senha, email, args.permitir_senha_fraca)
    with SessionLocal() as db:
        admin = _admin(db, email)
        admin.hashed_password = hash_password(senha)
        admin.password_changed_at = datetime.now(timezone.utc)
        admin.must_change_password = bool(
            args.provisoria or (not args.sem_troca and _producao())
        )
        admin.failed_login_attempts = 0
        admin.locked_until = None
        encerradas = _encerrar_sessoes(db, admin, "senha redefinida pelo script")
        db.commit()
    print(f"Senha de {email} redefinida. Sessões encerradas: {encerradas}.")


def mudar_ativo(args, ativo: bool) -> None:
    with SessionLocal() as db:
        admin = _admin(db, args.email)
        admin.is_active = ativo
        encerradas = (
            0 if ativo else _encerrar_sessoes(db, admin, "administrador desativado")
        )
        db.commit()
    print(
        f"{args.email}: {'ativado' if ativo else f'desativado (sessões encerradas: {encerradas})'}."
    )


def mudar_painel(args, liberar: bool) -> None:
    with SessionLocal() as db:
        admin = _admin(db, args.email)
        admin.painel_adm_ativo = liberar
        encerradas = (
            0 if liberar else _encerrar_sessoes(db, admin, "acesso ao painel removido")
        )
        db.commit()
    print(
        f"{args.email}: painel {'liberado' if liberar else f'bloqueado (sessões encerradas: {encerradas})'}."
    )


def listar(_args) -> None:
    with SessionLocal() as db:
        for admin in db.query(PlatformAdmin).order_by(PlatformAdmin.email):
            ultimo = (
                admin.last_login_at.strftime("%d/%m/%Y %H:%M")
                if admin.last_login_at
                else "nunca"
            )
            print(
                f"{admin.email:<40} {'ativo' if admin.is_active else 'INATIVO':<8} "
                f"painel: {'sim' if admin.painel_adm_ativo else 'não':<4} "
                f"troca obrigatória: {'sim' if admin.must_change_password else 'não':<4} último acesso: {ultimo}"
            )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="comando", required=True)

    def com_senha(p, nome_obrigatorio=False):
        p.add_argument("--email", required=True)
        p.add_argument(
            "--senha", help="Se omitida, a senha é pedida sem aparecer na tela."
        )
        p.add_argument(
            "--provisoria",
            action="store_true",
            help="Obriga a trocar a senha no primeiro acesso.",
        )
        p.add_argument(
            "--sem-troca",
            action="store_true",
            help="Não obriga a troca (padrão em desenvolvimento).",
        )
        p.add_argument(
            "--permitir-senha-fraca", action="store_true", help="Só em desenvolvimento."
        )

    p_criar = sub.add_parser("criar")
    com_senha(p_criar)
    p_criar.add_argument("--nome")
    p_criar.set_defaults(funcao=criar)

    p_senha = sub.add_parser("nova-senha")
    com_senha(p_senha)
    p_senha.set_defaults(funcao=nova_senha)

    for nome, ativo in (("desativar", False), ("ativar", True)):
        p = sub.add_parser(nome)
        p.add_argument("--email", required=True)
        p.set_defaults(funcao=lambda a, v=ativo: mudar_ativo(a, v))

    for nome, liberar in (("liberar-painel", True), ("bloquear-painel", False)):
        p = sub.add_parser(
            nome, help="Libera/bloqueia o acesso de um administrador ao painel adm."
        )
        p.add_argument("--email", required=True)
        p.set_defaults(funcao=lambda a, v=liberar: mudar_painel(a, v))

    sub.add_parser("listar").set_defaults(funcao=listar)

    args = parser.parse_args()
    args.funcao(args)


if __name__ == "__main__":
    main()
