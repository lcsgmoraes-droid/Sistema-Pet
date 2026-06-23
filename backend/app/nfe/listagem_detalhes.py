from fastapi import HTTPException
from sqlalchemy.orm import Session
import sys

from app.bling_integration import BlingAPI
from app.nfe.listagem_base import _detalhe_nota_valido, _venda_usa_nfce
from app.nfe.listagem_cache import _obter_detalhe_nfe_cache, _salvar_detalhe_nfe_cache
from app.nfe.listagem_normalizacao import _normalizar_nota_bling
from app.services.nfe_cache_service import obter_detalhe_nota_cache, upsert_nota_cache
from app.vendas_models import Venda


def _compat_attr(name: str, default):
    facade = sys.modules.get("app.nfe.listagem")
    return getattr(facade, name, default) if facade is not None else default


def _buscar_venda_por_nfe_bling_id(db: Session, tenant_id, nfe_id: int) -> Venda | None:
    return (
        db.query(Venda)
        .filter(
            Venda.tenant_id == tenant_id,
            Venda.nfe_bling_id == nfe_id,
        )
        .first()
    )


def _modelos_tentativa_detalhe(
    modelo: int | None,
    venda: Venda | None,
) -> list[int]:
    candidatos: list[int] = []
    modelo_param = str(modelo or "")
    if modelo_param in {"55", "65"}:
        candidatos.append(int(modelo_param))

    modelo_venda = str(getattr(venda, "nfe_modelo", "") or "")
    if modelo_venda in {"55", "65"}:
        candidatos.append(int(modelo_venda))

    candidatos.extend([55, 65])
    return list(dict.fromkeys(candidatos))


def _consultar_detalhe_cache_persistente(
    db: Session,
    tenant_id,
    nfe_id: int,
    modelo: int,
) -> dict | None:
    detalhe_cache = _compat_attr(
        "_obter_detalhe_nfe_cache", _obter_detalhe_nfe_cache
    )(tenant_id, nfe_id, modelo)
    if _detalhe_nota_valido(detalhe_cache):
        return detalhe_cache

    detalhe_cache = _compat_attr(
        "obter_detalhe_nota_cache", obter_detalhe_nota_cache
    )(
        db=db,
        tenant_id=tenant_id,
        nfe_id=nfe_id,
        modelo=modelo,
    )
    return detalhe_cache if _detalhe_nota_valido(detalhe_cache) else None


def _consultar_detalhe_remoto_bling(
    bling: BlingAPI,
    nfe_id: int,
    modelo: int,
) -> dict:
    return bling.consultar_nfce(nfe_id) if modelo == 65 else bling.consultar_nfe(nfe_id)


def _persistir_detalhe_remoto_bling(
    db: Session,
    tenant_id,
    nfe_id: int,
    modelo: int,
    detalhe: dict,
) -> None:
    _salvar_detalhe_nfe_cache(tenant_id, nfe_id, modelo, detalhe)
    _compat_attr("upsert_nota_cache", upsert_nota_cache)(
        db,
        tenant_id,
        _normalizar_nota_bling(detalhe, modelo),
        source="bling_detail",
        resumo_payload=detalhe,
        detalhe_payload=detalhe,
    )
    db.commit()


def _montar_detalhe_venda_local(nfe_id: int, venda: Venda | None) -> dict | None:
    if not venda:
        return None

    return {
        "id": nfe_id,
        "numero": venda.nfe_numero,
        "serie": venda.nfe_serie,
        "chaveAcesso": venda.nfe_chave,
        "situacao": {"descricao": venda.nfe_status} if venda.nfe_status else None,
        "dataEmissao": venda.nfe_data_emissao.isoformat()
        if venda.nfe_data_emissao
        else None,
        "contato": {
            "nome": venda.cliente.nome if venda.cliente else None,
            "cpfCnpj": (venda.cliente.cpf or venda.cliente.cnpj)
            if venda.cliente
            else None,
        },
        "totais": {"valorTotal": float(venda.total or 0)},
    }


def _consultar_detalhe_nota_bling(
    bling: BlingAPI,
    db: Session,
    tenant_id,
    nfe_id: int,
    *,
    modelo: int | None = None,
) -> tuple[dict, int, Venda | None]:
    venda = _buscar_venda_por_nfe_bling_id(db, tenant_id, nfe_id)
    erros: list[str] = []

    for modelo_atual in _modelos_tentativa_detalhe(modelo, venda):
        detalhe = _consultar_detalhe_cache_persistente(
            db,
            tenant_id,
            nfe_id,
            modelo_atual,
        )
        if detalhe:
            return detalhe, modelo_atual, venda

        try:
            detalhe = _consultar_detalhe_remoto_bling(bling, nfe_id, modelo_atual)
        except Exception as exc:
            erros.append(str(exc))
            continue

        if _detalhe_nota_valido(detalhe):
            _persistir_detalhe_remoto_bling(
                db, tenant_id, nfe_id, modelo_atual, detalhe
            )
            return detalhe, modelo_atual, venda

    detalhe_venda = _montar_detalhe_venda_local(nfe_id, venda)
    if detalhe_venda and _detalhe_nota_valido(detalhe_venda):
        modelo_venda = 65 if _venda_usa_nfce(venda) else 55
        return detalhe_venda, modelo_venda, venda

    raise HTTPException(
        status_code=404,
        detail="Nao foi possivel consultar os detalhes desta nota no Bling."
        + (f" Ultimos erros: {' | '.join(erros[:2])}" if erros else ""),
    )
