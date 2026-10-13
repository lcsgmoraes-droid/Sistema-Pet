"""Edição fiscal explícita de itens de uma tentativa IntNFe rejeitada."""

from __future__ import annotations

import re
from decimal import Decimal
from types import SimpleNamespace

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy.orm import Session

from app.audit_log import log_action
from app.auth.dependencies import get_current_user_and_tenant
from app.bling_integration_fiscal import _resolver_fiscal_item_nfe
from app.db import get_session
from app.empresa_config_fiscal_models import EmpresaConfigFiscal
from app.intnfe.emission import DirectEmissionError, _lot_from_recorded_fifo
from app.intnfe.repository import get_tenant
from app.kit_config_fiscal_models import KitConfigFiscal
from app.produto_config_fiscal_models import ProdutoConfigFiscal
from app.produtos_models import Produto, ProdutoLote
from app.vendas_models import Venda, VendaItem

router = APIRouter(tags=["NF-e"])

CAMPO_CONFIG = {
    "ncm": "ncm",
    "cest": "cest",
    "origem_mercadoria": "origem_mercadoria",
    "cfop": "cfop_venda",
    "cst_icms": "cst_icms",
    "cst_pis": "pis_cst",
    "cst_cofins": "cofins_cst",
    "aliquota_icms": "icms_aliquota",
    "aliquota_pis": "pis_aliquota",
    "aliquota_cofins": "cofins_aliquota",
}
CAMPO_LOTE = {
    "ncm": "fiscal_ncm",
    "cest": "fiscal_cest",
    "origem_mercadoria": "fiscal_origem_mercadoria",
}
CAMPO_LEGADO = {
    "ncm": "ncm", "cest": "cest", "origem_mercadoria": "origem",
    "cfop": "cfop", "aliquota_icms": "aliquota_icms",
    "aliquota_pis": "aliquota_pis", "aliquota_cofins": "aliquota_cofins",
}
IDENTIFICACAO_LEGADA = {"ncm", "cest", "origem_mercadoria", "cfop"}


class CorrecaoFiscalItemRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ncm: str | None = None
    cest: str | None = None
    origem_mercadoria: str | None = None
    cfop: str | None = None
    cst_icms: str | None = None
    cst_pis: str | None = None
    cst_cofins: str | None = None
    aliquota_icms: Decimal | None = None
    aliquota_pis: Decimal | None = None
    aliquota_cofins: Decimal | None = None

    @field_validator(
        "ncm", "cest", "origem_mercadoria", "cfop", "cst_icms",
        "cst_pis", "cst_cofins", mode="before",
    )
    @classmethod
    def validar_codigo(cls, value, info):
        campo = info.field_name
        text = re.sub(r"[.\s]", "", str(value if value is not None else ""))
        if campo == "cest" and not text:
            return None
        tamanhos = {
            "ncm": {8}, "cest": {7}, "origem_mercadoria": {1},
            "cfop": {4}, "cst_icms": {2, 3}, "cst_pis": {2}, "cst_cofins": {2},
        }
        if not text.isascii() or not text.isdigit() or len(text) not in tamanhos[campo]:
            raise ValueError("Informe um código fiscal válido, com a quantidade correta de dígitos.")
        if campo == "ncm" and text == "00000000":
            raise ValueError("Informe um NCM válido com 8 dígitos.")
        if campo == "origem_mercadoria" and text not in "012345678":
            raise ValueError("A origem da mercadoria deve estar entre 0 e 8.")
        if campo == "cfop" and text[0] not in "567":
            raise ValueError("Informe um CFOP de saída iniciado em 5, 6 ou 7.")
        return text

    @field_validator("aliquota_icms", "aliquota_pis", "aliquota_cofins")
    @classmethod
    def validar_aliquota(cls, value):
        if value is not None and (
            not value.is_finite() or value < 0 or value > 100
            or value != value.quantize(Decimal("0.01"))
        ):
            raise ValueError("A alíquota deve estar entre 0 e 100, com até duas casas decimais.")
        return value


def _consulta(db, modelo, *filtros, travar=False):
    query = db.query(modelo).filter(*filtros)
    if travar:
        query = query.populate_existing().with_for_update()
    return query.first()


def _exigir_rejeitada(venda):
    if (
        str(venda.nfe_status or "").strip().casefold() != "rejeitada"
        or venda.nfe_provider != "intnfe"
        or venda.nfe_bling_id
        or venda.nfe_protocolo
        or venda.nfe_data_autorizacao
    ):
        raise HTTPException(
            status_code=409,
            detail="A edição fiscal só está disponível para uma nota IntNFe confirmada como rejeitada, sem autorização.",
        )


