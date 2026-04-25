"""Rotas de dashboard, relatorios e PDFs do modulo veterinario."""
import csv
from datetime import date, timedelta
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from .auth.dependencies import get_current_user_and_tenant
from .db import get_session
from .pdf_veterinario import gerar_pdf_prontuario, gerar_pdf_receita
from .veterinario_clinico import _consulta_or_404, _prescricao_or_404
from .veterinario_core import _get_tenant
from .veterinario_financeiro import (
    _obter_regra_financeira_veterinaria,
    _resumo_financeiro_procedimento,
    _round_money,
)
from .veterinario_models import (
    AgendamentoVet,
    ConsultaVet,
    InternacaoVet,
    ItemPrescricao,
    PrescricaoVet,
    ProcedimentoConsulta,
    VacinaRegistro,
)
from .veterinario_serializers import _hash_prontuario_consulta

router = APIRouter()


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
