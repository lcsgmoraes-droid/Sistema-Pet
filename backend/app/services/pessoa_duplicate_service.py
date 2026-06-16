from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable
import logging
import re
import unicodedata

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Cliente
from app.services.pessoa_merge_service import executar_fusao_pessoas

logger = logging.getLogger(__name__)


CAMPOS_IDENTIDADE_FORTE = ("cpf", "cnpj", "crmv", "email", "telefone", "celular")
CAMPOS_COMPLETUDE = (
    "codigo",
    "tipo_pessoa",
    "cpf",
    "cnpj",
    "crmv",
    "email",
    "telefone",
    "celular",
    "cep",
    "endereco",
    "numero",
    "bairro",
    "cidade",
    "estado",
    "nome_fantasia",
    "razao_social",
    "observacoes",
)


@dataclass(frozen=True)
class DecisaoDuplicidadePessoa:
    pode_fundir_automaticamente: bool
    motivos_bloqueio: list[str]
    chave_nome: str


def normalizar_nome_pessoa(nome: Any) -> str:
    texto = unicodedata.normalize("NFKD", str(nome or ""))
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    texto = re.sub(r"[^a-zA-Z0-9]+", " ", texto.casefold())
    return " ".join(texto.split())


def _normalizar_valor_identidade(campo: str, valor: Any) -> str:
    texto = str(valor or "").strip()
    if not texto:
        return ""
    if campo in {"cpf", "cnpj", "telefone", "celular", "crmv"}:
        return "".join(ch for ch in texto if ch.isdigit())
    if campo == "email":
        return texto.casefold()
    return texto.casefold()


def _valor_preenchido(valor: Any) -> bool:
    if valor is None:
        return False
    if isinstance(valor, str):
        return bool(valor.strip())
    if isinstance(valor, (list, tuple, set, dict)):
        return bool(valor)
    return True


def _score_completude(pessoa: Any) -> int:
    return sum(
        1
        for campo in CAMPOS_COMPLETUDE
        if _valor_preenchido(getattr(pessoa, campo, None))
    )


def _prioridade_perfil_pessoa(pessoa: Any) -> int:
    if not bool(getattr(pessoa, "ativo", False)):
        return 0
    tipo_cadastro = str(getattr(pessoa, "tipo_cadastro", "") or "").strip().casefold()
    if tipo_cadastro == "funcionario":
        return 3
    if tipo_cadastro == "veterinario":
        return 2
    if bool(getattr(pessoa, "is_entregador", False)):
        return 1
    return 0


def avaliar_par_duplicidade_pessoas(
    pessoa_a: Any, pessoa_b: Any
) -> DecisaoDuplicidadePessoa:
    chave_a = normalizar_nome_pessoa(getattr(pessoa_a, "nome", ""))
    chave_b = normalizar_nome_pessoa(getattr(pessoa_b, "nome", ""))
    motivos: list[str] = []

    if not chave_a or chave_a != chave_b:
        motivos.append("nome_diferente")

    for campo in CAMPOS_IDENTIDADE_FORTE:
        valor_a = _normalizar_valor_identidade(campo, getattr(pessoa_a, campo, None))
        valor_b = _normalizar_valor_identidade(campo, getattr(pessoa_b, campo, None))
        if valor_a and valor_b and valor_a != valor_b:
            motivos.append(f"{campo}_conflitante")

    return DecisaoDuplicidadePessoa(
        pode_fundir_automaticamente=not motivos,
        motivos_bloqueio=motivos,
        chave_nome=chave_a,
    )


def escolher_pessoa_principal(
    pessoas: Iterable[Any],
    *,
    referencias_por_id: dict[int, int] | None = None,
) -> Any:
    pessoas_lista = list(pessoas)
    if not pessoas_lista:
        raise ValueError("Nenhuma pessoa informada para escolher o cadastro principal.")

    referencias_por_id = referencias_por_id or {}

    def chave(pessoa: Any) -> tuple[int, int, int, int, int]:
        pessoa_id = int(getattr(pessoa, "id", 0) or 0)
        ativa = 1 if bool(getattr(pessoa, "ativo", False)) else 0
        perfil_operacional = _prioridade_perfil_pessoa(pessoa)
        referencias = int(referencias_por_id.get(pessoa_id, 0) or 0)
        completude = _score_completude(pessoa)
        return (ativa, perfil_operacional, referencias, completude, -pessoa_id)

    return max(pessoas_lista, key=chave)


def _resumo_sugestao(pessoa: Cliente) -> dict[str, Any]:
    return {
        "id": pessoa.id,
        "codigo": pessoa.codigo,
        "nome": pessoa.nome,
        "tipo_cadastro": pessoa.tipo_cadastro,
        "tipo_pessoa": pessoa.tipo_pessoa,
        "documento": pessoa.cnpj or pessoa.cpf,
        "email": pessoa.email,
        "telefone": pessoa.celular or pessoa.telefone,
        "ativo": pessoa.ativo,
    }


