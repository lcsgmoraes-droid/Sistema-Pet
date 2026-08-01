from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
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
CAMPOS_IDENTIDADE_AUTOMATICA = ("cpf", "cnpj", "crmv")
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
    sinais_confirmacao: list[str]


@dataclass(frozen=True)
class PlanoFusaoAssistidaNome:
    elegivel: bool
    motivos_bloqueio: list[str]
    sinais_confirmacao: list[str]
    decisoes_campos: dict[str, str]
    pessoa_mais_recente_id: int


def normalizar_nome_pessoa(nome: Any) -> str:
    texto = unicodedata.normalize("NFKD", str(nome or ""))
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    texto = re.sub(r"[^a-zA-Z0-9]+", " ", texto.casefold())
    return " ".join(texto.split())


def _normalizar_valor_identidade(campo: str, valor: Any) -> str:
    texto = str(valor or "").strip()
    if not texto:
        return ""
    if campo in {"cpf", "cnpj", "telefone", "celular"}:
        return "".join(ch for ch in texto if ch.isdigit())
    if campo == "crmv":
        return "".join(ch for ch in texto.casefold() if ch.isalnum())
    if campo == "email":
        return texto.casefold()
    return texto.casefold()


def _documento_repetido(valor: str) -> bool:
    return bool(valor) and len(set(valor)) == 1


def _cpf_valido(valor: str) -> bool:
    if len(valor) != 11 or _documento_repetido(valor):
        return False
    for tamanho in (9, 10):
        soma = sum(
            int(valor[indice]) * (tamanho + 1 - indice) for indice in range(tamanho)
        )
        digito = (soma * 10) % 11
        if digito == 10:
            digito = 0
        if digito != int(valor[tamanho]):
            return False
    return True


def _cnpj_valido(valor: str) -> bool:
    if len(valor) != 14 or _documento_repetido(valor):
        return False
    pesos = (
        (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2),
        (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2),
    )
    base = valor[:12]
    for peso in pesos:
        soma = sum(
            int(digito) * multiplicador for digito, multiplicador in zip(base, peso)
        )
        resto = soma % 11
        base += str(0 if resto < 2 else 11 - resto)
    return base == valor


def _identidade_automatica_valida(campo: str, valor: str) -> bool:
    if campo == "cpf":
        return _cpf_valido(valor)
    if campo == "cnpj":
        return _cnpj_valido(valor)
    if campo == "crmv":
        return (
            5 <= len(valor) <= 20
            and sum(ch.isdigit() for ch in valor) >= 3
            and sum(ch.isalpha() for ch in valor) >= 2
        )
    return False


def _valor_preenchido(valor: Any) -> bool:
    if valor is None:
        return False
    if isinstance(valor, str):
        return bool(valor.strip())
    if isinstance(valor, (list, tuple, set, dict)):
        return bool(valor)
    return True


def _chave_recencia_pessoa(pessoa: Any) -> tuple[datetime, int]:
    criado_em = getattr(pessoa, "created_at", None)
    if isinstance(criado_em, datetime):
        if criado_em.tzinfo is not None:
            criado_em = criado_em.astimezone(timezone.utc).replace(tzinfo=None)
    else:
        criado_em = datetime.min
    return criado_em, int(getattr(pessoa, "id", 0) or 0)


def _normalizar_texto(valor: Any) -> str:
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    return " ".join(texto.casefold().split())


def _telefones_normalizados(pessoa: Any) -> set[str]:
    return {
        valor
        for campo in ("telefone", "celular")
        if (valor := _normalizar_valor_identidade(campo, getattr(pessoa, campo, None)))
    }


def _mesma_data_nascimento(pessoa_a: Any, pessoa_b: Any) -> bool:
    data_a = getattr(pessoa_a, "data_nascimento", None)
    data_b = getattr(pessoa_b, "data_nascimento", None)
    return bool(data_a and data_b and str(data_a) == str(data_b))


