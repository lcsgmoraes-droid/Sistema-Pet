from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, inspect, text
from sqlalchemy.orm import Session

from app.produto_config_fiscal_models import ProdutoConfigFiscal
from app.produtos_models import (
    Produto,
    ProdutoBlingSync,
    ProdutoBlingSyncQueue,
    ProdutoFornecedor,
    ProdutoGranelVinculo,
    ProdutoKitComponente,
    ProdutoListaPreco,
)
from app.utils.tenant_safe_sql import execute_tenant_safe
from app.services.produto_alias_service import _lock_alias_namespace
from app.services.produto_merge_safety import (
    PROTECTED_FIELDS,
    prepare_merge,
    preserve_aliases,
    preview_safety,
    record_merge,
    reference_snapshot,
)


from app.services.produto_merge_fields import CAMPOS_CADASTRAIS_FUSAO

ESTOQUE_SOMAR_CAMPOS = ("estoque_atual", "estoque_fisico", "estoque_ecommerce")

TABELAS_FK_ESPECIAIS = {
    "produto_bling_sync",
    "produto_config_fiscal",
    "produto_fornecedores",
    "produto_granel_vinculos",
    "produto_kit_componentes",
    "produto_listas_preco",
    "duplicatas_ignoradas",
    "produto_sku_aliases",
    "produto_bling_sync_queue",
    "produto_bling_cost_sync_queue",
}


def _valor_vazio(valor: Any) -> bool:
    if valor is None:
        return True
    if isinstance(valor, str):
        return not valor.strip()
    if isinstance(valor, (list, dict, tuple, set)):
        return len(valor) == 0
    return False


def _valores_iguais(valor_a: Any, valor_b: Any) -> bool:
    if isinstance(valor_a, datetime) or isinstance(valor_b, datetime):
        return str(valor_a or "") == str(valor_b or "")
    return valor_a == valor_b


def _valor_serializavel(valor: Any) -> Any:
    if isinstance(valor, datetime):
        return valor.isoformat()
    return valor


def _identificador(nome: str) -> str:
    return '"' + nome.replace('"', '""') + '"'


def _produto_resumo(produto: Produto) -> dict[str, Any]:
    return {
        "id": produto.id,
        "codigo": produto.codigo,
        "nome": produto.nome,
        "ativo": produto.ativo,
        "estoque_atual": produto.estoque_atual,
        "preco_venda": produto.preco_venda,
        "preco_custo": produto.preco_custo,
    }


def _obter_produtos(
    db: Session, tenant_id: Any, principal_id: int, duplicado_id: int, *, lock=False
) -> tuple[Produto, Produto]:
    if principal_id == duplicado_id:
        raise ValueError("Selecione dois produtos diferentes para fundir.")

    query = (
        db.query(Produto)
        .filter(
            Produto.tenant_id == tenant_id,
            Produto.id.in_([principal_id, duplicado_id]),
        )
        .order_by(Produto.id)
    )
    if lock:
        query = query.with_for_update().populate_existing()
    produtos = query.all()
    por_id = {int(produto.id): produto for produto in produtos}
    principal = por_id.get(int(principal_id))
    duplicado = por_id.get(int(duplicado_id))
    if not principal or not duplicado:
        raise ValueError("Produto principal ou duplicado nao encontrado neste tenant.")
    return principal, duplicado


def _consultar_fks_produto(db: Session) -> list[dict[str, str]]:
    if db.get_bind().dialect.name == "sqlite":
        inspector = inspect(db.connection())
        return [
            {"table_name": table, "column_name": column}
            for table in inspector.get_table_names()
            for fk in inspector.get_foreign_keys(table)
            if fk["referred_table"] == "produtos"
            for column, referred in zip(
                fk["constrained_columns"], fk["referred_columns"]
            )
            if referred == "id"
        ]
    rows = db.execute(
        text(
            """
            select tc.table_name, kcu.column_name
            from information_schema.table_constraints tc
            join information_schema.key_column_usage kcu
              on tc.constraint_name = kcu.constraint_name
             and tc.table_schema = kcu.table_schema
            join information_schema.constraint_column_usage ccu
              on ccu.constraint_name = tc.constraint_name
             and ccu.table_schema = tc.table_schema
            where tc.constraint_type = 'FOREIGN KEY'
              and tc.table_schema = 'public'
              and ccu.table_name = 'produtos'
              and ccu.column_name = 'id'
            order by tc.table_name, kcu.column_name
            """
        )
    ).mappings()
    return [
        {"table_name": row["table_name"], "column_name": row["column_name"]}
        for row in rows
    ]


