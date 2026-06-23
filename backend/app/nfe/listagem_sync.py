from datetime import datetime, timedelta
import sys
from time import monotonic, sleep

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.bling_integration import BlingAPI
from app.nfe.listagem_base import (
    _canal_label,
    _canal_slug,
    _coerce_float,
    _coerce_int,
    _detalhe_nota_valido,
    _dict,
    _extrair_valor_nota,
    _primeiro_preenchido,
    _status_nota_bling,
    _texto,
    _venda_usa_nfce,
)
from app.nfe.listagem_cache import _obter_detalhe_nfe_cache, _salvar_detalhe_nfe_cache
from app.nfe.listagem_detalhes import (
    _consultar_detalhe_cache_persistente,
    _consultar_detalhe_remoto_bling,
)
from app.nfe.listagem_normalizacao import (
    _normalizar_nota_bling,
    _normalizar_nota_venda_local,
    _normalizar_resumo_canal,
)
from app.nfe.listagem_pedidos import (
    _enriquecer_notas_com_pedidos_integrados,
    _normalizar_nota_pedido_integrado,
)
from app.pedido_integrado_models import PedidoIntegrado
from app.services.bling_sync_service import BlingSyncService
from app.services.nfe_cache_service import obter_estado_cache_notas, upsert_nota_cache
from app.utils.logger import logger
from app.vendas_models import Venda


def _compat_attr(name: str, default):
    facade = sys.modules.get("app.nfe.listagem")
    return getattr(facade, name, default) if facade is not None else default


def _sincronizar_vendas_em_cache(
    db: Session,
    tenant_id,
    *,
    desde: datetime | None = None,
) -> None:
    query = db.query(Venda).filter(
        Venda.tenant_id == tenant_id,
        Venda.nfe_bling_id.isnot(None),
    )
    if desde:
        query = query.filter(
            or_(
                Venda.updated_at >= desde,
                Venda.nfe_data_emissao >= desde,
            )
        )

    for venda in query.order_by(
        Venda.updated_at.desc(), Venda.nfe_data_emissao.desc()
    ).all():
        upsert_nota_cache(
            db,
            tenant_id,
            _normalizar_nota_venda_local(venda),
            source="local_venda",
        )


def _sincronizar_pedidos_integrados_em_cache(
    db: Session,
    tenant_id,
    *,
    desde: datetime | None = None,
    limite_scan: int = 2000,
) -> None:
    query = db.query(PedidoIntegrado).filter(PedidoIntegrado.tenant_id == tenant_id)
    if desde:
        query = query.filter(PedidoIntegrado.updated_at >= desde)

    pedidos = (
        query.order_by(
            PedidoIntegrado.updated_at.desc(), PedidoIntegrado.created_at.desc()
        )
        .limit(limite_scan)
        .all()
    )
    for pedido in pedidos:
        nota = _normalizar_nota_pedido_integrado(pedido)
        if not nota or not _texto(nota.get("id")):
            continue
        upsert_nota_cache(
            db,
            tenant_id,
            nota,
            source="pedido_integrado",
            resumo_payload=_dict(pedido.payload),
        )


def _sincronizar_fontes_locais_nfe_em_cache(
    db: Session,
    tenant_id,
    *,
    estado_cache: dict | None = None,
    force_refresh: bool = False,
) -> None:
    estado = estado_cache or obter_estado_cache_notas(db, tenant_id)
    desde = None
    if (
        estado.get("total")
        and not force_refresh
        and isinstance(estado.get("ultimo_sync"), datetime)
    ):
        desde = estado["ultimo_sync"] - timedelta(hours=6)

    _sincronizar_vendas_em_cache(db, tenant_id, desde=desde)
    _sincronizar_pedidos_integrados_em_cache(db, tenant_id, desde=desde)


