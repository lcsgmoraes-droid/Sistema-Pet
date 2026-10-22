"""Servico unico de identificacao do tutor pelo telefone do WhatsApp.

Antes existiam duas regras diferentes (uma frouxa, na criacao da sessao, e uma
rigida, na hora de consultar dados). Agora todo o atendimento usa esta: um
telefone so identifica um tutor quando existe exatamente um cadastro compativel
na loja. Dois cadastros com o mesmo numero (ambiguidade) ou nenhum cadastro
nunca escolhem um tutor "no palpite".

Comparacao de telefones brasileiros: os 8 ultimos digitos precisam ser iguais e,
quando os dois numeros trazem o DDD, o DDD tambem. O 9o digito e o codigo do
pais (55) nao atrapalham: "5511999998888", "(11) 99999-8888" e "11 9999-8888"
sao o mesmo numero.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import or_

from app.models import Cliente

SITUACAO_UNICO = "unico"
SITUACAO_NENHUM = "nenhum"
SITUACAO_AMBIGUO = "ambiguo"
SITUACAO_INVALIDO = "invalido"

LIMITE_CANDIDATOS = 50


@dataclass(frozen=True)
class ResolucaoTutor:
    """Resultado da identificacao: so `unico` traz um cliente_id."""

    situacao: str
    cliente_id: int | None = None
    candidatos: tuple = ()


def somente_digitos(valor: Any) -> str:
    return "".join(c for c in str(valor or "") if c.isdigit())


def chave_telefone(valor: Any) -> tuple[str | None, str] | None:
    """Devolve (ddd ou None, ultimos 8 digitos), ou None se nao for um telefone.

    Identificadores internos do WhatsApp (@lid) nao sao telefone.
    """
    if "@lid" in str(valor or ""):
        return None
    digitos = somente_digitos(valor)
    if len(digitos) < 8:
        return None
    resto = digitos[2:] if digitos.startswith("55") and len(digitos) >= 12 else digitos
    anterior = resto[:-8]
    ddd = anterior[:2] if len(anterior) >= 2 else None
    return ddd, digitos[-8:]


def telefones_compativeis(a: Any, b: Any) -> bool:
    chave_a, chave_b = chave_telefone(a), chave_telefone(b)
    if chave_a is None or chave_b is None:
        return False
    if chave_a[1] != chave_b[1]:
        return False
    ddd_a, ddd_b = chave_a[0], chave_b[0]
    return ddd_a is None or ddd_b is None or ddd_a == ddd_b


def resolver_tutor_por_telefone(
    db, tenant_id, phone: Any, *, limite: int = LIMITE_CANDIDATOS
) -> ResolucaoTutor:
    """Identifica o tutor da loja pelo telefone, sem nunca chutar."""
    chave = chave_telefone(phone)
    if chave is None:
        return ResolucaoTutor(SITUACAO_INVALIDO)

    ultimos4 = chave[1][-4:]
    consulta = db.query(Cliente.id, Cliente.celular, Cliente.telefone).filter(
        Cliente.tenant_id == tenant_id,
        or_(
            Cliente.celular.ilike(f"%{ultimos4}%"),
            Cliente.telefone.ilike(f"%{ultimos4}%"),
        ),
    )
    # Cadastros fundidos em outro nao participam da identificacao.
    fundido_em = getattr(Cliente, "merged_into_id", None)
    if fundido_em is not None:
        consulta = consulta.filter(fundido_em.is_(None))

    compativeis = sorted(
        {
            linha.id
            for linha in consulta.limit(limite).all()
            if any(
                telefones_compativeis(phone, telefone)
                for telefone in (linha.celular, linha.telefone)
                if telefone
            )
        }
    )
    if len(compativeis) == 1:
        return ResolucaoTutor(SITUACAO_UNICO, compativeis[0], tuple(compativeis))
    if not compativeis:
        return ResolucaoTutor(SITUACAO_NENHUM)
    return ResolucaoTutor(SITUACAO_AMBIGUO, None, tuple(compativeis))
