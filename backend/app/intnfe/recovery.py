"""Correções determinísticas e nova tentativa de documentos rejeitados."""

from __future__ import annotations

from app.intnfe.emission import (
    DirectEmissionError,
    emission_fingerprint,
    issue,
    reconcile,
)
from app.intnfe.numbering import NumberingInput, advance_numbering, read_numbering


REJECTED_STATUSES = {"rejeitada"}
PENDING_STATUSES = {"aguardando", "enviando", "processando", "inconclusiva"}
AUTHORIZED_STATUSES = {"autorizada", "cancelada", "inutilizada", "denegada"}
MAX_DUPLICATE_RETRIES = 10


def _normalized(value):
    return str(value or "").strip().casefold()


def _lock_sale(db, venda):
    """Recarrega a venda com trava antes de qualquer remoção de vínculo fiscal."""
    if hasattr(db, "refresh"):
        db.refresh(venda, with_for_update=True)


def _snapshot(venda):
    return {
        "tipo": venda.nfe_tipo,
        "modelo": venda.nfe_modelo,
        "numero": venda.nfe_numero,
        "serie": venda.nfe_serie,
        "chave": venda.nfe_chave,
        "status": venda.nfe_status,
        "provedor": venda.nfe_provider,
        "correlation_id": venda.nfe_correlation_id,
        "protocolo": venda.nfe_protocolo,
        "ambiente": venda.nfe_ambiente,
        "codigo_erro": venda.nfe_codigo_erro,
        "motivo_rejeicao": venda.nfe_motivo_rejeicao,
    }


def _clear_rejected_attempt(venda):
    """Limpa somente uma tentativa cujo resultado negativo já foi confirmado."""
    status = _normalized(venda.nfe_status)
    if status not in REJECTED_STATUSES:
        raise DirectEmissionError(
            "A correção automática só pode refazer uma nota confirmada como rejeitada.",
            status=409,
            code="ReemissaoNaoSegura",
        )
    if venda.nfe_protocolo or venda.nfe_data_autorizacao:
        raise DirectEmissionError(
            "A nota possui dados de autorização e não pode ser refeita automaticamente.",
            status=409,
            code="ReemissaoNaoSegura",
        )

    venda.nfe_tipo = None
    venda.nfe_modelo = None
    venda.nfe_numero = None
    venda.nfe_serie = None
    venda.nfe_chave = None
    venda.nfe_status = None
    venda.nfe_bling_id = None
    venda.nfe_provider = None
    venda.nfe_correlation_id = None
    venda.nfe_protocolo = None
    venda.nfe_ambiente = None
    venda.nfe_codigo_erro = None
    venda.nfe_idempotency_key = None
    venda.nfe_payload_hash = None
    venda.nfe_xml = None
    venda.nfe_data_emissao = None
    venda.nfe_data_autorizacao = None
    venda.nfe_motivo_rejeicao = None
    if venda.status == "pago_nf":
        venda.status = "finalizada"


def _advance_after_duplicate(db, tenant_id, api, venda, numbering_audit):
    failed_number = int(venda.nfe_numero or 0)
    series = str(venda.nfe_serie or "")
    model = int(venda.nfe_modelo or 0)
    environment = int(venda.nfe_ambiente or 0)
    if (
        not failed_number
        or not series
        or model not in {55, 65}
        or environment not in {1, 2}
    ):
        raise DirectEmissionError(
            "A rejeição por duplicidade não trouxe número, série, modelo e ambiente suficientes para corrigir a sequência.",
            status=409,
            code="NumeracaoIncompleta",
        )

    view = read_numbering(db, tenant_id, api)
    current = next(
        (
            row
            for row in view.series
            if (row.serie, row.modelo, row.ambienteCodigo)
            == (str(int(series)), model, environment)
        ),
        None,
    )
    last = current.ultimoNumero if current else 0
    if last >= failed_number:
        return None

    return advance_numbering(
        db,
        tenant_id,
        api,
        NumberingInput(
            serie=series,
            ambiente_codigo=environment,
            modelo=model,
            proximo_numero=failed_number + 1,
            ultimo_numero_consultado=last,
        ),
        numbering_audit,
    )


