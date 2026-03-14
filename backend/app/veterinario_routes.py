"""
Rotas do módulo veterinário.
Cobre: agendamentos, consultas, vacinas, exames, prescrições,
internações, peso, fotos, catálogos e perfil comportamental.
"""
import hashlib
import json
import os
import re
import secrets
import csv
from decimal import Decimal
from datetime import date, datetime, timedelta
from io import StringIO
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, inspect, or_
from sqlalchemy.orm import Session, joinedload

from .auth.dependencies import get_current_user_and_tenant
from .db import get_session
from .dre_plano_contas_models import DRECategoria, DRESubcategoria, NaturezaDRE
from .financeiro_models import CategoriaFinanceira, ContaReceber
from .ia.aba6_models import Conversa, MensagemChat
from .models import Cliente, Pet, Tenant, User
from .pdf_veterinario import gerar_pdf_prontuario, gerar_pdf_receita
from .produtos_models import EstoqueMovimentacao, Produto
from .veterinario_models import (
    AgendamentoVet,
    CatalogoProcedimento,
    ConsultaVet,
    ExameVet,
    FotoClinica,
    InternacaoVet,
    EvolucaoInternacao,
    ItemPrescricao,
    MedicamentoCatalogo,
    PerfilComportamental,
    PesoRegistro,
    PrescricaoVet,
    ProcedimentoConsulta,
    ProtocoloVacina,
    VacinaRegistro,
    VetPartnerLink,
)

router = APIRouter(prefix="/vet", tags=["Veterinário"])
UPLOADS_DIR = Path(__file__).resolve().parents[2] / "uploads" / "veterinario" / "exames"


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def _get_tenant(current: tuple) -> tuple:
    """Extrai user e tenant_id do tuple retornado pelo Depends."""
    user, tenant_id = current
    return user, tenant_id


def _get_partner_tenant_ids(db: Session, tenant_id) -> list:
    """Retorna lista de empresa_tenant_ids onde este vet é parceiro ativo."""
    links = db.query(VetPartnerLink).filter(
        VetPartnerLink.vet_tenant_id == str(tenant_id),
        VetPartnerLink.ativo == True,
    ).all()
    return [link.empresa_tenant_id for link in links]


def _all_accessible_tenant_ids(db: Session, tenant_id) -> list:
    """Retorna tenant_id atual + todos os tenants das empresas parceiras vinculadas."""
    return [str(tenant_id)] + _get_partner_tenant_ids(db, tenant_id)


def _as_float(value) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalizar_insumos(insumos: Optional[list]) -> list[dict]:
    normalizados = []
    if not isinstance(insumos, list):
        return normalizados

    for item in insumos:
        if not isinstance(item, dict):
            continue
        produto_id = item.get("produto_id")
        quantidade = _as_float(item.get("quantidade"))
        if not produto_id or not quantidade or quantidade <= 0:
            continue
        normalizados.append({
            "produto_id": int(produto_id),
            "quantidade": quantidade,
            "nome": (item.get("nome") or "").strip() or None,
            "unidade": (item.get("unidade") or "").strip() or None,
            "observacoes": (item.get("observacoes") or "").strip() or None,
            "baixar_estoque": bool(item.get("baixar_estoque", True)),
            "custo_unitario": _as_float(item.get("custo_unitario")) or 0.0,
            "custo_total": _as_float(item.get("custo_total")) or 0.0,
        })
    return normalizados


def _round_money(value: Optional[float]) -> float:
    return round(_as_float(value) or 0.0, 2)


def _buscar_produtos_por_ids(db: Session, tenant_id, produto_ids: list[int]) -> dict[int, Produto]:
    if not produto_ids:
        return {}

    produtos = db.query(Produto).filter(
        Produto.tenant_id == str(tenant_id),
        Produto.id.in_(produto_ids),
    ).all()
    return {produto.id: produto for produto in produtos}


def _enriquecer_insumos_com_custos(db: Session, tenant_id, insumos: Optional[list]) -> list[dict]:
    normalizados = _normalizar_insumos(insumos)
    produtos = _buscar_produtos_por_ids(db, tenant_id, [item["produto_id"] for item in normalizados])

    enriquecidos = []
    for item in normalizados:
        produto = produtos.get(item["produto_id"])
        if not produto:
            raise HTTPException(status_code=404, detail=f"Produto {item['produto_id']} não encontrado para o procedimento")

        custo_unitario = _round_money(produto.preco_custo)
        enriquecidos.append({
            **item,
            "nome": item.get("nome") or produto.nome,
            "unidade": item.get("unidade") or produto.unidade,
            "custo_unitario": custo_unitario,
            "custo_total": _round_money(custo_unitario * item["quantidade"]),
        })

    return enriquecidos


def _resumo_financeiro_insumos(insumos: Optional[list]) -> dict:
    itens = _normalizar_insumos(insumos)
    custo_total = _round_money(sum((_as_float(item.get("custo_total")) or 0.0) for item in itens))
    return {
        "insumos": itens,
        "custo_total": custo_total,
    }


def _obter_regra_financeira_veterinaria(db: Session, tenant_id) -> dict:
    link = db.query(VetPartnerLink).filter(
        VetPartnerLink.vet_tenant_id == str(tenant_id),
        VetPartnerLink.ativo == True,
    ).order_by(VetPartnerLink.id.desc()).first()

    if link and link.tipo_relacao == "parceiro":
        return {
            "modo_operacional": "parceiro",
            "comissao_empresa_pct": _round_money(link.comissao_empresa_pct),
            "empresa_tenant_id": str(link.empresa_tenant_id),
            "tenant_recebedor_id": str(link.vet_tenant_id),
        }

    return {
        "modo_operacional": "funcionario",
        "comissao_empresa_pct": 0.0,
        "empresa_tenant_id": str(tenant_id),
        "tenant_recebedor_id": str(tenant_id),
    }


def _resumo_financeiro_procedimento(valor, insumos: Optional[list], regra_financeira: Optional[dict] = None) -> dict:
    valor_cobrado = _round_money(valor)
    resumo_insumos = _resumo_financeiro_insumos(insumos)
    custo_total = resumo_insumos["custo_total"]
    margem_valor = _round_money(valor_cobrado - custo_total)
    margem_percentual = round((margem_valor / valor_cobrado) * 100, 2) if valor_cobrado > 0 else 0.0
    regra = regra_financeira or {
        "modo_operacional": "funcionario",
        "comissao_empresa_pct": 0.0,
        "empresa_tenant_id": None,
        "tenant_recebedor_id": None,
    }
    repasse_empresa_valor = 0.0
    receita_tenant_valor = valor_cobrado
    entrada_empresa_valor = valor_cobrado
    if regra["modo_operacional"] == "parceiro":
        repasse_empresa_valor = _round_money(valor_cobrado * ((_as_float(regra.get("comissao_empresa_pct")) or 0.0) / 100))
        receita_tenant_valor = _round_money(valor_cobrado - repasse_empresa_valor)
        entrada_empresa_valor = repasse_empresa_valor

    return {
        "valor_cobrado": valor_cobrado,
        "custo_total": custo_total,
        "margem_valor": margem_valor,
        "margem_percentual": margem_percentual,
        "modo_operacional": regra["modo_operacional"],
        "comissao_empresa_pct": _round_money(regra.get("comissao_empresa_pct")),
        "repasse_empresa_valor": repasse_empresa_valor,
        "receita_tenant_valor": receita_tenant_valor,
        "entrada_empresa_valor": entrada_empresa_valor,
        "insumos": resumo_insumos["insumos"],
    }


def _obter_dre_subcategoria_receita_padrao(db: Session, tenant_id) -> int:
    subcategoria = db.query(DRESubcategoria).join(
        DRECategoria, DRECategoria.id == DRESubcategoria.categoria_id
    ).filter(
        DRESubcategoria.tenant_id == str(tenant_id),
        DRECategoria.tenant_id == str(tenant_id),
        DRESubcategoria.ativo == True,
        DRECategoria.ativo == True,
        DRECategoria.natureza == NaturezaDRE.RECEITA,
    ).order_by(DRECategoria.ordem.asc(), DRESubcategoria.id.asc()).first()
    return subcategoria.id if subcategoria else 1


def _obter_ou_criar_categoria_financeira_vet(
    db: Session,
    tenant_id,
    user_id: int,
    nome: str,
    descricao: str,
) -> CategoriaFinanceira:
    categoria = db.query(CategoriaFinanceira).filter(
        CategoriaFinanceira.tenant_id == str(tenant_id),
        CategoriaFinanceira.nome == nome,
        CategoriaFinanceira.tipo == "receita",
    ).first()
    if categoria:
        return categoria

    categoria = CategoriaFinanceira(
        tenant_id=str(tenant_id),
        nome=nome,
        tipo="receita",
        descricao=descricao,
        dre_subcategoria_id=_obter_dre_subcategoria_receita_padrao(db, tenant_id),
        ativo=True,
        user_id=user_id,
    )
    db.add(categoria)
    db.flush()
    return categoria


def _criar_conta_receber_procedimento(
    db: Session,
    *,
    tenant_id,
    user_id: int,
    cliente_id: Optional[int],
    categoria_id: int,
    dre_subcategoria_id: int,
    descricao: str,
    valor: float,
    documento: str,
    observacoes: Optional[str] = None,
):
    existente = db.query(ContaReceber).filter(
        ContaReceber.tenant_id == str(tenant_id),
        ContaReceber.documento == documento,
    ).first()
    if existente:
        return existente

    conta = ContaReceber(
        tenant_id=str(tenant_id),
        descricao=descricao,
        cliente_id=cliente_id,
        categoria_id=categoria_id,
        dre_subcategoria_id=dre_subcategoria_id,
        canal="loja_fisica",
        valor_original=Decimal(str(_round_money(valor))),
        valor_recebido=Decimal("0"),
        valor_final=Decimal(str(_round_money(valor))),
        data_emissao=date.today(),
        data_vencimento=date.today(),
        status="pendente",
        documento=documento,
        observacoes=observacoes,
        user_id=user_id,
    )
    db.add(conta)
    db.flush()
    return conta


def _sincronizar_financeiro_procedimento(
    db: Session,
    procedimento: ProcedimentoConsulta,
    tenant_id,
    user_id: int,
) -> None:
    consulta = db.query(ConsultaVet).filter(
        ConsultaVet.id == procedimento.consulta_id,
        ConsultaVet.tenant_id == tenant_id,
    ).first()
    if not consulta:
        return

    regra = _obter_regra_financeira_veterinaria(db, tenant_id)
    resumo = _resumo_financeiro_procedimento(procedimento.valor, procedimento.insumos, regra)

    categoria_empresa = _obter_ou_criar_categoria_financeira_vet(
        db,
        regra["empresa_tenant_id"],
        user_id,
        "Veterinário - Procedimentos",
        "Receitas de procedimentos veterinários.",
    )

    if regra["modo_operacional"] == "parceiro":
        categoria_vet = _obter_ou_criar_categoria_financeira_vet(
            db,
            tenant_id,
            user_id,
            "Veterinário - Receita Líquida",
            "Receita líquida do veterinário após repasse da empresa.",
        )

        if resumo["receita_tenant_valor"] > 0:
            _criar_conta_receber_procedimento(
                db,
                tenant_id=tenant_id,
                user_id=user_id,
                cliente_id=consulta.cliente_id,
                categoria_id=categoria_vet.id,
                dre_subcategoria_id=categoria_vet.dre_subcategoria_id or _obter_dre_subcategoria_receita_padrao(db, tenant_id),
                descricao=f"Procedimento vet #{procedimento.id} - líquido {procedimento.nome}",
                valor=resumo["receita_tenant_valor"],
                documento=f"VET-PROC-{procedimento.id}-LIQUIDO-VET",
                observacoes=f"Receita líquida após repasse de {resumo['comissao_empresa_pct']}% para a empresa.",
            )

        if resumo["repasse_empresa_valor"] > 0:
            _criar_conta_receber_procedimento(
                db,
                tenant_id=regra["empresa_tenant_id"],
                user_id=user_id,
                cliente_id=None,
                categoria_id=categoria_empresa.id,
                dre_subcategoria_id=categoria_empresa.dre_subcategoria_id or _obter_dre_subcategoria_receita_padrao(db, regra["empresa_tenant_id"]),
                descricao=f"Repasse vet #{procedimento.id} - {procedimento.nome}",
                valor=resumo["repasse_empresa_valor"],
                documento=f"VET-PROC-{procedimento.id}-REPASSE-EMPRESA",
                observacoes=f"Base de repasse do parceiro veterinário ({resumo['comissao_empresa_pct']}%).",
            )
        return

    _criar_conta_receber_procedimento(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        cliente_id=consulta.cliente_id,
        categoria_id=categoria_empresa.id,
        dre_subcategoria_id=categoria_empresa.dre_subcategoria_id or _obter_dre_subcategoria_receita_padrao(db, tenant_id),
        descricao=f"Procedimento vet #{procedimento.id} - {procedimento.nome}",
        valor=resumo["entrada_empresa_valor"],
        documento=f"VET-PROC-{procedimento.id}-EMPRESA",
        observacoes="Receita gerada automaticamente a partir do procedimento veterinário.",
    )


def _serializar_procedimento(procedimento: ProcedimentoConsulta, db: Session, tenant_id) -> dict:
    regra = _obter_regra_financeira_veterinaria(db, tenant_id)
    resumo = _resumo_financeiro_procedimento(procedimento.valor, procedimento.insumos, regra)
    return {
        "id": procedimento.id,
        "consulta_id": procedimento.consulta_id,
        "catalogo_id": procedimento.catalogo_id,
        "nome": procedimento.nome,
        "descricao": procedimento.descricao,
        "valor": procedimento.valor,
        "valor_cobrado": resumo["valor_cobrado"],
        "realizado": procedimento.realizado,
        "observacoes": procedimento.observacoes,
        "insumos": resumo["insumos"],
        "custo_total": resumo["custo_total"],
        "margem_valor": resumo["margem_valor"],
        "margem_percentual": resumo["margem_percentual"],
        "modo_operacional": resumo["modo_operacional"],
        "comissao_empresa_pct": resumo["comissao_empresa_pct"],
        "repasse_empresa_valor": resumo["repasse_empresa_valor"],
        "receita_tenant_valor": resumo["receita_tenant_valor"],
        "entrada_empresa_valor": resumo["entrada_empresa_valor"],
        "estoque_baixado": bool(procedimento.estoque_baixado),
        "estoque_movimentacao_ids": procedimento.estoque_movimentacao_ids or [],
        "created_at": procedimento.created_at,
    }


def _serializar_catalogo(catalogo: CatalogoProcedimento, db: Session, tenant_id) -> dict:
    insumos = _enriquecer_insumos_com_custos(db, tenant_id, catalogo.insumos or []) if catalogo.insumos else []
    regra = _obter_regra_financeira_veterinaria(db, tenant_id)
    resumo = _resumo_financeiro_procedimento(catalogo.valor_padrao, insumos, regra)
    return {
        "id": catalogo.id,
        "nome": catalogo.nome,
        "descricao": catalogo.descricao,
        "categoria": catalogo.categoria,
        "valor_padrao": catalogo.valor_padrao,
        "duracao_minutos": catalogo.duracao_minutos,
        "requer_anestesia": catalogo.requer_anestesia,
        "observacoes": catalogo.observacoes,
        "insumos": resumo["insumos"],
        "custo_estimado": resumo["custo_total"],
        "margem_estimada": resumo["margem_valor"],
        "margem_percentual_estimada": resumo["margem_percentual"],
        "modo_operacional": resumo["modo_operacional"],
        "comissao_empresa_pct": resumo["comissao_empresa_pct"],
        "repasse_empresa_estimado": resumo["repasse_empresa_valor"],
        "receita_tenant_estimada": resumo["receita_tenant_valor"],
        "ativo": catalogo.ativo,
    }


def _meses_desde(data_base: Optional[date], referencia: Optional[date] = None) -> Optional[int]:
    if not data_base:
        return None
    ref = referencia or date.today()
    return max((ref.year - data_base.year) * 12 + (ref.month - data_base.month), 0)


def _avaliar_resultado_item(chave: str, valor) -> Optional[dict]:
    numero = _as_float(valor)
    if numero is None:
        return None

    regras = {
        "hematocrito": (25, 55, "Hematócrito fora da faixa."),
        "hemacias": (5, 10, "Hemácias fora da faixa."),
        "hemoglobina": (8, 18, "Hemoglobina fora da faixa."),
        "leucocitos": (6000, 17000, "Leucócitos fora da faixa."),
        "plaquetas": (180000, 500000, "Plaquetas fora da faixa."),
        "ureia": (10, 60, "Ureia elevada ou reduzida."),
        "creatinina": (0.5, 1.8, "Creatinina fora da faixa."),
        "alt": (10, 120, "ALT fora da faixa."),
        "ast": (10, 80, "AST fora da faixa."),
        "glicose": (70, 140, "Glicose fora da faixa."),
    }

    chave_limpa = (chave or "").strip().lower()
    if chave_limpa not in regras:
        return None

    minimo, maximo, mensagem = regras[chave_limpa]
    if minimo <= numero <= maximo:
        return {
            "campo": chave,
            "valor": numero,
            "status": "normal",
            "mensagem": f"{chave}: dentro da faixa esperada.",
        }

    status = "alto" if numero > maximo else "baixo"
    return {
        "campo": chave,
        "valor": numero,
        "status": status,
        "mensagem": mensagem,
    }


def _gerar_interpretacao_exame(exame: ExameVet) -> dict:
    alertas = []
    dados = exame.resultado_json if isinstance(exame.resultado_json, dict) else {}
    for chave, valor in dados.items():
        avaliacao = _avaliar_resultado_item(chave, valor)
        if avaliacao and avaliacao["status"] != "normal":
            alertas.append(avaliacao)

    texto_livre = (exame.resultado_texto or "").lower()
    termos_criticos = {
        "anemia": "Possível anemia descrita no laudo.",
        "trombocitopenia": "Laudo cita trombocitopenia.",
        "leucocitose": "Laudo cita leucocitose.",
        "insuficiência renal": "Laudo cita insuficiência renal.",
        "insuficiencia renal": "Laudo cita insuficiência renal.",
        "hepatopatia": "Laudo cita alteração hepática.",
        "fratura": "Laudo cita fratura.",
        "massa": "Laudo cita presença de massa.",
    }
    for termo, mensagem in termos_criticos.items():
        if termo in texto_livre:
            alertas.append({"campo": termo, "status": "atencao", "mensagem": mensagem})

    if not alertas:
        resumo = "Nenhum alerta automático relevante foi encontrado. Confirmar com avaliação clínica."
        conclusao = "Triagem automática sem achados críticos aparentes."
        confianca = 0.58
    else:
        resumo = "; ".join(dict.fromkeys(a["mensagem"] for a in alertas))
        conclusao = f"Triagem automática encontrou {len(alertas)} ponto(s) que merecem revisão veterinária."
        confianca = min(0.45 + (len(alertas) * 0.1), 0.89)

    return {
        "resumo": resumo,
        "conclusao": conclusao,
        "confianca": round(confianca, 2),
        "alertas": alertas,
        "payload": {
            "resultado_json": dados,
            "tem_resultado_texto": bool(exame.resultado_texto),
            "analisado_em": datetime.utcnow().isoformat(),
        },
    }


def _aplicar_baixa_estoque_procedimento(db: Session, procedimento: ProcedimentoConsulta, tenant_id, user_id: int) -> None:
    if not procedimento.realizado or procedimento.estoque_baixado:
        return

    itens = _normalizar_insumos(procedimento.insumos)
    produtos = _buscar_produtos_por_ids(db, tenant_id, [item["produto_id"] for item in itens])
    movimentacoes_ids = []
    for item in itens:
        if not item["baixar_estoque"]:
            continue

        produto = produtos.get(item["produto_id"])
        if not produto:
            raise HTTPException(status_code=404, detail=f"Produto {item['produto_id']} não encontrado para o procedimento")
        if not produto.ativo:
            raise HTTPException(status_code=404, detail=f"Produto {item['produto_id']} não encontrado para o procedimento")

        estoque_atual = float(produto.estoque_atual or 0)
        if estoque_atual < item["quantidade"]:
            raise HTTPException(
                status_code=400,
                detail=f"Estoque insuficiente para {produto.nome}. Disponível: {estoque_atual}, necessário: {item['quantidade']}",
            )

        quantidade_anterior = estoque_atual
        quantidade_nova = estoque_atual - item["quantidade"]
        produto.estoque_atual = quantidade_nova
        custo_unitario = _round_money(produto.preco_custo)
        custo_total = _round_money(custo_unitario * item["quantidade"])

        movimentacao = EstoqueMovimentacao(
            tenant_id=str(tenant_id),
            produto_id=produto.id,
            tipo="saida",
            motivo="procedimento_veterinario",
            quantidade=item["quantidade"],
            quantidade_anterior=quantidade_anterior,
            quantidade_nova=quantidade_nova,
            custo_unitario=custo_unitario,
            valor_total=custo_total,
            referencia_id=procedimento.id,
            referencia_tipo="procedimento_veterinario",
            documento=str(procedimento.consulta_id),
            observacao=f"Baixa automática do procedimento {procedimento.nome}",
            user_id=user_id,
        )
        db.add(movimentacao)
        db.flush()
        movimentacoes_ids.append(movimentacao.id)
        item["nome"] = item.get("nome") or produto.nome
        item["unidade"] = item.get("unidade") or produto.unidade
        item["custo_unitario"] = custo_unitario
        item["custo_total"] = custo_total

    procedimento.insumos = itens
    procedimento.estoque_baixado = bool(movimentacoes_ids) or procedimento.estoque_baixado
    procedimento.estoque_movimentacao_ids = movimentacoes_ids or procedimento.estoque_movimentacao_ids


