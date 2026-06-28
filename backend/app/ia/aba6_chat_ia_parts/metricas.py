"""Consultas agregadas usadas pelo contexto do chat IA."""

from datetime import datetime
from typing import Any, Dict, List, Optional


class ChatIAMetricasMixin:
    def _obter_resumo_vendas_periodo(
        self,
        tenant_id: Optional[str],
        data_inicio: datetime,
        data_fim: datetime,
    ) -> Dict[str, Any]:
        from app.vendas_models import Venda

        if not tenant_id:
            return {
                "quantidade": 0,
                "faturamento_bruto": 0.0,
                "descontos": 0.0,
                "faturamento_liquido": 0.0,
            }

        vendas = (
            self.db.query(Venda)
            .filter(
                Venda.tenant_id == tenant_id,
                Venda.data_venda >= data_inicio,
                Venda.data_venda <= data_fim,
                Venda.status != "cancelada",
            )
            .all()
        )

        faturamento_bruto = sum(
            float(v.subtotal or 0) + float(v.taxa_entrega or 0) for v in vendas
        )
        descontos = sum(float(v.desconto_valor or 0) for v in vendas)
        faturamento_liquido = sum(float(v.total or 0) for v in vendas)

        return {
            "quantidade": len(vendas),
            "faturamento_bruto": round(faturamento_bruto, 2),
            "descontos": round(descontos, 2),
            "faturamento_liquido": round(faturamento_liquido, 2),
        }

    def _obter_produtos_periodo(
        self,
        tenant_id: Optional[str],
        data_inicio: datetime,
        data_fim: datetime,
        limite: int = 5,
    ) -> Dict[str, List[Dict[str, Any]]]:
        from sqlalchemy.orm import selectinload
        from app.vendas_models import Venda, VendaItem

        if not tenant_id:
            return {"top_vendidos": [], "top_margem": []}

        vendas = (
            self.db.query(Venda)
            .options(selectinload(Venda.itens).selectinload(VendaItem.produto))
            .filter(
                Venda.tenant_id == tenant_id,
                Venda.data_venda >= data_inicio,
                Venda.data_venda <= data_fim,
                Venda.status != "cancelada",
            )
            .all()
        )

        acumulado: Dict[str, Dict[str, Any]] = {}

        for venda in vendas:
            for item in venda.itens:
                if not item.produto:
                    continue

                nome = item.produto.nome or f"Produto {item.produto_id}"
                qtd = float(item.quantidade or 0)
                receita = float(item.subtotal or 0)
                custo_unit = float(item.produto.preco_custo or 0)
                custo = custo_unit * qtd

                if nome not in acumulado:
                    acumulado[nome] = {
                        "produto": nome,
                        "quantidade": 0.0,
                        "receita": 0.0,
                        "custo": 0.0,
                    }

                acumulado[nome]["quantidade"] += qtd
                acumulado[nome]["receita"] += receita
                acumulado[nome]["custo"] += custo

        lista = []
        for dados in acumulado.values():
            receita = dados["receita"]
            custo = dados["custo"]
            lucro = receita - custo
            margem = (lucro / receita * 100) if receita > 0 else 0.0

            lista.append(
                {
                    "produto": dados["produto"],
                    "quantidade": round(dados["quantidade"], 2),
                    "receita": round(receita, 2),
                    "lucro": round(lucro, 2),
                    "margem_percentual": round(margem, 2),
                }
            )

        top_vendidos = sorted(lista, key=lambda x: x["quantidade"], reverse=True)[
            :limite
        ]
        top_margem = [p for p in lista if p["receita"] > 0]
        top_margem = sorted(
            top_margem, key=lambda x: x["margem_percentual"], reverse=True
        )[:limite]

        return {
            "top_vendidos": top_vendidos,
            "top_margem": top_margem,
        }

    def _obter_dre_simplificada_mes(
        self,
        tenant_id: Optional[str],
        data_inicio: datetime,
        data_fim: datetime,
    ) -> Dict[str, Any]:
        from app.vendas_models import Venda, VendaItem
        from app.financeiro_models import ContaPagar
        from sqlalchemy.orm import selectinload

        if not tenant_id:
            return {
                "receita_bruta": 0.0,
                "descontos": 0.0,
                "receita_liquida": 0.0,
                "cmv_estimado": 0.0,
                "lucro_bruto": 0.0,
                "despesas_operacionais": 0.0,
                "lucro_liquido_estimado": 0.0,
                "margem_liquida_estimada": 0.0,
            }

        vendas = (
            self.db.query(Venda)
            .options(selectinload(Venda.itens).selectinload(VendaItem.produto))
            .filter(
                Venda.tenant_id == tenant_id,
                Venda.data_venda >= data_inicio,
                Venda.data_venda <= data_fim,
                Venda.status.in_(["finalizada", "pago_nf", "baixa_parcial"]),
            )
            .all()
        )

        receita_bruta = sum(
            float(v.subtotal or 0) + float(v.taxa_entrega or 0) for v in vendas
        )
        descontos = sum(float(v.desconto_valor or 0) for v in vendas)
        receita_liquida = receita_bruta - descontos

        cmv_estimado = 0.0
        for venda in vendas:
            for item in venda.itens:
                if item.produto and item.produto.preco_custo:
                    cmv_estimado += float(item.produto.preco_custo) * float(
                        item.quantidade or 0
                    )

        lucro_bruto = receita_liquida - cmv_estimado

        despesas = (
            self.db.query(ContaPagar)
            .filter(
                ContaPagar.tenant_id == tenant_id,
                ContaPagar.data_emissao >= data_inicio.date(),
                ContaPagar.data_emissao <= data_fim.date(),
                ContaPagar.status != "cancelado",
            )
            .all()
        )
        despesas_operacionais = sum(float(c.valor_original or 0) for c in despesas)

        lucro_liquido = lucro_bruto - despesas_operacionais
        margem_liquida = (
            (lucro_liquido / receita_bruta * 100) if receita_bruta > 0 else 0.0
        )

        return {
            "receita_bruta": round(receita_bruta, 2),
            "descontos": round(descontos, 2),
            "receita_liquida": round(receita_liquida, 2),
            "cmv_estimado": round(cmv_estimado, 2),
            "lucro_bruto": round(lucro_bruto, 2),
            "despesas_operacionais": round(despesas_operacionais, 2),
            "lucro_liquido_estimado": round(lucro_liquido, 2),
            "margem_liquida_estimada": round(margem_liquida, 2),
        }

    def _obter_rankings_periodo(
        self,
        tenant_id: Optional[str],
        data_inicio: datetime,
        data_fim: datetime,
        limite: int = 5,
    ) -> Dict[str, List[Dict[str, Any]]]:
        from sqlalchemy.orm import selectinload
        from app.vendas_models import Venda, VendaItem

        if not tenant_id:
            return {"top_categorias_margem": [], "top_canais": []}

        vendas = (
            self.db.query(Venda)
            .options(selectinload(Venda.itens).selectinload(VendaItem.produto))
            .filter(
                Venda.tenant_id == tenant_id,
                Venda.data_venda >= data_inicio,
                Venda.data_venda <= data_fim,
                Venda.status != "cancelada",
            )
            .all()
        )

        categorias: Dict[str, Dict[str, float]] = {}
        canais: Dict[str, Dict[str, float]] = {}

        for venda in vendas:
            canal = (venda.canal or "loja_fisica").replace("_", " ")
            canais.setdefault(canal, {"receita": 0.0, "quantidade": 0.0})
            canais[canal]["receita"] += float(venda.total or 0)
            canais[canal]["quantidade"] += 1

            for item in venda.itens:
                if not item.produto:
                    continue

                categoria_obj = getattr(item.produto, "categoria", None)
                categoria_nome = "Sem categoria"
                if categoria_obj and getattr(categoria_obj, "nome", None):
                    categoria_nome = categoria_obj.nome
                elif getattr(item.produto, "subcategoria", None):
                    categoria_nome = item.produto.subcategoria

                receita = float(item.subtotal or 0)
                quantidade = float(item.quantidade or 0)
                custo = float(getattr(item.produto, "preco_custo", 0) or 0) * quantidade
                lucro = receita - custo

                categorias.setdefault(categoria_nome, {"receita": 0.0, "lucro": 0.0})
                categorias[categoria_nome]["receita"] += receita
                categorias[categoria_nome]["lucro"] += lucro

        top_categorias_margem = []
        for nome, dados in categorias.items():
            receita = dados["receita"]
            lucro = dados["lucro"]
            margem = (lucro / receita * 100) if receita > 0 else 0.0
            top_categorias_margem.append(
                {
                    "categoria": nome,
                    "receita": round(receita, 2),
                    "lucro": round(lucro, 2),
                    "margem_percentual": round(margem, 2),
                }
            )

        top_canais = [
            {
                "canal": nome,
                "receita": round(dados["receita"], 2),
                "quantidade": int(dados["quantidade"]),
            }
            for nome, dados in canais.items()
        ]

        top_categorias_margem.sort(
            key=lambda item: item["margem_percentual"], reverse=True
        )
        top_canais.sort(key=lambda item: item["receita"], reverse=True)

        return {
            "top_categorias_margem": top_categorias_margem[:limite],
            "top_canais": top_canais[:limite],
        }

    def _montar_resumo_executivo_periodo(
        self, tenant_id: Optional[str], periodo: Dict[str, Any]
    ) -> Dict[str, Any]:
        inicio = periodo["inicio"]
        fim = periodo["fim"]

        return {
            "periodo": periodo,
            "resumo_vendas": self._obter_resumo_vendas_periodo(tenant_id, inicio, fim),
            "produtos": self._obter_produtos_periodo(tenant_id, inicio, fim, limite=5),
            "dre": self._obter_dre_simplificada_mes(tenant_id, inicio, fim),
            "rankings": self._obter_rankings_periodo(tenant_id, inicio, fim, limite=5),
        }
