"""Aprendizado de classificacao para contas a pagar.

Usa a tabela existente de regras DRE como memoria do tenant e guarda os
campos de classificacao operacional dentro do JSON de criterios.
"""

from __future__ import annotations

from typing import Iterable, Optional
import re
import unicodedata

from sqlalchemy.orm import Session

from app.dre_regras_models import (
    OrigemRegra,
    RegraClassificacaoDRE,
    TipoRegraClassificacao,
)
from app.financeiro_models import ContaPagar


TIPOS_REGRAS_CONTAS_PAGAR = (
    TipoRegraClassificacao.BENEFICIARIO,
    TipoRegraClassificacao.PALAVRA_CHAVE,
    TipoRegraClassificacao.COMBO,
)


def _normalizar_texto(valor: Optional[str]) -> str:
    texto = str(valor or "").strip().lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    texto = texto.replace("-", " ")
    return re.sub(r"\s+", " ", texto).strip()


def normalizar_chave_descricao_conta_pagar(descricao: Optional[str]) -> str:
    """Remove partes variaveis para comparar lancamentos similares."""
    texto = _normalizar_texto(descricao)
    if not texto:
        return ""

    cortes = (
        r"\s+venda\s+\d+.*$",
        r"\s+parcela\s+\d+(?:\s*/\s*\d+)?.*$",
        r"\s+recorrencia\s+\d{1,2}\s*/\s*\d{4}.*$",
        r"\s+\(recorrencia\s+\d{1,2}\s*/\s*\d{4}\).*$",
    )
    for padrao in cortes:
        texto = re.sub(padrao, "", texto).strip()

    texto = re.sub(r"^nf\s*e?\s*\d+\s*", "nf e ", texto).strip()
    texto = re.sub(r"\b\d{5,}\b", "", texto).strip()
    return re.sub(r"\s+", " ", texto).strip()


def prefixo_busca_descricao_conta_pagar(descricao: Optional[str]) -> str:
    chave = normalizar_chave_descricao_conta_pagar(descricao)
    partes = chave.split()
    if len(partes) >= 2:
        return " ".join(partes[:2])
    return chave


def _criterios_da_regra(regra: RegraClassificacaoDRE) -> dict:
    criterios = regra.criterios or {}
    return criterios if isinstance(criterios, dict) else {}


def _regra_compativel_com_conta(
    conta: ContaPagar, regra: RegraClassificacaoDRE
) -> bool:
    criterios = _criterios_da_regra(regra)
    if not criterios.get("contas_pagar"):
        return False

    fornecedor_id = criterios.get("fornecedor_id")
    if fornecedor_id is not None:
        return conta.fornecedor_id is not None and int(fornecedor_id) == int(
            conta.fornecedor_id
        )

    descricao_chave = _normalizar_texto(criterios.get("descricao_chave"))
    if descricao_chave:
        return (
            normalizar_chave_descricao_conta_pagar(conta.descricao) == descricao_chave
        )

    return False


def _aplicar_regra_na_conta(
    conta: ContaPagar, regra: RegraClassificacaoDRE, *, sobrescrever: bool = False
) -> bool:
    criterios = _criterios_da_regra(regra)
    alterou = False

    if regra.dre_subcategoria_id and (sobrescrever or not conta.dre_subcategoria_id):
        conta.dre_subcategoria_id = regra.dre_subcategoria_id
        alterou = True
    if regra.canal and (sobrescrever or not conta.canal):
        conta.canal = regra.canal
        alterou = True

    categoria_id = criterios.get("categoria_id")
    if categoria_id is not None and (sobrescrever or not conta.categoria_id):
        conta.categoria_id = int(categoria_id)
        alterou = True

    tipo_despesa_id = criterios.get("tipo_despesa_id")
    if tipo_despesa_id is not None and (sobrescrever or not conta.tipo_despesa_id):
        conta.tipo_despesa_id = int(tipo_despesa_id)
        alterou = True

    canal = criterios.get("canal")
    if canal and (sobrescrever or not conta.canal):
        conta.canal = str(canal)
        alterou = True

    return alterou


def _query_regras_contas_pagar(db: Session, tenant_id):
    return (
        db.query(RegraClassificacaoDRE)
        .filter(
            RegraClassificacaoDRE.tenant_id == tenant_id,
            RegraClassificacaoDRE.ativo.is_(True),
            RegraClassificacaoDRE.tipo_regra.in_(TIPOS_REGRAS_CONTAS_PAGAR),
            RegraClassificacaoDRE.origem.in_(
                (OrigemRegra.APRENDIZADO, OrigemRegra.USUARIO)
            ),
        )
        .order_by(
            RegraClassificacaoDRE.prioridade.desc(), RegraClassificacaoDRE.id.desc()
        )
    )


def buscar_regra_classificacao_conta_pagar(
    db: Session,
    tenant_id,
    conta: ContaPagar,
) -> Optional[RegraClassificacaoDRE]:
    for regra in _query_regras_contas_pagar(db, tenant_id).all():
        if _regra_compativel_com_conta(conta, regra):
            return regra
    return None


