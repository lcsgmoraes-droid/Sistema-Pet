"""Uma tentativa durável por venda/ambiente; resultados incertos nunca são reenviados."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from app.audit_log import log_action
from app.intnfe.client import IntNFeError, _safe_validation_errors
from app.intnfe.emission import DirectEmissionError, _access_token, _connection
from app.intnfe.estorno_builder import (
    EstornoError,
    build,
    destinatario_anonimo,
    destinatario_proprio,
    exigir,
)
from app.intnfe.estorno_models import IntNFeEstorno
from app.intnfe.estorno_xml import validate_xml
from app.services.xml_contabilidade_hook import tentar_enfileirar_documento
from app.vendas_models import Venda


def _environment(connection, venda, override, *, require_config=True):
    env = override if override is not None else venda.nfe_ambiente
    exigir(env in (1, 2), "Ambiente da nota original inválido.")
    if override is None and require_config:
        exigir(
            connection.emission_environment == env,
            "O ambiente configurado precisa ser o mesmo da nota original.",
        )
    elif override is not None:
        exigir(override == 2, "O override operacional só permite homologação.")
    return env


def _record(db, venda, environment, *, lock=False):
    query = db.query(IntNFeEstorno).filter(
        IntNFeEstorno.tenant_id == UUID(str(venda.tenant_id)),
        IntNFeEstorno.venda_id == venda.id,
        IntNFeEstorno.ambiente_codigo == environment,
    )
    if lock:
        query = query.populate_existing().with_for_update()
    return query.first()


def _reload(db, venda, env):
    # Mesma ordem em todas as respostas de rede, inclusive na projeção da venda.
    venda = (
        db.query(Venda)
        .filter(Venda.id == venda.id, Venda.tenant_id == venda.tenant_id)
        .populate_existing()
        .with_for_update()
        .one()
    )
    return venda, _record(db, venda, env, lock=True)


def public_record(record):
    if not record:
        return None
    downloadable = (
        record.status in {"autorizado", "cancelado"}
        and record.xml_validado
        and bool(record.protocolo)
    )
    base = f"/nfe/vendas/{record.venda_id}/estorno"
    return {
        "id": record.id,
        "status": record.status,
        "ambiente_codigo": record.ambiente_codigo,
        "correlation_id": record.correlation_id,
        "numero": record.numero,
        "serie": record.serie,
        "chave": record.chave,
        "protocolo": record.protocolo,
        "codigo": record.codigo,
        "motivo": record.motivo,
        "xml_validado": bool(record.xml_validado),
        "pode_consultar": bool(record.correlation_id),
        "xml_url": base + "/xml" if downloadable else None,
        "danfe_url": base + "/danfe" if downloadable else None,
    }


def _result(record, *, previa=None, bloqueios=None):
    issues = list(bloqueios or [])
    success = bool(
        record
        and record.status == "autorizado"
        and record.xml_validado
        and record.protocolo
    )
    return {
        "success": success,
        "elegivel": not record and not issues and previa is not None,
        "bloqueios": issues,
        "previa": previa,
        "estorno": public_record(record),
    }


def _preview(payload, snapshot, payload_hash, venda):
    items = [
        {
            **item,
            "quantidade": float(Decimal(item["quantidade"])),
            "valor_unitario": float(Decimal(item["valor_unitario"])),
            "desconto": float(Decimal(item["desconto"])),
            "total": float(Decimal(item["total"])),
        }
        for item in snapshot["itens"]
    ]
    return {
        "payload_hash": payload_hash,
        "modelo": 55,
        "tipo_operacao": "entrada",
        "finalidade": "ajuste",
        "ambiente_codigo": snapshot["ambiente_codigo"],
        "ambiente_label": "Produção"
        if snapshot["ambiente_codigo"] == 1
        else "Homologação",
        "serie": snapshot["serie"],
        "emitente": {
            "nome": payload["emitente"]["razaoSocial"],
            "cnpj": snapshot["emitente_cnpj"],
        },
        "original": {
            "numero": venda.nfe_numero,
            "serie": venda.nfe_serie,
            "chave": snapshot["original_chave"],
            "status": venda.nfe_status,
        },
        "itens": items,
        "totais": {
            "produtos": float(
                sum(Decimal(i["valor_produtos"]) for i in snapshot["itens"])
            ),
            "desconto": float(sum(Decimal(i["desconto"]) for i in snapshot["itens"])),
            "total": float(Decimal(snapshot["total"])),
        },
        "declaracao": "Declaro que a operação não foi realizada e a mercadoria não saiu do estabelecimento.",
        "destinatario": {
            **payload["destinatario"],
            "nome": payload["destinatario"]["razaoSocial"],
            "cpf_cnpj": payload["destinatario"].get("cnpj")
            or payload["destinatario"].get("cpf"),
        },
    }


def preview(
    db,
    venda,
    *,
    environment_override=None,
    destinatario=None,
    destinatario_proprio_emitente=False,
):
    anonimo = False
    try:
        anonimo = destinatario_anonimo(venda)
        if destinatario_proprio_emitente:
            exigir(
                destinatario is None,
                "Escolha apenas uma identificação do destinatário.",
            )
            destinatario = destinatario_proprio(venda)
        connection = _connection(db, venda.tenant_id, require_enabled=False)
        env = _environment(
            connection, venda, environment_override, require_config=False
        )
        record = _record(db, venda, env)
        if record:
            result = _result(
                record,
                previa=_preview(
                    record.payload, record.snapshot, record.payload_hash, venda
                ),
            )
            return {
                **result,
                "destinatario_anonimo": anonimo,
                "requer_destinatario": False,
            }
        exigir(
            connection.emission_enabled,
            "A emissão direta precisa estar habilitada na integração fiscal.",
        )
        _environment(connection, venda, environment_override)
        payload, snapshot, digest, _ = build(
            venda, connection, ambiente_codigo=env, destinatario=destinatario
        )
        return {
            **_result(None, previa=_preview(payload, snapshot, digest, venda)),
            "destinatario_anonimo": anonimo,
            "requer_destinatario": False,
        }
    except (EstornoError, DirectEmissionError) as exc:
        return {
            **_result(None, bloqueios=[str(exc)]),
            "destinatario_anonimo": anonimo,
            "requer_destinatario": anonimo and destinatario is None,
        }


def _persist(db, venda, record, user_id, action):
    from app.vendas.fiscal_status import sincronizar_venda_apos_estorno

    sincronizar_venda_apos_estorno(db, venda, record)
    log_action(
        db,
        user_id=user_id,
        tenant_id=venda.tenant_id,
        action=action,
        entity_type="intnfe_estorno",
        entity_id=record.id,
        new_value={
            "status": record.status,
            "ambiente_codigo": record.ambiente_codigo,
            "payload_hash": record.payload_hash,
            "correlation_id": record.correlation_id,
            "xml_validado": record.xml_validado,
        },
        commit=False,
    )
    db.commit()


def _safe_message(error):
    values = _safe_validation_errors(
        {
            "erros": [
                getattr(error, "provider_message", None),
                *getattr(error, "validation_errors", []),
            ]
        }
    )
    return (
        " ".join(values)[:500]
        or "Não foi possível confirmar o resultado com a IntNFe. Consulte antes de qualquer nova ação."
    )


def create(
    db,
    venda,
    api,
    *,
    motivo,
    declaracao_operacao_nao_realizada,
    user_id=None,
    destinatario=None,
    environment_override=None,
    destinatario_proprio_emitente=False,
):
    exigir(
        declaracao_operacao_nao_realizada is True,
        "Confirme que a operação não foi realizada e a mercadoria não saiu.",
    )
    motivo = re.sub(r"[\x00-\x1f\x7f]", " ", str(motivo or "")).strip()
    exigir(15 <= len(motivo) <= 500, "Informe um motivo entre15 e500 caracteres.")
    connection = _connection(db, venda.tenant_id)
    env = _environment(connection, venda, environment_override)
    existing = _record(db, venda, env)
    if existing:
        return _result(existing)
    # Valida todos os dados fiscais antes inclusive da chamada de autenticação.
    if destinatario_proprio_emitente:
        exigir(
            destinatario is None, "Escolha apenas uma identificação do destinatário."
        )
        destinatario = destinatario_proprio(venda)
    build(
        venda, connection, ambiente_codigo=env, destinatario=destinatario, motivo=motivo
    )
    # Obter token não transmite documento e não mantém lock comercial durante rede.
    token = _access_token(api, connection, env)
    original_token = (
        token
        if env == venda.nfe_ambiente
        else _access_token(api, connection, venda.nfe_ambiente)
    )
    try:
        original_status = api.document_status(
            original_token, "nfce", venda.nfe_correlation_id
        )
    except IntNFeError as exc:
        raise EstornoError(_safe_message(exc), status=503, code=exc.code) from None
    exigir(
        str(original_status.get("status")) == "3",
        "A NFC-e original não está autorizada e vigente no emissor. Consulte sua situação antes de emitir estorno.",
    )
    venda = (
        db.query(Venda)
        .filter(Venda.id == venda.id, Venda.tenant_id == venda.tenant_id)
        .populate_existing()
        .with_for_update()
        .one()
    )
    existing = _record(db, venda, env, lock=True)
    if existing:
        return _result(existing)
    if destinatario_proprio_emitente:
        destinatario = destinatario_proprio(venda)
    payload, snapshot, digest, original_hash = build(
        venda, connection, ambiente_codigo=env, destinatario=destinatario, motivo=motivo
    )
    key = (
        "corepet-estorno-v1-"
        + hashlib.sha256(f"{venda.tenant_id}:{venda.id}:{env}".encode()).hexdigest()
    )
    record = IntNFeEstorno(
        tenant_id=venda.tenant_id,
        venda_id=venda.id,
        ambiente_codigo=env,
        original_chave=venda.nfe_chave,
        original_xml_hash=original_hash,
        payload=payload,
        payload_hash=digest,
        snapshot=snapshot,
        idempotency_key=key,
        status="enviando",
        motivo_operacao=motivo,
        declarado_nao_realizada=True,
        solicitado_por=user_id,
        tentativa_em=datetime.now(timezone.utc),
        xml_validado=False,
    )
    db.add(record)
    db.flush()
    # Commit obrigatório ANTES do único POST: inclusive timeout/crash impedem reenvio.
    _persist(db, venda, record, user_id, "nfe_estorno_tentativa")
    try:
        response = api.issue_document(
            token, "nfe", record.payload, record.idempotency_key
        )
    except IntNFeError as exc:
        venda, record = _reload(db, venda, env)
        if record.status != "autorizado":
            record.status = (
                "incerto"
                if exc.uncertain or exc.status not in {400, 401, 403, 422}
                else "rejeitado"
            )
            record.codigo, record.motivo = str(exc.code)[:80], _safe_message(exc)
            _persist(db, venda, record, user_id, "nfe_estorno_resultado")
        return _result(record)
    venda, record = _reload(db, venda, env)
    correlation = response.get("correlationId") if isinstance(response, dict) else None
    if not isinstance(correlation, str) or not re.fullmatch(
        r"[A-Za-z0-9_-]{1,128}", correlation
    ):
        record.status, record.codigo, record.motivo = (
            "incerto",
            "RespostaInvalida",
            "A IntNFe não informou o identificador. Não reenviar; solicite conferência ao suporte.",
        )
    else:
        record.correlation_id, record.status = correlation, "processando"
    _persist(db, venda, record, user_id, "nfe_estorno_resultado")
    return _result(record)


def reconcile(db, venda, api, *, environment_override=None, user_id=None):
    connection = _connection(db, venda.tenant_id, require_enabled=False)
    env = _environment(connection, venda, environment_override, require_config=False)
    record = _record(db, venda, env)
    exigir(record is not None, "Não há estorno registrado para esta venda e ambiente.")
    exigir(
        record.correlation_id,
        "Resultado incerto sem identificador. O suporte precisa conferir a tentativa; não reenviar.",
    )
    correlation = record.correlation_id
    token = _access_token(api, connection, env)
    try:
        result = api.document_status(token, "nfe", correlation)
        code = str(result.get("status"))
        xml = api.document_xml(token, "nfe", correlation) if code == "3" else None
    except IntNFeError as exc:
        raise EstornoError(_safe_message(exc), status=503, code=exc.code) from None
    # Não aplicar resposta externa sobre uma instância carregada antes da rede.
    venda = (
        db.query(Venda)
        .filter(Venda.id == venda.id, Venda.tenant_id == venda.tenant_id)
        .populate_existing()
        .with_for_update()
        .one()
    )
    record = _record(db, venda, env, lock=True)
    exigir(
        record.correlation_id == correlation,
        "A tentativa de estorno mudou. Consulte novamente.",
    )
    if record.status == "autorizado" and code != "5":
        return _result(record)
    if code == "3":
        try:
            data = validate_xml(xml, record.snapshot)
            exigir(
                hashlib.sha256(venda.nfe_xml.encode()).hexdigest()
                == record.original_xml_hash
                and venda.nfe_chave == record.original_chave,
                "O documento original mudou depois da tentativa. Conferência fiscal necessária.",
            )
        except EstornoError as exc:
            record.status, record.codigo, record.motivo, record.xml_validado = (
                "divergente",
                "XmlEstornoDivergente",
                str(exc),
                False,
            )
        else:
            for field, value in data.items():
                setattr(record, field, value)
            record.xml = xml.decode("utf-8-sig") if isinstance(xml, bytes) else xml
            record.status, record.xml_validado = "autorizado", True
            record.codigo, record.motivo = None, None
    else:
        record.status = {
            "4": "rejeitado",
            "5": "cancelado",
            "6": "inutilizado",
            "8": "denegado",
        }.get(code, "processando")
        record.codigo = str(result.get("codigoErro") or "")[:80] or None
        safe = _safe_validation_errors({"erros": [result.get("motivoRejeicao")]})
        record.motivo = safe[0] if safe else None
        if record.status != "cancelado":
            record.xml_validado = False
    if record.status in {"autorizado", "cancelado"} and record.xml_validado:
        tentar_enfileirar_documento(
            db, venda.tenant_id, "intnfe", f"estorno:{record.id}"
        )
    _persist(db, venda, record, user_id, "nfe_estorno_consulta")
    return _result(record)


def download(db, venda, api, kind):
    connection = _connection(db, venda.tenant_id, require_enabled=False)
    record = _record(db, venda, venda.nfe_ambiente)
    exigir(
        record
        and record.status in {"autorizado", "cancelado"}
        and record.xml_validado
        and record.protocolo,
        "O estorno ainda não foi autorizado com XML conferido.",
    )
    if kind == "xml":
        return record.xml.encode("utf-8"), record
    token = _access_token(api, connection, record.ambiente_codigo)
    pdf = api.document_danfe(token, "nfe", record.correlation_id)
    if not isinstance(pdf, bytes) or not pdf.startswith(b"%PDF-"):
        raise EstornoError(
            "O emissor não retornou o DANFE do estorno em PDF.",
            status=503,
            code="DanfeInvalido",
        )
    return pdf, record
