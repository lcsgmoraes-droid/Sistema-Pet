"""Cadastro dos protocolos de recorrencia vinculados aos produtos."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.produtos_models import (
    Produto,
    ProdutoProtocoloDose,
    ProdutoProtocoloRecorrencia,
)


def sincronizar_protocolos_produto(
    db: Session,
    *,
    produto: Produto,
    protocolos: list[dict],
) -> None:
    """Sincroniza os protocolos dentro da mesma transacao do produto."""
    existentes = (
        db.query(ProdutoProtocoloRecorrencia)
        .filter(
            ProdutoProtocoloRecorrencia.produto_id == produto.id,
            ProdutoProtocoloRecorrencia.tenant_id == produto.tenant_id,
        )
        .all()
    )
    existentes_por_id = {item.id: item for item in existentes}
    ids_recebidos: set[int] = set()
    for dados_originais in protocolos:
        dados = dict(dados_originais)
        doses = list(dados.pop("doses", []) or [])
        protocolo_id = dados.pop("id", None)
        dados.pop("ativo", None)

        if protocolo_id is not None:
            protocolo = existentes_por_id.get(int(protocolo_id))
            if protocolo is None:
                raise ValueError(
                    "Um dos protocolos informados não pertence a este produto."
                )
            ids_recebidos.add(protocolo.id)
        else:
            protocolo = ProdutoProtocoloRecorrencia(
                tenant_id=produto.tenant_id,
                produto_id=produto.id,
            )
            db.add(protocolo)

        for campo in (
            "nome",
            "tipo",
            "especie_compativel",
            "fase_vida",
            "intervalo_recompra_dias",
            "ajustar_ao_historico",
            "reiniciar_apos_dias",
            "observacoes",
        ):
            setattr(protocolo, campo, dados.get(campo))
        protocolo.ativo = True
        db.flush()
        ids_recebidos.add(protocolo.id)

        db.query(ProdutoProtocoloDose).filter(
            ProdutoProtocoloDose.protocolo_id == protocolo.id,
            ProdutoProtocoloDose.tenant_id == produto.tenant_id,
        ).delete(synchronize_session=False)

        for dose in doses:
            db.add(
                ProdutoProtocoloDose(
                    tenant_id=produto.tenant_id,
                    protocolo_id=protocolo.id,
                    numero_dose=int(dose["numero_dose"]),
                    dias_desde_inicio=int(dose["dias_desde_inicio"]),
                )
            )
    for protocolo in existentes:
        if protocolo.id not in ids_recebidos:
            db.delete(protocolo)

    _atualizar_campos_legados(produto, protocolos)
    db.flush()


def _atualizar_campos_legados(
    produto: Produto,
    protocolos: list[dict],
) -> None:
    """Mantem clientes antigos funcionais durante a transicao do formato."""
    produto.tem_recorrencia = bool(protocolos)
    if not protocolos:
        produto.tipo_recorrencia = None
        produto.intervalo_dias = None
        produto.numero_doses = None
        produto.especie_compativel = None
        produto.observacoes_recorrencia = None
        return

    principal = protocolos[0]
    produto.especie_compativel = principal.get("especie_compativel")
    produto.observacoes_recorrencia = principal.get("observacoes")

    if principal.get("tipo") == "recompra_continua":
        produto.tipo_recorrencia = "custom"
        produto.intervalo_dias = principal.get("intervalo_recompra_dias")
        produto.numero_doses = None
        return

    doses = sorted(
        principal.get("doses", []), key=lambda dose: int(dose["numero_dose"])
    )
    produto.tipo_recorrencia = "protocol"
    produto.numero_doses = len(doses)
    produto.intervalo_dias = (
        int(doses[1]["dias_desde_inicio"]) - int(doses[0]["dias_desde_inicio"])
        if len(doses) > 1
        else principal.get("reiniciar_apos_dias")
    )


def obter_protocolo_ativo_do_produto(
    db: Session,
    *,
    protocolo_id: int | None,
    produto_id: int | None,
    tenant_id,
) -> ProdutoProtocoloRecorrencia | None:
    """Resolve um protocolo apenas quando pertence ao produto e ao tenant da venda."""
    if protocolo_id is None or produto_id is None:
        return None
    return (
        db.query(ProdutoProtocoloRecorrencia)
        .filter(
            ProdutoProtocoloRecorrencia.id == int(protocolo_id),
            ProdutoProtocoloRecorrencia.produto_id == int(produto_id),
            ProdutoProtocoloRecorrencia.tenant_id == tenant_id,
            ProdutoProtocoloRecorrencia.ativo.is_(True),
        )
        .first()
    )


__all__ = ["obter_protocolo_ativo_do_produto", "sincronizar_protocolos_produto"]
