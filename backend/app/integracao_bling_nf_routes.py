
import os
import re
from uuid import UUID

from fastapi import APIRouter, Request, HTTPException, Depends, Query
from sqlalchemy import not_, exists, or_
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from app.db import get_session
from app.auth.dependencies import get_current_user_and_tenant
from app.services.nfe_cache_service import upsert_nota_cache
from app.pedido_integrado_models import PedidoIntegrado
from app.pedido_integrado_item_models import PedidoIntegradoItem
from app.services.bling_nf_service import (
    processar_nf_autorizada,
    processar_nf_cancelada,
    criar_produto_automatico_do_bling,
    AUTO_CADASTRO_BING_TAG,
)
from app.services.bling_flow_monitor_service import (
    abrir_incidente,
    registrar_evento,
    registrar_vinculo_nf_pedido,
    resolver_incidentes_relacionados,
)
from app.services.provisao_simples_service import gerar_provisao_simples_por_nf
from app.tenancy.context import set_current_tenant
from app.utils.logger import logger

# Tenant fixo para webhooks do Bling (chamadas sem JWT)
_BLING_WEBHOOK_TENANT_ID = os.getenv("BLING_WEBHOOK_TENANT_ID")

router = APIRouter(
    prefix="/integracoes/bling",
    tags=["Integração Bling - NF"]
)

# Situações de NF no Bling (campo situacao é um número)
# 1=Pendente, 2=Emitida DANFE, 4=Cancelada, 5=Autorizada, 9=Autorizada
_NF_SITUACAO_AUTORIZADA = {2, 5, 9}
_NF_SITUACAO_CANCELADA  = {4}


def _dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def _texto(value) -> str | None:
    if value is None:
        return None
    texto = str(value).strip()
    return texto or None


def _primeiro_preenchido(*valores):
    for valor in valores:
        if valor is None:
            continue
        if isinstance(valor, str) and not valor.strip():
            continue
        return valor
    return None


def _mesclar_ultima_nf(atual: dict | None, nova: dict | None) -> dict:
    atual = _dict(atual)
    nova = _dict(nova)
    mesclada = dict(atual)
    for chave, valor in nova.items():
        if valor in (None, "", [], {}):
            continue
        mesclada[chave] = valor
    return mesclada


def _coerce_data_nf(value) -> datetime | None:
    texto = _texto(value)
    if not texto:
        return None
    texto = texto.replace("Z", "+00:00")
    try:
        if "T" not in texto and " " in texto:
            texto = texto.replace(" ", "T", 1)
        dt = datetime.fromisoformat(texto)
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    except ValueError:
        try:
            return datetime.fromisoformat(texto.split("T")[0])
        except ValueError:
            return None


def _numero_nf_int(nf: dict | None) -> int | None:
    numero = _texto(_dict(nf).get("numero"))
    if not numero or not numero.isdigit():
        return None
    return int(numero)


def _nova_nf_deve_substituir(atual: dict | None, nova: dict | None) -> bool:
    atual = _dict(atual)
    nova = _dict(nova)
    if not atual:
        return True
    if not nova:
        return False

    atual_id = _texto(_primeiro_preenchido(atual.get("id"), atual.get("nfe_id")))
    nova_id = _texto(_primeiro_preenchido(nova.get("id"), nova.get("nfe_id")))
    atual_numero = _texto(atual.get("numero"))
    nova_numero = _texto(nova.get("numero"))

    if (atual_id and nova_id and atual_id == nova_id) or (atual_numero and nova_numero and atual_numero == nova_numero):
        return True

    atual_data = _coerce_data_nf(_primeiro_preenchido(atual.get("data_emissao"), atual.get("dataEmissao")))
    nova_data = _coerce_data_nf(_primeiro_preenchido(nova.get("data_emissao"), nova.get("dataEmissao")))
    if atual_data and nova_data and atual_data != nova_data:
        return nova_data > atual_data
    if nova_data and not atual_data:
        return True
    if atual_data and not nova_data:
        return False

    atual_numero_int = _numero_nf_int(atual)
    nova_numero_int = _numero_nf_int(nova)
    if atual_numero_int is not None and nova_numero_int is not None and atual_numero_int != nova_numero_int:
        return nova_numero_int > atual_numero_int

    return False


