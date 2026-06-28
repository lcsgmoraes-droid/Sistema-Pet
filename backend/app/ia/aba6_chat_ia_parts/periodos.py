"""Deteccao e montagem de periodos para o chat IA."""

from datetime import date, datetime, timedelta
import re
from typing import Any, Dict, List, Optional


class ChatIAPeriodosMixin:
    def _detectar_periodo(self, mensagem: str) -> Dict[str, Any]:
        texto = self._normalizar_texto(mensagem)
        agora = datetime.now()
        hoje = date.today()

        meses = {
            "janeiro": 1,
            "fevereiro": 2,
            "marco": 3,
            "abril": 4,
            "maio": 5,
            "junho": 6,
            "julho": 7,
            "agosto": 8,
            "setembro": 9,
            "outubro": 10,
            "novembro": 11,
            "dezembro": 12,
        }

        match_dias = re.search(r"ultimos?\s+(\d{1,3})\s+dias?", texto)
        if match_dias:
            dias = max(1, int(match_dias.group(1)))
            inicio = datetime.combine(
                hoje - timedelta(days=dias - 1), datetime.min.time()
            )
            fim = datetime.combine(hoje, datetime.max.time())
            return {"inicio": inicio, "fim": fim, "label": f"ultimos {dias} dias"}

        if "hoje" in texto or "dia de hoje" in texto:
            inicio, fim = self._date_bounds_for_today()
            return {"inicio": inicio, "fim": fim, "label": "hoje"}

        for nome_mes, numero_mes in meses.items():
            if nome_mes in texto:
                ano = agora.year
                match_ano = re.search(rf"{nome_mes}\s+de\s+(\d{{4}})", texto)
                if match_ano:
                    ano = int(match_ano.group(1))
                inicio = datetime(ano, numero_mes, 1)
                if numero_mes == 12:
                    proximo_mes = datetime(ano + 1, 1, 1)
                else:
                    proximo_mes = datetime(ano, numero_mes + 1, 1)
                fim = proximo_mes - timedelta(microseconds=1)
                return {"inicio": inicio, "fim": fim, "label": f"{nome_mes} de {ano}"}

        if "este mes" in texto or self.LABEL_MES_ATUAL in texto or "esse mes" in texto:
            inicio, fim = self._date_bounds_for_current_month()
            return {"inicio": inicio, "fim": fim, "label": self.LABEL_MES_ATUAL}

        inicio, fim = self._date_bounds_for_current_month()
        return {"inicio": inicio, "fim": fim, "label": self.LABEL_MES_ATUAL}

    def _listar_meses_mencionados(self, mensagem: str) -> List[Dict[str, Any]]:
        texto = self._normalizar_texto(mensagem)
        agora = datetime.now()
        meses = [
            ("janeiro", 1),
            ("fevereiro", 2),
            ("marco", 3),
            ("abril", 4),
            ("maio", 5),
            ("junho", 6),
            ("julho", 7),
            ("agosto", 8),
            ("setembro", 9),
            ("outubro", 10),
            ("novembro", 11),
            ("dezembro", 12),
        ]

        encontrados = []
        for nome_mes, numero_mes in meses:
            posicao = texto.find(nome_mes)
            if posicao == -1:
                continue

            ano = agora.year
            match_ano = re.search(rf"{nome_mes}\s+de\s+(\d{{4}})", texto)
            if match_ano:
                ano = int(match_ano.group(1))

            encontrados.append(
                {
                    "nome": nome_mes,
                    "numero": numero_mes,
                    "ano": ano,
                    "posicao": posicao,
                }
            )

        return sorted(encontrados, key=lambda item: item["posicao"])

    def _periodo_mes(
        self, ano: int, mes: int, nome_mes: Optional[str] = None
    ) -> Dict[str, Any]:
        inicio = datetime(ano, mes, 1)
        if mes == 12:
            proximo_mes = datetime(ano + 1, 1, 1)
        else:
            proximo_mes = datetime(ano, mes + 1, 1)
        fim = proximo_mes - timedelta(microseconds=1)
        return {
            "inicio": inicio,
            "fim": fim,
            "label": f"{nome_mes or mes} de {ano}",
        }

    def _detectar_comparacao_periodos(
        self, mensagem: str
    ) -> Optional[Dict[str, Dict[str, Any]]]:
        texto = self._normalizar_texto(mensagem)
        if not any(chave in texto for chave in ["compar", " vs ", " versus "]):
            return None

        meses_mencionados = self._listar_meses_mencionados(mensagem)
        if len(meses_mencionados) >= 2:
            atual = meses_mencionados[0]
            comparado = meses_mencionados[1]
            return {
                "periodo_a": self._periodo_mes(
                    atual["ano"], atual["numero"], atual["nome"]
                ),
                "periodo_b": self._periodo_mes(
                    comparado["ano"], comparado["numero"], comparado["nome"]
                ),
            }

        hoje = datetime.now()
        periodo_atual = self._periodo_mes(hoje.year, hoje.month, self.LABEL_MES_ATUAL)
        mes_anterior = 12 if hoje.month == 1 else hoje.month - 1
        ano_mes_anterior = hoje.year - 1 if hoje.month == 1 else hoje.year
        periodo_anterior = self._periodo_mes(
            ano_mes_anterior, mes_anterior, "mes anterior"
        )

        return {
            "periodo_a": periodo_atual,
            "periodo_b": periodo_anterior,
        }
