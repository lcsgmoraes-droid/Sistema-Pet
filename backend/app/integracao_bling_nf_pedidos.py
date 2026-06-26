"""Vinculo entre notas fiscais Bling e pedidos locais."""

import re
from decimal import Decimal

from sqlalchemy.orm import Session

from app.integracao_bling_nf_helpers import (
    _consolidar_ultima_nf,
    _dict,
    _modelo_nota_bling,
    _primeiro_preenchido,
    _status_nota_webhook,
    _texto,
)
from app.pedido_integrado_models import PedidoIntegrado
from app.services.pedido_integrado_consolidation_service import (
    localizar_pedido_canonico_por_numero_loja,
    localizar_pedido_por_bling_id,
)
from app.services.provisao_simples_service import gerar_provisao_simples_por_nf
from app.utils.logger import logger


def _obter_pedido_bling_id_por_nf(nf_id: str, situacao_num: int) -> str | None:
    return (
        _consultar_relacao_nf_bling(nf_id=nf_id, situacao_num=situacao_num) or {}
    ).get("pedido_bling_id")


def _extrair_numero_pedido_loja_nf(data: dict | None) -> str | None:
    data = data or {}
    info_adicionais = (
        data.get("informacoesAdicionais")
        if isinstance(data.get("informacoesAdicionais"), dict)
        else {}
    )
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
    pedido_payload = (
        payload.get("pedido") if isinstance(payload.get("pedido"), dict) else {}
    )
    webhook_payload = (
        payload.get("webhook") if isinstance(payload.get("webhook"), dict) else {}
    )

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


def _loja_id_nf_payload(data: dict | None) -> str | None:
    data = data if isinstance(data, dict) else {}
    loja = data.get("loja") if isinstance(data.get("loja"), dict) else {}
    loja_virtual = (
        data.get("lojaVirtual") if isinstance(data.get("lojaVirtual"), dict) else {}
    )
    unidade = (
        data.get("unidadeNegocio")
        if isinstance(data.get("unidadeNegocio"), dict)
        else {}
    )

    return _texto(
        _primeiro_preenchido(
            loja.get("id"),
            loja_virtual.get("id"),
            unidade.get("id"),
            data.get("loja_id"),
            data.get("lojaId"),
        )
    )


def _loja_id_pedido(pedido: PedidoIntegrado) -> str | None:
    payload = pedido.payload if isinstance(pedido.payload, dict) else {}
    pedido_payload = (
        payload.get("pedido") if isinstance(payload.get("pedido"), dict) else {}
    )
    webhook_payload = (
        payload.get("webhook") if isinstance(payload.get("webhook"), dict) else {}
    )

    pedido_loja = (
        pedido_payload.get("loja")
        if isinstance(pedido_payload.get("loja"), dict)
        else {}
    )
    webhook_loja = (
        webhook_payload.get("loja")
        if isinstance(webhook_payload.get("loja"), dict)
        else {}
    )
    loja_virtual = (
        pedido_payload.get("lojaVirtual")
        if isinstance(pedido_payload.get("lojaVirtual"), dict)
        else {}
    )

    return _texto(
        _primeiro_preenchido(
            pedido_loja.get("id"),
            webhook_loja.get("id"),
            loja_virtual.get("id"),
            pedido_payload.get("loja_id"),
            webhook_payload.get("loja_id"),
        )
    )


def _localizar_pedido_local_por_numero_bling(
    db: Session,
    *,
    tenant_id,
    pedido_bling_numero: str | None,
) -> PedidoIntegrado | None:
    numero = str(pedido_bling_numero or "").strip()
    if not numero:
        return None

    pedido = (
        db.query(PedidoIntegrado)
        .filter(
            PedidoIntegrado.tenant_id == tenant_id,
            PedidoIntegrado.pedido_bling_numero == numero,
        )
        .first()
    )
    if not pedido:
        return None

    pedido_canonico = localizar_pedido_por_bling_id(
        db,
        tenant_id=tenant_id,
        pedido_bling_id=getattr(pedido, "pedido_bling_id", None),
    )
    return pedido_canonico or pedido


def _localizar_pedido_local_por_numero_loja(
    db: Session,
    *,
    tenant_id,
    numero_pedido_loja: str | None,
    loja_id: str | None = None,
    limite_scan: int = 2000,
) -> PedidoIntegrado | None:
    return localizar_pedido_canonico_por_numero_loja(
        db,
        tenant_id=tenant_id,
        numero_pedido_loja=numero_pedido_loja,
        loja_id=loja_id,
        limite_scan=limite_scan,
    )


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

        if (
            not pedido_bling_id
            and not pedido_bling_numero
            and not numero_pedido_loja
            and ultima_falha
        ):
            raise ultima_falha
    except Exception as e:
        logger.warning(f"[BLING NF] Falha ao buscar NF {nf_id} na API: {e}")

    return {
        "pedido_bling_id": pedido_bling_id or None,
        "pedido_bling_numero": pedido_bling_numero or None,
        "numero_pedido_loja": numero_pedido_loja or None,
        "nf_completa": nf_completa,
    }


def _registrar_nf_no_pedido(
    pedido: PedidoIntegrado, data: dict, nf_id: str, situacao_num: int
) -> None:
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


def _nf_resumo_corresponde(
    resumo_nf: dict | None, *, nf_id: str | None, nf_numero: str | None
) -> bool:
    resumo_nf = _dict(resumo_nf)
    nf_id = _texto(nf_id)
    nf_numero = _texto(nf_numero)
    resumo_id = _texto(
        _primeiro_preenchido(resumo_nf.get("id"), resumo_nf.get("nfe_id"))
    )
    resumo_numero = _texto(resumo_nf.get("numero"))

    return bool(
        (nf_id and resumo_id and resumo_id == nf_id)
        or (nf_numero and resumo_numero and resumo_numero == nf_numero)
    )


def _remover_nf_do_pedido(
    pedido: PedidoIntegrado,
    *,
    nf_id: str | None = None,
    nf_numero: str | None = None,
) -> bool:
    payload_atual = pedido.payload if isinstance(pedido.payload, dict) else {}
    payload = dict(payload_atual)
    alterado = False

    if _nf_resumo_corresponde(
        payload.get("ultima_nf"), nf_id=nf_id, nf_numero=nf_numero
    ):
        payload.pop("ultima_nf", None)
        alterado = True

    pedido_payload = (
        payload.get("pedido") if isinstance(payload.get("pedido"), dict) else None
    )
    if pedido_payload is not None:
        pedido_payload = dict(pedido_payload)
        for chave in ("notaFiscal", "nota", "nfe"):
            if _nf_resumo_corresponde(
                pedido_payload.get(chave), nf_id=nf_id, nf_numero=nf_numero
            ):
                pedido_payload.pop(chave, None)
                alterado = True
        payload["pedido"] = pedido_payload

    if alterado:
        pedido.payload = payload
    return alterado


def _gerar_provisao_simples_se_aplicavel(
    db: Session, pedido: PedidoIntegrado, data: dict
) -> None:
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