def _mesmo_endereco(pessoa_a: Any, pessoa_b: Any) -> bool:
    cep_a = _normalizar_valor_identidade("telefone", getattr(pessoa_a, "cep", None))
    cep_b = _normalizar_valor_identidade("telefone", getattr(pessoa_b, "cep", None))
    numero_a = _normalizar_texto(getattr(pessoa_a, "numero", None))
    numero_b = _normalizar_texto(getattr(pessoa_b, "numero", None))
    if cep_a and cep_a == cep_b and numero_a and numero_a == numero_b:
        return True

    endereco_a = _normalizar_texto(getattr(pessoa_a, "endereco", None))
    endereco_b = _normalizar_texto(getattr(pessoa_b, "endereco", None))
    cidade_a = _normalizar_texto(getattr(pessoa_a, "cidade", None))
    cidade_b = _normalizar_texto(getattr(pessoa_b, "cidade", None))
    return bool(
        endereco_a
        and endereco_a == endereco_b
        and numero_a
        and numero_a == numero_b
        and cidade_a
        and cidade_a == cidade_b
    )


def planejar_fusao_assistida_por_nome(
    principal: Any,
    duplicado: Any,
    *,
    aceitar_nome_igual: bool = False,
) -> PlanoFusaoAssistidaNome:
    """Planeja fusao por nome, preservando bloqueios objetivos de identidade."""

    decisao_base = avaliar_par_duplicidade_pessoas(principal, duplicado)
    motivos = [
        motivo
        for motivo in decisao_base.motivos_bloqueio
        if motivo
        in {
            "cpf_conflitante",
            "cnpj_conflitante",
            "crmv_conflitante",
            "email_conflitante",
            "contas_app_diferentes",
            "nome_diferente",
        }
    ]
    sinais = list(decisao_base.sinais_confirmacao)

    email_principal = _normalizar_valor_identidade(
        "email", getattr(principal, "email", None)
    )
    email_duplicado = _normalizar_valor_identidade(
        "email", getattr(duplicado, "email", None)
    )
    if email_principal and email_principal == email_duplicado:
        sinais.append("email")

    if _telefones_normalizados(principal) & _telefones_normalizados(duplicado):
        sinais.append("telefone_compartilhado")

    data_principal = getattr(principal, "data_nascimento", None)
    data_duplicado = getattr(duplicado, "data_nascimento", None)
    if (
        data_principal
        and data_duplicado
        and not _mesma_data_nascimento(principal, duplicado)
    ):
        motivos.append("data_nascimento_conflitante")
    elif _mesma_data_nascimento(principal, duplicado):
        sinais.append("data_nascimento")

    if _mesmo_endereco(principal, duplicado):
        sinais.append("endereco")

    sinais = list(dict.fromkeys(sinais))
    motivos = list(dict.fromkeys(motivos))
    if not sinais and not aceitar_nome_igual:
        motivos.append("sem_evidencia_secundaria_compartilhada")
    elif not sinais:
        sinais.append("nome_igual_confirmado_pelo_dono")

    pessoa_mais_recente = max((principal, duplicado), key=_chave_recencia_pessoa)
    origem_recente = (
        "principal"
        if int(getattr(pessoa_mais_recente, "id", 0) or 0)
        == int(getattr(principal, "id", 0) or 0)
        else "duplicado"
    )
    decisoes_campos = {
        campo: origem_recente
        for campo in ("telefone", "celular")
        if _valor_preenchido(getattr(pessoa_mais_recente, campo, None))
    }

    return PlanoFusaoAssistidaNome(
        elegivel=not motivos,
        motivos_bloqueio=motivos,
        sinais_confirmacao=sinais,
        decisoes_campos=decisoes_campos,
        pessoa_mais_recente_id=int(getattr(pessoa_mais_recente, "id", 0) or 0),
    )


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
    sinais: list[str] = []

    for campo in CAMPOS_IDENTIDADE_FORTE:
        valor_a = _normalizar_valor_identidade(campo, getattr(pessoa_a, campo, None))
        valor_b = _normalizar_valor_identidade(campo, getattr(pessoa_b, campo, None))
        if valor_a and valor_b and valor_a != valor_b:
            motivos.append(f"{campo}_conflitante")
        if (
            campo in CAMPOS_IDENTIDADE_AUTOMATICA
            and valor_a
            and valor_a == valor_b
            and _identidade_automatica_valida(campo, valor_a)
        ):
            sinais.append(campo)

    contas = {
        int(conta_id)
        for conta_id in (
            getattr(pessoa_a, "auth_user_id", None),
            getattr(pessoa_b, "auth_user_id", None),
        )
        if conta_id
    }
    if len(contas) > 1:
        motivos.append("contas_app_diferentes")
    if not sinais:
        motivos.append("sem_identidade_forte_compartilhada")
    if not chave_a or chave_a != chave_b:
        motivos.append("nome_diferente")

    return DecisaoDuplicidadePessoa(
        pode_fundir_automaticamente=bool(sinais)
        and not any(
            motivo.endswith("_conflitante") or motivo == "contas_app_diferentes"
            for motivo in motivos
        ),
        motivos_bloqueio=motivos,
        chave_nome=chave_a,
        sinais_confirmacao=sinais,
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

    def chave(pessoa: Any) -> tuple[int, int, int, int, int, int]:
        pessoa_id = int(getattr(pessoa, "id", 0) or 0)
        ativa = 1 if bool(getattr(pessoa, "ativo", False)) else 0
        perfil_operacional = _prioridade_perfil_pessoa(pessoa)
        referencias = int(referencias_por_id.get(pessoa_id, 0) or 0)
        completude = _score_completude(pessoa)
        conta_vinculada = 1 if getattr(pessoa, "auth_user_id", None) else 0
        return (
            ativa,
            conta_vinculada,
            perfil_operacional,
            referencias,
            completude,
            -pessoa_id,
        )

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
        "auth_user_id": getattr(pessoa, "auth_user_id", None),
        "created_at": getattr(pessoa, "created_at", None),
    }