def _status_vacinal_pet(db: Session, pet: Pet, tenant_id) -> dict:
    especie = (pet.especie or "").strip().lower()
    protocolos = db.query(ProtocoloVacina).filter(
        ProtocoloVacina.tenant_id == tenant_id,
        ProtocoloVacina.ativo == True,
    ).all()
    protocolos_ativos = [
        protocolo for protocolo in protocolos
        if not protocolo.especie or protocolo.especie.strip().lower() in {"", especie, "todos", "all"}
    ]

    registros = db.query(VacinaRegistro).filter(
        VacinaRegistro.pet_id == pet.id,
        VacinaRegistro.tenant_id == tenant_id,
    ).order_by(VacinaRegistro.data_aplicacao.desc()).all()

    pendentes = []
    vencidas = []
    carteira = []
    hoje = date.today()
    registros_por_nome = {}
    for registro in registros:
        chave = (registro.nome_vacina or "").strip().lower()
        registros_por_nome.setdefault(chave, []).append(registro)
        status = "em_dia"
        if registro.data_proxima_dose and registro.data_proxima_dose < hoje:
            status = "atrasada"
            vencidas.append({
                "nome": registro.nome_vacina,
                "data_proxima_dose": registro.data_proxima_dose.isoformat(),
                "dias_atraso": (hoje - registro.data_proxima_dose).days,
            })
        elif registro.data_proxima_dose and registro.data_proxima_dose <= hoje + timedelta(days=30):
            status = "vence_breve"
        carteira.append({
            "id": registro.id,
            "nome": registro.nome_vacina,
            "data_aplicacao": registro.data_aplicacao.isoformat(),
            "data_proxima_dose": registro.data_proxima_dose.isoformat() if registro.data_proxima_dose else None,
            "numero_dose": registro.numero_dose,
            "lote": registro.lote,
            "fabricante": registro.fabricante,
            "status": status,
        })

    idade_meses = _meses_desde(pet.data_nascimento)
    for protocolo in protocolos_ativos:
        chave = (protocolo.nome or "").strip().lower()
        registros_vacina = registros_por_nome.get(chave, [])
        if registros_vacina:
            continue
        idade_inicio = protocolo.dose_inicial_semanas * 4 if protocolo.dose_inicial_semanas else None
        if idade_inicio is None or idade_meses is None or idade_meses >= idade_inicio:
            pendentes.append({
                "nome": protocolo.nome,
                "motivo": "Vacina prevista no protocolo sem registro aplicado.",
                "idade_inicio_meses": idade_inicio,
            })

    return {
        "carteira": carteira,
        "pendentes": pendentes,
        "vencidas": vencidas,
        "resumo": {
            "total_aplicadas": len(carteira),
            "total_pendentes": len(pendentes),
            "total_vencidas": len(vencidas),
        },
    }


def _montar_alertas_pet(db: Session, pet: Pet, tenant_id) -> list[dict]:
    alertas = []
    alergias = pet.alergias_lista if isinstance(getattr(pet, "alergias_lista", None), list) else None
    if not alergias and pet.alergias:
        alergias = [pet.alergias]
    for alergia in alergias or []:
        alertas.append({"tipo": "alergia", "nivel": "critico", "mensagem": f"Alergia registrada: {alergia}"})

    restricoes = getattr(pet, "restricoes_alimentares_lista", None) or []
    for restricao in restricoes:
        alertas.append({"tipo": "restricao", "nivel": "aviso", "mensagem": f"Restrição alimentar: {restricao}"})

    status_vacinal = _status_vacinal_pet(db, pet, tenant_id)
    for vacina in status_vacinal["vencidas"]:
        alertas.append({
            "tipo": "vacina_atrasada",
            "nivel": "aviso",
            "mensagem": f"Vacina {vacina['nome']} atrasada há {vacina['dias_atraso']} dia(s).",
        })
    for pendente in status_vacinal["pendentes"][:3]:
        alertas.append({
            "tipo": "vacina_pendente",
            "nivel": "info",
            "mensagem": f"Protocolo sem registro: {pendente['nome']}.",
        })

    exames_pendentes = db.query(ExameVet).filter(
        ExameVet.pet_id == pet.id,
        ExameVet.tenant_id == tenant_id,
        ExameVet.status.in_(["solicitado", "aguardando", "disponivel"]),
    ).order_by(ExameVet.created_at.desc()).limit(3).all()
    for exame in exames_pendentes:
        alertas.append({
            "tipo": "exame_pendente",
            "nivel": "info",
            "mensagem": f"Exame {exame.nome} ainda está em {exame.status}.",
        })

    return alertas


def _pet_or_404(db: Session, pet_id: int, tenant_id) -> Pet:
    tenant_ids = _all_accessible_tenant_ids(db, tenant_id)
    pet = (
        db.query(Pet)
        .join(Cliente)
        .options(joinedload(Pet.cliente))
        .filter(Pet.id == pet_id, Cliente.tenant_id.in_(tenant_ids))
        .first()
    )
    if not pet:
        raise HTTPException(status_code=404, detail="Pet não encontrado")
    return pet