def _contar_referencias(db: Session, produto_id: int) -> list[dict[str, Any]]:
    referencias = []
    for fk in _consultar_fks_produto(db):
        table_name = fk["table_name"]
        column_name = fk["column_name"]
        if table_name == "produtos" and column_name == "id":
            continue
        sql = text(
            f"select count(*) from {_identificador(table_name)} "
            f"where {_identificador(column_name)} = :produto_id"
        )
        total = int(db.execute(sql, {"produto_id": produto_id}).scalar() or 0)
        if total:
            referencias.append(
                {"tabela": table_name, "campo": column_name, "total": total}
            )
    return referencias


def montar_preview_fusao_produtos(
    db: Session,
    *,
    tenant_id: Any,
    principal_id: int,
    duplicado_id: int,
    estrategia_estoque: str = "somar",
) -> dict[str, Any]:
    principal, duplicado = _obter_produtos(db, tenant_id, principal_id, duplicado_id)
    campos = []

    for campo, label in CAMPOS_CADASTRAIS_FUSAO:
        valor_principal = getattr(principal, campo, None)
        valor_duplicado = getattr(duplicado, campo, None)
        principal_vazio = _valor_vazio(valor_principal)
        duplicado_vazio = _valor_vazio(valor_duplicado)
        conflito = (
            not principal_vazio
            and not duplicado_vazio
            and not _valores_iguais(valor_principal, valor_duplicado)
        )

        if principal_vazio and not duplicado_vazio:
            origem_padrao = "duplicado"
        else:
            origem_padrao = "principal"

        campos.append(
            {
                "campo": campo,
                "label": label,
                "principal": _valor_serializavel(valor_principal),
                "duplicado": _valor_serializavel(valor_duplicado),
                "conflito": conflito,
                "origem_padrao": origem_padrao,
                "automatico_por_vazio": principal_vazio and not duplicado_vazio,
            }
        )

    estoque_preview = {
        campo: {
            "principal": float(getattr(principal, campo, None) or 0),
            "duplicado": float(getattr(duplicado, campo, None) or 0),
            "final": float(getattr(principal, campo, None) or 0)
            + float(getattr(duplicado, campo, None) or 0),
        }
        for campo in ESTOQUE_SOMAR_CAMPOS
    }

    return {
        "principal": _produto_resumo(principal),
        "duplicado": _produto_resumo(duplicado),
        "campos": campos,
        "estoque_somado": estoque_preview,
        "referencias_duplicado": _contar_referencias(db, duplicado.id),
        **preview_safety(db, principal, duplicado, estrategia_estoque),
    }


def _gerar_codigo_merged_unico(db: Session, tenant_id: Any, duplicado: Produto) -> str:
    base = f"MERGED-{duplicado.id}"
    codigo_original = str(duplicado.codigo or "").strip()
    if codigo_original:
        base = f"{base}-{codigo_original}"
    base = base[:50]
    candidato = base
    contador = 1
    while (
        db.query(Produto.id)
        .filter(
            Produto.tenant_id == tenant_id,
            func.lower(func.trim(Produto.codigo)) == candidato.lower(),
            Produto.id != duplicado.id,
        )
        .first()
    ):
        sufixo = f"-{contador}"
        candidato = f"{base[: 50 - len(sufixo)]}{sufixo}"
        contador += 1
    return candidato