def _carregar_contexto(db, tenant_id, venda_id, item_id, *, travar=False):
    venda = _consulta(
        db, Venda, Venda.id == venda_id, Venda.tenant_id == tenant_id, travar=travar,
    )
    if venda is None:
        raise HTTPException(status_code=404, detail="Venda não encontrada.")
    _exigir_rejeitada(venda)
    item = _consulta(
        db, VendaItem, VendaItem.id == item_id, VendaItem.venda_id == venda_id,
        VendaItem.tenant_id == tenant_id, travar=travar,
    )
    if item is None or item.tipo != "produto" or not item.produto_id:
        raise HTTPException(status_code=404, detail="Item de produto não encontrado nesta venda.")
    produto = _consulta(
        db, Produto, Produto.id == item.produto_id, Produto.tenant_id == tenant_id,
        travar=travar,
    )
    if produto is None or getattr(item, "estoque_origem_tenant_id", None):
        raise HTTPException(status_code=409, detail="O produto deve pertencer à empresa desta venda para corrigir seus dados fiscais.")
    lote_id = item.lote_id
    if not lote_id:
        try:
            inferred = _lot_from_recorded_fifo(db, venda, item)
        except DirectEmissionError as exc:
            raise HTTPException(status_code=exc.status, detail=str(exc)) from exc
        lote_id = inferred.id if inferred is not None else None
    lote = None
    if lote_id:
        lote = _consulta(
            db, ProdutoLote, ProdutoLote.id == lote_id,
            ProdutoLote.produto_id == produto.id, ProdutoLote.tenant_id == tenant_id,
            travar=travar,
        )
        if lote is None:
            raise HTTPException(status_code=409, detail="O lote deste item não pertence ao produto e à empresa da venda.")
    fiscal_produto = _consulta(
        db, ProdutoConfigFiscal, ProdutoConfigFiscal.produto_id == produto.id,
        ProdutoConfigFiscal.tenant_id == tenant_id, travar=travar,
    )
    fiscal_kit = None
    if produto.tipo_produto == "KIT":
        fiscal_kit = _consulta(
            db, KitConfigFiscal, KitConfigFiscal.produto_kit_id == produto.id,
            KitConfigFiscal.tenant_id == tenant_id, travar=travar,
        )
    empresa = _consulta(db, EmpresaConfigFiscal, EmpresaConfigFiscal.tenant_id == tenant_id)
    return SimpleNamespace(
        venda=venda, item=item, produto=produto, lote=lote,
        fiscal_produto=fiscal_produto, fiscal_kit=fiscal_kit, empresa=empresa,
    )


def _valor_json(value):
    return float(value) if isinstance(value, Decimal) else value


def _fiscal_efetivo(db, contexto):
    resolved = _resolver_fiscal_item_nfe(
        db, contexto.venda,
        SimpleNamespace(produto=contexto.produto, lote=contexto.lote),
    )
    tenant = get_tenant(db, contexto.venda.tenant_id)
    cliente = getattr(contexto.venda, "cliente", None)
    uf_emissor = str(getattr(tenant, "uf", None) or "").strip().upper()
    uf_destino = str(getattr(cliente, "estado", None) or uf_emissor).strip().upper()
    interestadual = (
        str(getattr(contexto.venda, "nfe_tipo", None) or "nfce").lower() == "nfe"
        and uf_destino != uf_emissor
    )
    if interestadual and cliente is not None and not str(getattr(cliente, "inscricao_estadual", None) or "").strip():
        cfop = resolved.get("cfop_interestadual_nao_contribuinte")
    else:
        cfop = resolved.get("cfop_interestadual" if interestadual else "cfop_interno")
    fiscal = {
        campo: _valor_json(resolved.get("cfop" if campo == "cfop" else atributo))
        for campo, atributo in CAMPO_CONFIG.items()
    }
    fiscal["cfop"] = cfop
    return fiscal


def _fontes_fiscais(contexto, fiscal):
    fontes = {}
    for campo, atributo in CAMPO_CONFIG.items():
        if getattr(contexto.fiscal_kit, atributo, None) not in (None, ""):
            fontes[campo] = {"tipo": "kit", "id": contexto.produto.id}
        elif campo in CAMPO_LOTE and getattr(contexto.lote, CAMPO_LOTE[campo], None) not in (None, ""):
            fontes[campo] = {"tipo": "lote", "id": contexto.lote.id}
        elif getattr(contexto.fiscal_produto, atributo, None) not in (None, "") or (
            contexto.fiscal_produto is None and campo in IDENTIFICACAO_LEGADA
            and getattr(contexto.produto, CAMPO_LEGADO[campo], None) not in (None, "")
        ):
            fontes[campo] = {"tipo": "produto", "id": contexto.produto.id}
        else:
            fontes[campo] = {"tipo": "empresa", "id": getattr(contexto.empresa, "id", None)}
    lote_st = getattr(contexto.lote, "fiscal_icms_st", None)
    icms_st = lote_st if lote_st is not None else getattr(contexto.fiscal_produto, "icms_st", False)
    regime = str(getattr(contexto.empresa, "regime_tributario", None) or "").casefold()
    simples = bool(getattr(contexto.empresa, "simples_ativo", False) or "simples" in regime)
    if icms_st and simples:
        for campo in ("cfop", "aliquota_icms"):
            fontes[campo] = {"tipo": "regra_icms_st", "id": getattr(contexto.lote, "id", contexto.produto.id)}
        if not getattr(contexto.fiscal_kit, "cst_icms", None):
            fontes["cst_icms"] = {"tipo": "regra_icms_st", "id": getattr(contexto.lote, "id", contexto.produto.id)}
    elif fontes["cfop"]["tipo"] != "empresa":
        config = contexto.fiscal_kit if fontes["cfop"]["tipo"] == "kit" else contexto.fiscal_produto
        especifico = getattr(config, "cfop_venda", None) if config is not None else contexto.produto.cfop
        if especifico != fiscal["cfop"]:
            fontes["cfop"] = {"tipo": "empresa", "id": getattr(contexto.empresa, "id", None)}
    return fontes