def aplicar_classificacao_aprendida_conta_pagar(
    db: Session,
    tenant_id,
    conta: ContaPagar,
) -> bool:
    regra = buscar_regra_classificacao_conta_pagar(db, tenant_id, conta)
    if not regra:
        return False

    alterou = _aplicar_regra_na_conta(conta, regra, sobrescrever=False)
    if alterou:
        regra.aplicacoes_sucesso = (regra.aplicacoes_sucesso or 0) + 1
    return alterou


def _campos_classificacao_presentes(conta: ContaPagar, campos: Iterable[str]) -> dict:
    campos_set = set(campos or ())
    dados = {}
    if "categoria_id" in campos_set and conta.categoria_id is not None:
        dados["categoria_id"] = int(conta.categoria_id)
    if "tipo_despesa_id" in campos_set and conta.tipo_despesa_id is not None:
        dados["tipo_despesa_id"] = int(conta.tipo_despesa_id)
    if "canal" in campos_set and conta.canal:
        dados["canal"] = conta.canal
    return dados


def _dados_regra_para_conta(conta: ContaPagar, campos: Iterable[str]) -> Optional[dict]:
    if not conta.dre_subcategoria_id:
        return None

    campos_extras = _campos_classificacao_presentes(conta, campos)
    if not campos_extras and "dre_subcategoria_id" not in set(campos or ()):
        return None

    if conta.fornecedor_id:
        criterios = {
            "contas_pagar": True,
            "fornecedor_id": int(conta.fornecedor_id),
            "descricao_chave": normalizar_chave_descricao_conta_pagar(conta.descricao),
            **campos_extras,
        }
        return {
            "tipo_regra": TipoRegraClassificacao.BENEFICIARIO,
            "nome": f"Contas a pagar fornecedor #{conta.fornecedor_id}",
            "criterios": criterios,
        }

    descricao_chave = normalizar_chave_descricao_conta_pagar(conta.descricao)
    if len(descricao_chave) < 4:
        return None

    return {
        "tipo_regra": TipoRegraClassificacao.PALAVRA_CHAVE,
        "nome": f"Contas a pagar: {descricao_chave[:80]}",
        "criterios": {
            "contas_pagar": True,
            "descricao_chave": descricao_chave,
            **campos_extras,
        },
    }


def registrar_regra_classificacao_conta_pagar(
    db: Session,
    tenant_id,
    conta: ContaPagar,
    *,
    user_id: Optional[int],
    campos: Iterable[str],
) -> Optional[RegraClassificacaoDRE]:
    dados = _dados_regra_para_conta(conta, campos)
    if not dados:
        return None

    regra_existente = None
    for regra in _query_regras_contas_pagar(db, tenant_id).all():
        if _regra_compativel_com_conta(conta, regra):
            regra_existente = regra
            break

    criterios = dados["criterios"]
    if regra_existente:
        criterios_antigos = _criterios_da_regra(regra_existente)
        regra_existente.criterios = {**criterios_antigos, **criterios}
        regra_existente.dre_subcategoria_id = conta.dre_subcategoria_id
        regra_existente.canal = conta.canal or regra_existente.canal
        regra_existente.sugerir_apenas = False
        regra_existente.confianca = max(regra_existente.confianca or 0, 95)
        return regra_existente

    regra = RegraClassificacaoDRE(
        tenant_id=tenant_id,
        nome=dados["nome"],
        descricao="Criada automaticamente ao classificar conta a pagar",
        tipo_regra=dados["tipo_regra"],
        origem=OrigemRegra.APRENDIZADO,
        criterios=criterios,
        dre_subcategoria_id=conta.dre_subcategoria_id,
        canal=conta.canal,
        prioridade=95 if conta.fornecedor_id else 90,
        confianca=95,
        aplicacoes_sucesso=1,
        ativo=True,
        sugerir_apenas=False,
        criado_por_user_id=user_id,
    )
    db.add(regra)
    return regra


def aplicar_classificacao_similar_contas_pagar(
    db: Session,
    tenant_id,
    conta: ContaPagar,
    *,
    campos: Iterable[str],
    regra: Optional[RegraClassificacaoDRE] = None,
    user_id: Optional[int] = None,
) -> int:
    if regra is None:
        regra = registrar_regra_classificacao_conta_pagar(
            db,
            tenant_id,
            conta,
            user_id=user_id,
            campos=campos,
        )
    if not regra:
        return 0

    query = db.query(ContaPagar).filter(
        ContaPagar.tenant_id == tenant_id,
        ContaPagar.id != conta.id,
    )

    if conta.fornecedor_id:
        query = query.filter(ContaPagar.fornecedor_id == conta.fornecedor_id)
        candidatas = query.all()
    else:
        prefixo = prefixo_busca_descricao_conta_pagar(conta.descricao)
        if not prefixo:
            return 0
        candidatas = query.filter(ContaPagar.descricao.ilike(f"{prefixo}%")).all()

    atualizadas = 0
    for candidata in candidatas:
        if not _regra_compativel_com_conta(candidata, regra):
            continue
        if _aplicar_regra_na_conta(candidata, regra, sobrescrever=True):
            atualizadas += 1
    return atualizadas