def _copiar_campos_fiscais(
    primary: ProdutoConfigFiscal, duplicate: ProdutoConfigFiscal
) -> None:
    for column in ProdutoConfigFiscal.__table__.columns:
        name = column.name
        if name in {"id", "produto_id", "tenant_id", "created_at", "updated_at"}:
            continue
        if _valor_vazio(getattr(primary, name, None)) and not _valor_vazio(
            getattr(duplicate, name, None)
        ):
            setattr(primary, name, getattr(duplicate, name))


def _mesclar_config_fiscal(
    db: Session, principal_id: int, duplicado_id: int, tenant_id: Any
) -> int:
    primary = (
        db.query(ProdutoConfigFiscal)
        .filter(
            ProdutoConfigFiscal.tenant_id == tenant_id,
            ProdutoConfigFiscal.produto_id == principal_id,
        )
        .first()
    )
    duplicate = (
        db.query(ProdutoConfigFiscal)
        .filter(
            ProdutoConfigFiscal.tenant_id == tenant_id,
            ProdutoConfigFiscal.produto_id == duplicado_id,
        )
        .first()
    )
    if not duplicate:
        return 0
    if primary:
        _copiar_campos_fiscais(primary, duplicate)
        db.delete(duplicate)
    else:
        duplicate.produto_id = principal_id
    return 1


def _mesclar_fornecedores(
    db: Session, principal_id: int, duplicado_id: int, tenant_id: Any
) -> int:
    transferidos = 0
    duplicados = (
        db.query(ProdutoFornecedor)
        .filter(
            ProdutoFornecedor.tenant_id == tenant_id,
            ProdutoFornecedor.produto_id == duplicado_id,
        )
        .all()
    )
    for vinculo in duplicados:
        existente = (
            db.query(ProdutoFornecedor)
            .filter(
                ProdutoFornecedor.tenant_id == tenant_id,
                ProdutoFornecedor.produto_id == principal_id,
                ProdutoFornecedor.fornecedor_id == vinculo.fornecedor_id,
            )
            .first()
        )
        if existente:
            for campo in (
                "codigo_fornecedor",
                "preco_custo",
                "prazo_entrega",
                "estoque_fornecedor",
            ):
                if _valor_vazio(getattr(existente, campo, None)) and not _valor_vazio(
                    getattr(vinculo, campo, None)
                ):
                    setattr(existente, campo, getattr(vinculo, campo))
            existente.e_principal = bool(existente.e_principal or vinculo.e_principal)
            existente.ativo = bool(existente.ativo or vinculo.ativo)
            db.delete(vinculo)
        else:
            vinculo.produto_id = principal_id
        transferidos += 1
    return transferidos


def _mesclar_listas_preco(
    db: Session, principal_id: int, duplicado_id: int, tenant_id: Any
) -> int:
    transferidos = 0
    duplicados = (
        db.query(ProdutoListaPreco)
        .filter(
            ProdutoListaPreco.tenant_id == tenant_id,
            ProdutoListaPreco.produto_id == duplicado_id,
        )
        .all()
    )
    for item in duplicados:
        existente = (
            db.query(ProdutoListaPreco)
            .filter(
                ProdutoListaPreco.tenant_id == tenant_id,
                ProdutoListaPreco.produto_id == principal_id,
                ProdutoListaPreco.lista_preco_id == item.lista_preco_id,
            )
            .first()
        )
        if existente:
            if not existente.ativo and item.ativo:
                existente.preco = item.preco
                existente.desconto_percentual = item.desconto_percentual
                existente.desconto_valor = item.desconto_valor
                existente.ativo = True
            db.delete(item)
        else:
            item.produto_id = principal_id
        transferidos += 1
    return transferidos