def _enriquecer_notas_com_vendas(db: Session, tenant_id, notas: list[dict]) -> None:
    ids_bling = _ids_bling_das_notas(notas)
    if not ids_bling:
        return

    vendas_por_bling_id = _vendas_por_bling_id(db, tenant_id, ids_bling)
    for nota in notas:
        venda = vendas_por_bling_id.get(str(nota.get("id") or ""))
        if venda:
            _aplicar_venda_em_nota(nota, venda)


def _ids_bling_das_notas(notas: list[dict]) -> set[int]:
    return {
        nota_id
        for nota_id in (_coerce_int(nota.get("id"), 0) for nota in notas)
        if nota_id > 0
    }


def _vendas_por_bling_id(
    db: Session, tenant_id, ids_bling: set[int]
) -> dict[str, Venda]:
    vendas = (
        db.query(Venda)
        .filter(
            Venda.tenant_id == tenant_id,
            Venda.nfe_bling_id.in_(ids_bling),
        )
        .all()
    )
    return {str(venda.nfe_bling_id): venda for venda in vendas if venda.nfe_bling_id}


def _aplicar_venda_em_nota(nota: dict, venda: Venda) -> None:
    nota["venda_id"] = nota.get("venda_id") or venda.id
    nota["chave"] = nota.get("chave") or venda.nfe_chave or ""

    if not nota.get("valor") and venda.total is not None:
        nota["valor"] = float(venda.total or 0)

    _aplicar_cliente_venda_em_nota(nota, venda)
    nota["canal"] = nota.get("canal") or _texto(venda.canal)
    nota["canal_label"] = nota.get("canal_label") or _canal_label(
        _canal_slug(venda.canal), venda.canal
    )
    nota["numero_pedido_loja"] = nota.get("numero_pedido_loja") or _texto(
        venda.numero_venda
    )
    if not isinstance(nota.get("loja"), dict) or not nota.get("loja", {}).get("nome"):
        nota["loja"] = {"id": None, "nome": _texto(venda.loja_origem)}


def _aplicar_cliente_venda_em_nota(nota: dict, venda: Venda) -> None:
    cliente = nota.get("cliente") or {}
    if venda.cliente:
        cliente["id"] = cliente.get("id") or venda.cliente.id
        cliente["nome"] = cliente.get("nome") or venda.cliente.nome
        cliente["cpf_cnpj"] = (
            cliente.get("cpf_cnpj") or venda.cliente.cpf or venda.cliente.cnpj
        )
    nota["cliente"] = cliente


def _enriquecer_notas_com_detalhes_bling(
    bling: BlingAPI,
    db: Session,
    tenant_id,
    notas: list[dict],
    limite_consultas: int = 120,
) -> None:
    consultas = 0
    ultima_consulta_ts = 0.0

    for nota in notas:
        if consultas >= limite_consultas:
            break

        necessidades = _necessidades_detalhe_nota(nota)
        if not necessidades["precisa_detalhe"]:
            continue

        nota_id = _coerce_int(nota.get("id"), 0)
        if nota_id <= 0:
            continue

        try:
            modelo_nota = _coerce_int(nota.get("modelo"), 55)
            detalhe, fetched_remotamente, ultima_consulta_ts = (
                _buscar_detalhe_para_enriquecimento(
                    bling,
                    db,
                    tenant_id,
                    nota_id,
                    modelo_nota,
                    ultima_consulta_ts,
                )
            )
            if not _detalhe_nota_valido(detalhe):
                continue

            _aplicar_detalhe_bling_em_nota(nota, detalhe)
            if fetched_remotamente or necessidades["deve_persistir"]:
                _persistir_enriquecimento_detalhe(db, tenant_id, nota, detalhe)
            if fetched_remotamente:
                consultas += 1
        except Exception as e:
            logger.warning(
                "listar_nfes",
                f"Falha ao enriquecer NF {nota_id} via detalhe do Bling: {e}",
            )
            mensagem = str(e).upper()
            if "429" in mensagem or "TOO_MANY_REQUESTS" in mensagem:
                break


