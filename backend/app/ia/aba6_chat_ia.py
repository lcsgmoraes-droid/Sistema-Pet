"""
ABA 6: Chat IA - Lógica de Negócio

Sistema de chat com IA que responde perguntas sobre finanças
usando contexto do usuário (ABA 5: Fluxo de Caixa)
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, date
import os
import json
from decimal import Decimal
import re
import unicodedata

from app.utils.logger import logger
from app.ia.aba6_models import Conversa, MensagemChat, ContextoFinanceiro
from app.ia.aba5_fluxo_caixa import (
    calcular_indices_saude,
    obter_projecoes_proximos_dias,
    gerar_alertas_caixa
)


class ChatIAService:
    """Serviço para gerenciar chat com IA"""

    LABEL_MES_ATUAL = "mes atual"
    
    def __init__(self, db: Session):
        self.db = db
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
    
    # ==================== CONVERSAS ====================
    
    def criar_conversa(self, usuario_id: int) -> Conversa:
        """Cria nova conversa"""
        conversa = Conversa(
            usuario_id=usuario_id,
            criado_em=datetime.utcnow()
        )
        self.db.add(conversa)
        self.db.commit()
        self.db.refresh(conversa)
        return conversa
    
    def listar_conversas(self, usuario_id: int, limit: int = 20) -> List[Conversa]:
        """Lista conversas do usuário"""
        return (
            self.db.query(Conversa)
            .filter(Conversa.usuario_id == usuario_id)
            .order_by(Conversa.atualizado_em.desc())
            .limit(limit)
            .all()
        )
    
    def obter_conversa(self, conversa_id: int, usuario_id: int) -> Optional[Conversa]:
        """Obtém conversa específica"""
        return (
            self.db.query(Conversa)
            .filter(
                Conversa.id == conversa_id,
                Conversa.usuario_id == usuario_id
            )
            .first()
        )
    
    def deletar_conversa(self, conversa_id: int, usuario_id: int) -> bool:
        """Deleta conversa"""
        conversa = self.obter_conversa(conversa_id, usuario_id)
        if not conversa:
            return False
        
        self.db.delete(conversa)
        self.db.commit()
        return True
    
    # ==================== MENSAGENS ====================
    
    def adicionar_mensagem(
        self,
        conversa_id: int,
        tipo: str,  # 'usuario' ou 'assistente'
        conteudo: str,
        tokens_usados: int = 0,
        modelo_usado: str = None,
        contexto_usado: Dict = None
    ) -> MensagemChat:
        """Adiciona mensagem à conversa"""
        mensagem = MensagemChat(
            conversa_id=conversa_id,
            tipo=tipo,
            conteudo=conteudo,
            tokens_usados=tokens_usados,
            modelo_usado=modelo_usado,
            contexto_usado=contexto_usado,
            criado_em=datetime.utcnow()
        )
        self.db.add(mensagem)
        
        # Atualizar última mensagem da conversa
        conversa = self.db.query(Conversa).filter(Conversa.id == conversa_id).first()
        if conversa:
            conversa.atualizado_em = datetime.utcnow()
            
            # Se primeira mensagem e é do usuário, usar como título
            if not conversa.titulo and tipo == "usuario":
                conversa.titulo = conteudo[:50] + ("..." if len(conteudo) > 50 else "")
        
        self.db.commit()
        self.db.refresh(mensagem)
        return mensagem
    
    def obter_historico(self, conversa_id: int, limit: int = 50) -> List[MensagemChat]:
        """Obtém histórico de mensagens"""
        return (
            self.db.query(MensagemChat)
            .filter(MensagemChat.conversa_id == conversa_id)
            .order_by(MensagemChat.criado_em.asc())
            .limit(limit)
            .all()
        )

    def _resolver_tenant_id(self, usuario_id: int, tenant_id: Optional[str]) -> Optional[str]:
        """Resolve tenant_id para consultas seguras de dados."""
        if tenant_id:
            return str(tenant_id)

        try:
            from app.models import UserTenant

            user_tenant = (
                self.db.query(UserTenant)
                .filter(UserTenant.user_id == usuario_id)
                .order_by(UserTenant.id.desc())
                .first()
            )
            return str(user_tenant.tenant_id) if user_tenant else None
        except Exception as e:
            logger.warning(f"Não foi possível resolver tenant_id no chat IA: {e}")
            return None

    @staticmethod
    def _date_bounds_for_today() -> tuple[datetime, datetime]:
        hoje = date.today()
        inicio = datetime.combine(hoje, datetime.min.time())
        fim = datetime.combine(hoje, datetime.max.time())
        return inicio, fim

    @staticmethod
    def _date_bounds_for_current_month() -> tuple[datetime, datetime]:
        hoje = date.today()
        inicio = datetime(hoje.year, hoje.month, 1)
        fim = datetime.combine(hoje, datetime.max.time())
        return inicio, fim

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

        faturamento_bruto = sum(float(v.subtotal or 0) + float(v.taxa_entrega or 0) for v in vendas)
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

        top_vendidos = sorted(lista, key=lambda x: x["quantidade"], reverse=True)[:limite]
        top_margem = [p for p in lista if p["receita"] > 0]
        top_margem = sorted(top_margem, key=lambda x: x["margem_percentual"], reverse=True)[:limite]

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

        receita_bruta = sum(float(v.subtotal or 0) + float(v.taxa_entrega or 0) for v in vendas)
        descontos = sum(float(v.desconto_valor or 0) for v in vendas)
        receita_liquida = receita_bruta - descontos

        cmv_estimado = 0.0
        for venda in vendas:
            for item in venda.itens:
                if item.produto and item.produto.preco_custo:
                    cmv_estimado += float(item.produto.preco_custo) * float(item.quantidade or 0)

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
        margem_liquida = (lucro_liquido / receita_bruta * 100) if receita_bruta > 0 else 0.0

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

    @staticmethod
    def _normalizar_texto(texto: str) -> str:
        texto = unicodedata.normalize("NFKD", texto or "")
        texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
        return texto.lower().strip()

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
            inicio = datetime.combine(hoje - timedelta(days=dias - 1), datetime.min.time())
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

            encontrados.append({
                "nome": nome_mes,
                "numero": numero_mes,
                "ano": ano,
                "posicao": posicao,
            })

        return sorted(encontrados, key=lambda item: item["posicao"])

    def _periodo_mes(self, ano: int, mes: int, nome_mes: Optional[str] = None) -> Dict[str, Any]:
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

    def _detectar_comparacao_periodos(self, mensagem: str) -> Optional[Dict[str, Dict[str, Any]]]:
        texto = self._normalizar_texto(mensagem)
        if not any(chave in texto for chave in ["compar", " vs ", " versus "]):
            return None

        meses_mencionados = self._listar_meses_mencionados(mensagem)
        if len(meses_mencionados) >= 2:
            atual = meses_mencionados[0]
            comparado = meses_mencionados[1]
            return {
                "periodo_a": self._periodo_mes(atual["ano"], atual["numero"], atual["nome"]),
                "periodo_b": self._periodo_mes(comparado["ano"], comparado["numero"], comparado["nome"]),
            }

        hoje = datetime.now()
        periodo_atual = self._periodo_mes(hoje.year, hoje.month, self.LABEL_MES_ATUAL)
        mes_anterior = 12 if hoje.month == 1 else hoje.month - 1
        ano_mes_anterior = hoje.year - 1 if hoje.month == 1 else hoje.year
        periodo_anterior = self._periodo_mes(ano_mes_anterior, mes_anterior, "mes anterior")

        return {
            "periodo_a": periodo_atual,
            "periodo_b": periodo_anterior,
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

        top_categorias_margem.sort(key=lambda item: item["margem_percentual"], reverse=True)
        top_canais.sort(key=lambda item: item["receita"], reverse=True)

        return {
            "top_categorias_margem": top_categorias_margem[:limite],
            "top_canais": top_canais[:limite],
        }

    def _montar_resumo_executivo_periodo(self, tenant_id: Optional[str], periodo: Dict[str, Any]) -> Dict[str, Any]:
        inicio = periodo["inicio"]
        fim = periodo["fim"]

        return {
            "periodo": periodo,
            "resumo_vendas": self._obter_resumo_vendas_periodo(tenant_id, inicio, fim),
            "produtos": self._obter_produtos_periodo(tenant_id, inicio, fim, limite=5),
            "dre": self._obter_dre_simplificada_mes(tenant_id, inicio, fim),
            "rankings": self._obter_rankings_periodo(tenant_id, inicio, fim, limite=5),
        }

    
    # ==================== CONTEXTO FINANCEIRO ====================
    
    def obter_contexto_financeiro(self, usuario_id: int, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """Obtém contexto financeiro do usuário (dados do ABA 5)"""
        contexto = {}
        tenant_id_resolvido = self._resolver_tenant_id(usuario_id, tenant_id)
        
        try:
            # 1. Índices de saúde
            indices = calcular_indices_saude(usuario_id, self.db)
            contexto["indices_saude"] = {
                "saldo_atual": float(indices.get('saldo_atual', 0)),
                "dias_de_caixa": float(indices.get('dias_de_caixa', 0)),
                "status": indices.get('status', 'desconhecido'),
                "tendencia": indices.get('tendencia', 'estavel'),
                "score_saude": int(indices.get('score_saude', 0))
            }
            
            # 2. Projeções 15 dias
            projecoes = obter_projecoes_proximos_dias(usuario_id, dias=15, db=self.db)
            contexto["projecoes"] = [
                {
                    "data": p.get('data_projetada'),
                    "saldo_estimado": float(p.get('saldo_estimado', 0)),
                    "entrada_prevista": float(p.get('entrada_prevista', 0)),
                    "saida_prevista": float(p.get('saida_prevista', 0))
                }
                for p in projecoes[:7]  # Últimos 7 dias para resumo
            ]
            
            # 3. Alertas
            alertas = gerar_alertas_caixa(usuario_id, self.db)
            contexto["alertas"] = [
                {
                    "tipo": a.get("tipo", ""),
                    "titulo": a.get("titulo", ""),
                    "mensagem": a.get("mensagem", "")
                }
                for a in alertas
            ]

            inicio_dia, fim_dia = self._date_bounds_for_today()
            inicio_mes, fim_mes = self._date_bounds_for_current_month()

            contexto["vendas_hoje"] = self._obter_resumo_vendas_periodo(
                tenant_id_resolvido, inicio_dia, fim_dia
            )
            contexto["vendas_mes"] = self._obter_resumo_vendas_periodo(
                tenant_id_resolvido, inicio_mes, fim_mes
            )
            contexto["produtos_mes"] = self._obter_produtos_periodo(
                tenant_id_resolvido, inicio_mes, fim_mes, limite=5
            )
            contexto["dre_simplificada_mes"] = self._obter_dre_simplificada_mes(
                tenant_id_resolvido, inicio_mes, fim_mes
            )
            
        except Exception as e:
            logger.info(f"Erro ao obter contexto financeiro: {e}")
            contexto["erro"] = str(e)
        
        return contexto
    
    # ==================== IA RESPONSE ====================
    
    def gerar_resposta_ia(
        self,
        usuario_id: int,
        conversa_id: int,
        mensagem_usuario: str,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Gera resposta da IA baseada na mensagem do usuário"""
        
        # 1. Adicionar mensagem do usuário
        msg_usuario = self.adicionar_mensagem(
            conversa_id=conversa_id,
            tipo="usuario",
            conteudo=mensagem_usuario
        )
        
        # 2. Obter contexto financeiro
        contexto = self.obter_contexto_financeiro(usuario_id, tenant_id)
        
        # 3. Gerar resposta com regras locais
        resposta_texto = self._gerar_resposta_simples(mensagem_usuario, contexto, tenant_id=tenant_id)

        # 4. Adicionar resposta da IA
        msg_ia = self.adicionar_mensagem(
            conversa_id=conversa_id,
            tipo="assistente",
            conteudo=resposta_texto,
            tokens_usados=0,
            modelo_usado="regras_simples",
            contexto_usado=contexto
        )
        
        return {
            "conversa_id": conversa_id,
            "mensagem_usuario": {
                "id": msg_usuario.id,
                "conteudo": msg_usuario.conteudo,
                "criado_em": msg_usuario.criado_em.isoformat()
            },
            "mensagem_ia": {
                "id": msg_ia.id,
                "conteudo": msg_ia.conteudo,
                "criado_em": msg_ia.criado_em.isoformat()
            },
            "contexto_usado": contexto
        }
    
    def _gerar_resposta_simples(self, mensagem: str, contexto: Dict, tenant_id: Optional[str] = None) -> str:
        """Gera resposta simples baseada em regras (temporário antes de OpenAI)"""

        msg_lower = mensagem.lower()
        msg_normalizada = self._normalizar_texto(mensagem)

        indices = contexto.get("indices_saude", {})
        alertas = contexto.get("alertas", [])
        projecoes = contexto.get("projecoes", [])
        vendas_hoje = contexto.get("vendas_hoje", {})

        saldo = indices.get("saldo_atual", 0)
        dias_caixa = indices.get("dias_de_caixa", 0)
        status = indices.get("status", "").lower()

        periodo_detectado = self._detectar_periodo(mensagem)
        resumo_periodo = self._montar_resumo_executivo_periodo(tenant_id, periodo_detectado)
        resumo_vendas_periodo = resumo_periodo["resumo_vendas"]
        produtos_periodo = resumo_periodo["produtos"]
        dre_periodo = resumo_periodo["dre"]
        rankings_periodo = resumo_periodo["rankings"]
        label_periodo = periodo_detectado["label"]
        comparacao_periodos = self._detectar_comparacao_periodos(mensagem)

        def moeda(valor: float) -> str:
            return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        if comparacao_periodos:
            resumo_a = self._montar_resumo_executivo_periodo(tenant_id, comparacao_periodos["periodo_a"])
            resumo_b = self._montar_resumo_executivo_periodo(tenant_id, comparacao_periodos["periodo_b"])

            faturamento_a = float(resumo_a["resumo_vendas"].get("faturamento_liquido", 0))
            faturamento_b = float(resumo_b["resumo_vendas"].get("faturamento_liquido", 0))
            lucro_a = float(resumo_a["dre"].get("lucro_liquido_estimado", 0))
            lucro_b = float(resumo_b["dre"].get("lucro_liquido_estimado", 0))

            if any(palavra in msg_normalizada for palavra in ["canal", "canais"]):
                canais_a = {item["canal"]: item for item in resumo_a["rankings"].get("top_canais", [])}
                canais_b = {item["canal"]: item for item in resumo_b["rankings"].get("top_canais", [])}
                canais_ordenados = sorted(
                    set(canais_a.keys()) | set(canais_b.keys()),
                    key=lambda canal: max(
                        float(canais_a.get(canal, {}).get("receita", 0)),
                        float(canais_b.get(canal, {}).get("receita", 0)),
                    ),
                    reverse=True,
                )[:5]

                if not canais_ordenados:
                    return "Ainda não encontrei canais com vendas suficientes para comparar esses períodos."

                linhas = [
                    f"🛒 **Comparação por canal: {comparacao_periodos['periodo_a']['label']} x {comparacao_periodos['periodo_b']['label']}**\n"
                ]
                for canal in canais_ordenados:
                    receita_a = float(canais_a.get(canal, {}).get("receita", 0))
                    receita_b = float(canais_b.get(canal, {}).get("receita", 0))
                    linhas.append(
                        f"- {canal}: {moeda(receita_a)} vs {moeda(receita_b)} | diferença **{moeda(receita_a - receita_b)}**"
                    )
                return "\n".join(linhas)

            return (
                f"📊 **Comparação: {comparacao_periodos['periodo_a']['label']} x {comparacao_periodos['periodo_b']['label']}**\n\n"
                f"- Faturamento {comparacao_periodos['periodo_a']['label']}: **{moeda(faturamento_a)}**\n"
                f"- Faturamento {comparacao_periodos['periodo_b']['label']}: **{moeda(faturamento_b)}**\n"
                f"- Diferença de faturamento: **{moeda(faturamento_a - faturamento_b)}**\n"
                f"- Lucro líquido {comparacao_periodos['periodo_a']['label']}: **{moeda(lucro_a)}**\n"
                f"- Lucro líquido {comparacao_periodos['periodo_b']['label']}: **{moeda(lucro_b)}**\n"
                f"- Diferença de lucro: **{moeda(lucro_a - lucro_b)}**\n"
                f"- Margem {comparacao_periodos['periodo_a']['label']}: **{float(resumo_a['dre'].get('margem_liquida_estimada', 0)):.2f}%**\n"
                f"- Margem {comparacao_periodos['periodo_b']['label']}: **{float(resumo_b['dre'].get('margem_liquida_estimada', 0)):.2f}%**"
            )

        if any(palavra in msg_lower for palavra in ["vendas do dia", "vendas hoje", "quanto vendi hoje"]):
            return (
                "📊 **Vendas de Hoje**\n\n"
                f"- Quantidade: **{int(vendas_hoje.get('quantidade', 0))}** vendas\n"
                f"- Faturamento bruto: **{moeda(float(vendas_hoje.get('faturamento_bruto', 0)))}**\n"
                f"- Descontos: **{moeda(float(vendas_hoje.get('descontos', 0)))}**\n"
                f"- Faturamento líquido: **{moeda(float(vendas_hoje.get('faturamento_liquido', 0)))}**"
            )

        if any(palavra in msg_normalizada for palavra in ["raio x", "raio-x", "resumo geral", "resumo gerencial", "panorama"]):
            top_produto = (produtos_periodo.get("top_vendidos") or [None])[0]
            top_categoria = (rankings_periodo.get("top_categorias_margem") or [None])[0]
            top_canal = (rankings_periodo.get("top_canais") or [None])[0]

            linhas = [
                f"📌 **Raio-x do periodo: {label_periodo}**\n",
                f"- Vendas: **{int(resumo_vendas_periodo.get('quantidade', 0))}**",
                f"- Faturamento liquido: **{moeda(float(resumo_vendas_periodo.get('faturamento_liquido', 0)))}**",
                f"- Lucro liquido estimado: **{moeda(float(dre_periodo.get('lucro_liquido_estimado', 0)))}**",
                f"- Margem liquida estimada: **{float(dre_periodo.get('margem_liquida_estimada', 0)):.2f}%**",
            ]
            if top_produto:
                linhas.append(
                    f"- Produto lider: **{top_produto['produto']}** com {top_produto['quantidade']:.0f} unid"
                )
            if top_categoria:
                linhas.append(
                    f"- Melhor categoria por margem: **{top_categoria['categoria']}** com **{top_categoria['margem_percentual']:.2f}%**"
                )
            if top_canal:
                linhas.append(
                    f"- Canal mais forte: **{top_canal['canal']}** com **{moeda(float(top_canal['receita']))}**"
                )
            if alertas:
                linhas.append(f"- Alertas ativos: **{len(alertas)}**")
            return "\n".join(linhas)

        if any(palavra in msg_lower for palavra in ["vendas do mês", "vendas do mes"]) or (
            "vendas" in msg_normalizada and any(
                chave in msg_normalizada for chave in [
                    "ultimo", "ultimos", "marco", "abril", "maio", "junho", "julho", "agosto",
                    "setembro", "outubro", "novembro", "dezembro", "janeiro", "fevereiro", "mes"
                ]
            )
        ):
            return (
                f"📅 **Vendas de {label_periodo}**\n\n"
                f"- Quantidade: **{int(resumo_vendas_periodo.get('quantidade', 0))}** vendas\n"
                f"- Faturamento bruto: **{moeda(float(resumo_vendas_periodo.get('faturamento_bruto', 0)))}**\n"
                f"- Descontos: **{moeda(float(resumo_vendas_periodo.get('descontos', 0)))}**\n"
                f"- Faturamento líquido: **{moeda(float(resumo_vendas_periodo.get('faturamento_liquido', 0)))}**"
            )

        if any(palavra in msg_lower for palavra in ["mais vendido", "top produtos", "produto mais vendido"]):
            top_vendidos = produtos_periodo.get("top_vendidos", [])
            if not top_vendidos:
                return f"Ainda não encontrei produtos vendidos em {label_periodo} para montar o ranking."

            linhas = [f"🏆 **Top Produtos Mais Vendidos ({label_periodo})**\n"]
            for idx, item in enumerate(top_vendidos, 1):
                linhas.append(
                    f"{idx}. {item['produto']} — {item['quantidade']:.0f} unid — {moeda(float(item['receita']))}"
                )
            return "\n".join(linhas)

        if any(palavra in msg_lower for palavra in ["margem", "melhor margem", "maior margem"]):
            if "categoria" in msg_normalizada:
                top_categorias = rankings_periodo.get("top_categorias_margem", [])
                if not top_categorias:
                    return f"Ainda não encontrei categorias com margem calculável em {label_periodo}."

                linhas = [f"📦 **Categorias com Melhor Margem ({label_periodo})**\n"]
                for idx, item in enumerate(top_categorias, 1):
                    linhas.append(
                        f"{idx}. {item['categoria']} — margem {item['margem_percentual']:.2f}% — lucro {moeda(float(item['lucro']))}"
                    )
                return "\n".join(linhas)

            top_margem = produtos_periodo.get("top_margem", [])
            if not top_margem:
                return f"Ainda não encontrei produtos com margem calculável em {label_periodo}."

            linhas = [f"💎 **Produtos com Melhor Margem ({label_periodo})**\n"]
            for idx, item in enumerate(top_margem, 1):
                linhas.append(
                    f"{idx}. {item['produto']} — margem {item['margem_percentual']:.2f}% — lucro {moeda(float(item['lucro']))}"
                )
            return "\n".join(linhas)

        if any(palavra in msg_normalizada for palavra in ["canal", "canais", "desempenho por canal"]):
            top_canais = rankings_periodo.get("top_canais", [])
            if not top_canais:
                return f"Ainda não encontrei vendas por canal em {label_periodo}."

            linhas = [f"🛒 **Desempenho por Canal ({label_periodo})**\n"]
            for idx, item in enumerate(top_canais, 1):
                linhas.append(
                    f"{idx}. {item['canal']} — {item['quantidade']} vendas — {moeda(float(item['receita']))}"
                )
            return "\n".join(linhas)

        if "dre" in msg_lower:
            return (
                f"📈 **DRE Simplificada ({label_periodo})**\n\n"
                f"- Receita bruta: **{moeda(float(dre_periodo.get('receita_bruta', 0)))}**\n"
                f"- Descontos: **{moeda(float(dre_periodo.get('descontos', 0)))}**\n"
                f"- Receita líquida: **{moeda(float(dre_periodo.get('receita_liquida', 0)))}**\n"
                f"- CMV estimado: **{moeda(float(dre_periodo.get('cmv_estimado', 0)))}**\n"
                f"- Lucro bruto: **{moeda(float(dre_periodo.get('lucro_bruto', 0)))}**\n"
                f"- Despesas operacionais: **{moeda(float(dre_periodo.get('despesas_operacionais', 0)))}**\n"
                f"- Lucro líquido estimado: **{moeda(float(dre_periodo.get('lucro_liquido_estimado', 0)))}**\n"
                f"- Margem líquida estimada: **{float(dre_periodo.get('margem_liquida_estimada', 0)):.2f}%**"
            )

        if any(palavra in msg_lower for palavra in ["saldo", "quanto tenho", "dinheiro"]):
            return f"📊 Seu saldo atual é de **R$ {saldo:,.2f}**.\n\nVocê tem **{dias_caixa:.1f} dias de caixa**, o que significa que consegue cobrir suas despesas por esse período sem novas receitas.\n\n{'⚠️ Status: ' + status.upper() if status in ['critico', 'alerta'] else '✅ Status: OK'}"

        if any(palavra in msg_lower for palavra in ["dias de caixa", "quanto tempo", "quantos dias"]):
            interpretacao = ""
            if dias_caixa < 7:
                interpretacao = "🔴 **CRÍTICO**: Menos de uma semana! Ação urgente necessária."
            elif dias_caixa < 15:
                interpretacao = "🟡 **ALERTA**: Menos de duas semanas. Monitore com atenção."
            else:
                interpretacao = "🟢 **OK**: Situação confortável."

            return f"Você tem **{dias_caixa:.1f} dias de caixa**.\n\n{interpretacao}\n\nIsso é calculado dividindo seu saldo atual (R$ {saldo:,.2f}) pela despesa média diária."

        if any(palavra in msg_lower for palavra in ["como está", "situação", "saúde", "status"]):
            if status == "critico":
                return f"🔴 **Situação CRÍTICA!**\n\nSeu caixa está com apenas {dias_caixa:.1f} dias.\n\n**Ações recomendadas:**\n- Cortar despesas não essenciais\n- Acelerar cobranças\n- Buscar empréstimo/capital\n- Revisar planejamento urgentemente"
            if status == "alerta":
                return f"🟡 **Situação de ALERTA**\n\nVocê tem {dias_caixa:.1f} dias de caixa.\n\n**Recomendações:**\n- Monitorar diariamente\n- Evitar grandes gastos\n- Planejar com cuidado\n- Cobrar clientes em atraso"
            return f"🟢 **Situação OK!**\n\nVocê tem {dias_caixa:.1f} dias de caixa.\n\nSeu negócio está saudável financeiramente. Continue monitorando e aproveite para investir em crescimento."

        if any(palavra in msg_lower for palavra in ["alerta", "aviso", "problema", "risco"]):
            if alertas:
                resposta = f"⚠️ **Você tem {len(alertas)} alerta(s):**\n\n"
                for i, alerta in enumerate(alertas[:3], 1):
                    resposta += f"{i}. **{alerta.get('titulo', 'Alerta')}**\n   {alerta.get('mensagem', '')}\n\n"
                return resposta
            return "✅ **Nenhum alerta no momento!**\n\nSeu caixa está saudável e não há riscos iminentes."

        if any(palavra in msg_lower for palavra in ["projeção", "previsão", "futuro", "próximos dias"]):
            if projecoes:
                resposta = "📈 **Projeção dos próximos 7 dias:**\n\n"
                for proj in projecoes[:7]:
                    data = proj.get("data", "").split("T")[0]
                    saldo_est = proj.get("saldo_estimado", 0)
                    resposta += f"- **{data}**: R$ {saldo_est:,.2f}\n"
                return resposta
            return "Não há projeções disponíveis no momento. Clique em 'Atualizar Projeção' no Dashboard."

        return f"Olá! 👋 Sou seu assistente financeiro com IA.\n\n**Perguntas que você pode fazer agora:**\n- \"vendas de março\"\n- \"vendas dos últimos 15 dias\"\n- \"compare março com fevereiro\"\n- \"compare por canal este mês com o mês anterior\"\n- \"produto mais vendido no mês\"\n- \"melhor margem por categoria\"\n- \"desempenho por canal\"\n- \"DRE de março\"\n- \"qual é meu saldo atual?\"\n- \"há algum alerta?\"\n- \"me dá um raio-x do negócio\"\n\n📊 **Resumo rápido:**\n- Saldo: {moeda(float(saldo))}\n- Dias de caixa: {dias_caixa:.1f}\n- Status: {status.upper()}"


# Funções auxiliares para endpoints
def criar_conversa_service(db: Session, usuario_id: int) -> Conversa:
    """Helper para criar conversa"""
    service = ChatIAService(db)
    return service.criar_conversa(usuario_id)


def listar_conversas_service(db: Session, usuario_id: int, limit: int = 20) -> List[Conversa]:
    """Helper para listar conversas"""
    service = ChatIAService(db)
    return service.listar_conversas(usuario_id, limit)


def enviar_mensagem_service(
    db: Session,
    usuario_id: int,
    tenant_id: Optional[str],
    conversa_id: int,
    mensagem: str
) -> Dict[str, Any]:
    """Helper para enviar mensagem e obter resposta"""
    service = ChatIAService(db)
    return service.gerar_resposta_ia(usuario_id, conversa_id, mensagem, tenant_id=tenant_id)


def deletar_conversa_service(db: Session, conversa_id: int, usuario_id: int) -> bool:
    """Helper para deletar conversa"""
    service = ChatIAService(db)
    return service.deletar_conversa(conversa_id, usuario_id)
