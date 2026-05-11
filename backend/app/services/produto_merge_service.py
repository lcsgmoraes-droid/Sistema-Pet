from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, text
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


CAMPOS_CADASTRAIS_FUSAO: list[tuple[str, str]] = [
    ("codigo", "SKU"),
    ("nome", "Nome"),
    ("tipo", "Tipo"),
    ("tipo_produto", "Tipo do produto"),
    ("is_parent", "Produto pai"),
    ("is_sellable", "Vendavel"),
    ("produto_pai_id", "Produto pai vinculado"),
    ("variation_attributes", "Atributos da variacao"),
    ("variation_signature", "Assinatura da variacao"),
    ("tipo_kit", "Tipo de kit"),
    ("descricao_curta", "Descricao curta"),
    ("descricao_completa", "Descricao completa"),
    ("tags", "Tags"),
    ("codigo_barras", "Codigo de barras"),
    ("codigos_barras_alternativos", "Codigos de barras alternativos"),
    ("categoria_id", "Categoria"),
    ("subcategoria", "Subcategoria"),
    ("marca_id", "Marca"),
    ("fornecedor_id", "Fornecedor principal"),
    ("departamento_id", "Departamento"),
    ("preco_custo", "Preco de custo"),
    ("preco_venda", "Preco de venda"),
    ("preco_promocional", "Preco promocional ERP"),
    ("promocao_inicio", "Inicio da promocao ERP"),
    ("promocao_fim", "Fim da promocao ERP"),
    ("promocao_ativa", "Promocao ativa"),
    ("preco_ecommerce", "Preco e-commerce"),
    ("preco_ecommerce_promo", "Preco promocional e-commerce"),
    ("preco_ecommerce_promo_inicio", "Inicio promo e-commerce"),
    ("preco_ecommerce_promo_fim", "Fim promo e-commerce"),
    ("preco_app", "Preco app"),
    ("preco_app_promo", "Preco promocional app"),
    ("preco_app_promo_inicio", "Inicio promo app"),
    ("preco_app_promo_fim", "Fim promo app"),
    ("anunciar_ecommerce", "Anunciar no e-commerce"),
    ("anunciar_app", "Anunciar no app"),
    ("estoque_minimo", "Estoque minimo"),
    ("estoque_maximo", "Estoque maximo"),
    ("localizacao", "Localizacao"),
    ("crossdocking_dias", "Crossdocking"),
    ("controle_lote", "Controle de lote"),
    ("unidade", "Unidade"),
    ("condicao", "Condicao"),
    ("e_granel", "Produto granel"),
    ("participa_sugestao_compra", "Participa da sugestao de compra"),
    ("peso_liquido", "Peso liquido"),
    ("peso_bruto", "Peso bruto"),
    ("largura", "Largura"),
    ("altura", "Altura"),
    ("profundidade", "Profundidade"),
    ("volume", "Volume"),
    ("itens_por_caixa", "Itens por caixa"),
    ("frete_gratis", "Frete gratis"),
    ("producao", "Producao"),
    ("ncm", "NCM"),
    ("cest", "CEST"),
    ("gtin_ean", "GTIN/EAN"),
    ("gtin_ean_tributario", "GTIN/EAN tributario"),
    ("origem", "Origem fiscal"),
    ("perfil_tributario", "Perfil tributario"),
    ("forma_aquisicao", "Forma de aquisicao"),
    ("tipo_item", "Tipo do item"),
    ("percentual_tributos", "Percentual de tributos"),
    ("icms_base_retencao", "ICMS base retencao"),
    ("icms_valor_retencao", "ICMS valor retencao"),
    ("icms_valor_proprio", "ICMS valor proprio"),
    ("ipi_codigo_excecao", "IPI codigo excecao"),
    ("pis_valor_fixo", "PIS valor fixo"),
    ("cofins_valor_fixo", "COFINS valor fixo"),
    ("cfop", "CFOP"),
    ("aliquota_icms", "Aliquota ICMS"),
    ("aliquota_pis", "Aliquota PIS"),
    ("aliquota_cofins", "Aliquota COFINS"),
    ("informacoes_adicionais_nf", "Informacoes adicionais NF"),
    ("comissao_padrao", "Comissao padrao"),
    ("limite_desconto", "Limite de desconto"),
    ("data_validade", "Data de validade"),
    ("tem_recorrencia", "Tem recorrencia"),
    ("tipo_recorrencia", "Tipo de recorrencia"),
    ("intervalo_dias", "Intervalo em dias"),
    ("numero_doses", "Numero de doses"),
    ("observacoes_recorrencia", "Observacoes de recorrencia"),
    ("especie_compativel", "Especie compativel"),
    ("classificacao_racao", "Classificacao racao"),
    ("peso_embalagem", "Peso da embalagem"),
    ("tabela_nutricional", "Tabela nutricional"),
    ("categoria_racao", "Categoria da racao"),
    ("especies_indicadas", "Especies indicadas"),
    ("tabela_consumo", "Tabela de consumo"),
    ("porte_animal", "Porte animal"),
    ("fase_publico", "Fase/publico"),
    ("tipo_tratamento", "Tipo de tratamento"),
    ("sabor_proteina", "Sabor/proteina"),
    ("auto_classificar_nome", "Auto classificar nome"),
    ("linha_racao_id", "Linha da racao"),
    ("porte_animal_id", "Porte animal cadastrado"),
    ("fase_publico_id", "Fase/publico cadastrado"),
    ("tipo_tratamento_id", "Tratamento cadastrado"),
    ("sabor_proteina_id", "Sabor/proteina cadastrado"),
    ("apresentacao_peso_id", "Apresentacao/peso"),
    ("imagem_principal", "Imagem principal"),
]