def _necessidades_detalhe_nota(nota: dict) -> dict[str, bool]:
    valor_atual = _coerce_float(nota.get("valor"), 0.0) or 0.0
    status_atual = (_texto(nota.get("status")) or "").lower()
    precisa_numero = not _texto(nota.get("numero"))
    precisa_chave = not _texto(nota.get("chave"))
    precisa_reconciliar_status = status_atual in {"pendente", "emitida danfe"}
    precisa_resumo_canal = not any(
        (
            nota.get("canal_label"),
            nota.get("loja", {}).get("nome")
            if isinstance(nota.get("loja"), dict)
            else None,
            nota.get("origem_loja_virtual"),
            nota.get("numero_pedido_loja"),
        )
    )
    deve_persistir = (
        precisa_numero
        or precisa_chave
        or precisa_resumo_canal
        or precisa_reconciliar_status
    )
    return {
        "precisa_detalhe": valor_atual <= 0 or deve_persistir,
        "deve_persistir": deve_persistir,
    }


def _buscar_detalhe_para_enriquecimento(
    bling: BlingAPI,
    db: Session,
    tenant_id,
    nota_id: int,
    modelo_nota: int,
    ultima_consulta_ts: float,
) -> tuple[dict | None, bool, float]:
    detalhe = _consultar_detalhe_cache_persistente(db, tenant_id, nota_id, modelo_nota)
    if _detalhe_nota_valido(detalhe):
        return detalhe, False, ultima_consulta_ts

    if ultima_consulta_ts:
        intervalo = monotonic() - ultima_consulta_ts
        if intervalo < 0.36:
            sleep(0.36 - intervalo)

    detalhe = _consultar_detalhe_remoto_bling(bling, nota_id, modelo_nota)
    ultima_consulta_ts = monotonic()
    if _detalhe_nota_valido(detalhe):
        _salvar_detalhe_nfe_cache(tenant_id, nota_id, modelo_nota, detalhe)
        return detalhe, True, ultima_consulta_ts
    return detalhe, False, ultima_consulta_ts


def _aplicar_detalhe_bling_em_nota(nota: dict, detalhe: dict) -> None:
    nota["numero"] = (
        _texto(_primeiro_preenchido(detalhe.get("numero"), nota.get("numero"))) or ""
    )
    nota["serie"] = (
        _texto(_primeiro_preenchido(detalhe.get("serie"), nota.get("serie"))) or ""
    )
    nota["data_emissao"] = _primeiro_preenchido(
        detalhe.get("dataEmissao"),
        detalhe.get("data_emissao"),
        nota.get("data_emissao"),
    )
    nota["valor"] = _extrair_valor_nota(detalhe) or nota.get("valor") or 0.0
    nota["status"] = _status_nota_bling(detalhe)
    nota["chave"] = detalhe.get("chaveAcesso") or nota.get("chave") or ""
    _aplicar_cliente_detalhe_em_nota(nota, detalhe)
    _aplicar_resumo_canal_em_nota(nota, _normalizar_resumo_canal(detalhe))


def _aplicar_cliente_detalhe_em_nota(nota: dict, detalhe: dict) -> None:
    contato = detalhe.get("contato") or {}
    cliente = nota.get("cliente") or {}
    cliente["id"] = cliente.get("id") or contato.get("id")
    cliente["nome"] = (
        cliente.get("nome") or contato.get("nome") or contato.get("descricao")
    )
    cliente["cpf_cnpj"] = (
        cliente.get("cpf_cnpj")
        or contato.get("cpf")
        or contato.get("cnpj")
        or contato.get("cpfCnpj")
    )
    nota["cliente"] = cliente


def _aplicar_resumo_canal_em_nota(nota: dict, resumo_canal: dict) -> None:
    nota["canal"] = nota.get("canal") or resumo_canal.get("canal")
    nota["canal_label"] = nota.get("canal_label") or resumo_canal.get("canal_label")
    if not isinstance(nota.get("loja"), dict) or not nota.get("loja", {}).get("nome"):
        nota["loja"] = resumo_canal.get("loja")

    for campo in (
        "unidade_negocio",
        "numero_loja_virtual",
        "origem_loja_virtual",
        "origem_canal_venda",
        "numero_pedido_loja",
        "pedido_bling_id_ref",
    ):
        nota[campo] = nota.get(campo) or resumo_canal.get(campo)