def _consolidar_ultima_nf(atual: dict | None, nova: dict | None) -> dict:
    if _nova_nf_deve_substituir(atual, nova):
        return _mesclar_ultima_nf(atual, nova)
    return _mesclar_ultima_nf(nova, atual)


def _modelo_nota_bling(nf_data: dict | None) -> int:
    nf_data = _dict(nf_data)
    for candidato in (
        nf_data.get("modelo"),
        nf_data.get("modeloDocumento"),
        nf_data.get("modelo_nf"),
    ):
        texto = _texto(candidato)
        if texto in {"55", "65"}:
            return int(texto)

    tipo = (_texto(nf_data.get("tipo")) or "").lower()
    if "nfce" in tipo:
        return 65
    return 55


def _status_nota_webhook(nf_data: dict | None, situacao_num: int | None = None) -> str | None:
    nf_data = _dict(nf_data)
    try:
        from app.nfe_routes import _status_nota_bling

        if nf_data:
            return _status_nota_bling(nf_data)
        if situacao_num is not None:
            return _status_nota_bling({"situacao": situacao_num})
    except Exception:
        pass

    if situacao_num in _NF_SITUACAO_CANCELADA:
        return "Cancelada"
    if situacao_num in _NF_SITUACAO_AUTORIZADA:
        return "Autorizada"
    if situacao_num == 1:
        return "Pendente"
    return _texto(_dict(nf_data.get("situacao")).get("descricao")) or _texto(nf_data.get("status")) or "Pendente"


def _nf_webhook_autorizada(nf_data: dict | None, situacao_num: int | None = None) -> bool:
    return (_status_nota_webhook(nf_data, situacao_num) or "").strip().lower() == "autorizada"


def _nf_webhook_cancelada(nf_data: dict | None, situacao_num: int | None = None) -> bool:
    return (_status_nota_webhook(nf_data, situacao_num) or "").strip().lower() == "cancelada"


def _atualizar_cache_nota_webhook(
    *,
    db: Session,
    tenant_id,
    nf_data: dict | None,
    source: str,
) -> None:
    nf_data = _dict(nf_data)
    nf_id = _texto(nf_data.get("id"))
    if not tenant_id or not nf_id:
        return

    try:
        from app.nfe_routes import _normalizar_nota_bling

        modelo = _modelo_nota_bling(nf_data)
        nota = _normalizar_nota_bling({**nf_data, "id": nf_id}, modelo=modelo)
        upsert_nota_cache(
            db,
            tenant_id,
            nota,
            source=source,
            resumo_payload=nf_data,
            detalhe_payload=nf_data,
        )
    except Exception as exc:
        logger.warning(f"[BLING NF] Falha ao atualizar cache local da NF {nf_id}: {exc}")


def _query_itens_sem_produto(db: Session, tenant_id):
    from app.produtos_models import Produto

    produto_existe = exists().where(
        Produto.tenant_id == tenant_id,
        or_(
            Produto.codigo == PedidoIntegradoItem.sku,
            Produto.codigo_barras == PedidoIntegradoItem.sku,
        ),
    )

    return (
        db.query(PedidoIntegradoItem, PedidoIntegrado)
        .join(PedidoIntegrado, PedidoIntegrado.id == PedidoIntegradoItem.pedido_integrado_id)
        .filter(
            PedidoIntegradoItem.tenant_id == tenant_id,
            not_(produto_existe),
        )
        .order_by(PedidoIntegradoItem.reservado_em.desc())
    )


