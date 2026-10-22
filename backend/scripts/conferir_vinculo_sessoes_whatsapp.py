"""Confere os vinculos conversa -> tutor gravados pela regra antiga (frouxa).

SOMENTE LEITURA: lista as conversas cujo cliente_id nao corresponde ao telefone
do cadastro (vinculo duvidoso) e as que hoje ficariam sem vinculo ou ambiguas.
Nada e alterado; a decisao do que corrigir e humana.

Uso (a partir de backend/):
    python -m scripts.conferir_vinculo_sessoes_whatsapp --saida relatorio.json
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from uuid import UUID

from app.db import SessionLocal
from app.models import Cliente, Tenant
from app.tenancy.context import tenant_context
from app.whatsapp.customer_lookup import (
    SITUACAO_UNICO,
    resolver_tutor_por_telefone,
    telefones_compativeis,
)
from app.whatsapp.models import WhatsAppSession


def classificar_vinculo(cliente_id_atual, telefone_sessao, cadastro, resolucao) -> str:
    """Classifica o vinculo de uma conversa sem alterar nada.

    - ok: o cadastro ligado tem telefone compativel com o da conversa.
    - duvidoso: ha cadastro ligado, mas o telefone nao corresponde.
    - sem_vinculo_e_unico: nao ha vinculo, mas hoje um unico cadastro corresponde.
    - sem_vinculo_ambiguo: nao ha vinculo e varios cadastros correspondem.
    - sem_vinculo: nao ha vinculo e nenhum cadastro corresponde.
    """
    if cliente_id_atual:
        telefones = [
            t
            for t in (
                getattr(cadastro, "celular", None),
                getattr(cadastro, "telefone", None),
            )
            if t
        ]
        if cadastro is not None and any(
            telefones_compativeis(telefone_sessao, t) for t in telefones
        ):
            return "ok"
        return "duvidoso"
    if resolucao.situacao == SITUACAO_UNICO:
        return "sem_vinculo_e_unico"
    if resolucao.situacao == "ambiguo":
        return "sem_vinculo_ambiguo"
    return "sem_vinculo"


def conferir(db, tenant_id=None) -> list[dict]:
    ids = [tenant_id] if tenant_id else [t.id for t in db.query(Tenant).all()]
    achados = []
    for tid in ids:
        # Conversas e clientes sao TenantScoped: toda query exige a loja no contexto.
        with tenant_context(tid):
            sessoes = (
                db.query(WhatsAppSession).filter(WhatsAppSession.tenant_id == tid).all()
            )
            for sessao in sessoes:
                cadastro = (
                    db.query(Cliente.id, Cliente.celular, Cliente.telefone)
                    .filter(Cliente.tenant_id == tid, Cliente.id == sessao.cliente_id)
                    .first()
                    if sessao.cliente_id
                    else None
                )
                resolucao = resolver_tutor_por_telefone(db, tid, sessao.phone_number)
                classe = classificar_vinculo(
                    sessao.cliente_id, sessao.phone_number, cadastro, resolucao
                )
                if classe != "ok":
                    achados.append(
                        {
                            "sessao_id": str(sessao.id),
                            "tenant_id": str(tid),
                            "telefone": sessao.phone_number,
                            "cliente_id_atual": sessao.cliente_id,
                            "situacao": classe,
                            "candidatos": list(resolucao.candidatos),
                        }
                    )
    return achados


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saida", help="arquivo JSON do relatorio")
    parser.add_argument("--tenant-id", help="conferir so uma loja")
    args = parser.parse_args()

    with SessionLocal() as db:
        achados = conferir(db, UUID(args.tenant_id) if args.tenant_id else None)

    resumo = Counter(a["situacao"] for a in achados)
    conteudo = {
        "total_a_revisar": len(achados),
        "resumo": dict(resumo),
        "itens": achados,
    }
    if args.saida:
        with open(args.saida, "w", encoding="utf-8") as arquivo:
            json.dump(conteudo, arquivo, ensure_ascii=False, indent=2)
        print(f"Relatorio gravado em {args.saida}")
    print(
        json.dumps(
            {"total_a_revisar": len(achados), "resumo": dict(resumo)},
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
