from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
import json
import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import AppAccessProfile, Cliente, PessoaMergeLog
from app.produtos_models import ProdutoFornecedor
from app.services.app_access_profile_service import sync_cliente_app_access_profiles

logger = logging.getLogger(__name__)


CAMPOS_CADASTRAIS_PESSOA: list[tuple[str, str]] = [
    ("tipo_cadastro", "Tipo de cadastro"),
    ("tipo_pessoa", "Tipo de pessoa"),
    ("fornecedor_grupo_id", "Grupo de fornecedor"),
    ("nome", "Nome"),
    ("data_nascimento", "Data de nascimento"),
    ("cpf", "CPF"),
    ("cnpj", "CNPJ"),
    ("inscricao_estadual", "Inscricao estadual"),
    ("razao_social", "Razao social"),
    ("nome_fantasia", "Nome fantasia"),
    ("responsavel", "Responsavel"),
    ("crmv", "CRMV"),
    ("email", "Email"),
    ("telefone", "Telefone"),
    ("celular", "Celular"),
    ("cep", "CEP"),
    ("endereco", "Endereco"),
    ("numero", "Numero"),
    ("complemento", "Complemento"),
    ("bairro", "Bairro"),
    ("cidade", "Cidade"),
    ("estado", "Estado"),
    ("endereco_entrega", "Endereco de entrega"),
    ("endereco_entrega_2", "Segundo endereco de entrega"),
    ("enderecos_adicionais", "Enderecos adicionais"),
    ("parceiro_ativo", "Parceiro ativo"),
    ("parceiro_desde", "Parceiro desde"),
    ("parceiro_observacoes", "Observacoes de parceiro"),
    ("data_fechamento_comissao", "Dia de fechamento de comissao"),
    ("is_entregador", "Entregador"),
    ("entregador_padrao", "Entregador padrao"),
    ("is_terceirizado", "Terceirizado"),
    ("recebe_repasse", "Recebe repasse"),
    ("gera_conta_pagar", "Gera conta a pagar"),
    ("tipo_vinculo_entrega", "Tipo de vinculo de entrega"),
    ("valor_padrao_entrega", "Valor padrao de entrega"),
    ("valor_por_km", "Valor por km"),
    ("recebe_comissao_entrega", "Recebe comissao de entrega"),
    ("entregador_ativo", "Entregador ativo"),
    ("controla_rh", "Controla RH"),
    ("gera_conta_pagar_custo_entrega", "Gera custo de entrega"),
    ("media_entregas_configurada", "Media de entregas configurada"),
    ("media_entregas_real", "Media real de entregas"),
    ("custo_rh_ajustado", "Custo RH ajustado"),
    ("modelo_custo_entrega", "Modelo de custo de entrega"),
    ("taxa_fixa_entrega", "Taxa fixa de entrega"),
    ("valor_por_km_entrega", "Valor por km entrega"),
    ("moto_propria", "Moto propria"),
    ("tipo_acerto_entrega", "Tipo de acerto de entrega"),
    ("dia_semana_acerto", "Dia da semana de acerto"),
    ("dia_mes_acerto", "Dia do mes de acerto"),
    ("data_ultimo_acerto", "Data do ultimo acerto"),
    ("controla_dre", "Controla DRE"),
    ("observacoes", "Observacoes"),
]

TABELAS_FK_ESPECIAIS = {
    "app_access_profiles",
    "pessoa_merge_logs",
    "produto_fornecedores",
}

CAMPOS_BOOLEANOS_UNIAO = {
    "parceiro_ativo",
    "is_entregador",
    "entregador_padrao",
    "is_terceirizado",
    "recebe_repasse",
    "gera_conta_pagar",
    "recebe_comissao_entrega",
    "entregador_ativo",
    "controla_rh",
    "gera_conta_pagar_custo_entrega",
    "controla_dre",
}

REFERENCIAS_SEM_FK = [
    ("movimentacoes_caixa", "fornecedor_id"),
    ("pedidos_compra", "fornecedor_id"),
    ("notas_entrada", "fornecedor_id"),
    ("compras_pendencias_fornecedor", "fornecedor_id"),
    ("fornecedor_grupos", "fornecedor_principal_id"),
    ("pedidos", "cliente_id"),
    ("pedido_checkout_read", "cliente_id"),
]


def _valor_vazio(valor: Any) -> bool:
    if valor is None:
        return True
    if isinstance(valor, str):
        return not valor.strip()
    if isinstance(valor, (list, dict, tuple, set)):
        return len(valor) == 0
    return False