def _executar_autocadastro_skus(db: Session, tenant_id, rows, max_skus_autocadastro: int):
    skus = []
    vistos = set()

    for item, _pedido in rows:
        sku = (item.sku or "").strip()
        if not sku or sku in vistos:
            continue
        vistos.add(sku)
        skus.append(sku)
        if len(skus) >= max_skus_autocadastro:
            break

    auto_cadastros_executados = 0
    auto_cadastros_falhas = 0

    for sku in skus:
        try:
            produto = criar_produto_automatico_do_bling(
                db=db,
                tenant_id=tenant_id,
                sku=sku,
            )
            if produto:
                auto_cadastros_executados += 1
        except Exception as e:
            auto_cadastros_falhas += 1
            logger.warning(f"[AUTO-BLING-NF] Falha no autocadastro de SKU {sku}: {e}")

    if auto_cadastros_executados > 0:
        db.commit()

    return auto_cadastros_executados, auto_cadastros_falhas


def _serializar_itens_sem_produto(rows):
    def _fmt(dt):
        if not dt:
            return None
        if hasattr(dt, "isoformat"):
            return dt.isoformat()
        return str(dt)

    return [
        {
            "item_id": item.id,
            "sku": item.sku,
            "descricao": item.descricao,
            "quantidade": item.quantidade,
            "reservado_em": _fmt(item.reservado_em),
            "vendido_em": _fmt(item.vendido_em),
            "liberado_em": _fmt(item.liberado_em),
            "pedido_bling_numero": pedido.pedido_bling_numero,
            "pedido_bling_id": pedido.pedido_bling_id,
            "pedido_status": pedido.status,
            "pedido_confirmado_em": _fmt(pedido.confirmado_em),
        }
        for item, pedido in rows
    ]


def _obter_pedido_bling_id_por_nf(nf_id: str, situacao_num: int) -> str | None:
    return (_consultar_relacao_nf_bling(nf_id=nf_id, situacao_num=situacao_num) or {}).get("pedido_bling_id")


def _extrair_numero_pedido_loja_nf(data: dict | None) -> str | None:
    data = data or {}
    info_adicionais = data.get("informacoesAdicionais") if isinstance(data.get("informacoesAdicionais"), dict) else {}
    texto_complementar = (
        info_adicionais.get("informacoesComplementares")
        or data.get("informacoesComplementares")
        or data.get("observacoes")
        or ""
    )

    candidatos = [
        data.get("numeroPedidoLoja"),
        data.get("numeroLojaVirtual"),
        data.get("numeroLoja"),
        info_adicionais.get("numeroPedidoLoja"),
        info_adicionais.get("numeroLojaVirtual"),
        info_adicionais.get("numeroLoja"),
    ]

    for candidato in candidatos:
        texto = str(candidato or "").strip()
        if texto:
            return texto

    match = re.search(
        r"n[ºo°]?\s*pedido(?:\s*na\s*loja|\s*loja)?\s*:\s*([^\r\n|]+)",
        str(texto_complementar or ""),
        flags=re.IGNORECASE | re.MULTILINE,
    )
    if match:
        return str(match.group(1) or "").strip() or None
    return None


def _numero_pedido_loja_do_payload(pedido: PedidoIntegrado) -> str | None:
    payload = pedido.payload if isinstance(pedido.payload, dict) else {}
    pedido_payload = payload.get("pedido") if isinstance(payload.get("pedido"), dict) else {}
    webhook_payload = payload.get("webhook") if isinstance(payload.get("webhook"), dict) else {}

    for candidato in (
        pedido_payload.get("numeroLoja"),
        pedido_payload.get("numeroPedidoLoja"),
        pedido_payload.get("numeroPedido"),
        webhook_payload.get("numeroLoja"),
        webhook_payload.get("numeroPedidoLoja"),
        payload.get("numeroLoja"),
        payload.get("numeroPedidoLoja"),
    ):
        texto = str(candidato or "").strip()
        if texto:
            return texto
    return None