def repair_and_retry(
    db,
    tenant,
    venda,
    api,
    *,
    reset_audit,
    numbering_audit,
    max_duplicate_retries=MAX_DUPLICATE_RETRIES,
):
    """Corrige o que é comprovável, remove a rejeição e transmite novamente."""
    _lock_sale(db, venda)
    status = _normalized(venda.nfe_status)
    if status in PENDING_STATUSES:
        if venda.nfe_correlation_id:
            current = reconcile(db, venda, api)
            if current["processando"]:
                raise DirectEmissionError(
                    "A tentativa existente ainda está em processamento. O CorePet consultou o emissor e não criará outra nota.",
                    status=409,
                    code="ResultadoNaoConfirmado",
                    correlation=venda.nfe_correlation_id,
                )
            if current["success"]:
                return {
                    **current,
                    "correcoes_aplicadas": ["Status atualizado no emissor."],
                }
            status = _normalized(venda.nfe_status)
        else:
            raise DirectEmissionError(
                "Existe um envio sem confirmação. Consulte o suporte antes de tentar outra nota.",
                status=409,
                code="ResultadoNaoConfirmado",
            )
    if status in AUTHORIZED_STATUSES:
        raise DirectEmissionError(
            "Esta nota possui um resultado fiscal definitivo e não pode ser reemitida.",
            status=409,
            code="ReemissaoNaoSegura",
        )
    if status not in REJECTED_STATUSES or venda.nfe_provider != "intnfe":
        raise DirectEmissionError(
            "Não existe uma nota rejeitada pela IntNFe para corrigir nesta venda.",
            status=409,
            code="RejeicaoNaoEncontrada",
        )

    document_type = (
        "nfe" if (venda.nfe_tipo == "nfe" or venda.nfe_modelo == "55") else "nfce"
    )
    applied = []

    for duplicate_attempt in range(max_duplicate_retries + 1):
        _lock_sale(db, venda)
        if _normalized(venda.nfe_status) not in REJECTED_STATUSES:
            raise DirectEmissionError(
                "A situação da nota mudou enquanto a correção era preparada. Atualize a Central de NF antes de continuar.",
                status=409,
                code="SituacaoAlterada",
                correlation=venda.nfe_correlation_id,
            )
        attempt_signature = (
            venda.nfe_correlation_id,
            venda.nfe_codigo_erro,
            venda.nfe_numero,
            venda.nfe_serie,
        )
        # A montagem completa funciona como trava: só limpamos a rejeição quando
        # cadastro, lote, totais, pagamento e tributação atuais já são válidos.
        previous_fingerprint = venda.nfe_payload_hash
        current_fingerprint = emission_fingerprint(db, tenant, venda, document_type)
        duplicate_number = str(venda.nfe_codigo_erro or "").strip() == "539"
        if not duplicate_number and (
            not previous_fingerprint or previous_fingerprint == current_fingerprint
        ):
            raise DirectEmissionError(
                "O CorePet validou os dados, mas não encontrou uma correção automática segura para esta rejeição. Revise o motivo informado antes de transmitir outra nota.",
                status=409,
                code="CorrecaoAutomaticaIndisponivel",
                correlation=venda.nfe_correlation_id,
            )
        if not duplicate_number:
            applied.append(
                "Dados da venda ou do lote fiscal foram corrigidos desde a rejeição."
            )

        if duplicate_number:
            changed = _advance_after_duplicate(
                db, tenant.id, api, venda, numbering_audit
            )
            if changed is not None:
                applied.append(
                    f"Sequência fiscal avançada após a rejeição do número {venda.nfe_numero}."
                )

        # A consulta de numeração pode liberar a transação. Antes de limpar os
        # campos, a linha é travada de novo e a tentativa precisa ser a mesma.
        _lock_sale(db, venda)
        current_signature = (
            venda.nfe_correlation_id,
            venda.nfe_codigo_erro,
            venda.nfe_numero,
            venda.nfe_serie,
        )
        if (
            _normalized(venda.nfe_status) not in REJECTED_STATUSES
            or current_signature != attempt_signature
        ):
            raise DirectEmissionError(
                "A situação da nota mudou enquanto a correção era preparada. Atualize a Central de NF antes de continuar.",
                status=409,
                code="SituacaoAlterada",
                correlation=venda.nfe_correlation_id,
            )

        old_value = _snapshot(venda)
        _clear_rejected_attempt(venda)
        reset_audit(old_value, {"resultado": "tentativa_rejeitada_removida"})
        db.commit()
        applied.append("Tentativa rejeitada removida com segurança.")

        result = issue(db, tenant, venda, document_type, api)
        result = {**result, "correcoes_aplicadas": list(dict.fromkeys(applied))}
        if (
            result["success"]
            or result["processando"]
            or str(result.get("codigo_erro") or "") != "539"
        ):
            return result
        if duplicate_attempt >= max_duplicate_retries:
            raise DirectEmissionError(
                "A sequência encontrou muitas numerações já usadas. Confira o último número no sistema anterior e ajuste a numeração fiscal.",
                status=409,
                code="LimiteDuplicidade",
                correlation=result.get("correlation_id"),
            )

    raise DirectEmissionError(
        "Não foi possível concluir a correção automática.", status=409
    )