def _grupos_por_nome_normalizado(pessoas: list[Cliente]) -> dict[str, list[Cliente]]:
    grupos: dict[str, list[Cliente]] = {}
    for pessoa in pessoas:
        chave = normalizar_nome_pessoa(pessoa.nome)
        if not chave:
            continue
        grupos.setdefault(chave, []).append(pessoa)
    return {chave: grupo for chave, grupo in grupos.items() if len(grupo) > 1}


def listar_sugestoes_duplicidade_pessoas(
    db: Session,
    *,
    tenant_id: Any,
    limit: int = 50,
) -> dict[str, Any]:
    pessoas = (
        db.query(Cliente)
        .filter(Cliente.tenant_id == tenant_id)
        .filter(Cliente.ativo.is_(True))
        .filter(func.length(func.trim(func.coalesce(Cliente.nome, ""))) > 0)
        .order_by(Cliente.nome.asc(), Cliente.id.asc())
        .all()
    )

    sugestoes = []
    for chave_nome, grupo in _grupos_por_nome_normalizado(pessoas).items():
        principal = escolher_pessoa_principal(grupo)
        for duplicado in grupo:
            if int(duplicado.id) == int(principal.id):
                continue
            decisao = avaliar_par_duplicidade_pessoas(principal, duplicado)
            if decisao.pode_fundir_automaticamente:
                continue
            sugestoes.append(
                {
                    "chave_nome": chave_nome,
                    "principal": _resumo_sugestao(principal),
                    "duplicado": _resumo_sugestao(duplicado),
                    "motivos": decisao.motivos_bloqueio,
                }
            )
            if len(sugestoes) >= limit:
                return {"sugestoes": sugestoes, "total": len(sugestoes)}

    return {"sugestoes": sugestoes, "total": len(sugestoes)}


def executar_fusoes_automaticas_pessoas_duplicadas(
    db: Session,
    *,
    tenant_id: Any,
    user_id: int,
    limit: int = 25,
    nome: str | None = None,
) -> dict[str, Any]:
    query = (
        db.query(Cliente)
        .filter(Cliente.tenant_id == tenant_id)
        .filter(Cliente.ativo.is_(True))
        .filter(func.length(func.trim(func.coalesce(Cliente.nome, ""))) > 0)
        .order_by(Cliente.nome.asc(), Cliente.id.asc())
    )

    pessoas = query.all()
    grupos = _grupos_por_nome_normalizado(pessoas)
    if nome:
        chave_nome_filtro = normalizar_nome_pessoa(nome)
        grupos = (
            {chave_nome_filtro: grupos.get(chave_nome_filtro, [])}
            if chave_nome_filtro
            else {}
        )

    fusoes = []
    sugestoes = []

    for chave_nome, grupo in grupos.items():
        if len(grupo) < 2:
            continue
        principal = escolher_pessoa_principal(grupo)
        for duplicado in grupo:
            if len(fusoes) >= limit:
                return {
                    "automaticas": fusoes,
                    "sugestoes": sugestoes,
                    "total_automaticas": len(fusoes),
                }
            if int(duplicado.id) == int(principal.id):
                continue

            decisao = avaliar_par_duplicidade_pessoas(principal, duplicado)
            if not decisao.pode_fundir_automaticamente:
                sugestoes.append(
                    {
                        "chave_nome": chave_nome,
                        "principal": _resumo_sugestao(principal),
                        "duplicado": _resumo_sugestao(duplicado),
                        "motivos": decisao.motivos_bloqueio,
                    }
                )
                continue

            try:
                resultado = executar_fusao_pessoas(
                    db,
                    tenant_id=tenant_id,
                    principal_id=principal.id,
                    duplicado_id=duplicado.id,
                    decisoes_campos={},
                    user_id=user_id,
                    observacao="Fusao automatica por nome 100% igual e sem conflitos fortes.",
                )
                principal = (
                    db.query(Cliente)
                    .filter(Cliente.id == resultado["principal"]["id"])
                    .first()
                    or principal
                )
                fusoes.append(
                    {
                        "chave_nome": chave_nome,
                        "principal": resultado["principal"],
                        "duplicado_inativado": resultado["duplicado_inativado"],
                    }
                )
            except Exception as exc:
                db.rollback()
                logger.exception(
                    "Erro ao executar fusao automatica de pessoas duplicadas"
                )
                sugestoes.append(
                    {
                        "chave_nome": chave_nome,
                        "principal": _resumo_sugestao(principal),
                        "duplicado": _resumo_sugestao(duplicado),
                        "motivos": [f"erro_fusao: {exc}"],
                    }
                )

    return {
        "automaticas": fusoes,
        "sugestoes": sugestoes,
        "total_automaticas": len(fusoes),
    }