def _localizar_pedido_local_por_numero_bling(
    db: Session,
    *,
    tenant_id,
    pedido_bling_numero: str | None,
) -> PedidoIntegrado | None:
    numero = str(pedido_bling_numero or "").strip()
    if not numero:
        return None

    return (
        db.query(PedidoIntegrado)
        .filter(
            PedidoIntegrado.tenant_id == tenant_id,
            PedidoIntegrado.pedido_bling_numero == numero,
        )
        .first()
    )


def _localizar_pedido_local_por_numero_loja(
    db: Session,
    *,
    tenant_id,
    numero_pedido_loja: str | None,
    limite_scan: int = 2000,
) -> PedidoIntegrado | None:
    numero = str(numero_pedido_loja or "").strip()
    if not numero:
        return None

    pedidos = (
        db.query(PedidoIntegrado)
        .filter(PedidoIntegrado.tenant_id == tenant_id)
        .order_by(PedidoIntegrado.created_at.desc())
        .limit(limite_scan)
        .all()
    )
    for pedido in pedidos:
        if _numero_pedido_loja_do_payload(pedido) == numero:
            return pedido
    return None


def _consultar_relacao_nf_bling(nf_id: str, situacao_num: int) -> dict:
    pedido_bling_id = None
    pedido_bling_numero = None
    numero_pedido_loja = None

    try:
        from app.bling_integration import BlingAPI

        bling = BlingAPI()
        ultima_falha = None
        nf_completa = {}

        for consulta in (bling.consultar_nfe, bling.consultar_nfce):
            try:
                nf_completa = consulta(int(nf_id))
                break
            except Exception as e:
                ultima_falha = e

        pedido_ref = (
            nf_completa.get("pedido")
            or nf_completa.get("pedidoCompra")
            or nf_completa.get("pedidoVenda")
        )
        if isinstance(pedido_ref, dict):
            pedido_bling_id = str(pedido_ref.get("id", "")).strip() or None
            pedido_bling_numero = str(pedido_ref.get("numero", "")).strip() or None
        numero_pedido_loja = _extrair_numero_pedido_loja_nf(nf_completa)
        logger.info(
            f"[BLING NF] NF {nf_id} situacao={situacao_num} "
            f"pedido_bling_id={pedido_bling_id} pedido_bling_numero={pedido_bling_numero} "
            f"numero_pedido_loja={numero_pedido_loja}"
        )

        if not pedido_bling_id and not pedido_bling_numero and not numero_pedido_loja and ultima_falha:
            raise ultima_falha
    except Exception as e:
        logger.warning(f"[BLING NF] Falha ao buscar NF {nf_id} na API: {e}")

    return {
        "pedido_bling_id": pedido_bling_id or None,
        "pedido_bling_numero": pedido_bling_numero or None,
        "numero_pedido_loja": numero_pedido_loja or None,
        "nf_completa": nf_completa,
    }


def _registrar_nf_no_pedido(pedido: PedidoIntegrado, data: dict, nf_id: str, situacao_num: int) -> None:
    payload_atual = pedido.payload if isinstance(pedido.payload, dict) else {}
    ultima_nf_atual = _dict(payload_atual.get("ultima_nf"))
    status_nf = _status_nota_webhook(data, situacao_num)
    pedido.payload = {
        **payload_atual,
        "ultima_nf": _consolidar_ultima_nf(
            ultima_nf_atual,
            {
                "id": nf_id,
                "numero": data.get("numero"),
                "serie": data.get("serie"),
                "situacao": status_nf,
                "situacao_codigo": situacao_num,
                "chave": data.get("chaveAcesso") or data.get("chave"),
                "data_emissao": data.get("dataEmissao") or data.get("data_emissao"),
                "valor_total": (
                    data.get("valorNota")
                    or data.get("valorTotalNf")
                    or data.get("valor_total")
                    or data.get("valorTotal")
                ),
                "modelo": _modelo_nota_bling(data),
                "tipo": "nfce" if _modelo_nota_bling(data) == 65 else "nfe",
            },
        ),
    }