def _mesclar_bling_sync(
    db: Session, principal_id: int, duplicado_id: int, tenant_id: Any
) -> int:
    # Preserve transitive retired identities when a previous survivor is merged.
    retired = (
        db.query(ProdutoBlingSync)
        .filter(
            ProdutoBlingSync.tenant_id == tenant_id,
            ProdutoBlingSync.retirado_para_produto_id == duplicado_id,
        )
        .order_by(ProdutoBlingSync.id)
        .with_for_update()
        .all()
    )
    for link in retired:
        if link.produto_id == principal_id:
            raise ValueError("Ciclo de identidade Bling detectado; fusao bloqueada.")
        link.retirado_para_produto_id = principal_id
        link.sincronizar = False
    primary = (
        db.query(ProdutoBlingSync)
        .filter(
            ProdutoBlingSync.tenant_id == tenant_id,
            ProdutoBlingSync.produto_id == principal_id,
        )
        .first()
    )
    duplicate = (
        db.query(ProdutoBlingSync)
        .filter(
            ProdutoBlingSync.tenant_id == tenant_id,
            ProdutoBlingSync.produto_id == duplicado_id,
        )
        .first()
    )
    if not duplicate:
        return 0
    if primary:
        # The old external identity and its historical queue stay attached to
        # the archived product. It can resolve orders, never publish inventory.
        duplicate.retirado_para_produto_id = principal_id
        duplicate.sincronizar = False
        duplicate.estoque_compartilhado = False
        duplicate.status = "retirado_fusao"
        duplicate.proxima_tentativa_sync = None
    else:
        duplicate.produto_id = principal_id
        db.query(ProdutoBlingSyncQueue).filter(
            ProdutoBlingSyncQueue.tenant_id == tenant_id,
            ProdutoBlingSyncQueue.sync_id == duplicate.id,
            ProdutoBlingSyncQueue.produto_id == duplicado_id,
        ).update(
            {ProdutoBlingSyncQueue.produto_id: principal_id}, synchronize_session=False
        )
    return 1


def _mesclar_componentes_kit(
    db: Session, principal_id: int, duplicado_id: int, tenant_id: Any
) -> int:
    alterados = 0
    componentes = (
        db.query(ProdutoKitComponente)
        .filter(
            ProdutoKitComponente.tenant_id == tenant_id,
            (ProdutoKitComponente.kit_id == duplicado_id)
            | (ProdutoKitComponente.produto_componente_id == duplicado_id),
        )
        .all()
    )
    for componente in componentes:
        novo_kit_id = (
            principal_id if componente.kit_id == duplicado_id else componente.kit_id
        )
        novo_componente_id = (
            principal_id
            if componente.produto_componente_id == duplicado_id
            else componente.produto_componente_id
        )

        if novo_kit_id == novo_componente_id:
            db.delete(componente)
            alterados += 1
            continue

        existente = (
            db.query(ProdutoKitComponente)
            .filter(
                ProdutoKitComponente.tenant_id == tenant_id,
                ProdutoKitComponente.kit_id == novo_kit_id,
                ProdutoKitComponente.produto_componente_id == novo_componente_id,
                ProdutoKitComponente.id != componente.id,
            )
            .first()
        )
        if existente:
            existente.quantidade = float(existente.quantidade or 0) + float(
                componente.quantidade or 0
            )
            existente.opcional = bool(existente.opcional and componente.opcional)
            db.delete(componente)
        else:
            componente.kit_id = novo_kit_id
            componente.produto_componente_id = novo_componente_id
        alterados += 1
    return alterados


def _mesclar_vinculos_granel(
    db: Session, principal_id: int, duplicado_id: int, tenant_id: Any
) -> int:
    alterados = 0
    vinculos = (
        db.query(ProdutoGranelVinculo)
        .filter(
            ProdutoGranelVinculo.tenant_id == tenant_id,
            (ProdutoGranelVinculo.produto_origem_id == duplicado_id)
            | (ProdutoGranelVinculo.produto_granel_id == duplicado_id),
        )
        .all()
    )
    for vinculo in vinculos:
        nova_origem = (
            principal_id
            if vinculo.produto_origem_id == duplicado_id
            else vinculo.produto_origem_id
        )
        novo_granel = (
            principal_id
            if vinculo.produto_granel_id == duplicado_id
            else vinculo.produto_granel_id
        )

        if nova_origem == novo_granel:
            db.delete(vinculo)
            alterados += 1
            continue

        existente = (
            db.query(ProdutoGranelVinculo)
            .filter(
                ProdutoGranelVinculo.tenant_id == tenant_id,
                ProdutoGranelVinculo.produto_origem_id == nova_origem,
                ProdutoGranelVinculo.produto_granel_id == novo_granel,
                ProdutoGranelVinculo.id != vinculo.id,
            )
            .first()
        )
        if existente:
            existente.ativo = bool(existente.ativo or vinculo.ativo)
            if not existente.observacao and vinculo.observacao:
                existente.observacao = vinculo.observacao
            db.delete(vinculo)
        else:
            vinculo.produto_origem_id = nova_origem
            vinculo.produto_granel_id = novo_granel
        alterados += 1
    return alterados