def _consulta_or_404(db: Session, consulta_id: int, tenant_id) -> ConsultaVet:
    c = db.query(ConsultaVet).filter(ConsultaVet.id == consulta_id, ConsultaVet.tenant_id == tenant_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Consulta não encontrada")
    return c


def _prescricao_or_404(db: Session, prescricao_id: int, tenant_id) -> PrescricaoVet:
    p = (
        db.query(PrescricaoVet)
        .options(joinedload(PrescricaoVet.itens), joinedload(PrescricaoVet.pet), joinedload(PrescricaoVet.consulta))
        .filter(PrescricaoVet.id == prescricao_id, PrescricaoVet.tenant_id == tenant_id)
        .first()
    )
    if not p:
        raise HTTPException(status_code=404, detail="Prescrição não encontrada")
    return p


def _upsert_lembretes_push_agendamento(db: Session, ag: AgendamentoVet, tenant_id) -> None:
    """Cria/atualiza lembretes push de 24h e 1h para o tutor no app mobile."""
    if not ag.data_hora or not ag.cliente_id:
        return

    if ag.status in {"cancelado", "faltou"}:
        return

    from app.campaigns.models import NotificationChannelEnum, NotificationQueue, NotificationStatusEnum

    cliente = db.query(Cliente).filter(
        Cliente.id == ag.cliente_id,
        Cliente.tenant_id == str(tenant_id),
    ).first()
    if not cliente or not cliente.user_id:
        return

    user_tutor = db.query(User).filter(
        User.id == cliente.user_id,
        User.tenant_id == str(tenant_id),
    ).first()
    if not user_tutor or not getattr(user_tutor, "push_token", None):
        return

    prefixo = f"vet-agendamento:{ag.id}:"

    db.query(NotificationQueue).filter(
        NotificationQueue.idempotency_key.like(f"{prefixo}%"),
        NotificationQueue.status == NotificationStatusEnum.pending,
    ).delete(synchronize_session=False)

    agora = datetime.now(ag.data_hora.tzinfo) if getattr(ag.data_hora, "tzinfo", None) else datetime.now()
    lembretes = [
        (
            24,
            "Lembrete de consulta veterinária",
            f"Olá! A consulta do pet está marcada para amanhã às {ag.data_hora.strftime('%H:%M')}.",
        ),
        (
            1,
            "Lembrete de consulta veterinária",
            f"A consulta do pet começa em 1 hora ({ag.data_hora.strftime('%H:%M')}).",
        ),
    ]

    for horas, assunto, mensagem in lembretes:
        envio_em = ag.data_hora - timedelta(hours=horas)
        if envio_em <= agora:
            continue

        idempotencia = f"{prefixo}{horas}h:{ag.data_hora.isoformat()}"
        existe = db.query(NotificationQueue.id).filter(
            NotificationQueue.idempotency_key == idempotencia
        ).first()
        if existe:
            continue

        db.add(
            NotificationQueue(
                tenant_id=tenant_id,
                idempotency_key=idempotencia,
                customer_id=cliente.id,
                channel=NotificationChannelEnum.push,
                subject=assunto,
                body=mensagem,
                push_token=user_tutor.push_token,
                scheduled_at=envio_em,
            )
        )


_BAIA_MOTIVO_RE = re.compile(r"\s*\[BAIA:(?P<baia>[^\]]+)\]\s*$")
_PROC_PREFIX = "[PROC_INT]"


def _pack_motivo_baia(motivo: str, baia: Optional[str]) -> str:
    motivo_limpo = (motivo or "").strip()
    baia_limpa = (baia or "").strip()
    if not baia_limpa:
        return motivo_limpo
    return f"{motivo_limpo} [BAIA:{baia_limpa}]"


def _split_motivo_baia(motivo: Optional[str]) -> tuple[str, Optional[str]]:
    texto = (motivo or "").strip()
    m = _BAIA_MOTIVO_RE.search(texto)
    if not m:
        return texto, None
    baia = (m.group("baia") or "").strip() or None
    motivo_sem_baia = _BAIA_MOTIVO_RE.sub("", texto).strip()
    return motivo_sem_baia, baia


def _normalizar_baia(baia: Optional[str]) -> Optional[str]:
    valor = (baia or "").strip()
    if not valor:
        return None
    return valor.lower()


def _build_procedimento_observacao(payload: dict) -> str:
    return f"{_PROC_PREFIX}{json.dumps(payload, ensure_ascii=False)}"


def _parse_procedimento_observacao(observacoes: Optional[str]) -> Optional[dict]:
    texto = (observacoes or "").strip()
    if not texto.startswith(_PROC_PREFIX):
        return None
    bruto = texto[len(_PROC_PREFIX):]
    if not bruto:
        return None
    try:
        parsed = json.loads(bruto)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def _separar_evolucoes_e_procedimentos(registros: list[EvolucaoInternacao]) -> tuple[list[dict], list[dict]]:
    evolucoes_formatadas = []
    procedimentos_formatados = []

    for ev in registros:
        proc_payload = _parse_procedimento_observacao(ev.observacoes)
        if proc_payload:
            procedimentos_formatados.append({
                "id": ev.id,
                "data_hora": ev.data_hora,
                "status": proc_payload.get("status") or "concluido",
                "horario_agendado": proc_payload.get("horario_agendado"),
                "medicamento": proc_payload.get("medicamento"),
                "dose": proc_payload.get("dose"),
                "via": proc_payload.get("via"),
                "executado_por": proc_payload.get("executado_por"),
                "horario_execucao": proc_payload.get("horario_execucao"),
                "observacao_execucao": proc_payload.get("observacao_execucao"),
                "observacoes_agenda": proc_payload.get("observacoes_agenda"),
            })
            continue

        evolucoes_formatadas.append({
            "id": ev.id,
            "data_hora": ev.data_hora,
            "temperatura": ev.temperatura,
            "freq_cardiaca": ev.frequencia_cardiaca,
            "freq_respiratoria": ev.frequencia_respiratoria,
            "nivel_dor": ev.nivel_dor,
            "pressao_sistolica": ev.pressao_sistolica,
            "glicemia": ev.glicemia,
            "peso": ev.peso,
            "observacoes": ev.observacoes,
        })

    return evolucoes_formatadas, procedimentos_formatados


# ═══════════════════════════════════════════════════════════════
# AGENDAMENTOS
# ═══════════════════════════════════════════════════════════════

class AgendamentoCreate(BaseModel):
    pet_id: int
    cliente_id: int
    veterinario_id: Optional[int] = None
    data_hora: datetime
    duracao_minutos: int = 30
    tipo: str = "consulta"
    motivo: Optional[str] = None
    is_emergencia: bool = False
    sintoma_emergencia: Optional[str] = None
    observacoes: Optional[str] = None


class AgendamentoUpdate(BaseModel):
    data_hora: Optional[datetime] = None
    duracao_minutos: Optional[int] = None
    tipo: Optional[str] = None
    motivo: Optional[str] = None
    status: Optional[str] = None
    veterinario_id: Optional[int] = None
    observacoes: Optional[str] = None
    pretriagem: Optional[dict] = None


class AgendamentoResponse(BaseModel):
    id: int
    pet_id: int
    cliente_id: int
    veterinario_id: Optional[int]
    data_hora: datetime
    duracao_minutos: int
    tipo: str
    motivo: Optional[str]
    status: str
    is_emergencia: bool
    consulta_id: Optional[int]
    observacoes: Optional[str]
    pet_nome: Optional[str] = None
    cliente_nome: Optional[str] = None
    veterinario_nome: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ═══════════════════════════════════════════════════════════════
# VETERINÁRIOS (listagem para seleção em formulários)
# ═══════════════════════════════════════════════════════════════

class VeterinarioSimples(BaseModel):
    id: int
    nome: str
    crmv: Optional[str] = None
    email: Optional[str] = None
    telefone: Optional[str] = None

    class Config:
        from_attributes = True


@router.get("/veterinarios", response_model=List[VeterinarioSimples])
def listar_veterinarios(
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    """Lista pessoas cadastradas como veterinário neste tenant (para selects nos formulários)."""
    user, tenant_id = _get_tenant(current)
    vets = (
        db.query(Cliente)
        .filter(
            Cliente.tenant_id == tenant_id,
            Cliente.tipo_cadastro == "veterinario",
            Cliente.ativo == True,
        )
        .order_by(Cliente.nome)
        .all()
    )
    return [
        {"id": v.id, "nome": v.nome, "crmv": getattr(v, "crmv", None), "email": v.email, "telefone": v.telefone}
        for v in vets
    ]


# ═══════════════════════════════════════════════════════════════
# PETS ACESSÍVEIS (próprio tenant + empresas parceiras)
# ═══════════════════════════════════════════════════════════════

@router.get("/pets")
def listar_pets_vet(
    busca: Optional[str] = Query(None),
    limit: int = Query(500, ge=1, le=1000),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    """
    Lista os pets acessíveis ao veterinário:
    - pets do próprio tenant (se tiver cadastros próprios)
    - pets de todas as empresas parceiras ativas vinculadas
    """
    user, tenant_id = _get_tenant(current)
    tenant_ids = _all_accessible_tenant_ids(db, tenant_id)

    q = (
        db.query(Pet)
        .join(Cliente)
        .options(joinedload(Pet.cliente))
        .filter(Cliente.tenant_id.in_(tenant_ids), Pet.ativo == True)
    )

    if busca:
        busca_term = f"%{busca}%"
        q = q.filter(
            or_(
                Pet.nome.ilike(busca_term),
                Pet.raca.ilike(busca_term),
                Cliente.nome.ilike(busca_term),
            )
        )

    pets = q.order_by(Pet.nome).limit(limit).all()

    return [
        {
            "id": p.id,
            "codigo": p.codigo,
            "cliente_id": p.cliente_id,
            "nome": p.nome,
            "especie": p.especie,
            "raca": p.raca,
            "sexo": p.sexo,
            "castrado": p.castrado,
            "data_nascimento": p.data_nascimento,
            "peso": p.peso,
            "porte": p.porte,
            "microchip": p.microchip,
            "alergias": p.alergias,
            "doencas_cronicas": p.doencas_cronicas,
            "medicamentos_continuos": p.medicamentos_continuos,
            "historico_clinico": p.historico_clinico,
            "observacoes": p.observacoes,
            "foto_url": p.foto_url,
            "ativo": p.ativo,
            "tenant_id": str(p.tenant_id),
            "cliente_nome": p.cliente.nome if p.cliente else None,
            "cliente_telefone": p.cliente.telefone if p.cliente else None,
            "cliente_celular": p.cliente.celular if p.cliente else None,
        }
        for p in pets
    ]


@router.get("/agendamentos", response_model=List[AgendamentoResponse])
def listar_agendamentos(
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    status: Optional[str] = None,
    pet_id: Optional[int] = None,
    veterinario_id: Optional[int] = None,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    q = db.query(AgendamentoVet).filter(AgendamentoVet.tenant_id == tenant_id)

    if data_inicio:
        q = q.filter(func.date(AgendamentoVet.data_hora) >= data_inicio)
    if data_fim:
        q = q.filter(func.date(AgendamentoVet.data_hora) <= data_fim)
    if status:
        q = q.filter(AgendamentoVet.status == status)
    if pet_id:
        q = q.filter(AgendamentoVet.pet_id == pet_id)
    if veterinario_id:
        q = q.filter(AgendamentoVet.veterinario_id == veterinario_id)

    agendamentos = q.order_by(AgendamentoVet.data_hora).all()

    result = []
    for ag in agendamentos:
        d = {
            "id": ag.id,
            "pet_id": ag.pet_id,
            "cliente_id": ag.cliente_id,
            "veterinario_id": ag.veterinario_id,
            "data_hora": ag.data_hora,
            "duracao_minutos": ag.duracao_minutos,
            "tipo": ag.tipo,
            "motivo": ag.motivo,
            "status": ag.status,
            "is_emergencia": ag.is_emergencia,
            "consulta_id": ag.consulta_id,
            "observacoes": ag.observacoes,
            "created_at": ag.created_at,
        }


    @router.get("/agendamentos/{agendamento_id}/push-diagnostico")
    def diagnostico_push_agendamento(
        agendamento_id: int,
        db: Session = Depends(get_session),
        current=Depends(get_current_user_and_tenant),
    ):
        _, tenant_id = _get_tenant(current)
        ag = db.query(AgendamentoVet).filter(
            AgendamentoVet.id == agendamento_id,
            AgendamentoVet.tenant_id == tenant_id,
        ).first()
        if not ag:
            raise HTTPException(404, "Agendamento não encontrado")

        from app.campaigns.models import NotificationQueue, NotificationStatusEnum

        cliente = db.query(Cliente).filter(
            Cliente.id == ag.cliente_id,
            Cliente.tenant_id == str(tenant_id),
        ).first()
        user_tutor = None
        if cliente and cliente.user_id:
            user_tutor = db.query(User).filter(
                User.id == cliente.user_id,
                User.tenant_id == str(tenant_id),
            ).first()

        prefixo = f"vet-agendamento:{ag.id}:"
        lembretes = db.query(NotificationQueue).filter(
            NotificationQueue.tenant_id == str(tenant_id),
            NotificationQueue.idempotency_key.like(f"{prefixo}%"),
        ).order_by(NotificationQueue.scheduled_at.asc(), NotificationQueue.created_at.desc()).all()

        return {
            "agendamento_id": ag.id,
            "pet_id": ag.pet_id,
            "cliente_id": ag.cliente_id,
            "data_hora": ag.data_hora.isoformat() if ag.data_hora else None,
            "status": ag.status,
            "tutor_tem_push_token": bool(getattr(user_tutor, "push_token", None)),
            "push_token_preview": f"{user_tutor.push_token[:18]}..." if getattr(user_tutor, "push_token", None) else None,
            "lembretes": [
                {
                    "id": lembrete.id,
                    "subject": lembrete.subject,
                    "status": lembrete.status.value if hasattr(lembrete.status, "value") else str(lembrete.status),
                    "scheduled_at": lembrete.scheduled_at.isoformat() if lembrete.scheduled_at else None,
                }
                for lembrete in lembretes
            ],
            "observacao": "Para validar push real no celular, o app precisa estar fora do Expo Go e com token registrado.",
        }
        if ag.pet:
            d["pet_nome"] = ag.pet.nome
        if ag.cliente:
            d["cliente_nome"] = ag.cliente.nome
        if ag.veterinario:
            d["veterinario_nome"] = ag.veterinario.nome
        result.append(d)
    return result


@router.post("/agendamentos", response_model=AgendamentoResponse, status_code=201)
def criar_agendamento(
    body: AgendamentoCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    ag = AgendamentoVet(
        pet_id=body.pet_id,
        cliente_id=body.cliente_id,
        veterinario_id=body.veterinario_id,
        user_id=user.id,
        data_hora=body.data_hora,
        duracao_minutos=body.duracao_minutos,
        tipo=body.tipo,
        motivo=body.motivo,
        is_emergencia=body.is_emergencia,
        sintoma_emergencia=body.sintoma_emergencia,
        observacoes=body.observacoes,
        status="agendado",
    )
    db.add(ag)
    db.flush()
    _upsert_lembretes_push_agendamento(db, ag, tenant_id)
    db.commit()
    db.refresh(ag)
    return _agendamento_to_dict(ag)


@router.patch("/agendamentos/{agendamento_id}", response_model=AgendamentoResponse)
def atualizar_agendamento(
    agendamento_id: int,
    body: AgendamentoUpdate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    ag = db.query(AgendamentoVet).filter(
        AgendamentoVet.id == agendamento_id,
        AgendamentoVet.tenant_id == tenant_id,
    ).first()
    if not ag:
        raise HTTPException(404, "Agendamento não encontrado")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(ag, field, value)

    _upsert_lembretes_push_agendamento(db, ag, tenant_id)
    db.commit()
    db.refresh(ag)
    return _agendamento_to_dict(ag)


def _agendamento_to_dict(ag: AgendamentoVet) -> dict:
    return {
        "id": ag.id,
        "pet_id": ag.pet_id,
        "cliente_id": ag.cliente_id,
        "veterinario_id": ag.veterinario_id,
        "data_hora": ag.data_hora,
        "duracao_minutos": ag.duracao_minutos,
        "tipo": ag.tipo,
        "motivo": ag.motivo,
        "status": ag.status,
        "is_emergencia": ag.is_emergencia,
        "consulta_id": ag.consulta_id,
        "observacoes": ag.observacoes,
        "created_at": ag.created_at,
        "pet_nome": ag.pet.nome if ag.pet else None,
        "cliente_nome": ag.cliente.nome if ag.cliente else None,
        "veterinario_nome": ag.veterinario.nome if ag.veterinario else None,
    }


# ═══════════════════════════════════════════════════════════════
# CONSULTAS
# ═══════════════════════════════════════════════════════════════

class ConsultaCreate(BaseModel):
    pet_id: int
    cliente_id: int
    veterinario_id: Optional[int] = None
    tipo: str = "consulta"
    agendamento_id: Optional[int] = None
    queixa_principal: Optional[str] = None


class ConsultaUpdate(BaseModel):
    queixa_principal: Optional[str] = None
    historia_clinica: Optional[str] = None
    peso_consulta: Optional[float] = None
    temperatura: Optional[float] = None
    frequencia_cardiaca: Optional[int] = None
    frequencia_respiratoria: Optional[int] = None
    tpc: Optional[str] = None
    mucosas: Optional[str] = None
    hidratacao: Optional[str] = None
    nivel_dor: Optional[int] = None
    saturacao_o2: Optional[float] = None
    pressao_sistolica: Optional[int] = None
    pressao_diastolica: Optional[int] = None
    glicemia: Optional[float] = None
    exame_fisico: Optional[str] = None
    hipotese_diagnostica: Optional[str] = None
    diagnostico: Optional[str] = None
    diagnostico_simples: Optional[str] = None
    conduta: Optional[str] = None
    retorno_em_dias: Optional[int] = None
    data_retorno: Optional[date] = None
    asa_score: Optional[int] = None
    asa_justificativa: Optional[str] = None
    observacoes_internas: Optional[str] = None
    observacoes_tutor: Optional[str] = None
    veterinario_id: Optional[int] = None


class ConsultaResponse(BaseModel):
    id: int
    pet_id: int
    cliente_id: int
    veterinario_id: Optional[int]
    tipo: str
    status: str
    queixa_principal: Optional[str]
    historia_clinica: Optional[str]
    peso_consulta: Optional[float]
    temperatura: Optional[float]
    frequencia_cardiaca: Optional[int]
    frequencia_respiratoria: Optional[int]
    tpc: Optional[str]
    mucosas: Optional[str]
    hidratacao: Optional[str]
    nivel_dor: Optional[int]
    saturacao_o2: Optional[float]
    pressao_sistolica: Optional[int]
    pressao_diastolica: Optional[int]
    glicemia: Optional[float]
    exame_fisico: Optional[str]
    hipotese_diagnostica: Optional[str]
    diagnostico: Optional[str]
    diagnostico_simples: Optional[str]
    conduta: Optional[str]
    retorno_em_dias: Optional[int]
    data_retorno: Optional[date]
    asa_score: Optional[int]
    asa_justificativa: Optional[str]
    observacoes_internas: Optional[str]
    observacoes_tutor: Optional[str]
    hash_prontuario: Optional[str]
    finalizado_em: Optional[datetime]
    inicio_atendimento: Optional[datetime]
    fim_atendimento: Optional[datetime]
    pet_nome: Optional[str] = None
    cliente_nome: Optional[str] = None
    veterinario_nome: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/consultas", response_model=List[ConsultaResponse])
def listar_consultas(
    pet_id: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    q = db.query(ConsultaVet).filter(ConsultaVet.tenant_id == tenant_id)
    if pet_id:
        q = q.filter(ConsultaVet.pet_id == pet_id)
    if status:
        q = q.filter(ConsultaVet.status == status)
    consultas = q.order_by(ConsultaVet.created_at.desc()).offset(skip).limit(limit).all()
    return [_consulta_to_dict(c) for c in consultas]


@router.post("/consultas", response_model=ConsultaResponse, status_code=201)
def criar_consulta(
    body: ConsultaCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)

    # Fallback defensivo: alguns fluxos podem chegar sem tenant no contexto.
    if tenant_id is None:
        cliente_ref = db.query(Cliente).filter(Cliente.id == body.cliente_id).first()
        if not cliente_ref or not cliente_ref.tenant_id:
            raise HTTPException(status_code=400, detail="Cliente inválido para criação da consulta")
        tenant_id = cliente_ref.tenant_id

    cliente_ok = db.query(Cliente).filter(
        Cliente.id == body.cliente_id,
        Cliente.tenant_id == tenant_id,
    ).first()
    if not cliente_ok:
        raise HTTPException(status_code=404, detail="Tutor não encontrado neste tenant")

    pet_ok = db.query(Pet).filter(
        Pet.id == body.pet_id,
        Pet.cliente_id == body.cliente_id,
    ).first()
    if not pet_ok:
        raise HTTPException(status_code=404, detail="Pet não encontrado para o tutor informado")

    c = ConsultaVet(
        pet_id=body.pet_id,
        cliente_id=body.cliente_id,
        veterinario_id=body.veterinario_id,
        user_id=user.id,
        tenant_id=tenant_id,
        tipo=body.tipo,
        queixa_principal=body.queixa_principal,
        status="em_andamento",
        inicio_atendimento=datetime.now(),
    )
    db.add(c)
    db.flush()

    # Vincula ao agendamento se informado
    if body.agendamento_id:
        ag = db.query(AgendamentoVet).filter(
            AgendamentoVet.id == body.agendamento_id,
            AgendamentoVet.tenant_id == tenant_id,
        ).first()
        if ag:
            ag.consulta_id = c.id
            ag.status = "em_atendimento"
            ag.inicio_atendimento = c.inicio_atendimento

    db.commit()
    db.refresh(c)
    return _consulta_to_dict(c)


@router.get("/consultas/{consulta_id}", response_model=ConsultaResponse)
def obter_consulta(
    consulta_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    c = _consulta_or_404(db, consulta_id, tenant_id)
    return _consulta_to_dict(c)


@router.patch("/consultas/{consulta_id}", response_model=ConsultaResponse)
def atualizar_consulta(
    consulta_id: int,
    body: ConsultaUpdate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    c = _consulta_or_404(db, consulta_id, tenant_id)

    if c.status == "finalizada":
        raise HTTPException(400, "Consulta já finalizada não pode ser editada")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(c, field, value)

    # Se registrou peso, cria registro na curva de peso
    if body.peso_consulta and body.peso_consulta > 0:
        peso_reg = PesoRegistro(
            pet_id=c.pet_id,
            consulta_id=c.id,
            user_id=user.id,
            data=date.today(),
            peso_kg=body.peso_consulta,
        )
        db.add(peso_reg)

        # Atualiza peso no cadastro do pet
        pet = db.query(Pet).filter(Pet.id == c.pet_id).first()
        if pet:
            pet.peso = body.peso_consulta

    db.commit()
    db.refresh(c)
    return _consulta_to_dict(c)


@router.post("/consultas/{consulta_id}/finalizar", response_model=ConsultaResponse)
def finalizar_consulta(
    consulta_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    c = _consulta_or_404(db, consulta_id, tenant_id)

    if c.status == "finalizada":
        raise HTTPException(400, "Consulta já está finalizada")

    c.status = "finalizada"
    c.fim_atendimento = datetime.now()
    c.finalizado_em = datetime.now()
    c.finalizado_por_id = user.id

    # Hash do prontuário para imutabilidade
    c.hash_prontuario = _hash_prontuario_consulta(c)

    # Finaliza agendamento vinculado
    if c.agendamento:
        c.agendamento.status = "finalizado"
        c.agendamento.fim_atendimento = c.fim_atendimento

    db.commit()
    db.refresh(c)
    return _consulta_to_dict(c)


def _consulta_to_dict(c: ConsultaVet) -> dict:
    return {
        "id": c.id,
        "pet_id": c.pet_id,
        "cliente_id": c.cliente_id,
        "veterinario_id": c.veterinario_id,
        "tipo": c.tipo,
        "status": c.status,
        "queixa_principal": c.queixa_principal,
        "historia_clinica": c.historia_clinica,
        "peso_consulta": c.peso_consulta,
        "temperatura": c.temperatura,
        "frequencia_cardiaca": c.frequencia_cardiaca,
        "frequencia_respiratoria": c.frequencia_respiratoria,
        "tpc": c.tpc,
        "mucosas": c.mucosas,
        "hidratacao": c.hidratacao,
        "nivel_dor": c.nivel_dor,
        "saturacao_o2": c.saturacao_o2,
        "pressao_sistolica": c.pressao_sistolica,
        "pressao_diastolica": c.pressao_diastolica,
        "glicemia": c.glicemia,
        "exame_fisico": c.exame_fisico,
        "hipotese_diagnostica": c.hipotese_diagnostica,
        "diagnostico": c.diagnostico,
        "diagnostico_simples": c.diagnostico_simples,
        "conduta": c.conduta,
        "retorno_em_dias": c.retorno_em_dias,
        "data_retorno": c.data_retorno,
        "asa_score": c.asa_score,
        "asa_justificativa": c.asa_justificativa,
        "observacoes_internas": c.observacoes_internas,
        "observacoes_tutor": c.observacoes_tutor,
        "hash_prontuario": c.hash_prontuario,
        "finalizado_em": c.finalizado_em,
        "inicio_atendimento": c.inicio_atendimento,
        "fim_atendimento": c.fim_atendimento,
        "pet_nome": c.pet.nome if c.pet else None,
        "cliente_nome": c.cliente.nome if c.cliente else None,
        "veterinario_nome": c.veterinario.nome if c.veterinario else None,
        "created_at": c.created_at,
    }


def _hash_prontuario_consulta(c: ConsultaVet) -> str:
    conteudo = f"{c.id}|{c.pet_id}|{c.diagnostico}|{c.conduta}|{c.finalizado_em}"
    return hashlib.sha256(conteudo.encode()).hexdigest()


# ═══════════════════════════════════════════════════════════════
# PRESCRIÇÕES
# ═══════════════════════════════════════════════════════════════

class ItemPrescricaoIn(BaseModel):
    nome_medicamento: str
    concentracao: Optional[str] = None
    forma_farmaceutica: Optional[str] = None
    quantidade: Optional[str] = None
    posologia: str
    via_administracao: Optional[str] = None
    duracao_dias: Optional[int] = None
    medicamento_catalogo_id: Optional[int] = None


class PrescricaoCreate(BaseModel):
    consulta_id: int
    pet_id: int
    veterinario_id: Optional[int] = None
    tipo_receituario: str = "simples"
    observacoes: Optional[str] = None
    itens: List[ItemPrescricaoIn]


class PrescricaoResponse(BaseModel):
    id: int
    consulta_id: int
    pet_id: int
    veterinario_id: Optional[int]
    numero: Optional[str]
    data_emissao: date
    tipo_receituario: str
    observacoes: Optional[str]
    hash_receita: Optional[str]
    itens: List[dict]
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/consultas/{consulta_id}/prescricoes", response_model=List[PrescricaoResponse])
def listar_prescricoes(
    consulta_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    _consulta_or_404(db, consulta_id, tenant_id)
    prescricoes = db.query(PrescricaoVet).filter(
        PrescricaoVet.consulta_id == consulta_id,
        PrescricaoVet.tenant_id == tenant_id,
    ).all()
    return [_prescricao_to_dict(p) for p in prescricoes]


@router.post("/prescricoes", response_model=PrescricaoResponse, status_code=201)
def criar_prescricao(
    body: PrescricaoCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)

    if tenant_id is None:
        consulta_ref = db.query(ConsultaVet).filter(ConsultaVet.id == body.consulta_id).first()
        if not consulta_ref or not consulta_ref.tenant_id:
            raise HTTPException(status_code=400, detail="Consulta inválida para emissão de prescrição")
        tenant_id = consulta_ref.tenant_id

    consulta_ok = db.query(ConsultaVet).filter(
        ConsultaVet.id == body.consulta_id,
        ConsultaVet.tenant_id == tenant_id,
    ).first()
    if not consulta_ok:
        raise HTTPException(status_code=404, detail="Consulta não encontrada neste tenant")

    # Número sequencial
    total = db.query(func.count(PrescricaoVet.id)).filter(PrescricaoVet.tenant_id == tenant_id).scalar() or 0
    numero = f"REC-{total + 1:05d}"

    p = PrescricaoVet(
        consulta_id=body.consulta_id,
        pet_id=body.pet_id,
        veterinario_id=body.veterinario_id,
        user_id=user.id,
        tenant_id=tenant_id,
        numero=numero,
        data_emissao=date.today(),
        tipo_receituario=body.tipo_receituario,
        observacoes=body.observacoes,
    )
    db.add(p)
    db.flush()

    for it in body.itens:
        item = ItemPrescricao(
            prescricao_id=p.id,
            tenant_id=tenant_id,
            nome_medicamento=it.nome_medicamento,
            concentracao=it.concentracao,
            forma_farmaceutica=it.forma_farmaceutica,
            quantidade=it.quantidade,
            posologia=it.posologia,
            via_administracao=it.via_administracao,
            duracao_dias=it.duracao_dias,
            medicamento_catalogo_id=it.medicamento_catalogo_id,
        )
        db.add(item)

    db.flush()

    # Hash da receita
    conteudo = f"{p.id}|{p.pet_id}|{p.data_emissao}|{[it.nome_medicamento for it in body.itens]}"
    p.hash_receita = hashlib.sha256(conteudo.encode()).hexdigest()

    db.commit()
    db.refresh(p)
    return _prescricao_to_dict(p)


def _prescricao_to_dict(p: PrescricaoVet) -> dict:
    return {
        "id": p.id,
        "consulta_id": p.consulta_id,
        "pet_id": p.pet_id,
        "veterinario_id": p.veterinario_id,
        "numero": p.numero,
        "data_emissao": p.data_emissao,
        "tipo_receituario": p.tipo_receituario,
        "observacoes": p.observacoes,
        "hash_receita": p.hash_receita,
        "created_at": p.created_at,
        "itens": [
            {
                "id": it.id,
                "nome_medicamento": it.nome_medicamento,
                "concentracao": it.concentracao,
                "forma_farmaceutica": it.forma_farmaceutica,
                "quantidade": it.quantidade,
                "posologia": it.posologia,
                "via_administracao": it.via_administracao,
                "duracao_dias": it.duracao_dias,
                "medicamento_catalogo_id": it.medicamento_catalogo_id,
            }
            for it in p.itens
        ],
    }


# ═══════════════════════════════════════════════════════════════
# VACINAS
# ═══════════════════════════════════════════════════════════════

class VacinaCreate(BaseModel):
    pet_id: int
    consulta_id: Optional[int] = None
    veterinario_id: Optional[int] = None
    protocolo_id: Optional[int] = None
    nome_vacina: str
    fabricante: Optional[str] = None
    lote: Optional[str] = None
    data_aplicacao: date
    data_proxima_dose: Optional[date] = None
    numero_dose: int = 1
    via_administracao: Optional[str] = None
    observacoes: Optional[str] = None


class VacinaResponse(BaseModel):
    id: int
    pet_id: int
    consulta_id: Optional[int]
    nome_vacina: str
    fabricante: Optional[str]
    lote: Optional[str]
    data_aplicacao: date
    data_proxima_dose: Optional[date]
    numero_dose: int
    via_administracao: Optional[str]
    observacoes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/pets/{pet_id}/vacinas", response_model=List[VacinaResponse])
def listar_vacinas_pet(
    pet_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)

    # Fallback defensivo: quando o tenant não vem no contexto, usa o tenant do pet informado.
    if tenant_id is None:
        pet_ref = db.query(Pet).filter(Pet.id == pet_id).first()
        if not pet_ref or not pet_ref.tenant_id:
            raise HTTPException(status_code=404, detail="Pet não encontrado")
        tenant_id = pet_ref.tenant_id

    vacinas = db.query(VacinaRegistro).filter(
        VacinaRegistro.pet_id == pet_id,
        VacinaRegistro.tenant_id == tenant_id,
    ).order_by(VacinaRegistro.data_aplicacao.desc()).all()
    return vacinas


@router.post("/vacinas", response_model=VacinaResponse, status_code=201)
def registrar_vacina(
    body: VacinaCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)

    # Fallback defensivo: em alguns fluxos o tenant pode vir nulo no contexto.
    if tenant_id is None:
        pet_ref = db.query(Pet).filter(Pet.id == body.pet_id).first()
        if not pet_ref or not pet_ref.tenant_id:
            raise HTTPException(status_code=400, detail="Pet inválido para registro de vacina")
        tenant_id = pet_ref.tenant_id

    pet_ok = db.query(Pet).filter(
        Pet.id == body.pet_id,
        Pet.tenant_id == tenant_id,
    ).first()
    if not pet_ok:
        raise HTTPException(status_code=404, detail="Pet não encontrado neste tenant")

    user_id = getattr(user, "id", None)
    if user_id is None and isinstance(user, dict):
        user_id = user.get("id")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Usuário inválido para registrar vacina")

    v = VacinaRegistro(
        pet_id=body.pet_id,
        consulta_id=body.consulta_id,
        veterinario_id=body.veterinario_id,
        user_id=user_id,
        tenant_id=tenant_id,
        protocolo_id=body.protocolo_id,
        nome_vacina=body.nome_vacina,
        fabricante=body.fabricante,
        lote=body.lote,
        data_aplicacao=body.data_aplicacao,
        data_proxima_dose=body.data_proxima_dose,
        numero_dose=body.numero_dose,
        via_administracao=body.via_administracao,
        observacoes=body.observacoes,
    )
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


@router.get("/vacinas/vencendo")
def vacinas_vencendo(
    dias: int = 30,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    """Lista vacinas que vencem nos próximos N dias."""
    user, tenant_id = _get_tenant(current)
    from datetime import timedelta
    limite = date.today() + timedelta(days=dias)
    vacinas = (
        db.query(VacinaRegistro)
        .filter(
            VacinaRegistro.tenant_id == tenant_id,
            VacinaRegistro.data_proxima_dose != None,  # noqa
            VacinaRegistro.data_proxima_dose <= limite,
            VacinaRegistro.data_proxima_dose >= date.today(),
        )
        .order_by(VacinaRegistro.data_proxima_dose)
        .all()
    )
    result = []
    for v in vacinas:
        result.append({
            "id": v.id,
            "pet_id": v.pet_id,
            "pet_nome": v.pet.nome if v.pet else None,
            "nome_vacina": v.nome_vacina,
            "data_proxima_dose": v.data_proxima_dose,
            "dias_restantes": (v.data_proxima_dose - date.today()).days,
        })
    return result


# ═══════════════════════════════════════════════════════════════
# EXAMES
# ═══════════════════════════════════════════════════════════════

class ExameCreate(BaseModel):
    pet_id: int
    consulta_id: Optional[int] = None
    tipo: str = "laboratorial"
    nome: str
    data_solicitacao: Optional[date] = None
    laboratorio: Optional[str] = None
    observacoes: Optional[str] = None


class ExameUpdate(BaseModel):
    data_resultado: Optional[date] = None
    status: Optional[str] = None
    resultado_texto: Optional[str] = None
    resultado_json: Optional[dict] = None
    interpretacao: Optional[str] = None
    interpretacao_ia: Optional[str] = None
    interpretacao_ia_resumo: Optional[str] = None
    interpretacao_ia_confianca: Optional[float] = None
    interpretacao_ia_alertas: Optional[list] = None
    interpretacao_ia_payload: Optional[dict] = None
    arquivo_url: Optional[str] = None
    arquivo_nome: Optional[str] = None
    observacoes: Optional[str] = None


class ExameResponse(BaseModel):
    id: int
    pet_id: int
    consulta_id: Optional[int]
    tipo: str
    nome: str
    data_solicitacao: Optional[date]
    data_resultado: Optional[date]
    status: str
    laboratorio: Optional[str]
    resultado_texto: Optional[str]
    resultado_json: Optional[dict]
    interpretacao: Optional[str]
    interpretacao_ia: Optional[str]
    interpretacao_ia_resumo: Optional[str]
    interpretacao_ia_confianca: Optional[float]
    interpretacao_ia_alertas: Optional[list]
    interpretacao_ia_payload: Optional[dict]
    arquivo_url: Optional[str]
    arquivo_nome: Optional[str]
    observacoes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/pets/{pet_id}/exames", response_model=List[ExameResponse])
def listar_exames_pet(
    pet_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    exames = db.query(ExameVet).filter(
        ExameVet.pet_id == pet_id,
        ExameVet.tenant_id == tenant_id,
    ).order_by(ExameVet.data_solicitacao.desc()).all()
    return exames


@router.get("/exames", summary="Lista exames com arquivo anexado")
def listar_exames_anexados(
    periodo: str = Query("hoje", description="hoje | semana | periodo"),
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    tutor: Optional[str] = Query(None),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)

    periodo = (periodo or "hoje").strip().lower()
    hoje = date.today()

    if periodo == "hoje":
        inicio_ref = hoje
        fim_ref = hoje
    elif periodo == "semana":
        inicio_ref = hoje - timedelta(days=6)
        fim_ref = hoje
    elif periodo == "periodo":
        if not data_inicio or not data_fim:
            raise HTTPException(422, "Informe data_inicio e data_fim para o período personalizado.")
        inicio_ref = data_inicio
        fim_ref = data_fim
    else:
        raise HTTPException(422, "Período inválido. Use: hoje, semana ou periodo.")

    data_ref_expr = func.date(func.coalesce(ExameVet.data_resultado, ExameVet.created_at))

    q = (
        db.query(ExameVet)
        .join(Pet, Pet.id == ExameVet.pet_id)
        .outerjoin(Cliente, Cliente.id == Pet.cliente_id)
        .filter(
            ExameVet.tenant_id == tenant_id,
            ExameVet.arquivo_url.isnot(None),
            ExameVet.arquivo_url != "",
            data_ref_expr >= inicio_ref,
            data_ref_expr <= fim_ref,
        )
    )

    if tutor and tutor.strip():
        termo = f"%{tutor.strip()}%"
        q = q.filter(Cliente.nome.ilike(termo))

    exames = q.order_by(data_ref_expr.desc(), ExameVet.id.desc()).all()

    items = []
    for exame in exames:
        data_upload = exame.data_resultado
        if not data_upload and exame.created_at:
            data_upload = exame.created_at.date()

        pet = exame.pet
        tutor_nome = pet.cliente.nome if pet and pet.cliente else None

        items.append({
            "exame_id": exame.id,
            "pet_id": exame.pet_id,
            "pet_nome": pet.nome if pet else None,
            "tutor_nome": tutor_nome,
            "nome_exame": exame.nome,
            "tipo": exame.tipo,
            "status": exame.status,
            "data_upload": data_upload.isoformat() if data_upload else None,
            "arquivo_nome": exame.arquivo_nome,
            "arquivo_url": exame.arquivo_url,
            "tem_interpretacao_ia": bool(exame.interpretacao_ia),
        })

    return {
        "items": items,
        "total": len(items),
        "periodo": periodo,
        "data_inicio": inicio_ref.isoformat(),
        "data_fim": fim_ref.isoformat(),
    }


@router.post("/exames", response_model=ExameResponse, status_code=201)
def criar_exame(
    body: ExameCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    e = ExameVet(
        tenant_id=tenant_id,
        pet_id=body.pet_id,
        consulta_id=body.consulta_id,
        user_id=user.id,
        tipo=body.tipo,
        nome=body.nome,
        data_solicitacao=body.data_solicitacao or date.today(),
        laboratorio=body.laboratorio,
        observacoes=body.observacoes,
        status="solicitado",
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


@router.patch("/exames/{exame_id}", response_model=ExameResponse)
def atualizar_exame(
    exame_id: int,
    body: ExameUpdate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    e = db.query(ExameVet).filter(ExameVet.id == exame_id, ExameVet.tenant_id == tenant_id).first()
    if not e:
        raise HTTPException(404, "Exame não encontrado")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(e, field, value)
    if body.data_resultado and e.status == "solicitado":
        e.status = "disponivel"
    db.commit()
    db.refresh(e)
    return e


@router.post("/exames/{exame_id}/interpretar-ia", response_model=ExameResponse)
def interpretar_exame_ia(
    exame_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    exame = db.query(ExameVet).filter(
        ExameVet.id == exame_id,
        ExameVet.tenant_id == tenant_id,
    ).first()
    if not exame:
        raise HTTPException(404, "Exame não encontrado")
    if not exame.resultado_texto and not exame.resultado_json:
        raise HTTPException(400, "O exame ainda não possui resultado para interpretar")

    analise = _gerar_interpretacao_exame(exame)
    exame.interpretacao_ia = analise["conclusao"]
    exame.interpretacao_ia_resumo = analise["resumo"]
    exame.interpretacao_ia_confianca = analise["confianca"]
    exame.interpretacao_ia_alertas = analise["alertas"]
    exame.interpretacao_ia_payload = analise["payload"]
    if exame.status in {"disponivel", "aguardando", "coletado", "solicitado"}:
        exame.status = "interpretado"
    db.commit()
    db.refresh(exame)
    return exame


@router.post("/exames/{exame_id}/arquivo", response_model=ExameResponse)
def upload_arquivo_exame(
    exame_id: int,
    arquivo: UploadFile = File(...),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    exame = db.query(ExameVet).filter(
        ExameVet.id == exame_id,
        ExameVet.tenant_id == tenant_id,
    ).first()
    if not exame:
        raise HTTPException(404, "Exame não encontrado")

    nome_original = (arquivo.filename or "resultado").strip()
    extensao = Path(nome_original).suffix.lower()
    extensoes_permitidas = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}
    if extensao not in extensoes_permitidas:
        raise HTTPException(400, "Formato inválido. Envie PDF ou imagem.")

    conteudo = arquivo.file.read()
    if not conteudo:
        raise HTTPException(400, "Arquivo vazio.")

    pasta_tenant = UPLOADS_DIR / str(tenant_id)
    pasta_tenant.mkdir(parents=True, exist_ok=True)

    nome_seguro = re.sub(r"[^a-zA-Z0-9_.-]", "_", Path(nome_original).stem).strip("_") or "resultado"
    nome_arquivo = f"exame_{exame.id}_{secrets.token_hex(4)}_{nome_seguro}{extensao}"
    caminho_arquivo = pasta_tenant / nome_arquivo

    with open(caminho_arquivo, "wb") as file_handle:
        file_handle.write(conteudo)

    exame.arquivo_nome = nome_original
    exame.arquivo_url = f"/uploads/veterinario/exames/{tenant_id}/{nome_arquivo}"
    if not exame.data_resultado:
        exame.data_resultado = date.today()
    if exame.status == "solicitado":
        exame.status = "disponivel"
    db.commit()
    db.refresh(exame)
    return exame


# ═══════════════════════════════════════════════════════════════
# PESO — curva de peso do pet
# ═══════════════════════════════════════════════════════════════

@router.get("/pets/{pet_id}/peso")
def curva_peso(
    pet_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    registros = db.query(PesoRegistro).filter(
        PesoRegistro.pet_id == pet_id,
        PesoRegistro.tenant_id == tenant_id,
    ).order_by(PesoRegistro.data).all()
    return [{"data": r.data, "peso_kg": r.peso_kg, "consulta_id": r.consulta_id} for r in registros]


@router.post("/pets/{pet_id}/peso", status_code=201)
def registrar_peso(
    pet_id: int,
    peso_kg: float = Query(..., gt=0),
    observacoes: Optional[str] = None,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    r = PesoRegistro(
        pet_id=pet_id,
        user_id=user.id,
        data=date.today(),
        peso_kg=peso_kg,
        observacoes=observacoes,
    )
    db.add(r)
    # Atualiza peso principal do pet
    pet = db.query(Pet).filter(Pet.id == pet_id).first()
    if pet:
        pet.peso = peso_kg
    db.commit()
    return {"ok": True, "peso_kg": peso_kg}


# ═══════════════════════════════════════════════════════════════
# PROCEDIMENTOS
# ═══════════════════════════════════════════════════════════════

class ProcedimentoCreate(BaseModel):
    consulta_id: int
    catalogo_id: Optional[int] = None
    nome: str
    descricao: Optional[str] = None
    valor: Optional[float] = None
    realizado: bool = True
    observacoes: Optional[str] = None
    insumos: list[dict] = Field(default_factory=list)
    baixar_estoque: bool = True


class ProcedimentoResponse(BaseModel):
    id: int
    consulta_id: int
    catalogo_id: Optional[int]
    nome: str
    descricao: Optional[str]
    valor: Optional[float]
    valor_cobrado: float = 0
    realizado: bool
    observacoes: Optional[str]
    insumos: list[dict] = Field(default_factory=list)
    custo_total: float = 0
    margem_valor: float = 0
    margem_percentual: float = 0
    modo_operacional: str = "funcionario"
    comissao_empresa_pct: float = 0
    repasse_empresa_valor: float = 0
    receita_tenant_valor: float = 0
    entrada_empresa_valor: float = 0
    estoque_baixado: bool = False
    estoque_movimentacao_ids: list[int] = Field(default_factory=list)
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/consultas/{consulta_id}/procedimentos", response_model=List[ProcedimentoResponse])
def listar_procedimentos_consulta(
    consulta_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    procedimentos = db.query(ProcedimentoConsulta).filter(
        ProcedimentoConsulta.consulta_id == consulta_id,
        ProcedimentoConsulta.tenant_id == tenant_id,
    ).order_by(ProcedimentoConsulta.created_at.desc()).all()
    return [_serializar_procedimento(procedimento, db, tenant_id) for procedimento in procedimentos]


@router.post("/procedimentos", response_model=ProcedimentoResponse, status_code=201)
def adicionar_procedimento(
    body: ProcedimentoCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    catalogo = None
    if body.catalogo_id:
        catalogo = db.query(CatalogoProcedimento).filter(
            CatalogoProcedimento.id == body.catalogo_id,
            CatalogoProcedimento.tenant_id == tenant_id,
        ).first()
        if not catalogo:
            raise HTTPException(status_code=404, detail="Procedimento de catálogo não encontrado")

    insumos = _normalizar_insumos(body.insumos or [])
    if not insumos and catalogo and isinstance(catalogo.insumos, list):
        insumos = _normalizar_insumos(catalogo.insumos)
    insumos = _enriquecer_insumos_com_custos(db, tenant_id, insumos)

    p = ProcedimentoConsulta(
        tenant_id=tenant_id,
        consulta_id=body.consulta_id,
        catalogo_id=body.catalogo_id,
        user_id=user.id,
        nome=body.nome or (catalogo.nome if catalogo else "Procedimento"),
        descricao=body.descricao if body.descricao is not None else (catalogo.descricao if catalogo else None),
        valor=body.valor if body.valor is not None else (float(catalogo.valor_padrao) if catalogo and catalogo.valor_padrao is not None else None),
        realizado=body.realizado,
        observacoes=body.observacoes,
        insumos=insumos,
    )
    db.add(p)
    db.flush()
    if body.baixar_estoque:
        _aplicar_baixa_estoque_procedimento(db, p, tenant_id, user.id)
    _sincronizar_financeiro_procedimento(db, p, tenant_id, user.id)
    db.commit()
    db.refresh(p)
    return _serializar_procedimento(p, db, tenant_id)


# ═══════════════════════════════════════════════════════════════
# CATÁLOGO DE PROCEDIMENTOS
# ═══════════════════════════════════════════════════════════════

class CatalogoCreate(BaseModel):
    nome: str
    descricao: Optional[str] = None
    categoria: Optional[str] = None
    valor_padrao: Optional[float] = None
    duracao_minutos: Optional[int] = None
    requer_anestesia: bool = False
    observacoes: Optional[str] = None
    insumos: list[dict] = Field(default_factory=list)


class CatalogoResponse(BaseModel):
    id: int
    nome: str
    descricao: Optional[str]
    categoria: Optional[str]
    valor_padrao: Optional[float]
    duracao_minutos: Optional[int]
    requer_anestesia: bool
    observacoes: Optional[str]
    insumos: list[dict] = Field(default_factory=list)
    custo_estimado: float = 0
    margem_estimada: float = 0
    margem_percentual_estimada: float = 0
    modo_operacional: str = "funcionario"
    comissao_empresa_pct: float = 0
    repasse_empresa_estimado: float = 0
    receita_tenant_estimada: float = 0
    ativo: bool

    class Config:
        from_attributes = True


@router.get("/catalogo/procedimentos", response_model=List[CatalogoResponse])
def listar_catalogo_procedimentos(
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    catalogos = db.query(CatalogoProcedimento).filter(
        CatalogoProcedimento.tenant_id == tenant_id,
        CatalogoProcedimento.ativo == True,  # noqa
    ).order_by(CatalogoProcedimento.nome).all()
    return [_serializar_catalogo(catalogo, db, tenant_id) for catalogo in catalogos]


@router.post("/catalogo/procedimentos", response_model=CatalogoResponse, status_code=201)
def criar_catalogo_procedimento(
    body: CatalogoCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    p = CatalogoProcedimento(
        tenant_id=tenant_id,
        nome=body.nome,
        descricao=body.descricao,
        categoria=body.categoria,
        valor_padrao=body.valor_padrao,
        duracao_minutos=body.duracao_minutos,
        requer_anestesia=body.requer_anestesia,
        observacoes=body.observacoes,
        insumos=_normalizar_insumos(body.insumos),
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return _serializar_catalogo(p, db, tenant_id)


@router.get("/catalogo/produtos-estoque")
def listar_produtos_estoque(
    busca: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    q = db.query(Produto).filter(
        Produto.tenant_id == str(tenant_id),
        Produto.ativo == True,
        Produto.situacao == True,
    )
    if busca:
        termo = f"%{busca}%"
        q = q.filter(or_(Produto.nome.ilike(termo), Produto.codigo.ilike(termo)))
    produtos = q.order_by(Produto.nome).limit(limit).all()
    return [
        {
            "id": produto.id,
            "codigo": produto.codigo,
            "nome": produto.nome,
            "unidade": produto.unidade,
            "estoque_atual": float(produto.estoque_atual or 0),
            "preco_custo": _round_money(produto.preco_custo),
        }
        for produto in produtos
    ]


@router.get("/pets/{pet_id}/alertas")
def listar_alertas_pet(
    pet_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    pet = _pet_or_404(db, pet_id, tenant_id)
    return {
        "pet_id": pet.id,
        "alertas": _montar_alertas_pet(db, pet, tenant_id),
        "status_vacinal": _status_vacinal_pet(db, pet, tenant_id),
    }


@router.get("/pets/{pet_id}/carteirinha")
def obter_carteirinha_pet(
    pet_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    pet = _pet_or_404(db, pet_id, tenant_id)
    status_vacinal = _status_vacinal_pet(db, pet, tenant_id)
    exames = db.query(ExameVet).filter(
        ExameVet.pet_id == pet.id,
        ExameVet.tenant_id == tenant_id,
    ).order_by(ExameVet.created_at.desc()).limit(10).all()
    consultas = db.query(ConsultaVet).filter(
        ConsultaVet.pet_id == pet.id,
        ConsultaVet.tenant_id == tenant_id,
    ).order_by(ConsultaVet.created_at.desc()).limit(10).all()

    return {
        "pet": {
            "id": pet.id,
            "nome": pet.nome,
            "especie": pet.especie,
            "raca": pet.raca,
            "peso": float(pet.peso) if pet.peso is not None else None,
            "foto_url": pet.foto_url,
            "tipo_sanguineo": getattr(pet, "tipo_sanguineo", None),
            "alergias": getattr(pet, "alergias_lista", None) or ([pet.alergias] if pet.alergias else []),
            "restricoes_alimentares": getattr(pet, "restricoes_alimentares_lista", None) or [],
            "medicamentos_continuos": getattr(pet, "medicamentos_continuos_lista", None) or [],
            "condicoes_cronicas": getattr(pet, "condicoes_cronicas_lista", None) or [],
        },
        "alertas": _montar_alertas_pet(db, pet, tenant_id),
        "status_vacinal": status_vacinal,
        "consultas": [
            {
                "id": consulta.id,
                "data": consulta.created_at.date().isoformat() if consulta.created_at else None,
                "tipo": consulta.tipo,
                "status": consulta.status,
                "diagnostico": consulta.diagnostico,
                "observacoes_tutor": consulta.observacoes_tutor,
            }
            for consulta in consultas
        ],
        "exames": [
            {
                "id": exame.id,
                "nome": exame.nome,
                "tipo": exame.tipo,
                "status": exame.status,
                "data_resultado": exame.data_resultado.isoformat() if exame.data_resultado else None,
                "interpretacao_ia_resumo": exame.interpretacao_ia_resumo,
                "arquivo_url": exame.arquivo_url,
            }
            for exame in exames
        ],
    }


# ═══════════════════════════════════════════════════════════════
# CATÁLOGO DE MEDICAMENTOS
# ═══════════════════════════════════════════════════════════════

class MedicamentoCreate(BaseModel):
    nome: str
    nome_comercial: Optional[str] = None
    principio_ativo: Optional[str] = None
    fabricante: Optional[str] = None
    forma_farmaceutica: Optional[str] = None
    concentracao: Optional[str] = None
    especies_indicadas: Optional[list] = None
    indicacoes: Optional[str] = None
    contraindicacoes: Optional[str] = None
    interacoes: Optional[str] = None
    posologia_referencia: Optional[str] = None
    dose_min_mgkg: Optional[float] = None
    dose_max_mgkg: Optional[float] = None
    eh_antibiotico: bool = False
    eh_controlado: bool = False
    observacoes: Optional[str] = None


@router.get("/catalogo/medicamentos")
def listar_medicamentos(
    busca: Optional[str] = None,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    q = db.query(MedicamentoCatalogo).filter(
        MedicamentoCatalogo.tenant_id == tenant_id,
        MedicamentoCatalogo.ativo == True,  # noqa
    )
    if busca:
        termo = f"%{busca}%"
        q = q.filter(
            or_(
                MedicamentoCatalogo.nome.ilike(termo),
                MedicamentoCatalogo.principio_ativo.ilike(termo),
                MedicamentoCatalogo.nome_comercial.ilike(termo),
            )
        )
    return q.order_by(MedicamentoCatalogo.nome).limit(50).all()


@router.post("/catalogo/medicamentos", status_code=201)
def criar_medicamento(
    body: MedicamentoCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    m = MedicamentoCatalogo(**body.model_dump())
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


# ═══════════════════════════════════════════════════════════════
# PROTOCOLOS DE VACINAS
# ═══════════════════════════════════════════════════════════════

@router.get("/catalogo/protocolos-vacinas")
def listar_protocolos_vacinas(
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    return db.query(ProtocoloVacina).filter(
        ProtocoloVacina.tenant_id == tenant_id,
        ProtocoloVacina.ativo == True,  # noqa
    ).order_by(ProtocoloVacina.nome).all()


@router.post("/catalogo/protocolos-vacinas", status_code=201)
def criar_protocolo_vacina(
    nome: str,
    especie: Optional[str] = None,
    reforco_anual: bool = True,
    numero_doses_serie: int = 1,
    intervalo_doses_dias: Optional[int] = None,
    observacoes: Optional[str] = None,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    p = ProtocoloVacina(
        nome=nome,
        especie=especie,
        reforco_anual=reforco_anual,
        numero_doses_serie=numero_doses_serie,
        intervalo_doses_dias=intervalo_doses_dias,
        observacoes=observacoes,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


# ═══════════════════════════════════════════════════════════════
# INTERNAÇÃO
# ═══════════════════════════════════════════════════════════════

class InternacaoCreate(BaseModel):
    pet_id: int
    consulta_id: Optional[int] = None
    veterinario_id: Optional[int] = None
    motivo: Optional[str] = None
    motivo_internacao: Optional[str] = None
    box: Optional[str] = None
    baia_numero: Optional[str] = None
    data_entrada: Optional[datetime] = None


class EvolucaoCreate(BaseModel):
    temperatura: Optional[float] = None
    frequencia_cardiaca: Optional[int] = None
    frequencia_respiratoria: Optional[int] = None
    # Compatibilidade com payload antigo do frontend
    freq_cardiaca: Optional[int] = None
    freq_respiratoria: Optional[int] = None
    nivel_dor: Optional[int] = None
    pressao_sistolica: Optional[int] = None
    glicemia: Optional[float] = None
    peso: Optional[float] = None
    observacoes: Optional[str] = None


class ProcedimentoInternacaoCreate(BaseModel):
    horario_agendado: Optional[datetime] = None
    medicamento: str
    dose: Optional[str] = None
    via: Optional[str] = None
    observacoes_agenda: Optional[str] = None
    executado_por: Optional[str] = None
    horario_execucao: Optional[datetime] = None
    observacao_execucao: Optional[str] = None
    status: Optional[str] = "concluido"


@router.get("/internacoes")
def listar_internacoes(
    status: Optional[str] = "internado",
    pet_id: Optional[int] = None,
    cliente_id: Optional[int] = None,
    data_saida_inicio: Optional[date] = Query(None),
    data_saida_fim: Optional[date] = Query(None),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)

    # Compatibilidade: telas antigas enviavam "ativa" para status de internação aberta.
    status_map = {
        "ativa": "internado",
    }
    status_normalizado = status_map.get(status, status)

    # Fallback defensivo: em alguns fluxos o tenant pode vir no usuário e não no retorno do Depends.
    if tenant_id is None:
        tenant_id = getattr(user, "tenant_id", None)
    if tenant_id is None and isinstance(user, dict):
        tenant_id = user.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=401, detail="Tenant não identificado para listar internações")

    q = db.query(InternacaoVet).filter(InternacaoVet.tenant_id == tenant_id)
    if status_normalizado:
        q = q.filter(InternacaoVet.status == status_normalizado)
    if pet_id:
        q = q.filter(InternacaoVet.pet_id == pet_id)
    if cliente_id:
        q = q.filter(InternacaoVet.pet.has(Pet.cliente_id == cliente_id))
    if data_saida_inicio:
        q = q.filter(func.date(InternacaoVet.data_saida) >= data_saida_inicio)
    if data_saida_fim:
        q = q.filter(func.date(InternacaoVet.data_saida) <= data_saida_fim)

    internacoes = q.order_by(InternacaoVet.data_entrada.desc()).all()
    result = []
    for i in internacoes:
        motivo_limpo, box = _split_motivo_baia(i.motivo)
        tutor = i.pet.cliente if i.pet and i.pet.cliente else None
        result.append({
            "id": i.id,
            "pet_id": i.pet_id,
            "pet_nome": i.pet.nome if i.pet else None,
            "tutor_id": tutor.id if tutor else None,
            "tutor_nome": tutor.nome if tutor else None,
            "motivo": motivo_limpo,
            "box": box,
            "status": i.status,
            "data_entrada": i.data_entrada,
            "data_saida": i.data_saida,
            "observacoes_alta": i.observacoes,
        })
    return result


@router.get("/internacoes/{internacao_id}")
def obter_internacao(
    internacao_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)

    i = db.query(InternacaoVet).filter(InternacaoVet.id == internacao_id).first()
    if not i:
        raise HTTPException(404, "Internação não encontrada")

    if tenant_id is not None and i.tenant_id is not None and i.tenant_id != tenant_id:
        raise HTTPException(404, "Internação não encontrada")

    evolucoes = (
        db.query(EvolucaoInternacao)
        .filter(EvolucaoInternacao.internacao_id == internacao_id)
        .order_by(EvolucaoInternacao.data_hora.desc())
        .all()
    )

    motivo_limpo, box = _split_motivo_baia(i.motivo)

    evolucoes_formatadas, procedimentos_formatados = _separar_evolucoes_e_procedimentos(evolucoes)

    return {
        "id": i.id,
        "pet_id": i.pet_id,
        "pet_nome": i.pet.nome if i.pet else None,
        "tutor_id": i.pet.cliente.id if i.pet and i.pet.cliente else None,
        "tutor_nome": i.pet.cliente.nome if i.pet and i.pet.cliente else None,
        "motivo": motivo_limpo,
        "box": box,
        "status": i.status,
        "data_entrada": i.data_entrada,
        "data_saida": i.data_saida,
        "observacoes_alta": i.observacoes,
        "evolucoes": evolucoes_formatadas,
        "procedimentos": procedimentos_formatados,
    }


@router.get("/pets/{pet_id}/internacoes-historico")
def obter_historico_internacoes_pet(
    pet_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)

    if tenant_id is None:
        tenant_id = getattr(user, "tenant_id", None)
    if tenant_id is None and isinstance(user, dict):
        tenant_id = user.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=401, detail="Tenant não identificado")

    pet = db.query(Pet).filter(Pet.id == pet_id, Pet.tenant_id == tenant_id).first()
    if not pet:
        raise HTTPException(404, "Pet não encontrado")

    internacoes = (
        db.query(InternacaoVet)
        .filter(InternacaoVet.pet_id == pet_id, InternacaoVet.tenant_id == tenant_id)
        .order_by(InternacaoVet.data_entrada.desc())
        .all()
    )

    historico = []
    for internacao in internacoes:
        motivo_limpo, box = _split_motivo_baia(internacao.motivo)
        registros = (
            db.query(EvolucaoInternacao)
            .filter(EvolucaoInternacao.internacao_id == internacao.id)
            .order_by(EvolucaoInternacao.data_hora.desc())
            .all()
        )
        evols, procs = _separar_evolucoes_e_procedimentos(registros)

        historico.append({
            "internacao_id": internacao.id,
            "status": internacao.status,
            "motivo": motivo_limpo,
            "box": box,
            "data_entrada": internacao.data_entrada,
            "data_saida": internacao.data_saida,
            "observacoes_alta": internacao.observacoes,
            "evolucoes": evols,
            "procedimentos": procs,
        })

    return {
        "pet_id": pet.id,
        "pet_nome": pet.nome,
        "historico": historico,
    }


@router.post("/internacoes", status_code=201)
def criar_internacao(
    body: InternacaoCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)

    motivo = (body.motivo or body.motivo_internacao or "").strip()
    box = (body.box or body.baia_numero or "").strip()
    box_normalizado = _normalizar_baia(box)
    if not motivo:
        raise HTTPException(status_code=422, detail="Campo 'motivo' é obrigatório")

    if tenant_id is None:
        pet_ref = db.query(Pet).filter(Pet.id == body.pet_id).first()
        if not pet_ref or not pet_ref.tenant_id:
            raise HTTPException(status_code=400, detail="Pet inválido para internação")
        tenant_id = pet_ref.tenant_id

    pet_ok = db.query(Pet).filter(
        Pet.id == body.pet_id,
        Pet.tenant_id == tenant_id,
    ).first()
    if not pet_ok:
        raise HTTPException(status_code=404, detail="Pet não encontrado neste tenant")

    if box_normalizado:
        internacoes_ativas = (
            db.query(InternacaoVet)
            .filter(
                InternacaoVet.tenant_id == tenant_id,
                InternacaoVet.status == "internado",
            )
            .all()
        )
        for internacao_ativa in internacoes_ativas:
            _, box_ocupado = _split_motivo_baia(internacao_ativa.motivo)
            if _normalizar_baia(box_ocupado) == box_normalizado:
                raise HTTPException(
                    status_code=409,
                    detail=f"A baia {box} já está ocupada por outro internado.",
                )

    user_id = getattr(user, "id", None)
    if user_id is None and isinstance(user, dict):
        user_id = user.get("id")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Usuário inválido para internação")

    i = InternacaoVet(
        pet_id=body.pet_id,
        consulta_id=body.consulta_id,
        veterinario_id=body.veterinario_id,
        user_id=user_id,
        tenant_id=tenant_id,
        motivo=_pack_motivo_baia(motivo, box),
        data_entrada=body.data_entrada or datetime.now(),
        status="internado",
    )
    db.add(i)
    db.commit()
    db.refresh(i)
    return {"id": i.id, "status": i.status, "data_entrada": i.data_entrada}


@router.post("/internacoes/{internacao_id}/evolucao", status_code=201)
def registrar_evolucao(
    internacao_id: int,
    body: EvolucaoCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)

    i = db.query(InternacaoVet).filter(InternacaoVet.id == internacao_id).first()
    if not i:
        raise HTTPException(404, "Internação não encontrada")

    # Se o tenant veio no contexto, valida acesso. Se não veio, usa o tenant da internação.
    if tenant_id is not None and i.tenant_id is not None and i.tenant_id != tenant_id:
        raise HTTPException(404, "Internação não encontrada")

    tenant_id_evolucao = i.tenant_id or tenant_id
    if tenant_id_evolucao is None:
        raise HTTPException(status_code=422, detail="Tenant não identificado para registrar evolução")

    user_id = getattr(user, "id", None)
    if user_id is None and isinstance(user, dict):
        user_id = user.get("id")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Usuário inválido para registrar evolução")

    dados = body.model_dump(exclude_unset=True)
    # Compatibilidade de nomes de campos vindos de versões antigas da tela.
    if dados.get("frequencia_cardiaca") is None and body.freq_cardiaca is not None:
        dados["frequencia_cardiaca"] = body.freq_cardiaca
    if dados.get("frequencia_respiratoria") is None and body.freq_respiratoria is not None:
        dados["frequencia_respiratoria"] = body.freq_respiratoria
    dados.pop("freq_cardiaca", None)
    dados.pop("freq_respiratoria", None)

    ev = EvolucaoInternacao(
        internacao_id=internacao_id,
        user_id=user_id,
        tenant_id=tenant_id_evolucao,
        **dados,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev


@router.post("/internacoes/{internacao_id}/procedimento", status_code=201)
def registrar_procedimento_internacao(
    internacao_id: int,
    body: ProcedimentoInternacaoCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)

    i = db.query(InternacaoVet).filter(InternacaoVet.id == internacao_id).first()
    if not i:
        raise HTTPException(404, "Internação não encontrada")

    if tenant_id is not None and i.tenant_id is not None and i.tenant_id != tenant_id:
        raise HTTPException(404, "Internação não encontrada")

    tenant_id_registro = i.tenant_id or tenant_id
    if tenant_id_registro is None:
        raise HTTPException(status_code=422, detail="Tenant não identificado para registrar procedimento")

    user_id = getattr(user, "id", None)
    if user_id is None and isinstance(user, dict):
        user_id = user.get("id")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Usuário inválido para registrar procedimento")

    status_procedimento = (body.status or "concluido").strip().lower()
    if status_procedimento not in {"agendado", "concluido"}:
        raise HTTPException(status_code=422, detail="Status do procedimento inválido. Use 'agendado' ou 'concluido'.")

    if status_procedimento == "concluido":
        if not (body.executado_por or "").strip():
            raise HTTPException(status_code=422, detail="Campo 'executado_por' é obrigatório para procedimento concluído")
        if not body.horario_execucao:
            raise HTTPException(status_code=422, detail="Campo 'horario_execucao' é obrigatório para procedimento concluído")

    data_referencia = body.horario_agendado or body.horario_execucao or datetime.now()

    payload = {
        "status": status_procedimento,
        "horario_agendado": body.horario_agendado.isoformat() if body.horario_agendado else None,
        "medicamento": body.medicamento,
        "dose": body.dose,
        "via": body.via,
        "observacoes_agenda": body.observacoes_agenda,
        "executado_por": (body.executado_por or "").strip() or None,
        "horario_execucao": body.horario_execucao.isoformat() if body.horario_execucao else None,
        "observacao_execucao": body.observacao_execucao,
    }

    ev = EvolucaoInternacao(
        internacao_id=internacao_id,
        user_id=user_id,
        tenant_id=tenant_id_registro,
        data_hora=data_referencia,
        observacoes=_build_procedimento_observacao(payload),
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)

    return {
        "id": ev.id,
        "data_hora": ev.data_hora,
        "status": status_procedimento,
        **payload,
    }


@router.patch("/internacoes/{internacao_id}/alta")
def dar_alta(
    internacao_id: int,
    observacoes: Optional[str] = None,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    i = db.query(InternacaoVet).filter(
        InternacaoVet.id == internacao_id,
        InternacaoVet.tenant_id == tenant_id,
    ).first()
    if not i:
        raise HTTPException(404, "Internação não encontrada")
    i.status = "alta"
    i.data_saida = datetime.now()
    if observacoes:
        i.observacoes = observacoes
    db.commit()
    return {"ok": True, "status": "alta", "data_saida": i.data_saida}


# ═══════════════════════════════════════════════════════════════
# PERFIL COMPORTAMENTAL
# ═══════════════════════════════════════════════════════════════

class PerfilComportamentalIn(BaseModel):
    temperamento: Optional[str] = None
    reacao_animais: Optional[str] = None
    reacao_pessoas: Optional[str] = None
    medo_secador: Optional[str] = None
    medo_tesoura: Optional[str] = None
    aceita_focinheira: Optional[str] = None
    comportamento_carro: Optional[str] = None
    observacoes: Optional[str] = None


@router.get("/pets/{pet_id}/perfil-comportamental")
def obter_perfil_comportamental(
    pet_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    perfil = db.query(PerfilComportamental).filter(
        PerfilComportamental.pet_id == pet_id,
        PerfilComportamental.tenant_id == tenant_id,
    ).first()
    return perfil or {}


@router.put("/pets/{pet_id}/perfil-comportamental")
def salvar_perfil_comportamental(
    pet_id: int,
    body: PerfilComportamentalIn,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    perfil = db.query(PerfilComportamental).filter(
        PerfilComportamental.pet_id == pet_id,
        PerfilComportamental.tenant_id == tenant_id,
    ).first()

    if perfil:
        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(perfil, field, value)
    else:
        perfil = PerfilComportamental(
            pet_id=pet_id,
            user_id=user.id,
            **body.model_dump(),
        )
        db.add(perfil)

    db.commit()
    db.refresh(perfil)
    return perfil


# ═══════════════════════════════════════════════════════════════
# DASHBOARD VETERINÁRIO
# ═══════════════════════════════════════════════════════════════

@router.get("/dashboard")
def dashboard_vet(
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    """Resumo do dia para o dashboard veterinário."""
    _, tenant_id = _get_tenant(current)
    hoje = date.today()
    janela_30d = hoje - timedelta(days=30)

    agendamentos_hoje = db.query(func.count(AgendamentoVet.id)).filter(
        AgendamentoVet.tenant_id == tenant_id,
        func.date(AgendamentoVet.data_hora) == hoje,
    ).scalar() or 0

    consultas_hoje = db.query(func.count(ConsultaVet.id)).filter(
        ConsultaVet.tenant_id == tenant_id,
        func.date(ConsultaVet.created_at) == hoje,
    ).scalar() or 0

    em_atendimento = db.query(func.count(ConsultaVet.id)).filter(
        ConsultaVet.tenant_id == tenant_id,
        ConsultaVet.status == "em_andamento",
    ).scalar() or 0

    internados = db.query(func.count(InternacaoVet.id)).filter(
        InternacaoVet.tenant_id == tenant_id,
        InternacaoVet.status == "internado",
    ).scalar() or 0

    vacinas_vencendo_30d = db.query(func.count(VacinaRegistro.id)).filter(
        VacinaRegistro.tenant_id == tenant_id,
        VacinaRegistro.data_proxima_dose != None,  # noqa
        VacinaRegistro.data_proxima_dose >= hoje,
        VacinaRegistro.data_proxima_dose <= hoje + timedelta(days=30),
    ).scalar() or 0

    consultas_mes = db.query(func.count(ConsultaVet.id)).filter(
        ConsultaVet.tenant_id == tenant_id,
        func.extract("month", ConsultaVet.created_at) == hoje.month,
        func.extract("year", ConsultaVet.created_at) == hoje.year,
    ).scalar() or 0

    consultas_com_retorno_vencido = db.query(ConsultaVet).filter(
        ConsultaVet.tenant_id == tenant_id,
        ConsultaVet.data_retorno.isnot(None),
        ConsultaVet.data_retorno < hoje,
        ConsultaVet.status == "finalizada",
    ).all()

    retornos_pendentes = 0
    for consulta_base in consultas_com_retorno_vencido:
        existe_retorno = db.query(ConsultaVet.id).filter(
            ConsultaVet.tenant_id == tenant_id,
            ConsultaVet.pet_id == consulta_base.pet_id,
            ConsultaVet.tipo == "retorno",
            ConsultaVet.status != "cancelada",
            func.date(ConsultaVet.created_at) >= consulta_base.data_retorno,
        ).first()
        if not existe_retorno:
            retornos_pendentes += 1

    consultas_30d = db.query(ConsultaVet).filter(
        ConsultaVet.tenant_id == tenant_id,
        func.date(ConsultaVet.created_at) >= janela_30d,
    ).all()

    total_30d = len(consultas_30d)
    retornos_30d = sum(1 for c in consultas_30d if (c.tipo or "").strip().lower() == "retorno")
    taxa_retorno_30d = round((retornos_30d / total_30d) * 100, 1) if total_30d else 0.0

    duracoes_min = []
    for consulta in consultas_30d:
        if consulta.inicio_atendimento and consulta.fim_atendimento:
            delta = consulta.fim_atendimento - consulta.inicio_atendimento
            duracoes_min.append(max(delta.total_seconds() / 60.0, 0))

    tempo_medio_atendimento_min = round(sum(duracoes_min) / len(duracoes_min), 1) if duracoes_min else 0.0
    procedimentos_30d = db.query(ProcedimentoConsulta).join(
        ConsultaVet, ConsultaVet.id == ProcedimentoConsulta.consulta_id
    ).filter(
        ProcedimentoConsulta.tenant_id == tenant_id,
        ProcedimentoConsulta.realizado == True,
        func.date(ConsultaVet.created_at) >= janela_30d,
    ).all()
    regra_financeira = _obter_regra_financeira_veterinaria(db, tenant_id)
    financeiro_30d = [_resumo_financeiro_procedimento(procedimento.valor, procedimento.insumos, regra_financeira) for procedimento in procedimentos_30d]
    faturamento_procedimentos_30d = _round_money(sum(item["valor_cobrado"] for item in financeiro_30d))
    custo_procedimentos_30d = _round_money(sum(item["custo_total"] for item in financeiro_30d))
    margem_procedimentos_30d = _round_money(sum(item["margem_valor"] for item in financeiro_30d))
    margem_percentual_procedimentos_30d = round((margem_procedimentos_30d / faturamento_procedimentos_30d) * 100, 2) if faturamento_procedimentos_30d > 0 else 0.0
    repasse_empresa_procedimentos_30d = _round_money(sum(item["repasse_empresa_valor"] for item in financeiro_30d))
    receita_tenant_procedimentos_30d = _round_money(sum(item["receita_tenant_valor"] for item in financeiro_30d))
    entrada_empresa_procedimentos_30d = _round_money(sum(item["entrada_empresa_valor"] for item in financeiro_30d))

    return {
        "consultas_hoje": consultas_hoje,
        "agendamentos_hoje": agendamentos_hoje,
        "em_atendimento": em_atendimento,
        "internados": internados,
        "vacinas_vencendo_30d": vacinas_vencendo_30d,
        "consultas_mes": consultas_mes,
        "retornos_pendentes": retornos_pendentes,
        "total_consultas_30d": total_30d,
        "retornos_30d": retornos_30d,
        "taxa_retorno_30d": taxa_retorno_30d,
        "tempo_medio_atendimento_min": tempo_medio_atendimento_min,
        "modelo_operacional_financeiro": regra_financeira["modo_operacional"],
        "comissao_empresa_pct_padrao": regra_financeira["comissao_empresa_pct"],
        "faturamento_procedimentos_30d": faturamento_procedimentos_30d,
        "custo_procedimentos_30d": custo_procedimentos_30d,
        "margem_procedimentos_30d": margem_procedimentos_30d,
        "margem_percentual_procedimentos_30d": margem_percentual_procedimentos_30d,
        "repasse_empresa_procedimentos_30d": repasse_empresa_procedimentos_30d,
        "receita_tenant_procedimentos_30d": receita_tenant_procedimentos_30d,
        "entrada_empresa_procedimentos_30d": entrada_empresa_procedimentos_30d,
    }


@router.get("/relatorios/clinicos")
def relatorio_clinico_vet(
    dias: int = Query(default=30, ge=7, le=365),
    top: int = Query(default=5, ge=3, le=15),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    data_inicio = date.today() - timedelta(days=dias)

    consultas = db.query(ConsultaVet).filter(
        ConsultaVet.tenant_id == tenant_id,
        func.date(ConsultaVet.created_at) >= data_inicio,
    ).all()

    total_consultas = len(consultas)
    consultas_finalizadas = sum(1 for c in consultas if (c.status or "").strip().lower() == "finalizada")

    diagnosticos_count = {}
    for consulta in consultas:
        diagnostico = (consulta.diagnostico or "").strip()
        if not diagnostico:
            continue
        chave = diagnostico.split("\n")[0].split(";")[0].strip()
        if not chave:
            continue
        diagnosticos_count[chave] = diagnosticos_count.get(chave, 0) + 1

    top_diagnosticos = [
        {"nome": nome, "quantidade": qtd}
        for nome, qtd in sorted(diagnosticos_count.items(), key=lambda item: item[1], reverse=True)[:top]
    ]

    procedimentos_periodo = db.query(ProcedimentoConsulta).join(
        ConsultaVet, ConsultaVet.id == ProcedimentoConsulta.consulta_id
    ).filter(
        ProcedimentoConsulta.tenant_id == tenant_id,
        ProcedimentoConsulta.realizado == True,
        func.date(ConsultaVet.created_at) >= data_inicio,
    ).all()

    procedimentos_resumo = {}
    total_procedimentos_valor = 0.0
    total_procedimentos_custo = 0.0
    total_procedimentos_margem = 0.0
    total_repasse_empresa = 0.0
    total_receita_tenant = 0.0
    total_entrada_empresa = 0.0
    regra_financeira = _obter_regra_financeira_veterinaria(db, tenant_id)
    for procedimento in procedimentos_periodo:
        resumo = _resumo_financeiro_procedimento(procedimento.valor, procedimento.insumos, regra_financeira)
        chave = (procedimento.nome or "Procedimento").strip() or "Procedimento"
        item = procedimentos_resumo.setdefault(chave, {
            "nome": chave,
            "quantidade": 0,
            "valor_total": 0.0,
            "custo_total": 0.0,
            "margem_total": 0.0,
            "repasse_empresa_total": 0.0,
            "receita_tenant_total": 0.0,
            "entrada_empresa_total": 0.0,
        })
        item["quantidade"] += 1
        item["valor_total"] += resumo["valor_cobrado"]
        item["custo_total"] += resumo["custo_total"]
        item["margem_total"] += resumo["margem_valor"]
        item["repasse_empresa_total"] += resumo["repasse_empresa_valor"]
        item["receita_tenant_total"] += resumo["receita_tenant_valor"]
        item["entrada_empresa_total"] += resumo["entrada_empresa_valor"]
        total_procedimentos_valor += resumo["valor_cobrado"]
        total_procedimentos_custo += resumo["custo_total"]
        total_procedimentos_margem += resumo["margem_valor"]
        total_repasse_empresa += resumo["repasse_empresa_valor"]
        total_receita_tenant += resumo["receita_tenant_valor"]
        total_entrada_empresa += resumo["entrada_empresa_valor"]

    top_procedimentos = [
        {
            "nome": item["nome"],
            "quantidade": int(item["quantidade"]),
            "valor_total": _round_money(item["valor_total"]),
            "custo_total": _round_money(item["custo_total"]),
            "margem_total": _round_money(item["margem_total"]),
            "repasse_empresa_total": _round_money(item["repasse_empresa_total"]),
            "receita_tenant_total": _round_money(item["receita_tenant_total"]),
            "entrada_empresa_total": _round_money(item["entrada_empresa_total"]),
            "margem_percentual": round((item["margem_total"] / item["valor_total"]) * 100, 2) if item["valor_total"] > 0 else 0.0,
        }
        for item in sorted(
            procedimentos_resumo.values(),
            key=lambda item: (item["quantidade"], item["valor_total"]),
            reverse=True,
        )[:top]
    ]

    top_medicamentos_db = (
        db.query(
            ItemPrescricao.nome_medicamento.label("nome"),
            func.count(ItemPrescricao.id).label("quantidade"),
        )
        .join(PrescricaoVet, PrescricaoVet.id == ItemPrescricao.prescricao_id)
        .filter(
            PrescricaoVet.tenant_id == tenant_id,
            func.date(PrescricaoVet.created_at) >= data_inicio,
        )
        .group_by(ItemPrescricao.nome_medicamento)
        .order_by(func.count(ItemPrescricao.id).desc())
        .limit(top)
        .all()
    )

    return {
        "periodo_dias": dias,
        "consultas": {
            "total": total_consultas,
            "finalizadas": consultas_finalizadas,
            "em_andamento": max(total_consultas - consultas_finalizadas, 0),
        },
        "financeiro_procedimentos": {
            "modo_operacional": regra_financeira["modo_operacional"],
            "comissao_empresa_pct": regra_financeira["comissao_empresa_pct"],
            "faturamento_total": _round_money(total_procedimentos_valor),
            "custo_total": _round_money(total_procedimentos_custo),
            "margem_total": _round_money(total_procedimentos_margem),
            "repasse_empresa_total": _round_money(total_repasse_empresa),
            "receita_tenant_total": _round_money(total_receita_tenant),
            "entrada_empresa_total": _round_money(total_entrada_empresa),
            "margem_percentual": round((total_procedimentos_margem / total_procedimentos_valor) * 100, 2) if total_procedimentos_valor > 0 else 0.0,
        },
        "top_diagnosticos": [
            {"nome": item["nome"], "quantidade": int(item["quantidade"])}
            for item in top_diagnosticos
        ],
        "top_procedimentos": top_procedimentos,
        "top_medicamentos": [
            {"nome": item.nome, "quantidade": int(item.quantidade)}
            for item in top_medicamentos_db
        ],
    }


@router.get("/relatorios/clinicos/export.csv")
def exportar_relatorio_clinico_csv(
    dias: int = Query(default=30, ge=7, le=365),
    top: int = Query(default=5, ge=3, le=15),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    dados = relatorio_clinico_vet(dias=dias, top=top, db=db, current=current)
    conteudo = []
    conteudo.append(["Relatório clínico veterinário"])
    conteudo.append(["Período (dias)", str(dados["periodo_dias"])])
    conteudo.append(["Consultas totais", str(dados["consultas"]["total"])])
    conteudo.append(["Consultas finalizadas", str(dados["consultas"]["finalizadas"])])
    conteudo.append(["Consultas em andamento", str(dados["consultas"]["em_andamento"])])
    conteudo.append(["Faturamento procedimentos", f"{dados['financeiro_procedimentos']['faturamento_total']:.2f}"])
    conteudo.append(["Custo procedimentos", f"{dados['financeiro_procedimentos']['custo_total']:.2f}"])
    conteudo.append(["Margem procedimentos", f"{dados['financeiro_procedimentos']['margem_total']:.2f}"])
    conteudo.append(["Margem % procedimentos", f"{dados['financeiro_procedimentos']['margem_percentual']:.2f}"])
    conteudo.append(["Modo operacional", dados["financeiro_procedimentos"]["modo_operacional"]])
    conteudo.append(["Comissão empresa %", f"{dados['financeiro_procedimentos']['comissao_empresa_pct']:.2f}"])
    conteudo.append(["Entrada empresa", f"{dados['financeiro_procedimentos']['entrada_empresa_total']:.2f}"])
    conteudo.append(["Repasse empresa", f"{dados['financeiro_procedimentos']['repasse_empresa_total']:.2f}"])
    conteudo.append(["Receita líquida vet", f"{dados['financeiro_procedimentos']['receita_tenant_total']:.2f}"])
    conteudo.append([])
    conteudo.append(["Top diagnósticos"])
    conteudo.append(["Nome", "Quantidade"])
    for item in dados["top_diagnosticos"]:
        conteudo.append([item["nome"], str(item["quantidade"])])
    conteudo.append([])
    conteudo.append(["Top procedimentos"])
    conteudo.append(["Nome", "Quantidade", "Faturamento", "Custo", "Margem", "Entrada empresa", "Repasse empresa", "Líquido vet", "Margem %"])
    for item in dados["top_procedimentos"]:
        conteudo.append([
            item["nome"],
            str(item["quantidade"]),
            f"{item['valor_total']:.2f}",
            f"{item['custo_total']:.2f}",
            f"{item['margem_total']:.2f}",
            f"{item['entrada_empresa_total']:.2f}",
            f"{item['repasse_empresa_total']:.2f}",
            f"{item['receita_tenant_total']:.2f}",
            f"{item['margem_percentual']:.2f}",
        ])
    conteudo.append([])
    conteudo.append(["Top medicamentos"])
    conteudo.append(["Nome", "Quantidade"])
    for item in dados["top_medicamentos"]:
        conteudo.append([item["nome"], str(item["quantidade"])])

    sio = StringIO()
    writer = csv.writer(sio, delimiter=';')
    writer.writerows(conteudo)
    csv_string = "\ufeff" + sio.getvalue()

    return Response(
        content=csv_string,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename=relatorio_clinico_vet_{dias}d.csv"},
    )


@router.get("/consultas/{consulta_id}/assinatura")
def validar_assinatura_consulta(
    consulta_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    c = _consulta_or_404(db, consulta_id, tenant_id)

    if not c.finalizado_em or not c.hash_prontuario:
        return {
            "assinada": False,
            "hash_valido": False,
            "hash_prontuario": c.hash_prontuario,
            "hash_recalculado": None,
            "finalizado_em": c.finalizado_em,
            "motivo": "Consulta ainda não foi finalizada e assinada digitalmente.",
        }

    hash_recalculado = _hash_prontuario_consulta(c)
    return {
        "assinada": True,
        "hash_valido": hash_recalculado == c.hash_prontuario,
        "hash_prontuario": c.hash_prontuario,
        "hash_recalculado": hash_recalculado,
        "finalizado_em": c.finalizado_em,
        "motivo": "OK" if hash_recalculado == c.hash_prontuario else "Hash divergente: possível alteração após finalização.",
    }


@router.get("/consultas/{consulta_id}/prontuario.pdf")
def baixar_prontuario_pdf(
    consulta_id: int,
    request: Request,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    c = (
        db.query(ConsultaVet)
        .options(
            joinedload(ConsultaVet.pet),
            joinedload(ConsultaVet.cliente),
            joinedload(ConsultaVet.veterinario),
            joinedload(ConsultaVet.prescricoes).joinedload(PrescricaoVet.itens),
        )
        .filter(ConsultaVet.id == consulta_id, ConsultaVet.tenant_id == tenant_id)
        .first()
    )
    if not c:
        raise HTTPException(status_code=404, detail="Consulta não encontrada")
    if c.status != "finalizada":
        raise HTTPException(status_code=400, detail="A consulta precisa estar finalizada para gerar o prontuário em PDF")

    hash_recalculado = _hash_prontuario_consulta(c)
    validacao = {
        "assinada": bool(c.finalizado_em and c.hash_prontuario),
        "hash_valido": hash_recalculado == c.hash_prontuario,
        "hash_prontuario": c.hash_prontuario,
    }
    url_validacao = f"{str(request.base_url).rstrip('/')}/vet/consultas/{consulta_id}/assinatura"
    pdf_buffer = gerar_pdf_prontuario(c, validacao, c.prescricoes or [], url_validacao)

    filename = f"prontuario_consulta_{consulta_id}.pdf"
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/prescricoes/{prescricao_id}/pdf")
def baixar_prescricao_pdf(
    prescricao_id: int,
    request: Request,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    p = _prescricao_or_404(db, prescricao_id, tenant_id)
    url_validacao = f"{str(request.base_url).rstrip('/')}/vet/consultas/{p.consulta_id}/assinatura"
    pdf_buffer = gerar_pdf_receita(p, url_validacao)

    numero = (p.numero or f"prescricao_{p.id}").replace("/", "-")
    filename = f"{numero}.pdf"
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ═══════════════════════════════════════════════════════════════
# PARCEIRO VETERINÁRIO (MULTI-TENANT)
# ═══════════════════════════════════════════════════════════════


class PartnerLinkCreate(BaseModel):
    vet_tenant_id: str  # UUID do tenant do veterinário parceiro
    tipo_relacao: str = "parceiro"  # 'parceiro' | 'funcionario'
    comissao_empresa_pct: Optional[float] = None


class PartnerLinkUpdate(BaseModel):
    tipo_relacao: Optional[str] = None
    comissao_empresa_pct: Optional[float] = None
    ativo: Optional[bool] = None


class PartnerLinkResponse(BaseModel):
    id: int
    empresa_tenant_id: str
    vet_tenant_id: str
    tipo_relacao: str
    comissao_empresa_pct: Optional[float]
    ativo: bool
    criado_em: datetime
    # campos extras enriquecidos
    vet_tenant_nome: Optional[str] = None
    empresa_tenant_nome: Optional[str] = None

    class Config:
        from_attributes = True


@router.get("/parceiros", response_model=List[PartnerLinkResponse], summary="Lista parcerias do tenant atual")
def listar_parceiros(
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    """Retorna todos os vínculos de parceria em que o tenant atual é a empresa (loja)."""
    user, tenant_id = _get_tenant(current)
    links = db.query(VetPartnerLink).filter(
        VetPartnerLink.empresa_tenant_id == str(tenant_id),
    ).all()

    result = []
    for link in links:
        vet_tenant = db.query(Tenant).filter(Tenant.id == str(link.vet_tenant_id)).first()
        result.append(
            PartnerLinkResponse(
                id=link.id,
                empresa_tenant_id=str(link.empresa_tenant_id),
                vet_tenant_id=str(link.vet_tenant_id),
                tipo_relacao=link.tipo_relacao,
                comissao_empresa_pct=float(link.comissao_empresa_pct) if link.comissao_empresa_pct else None,
                ativo=link.ativo,
                criado_em=link.criado_em,
                vet_tenant_nome=vet_tenant.name if vet_tenant else None,
            )
        )
    return result


@router.post("/parceiros", response_model=PartnerLinkResponse, status_code=201, summary="Cria vínculo com veterinário parceiro")
def criar_parceiro(
    payload: PartnerLinkCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    """Cria um vínculo de parceria entre o tenant atual (loja) e um tenant veterinário."""
    user, tenant_id = _get_tenant(current)

    # Verifica se o tenant de destino existe
    vet_tenant = db.query(Tenant).filter(Tenant.id == payload.vet_tenant_id).first()
    if not vet_tenant:
        raise HTTPException(status_code=404, detail="Tenant do veterinário não encontrado.")

    # Impede vínculo consigo mesmo
    if str(payload.vet_tenant_id) == str(tenant_id):
        raise HTTPException(status_code=400, detail="O tenant parceiro não pode ser o mesmo tenant atual.")

    # Impede duplicata
    existente = db.query(VetPartnerLink).filter(
        VetPartnerLink.empresa_tenant_id == str(tenant_id),
        VetPartnerLink.vet_tenant_id == payload.vet_tenant_id,
    ).first()
    if existente:
        raise HTTPException(status_code=409, detail="Já existe um vínculo com este veterinário parceiro.")

    link = VetPartnerLink(
        empresa_tenant_id=str(tenant_id),
        vet_tenant_id=payload.vet_tenant_id,
        tipo_relacao=payload.tipo_relacao,
        comissao_empresa_pct=payload.comissao_empresa_pct,
        ativo=True,
    )
    db.add(link)
    db.commit()
    db.refresh(link)

    return PartnerLinkResponse(
        id=link.id,
        empresa_tenant_id=str(link.empresa_tenant_id),
        vet_tenant_id=str(link.vet_tenant_id),
        tipo_relacao=link.tipo_relacao,
        comissao_empresa_pct=float(link.comissao_empresa_pct) if link.comissao_empresa_pct else None,
        ativo=link.ativo,
        criado_em=link.criado_em,
        vet_tenant_nome=vet_tenant.name,
    )


@router.patch("/parceiros/{link_id}", response_model=PartnerLinkResponse, summary="Atualiza vínculo de parceria")
def atualizar_parceiro(
    link_id: int,
    payload: PartnerLinkUpdate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    link = db.query(VetPartnerLink).filter(
        VetPartnerLink.id == link_id,
        VetPartnerLink.empresa_tenant_id == str(tenant_id),
    ).first()
    if not link:
        raise HTTPException(status_code=404, detail="Vínculo de parceria não encontrado.")

    if payload.tipo_relacao is not None:
        link.tipo_relacao = payload.tipo_relacao
    if payload.comissao_empresa_pct is not None:
        link.comissao_empresa_pct = payload.comissao_empresa_pct
    if payload.ativo is not None:
        link.ativo = payload.ativo

    db.commit()
    db.refresh(link)

    vet_tenant = db.query(Tenant).filter(Tenant.id == str(link.vet_tenant_id)).first()
    return PartnerLinkResponse(
        id=link.id,
        empresa_tenant_id=str(link.empresa_tenant_id),
        vet_tenant_id=str(link.vet_tenant_id),
        tipo_relacao=link.tipo_relacao,
        comissao_empresa_pct=float(link.comissao_empresa_pct) if link.comissao_empresa_pct else None,
        ativo=link.ativo,
        criado_em=link.criado_em,
        vet_tenant_nome=vet_tenant.name if vet_tenant else None,
    )


@router.delete("/parceiros/{link_id}", status_code=204, summary="Remove vínculo de parceria")
def remover_parceiro(
    link_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    link = db.query(VetPartnerLink).filter(
        VetPartnerLink.id == link_id,
        VetPartnerLink.empresa_tenant_id == str(tenant_id),
    ).first()
    if not link:
        raise HTTPException(status_code=404, detail="Vínculo de parceria não encontrado.")
    db.delete(link)
    db.commit()


@router.get("/tenants-veterinarios", summary="Lista tenants com tipo veterinary_clinic")
def listar_tenants_veterinarios(
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    """Lista tenants que podem ser vinculados como parceiros (veterinary_clinic)."""
    _get_tenant(current)
    tenants = db.query(Tenant).filter(
        Tenant.organization_type == "veterinary_clinic",
        Tenant.status == "active",
    ).all()
    return [{"id": str(t.id), "nome": t.name, "cnpj": t.cnpj} for t in tenants]


# ═══════════════════════════════════════════════════════════════
# RELATÓRIO DE REPASSE — fechamento operacional parceiro
# ═══════════════════════════════════════════════════════════════

@router.get("/relatorios/repasse", summary="Relatório de repasse veterinário por período")
def relatorio_repasse(
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    """
    Lista todas as contas a receber geradas por procedimentos veterinários
    (documento começando com VET-PROC-), filtrando por período e status.
    Útil para fechar o repasse com o veterinário parceiro.
    """
    user, tenant_id = _get_tenant(current)

    query = db.query(ContaReceber).filter(
        ContaReceber.tenant_id == str(tenant_id),
        ContaReceber.documento.like("VET-PROC-%"),
    )

    if data_inicio:
        query = query.filter(ContaReceber.data_emissao >= data_inicio)
    if data_fim:
        query = query.filter(ContaReceber.data_emissao <= data_fim)
    if status:
        query = query.filter(ContaReceber.status == status)

    contas = query.order_by(ContaReceber.data_emissao.desc()).all()

    items = []
    total_valor = 0.0
    total_recebido = 0.0
    total_pendente = 0.0

    for c in contas:
        tipo = "repasse_empresa" if "-REPASSE-EMPRESA" in (c.documento or "") else "liquido_vet"
        valor = float(c.valor_final or 0)
        recebido = float(c.valor_recebido or 0)
        pendente = valor - recebido if c.status != "recebido" else 0.0

        total_valor += valor
        total_recebido += recebido if c.status == "recebido" else 0.0
        total_pendente += pendente

        items.append({
            "id": c.id,
            "documento": c.documento,
            "descricao": c.descricao,
            "tipo": tipo,
            "valor": valor,
            "valor_recebido": recebido,
            "data_emissao": c.data_emissao.isoformat() if c.data_emissao else None,
            "data_vencimento": c.data_vencimento.isoformat() if c.data_vencimento else None,
            "data_recebimento": c.data_recebimento.isoformat() if c.data_recebimento else None,
            "status": c.status,
            "observacoes": c.observacoes,
        })

    return {
        "items": items,
        "total_valor": _round_money(total_valor),
        "total_recebido": _round_money(total_recebido),
        "total_pendente": _round_money(total_pendente),
        "quantidade": len(items),
    }


@router.post("/relatorios/repasse/{conta_id}/baixar", summary="Dá baixa (recebimento) em um lançamento de repasse")
def baixar_repasse(
    conta_id: int,
    data_recebimento: Optional[date] = Query(None),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    """
    Marca um lançamento de repasse veterinário como recebido.
    Atualiza status='recebido', valor_recebido=valor_final e data_recebimento.
    """
    user, tenant_id = _get_tenant(current)

    conta = db.query(ContaReceber).filter(
        ContaReceber.id == conta_id,
        ContaReceber.tenant_id == str(tenant_id),
        ContaReceber.documento.like("VET-PROC-%"),
    ).first()

    if not conta:
        raise HTTPException(404, "Lançamento de repasse não encontrado.")
    if conta.status == "recebido":
        raise HTTPException(400, "Este lançamento já foi baixado.")

    conta.status = "recebido"
    conta.valor_recebido = conta.valor_final
    conta.data_recebimento = data_recebimento or date.today()
    db.commit()

    return {
        "ok": True,
        "id": conta.id,
        "status": conta.status,
        "data_recebimento": conta.data_recebimento.isoformat(),
        "valor_recebido": float(conta.valor_recebido),
    }


# ═══════════════════════════════════════════════════════════════
# CHAT IA — interpretação clínica conversacional de exames
# ═══════════════════════════════════════════════════════════════

class ExameChatPayload(BaseModel):
    pergunta: str


class VetAssistenteIAPayload(BaseModel):
    mensagem: str
    modo: str = "livre"  # livre | atendimento
    conversa_id: Optional[int] = None
    salvar_historico: bool = True
    pet_id: Optional[int] = None
    consulta_id: Optional[int] = None
    exame_id: Optional[int] = None
    medicamento_1: Optional[str] = None
    medicamento_2: Optional[str] = None
    peso_kg: Optional[float] = None
    especie: Optional[str] = None


class VetMensagemFeedbackPayload(BaseModel):
    util: bool
    nota: Optional[int] = Field(default=None, ge=1, le=5)
    comentario: Optional[str] = None


def _normalizar_texto(v: Optional[str]) -> str:
    return (v or "").strip().lower()


def _detectar_medicamentos_no_texto(texto: str, meds: list[MedicamentoCatalogo]) -> list[MedicamentoCatalogo]:
    encontrados: list[MedicamentoCatalogo] = []
    for med in meds:
        nome = _normalizar_texto(med.nome)
        nome_comercial = _normalizar_texto(med.nome_comercial)
        principio = _normalizar_texto(med.principio_ativo)
        if (nome and nome in texto) or (nome_comercial and nome_comercial in texto) or (principio and principio in texto):
            encontrados.append(med)
        if len(encontrados) >= 2:
            break
    return encontrados


def _normalizar_modo_ia(modo: Optional[str]) -> str:
    modo_limpo = (modo or "livre").strip().lower()
    return modo_limpo if modo_limpo in ["livre", "atendimento"] else "livre"


def _garantir_tabelas_memoria_ia(db: Session) -> dict:
    """
    Garante que as tabelas de memória usadas pela IA existam.
    Evita falha silenciosa de histórico em ambientes sem migração aplicada.
    """
    bind = db.get_bind()
    insp = inspect(bind)
    criadas = []

    if not insp.has_table("conversas_ia"):
        Conversa.__table__.create(bind=bind, checkfirst=True)
        criadas.append("conversas_ia")

    if not insp.has_table("mensagens_chat"):
        MensagemChat.__table__.create(bind=bind, checkfirst=True)
        criadas.append("mensagens_chat")

    return {"ok": True, "criadas": criadas}


def _carregar_memoria_conversa(db: Session, tenant_id, conversa_id: int, limite: int = 8) -> list[MensagemChat]:
    return db.query(MensagemChat).filter(
        MensagemChat.tenant_id == str(tenant_id),
        MensagemChat.conversa_id == conversa_id,
    ).order_by(MensagemChat.id.desc()).limit(limite).all()[::-1]


def _obter_ou_criar_conversa_vet(
    db: Session,
    tenant_id,
    user_id: int,
    payload: VetAssistenteIAPayload,
    pet: Optional[Pet],
    consulta: Optional[ConsultaVet],
    exame: Optional[ExameVet],
) -> Conversa:
    if payload.conversa_id:
        conversa = db.query(Conversa).filter(
            Conversa.id == payload.conversa_id,
            Conversa.tenant_id == str(tenant_id),
            Conversa.usuario_id == user_id,
        ).first()
        if conversa:
            return conversa

    modo = _normalizar_modo_ia(payload.modo)
    if pet:
        titulo = f"Vet {modo} - {pet.nome}"
    elif consulta:
        titulo = f"Vet {modo} - Consulta {consulta.id}"
    elif exame:
        titulo = f"Vet {modo} - Exame {exame.id}"
    else:
        titulo = f"Vet {modo} - {datetime.now().strftime('%d/%m %H:%M')}"

    conversa = Conversa(
        tenant_id=str(tenant_id),
        usuario_id=user_id,
        titulo=titulo,
        finalizada=False,
    )
    db.add(conversa)
    db.flush()
    return conversa


def _resumo_contexto_clinico(
    pet: Optional[Pet],
    consulta: Optional[ConsultaVet],
    exame: Optional[ExameVet],
) -> str:
    blocos = []
    if pet:
        blocos.append(
            f"Paciente: {pet.nome} | espécie: {pet.especie or 'não informada'} | raça: {pet.raca or 'n/i'}"
        )
    if consulta:
        blocos.append(
            "Consulta atual: "
            f"queixa={consulta.queixa_principal or 'n/i'}; "
            f"história={consulta.historia_clinica or 'n/i'}; "
            f"exame físico={consulta.exame_fisico or 'n/i'}; "
            f"diagnóstico={consulta.diagnostico or consulta.hipotese_diagnostica or 'n/i'}"
        )
    if exame:
        data_ref = exame.data_resultado.isoformat() if exame.data_resultado else "n/i"
        blocos.append(
            "Exame selecionado: "
            f"{exame.nome or exame.tipo} | data={data_ref} | "
            f"resumo ia={exame.interpretacao_ia_resumo or 'n/i'}"
        )
    return "\n".join(blocos).strip()


def _montar_resposta_dose(
    mensagem: str,
    meds: list[MedicamentoCatalogo],
    peso_kg: Optional[float],
    especie: Optional[str],
) -> Optional[str]:
    texto = _normalizar_texto(mensagem)
    if not any(k in texto for k in ["dose", "dosagem", "mg/kg", "posologia"]):
        return None

    if not peso_kg or peso_kg <= 0:
        return "Para calcular dose com segurança, informe o peso atual do pet em kg."

    if not especie:
        return "Para cálculo de dose com segurança, informe também a espécie do pet (cão, gato, etc.)."

    med_match = None
    for med in meds:
        nome = _normalizar_texto(med.nome)
        nome_comercial = _normalizar_texto(med.nome_comercial)
        principio = _normalizar_texto(med.principio_ativo)
        if (nome and nome in texto) or (nome_comercial and nome_comercial in texto) or (principio and principio in texto):
            med_match = med
            break

    if not med_match:
        return "Não identifiquei o medicamento na pergunta. Informe o nome (ou princípio ativo) para calcular a dose."

    dose_min = med_match.dose_min_mgkg
    dose_max = med_match.dose_max_mgkg
    if dose_min is None and dose_max is None:
        return (
            f"Encontrei {med_match.nome}, mas ele não tem dose mg/kg cadastrada no catálogo. "
            "Verifique a bula/protocolo antes de prescrever."
        )

    dose_ref = dose_min if dose_min is not None else dose_max
    dose_max_ref = dose_max if dose_max is not None else dose_min

    total_min = float(dose_ref) * float(peso_kg)
    total_max = float(dose_max_ref) * float(peso_kg)
    total_media = (total_min + total_max) / 2

    if abs(total_min - total_max) < 1e-9:
        faixa = f"{total_min:.2f} mg"
        faixa_mgkg = f"{dose_ref:.2f} mg/kg"
    else:
        faixa = f"{total_min:.2f} mg a {total_max:.2f} mg"
        faixa_mgkg = f"{dose_ref:.2f} a {dose_max_ref:.2f} mg/kg"

    return (
        f"Dose de referência para {med_match.nome} (peso {peso_kg:.2f} kg): {faixa_mgkg}. "
        f"Total estimado: {faixa} (média {total_media:.2f} mg). "
        "Confirme frequência, via e duração conforme bula e condição clínica. "
        "Se houver comorbidade renal/hepática, considere ajuste de dose."
    )


def _montar_resposta_interacao(
    mensagem: str,
    meds: list[MedicamentoCatalogo],
    medicamento_1: Optional[str],
    medicamento_2: Optional[str],
) -> Optional[str]:
    texto = _normalizar_texto(mensagem)
    if not any(k in texto for k in ["associar", "junto", "intera", "combinar", "pode usar com"]):
        return None

    med_a = None
    med_b = None
    m1 = _normalizar_texto(medicamento_1)
    m2 = _normalizar_texto(medicamento_2)

    if m1 and m2:
        for med in meds:
            nome = _normalizar_texto(med.nome)
            nome_comercial = _normalizar_texto(med.nome_comercial)
            principio = _normalizar_texto(med.principio_ativo)
            if not med_a and (m1 == nome or m1 == nome_comercial or m1 == principio or m1 in nome):
                med_a = med
            if not med_b and (m2 == nome or m2 == nome_comercial or m2 == principio or m2 in nome):
                med_b = med
    else:
        encontrados = _detectar_medicamentos_no_texto(texto, meds)
        if len(encontrados) >= 2:
            med_a, med_b = encontrados[0], encontrados[1]

    if not med_a or not med_b:
        return "Para avaliar associação medicamentosa, informe dois medicamentos (nome ou princípio ativo)."

    principio_a = _normalizar_texto(med_a.principio_ativo)
    principio_b = _normalizar_texto(med_b.principio_ativo)

    if principio_a and principio_b and principio_a == principio_b:
        return (
            f"Atenção: {med_a.nome} e {med_b.nome} parecem ter o mesmo princípio ativo ({med_a.principio_ativo}). "
            "Há risco de duplicidade terapêutica e aumento de efeitos adversos."
        )

    riscos = []
    texto_interacoes = f"{_normalizar_texto(med_a.interacoes)} {_normalizar_texto(med_b.interacoes)}"
    if principio_a and principio_a in texto_interacoes:
        riscos.append(f"{med_b.nome} cita interação relevante com o princípio {med_a.principio_ativo}.")
    if principio_b and principio_b in texto_interacoes:
        riscos.append(f"{med_a.nome} cita interação relevante com o princípio {med_b.principio_ativo}.")

    if riscos:
        return (
            f"Associação {med_a.nome} + {med_b.nome}: encontrada possível interação em catálogo. "
            + " ".join(riscos)
            + " Avalie ajuste de dose, intervalo e monitoramento clínico."
        )

    return (
        f"Não encontrei alerta explícito de interação entre {med_a.nome} e {med_b.nome} no catálogo local. "
        "Mesmo assim, confirme em bula e considere função renal/hepática, idade e comorbidades antes de associar."
    )


def _montar_resposta_sintomas(mensagem: str, especie: Optional[str]) -> Optional[str]:
    texto = _normalizar_texto(mensagem)
    gatilhos = ["sintoma", "possibilidade", "diagnóstico", "hipótese", "o que olhar", "investigar"]
    if not any(k in texto for k in gatilhos):
        return None

    mapa = {
        "vomit": ["gastroenterite", "ingestão alimentar inadequada", "pancreatite", "corpo estranho"],
        "diarre": ["parasitoses", "gastroenterite", "disbiose", "doença inflamatória intestinal"],
        "tosse": ["traqueobronquite", "colapso de traqueia", "cardiopatia", "pneumonia"],
        "febre": ["processo infeccioso", "inflamação sistêmica", "doença transmitida por vetor"],
        "apat": ["dor", "infecção", "anemia", "distúrbio metabólico"],
        "prur": ["dermatite alérgica", "ectoparasitas", "infecção cutânea secundária"],
        "poliuria": ["doença renal", "diabetes mellitus", "hiperadrenocorticismo"],
        "convuls": ["epilepsia", "distúrbio metabólico", "intoxicação", "doença intracraniana"],
    }

    hipoteses = []
    for chave, possibilidades in mapa.items():
        if chave in texto:
            hipoteses.extend(possibilidades)

    if not hipoteses:
        hipoteses = [
            "processo infeccioso",
            "dor/condição inflamatória",
            "distúrbio metabólico/endócrino",
            "causa gastrointestinal",
        ]

    especie_txt = (especie or "não informada").strip()
    hipoteses_unicas = []
    for h in hipoteses:
        if h not in hipoteses_unicas:
            hipoteses_unicas.append(h)

    principais = ", ".join(hipoteses_unicas[:5])
    return (
        f"Pelas informações citadas ({especie_txt}), as principais hipóteses iniciais incluem: {principais}. "
        "Para fechar diagnóstico, recomendo revisar sinais vitais completos, dor, hidratação, evolução temporal, "
        "histórico medicamentoso e exames complementares dirigidos (hemograma, bioquímica e imagem conforme achados)."
    )


def _montar_resposta_plano_estruturado(
    mensagem: str,
    pet: Optional[Pet],
    consulta: Optional[ConsultaVet],
    exame: Optional[ExameVet],
) -> Optional[str]:
    texto = _normalizar_texto(mensagem)
    gatilhos = ["plano", "conduta", "fechar diagnóstico", "fechar diagnostico", "o que fazer agora"]
    if not any(k in texto for k in gatilhos):
        return None

    contexto = _resumo_contexto_clinico(pet, consulta, exame)
    if not contexto:
        return (
            "Plano sugerido (estrutura mínima):\n"
            "1) Estabilização e dor: confirmar sinais vitais e escala de dor.\n"
            "2) Diagnóstico direcionado: hemograma + bioquímica + exame complementar conforme sistema acometido.\n"
            "3) Terapêutica inicial: suporte e monitorização de resposta em 24-48h.\n"
            "4) Reavaliação: definir critério de melhora/piora e retorno programado."
        )

    return (
        "Plano clínico estruturado com base no contexto atual:\n"
        "1) Hipóteses priorizadas: usar queixa + exame físico + exame complementar para ranquear hipóteses.\n"
        "2) Exames de confirmação: escolher exames com maior impacto para diferenciar as principais hipóteses.\n"
        "3) Conduta imediata: suporte, analgesia e hidratação conforme estado clínico.\n"
        "4) Segurança medicamentosa: revisar dose por espécie/peso e risco de interação.\n"
        "5) Follow-up: registrar sinais de alarme e prazo de reavaliação.\n"
        f"Resumo de contexto utilizado:\n{contexto}"
    )


def _montar_prompt_vet_llm(
    mensagem: str,
    pet: Optional[Pet],
    consulta: Optional[ConsultaVet],
    exame: Optional[ExameVet],
    especie: Optional[str],
    peso_kg: Optional[float],
    meds: list[MedicamentoCatalogo],
    modo: Optional[str],
) -> tuple[str, str]:
    especie_txt = (especie or "não informada").strip()
    peso_txt = f"{float(peso_kg):.2f} kg" if peso_kg and peso_kg > 0 else "não informado"

    meds_preview = []
    for med in meds[:20]:
        partes = [med.nome]
        if med.principio_ativo:
            partes.append(f"princípio: {med.principio_ativo}")
        if med.dose_min_mgkg is not None or med.dose_max_mgkg is not None:
            dmin = med.dose_min_mgkg if med.dose_min_mgkg is not None else med.dose_max_mgkg
            dmax = med.dose_max_mgkg if med.dose_max_mgkg is not None else med.dose_min_mgkg
            partes.append(f"dose mg/kg: {dmin} a {dmax}")
        meds_preview.append(" | ".join(partes))

    contexto_clinico = _resumo_contexto_clinico(pet, consulta, exame) or "Sem contexto clínico detalhado."

    prompt_system = (
        "Você é um assistente clínico veterinário para apoio à decisão. "
        "Responda em português do Brasil, direto e claro. "
        "Não invente dados. Não substitua consulta veterinária. "
        "Sempre inclua orientação de segurança quando houver dose, interação medicamentosa ou risco clínico.\n\n"
        "REGRAS:\n"
        "1) Se faltar dado crítico (peso, espécie, medicamento), peça esse dado antes de concluir.\n"
        "2) Em dose, informe faixa e recomende confirmar bula/protocolo.\n"
        "3) Em interação, sinalize incerteza quando não houver dado explícito.\n"
        "4) Evite diagnóstico definitivo; forneça hipóteses e próximos passos.\n"
        "5) Seja objetivo (preferir até 8 linhas, exceto quando pedirem plano detalhado).\n\n"
        f"MODO: {_normalizar_modo_ia(modo)}\n"
        f"ESPÉCIE: {especie_txt}\n"
        f"PESO: {peso_txt}\n"
        f"CONTEXTO CLÍNICO:\n{contexto_clinico}\n\n"
        "CATÁLOGO RESUMIDO DE MEDICAMENTOS (amostra):\n"
        f"{chr(10).join(meds_preview) if meds_preview else 'Sem medicamentos ativos no catálogo.'}"
    )

    prompt_user = f"Pergunta do veterinário: {mensagem}"
    return prompt_system, prompt_user


def _tentar_resposta_llm_veterinaria(
    mensagem: str,
    memoria: list[MensagemChat],
    pet: Optional[Pet],
    consulta: Optional[ConsultaVet],
    exame: Optional[ExameVet],
    especie: Optional[str],
    peso_kg: Optional[float],
    meds: list[MedicamentoCatalogo],
    modo: Optional[str],
) -> tuple[Optional[str], Optional[str]]:
    groq_key = os.getenv("GROQ_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")

    if not (groq_key or openai_key or gemini_key):
        return None, None

    prompt_system, prompt_user = _montar_prompt_vet_llm(
        mensagem=mensagem,
        pet=pet,
        consulta=consulta,
        exame=exame,
        especie=especie,
        peso_kg=peso_kg,
        meds=meds,
        modo=modo,
    )

    mensagens = [{"role": "system", "content": prompt_system}]
    for m in memoria[-6:]:
        conteudo = (m.conteudo or "").strip()
        if not conteudo:
            continue
        role = "assistant" if m.tipo == "assistente" else "user"
        mensagens.append({"role": role, "content": conteudo[:3000]})
    mensagens.append({"role": "user", "content": prompt_user})

    try:
        if groq_key:
            from groq import Groq

            client_ia = Groq(api_key=groq_key)
            completion = client_ia.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=mensagens,
                temperature=0.2,
                max_tokens=600,
            )
            resposta = (completion.choices[0].message.content or "").strip()
            return (resposta or None), "groq:llama-3.3-70b-versatile"

        if openai_key:
            from openai import OpenAI

            client_ia = OpenAI(api_key=openai_key, timeout=25.0)
            completion = client_ia.chat.completions.create(
                model="gpt-4o-mini",
                messages=mensagens,
                temperature=0.2,
                max_tokens=600,
            )
            resposta = (completion.choices[0].message.content or "").strip()
            return (resposta or None), "openai:gpt-4o-mini"

        if gemini_key:
            import google.generativeai as genai

            genai.configure(api_key=gemini_key)
            model_ia = genai.GenerativeModel("gemini-1.5-flash")
            historico_txt = "\n".join(
                [f"{msg['role']}: {msg['content']}" for msg in mensagens if msg["role"] != "system"]
            )
            prompt_completo = f"{prompt_system}\n\n{historico_txt}"
            response = model_ia.generate_content(prompt_completo)
            resposta = (getattr(response, "text", "") or "").strip()
            return (resposta or None), "gemini:gemini-1.5-flash"

    except Exception:
        return None, None

    return None, None


@router.post("/ia/assistente", summary="Assistente IA veterinário (livre ou vinculado ao atendimento)")
def assistente_ia_veterinario(
    payload: VetAssistenteIAPayload,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)

    mensagem = (payload.mensagem or "").strip()
    if not mensagem:
        raise HTTPException(422, "Informe uma mensagem para o assistente.")

    pet = None
    consulta = None
    exame = None

    if payload.pet_id:
        pet = db.query(Pet).filter(Pet.id == payload.pet_id, Pet.tenant_id == tenant_id).first()

    if payload.consulta_id:
        consulta = db.query(ConsultaVet).filter(
            ConsultaVet.id == payload.consulta_id,
            ConsultaVet.tenant_id == tenant_id,
        ).first()
        if consulta and not pet:
            pet = db.query(Pet).filter(Pet.id == consulta.pet_id, Pet.tenant_id == tenant_id).first()

    if payload.exame_id:
        exame = db.query(ExameVet).filter(
            ExameVet.id == payload.exame_id,
            ExameVet.tenant_id == tenant_id,
        ).first()
        if exame and not pet:
            pet = db.query(Pet).filter(Pet.id == exame.pet_id, Pet.tenant_id == tenant_id).first()

    especie = payload.especie or (pet.especie if pet else None)
    peso_kg = payload.peso_kg
    if (not peso_kg or peso_kg <= 0) and pet and getattr(pet, "peso", None):
        try:
            peso_kg = float(pet.peso)
        except Exception:
            peso_kg = None
    if (not peso_kg or peso_kg <= 0) and consulta and getattr(consulta, "peso_consulta", None):
        try:
            peso_kg = float(consulta.peso_consulta)
        except Exception:
            peso_kg = None

    meds = db.query(MedicamentoCatalogo).filter(
        MedicamentoCatalogo.tenant_id == tenant_id,
        MedicamentoCatalogo.ativo == True,  # noqa
    ).order_by(MedicamentoCatalogo.nome).limit(200).all()

    conversa = None
    memoria = []
    contexto_memoria = ""
    historico_salvo = False
    modelo_usado = "vet-regra"
    if payload.salvar_historico:
        try:
            _garantir_tabelas_memoria_ia(db)
            conversa = _obter_ou_criar_conversa_vet(
                db=db,
                tenant_id=tenant_id,
                user_id=user.id,
                payload=payload,
                pet=pet,
                consulta=consulta,
                exame=exame,
            )
            memoria = _carregar_memoria_conversa(db, tenant_id, conversa.id, limite=8)
            memoria_usuario = [m.conteudo for m in memoria if m.tipo == "usuario"]
            contexto_memoria = " | ".join(memoria_usuario[-2:]).strip()
        except Exception:
            db.rollback()
            conversa = None
            memoria = []
            contexto_memoria = ""

    mensagem_analise = mensagem
    if contexto_memoria:
        mensagem_analise = f"{mensagem} {contexto_memoria}"

    resposta_llm, modelo_llm = _tentar_resposta_llm_veterinaria(
        mensagem=mensagem,
        memoria=memoria,
        pet=pet,
        consulta=consulta,
        exame=exame,
        especie=especie,
        peso_kg=peso_kg,
        meds=meds,
        modo=payload.modo,
    )

    if resposta_llm:
        resposta_final = resposta_llm
        modelo_usado = modelo_llm or "vet-llm"
    else:
        respostas = []

        if exame:
            respostas.append(
                _responder_chat_exame(
                    pergunta=mensagem_analise.lower(),
                    exame_nome=exame.nome,
                    tipo_exame=exame.tipo,
                    especie=(pet.especie if pet else "não informada"),
                    nome_pet=(pet.nome if pet else "paciente"),
                    alergias=(getattr(pet, "alergias_lista", None) or []),
                    alertas=(exame.interpretacao_ia_alertas or []),
                    resumo_ia=(exame.interpretacao_ia_resumo or ""),
                    conclusao_ia=(exame.interpretacao_ia or ""),
                    dados_json=(exame.resultado_json or {}),
                    texto_resultado=(exame.resultado_texto or ""),
                )
            )

        resp_dose = _montar_resposta_dose(mensagem_analise, meds, peso_kg, especie)
        if resp_dose:
            respostas.append(resp_dose)

        resp_interacao = _montar_resposta_interacao(
            mensagem_analise,
            meds,
            payload.medicamento_1,
            payload.medicamento_2,
        )
        if resp_interacao:
            respostas.append(resp_interacao)

        resp_sintomas = _montar_resposta_sintomas(mensagem_analise, especie)
        if resp_sintomas:
            respostas.append(resp_sintomas)

        resp_plano = _montar_resposta_plano_estruturado(mensagem_analise, pet, consulta, exame)
        if resp_plano:
            respostas.append(resp_plano)

        if not respostas:
            contexto = []
            if pet:
                contexto.append(f"pet: {pet.nome}")
            if especie:
                contexto.append(f"espécie: {especie}")
            if peso_kg:
                contexto.append(f"peso: {peso_kg:.2f} kg")
            contexto_txt = " | ".join(contexto) if contexto else "sem contexto clínico selecionado"

            respostas.append(
                "Posso te ajudar com: cálculo de dose por mg/kg, avaliação de associação medicamentosa, "
                "hipóteses por sintomas e checklist para fechamento diagnóstico. "
                f"Contexto atual: {contexto_txt}."
            )

        resposta_final = "\n\n".join(respostas)

    resposta_final += (
        "\n\nAviso clínico: resposta de apoio à decisão. "
        "Sempre confirmar conduta final com exame físico, histórico completo e protocolos da clínica."
    )

    contexto_msg = {
        "modulo": "vet",
        "modo": _normalizar_modo_ia(payload.modo),
        "pet_id": pet.id if pet else None,
        "consulta_id": consulta.id if consulta else None,
        "exame_id": exame.id if exame else None,
        "peso_kg": peso_kg,
        "especie": especie,
    }

    if payload.salvar_historico and conversa:
        try:
            db.add(MensagemChat(
                tenant_id=str(tenant_id),
                conversa_id=conversa.id,
                tipo="usuario",
                conteudo=mensagem,
                modelo_usado=modelo_usado,
                contexto_usado=contexto_msg,
            ))
            db.add(MensagemChat(
                tenant_id=str(tenant_id),
                conversa_id=conversa.id,
                tipo="assistente",
                conteudo=resposta_final,
                modelo_usado=modelo_usado,
                contexto_usado={**contexto_msg, "feedback": None},
            ))
            conversa.atualizado_em = datetime.utcnow()
            db.commit()
            historico_salvo = True
        except Exception:
            db.rollback()
            historico_salvo = False

    return {
        "resposta": resposta_final,
        "conversa_id": conversa.id if conversa else payload.conversa_id,
        "historico_salvo": historico_salvo,
        "contexto": {
            "modo": payload.modo,
            "pet_id": pet.id if pet else None,
            "pet_nome": pet.nome if pet else None,
            "consulta_id": consulta.id if consulta else None,
            "exame_id": exame.id if exame else None,
            "peso_kg": peso_kg,
            "especie": especie,
        },
    }


@router.get("/ia/conversas", summary="Lista conversas do assistente IA veterinário")
def listar_conversas_assistente_vet(
    limit: int = Query(20, ge=1, le=100),
    pet_id: Optional[int] = Query(None),
    consulta_id: Optional[int] = Query(None),
    exame_id: Optional[int] = Query(None),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    _garantir_tabelas_memoria_ia(db)

    conversas = db.query(Conversa).filter(
        Conversa.tenant_id == str(tenant_id),
        Conversa.usuario_id == user.id,
    ).order_by(Conversa.atualizado_em.desc(), Conversa.id.desc()).limit(limit).all()

    itens = []
    for conversa in conversas:
        mensagens = db.query(MensagemChat).filter(
            MensagemChat.tenant_id == str(tenant_id),
            MensagemChat.conversa_id == conversa.id,
        ).order_by(MensagemChat.id.asc()).all()

        if not mensagens:
            continue

        mensagens_vet = [m for m in mensagens if isinstance(m.contexto_usado, dict) and m.contexto_usado.get("modulo") == "vet"]
        if not mensagens_vet:
            continue

        ultima = mensagens[-1]
        contexto_base = next((m.contexto_usado for m in mensagens_vet if isinstance(m.contexto_usado, dict)), {}) or {}

        if pet_id and int(contexto_base.get("pet_id") or 0) != int(pet_id):
            continue
        if consulta_id and int(contexto_base.get("consulta_id") or 0) != int(consulta_id):
            continue
        if exame_id and int(contexto_base.get("exame_id") or 0) != int(exame_id):
            continue

        itens.append({
            "id": conversa.id,
            "titulo": conversa.titulo,
            "atualizado_em": conversa.atualizado_em.isoformat() if conversa.atualizado_em else None,
            "ultima_mensagem": (ultima.conteudo or "")[:180],
            "contexto": {
                "modo": contexto_base.get("modo"),
                "pet_id": contexto_base.get("pet_id"),
                "consulta_id": contexto_base.get("consulta_id"),
                "exame_id": contexto_base.get("exame_id"),
            },
        })

    return {"items": itens}


@router.get("/ia/conversas/{conversa_id}/mensagens", summary="Lista mensagens de uma conversa IA veterinária")
def listar_mensagens_conversa_assistente_vet(
    conversa_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    _garantir_tabelas_memoria_ia(db)

    conversa = db.query(Conversa).filter(
        Conversa.id == conversa_id,
        Conversa.tenant_id == str(tenant_id),
        Conversa.usuario_id == user.id,
    ).first()
    if not conversa:
        raise HTTPException(404, "Conversa não encontrada.")

    mensagens = db.query(MensagemChat).filter(
        MensagemChat.tenant_id == str(tenant_id),
        MensagemChat.conversa_id == conversa_id,
    ).order_by(MensagemChat.id.asc()).all()

    itens = []
    for msg in mensagens:
        contexto = msg.contexto_usado if isinstance(msg.contexto_usado, dict) else {}
        if contexto.get("modulo") != "vet":
            continue
        itens.append({
            "id": msg.id,
            "tipo": msg.tipo,
            "conteudo": msg.conteudo,
            "criado_em": msg.criado_em.isoformat() if msg.criado_em else None,
            "feedback": contexto.get("feedback"),
        })

    return {
        "conversa": {
            "id": conversa.id,
            "titulo": conversa.titulo,
            "atualizado_em": conversa.atualizado_em.isoformat() if conversa.atualizado_em else None,
        },
        "items": itens,
    }


@router.post("/ia/mensagens/{mensagem_id}/feedback", summary="Registra feedback da resposta da IA veterinária")
def registrar_feedback_mensagem_assistente_vet(
    mensagem_id: int,
    payload: VetMensagemFeedbackPayload,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    _garantir_tabelas_memoria_ia(db)

    mensagem = db.query(MensagemChat).join(
        Conversa, Conversa.id == MensagemChat.conversa_id
    ).filter(
        MensagemChat.id == mensagem_id,
        MensagemChat.tenant_id == str(tenant_id),
        Conversa.usuario_id == user.id,
    ).first()
    if not mensagem:
        raise HTTPException(404, "Mensagem não encontrada.")
    if mensagem.tipo != "assistente":
        raise HTTPException(400, "Feedback só pode ser registrado em respostas da IA.")

    contexto = mensagem.contexto_usado if isinstance(mensagem.contexto_usado, dict) else {}
    if contexto.get("modulo") != "vet":
        raise HTTPException(400, "Mensagem não pertence ao assistente veterinário.")

    contexto["feedback"] = {
        "util": bool(payload.util),
        "nota": payload.nota,
        "comentario": (payload.comentario or "").strip() or None,
        "avaliado_em": datetime.utcnow().isoformat(),
        "avaliado_por": user.id,
    }
    mensagem.contexto_usado = contexto
    db.commit()

    return {"ok": True, "mensagem_id": mensagem.id, "feedback": contexto["feedback"]}


@router.get("/ia/memoria-status", summary="Verifica e prepara tabelas de memória da IA veterinária")
def memoria_status_assistente_vet(
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _user, _tenant_id = _get_tenant(current)
    status_memoria = _garantir_tabelas_memoria_ia(db)
    return status_memoria


@router.post("/exames/{exame_id}/chat", summary="Chat clínico conversacional sobre um exame")
def chat_exame_ia(
    exame_id: int,
    payload: ExameChatPayload,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    """
    Responde perguntas clínicas sobre um exame específico, usando o resultado,
    a interpretação existente e o histórico básico do paciente como contexto.
    """
    user, tenant_id = _get_tenant(current)

    exame = db.query(ExameVet).filter(
        ExameVet.id == exame_id,
        ExameVet.tenant_id == tenant_id,
    ).first()
    if not exame:
        raise HTTPException(404, "Exame não encontrado.")

    pet = db.query(Pet).filter(Pet.id == exame.pet_id).first()
    pergunta = (payload.pergunta or "").strip().lower()

    # Monta contexto clínico do paciente
    especie = (pet.especie or "não informada") if pet else "não informada"
    nome_pet = pet.nome if pet else "paciente"
    alergias = []
    if pet:
        al = pet.alergias_lista or pet.alergias
        if isinstance(al, list):
            alergias = al
        elif isinstance(al, str) and al.strip():
            alergias = [al]

    alertas_exame = exame.interpretacao_ia_alertas or []
    resumo_ia = exame.interpretacao_ia_resumo or ""
    conclusao_ia = exame.interpretacao_ia or ""
    dados_json = exame.resultado_json or {}
    texto_resultado = exame.resultado_texto or ""

    # Base de conhecimento para Q&A clínica
    resposta = _responder_chat_exame(
        pergunta=pergunta,
        exame_nome=exame.nome,
        tipo_exame=exame.tipo,
        especie=especie,
        nome_pet=nome_pet,
        alergias=alergias,
        alertas=alertas_exame,
        resumo_ia=resumo_ia,
        conclusao_ia=conclusao_ia,
        dados_json=dados_json,
        texto_resultado=texto_resultado,
    )

    return {
        "exame_id": exame_id,
        "pergunta": payload.pergunta,
        "resposta": resposta,
        "contexto": {
            "pet_nome": nome_pet,
            "especie": especie,
            "exame_nome": exame.nome,
            "tem_interpretacao": bool(conclusao_ia),
        },
    }


def _responder_chat_exame(
    *,
    pergunta: str,
    exame_nome: str,
    tipo_exame: str,
    especie: str,
    nome_pet: str,
    alergias: list,
    alertas: list,
    resumo_ia: str,
    conclusao_ia: str,
    dados_json: dict,
    texto_resultado: str,
) -> str:
    """Responde perguntas clínicas usando regras contextuais e os dados do exame."""

    # Interpreta se ainda não foi feito
    if not conclusao_ia and not resumo_ia:
        resumo_ia = "Ainda sem interpretação automática. Use 'Interpretar com IA' antes de perguntar."
        conclusao_ia = resumo_ia

    alertas_nomes = [a.get("campo", "") for a in alertas if isinstance(a, dict)]
    alertas_mensagens = [a.get("mensagem", "") for a in alertas if isinstance(a, dict)]

    # Palavras-chave e respostas contextuais
    if any(k in pergunta for k in ["resumo", "resumir", "explicar", "o que diz", "o que significa", "resultado"]):
        if not texto_resultado and not dados_json:
            return f"O exame '{exame_nome}' ainda não tem resultado registrado. Adicione o resultado antes de solicitar a interpretação."
        partes = []
        if conclusao_ia:
            partes.append(f"**Conclusão da triagem automática:** {conclusao_ia}")
        if resumo_ia and resumo_ia != conclusao_ia:
            partes.append(f"**Detalhes:** {resumo_ia}")
        if alertas_mensagens:
            partes.append("**Alertas encontrados:** " + "; ".join(alertas_mensagens))
        return "\n\n".join(partes) if partes else "Nenhuma interpretação disponível ainda."

    if any(k in pergunta for k in ["alerta", "preocupante", "crítico", "grave", "urgente", "emergência"]):
        if not alertas:
            return f"A triagem automática do exame '{exame_nome}' não encontrou alertas críticos. Isso não substitui a avaliação clínica — verifique os valores numericamente se disponíveis."
        msgs = "\n- ".join(alertas_mensagens) if alertas_mensagens else "Alertas detectados, mas sem detalhes textuais."
        return f"**Pontos de atenção encontrados no exame {exame_nome}:**\n\n- {msgs}\n\nRecomendo revisão clínica presencial."

    if any(k in pergunta for k in ["normal", "status", "tudo certo", "está bem", "dentro do normal"]):
        if not alertas:
            return f"A triagem automática não encontrou valores fora do padrão em '{exame_nome}'. O exame parece dentro da normalidade pelos critérios automatizados — confirme com avaliação clínica."
        return f"Foram encontrados {len(alertas)} ponto(s) de atenção: {resumo_ia}. Revise os valores clínicamente."

    if any(k in pergunta for k in ["próximo passo", "conduta", "tratamento", "o que fazer", "recomendação"]):
        if alertas:
            return (
                f"Com base nos alertas encontrados em '{exame_nome}' ({especie}), a conduta sugerida é:\n\n"
                f"1. Avaliar os itens fora do normal diretamente nos valores do resultado\n"
                f"2. Correlacionar com sinais clínicos de {nome_pet}\n"
                f"3. Considerar exames complementares se necessário\n"
                f"4. Registrar diagnóstico e tratamento na consulta\n\n"
                f"_Alertas identificados: {resumo_ia}_"
            )
        return (
            f"A triagem automática de '{exame_nome}' não indicou alterações críticas.\n"
            f"Sugestões gerais de conduta:\n\n"
            f"1. Confirmar valores com referências da espécie ({especie})\n"
            f"2. Correlacionar com os sinais clínicos de {nome_pet}\n"
            f"3. Repetir o exame conforme evolução clínica\n"
        )

    if any(k in pergunta for k in ["alergia", "medicamento", "contraindicado", "intolerância"]):
        if alergias:
            lista_al = ", ".join(alergias)
            return (
                f"{nome_pet} tem alergias registradas: **{lista_al}**.\n\n"
                f"Ao definir o tratamento com base no exame '{exame_nome}', evite medicamentos ou substâncias relacionadas."
            )
        return f"Não há alergias registradas para {nome_pet}. Verifique a ficha clínica para mais segurança."

    if any(k in pergunta for k in ["leucocit", "hemograma", "glóbulo", "eritrocit"]):
        dados_hemo = {k: v for k, v in dados_json.items() if any(t in k.lower() for t in ["leuco", "eritro", "hemo", "plaqueta", "glob"])}
        if dados_hemo:
            linhas = "\n".join(f"- {k}: {v}" for k, v in dados_hemo.items())
            return f"Valores hematológicos registrados no resultado:\n{linhas}\n\nInterpretação geral: {resumo_ia or 'sem interpretação automática disponível'}"
        return f"Não há valores hematológicos estruturados no resultado do exame '{exame_nome}'. Verifique o texto do laudo ou reenvie como JSON estruturado."

    if any(k in pergunta for k in ["rim", "renal", "creatinina", "ureia", "uréia"]):
        dados_renal = {k: v for k, v in dados_json.items() if any(t in k.lower() for t in ["creat", "ureia", "uria", "rim", "renal", "tgo", "tgp"])}
        if dados_renal:
            linhas = "\n".join(f"- {k}: {v}" for k, v in dados_renal.items())
            return f"Valores relacionados à função renal/hepática:\n{linhas}\n\n{resumo_ia or 'Consulte a interpretação automática.'}"
        return "Não há parâmetros renais estruturados no resultado. Verifique o laudo original."

    if any(k in pergunta for k in ["imagem", "raio", "ultrassom", "eco", "rx", "radiografia"]):
        if tipo_exame in {"radiografia", "ultrassom", "ecocardiograma", "imagem"}:
            return (
                f"O exame '{exame_nome}' é do tipo imagem. "
                f"A interpretação de imagens requer avaliação por médico veterinário especialista. "
                f"Use os campos de resultado para registrar o laudo textual do radiologista/ultrassonografista, "
                f"que será incluído automaticamente na triagem."
            )
        return "Este exame não é do tipo imagem. Verifique o tipo de exame cadastrado."

    # Resposta genérica baseada no contexto disponível
    partes_resposta = [f"Sobre o exame **{exame_nome}** de {nome_pet} ({especie}):"]
    if conclusao_ia:
        partes_resposta.append(f"\n**Interpretação automática:** {conclusao_ia}")
    if alertas_mensagens:
        partes_resposta.append(f"\n**Pontos de atenção:** {'; '.join(alertas_mensagens)}")
    if not conclusao_ia and not alertas:
        partes_resposta.append("\nAinda sem interpretação. Registre o resultado e use 'Interpretar com IA' para uma análise automática.")
    partes_resposta.append(
        "\n\n_Dica: tente perguntas como 'O que diz o resultado?', 'Há alertas?', 'Qual a conduta recomendada?' ou 'Tem risco de alergia?'_"
    )
    return "".join(partes_resposta)


# ═══════════════════════════════════════════════════════════════
# CALENDÁRIO PREVENTIVO — protocolos por espécie
# ═══════════════════════════════════════════════════════════════

# Protocolos padrão integrados (baseados em médias CFMV)
_CALENDARIO_PADRAO = {
    "cão": [
        {"vacina": "V8 / V10 (1ª dose)", "fase": "filhote", "idade_semanas_min": 6, "idade_semanas_max": 8, "dose": "1ª dose", "reforco_anual": False, "observacoes": "Iniciar série em filhotes a partir de 6 semanas"},
        {"vacina": "V8 / V10 (2ª dose)", "fase": "filhote", "idade_semanas_min": 9, "idade_semanas_max": 11, "dose": "2ª dose", "reforco_anual": False, "observacoes": "21-28 dias após a 1ª dose"},
        {"vacina": "V8 / V10 (3ª dose)", "fase": "filhote", "idade_semanas_min": 12, "idade_semanas_max": 16, "dose": "3ª dose", "reforco_anual": False, "observacoes": "21-28 dias após a 2ª dose — completar série"},
        {"vacina": "V8 / V10 (reforço adulto)", "fase": "adulto", "idade_semanas_min": 52, "idade_semanas_max": None, "dose": "Reforço anual", "reforco_anual": True, "observacoes": "Reforço anual após completar a série filhote"},
        {"vacina": "Antirrábica", "fase": "filhote", "idade_semanas_min": 12, "idade_semanas_max": 16, "dose": "1ª dose", "reforco_anual": True, "observacoes": "Obrigatória por lei. Reforço anual"},
        {"vacina": "Bordetella (tosse dos canis)", "fase": "filhote", "idade_semanas_min": 8, "idade_semanas_max": 12, "dose": "1ª dose", "reforco_anual": True, "observacoes": "Especialmente para cães em contato com outros cães"},
        {"vacina": "Leishmaniose", "fase": "adulto", "idade_semanas_min": 24, "idade_semanas_max": None, "dose": "3 doses (0, 21, 42 dias)", "reforco_anual": True, "observacoes": "Recomendada em áreas endêmicas. Requer teste negativo antes"},
        {"vacina": "Giárdia", "fase": "filhote", "idade_semanas_min": 8, "idade_semanas_max": None, "dose": "2 doses (21 dias)", "reforco_anual": True, "observacoes": "Para cães com risco de exposição"},
        {"vacina": "Leptospirose", "fase": "filhote", "idade_semanas_min": 8, "idade_semanas_max": 12, "dose": "2 doses (21 dias)", "reforco_anual": True, "observacoes": "Geralmente inclusa na V8/V10. Reforço semestral em áreas de risco"},
    ],
    "gato": [
        {"vacina": "Tríplice Felina V3 (1ª dose)", "fase": "filhote", "idade_semanas_min": 8, "idade_semanas_max": 10, "dose": "1ª dose", "reforco_anual": False, "observacoes": "Cobre herpevírus, calicivírus e panleucopenia"},
        {"vacina": "Tríplice Felina V3 (2ª dose)", "fase": "filhote", "idade_semanas_min": 11, "idade_semanas_max": 13, "dose": "2ª dose", "reforco_anual": False, "observacoes": "21 dias após a 1ª dose"},
        {"vacina": "Tríplice Felina V3 (3ª dose)", "fase": "filhote", "idade_semanas_min": 14, "idade_semanas_max": 16, "dose": "3ª dose + início anual", "reforco_anual": True, "observacoes": "Completar série. Após: reforço anual"},
        {"vacina": "Antirrábica", "fase": "filhote", "idade_semanas_min": 12, "idade_semanas_max": 16, "dose": "1ª dose", "reforco_anual": True, "observacoes": "Recomendada. Reforço anual"},
        {"vacina": "FeLV (Leucemia Felina)", "fase": "filhote", "idade_semanas_min": 8, "idade_semanas_max": 12, "dose": "2 doses (28 dias)", "reforco_anual": True, "observacoes": "Para gatos com acesso à rua ou contato com outros felinos. Requer teste FeLV negativo antes"},
        {"vacina": "FIV/FeLV combo", "fase": "adulto", "idade_semanas_min": 26, "idade_semanas_max": None, "dose": "3 doses (21 dias)", "reforco_anual": True, "observacoes": "Para gatos de exterior. Teste negativo obrigatório antes"},
        {"vacina": "Clamidofilose (V4)", "fase": "filhote", "idade_semanas_min": 9, "idade_semanas_max": None, "dose": "2 doses (21 dias)", "reforco_anual": True, "observacoes": "Para gatos em criações ou com outros felinos"},
    ],
    "coelho": [
        {"vacina": "Calicivírus Hemorrágico (VHD)", "fase": "adulto", "idade_semanas_min": 12, "idade_semanas_max": None, "dose": "1ª dose", "reforco_anual": True, "observacoes": "Alta mortalidade. Disponibilidade varia por região"},
        {"vacina": "Mixomatose", "fase": "adulto", "idade_semanas_min": 6, "idade_semanas_max": None, "dose": "1ª dose", "reforco_anual": True, "observacoes": "Principalmente para coelhos com acesso a áreas externas"},
    ],
    "todos": [
        {"vacina": "Antiparasitário (vermífugo)", "fase": "filhote", "idade_semanas_min": 2, "idade_semanas_max": None, "dose": "Preventivo", "reforco_anual": False, "observacoes": "A cada 15 dias até 3 meses, depois trimestral"},
        {"vacina": "Antipulgas / Carrapatos", "fase": "todos", "idade_semanas_min": 8, "idade_semanas_max": None, "dose": "Mensal ou conforme produto", "reforco_anual": False, "observacoes": "Ectoparasitas — manter regularmente durante toda a vida"},
    ],
}


@router.get("/catalogo/calendario-preventivo", summary="Calendário preventivo por espécie")
def calendario_preventivo(
    especie: Optional[str] = Query(None),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    """
    Retorna o calendário preventivo padrão por espécie (cão, gato, coelho, todos)
    mesclado com os protocolos de vacina configurados pelo tenant.
    """
    user, tenant_id = _get_tenant(current)

    especie_norm = (especie or "").strip().lower()

    # Monta calendário base
    calendario_base = []
    for esp, protocolos in _CALENDARIO_PADRAO.items():
        if not especie_norm or especie_norm in esp or esp in especie_norm or esp == "todos":
            for p in protocolos:
                calendario_base.append({**p, "especie": esp, "fonte": "padrao"})

    # Adiciona protocolos personalizados do tenant
    query_protocolos = db.query(ProtocoloVacina).filter(
        ProtocoloVacina.tenant_id == tenant_id,
        ProtocoloVacina.ativo == True,  # noqa
    )
    if especie_norm:
        query_protocolos = query_protocolos.filter(
            (ProtocoloVacina.especie == None) |
            (ProtocoloVacina.especie == "") |
            (ProtocoloVacina.especie.ilike(f"%{especie_norm}%"))
        )

    for p in query_protocolos.all():
        idade_min = p.dose_inicial_semanas

        reforco_dias = p.intervalo_doses_dias or (365 if p.reforco_anual else None)
        calendario_base.append({
            "vacina": p.nome,
            "fase": "filhote" if (idade_min or 0) < 26 else "adulto",
            "idade_semanas_min": idade_min,
            "idade_semanas_max": None,
            "dose": f"{p.numero_doses_serie} dose(s)" if p.numero_doses_serie > 1 else "dose única",
            "reforco_anual": p.reforco_anual,
            "intervalo_doses_dias": p.intervalo_doses_dias,
            "observacoes": p.observacoes or "",
            "especie": p.especie or "todos",
            "fonte": "personalizado",
            "protocolo_id": p.id,
        })

    # Ordena por espécie e idade mínima
    calendario_base.sort(key=lambda x: (x.get("especie", ""), x.get("idade_semanas_min") or 0))

    return {
        "especie_filtro": especie_norm or "todas",
        "total": len(calendario_base),
        "items": calendario_base,
    }