def _grupos_por_nome_normalizado(pessoas: list[Cliente]) -> dict[str, list[Cliente]]:
    grupos: dict[str, list[Cliente]] = {}
    for pessoa in pessoas:
        chave = normalizar_nome_pessoa(pessoa.nome)
        if not chave:
            continue
        grupos.setdefault(chave, []).append(pessoa)
    return {chave: grupo for chave, grupo in grupos.items() if len(grupo) > 1}


def _grupos_por_identidade_forte(
    pessoas: list[Cliente],
) -> dict[str, list[Cliente]]:
    grupos: dict[str, list[Cliente]] = {}
    for pessoa in pessoas:
        for campo in CAMPOS_IDENTIDADE_AUTOMATICA:
            valor = _normalizar_valor_identidade(campo, getattr(pessoa, campo, None))
            if not _identidade_automatica_valida(campo, valor):
                continue
            grupos.setdefault(f"{campo}:{valor}", []).append(pessoa)
    return {chave: grupo for chave, grupo in grupos.items() if len(grupo) > 1}


def _pares_candidatos(pessoas: list[Cliente]) -> list[tuple[Cliente, Cliente]]:
    pares: dict[tuple[int, int], tuple[Cliente, Cliente]] = {}
    grupos = list(_grupos_por_nome_normalizado(pessoas).values())
    grupos.extend(_grupos_por_identidade_forte(pessoas).values())
    for grupo in grupos:
        principal = escolher_pessoa_principal(grupo)
        for pessoa in grupo:
            if int(pessoa.id) == int(principal.id):
                continue
            chave = tuple(sorted((int(principal.id), int(pessoa.id))))
            pares[chave] = (principal, pessoa)
    return list(pares.values())