def _transferir_referencias_genericas(
    db: Session,
    *,
    principal_id: int,
    duplicado_id: int,
    tenant_id: Any,
) -> list[dict[str, Any]]:
    transferencias = []
    for fk in _consultar_fks_produto(db):
        tabela = fk["table_name"]
        campo = fk["column_name"]
        if tabela in TABELAS_FK_ESPECIAIS:
            continue
        if tabela == "produtos" and campo == "produto_predecessor_id":
            continue
        tenant_predicate = ""
        if any(
            column["name"] == "tenant_id"
            for column in inspect(db.connection()).get_columns(tabela)
        ):
            tenant_predicate = " and tenant_id = :tenant_id"
        if tabela == "produtos" and campo == "produto_pai_id":
            sql = text(
                f"update {_identificador(tabela)} set {_identificador(campo)} = :principal_id "
                f"where {_identificador(campo)} = :duplicado_id and id != :duplicado_id{tenant_predicate}"
            )
        else:
            sql = text(
                f"update {_identificador(tabela)} set {_identificador(campo)} = :principal_id "
                f"where {_identificador(campo)} = :duplicado_id{tenant_predicate}"
            )
        result = db.execute(
            sql,
            {
                "principal_id": principal_id,
                "duplicado_id": duplicado_id,
                "tenant_id": str(tenant_id)
                if db.get_bind().dialect.name == "postgresql"
                else str(tenant_id).replace("-", ""),
            },
        )
        if result.rowcount:
            transferencias.append(
                {"tabela": tabela, "campo": campo, "total": int(result.rowcount)}
            )
    return transferencias