ESTOQUE_SOMAR_CAMPOS = ("estoque_atual", "estoque_fisico", "estoque_ecommerce")

TABELAS_FK_ESPECIAIS = {
    "produto_bling_sync",
    "produto_config_fiscal",
    "produto_fornecedores",
    "produto_granel_vinculos",
    "produto_kit_componentes",
    "produto_listas_preco",
    "duplicatas_ignoradas",
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


def _obter_produtos(db: Session, tenant_id: Any, principal_id: int, duplicado_id: int) -> tuple[Produto, Produto]:
    if principal_id == duplicado_id:
        raise ValueError("Selecione dois produtos diferentes para fundir.")

    produtos = (
        db.query(Produto)
        .filter(
            Produto.tenant_id == tenant_id,
            Produto.id.in_([principal_id, duplicado_id]),
        )
        .all()
    )
    por_id = {int(produto.id): produto for produto in produtos}
    principal = por_id.get(int(principal_id))
    duplicado = por_id.get(int(duplicado_id))
    if not principal or not duplicado:
        raise ValueError("Produto principal ou duplicado nao encontrado neste tenant.")
    return principal, duplicado


def _consultar_fks_produto(db: Session) -> list[dict[str, str]]:
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
    return [{"table_name": row["table_name"], "column_name": row["column_name"]} for row in rows]


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
            referencias.append({"tabela": table_name, "campo": column_name, "total": total})
    return referencias


def montar_preview_fusao_produtos(
    db: Session,
    *,
    tenant_id: Any,
    principal_id: int,
    duplicado_id: int,
) -> dict[str, Any]:
    principal, duplicado = _obter_produtos(db, tenant_id, principal_id, duplicado_id)
    campos = []

    for campo, label in CAMPOS_CADASTRAIS_FUSAO:
        valor_principal = getattr(principal, campo, None)
        valor_duplicado = getattr(duplicado, campo, None)
        principal_vazio = _valor_vazio(valor_principal)
        duplicado_vazio = _valor_vazio(valor_duplicado)
        conflito = not principal_vazio and not duplicado_vazio and not _valores_iguais(valor_principal, valor_duplicado)

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
            "final": float(getattr(principal, campo, None) or 0) + float(getattr(duplicado, campo, None) or 0),
        }
        for campo in ESTOQUE_SOMAR_CAMPOS
    }

    return {
        "principal": _produto_resumo(principal),
        "duplicado": _produto_resumo(duplicado),
        "campos": campos,
        "estoque_somado": estoque_preview,
        "referencias_duplicado": _contar_referencias(db, duplicado.id),
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


def _copiar_campos_fiscais(primary: ProdutoConfigFiscal, duplicate: ProdutoConfigFiscal) -> None:
    for column in ProdutoConfigFiscal.__table__.columns:
        name = column.name
        if name in {"id", "produto_id", "tenant_id", "created_at", "updated_at"}:
            continue
        if _valor_vazio(getattr(primary, name, None)) and not _valor_vazio(getattr(duplicate, name, None)):
            setattr(primary, name, getattr(duplicate, name))


def _mesclar_config_fiscal(db: Session, principal_id: int, duplicado_id: int, tenant_id: Any) -> int:
    primary = (
        db.query(ProdutoConfigFiscal)
        .filter(ProdutoConfigFiscal.tenant_id == tenant_id, ProdutoConfigFiscal.produto_id == principal_id)
        .first()
    )
    duplicate = (
        db.query(ProdutoConfigFiscal)
        .filter(ProdutoConfigFiscal.tenant_id == tenant_id, ProdutoConfigFiscal.produto_id == duplicado_id)
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


def _mesclar_fornecedores(db: Session, principal_id: int, duplicado_id: int, tenant_id: Any) -> int:
    transferidos = 0
    duplicados = (
        db.query(ProdutoFornecedor)
        .filter(ProdutoFornecedor.tenant_id == tenant_id, ProdutoFornecedor.produto_id == duplicado_id)
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
            for campo in ("codigo_fornecedor", "preco_custo", "prazo_entrega", "estoque_fornecedor"):
                if _valor_vazio(getattr(existente, campo, None)) and not _valor_vazio(getattr(vinculo, campo, None)):
                    setattr(existente, campo, getattr(vinculo, campo))
            existente.e_principal = bool(existente.e_principal or vinculo.e_principal)
            existente.ativo = bool(existente.ativo or vinculo.ativo)
            db.delete(vinculo)
        else:
            vinculo.produto_id = principal_id
        transferidos += 1
    return transferidos


def _mesclar_listas_preco(db: Session, principal_id: int, duplicado_id: int, tenant_id: Any) -> int:
    transferidos = 0
    duplicados = (
        db.query(ProdutoListaPreco)
        .filter(ProdutoListaPreco.tenant_id == tenant_id, ProdutoListaPreco.produto_id == duplicado_id)
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


def _mesclar_bling_sync(db: Session, principal_id: int, duplicado_id: int, tenant_id: Any) -> int:
    primary = (
        db.query(ProdutoBlingSync)
        .filter(ProdutoBlingSync.tenant_id == tenant_id, ProdutoBlingSync.produto_id == principal_id)
        .first()
    )
    duplicate = (
        db.query(ProdutoBlingSync)
        .filter(ProdutoBlingSync.tenant_id == tenant_id, ProdutoBlingSync.produto_id == duplicado_id)
        .first()
    )
    if not duplicate:
        return 0
    if primary:
        db.query(ProdutoBlingSyncQueue).filter(ProdutoBlingSyncQueue.sync_id == duplicate.id).update(
            {ProdutoBlingSyncQueue.sync_id: primary.id},
            synchronize_session=False,
        )
        for column in ProdutoBlingSync.__table__.columns:
            name = column.name
            if name in {"id", "produto_id", "tenant_id", "created_at", "updated_at"}:
                continue
            if _valor_vazio(getattr(primary, name, None)) and not _valor_vazio(getattr(duplicate, name, None)):
                setattr(primary, name, getattr(duplicate, name))
        db.delete(duplicate)
    else:
        duplicate.produto_id = principal_id
    return 1


def _mesclar_componentes_kit(db: Session, principal_id: int, duplicado_id: int, tenant_id: Any) -> int:
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
        novo_kit_id = principal_id if componente.kit_id == duplicado_id else componente.kit_id
        novo_componente_id = (
            principal_id if componente.produto_componente_id == duplicado_id else componente.produto_componente_id
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
            existente.quantidade = float(existente.quantidade or 0) + float(componente.quantidade or 0)
            existente.opcional = bool(existente.opcional and componente.opcional)
            db.delete(componente)
        else:
            componente.kit_id = novo_kit_id
            componente.produto_componente_id = novo_componente_id
        alterados += 1
    return alterados


def _mesclar_vinculos_granel(db: Session, principal_id: int, duplicado_id: int, tenant_id: Any) -> int:
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
        nova_origem = principal_id if vinculo.produto_origem_id == duplicado_id else vinculo.produto_origem_id
        novo_granel = principal_id if vinculo.produto_granel_id == duplicado_id else vinculo.produto_granel_id

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
) -> list[dict[str, Any]]:
    transferencias = []
    for fk in _consultar_fks_produto(db):
        tabela = fk["table_name"]
        campo = fk["column_name"]
        if tabela in TABELAS_FK_ESPECIAIS:
            continue
        if tabela == "produtos" and campo == "produto_predecessor_id":
            continue
        if tabela == "produtos" and campo == "produto_pai_id":
            sql = text(
                f"update {_identificador(tabela)} set {_identificador(campo)} = :principal_id "
                f"where {_identificador(campo)} = :duplicado_id and id != :duplicado_id"
            )
        else:
            sql = text(
                f"update {_identificador(tabela)} set {_identificador(campo)} = :principal_id "
                f"where {_identificador(campo)} = :duplicado_id"
            )
        result = db.execute(sql, {"principal_id": principal_id, "duplicado_id": duplicado_id})
        if result.rowcount:
            transferencias.append({"tabela": tabela, "campo": campo, "total": int(result.rowcount)})
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
) -> dict[str, Any]:
    principal, duplicado = _obter_produtos(db, tenant_id, principal_id, duplicado_id)
    agora = datetime.utcnow()
    decisoes_campos = decisoes_campos or {}
    codigo_original_duplicado = duplicado.codigo

    campos_aplicados = []
    for campo, label in CAMPOS_CADASTRAIS_FUSAO:
        if campo in ESTOQUE_SOMAR_CAMPOS:
            continue
        valor_principal = getattr(principal, campo, None)
        valor_duplicado = getattr(duplicado, campo, None)
        origem = decisoes_campos.get(campo)
        if origem not in {"principal", "duplicado"}:
            origem = "duplicado" if _valor_vazio(valor_principal) and not _valor_vazio(valor_duplicado) else "principal"

        if origem == "duplicado" and not _valor_vazio(valor_duplicado):
            setattr(principal, campo, valor_duplicado)
            campos_aplicados.append({"campo": campo, "label": label, "origem": "duplicado"})

    for campo in ESTOQUE_SOMAR_CAMPOS:
        setattr(principal, campo, float(getattr(principal, campo, None) or 0) + float(getattr(duplicado, campo, None) or 0))

    transferidos_especiais = {
        "produto_fornecedores": _mesclar_fornecedores(db, principal.id, duplicado.id, tenant_id),
        "produto_listas_preco": _mesclar_listas_preco(db, principal.id, duplicado.id, tenant_id),
        "produto_bling_sync": _mesclar_bling_sync(db, principal.id, duplicado.id, tenant_id),
        "produto_config_fiscal": _mesclar_config_fiscal(db, principal.id, duplicado.id, tenant_id),
        "produto_kit_componentes": _mesclar_componentes_kit(db, principal.id, duplicado.id, tenant_id),
        "produto_granel_vinculos": _mesclar_vinculos_granel(db, principal.id, duplicado.id, tenant_id),
    }

    db.execute(
        text(
            """
            delete from duplicatas_ignoradas
            where produto_id_1 in (:principal_id, :duplicado_id)
               or produto_id_2 in (:principal_id, :duplicado_id)
            """
        ),
        {"principal_id": principal.id, "duplicado_id": duplicado.id},
    )

    transferidos_genericos = _transferir_referencias_genericas(
        db,
        principal_id=principal.id,
        duplicado_id=duplicado.id,
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

    nota_auditoria = (
        f"\n[{agora.isoformat()}] Fusao de produto: produto #{duplicado.id} "
        f"({codigo_original_duplicado}) fundido no produto #{principal.id} por usuario #{user_id}."
    )
    if observacao:
        nota_auditoria += f" Observacao: {observacao.strip()}"
    principal.informacoes_adicionais_nf = (principal.informacoes_adicionais_nf or "") + nota_auditoria
    duplicado.informacoes_adicionais_nf = (duplicado.informacoes_adicionais_nf or "") + nota_auditoria
    principal.updated_at = agora
    duplicado.updated_at = agora

    db.flush()
    db.commit()
    db.refresh(principal)
    db.refresh(duplicado)

    return {
        "success": True,
        "principal": _produto_resumo(principal),
        "duplicado_inativado": _produto_resumo(duplicado),
        "campos_aplicados": campos_aplicados,
        "estoque_somado": {campo: getattr(principal, campo, None) for campo in ESTOQUE_SOMAR_CAMPOS},
        "transferidos_especiais": transferidos_especiais,
        "transferidos_genericos": transferidos_genericos,
    }