def _persistir_enriquecimento_detalhe(
    db: Session,
    tenant_id,
    nota: dict,
    detalhe: dict,
) -> None:
    _compat_attr("upsert_nota_cache", upsert_nota_cache)(
        db,
        tenant_id,
        nota,
        source="bling_detail",
        resumo_payload=nota,
        detalhe_payload=detalhe,
    )


def _sincronizar_cache_nfes_com_bling(
    db: Session,
    tenant_id,
    *,
    data_inicial: str | None = None,
    data_final: str | None = None,
    situacao: str | None = None,
) -> tuple[bool, list[dict]]:
    try:
        bling = BlingAPI()
    except Exception as e:
        logger.warning(
            "listar_nfes", f"Bling indisponivel para sincronizacao incremental: {e}"
        )
        return False, []

    nfe_ok, notas_nfe, rate_limit_nfe = _listar_notas_bling_por_modelo(
        bling,
        modelo=55,
        data_inicial=data_inicial,
        data_final=data_final,
        situacao=situacao,
    )
    if rate_limit_nfe:
        return False, []

    nfce_ok, notas_nfce, rate_limit_nfce = _listar_notas_bling_por_modelo(
        bling,
        modelo=65,
        data_inicial=data_inicial,
        data_final=data_final,
        situacao=situacao,
    )
    if rate_limit_nfce:
        return False, []

    notas_sincronizadas = _deduplicar_notas_bling([*notas_nfe, *notas_nfce])
    bling_ok = nfe_ok or nfce_ok

    if not notas_sincronizadas:
        return bling_ok, []

    _enriquecer_notas_com_vendas(db, tenant_id, notas_sincronizadas)
    _enriquecer_notas_com_pedidos_integrados(db, tenant_id, notas_sincronizadas)
    _enriquecer_notas_com_detalhes_bling(
        bling,
        db,
        tenant_id,
        notas_sincronizadas[:20],
        limite_consultas=8,
    )
    for nota in notas_sincronizadas:
        upsert_nota_cache(
            db,
            tenant_id,
            nota,
            source="bling_api",
            resumo_payload=nota,
        )
    db.commit()
    return bling_ok, notas_sincronizadas


def _listar_notas_bling_por_modelo(
    bling: BlingAPI,
    *,
    modelo: int,
    data_inicial: str | None,
    data_final: str | None,
    situacao: str | None,
) -> tuple[bool, list[dict], bool]:
    try:
        listar = bling.listar_nfces if modelo == 65 else bling.listar_nfes
        resposta = listar(
            data_inicial=data_inicial,
            data_final=data_final,
            situacao=situacao,
        )
    except Exception as exc:
        tipo = "NFC-e" if modelo == 65 else "NF-e"
        logger.warning(
            "listar_nfes",
            f"Bling {tipo} nao disponivel para sincronizacao incremental: {exc}",
        )
        if _erro_rate_limit_bling(exc):
            BlingSyncService.register_rate_limit_cooldown(exc)
            return False, [], True
        return False, [], False

    notas = [
        _normalizar_nota_bling(item, modelo=modelo)
        for item in resposta.get("data") or []
    ]
    return True, notas, False


def _erro_rate_limit_bling(exc: Exception) -> bool:
    mensagem = str(exc).upper()
    return "TOO_MANY_REQUESTS" in mensagem or "429" in mensagem


def _deduplicar_notas_bling(notas: list[dict]) -> list[dict]:
    notas_unicas: list[dict] = []
    ids_ja_adicionados: set[tuple[str, int]] = set()
    for nota in notas:
        chave = (str(nota.get("id") or ""), _coerce_int(nota.get("modelo"), 55))
        if chave in ids_ja_adicionados:
            continue
        notas_unicas.append(nota)
        ids_ja_adicionados.add(chave)
    return notas_unicas