def executar_fusao_produtos(
    db: Session,
    *,
    tenant_id: Any,
    principal_id: int,
    duplicado_id: int,
    decisoes_campos: dict[str, str] | None,
    user_id: int,
    observacao: str | None = None,
    estrategia_estoque: str = "somar",
    preview_token: str | None = None,
    preservar_vinculo_bling_duplicado: bool = False,
    aliases_sku: list[str] | None = None,
) -> dict[str, Any]:
    _lock_alias_namespace(db, tenant_id)
    principal, duplicado = _obter_produtos(
        db, tenant_id, principal_id, duplicado_id, lock=True
    )
    aliases_sku = aliases_sku or []
    if (estrategia_estoque == "manter_principal" or aliases_sku) and len(
        str(observacao or "").strip()
    ) < 10:
        raise ValueError(
            "Informe a evidencia da contagem ou identidade confirmada (ao menos 10 caracteres)."
        )
    motivo = str(observacao or "Fusao de cadastros confirmada pelo operador.").strip()
    before = prepare_merge(
        db,
        principal,
        duplicado,
        estrategia=estrategia_estoque,
        preview_token=preview_token,
        preservar_bling=preservar_vinculo_bling_duplicado,
        aliases=aliases_sku,
        motivo=motivo,
    )
    references_before = reference_snapshot(
        db, duplicado.id, _consultar_fks_produto(db), tenant_id=tenant_id
    )
    aliases_applied = preserve_aliases(
        db, principal, duplicado, aliases=aliases_sku, user_id=user_id, motivo=motivo
    )
    agora = datetime.utcnow()
    decisoes_campos = decisoes_campos or {}
    codigo_original_duplicado = duplicado.codigo

    campos_aplicados = []
    for campo, label in CAMPOS_CADASTRAIS_FUSAO:
        if campo in ESTOQUE_SOMAR_CAMPOS:
            continue
        if estrategia_estoque == "manter_principal" and (
            campo in PROTECTED_FIELDS
            or campo.startswith("preco_")
            or campo.startswith("promocao_")
        ):
            continue
        valor_principal = getattr(principal, campo, None)
        valor_duplicado = getattr(duplicado, campo, None)
        origem = decisoes_campos.get(campo)
        if origem not in {"principal", "duplicado"}:
            origem = (
                "duplicado"
                if _valor_vazio(valor_principal) and not _valor_vazio(valor_duplicado)
                else "principal"
            )

        if origem == "duplicado" and not _valor_vazio(valor_duplicado):
            setattr(principal, campo, valor_duplicado)
            campos_aplicados.append(
                {"campo": campo, "label": label, "origem": "duplicado"}
            )

    for campo in ESTOQUE_SOMAR_CAMPOS:
        if estrategia_estoque == "somar":
            setattr(
                principal,
                campo,
                float(getattr(principal, campo, None) or 0)
                + float(getattr(duplicado, campo, None) or 0),
            )
        setattr(duplicado, campo, 0)

    transferidos_especiais = {
        "produto_fornecedores": _mesclar_fornecedores(
            db, principal.id, duplicado.id, tenant_id
        ),
        "produto_listas_preco": _mesclar_listas_preco(
            db, principal.id, duplicado.id, tenant_id
        ),
        "produto_bling_sync": _mesclar_bling_sync(
            db, principal.id, duplicado.id, tenant_id
        ),
        "produto_config_fiscal": _mesclar_config_fiscal(
            db, principal.id, duplicado.id, tenant_id
        ),
        "produto_kit_componentes": _mesclar_componentes_kit(
            db, principal.id, duplicado.id, tenant_id
        ),
        "produto_granel_vinculos": _mesclar_vinculos_granel(
            db, principal.id, duplicado.id, tenant_id
        ),
    }

    execute_tenant_safe(
        db,
        """
        delete from duplicatas_ignoradas
        where {tenant_filter}
          and (
            produto_id_1 in (:principal_id, :duplicado_id)
            or produto_id_2 in (:principal_id, :duplicado_id)
          )
        """,
        {"principal_id": principal.id, "duplicado_id": duplicado.id},
        tenant_id=tenant_id,
    )

    transferidos_genericos = _transferir_referencias_genericas(
        db,
        principal_id=principal.id,
        duplicado_id=duplicado.id,
        tenant_id=tenant_id,
    )

    duplicado.codigo = _gerar_codigo_merged_unico(db, tenant_id, duplicado)
    duplicado.ativo = False
    duplicado.situacao = False
    duplicado.deleted_at = duplicado.deleted_at or agora
    duplicado.data_descontinuacao = duplicado.data_descontinuacao or agora
    duplicado.produto_predecessor_id = principal.id
    duplicado.motivo_descontinuacao = (
        f"Fundido no produto #{principal.id} ({principal.codigo}). SKU original: {codigo_original_duplicado or '-'}"
    )[:255]

    principal.updated_at = agora
    duplicado.updated_at = agora

    db.flush()
    audit = record_merge(
        db,
        principal,
        duplicado,
        user_id=user_id,
        estrategia=estrategia_estoque,
        motivo=motivo,
        before=before,
        references=references_before,
        aliases=aliases_applied,
    )
    db.commit()
    db.refresh(principal)
    db.refresh(duplicado)

    return {
        "success": True,
        "auditoria_id": audit.id,
        "aliases_sku": aliases_applied,
        "estrategia_estoque": estrategia_estoque,
        "principal": _produto_resumo(principal),
        "duplicado_inativado": _produto_resumo(duplicado),
        "campos_aplicados": campos_aplicados,
        "estoque_somado": {
            campo: getattr(principal, campo, None) for campo in ESTOQUE_SOMAR_CAMPOS
        },
        "transferidos_especiais": transferidos_especiais,
        "transferidos_genericos": transferidos_genericos,
    }