def _gerar_provisao_simples_se_aplicavel(db: Session, pedido: PedidoIntegrado, data: dict) -> None:
    try:
        valor_total_nf = data.get("valorTotalNf") or data.get("valor_total", 0)
        data_emissao = data.get("dataEmissao") or data.get("data_emissao")

        if not valor_total_nf or not data_emissao or not pedido.tenant_id:
            return

        if isinstance(data_emissao, str):
            from datetime import date

            data_emissao = date.fromisoformat(data_emissao.split("T")[0])

        resultado = gerar_provisao_simples_por_nf(
            db=db,
            tenant_id=pedido.tenant_id,
            valor_nf=Decimal(str(valor_total_nf)),
            data_emissao=data_emissao,
            usuario_id=pedido.usuario_id if hasattr(pedido, "usuario_id") else None,
        )

        if resultado.get("sucesso"):
            logger.info(
                f"✅ Provisão Simples: R$ {resultado['valor_provisao']:.2f} "
                f"(Período {resultado['mes']}/{resultado['ano']})"
            )
    except Exception as e:
        logger.info(f"⚠️  Erro ao gerar provisão Simples Nacional: {e}")
        import traceback

        traceback.print_exc()


@router.post("/nf")
async def receber_nf_bling(request: Request, db: Session = Depends(get_session)):
    """
    Recebe webhooks de NF-e e NF-e de consumidor do Bling.
    Formato envelope v1:
      { eventId, date, version, event: 'invoice.created'|'invoice.updated', data: {...} }
    O campo data.situacao é um NÚMERO: 2=Emitida, 5/9=Autorizada, 4=Cancelada.
    O payload do webhook NÃO inclui o pedido vinculado — precisa chamar a API.
    """
    body = await request.json()

    # Injetar tenant no contexto (webhook chega sem JWT)
    tenant_id_monitor = UUID(_BLING_WEBHOOK_TENANT_ID) if _BLING_WEBHOOK_TENANT_ID else None
    if _BLING_WEBHOOK_TENANT_ID:
        set_current_tenant(UUID(_BLING_WEBHOOK_TENANT_ID))

    # Desempacotar envelope Bling (v1)
    event = body.get("event", "invoice.updated")
    event_date = body.get("date")
    data = body.get("data", body)  # fallback p/ payload legado

    nf_id = str(data.get("id", ""))
    if not nf_id or nf_id == "None":
        if tenant_id_monitor:
            registrar_evento(
                tenant_id=tenant_id_monitor,
                source="webhook",
                event_type=event or "invoice.updated",
                entity_type="nf",
                status="ignored",
                severity="warning",
                message="Webhook de NF ignorado porque chegou sem id da nota.",
                payload=_dict(data) or _dict(body),
                processed_at=event_date,
            )
        logger.info(f"[BLING NF] Webhook ignorado sem id. event={event}")
        return {"status": "ignorado", "motivo": "sem_id"}

    situacao_num = data.get("situacao")
    try:
        situacao_num = int(situacao_num)
    except (TypeError, ValueError):
        situacao_num = 0

    # Buscar NF completa na API do Bling para obter o pedido vinculado
    nf_relacao = _consultar_relacao_nf_bling(nf_id=nf_id, situacao_num=situacao_num)
    nf_dados = _dict(nf_relacao.get("nf_completa")) or _dict(data)
    pedido_ref_nf = _dict(
        _dict(nf_dados).get("pedido")
        or _dict(nf_dados).get("pedidoVenda")
        or _dict(nf_dados).get("pedidoCompra")
        or _dict(data).get("pedido")
        or _dict(data).get("pedidoVenda")
        or _dict(data).get("pedidoCompra")
    )
    pedido_bling_id = nf_relacao.get("pedido_bling_id") or _texto(pedido_ref_nf.get("id"))
    pedido_bling_numero = nf_relacao.get("pedido_bling_numero") or _texto(pedido_ref_nf.get("numero"))
    numero_pedido_loja = (
        nf_relacao.get("numero_pedido_loja")
        or _extrair_numero_pedido_loja_nf(nf_dados)
        or _extrair_numero_pedido_loja_nf(data)
    )
    nf_numero = str(_dict(nf_dados).get("numero") or "").strip() or None

    if tenant_id_monitor:
        _atualizar_cache_nota_webhook(
            db=db,
            tenant_id=tenant_id_monitor,
            nf_data=nf_dados,
            source="bling_webhook_nf",
        )

    if tenant_id_monitor:
        registrar_evento(
            tenant_id=tenant_id_monitor,
            source="webhook",
            event_type=event or "invoice.updated",
            entity_type="nf",
            status="received",
            severity="info",
            message="Webhook de NF recebido; o sistema vai localizar o pedido e atualizar o vinculo da nota.",
            pedido_bling_id=pedido_bling_id,
            nf_bling_id=nf_id,
            payload={
                **_dict(data),
                "status_nf": _status_nota_webhook(nf_dados, situacao_num),
                "nf_numero": nf_numero,
                "pedido_bling_numero": pedido_bling_numero,
                "numero_pedido_loja": numero_pedido_loja,
            },
            processed_at=event_date,
        )

    pedido = None
    if pedido_bling_id:
        query = db.query(PedidoIntegrado).filter(PedidoIntegrado.pedido_bling_id == pedido_bling_id)
        if tenant_id_monitor:
            query = query.filter(PedidoIntegrado.tenant_id == tenant_id_monitor)
        pedido = query.first()
    if not pedido and tenant_id_monitor and pedido_bling_numero:
        pedido = _localizar_pedido_local_por_numero_bling(
            db,
            tenant_id=tenant_id_monitor,
            pedido_bling_numero=pedido_bling_numero,
        )
        if pedido:
            pedido_bling_id = pedido.pedido_bling_id
    if not pedido and tenant_id_monitor and numero_pedido_loja:
        pedido = _localizar_pedido_local_por_numero_loja(
            db,
            tenant_id=tenant_id_monitor,
            numero_pedido_loja=numero_pedido_loja,
        )
        if pedido:
            pedido_bling_id = pedido.pedido_bling_id

    if not pedido and not pedido_bling_id and not pedido_bling_numero:
        # NF sem pedido vinculado (ex: NF emitida manualmente fora do fluxo)
        if tenant_id_monitor:
            abrir_incidente(
                tenant_id=tenant_id_monitor,
                code="NF_SEM_PEDIDO_VINCULADO",
                severity="high",
                title="NF sem pedido vinculado",
                message="A NF recebida do Bling nao retornou nenhum pedido vinculado na consulta da API.",
                suggested_action="Revisar a origem da NF no Bling e vincular manualmente ao pedido correto, se existir.",
                auto_fixable=False,
                nf_bling_id=nf_id,
                details={
                    "situacao_num": situacao_num,
                    "nf_numero": nf_numero,
                    "pedido_bling_numero": pedido_bling_numero,
                    "numero_pedido_loja": numero_pedido_loja,
                },
                source="runtime",
            )
        return {
            "status": "ok",
            "acao": "nf_registrada_sem_pedido_vinculado",
            "situacao": _status_nota_webhook(nf_dados, situacao_num),
        }

    if not pedido:
        if tenant_id_monitor:
            abrir_incidente(
                tenant_id=tenant_id_monitor,
                code="NF_SEM_PEDIDO_LOCAL",
                severity="critical",
                title="NF vinculada a pedido inexistente localmente",
                message="A NF referencia um pedido do Bling que ainda nao existe ou nao foi encontrado no sistema.",
                suggested_action="Importar/reprocessar o pedido correspondente antes de consolidar a NF.",
                auto_fixable=False,
                pedido_bling_id=pedido_bling_id,
                nf_bling_id=nf_id,
                details={
                    "situacao_num": situacao_num,
                    "nf_numero": nf_numero,
                    "pedido_bling_numero": pedido_bling_numero,
                    "numero_pedido_loja": numero_pedido_loja,
                },
                source="runtime",
            )
        return {
            "status": "ok",
            "acao": "nf_registrada_sem_pedido_local",
            "situacao": _status_nota_webhook(nf_dados, situacao_num),
        }

    if pedido.tenant_id != tenant_id_monitor:
        _atualizar_cache_nota_webhook(
            db=db,
            tenant_id=pedido.tenant_id,
            nf_data=nf_dados,
            source="bling_webhook_nf",
        )

    _registrar_nf_no_pedido(
        pedido=pedido,
        data=nf_dados,
        nf_id=nf_id,
        situacao_num=situacao_num,
    )
    registrar_vinculo_nf_pedido(
        pedido=pedido,
        source="webhook",
        nf_bling_id=nf_id,
        nf_numero=nf_numero,
        message="NF localizada no webhook e vinculada ao pedido correspondente.",
        payload={
            "link_source": "nf.webhook",
            "pedido_status_antes": pedido.status,
            "numero_pedido_loja": numero_pedido_loja,
        },
        processed_at=event_date,
        db=db,
    )
    resolver_incidentes_relacionados(
        db,
        tenant_id=pedido.tenant_id,
        codes=["NF_SEM_PEDIDO_VINCULADO", "NF_SEM_PEDIDO_LOCAL"],
        pedido_integrado_id=pedido.id,
        pedido_bling_id=pedido.pedido_bling_id,
        nf_bling_id=nf_id,
        resolution_note="NF vinculada posteriormente ao pedido correspondente.",
    )

    itens = db.query(PedidoIntegradoItem).filter(
        PedidoIntegradoItem.pedido_integrado_id == pedido.id
    ).all()

    # ============================
    # NF EMITIDA / AUTORIZADA
    # ============================
    if _nf_webhook_autorizada(nf_dados, situacao_num):
        acao = processar_nf_autorizada(db=db, pedido=pedido, itens=itens, nf_id=nf_id)
        _gerar_provisao_simples_se_aplicavel(db=db, pedido=pedido, data=nf_dados)
        registrar_evento(
            tenant_id=pedido.tenant_id,
            source="webhook",
            event_type="invoice.authorized",
            entity_type="nf",
            status="ok",
            severity="info",
            message=(
                "NF autorizada processada, pedido vinculado e estoque reconciliado."
                if acao == "venda_confirmada"
                else "NF autorizada processada; o pedido ja estava conciliado anteriormente."
            ),
            pedido_integrado_id=pedido.id,
            pedido_bling_id=pedido.pedido_bling_id,
            nf_bling_id=nf_id,
            payload={
                "acao": acao,
                "nf_numero": nf_numero,
                "numero_pedido_loja": numero_pedido_loja,
                "pedido_status_atual": pedido.status,
            },
            processed_at=event_date,
        )

        return {"status": "ok", "acao": acao}

    # ============================
    # NF CANCELADA
    # ============================
    if _nf_webhook_cancelada(nf_dados, situacao_num):
        acao = processar_nf_cancelada(db=db, pedido=pedido, itens=itens, nf_id=nf_id)
        registrar_evento(
            tenant_id=pedido.tenant_id,
            source="webhook",
            event_type="invoice.cancelled",
            entity_type="nf",
            status="ok",
            severity="info",
            message="NF cancelada processada e pedido atualizado conforme o evento recebido.",
            pedido_integrado_id=pedido.id,
            pedido_bling_id=pedido.pedido_bling_id,
            nf_bling_id=nf_id,
            payload={
                "acao": acao,
                "nf_numero": nf_numero,
                "numero_pedido_loja": numero_pedido_loja,
                "pedido_status_atual": pedido.status,
            },
            processed_at=event_date,
        )
        return {"status": "ok", "acao": acao}

    db.add(pedido)
    db.commit()

    status_nf = _status_nota_webhook(nf_dados, situacao_num) or "Pendente"
    registrar_evento(
        tenant_id=pedido.tenant_id,
        source="webhook",
        event_type="invoice.status_updated",
        entity_type="nf",
        status="ok",
        severity="info",
        message="Status da NF atualizado e vinculo com o pedido mantido no sistema.",
        pedido_integrado_id=pedido.id,
        pedido_bling_id=pedido.pedido_bling_id,
        nf_bling_id=nf_id,
        payload={
            "acao": "status_nf_atualizado",
            "status_nf": status_nf,
            "nf_numero": nf_numero,
            "numero_pedido_loja": numero_pedido_loja,
            "pedido_status_atual": pedido.status,
        },
        processed_at=event_date,
    )
    return {
        "status": "ok",
        "acao": "status_nf_atualizado",
        "situacao": status_nf,
    }