@router.get("/vendas/{venda_id}/itens/{item_id}/fiscal")
def obter_fiscal_item_rejeitado(
    venda_id: int, item_id: int, db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _user, tenant_id = user_and_tenant
    contexto = _carregar_contexto(db, tenant_id, venda_id, item_id)
    fiscal = _fiscal_efetivo(db, contexto)
    return {
        "venda_id": venda_id, "item_id": item_id, "produto_id": contexto.produto.id,
        "lote_id": getattr(contexto.lote, "id", None), "nome": contexto.produto.nome,
        "fiscal": fiscal,
        "fontes_fiscais": _fontes_fiscais(contexto, fiscal), "editavel": True,
    }


def _aplicar_patch(db, contexto, patch):
    is_kit = contexto.produto.tipo_produto == "KIT"
    config = contexto.fiscal_kit if is_kit else contexto.fiscal_produto
    if config is None:
        if is_kit:
            config = KitConfigFiscal(
                tenant_id=contexto.venda.tenant_id, produto_kit_id=contexto.produto.id,
                herdado_da_empresa=False,
            )
        else:
            config = ProdutoConfigFiscal(
                tenant_id=contexto.venda.tenant_id, produto_id=contexto.produto.id,
                herdado_da_empresa=False,
            )
            # A presença do V2 torna seus campos autoritativos; preservar o legado.
            for campo in IDENTIFICACAO_LEGADA:
                setattr(config, CAMPO_CONFIG[campo], getattr(contexto.produto, CAMPO_LEGADO[campo], None))
        db.add(config)
    fontes = [{"tipo": "kit" if is_kit else "produto", "id": contexto.produto.id, "campos": list(patch)}]
    for campo, valor in patch.items():
        setattr(config, CAMPO_CONFIG[campo], valor)
    config.herdado_da_empresa = False
    # O snapshot do lote precede o cadastro do produto na emissão.
    campos_lote = []
    if contexto.lote is not None and not is_kit:
        for campo, atributo in CAMPO_LOTE.items():
            if campo in patch and getattr(contexto.lote, atributo, None) not in (None, ""):
                setattr(contexto.lote, atributo, patch[campo])
                campos_lote.append(campo)
    if campos_lote:
        fontes.append({"tipo": "lote", "id": contexto.lote.id, "campos": campos_lote})
    for campo in patch:
        if campo in CAMPO_LEGADO:
            value = getattr(config, CAMPO_CONFIG[campo])
            setattr(contexto.produto, CAMPO_LEGADO[campo], _valor_json(value))
    return fontes


@router.put("/vendas/{venda_id}/itens/{item_id}/fiscal")
def salvar_fiscal_item_rejeitado(
    venda_id: int, item_id: int, request: CorrecaoFiscalItemRequest,
    db: Session = Depends(get_session), user_and_tenant=Depends(get_current_user_and_tenant),
):
    user, tenant_id = user_and_tenant
    patch = request.model_dump(exclude_unset=True)
    if not patch:
        raise HTTPException(status_code=422, detail="Informe ao menos um campo fiscal para corrigir.")
    try:
        contexto = _carregar_contexto(db, tenant_id, venda_id, item_id, travar=True)
        antes = _fiscal_efetivo(db, contexto)
        fontes = _aplicar_patch(db, contexto, patch)
        db.flush()
        depois = _fiscal_efetivo(db, contexto)
        for campo in patch:
            if depois[campo] != _valor_json(patch[campo]):
                raise HTTPException(
                    status_code=409,
                    detail=f"A regra fiscal da empresa ou do lote prevalece sobre o campo {campo}. Revise essa regra antes de reenviar a nota.",
                )
        log_action(
            db, user.id, "corrigir_item_nfe_rejeitada", entity_type="venda",
            entity_id=venda_id, old_value={campo: antes[campo] for campo in patch},
            new_value={"item_id": item_id, "campos": {campo: depois[campo] for campo in patch}, "fontes_atualizadas": fontes},
            tenant_id=tenant_id, commit=False,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {
        "message": "Correção fiscal salva. Revalide os dados antes de reenviar a nota.",
        "venda_id": venda_id, "item_id": item_id, "campos_alterados": list(patch),
        "fontes_atualizadas": fontes,
    }
