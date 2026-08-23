"""Planejamento de reposicao e leitura financeira para grupos de empresas."""

from __future__ import annotations

from datetime import date, datetime
from math import ceil
from uuid import UUID

from sqlalchemy.orm import Session

from app.empresa_grupo_analise_detalhes_service import (
    EmpresaGrupoAnaliseDetalhesService,
)
from app.empresa_grupo_analise_service import (
    STATUS_CONTAS_ABERTAS,
    EmpresaGrupoAnaliseService,
    _moeda,
    _numero,
    _quantidade,
)
from app.financeiro_models import ContaPagar, ContaReceber
from app.tenancy.context import tenant_context
from app.utils.timezone import now_brasilia


FAIXAS_FINANCEIRAS = (
    ("vencido", "Vencido"),
    ("hoje", "Hoje"),
    ("1_7", "Próximos 7 dias"),
    ("8_15", "De 8 a 15 dias"),
    ("16_30", "De 16 a 30 dias"),
    ("31_60", "De 31 a 60 dias"),
    ("acima_60", "Acima de 60 dias"),
)


class EmpresaGrupoPlanejamentoService:
    """Calcula acoes sugeridas sem alterar estoque ou financeiro."""

    def __init__(self, db: Session, *, agora: datetime | None = None):
        self.db = db
        self.agora = agora or now_brasilia()
        self.resumo = EmpresaGrupoAnaliseService(db, agora=self.agora)
        self.detalhes = EmpresaGrupoAnaliseDetalhesService(db, agora=self.agora)

    @staticmethod
    def _prioridade(*, cobertura: float | None, compra: float, transferencias: list):
        if cobertura is not None and cobertura < 7:
            return "critico"
        if compra > 0 or (cobertura is not None and cobertura < 15):
            return "alerta"
        if transferencias:
            return "atencao"
        return "normal"

    @staticmethod
    def _planejar_transferencias(empresas: list[dict]) -> list[dict]:
        doadores = [dict(item) for item in empresas if item["excedente_inicial"] > 0]
        receptores = [dict(item) for item in empresas if item["deficit_inicial"] > 0]
        transferencias = []

        for receptor in receptores:
            falta = receptor["deficit_inicial"]
            for doador in doadores:
                disponivel = doador["excedente_inicial"]
                quantidade = min(falta, disponivel)
                if quantidade <= 0.0005:
                    continue
                transferencias.append(
                    {
                        "empresa_origem_id": doador["empresa_id"],
                        "empresa_origem_nome": doador["empresa_nome"],
                        "produto_origem_id": doador["produto_id"],
                        "sku_origem": doador["sku"],
                        "empresa_destino_id": receptor["empresa_id"],
                        "empresa_destino_nome": receptor["empresa_nome"],
                        "produto_destino_id": receptor["produto_id"],
                        "sku_destino": receptor["sku"],
                        "quantidade": _quantidade(quantidade),
                    }
                )
                falta -= quantidade
                doador["excedente_inicial"] -= quantidade
                if falta <= 0.0005:
                    break
        return transferencias

    @staticmethod
    def _compras_por_empresa(
        empresas: list[dict], transferencias: list[dict]
    ) -> dict[str, float]:
        recebimentos = {}
        for transferencia in transferencias:
            destino = transferencia["empresa_destino_id"]
            recebimentos[destino] = recebimentos.get(destino, 0) + _numero(
                transferencia["quantidade"]
            )
        return {
            item["empresa_id"]: max(
                0,
                item["deficit_inicial"] - recebimentos.get(item["empresa_id"], 0),
            )
            for item in empresas
        }

    def listar_reposicao_inteligente(
        self,
        grupo_id: int,
        empresa_atual_id,
        *,
        periodo_dias: int = 30,
        dias_cobertura: int = 30,
        busca: str = "",
        somente_acao: bool = True,
        limite: int = 200,
    ) -> dict:
        produtos = self.detalhes.listar_produtos_vendidos(
            grupo_id,
            empresa_atual_id,
            periodo_dias=periodo_dias,
            busca=busca,
            limite=100_000,
        )
        itens = []
        produtos_com_acao = 0
        for produto in produtos["itens"]:
            empresas = []
            for detalhe in produto["empresas"]:
                consumo_diario = _numero(detalhe["quantidade"]) / periodo_dias
                estoque = max(_numero(detalhe["estoque"]), 0)
                estoque_alvo = consumo_diario * dias_cobertura
                empresas.append(
                    {
                        **detalhe,
                        "consumo_diario": _quantidade(consumo_diario),
                        "estoque_alvo": _quantidade(estoque_alvo),
                        "deficit_inicial": max(0, estoque_alvo - estoque),
                        "excedente_inicial": max(0, estoque - estoque_alvo),
                        "cobertura_dias": round(estoque / consumo_diario, 1)
                        if consumo_diario > 0
                        else None,
                    }
                )

            transferencias = self._planejar_transferencias(empresas)
            compras_por_empresa = self._compras_por_empresa(empresas, transferencias)
            quantidade_compra_exata = sum(compras_por_empresa.values())
            quantidade_compra = ceil(max(0, quantidade_compra_exata - 0.0005))
            custos = [
                _numero(item.get("preco_custo"))
                for item in empresas
                if _numero(item.get("preco_custo")) > 0
            ]
            custo_medio = _moeda(sum(custos) / len(custos)) if custos else 0
            for empresa in empresas:
                empresa["deficit_inicial"] = _quantidade(empresa["deficit_inicial"])
                empresa["excedente_inicial"] = _quantidade(empresa["excedente_inicial"])
                empresa["compra_sugerida"] = _quantidade(
                    compras_por_empresa[empresa["empresa_id"]]
                )

            cobertura = produto["cobertura_dias"]
            prioridade = self._prioridade(
                cobertura=cobertura,
                compra=quantidade_compra,
                transferencias=transferencias,
            )
            tem_acao = quantidade_compra > 0 or bool(transferencias)
            if tem_acao:
                produtos_com_acao += 1
            if somente_acao and not tem_acao:
                continue
            itens.append(
                {
                    "produto_nome": produto["produto_nome"],
                    "sku": produto["sku"],
                    "ean": produto["ean"],
                    "tipo_vinculo": produto["tipo_vinculo"],
                    "prioridade": prioridade,
                    "quantidade_vendida": produto["quantidade"],
                    "consumo_diario_grupo": _quantidade(
                        _numero(produto["quantidade"]) / periodo_dias
                    ),
                    "estoque_grupo": produto["estoque_grupo"],
                    "cobertura_dias": cobertura,
                    "dias_cobertura_alvo": dias_cobertura,
                    "quantidade_compra_sugerida": quantidade_compra,
                    "custo_medio": custo_medio,
                    "valor_compra_estimado": _moeda(quantidade_compra * custo_medio),
                    "empresas": empresas,
                    "transferencias_sugeridas": transferencias,
                }
            )

        ordem = {"critico": 0, "alerta": 1, "atencao": 2, "normal": 3}
        itens.sort(
            key=lambda item: (
                ordem[item["prioridade"]],
                -item["valor_compra_estimado"],
                item["produto_nome"],
            )
        )
        return {
            "grupo": produtos["grupo"],
            "periodo": produtos["periodo"],
            "dias_cobertura_alvo": dias_cobertura,
            "somente_acao": somente_acao,
            "resumo": {
                "produtos_analisados": produtos["resumo"]["produtos"],
                "produtos_com_acao": produtos_com_acao,
                "produtos_para_comprar": sum(
                    1 for item in itens if item["quantidade_compra_sugerida"] > 0
                ),
                "produtos_para_transferir": sum(
                    1 for item in itens if item["transferencias_sugeridas"]
                ),
                "quantidade_compra_sugerida": _quantidade(
                    sum(item["quantidade_compra_sugerida"] for item in itens)
                ),
                "valor_compra_estimado": _moeda(
                    sum(item["valor_compra_estimado"] for item in itens)
                ),
            },
            "itens": itens[:limite],
            "limite": limite,
        }

    @staticmethod
    def _faixa_vencimento(vencimento: date, hoje: date) -> str:
        dias = (vencimento - hoje).days
        if dias < 0:
            return "vencido"
        if dias == 0:
            return "hoje"
        if dias <= 7:
            return "1_7"
        if dias <= 15:
            return "8_15"
        if dias <= 30:
            return "16_30"
        if dias <= 60:
            return "31_60"
        return "acima_60"

    @staticmethod
    def _novo_mapa_faixas() -> dict:
        return {
            chave: {
                "chave": chave,
                "label": label,
                "receber": 0.0,
                "pagar": 0.0,
                "titulos_receber": 0,
                "titulos_pagar": 0,
            }
            for chave, label in FAIXAS_FINANCEIRAS
        }

    def analisar_financeiro(self, grupo_id: int, empresa_atual_id) -> dict:
        grupo, membros = self.resumo._grupo_e_membros(grupo_id, empresa_atual_id)
        hoje = self.agora.date()
        faixas = self._novo_mapa_faixas()
        empresas = []

        for membro, empresa in membros:
            empresa_id = str(membro.empresa_id)
            empresa_uuid = UUID(empresa_id)
            with tenant_context(empresa_uuid):
                receber = (
                    self.db.query(
                        ContaReceber.data_vencimento,
                        ContaReceber.valor_final,
                        ContaReceber.valor_recebido,
                    )
                    .filter(
                        ContaReceber.tenant_id == empresa_uuid,
                        ContaReceber.status.in_(STATUS_CONTAS_ABERTAS),
                    )
                    .all()
                )
                pagar = (
                    self.db.query(
                        ContaPagar.data_vencimento,
                        ContaPagar.valor_final,
                        ContaPagar.valor_pago,
                    )
                    .filter(
                        ContaPagar.tenant_id == empresa_uuid,
                        ContaPagar.status.in_(STATUS_CONTAS_ABERTAS),
                    )
                    .all()
                )

            empresa_resumo = {
                "empresa_id": empresa_id,
                "empresa_nome": empresa.name,
                "papel": membro.papel,
                "receber_aberto": 0.0,
                "receber_vencido": 0.0,
                "pagar_aberto": 0.0,
                "pagar_vencido": 0.0,
            }
            for vencimento, valor_final, valor_recebido in receber:
                saldo = max(_numero(valor_final) - _numero(valor_recebido), 0)
                if saldo <= 0:
                    continue
                chave = self._faixa_vencimento(vencimento, hoje)
                faixas[chave]["receber"] += saldo
                faixas[chave]["titulos_receber"] += 1
                empresa_resumo["receber_aberto"] += saldo
                if chave == "vencido":
                    empresa_resumo["receber_vencido"] += saldo
            for vencimento, valor_final, valor_pago in pagar:
                saldo = max(_numero(valor_final) - _numero(valor_pago), 0)
                if saldo <= 0:
                    continue
                chave = self._faixa_vencimento(vencimento, hoje)
                faixas[chave]["pagar"] += saldo
                faixas[chave]["titulos_pagar"] += 1
                empresa_resumo["pagar_aberto"] += saldo
                if chave == "vencido":
                    empresa_resumo["pagar_vencido"] += saldo
            for chave in (
                "receber_aberto",
                "receber_vencido",
                "pagar_aberto",
                "pagar_vencido",
            ):
                empresa_resumo[chave] = _moeda(empresa_resumo[chave])
            empresa_resumo["saldo_liquido"] = _moeda(
                empresa_resumo["receber_aberto"] - empresa_resumo["pagar_aberto"]
            )
            empresas.append(empresa_resumo)

        faixas_lista = []
        for chave, _label in FAIXAS_FINANCEIRAS:
            faixa = faixas[chave]
            faixa["receber"] = _moeda(faixa["receber"])
            faixa["pagar"] = _moeda(faixa["pagar"])
            faixa["saldo"] = _moeda(faixa["receber"] - faixa["pagar"])
            faixas_lista.append(faixa)

        receber_aberto = _moeda(sum(item["receber"] for item in faixas_lista))
        pagar_aberto = _moeda(sum(item["pagar"] for item in faixas_lista))
        receber_vencido = faixas["vencido"]["receber"]
        pagar_vencido = faixas["vencido"]["pagar"]
        faixas_30 = {"hoje", "1_7", "8_15", "16_30"}
        saldo_30_dias = _moeda(
            sum(
                item["receber"] - item["pagar"]
                for item in faixas_lista
                if item["chave"] in faixas_30
            )
        )
        return {
            "grupo": {"id": grupo.id, "nome": grupo.nome},
            "gerado_em": self.agora.isoformat(),
            "resumo": {
                "receber_aberto": receber_aberto,
                "pagar_aberto": pagar_aberto,
                "saldo_liquido": _moeda(receber_aberto - pagar_aberto),
                "receber_vencido": receber_vencido,
                "pagar_vencido": pagar_vencido,
                "saldo_30_dias": saldo_30_dias,
                "inadimplencia_receber_percentual": round(
                    receber_vencido / receber_aberto * 100, 1
                )
                if receber_aberto
                else 0,
                "atraso_pagar_percentual": round(pagar_vencido / pagar_aberto * 100, 1)
                if pagar_aberto
                else 0,
            },
            "faixas": faixas_lista,
            "empresas": empresas,
        }