# ============================================================
# GET /integracoes/bling/nf/itens-sem-produto
# Itens de pedidos Bling cujo SKU não existe no cadastro local.
# Serve como painel de monitoramento para identificar SKUs órfãos.
# ============================================================

@router.get("/nf/itens-sem-produto")
def listar_itens_sem_produto(
    por_pagina: int = Query(50, ge=1, le=200),
    pagina: int = Query(1, ge=1),
    autocriar_automaticamente: bool = Query(True),
    max_skus_autocadastro: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_session),
    user_tenant=Depends(get_current_user_and_tenant),
):
    """
    Retorna itens de pedidos integrados (Bling) cujo SKU não encontrou
    correspondência em nenhum produto cadastrado (codigo ou codigo_barras).
    Use este endpoint para identificar e corrigir desvinculações de estoque.
    """
    tenant_id = user_tenant[1]
    q = _query_itens_sem_produto(db=db, tenant_id=tenant_id)

    auto_cadastros_executados = 0
    auto_cadastros_falhas = 0

    if autocriar_automaticamente:
        candidatos = q.limit(max_skus_autocadastro * 4).all()
        auto_cadastros_executados, auto_cadastros_falhas = _executar_autocadastro_skus(
            db=db,
            tenant_id=tenant_id,
            rows=candidatos,
            max_skus_autocadastro=max_skus_autocadastro,
        )

        if auto_cadastros_executados > 0:
            q = _query_itens_sem_produto(db=db, tenant_id=tenant_id)

    total = q.count()
    rows = q.offset((pagina - 1) * por_pagina).limit(por_pagina).all()
    items = _serializar_itens_sem_produto(rows)

    return {
        "total": total,
        "pagina": pagina,
        "por_pagina": por_pagina,
        "items": items,
        "autocriar_automaticamente": autocriar_automaticamente,
        "auto_cadastros_executados": auto_cadastros_executados,
        "auto_cadastros_falhas": auto_cadastros_falhas,
    }


@router.get("/nf/autocadastros-recentes")
def listar_autocadastros_recentes(
    horas: int = Query(24, ge=1, le=72),
    limite: int = Query(50, ge=1, le=200),
    resumo: bool = Query(False),
    db: Session = Depends(get_session),
    user_tenant=Depends(get_current_user_and_tenant),
):
    from app.produtos_models import Produto

    tenant_id = user_tenant[1]
    dt_limite = datetime.now(timezone.utc) - timedelta(hours=horas)

    q = (
        db.query(Produto)
        .filter(
            Produto.tenant_id == tenant_id,
            Produto.informacoes_adicionais_nf.isnot(None),
            Produto.informacoes_adicionais_nf.ilike(f"%{AUTO_CADASTRO_BING_TAG}%"),
            Produto.created_at >= dt_limite,
        )
        .order_by(Produto.created_at.desc())
    )

    total = q.count()
    if resumo:
        return {"total": total, "horas": horas}

    produtos = q.limit(limite).all()
    items = [
        {
            "produto_id": p.id,
            "codigo": p.codigo,
            "nome": p.nome,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in produtos
    ]

    return {
        "total": total,
        "horas": horas,
        "limite": limite,
        "items": items,
    }