def _valores_iguais(valor_a: Any, valor_b: Any) -> bool:
    if isinstance(valor_a, (date, datetime)) or isinstance(valor_b, (date, datetime)):
        return str(valor_a or "") == str(valor_b or "")
    if isinstance(valor_a, Decimal) or isinstance(valor_b, Decimal):
        return Decimal(str(valor_a or 0)) == Decimal(str(valor_b or 0))
    return valor_a == valor_b


def _valor_serializavel(valor: Any) -> Any:
    if isinstance(valor, (datetime, date)):
        return valor.isoformat()
    if isinstance(valor, Decimal):
        return float(valor)
    return valor


def _identificador(nome: str) -> str:
    return '"' + nome.replace('"', '""') + '"'


def _tenant_where_clause(db: Session, table_name: str, params: dict[str, Any]) -> str:
    if not _table_has_column(db, table_name, "tenant_id"):
        return ""

    params["tenant_id_text"] = str(params.pop("tenant_id"))
    return f" and {_identificador('tenant_id')}::text = :tenant_id_text"


def _pessoa_resumo(pessoa: Cliente) -> dict[str, Any]:
    return {
        "id": pessoa.id,
        "codigo": pessoa.codigo,
        "nome": pessoa.nome,
        "tipo_cadastro": pessoa.tipo_cadastro,
        "tipo_pessoa": pessoa.tipo_pessoa,
        "documento": pessoa.cnpj or pessoa.cpf,
        "email": pessoa.email,
        "telefone": pessoa.celular or pessoa.telefone,
        "ativo": pessoa.ativo,
        "credito": float(pessoa.credito or 0),
        "auth_user_id": getattr(pessoa, "auth_user_id", None),
        "merged_into_id": getattr(pessoa, "merged_into_id", None),
    }


def _obter_pessoas(
    db: Session, tenant_id: Any, principal_id: int, duplicado_id: int
) -> tuple[Cliente, Cliente]:
    if principal_id == duplicado_id:
        raise ValueError("Selecione duas pessoas diferentes para fundir.")

    pessoas = (
        db.query(Cliente)
        .filter(
            Cliente.tenant_id == tenant_id,
            Cliente.id.in_([principal_id, duplicado_id]),
        )
        .with_for_update()
        .all()
    )
    por_id = {int(pessoa.id): pessoa for pessoa in pessoas}
    principal = por_id.get(int(principal_id))
    duplicado = por_id.get(int(duplicado_id))
    if not principal or not duplicado:
        raise ValueError("Pessoa principal ou duplicada nao encontrada neste tenant.")
    if principal.ativo is False:
        raise ValueError("O cadastro principal precisa estar ativo.")
    if duplicado.ativo is False or getattr(duplicado, "merged_into_id", None):
        raise ValueError("O cadastro duplicado ja foi inativado ou fundido.")
    return principal, duplicado


def _table_has_column(db: Session, table_name: str, column_name: str) -> bool:
    return bool(
        db.execute(
            text(
                """
                select 1
                from information_schema.columns
                where table_schema = 'public'
                  and table_name = :table_name
                  and column_name = :column_name
                limit 1
                """
            ),
            {"table_name": table_name, "column_name": column_name},
        ).scalar()
    )