def _paginar_sugestoes(itens: list[Any], *, skip: int, limit: int) -> list[Any]:
    inicio = max(int(skip or 0), 0)
    fim = inicio + max(int(limit or 0), 0)
    return itens[inicio:fim]


def listar_sugestoes_duplicidade_pessoas(
    db: Session,
    *,
    tenant_id: Any,
    skip: int = 0,
    limit: int = 50,
) -> dict[str, Any]:
    pessoas = (
        db.query(Cliente)
        .filter(Cliente.tenant_id == tenant_id)
        .filter(Cliente.ativo.is_not(False))
        .filter(func.length(func.trim(func.coalesce(Cliente.nome, ""))) > 0)
        .order_by(Cliente.nome.asc(), Cliente.id.asc())
        .all()
    )

    sugestoes = []
    automaticas = []
    for principal, duplicado in _pares_candidatos(pessoas):
        decisao = avaliar_par_duplicidade_pessoas(principal, duplicado)
        item = {
            "chave_nome": decisao.chave_nome,
            "principal": _resumo_sugestao(principal),
            "duplicado": _resumo_sugestao(duplicado),
            "motivos": decisao.motivos_bloqueio,
            "sinais": decisao.sinais_confirmacao,
        }
        if decisao.pode_fundir_automaticamente:
            automaticas.append(item)
        else:
            sugestoes.append(item)

    inicio = max(int(skip or 0), 0)

    return {
        "sugestoes": _paginar_sugestoes(sugestoes, skip=inicio, limit=limit),
        "total": len(sugestoes),
        "automaticas": _paginar_sugestoes(automaticas, skip=inicio, limit=limit),
        "total_automaticas": len(automaticas),
        "skip": inicio,
        "limit": limit,
    }