def _consultar_referencias_cliente(db: Session) -> list[dict[str, str]]:
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
              and ccu.table_name = 'clientes'
              and ccu.column_name = 'id'
            order by tc.table_name, kcu.column_name
            """
        )
    ).mappings()
    referencias = [
        {"table_name": row["table_name"], "column_name": row["column_name"]}
        for row in rows
    ]
    existentes = {(ref["table_name"], ref["column_name"]) for ref in referencias}
    for table_name, column_name in REFERENCIAS_SEM_FK:
        if (table_name, column_name) not in existentes and _table_has_column(
            db, table_name, column_name
        ):
            referencias.append({"table_name": table_name, "column_name": column_name})
    return referencias


def _contar_referencias(
    db: Session, pessoa_id: int, tenant_id: Any
) -> list[dict[str, Any]]:
    referencias = []
    for fk in _consultar_referencias_cliente(db):
        table_name = fk["table_name"]
        column_name = fk["column_name"]
        if table_name == "clientes" and column_name == "id":
            continue

        params = {"pessoa_id": pessoa_id}
        if _table_has_column(db, table_name, "tenant_id"):
            params["tenant_id"] = tenant_id
        where_tenant = _tenant_where_clause(db, table_name, params)

        sql = text(
            f"select count(*) from {_identificador(table_name)} "
            f"where {_identificador(column_name)} = :pessoa_id{where_tenant}"
        )
        try:
            total = int(db.execute(sql, params).scalar() or 0)
        except Exception as exc:
            db.rollback()
            logger.warning(
                "Ignorando contagem de referencia da fusao de pessoas em %s.%s: %s",
                table_name,
                column_name,
                exc,
            )
            continue
        if total:
            referencias.append(
                {"tabela": table_name, "campo": column_name, "total": total}
            )
    return referencias


def montar_preview_fusao_pessoas(
    db: Session,
    *,
    tenant_id: Any,
    principal_id: int,
    duplicado_id: int,
) -> dict[str, Any]:
    principal, duplicado = _obter_pessoas(db, tenant_id, principal_id, duplicado_id)
    campos = []

    for campo, label in CAMPOS_CADASTRAIS_PESSOA:
        valor_principal = getattr(principal, campo, None)
        valor_duplicado = getattr(duplicado, campo, None)
        principal_vazio = _valor_vazio(valor_principal)
        duplicado_vazio = _valor_vazio(valor_duplicado)
        conflito = (
            not principal_vazio
            and not duplicado_vazio
            and not _valores_iguais(valor_principal, valor_duplicado)
        )
        origem_padrao = (
            "duplicado" if principal_vazio and not duplicado_vazio else "principal"
        )

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

    credito_preview = {
        "principal": float(principal.credito or 0),
        "duplicado": float(duplicado.credito or 0),
        "final": float(principal.credito or 0) + float(duplicado.credito or 0),
    }
    contas_app = {
        int(conta_id)
        for conta_id in (
            getattr(principal, "auth_user_id", None),
            getattr(duplicado, "auth_user_id", None),
        )
        if conta_id
    }
    bloqueios = []
    if len(contas_app) > 1:
        bloqueios.append(
            "Os cadastros estao ligados a contas de aplicativo diferentes. "
            "Revise os acessos antes de fundir."
        )

    return {
        "principal": _pessoa_resumo(principal),
        "duplicado": _pessoa_resumo(duplicado),
        "campos": campos,
        "credito_somado": credito_preview,
        "referencias_duplicado": _contar_referencias(db, duplicado.id, tenant_id),
        "bloqueios": bloqueios,
    }


def _snapshot_pessoa(pessoa: Cliente) -> dict[str, Any]:
    campos = {
        campo: _valor_serializavel(getattr(pessoa, campo, None))
        for campo, _label in CAMPOS_CADASTRAIS_PESSOA
    }
    campos.update(
        {
            "id": pessoa.id,
            "codigo": pessoa.codigo,
            "auth_user_id": getattr(pessoa, "auth_user_id", None),
            "merged_into_id": getattr(pessoa, "merged_into_id", None),
            "ativo": pessoa.ativo,
            "credito": float(pessoa.credito or 0),
        }
    )
    return campos


def _snapshot_perfis_app(
    db: Session, *, tenant_id: Any, pessoa_ids: list[int]
) -> dict[str, list[dict[str, Any]]]:
    resultado = {str(pessoa_id): [] for pessoa_id in pessoa_ids}
    grants = (
        db.query(AppAccessProfile)
        .filter(
            AppAccessProfile.tenant_id == tenant_id,
            AppAccessProfile.cliente_id.in_(pessoa_ids),
        )
        .all()
    )
    for grant in grants:
        resultado.setdefault(str(grant.cliente_id), []).append(
            {
                "profile_type": grant.profile_type,
                "user_id": grant.user_id,
                "is_active": grant.is_active,
                "granted_by_user_id": grant.granted_by_user_id,
            }
        )
    return resultado


def _lista_json(valor: Any) -> list[Any]:
    if isinstance(valor, str):
        try:
            valor = json.loads(valor)
        except Exception:
            return []
    return list(valor) if isinstance(valor, list) else []


def _unir_listas_json(valor_a: Any, valor_b: Any) -> list[Any] | None:
    resultado: list[Any] = []
    vistos: set[str] = set()
    for item in [*_lista_json(valor_a), *_lista_json(valor_b)]:
        chave = json.dumps(item, sort_keys=True, ensure_ascii=False, default=str)
        if chave in vistos:
            continue
        vistos.add(chave)
        resultado.append(item)
    return resultado or None


def _unir_textos(valor_a: Any, valor_b: Any) -> str | None:
    partes = []
    for valor in (valor_a, valor_b):
        texto = str(valor or "").strip()
        if texto and texto not in partes:
            partes.append(texto)
    return "\n\n".join(partes) or None


def _perfis_inerentes(pessoa: Cliente) -> set[str]:
    perfis: set[str] = set()
    tipo = str(getattr(pessoa, "tipo_cadastro", "") or "").strip().casefold()
    if tipo in {"cliente", "funcionario", "veterinario"}:
        perfis.add(tipo)
    if bool(getattr(pessoa, "is_entregador", False)):
        perfis.add("entregador")
    return perfis


def _mesclar_perfis_app(
    db: Session,
    *,
    principal: Cliente,
    duplicado: Cliente,
    tenant_id: Any,
    user_id: int,
) -> list[str]:
    grants = (
        db.query(AppAccessProfile)
        .filter(
            AppAccessProfile.tenant_id == tenant_id,
            AppAccessProfile.cliente_id.in_([principal.id, duplicado.id]),
            AppAccessProfile.is_active.is_(True),
        )
        .all()
    )
    perfis = _perfis_inerentes(principal) | _perfis_inerentes(duplicado)
    perfis.update(grant.profile_type for grant in grants)

    # Remove os grants do duplicado antes de sincronizar para evitar colisao da
    # chave unica (tenant, pessoa, perfil).
    for grant in grants:
        if int(grant.cliente_id) == int(duplicado.id):
            db.delete(grant)
    db.flush()

    return sync_cliente_app_access_profiles(
        db,
        tenant_id=tenant_id,
        cliente=principal,
        profile_types=perfis,
        granted_by_user_id=user_id,
        linked_user_id=getattr(principal, "auth_user_id", None),
    )


def _mesclar_produto_fornecedores(
    db: Session, principal_id: int, duplicado_id: int, tenant_id: Any
) -> int:
    transferidos = 0
    vinculos = (
        db.query(ProdutoFornecedor)
        .filter(
            ProdutoFornecedor.tenant_id == tenant_id,
            ProdutoFornecedor.fornecedor_id == duplicado_id,
        )
        .all()
    )
    for vinculo in vinculos:
        existente = (
            db.query(ProdutoFornecedor)
            .filter(
                ProdutoFornecedor.tenant_id == tenant_id,
                ProdutoFornecedor.produto_id == vinculo.produto_id,
                ProdutoFornecedor.fornecedor_id == principal_id,
                ProdutoFornecedor.id != vinculo.id,
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
            vinculo.fornecedor_id = principal_id
        transferidos += 1
    return transferidos


def _transferir_referencias_genericas(
    db: Session,
    *,
    principal_id: int,
    duplicado_id: int,
    tenant_id: Any,
) -> list[dict[str, Any]]:
    transferencias = []
    for fk in _consultar_referencias_cliente(db):
        tabela = fk["table_name"]
        campo = fk["column_name"]
        if tabela in TABELAS_FK_ESPECIAIS:
            continue

        params = {"principal_id": principal_id, "duplicado_id": duplicado_id}
        if _table_has_column(db, tabela, "tenant_id"):
            params["tenant_id"] = tenant_id
        where_tenant = _tenant_where_clause(db, tabela, params)

        sql = text(
            f"update {_identificador(tabela)} set {_identificador(campo)} = :principal_id "
            f"where {_identificador(campo)} = :duplicado_id{where_tenant}"
        )
        result = db.execute(sql, params)
        if result.rowcount:
            transferencias.append(
                {"tabela": tabela, "campo": campo, "total": int(result.rowcount)}
            )
    return transferencias


def transferir_referencias_pessoa(
    db: Session,
    *,
    tenant_id: Any,
    principal_id: int,
    duplicado_id: int,
) -> dict[str, Any]:
    """Transfere todas as referencias de uma pessoa duplicada para a principal sem commitar."""
    return {
        "transferidos_especiais": {
            "produto_fornecedores": _mesclar_produto_fornecedores(
                db,
                principal_id,
                duplicado_id,
                tenant_id,
            ),
        },
        "transferidos_genericos": _transferir_referencias_genericas(
            db,
            principal_id=principal_id,
            duplicado_id=duplicado_id,
            tenant_id=tenant_id,
        ),
    }


def executar_fusao_pessoas(
    db: Session,
    *,
    tenant_id: Any,
    principal_id: int,
    duplicado_id: int,
    decisoes_campos: dict[str, str] | None,
    user_id: int,
    observacao: str | None = None,
    modo: str = "manual",
    motivo: str | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    principal, duplicado = _obter_pessoas(db, tenant_id, principal_id, duplicado_id)
    agora = datetime.utcnow()
    decisoes_campos = decisoes_campos or {}
    snapshot_antes = {
        "principal": _snapshot_pessoa(principal),
        "duplicado": _snapshot_pessoa(duplicado),
        "perfis_app": _snapshot_perfis_app(
            db,
            tenant_id=tenant_id,
            pessoa_ids=[principal.id, duplicado.id],
        ),
    }

    principal_auth_user_id = getattr(principal, "auth_user_id", None)
    duplicado_auth_user_id = getattr(duplicado, "auth_user_id", None)
    if (
        principal_auth_user_id
        and duplicado_auth_user_id
        and int(principal_auth_user_id) != int(duplicado_auth_user_id)
    ):
        raise ValueError(
            "A fusao foi bloqueada porque os cadastros estao ligados a contas "
            "de aplicativo diferentes. Revise os acessos antes de continuar."
        )

    # Libera primeiro o vinculo do duplicado para respeitar o indice unico de
    # conta ativa mesmo quando a conta precisa migrar para o principal.
    if duplicado_auth_user_id:
        duplicado.auth_user_id = None
        db.flush()
    if not principal_auth_user_id and duplicado_auth_user_id:
        principal.auth_user_id = duplicado_auth_user_id

    campos_aplicados = []
    for campo, label in CAMPOS_CADASTRAIS_PESSOA:
        valor_principal = getattr(principal, campo, None)
        valor_duplicado = getattr(duplicado, campo, None)

        if campo in CAMPOS_BOOLEANOS_UNIAO:
            valor_final = bool(valor_principal or valor_duplicado)
            if valor_final != bool(valor_principal):
                setattr(principal, campo, valor_final)
                campos_aplicados.append(
                    {"campo": campo, "label": label, "origem": "uniao"}
                )
            continue

        if campo == "enderecos_adicionais":
            valor_final = _unir_listas_json(valor_principal, valor_duplicado)
            if valor_final != _lista_json(valor_principal):
                setattr(principal, campo, valor_final)
                campos_aplicados.append(
                    {"campo": campo, "label": label, "origem": "uniao"}
                )
            continue

        if campo in {"observacoes", "parceiro_observacoes"}:
            valor_final = _unir_textos(valor_principal, valor_duplicado)
            if valor_final != (valor_principal or None):
                setattr(principal, campo, valor_final)
                campos_aplicados.append(
                    {"campo": campo, "label": label, "origem": "uniao"}
                )
            continue

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

    perfis_app = _mesclar_perfis_app(
        db,
        principal=principal,
        duplicado=duplicado,
        tenant_id=tenant_id,
        user_id=user_id,
    )

    principal.credito = Decimal(str(principal.credito or 0)) + Decimal(
        str(duplicado.credito or 0)
    )
    duplicado.credito = Decimal("0")

    transferencias = transferir_referencias_pessoa(
        db,
        tenant_id=tenant_id,
        principal_id=principal.id,
        duplicado_id=duplicado.id,
    )

    nota = (
        f"\n[{agora.isoformat()}] Fusao de pessoa: cadastro #{duplicado.id} "
        f"({duplicado.codigo or '-'}) fundido no cadastro #{principal.id} "
        f"por usuario #{user_id}."
    )
    if observacao:
        nota += f" Observacao: {observacao.strip()}"

    principal.observacoes = _unir_textos(principal.observacoes, nota)
    duplicado.observacoes = (duplicado.observacoes or "") + nota
    duplicado.ativo = False
    duplicado.merged_into_id = principal.id
    principal.updated_at = agora
    duplicado.updated_at = agora

    resumo_transferencias = {
        "campos_aplicados": campos_aplicados,
        "credito_somado": float(principal.credito or 0),
        "perfis_app": perfis_app,
        "transferidos_especiais": transferencias["transferidos_especiais"],
        "transferidos_genericos": transferencias["transferidos_genericos"],
    }
    merge_log = PessoaMergeLog(
        tenant_id=tenant_id,
        principal_id=principal.id,
        duplicado_id=duplicado.id,
        actor_user_id=user_id,
        modo=(modo or "manual")[:30],
        motivo=(motivo or None),
        status="concluida",
        snapshot_antes=snapshot_antes,
        resumo_transferencias=resumo_transferencias,
        observacao=(observacao or None),
    )
    db.add(merge_log)
    db.flush()
    if commit:
        db.commit()
        db.refresh(principal)
        db.refresh(duplicado)

    return {
        "success": True,
        "principal": _pessoa_resumo(principal),
        "duplicado_inativado": _pessoa_resumo(duplicado),
        "merge_log_id": merge_log.id,
        "campos_aplicados": campos_aplicados,
        "credito_somado": float(principal.credito or 0),
        "perfis_app": perfis_app,
        "transferidos_especiais": transferencias["transferidos_especiais"],
        "transferidos_genericos": transferencias["transferidos_genericos"],
    }