def executar_fusoes_assistidas_pessoas_por_nome(
    db: Session,
    *,
    tenant_id: Any,
    user_id: int,
    confirmar: bool = False,
    aceitar_nome_igual: bool = False,
    limit: int = 200,
) -> dict[str, Any]:
    """Simula ou executa fusoes por nome, mantendo conflitos objetivos bloqueados."""

    pessoas = (
        db.query(Cliente)
        .filter(Cliente.tenant_id == tenant_id)
        .filter(Cliente.ativo.is_not(False))
        .filter(func.length(func.trim(func.coalesce(Cliente.nome, ""))) > 0)
        .order_by(Cliente.nome.asc(), Cliente.id.asc())
        .all()
    )
    grupos = _grupos_por_nome_normalizado(pessoas)
    elegiveis: list[dict[str, Any]] = []
    bloqueadas: list[dict[str, Any]] = []
    fusoes: list[dict[str, Any]] = []

    for chave_nome, grupo in grupos.items():
        principal = escolher_pessoa_principal(grupo)
        duplicados = sorted(
            (pessoa for pessoa in grupo if int(pessoa.id) != int(principal.id)),
            key=_chave_recencia_pessoa,
        )

        for duplicado in duplicados:
            plano = planejar_fusao_assistida_por_nome(
                principal,
                duplicado,
                aceitar_nome_igual=aceitar_nome_igual,
            )
            item = {
                "chave_nome": chave_nome,
                "principal": _resumo_sugestao(principal),
                "duplicado": _resumo_sugestao(duplicado),
                "pessoa_mais_recente_id": plano.pessoa_mais_recente_id,
                "sinais": plano.sinais_confirmacao,
                "decisoes_campos": plano.decisoes_campos,
            }
            if not plano.elegivel:
                bloqueadas.append({**item, "motivos": plano.motivos_bloqueio})
                continue
            if len(elegiveis) >= limit:
                continue

            elegiveis.append(item)
            if not confirmar:
                continue

            try:
                resultado = executar_fusao_pessoas(
                    db,
                    tenant_id=tenant_id,
                    principal_id=principal.id,
                    duplicado_id=duplicado.id,
                    decisoes_campos=plano.decisoes_campos,
                    user_id=user_id,
                    observacao=(
                        "Fusao em lote por nome normalizado igual, confirmada pelo dono; "
                        "telefone do cadastro mais recente."
                        if aceitar_nome_igual
                        else "Fusao assistida por nome normalizado igual e evidencia "
                        "secundaria compartilhada; telefone do cadastro mais recente."
                    ),
                    modo=(
                        "nome_igual_confirmado"
                        if aceitar_nome_igual
                        else "assistida_nome_recente"
                    ),
                    motivo=",".join(plano.sinais_confirmacao),
                )
                principal = (
                    db.query(Cliente)
                    .filter(
                        Cliente.tenant_id == tenant_id,
                        Cliente.id == resultado["principal"]["id"],
                    )
                    .first()
                    or principal
                )
                fusoes.append(
                    {
                        **item,
                        "principal": resultado["principal"],
                        "duplicado_inativado": resultado["duplicado_inativado"],
                        "merge_log_id": resultado.get("merge_log_id"),
                    }
                )
            except Exception as exc:
                db.rollback()
                logger.exception("Erro na fusao assistida de pessoas por nome")
                bloqueadas.append({**item, "motivos": [f"erro_fusao: {exc}"]})

    return {
        "simulacao": not confirmar,
        "elegiveis": elegiveis,
        "bloqueadas": bloqueadas,
        "fusoes": fusoes,
        "total_elegiveis": len(elegiveis),
        "total_bloqueadas": len(bloqueadas),
        "total_fundidas": len(fusoes),
        "aceitar_nome_igual": aceitar_nome_igual,
        "limit": limit,
    }


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
        .filter(Cliente.ativo.is_not(False))
        .filter(func.length(func.trim(func.coalesce(Cliente.nome, ""))) > 0)
        .order_by(Cliente.nome.asc(), Cliente.id.asc())
    )

    pessoas = query.all()
    grupos = _grupos_por_identidade_forte(pessoas)
    if nome:
        chave_nome_filtro = normalizar_nome_pessoa(nome)
        grupos = {
            chave: [
                pessoa
                for pessoa in grupo
                if normalizar_nome_pessoa(pessoa.nome) == chave_nome_filtro
            ]
            for chave, grupo in grupos.items()
        }

    fusoes = []
    sugestoes = []
    processados: set[int] = set()
    pares_tentados: set[tuple[int, int]] = set()

    for chave_identidade, grupo in grupos.items():
        grupo = [pessoa for pessoa in grupo if int(pessoa.id) not in processados]
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
            chave_par = tuple(sorted((int(principal.id), int(duplicado.id))))
            if chave_par in pares_tentados:
                continue
            pares_tentados.add(chave_par)

            decisao = avaliar_par_duplicidade_pessoas(principal, duplicado)
            if not decisao.pode_fundir_automaticamente:
                sugestoes.append(
                    {
                        "chave_identidade": chave_identidade,
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
                    observacao=(
                        "Fusao automatica por identidade forte valida e sem conflitos."
                    ),
                    modo="automatica_identidade_forte",
                    motivo=",".join(decisao.sinais_confirmacao),
                )
                principal = (
                    db.query(Cliente)
                    .filter(Cliente.id == resultado["principal"]["id"])
                    .first()
                    or principal
                )
                processados.add(int(duplicado.id))
                fusoes.append(
                    {
                        "chave_identidade": chave_identidade,
                        "principal": resultado["principal"],
                        "duplicado_inativado": resultado["duplicado_inativado"],
                        "merge_log_id": resultado.get("merge_log_id"),
                    }
                )
            except Exception as exc:
                db.rollback()
                logger.exception(
                    "Erro ao executar fusao automatica de pessoas duplicadas"
                )
                sugestoes.append(
                    {
                        "chave_identidade": chave_identidade,
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
