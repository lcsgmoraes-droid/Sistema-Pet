"""
Sistema de Notificações Proativas via WhatsApp
Envia mensagens automáticas para clientes (entregas, lembretes, promoções)
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# TEMPLATES DE NOTIFICAÇÕES
# ============================================================================

NOTIFICATION_TEMPLATES = {
    # Notificações de entrega
    "pedido_confirmado": {
        "titulo": "Pedido Confirmado",
        "mensagem": """✅ *Pedido Confirmado!*

Olá {nome_cliente}!

Seu pedido #{codigo_pedido} foi confirmado e já está sendo preparado.

📦 *Itens:*
{itens}

💰 *Total:* R$ {total}
🚚 *Previsão de entrega:* {previsao}

Você receberá atualizações automáticas sobre o status da sua entrega!"""
    },
    
    "pedido_saiu_entrega": {
        "titulo": "Pedido Saiu para Entrega",
        "mensagem": """🚚 *Seu pedido saiu para entrega!*

Olá {nome_cliente}!

Pedido #{codigo_pedido} está a caminho! 

📍 *Previsão:* Chega hoje até {horario_previsto}
🔗 *Rastreamento:* {link_rastreio}

Em breve estará com você! 🎉"""
    },
    
    "pedido_entregue": {
        "titulo": "Pedido Entregue",
        "mensagem": """✅ *Pedido Entregue!*

Olá {nome_cliente}!

Seu pedido #{codigo_pedido} foi entregue com sucesso! 

Esperamos que você e seu pet aproveitem! 🐾

⭐ Avalie sua experiência:
{link_avaliacao}"""
    },
    
    # Lembretes de agendamento
    "lembrete_agendamento_24h": {
        "titulo": "Lembrete: Agendamento Amanhã",
        "mensagem": """⏰ *Lembrete de Agendamento*

Olá {nome_cliente}!

Lembramos que você tem um agendamento amanhã:

🐾 *Pet:* {nome_pet}
💈 *Serviço:* {tipo_servico}
📅 *Data:* {data}
🕐 *Horário:* {horario}

Confirme sua presença ou reagende se necessário!"""
    },
    
    "lembrete_agendamento_2h": {
        "titulo": "Lembrete: Agendamento em 2h",
        "mensagem": """⏰ *Seu agendamento é daqui a 2 horas!*

🐾 Pet: {nome_pet}
💈 Serviço: {tipo_servico}
🕐 Horário: {horario}

📍 Endereço: {endereco}

Te esperamos! 🐶"""
    },
    
    # Aniversários
    "aniversario_pet": {
        "titulo": "Aniversário do Pet",
        "mensagem": """🎉 *Parabéns, {nome_pet}!* 🎂

Hoje é um dia especial! O {nome_pet} está fazendo aniversário! 🎈

Como presente, temos um *desconto exclusivo de 20%* em qualquer produto ou serviço hoje!

Use o cupom: *ANIVER{nome_pet}*

Felicidades para vocês! 🐾💙"""
    },
    
    "aniversario_cliente": {
        "titulo": "Feliz Aniversário",
        "mensagem": """🎉 *Feliz Aniversário, {nome_cliente}!* 🎂

É um prazer ter você como cliente!

Como presente, preparamos um *desconto de 15%* válido por 7 dias em toda a loja!

Cupom: *ANIVER{codigo_cupom}*

Aproveite! 🎁"""
    },
    
    # Promoções
    "promocao_produto": {
        "titulo": "Promoção Especial",
        "mensagem": """🔥 *PROMOÇÃO ESPECIAL!*

{nome_produto}
~~R$ {preco_original}~~ por *R$ {preco_promocional}*

⏰ Válido até {data_fim}

Aproveite enquanto durar o estoque!

{link_compra}"""
    },
    
    "produto_voltou_estoque": {
        "titulo": "Produto Voltou ao Estoque",
        "mensagem": """✅ *Boa notícia!*

O produto que você procurava voltou ao estoque:

📦 *{nome_produto}*
💰 R$ {preco}

Estoque limitado! Garanta o seu agora:
{link_compra}"""
    },
    
    # Vacinas e consultas
    "lembrete_vacina": {
        "titulo": "Lembrete: Vacina em Atraso",
        "mensagem": """💉 *Atenção: Vacina Pendente*

Olá {nome_cliente}!

A vacina do {nome_pet} está próxima do vencimento:

💉 *Vacina:* {tipo_vacina}
📅 *Vencimento:* {data_vencimento}

Agende já a próxima dose e mantenha seu pet protegido! 🐾

Responda esta mensagem para agendar."""
    },
    
    "pos_consulta": {
        "titulo": "Pós-Consulta",
        "mensagem": """🏥 *Como está o {nome_pet}?*

Olá {nome_cliente}!

Já se passaram {dias} dias desde a consulta do {nome_pet}.

Gostaríamos de saber como ele está! Teve alguma melhora?

Qualquer dúvida, estamos à disposição! 💙"""
    },
    
    # Reengajamento
    "cliente_inativo": {
        "titulo": "Sentimos sua Falta",
        "mensagem": """😢 *Sentimos sua falta!*

Olá {nome_cliente}!

Faz um tempo que não vemos você e o {nome_pet} por aqui!

Como presente de boas-vindas, preparamos um *desconto de 25%* na próxima visita!

Cupom: *VOLTEI{codigo_cupom}*
Válido por 15 dias.

Esperamos ver vocês em breve! 🐾💙"""
    },
    
    # Pesquisas
    "pesquisa_satisfacao": {
        "titulo": "Pesquisa de Satisfação",
        "mensagem": """⭐ *Sua opinião é importante!*

Olá {nome_cliente}!

Nos ajude a melhorar! Como foi sua experiência conosco?

{link_pesquisa}

Leva menos de 1 minuto! 🙏"""
    }
}


# ============================================================================
# CLASSE PRINCIPAL
# ============================================================================

class NotificationManager:
    """Gerenciador de notificações proativas"""
    
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
    
    async def enviar_notificacao(
        self,
        tipo: str,
        telefone: str,
        dados: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Envia uma notificação proativa
        
        Args:
            tipo: Tipo de notificação (chave em NOTIFICATION_TEMPLATES)
            telefone: Telefone do destinatário
            dados: Dados para preencher o template
            
        Returns:
            Resultado do envio
        """
        try:
            # Valida tipo de notificação
            if tipo not in NOTIFICATION_TEMPLATES:
                return {
                    "success": False,
                    "error": f"Tipo de notificação inválido: {tipo}"
                }
            
            template = NOTIFICATION_TEMPLATES[tipo]
            
            # Preenche template
            mensagem = template["mensagem"].format(**dados)
            
            # TODO: Integrar com provedor WhatsApp (360dialog, Twilio)
            # Por enquanto, apenas loga
            logger.info(f"Enviando notificação '{tipo}' para {telefone}")
            logger.info(f"Mensagem: {mensagem}")
            
            # Mock: sucesso
            return {
                "success": True,
                "tipo": tipo,
                "telefone": telefone,
                "timestamp": datetime.now().isoformat(),
                "message": "Notificação enviada com sucesso"
            }
        
        except KeyError as e:
            return {
                "success": False,
                "error": f"Campo obrigatório faltando: {e}"
            }
        except Exception as e:
            logger.error(f"Erro ao enviar notificação: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def agendar_notificacao(
        self,
        tipo: str,
        telefone: str,
        dados: Dict[str, Any],
        data_envio: datetime
    ) -> Dict[str, Any]:
        """
        Agenda uma notificação para envio futuro
        
        TODO: Implementar com Celery ou sistema de jobs
        """
        try:
            # Mock: salvar no banco para processamento posterior
            logger.info(
                f"Agendando notificação '{tipo}' para {telefone} "
                f"em {data_envio.isoformat()}"
            )
            
            return {
                "success": True,
                "tipo": tipo,
                "telefone": telefone,
                "data_envio": data_envio.isoformat(),
                "message": "Notificação agendada"
            }
        
        except Exception as e:
            logger.error(f"Erro ao agendar notificação: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    # ========================================================================
    # MÉTODOS AUXILIARES - Triggers Automáticos
    # ========================================================================
    
    async def notificar_pedido_criado(
        self,
        pedido_id: str,
        telefone: str,
        dados_pedido: Dict[str, Any]
    ):
        """Envia notificação quando pedido é criado"""
        return await self.enviar_notificacao(
            tipo="pedido_confirmado",
            telefone=telefone,
            dados={
                "nome_cliente": dados_pedido.get("nome_cliente", "Cliente"),
                "codigo_pedido": pedido_id,
                "itens": self._formatar_itens(dados_pedido.get("itens", [])),
                "total": f"{dados_pedido.get('total', 0):.2f}",
                "previsao": dados_pedido.get("previsao_entrega", "3-5 dias úteis")
            }
        )
    
    async def notificar_pedido_saiu_entrega(
        self,
        pedido_id: str,
        telefone: str,
        horario_previsto: str,
        link_rastreio: str
    ):
        """Notifica quando pedido sai para entrega"""
        return await self.enviar_notificacao(
            tipo="pedido_saiu_entrega",
            telefone=telefone,
            dados={
                "nome_cliente": "Cliente",  # TODO: buscar do banco
                "codigo_pedido": pedido_id,
                "horario_previsto": horario_previsto,
                "link_rastreio": link_rastreio
            }
        )
    
    async def agendar_lembrete_agendamento(
        self,
        agendamento_id: str,
        telefone: str,
        dados_agendamento: Dict[str, Any]
    ):
        """Agenda lembretes para agendamento"""
        
        data_agendamento = dados_agendamento.get("data_hora")
        if isinstance(data_agendamento, str):
            data_agendamento = datetime.fromisoformat(data_agendamento)
        
        # Lembrete 24h antes
        data_lembrete_24h = data_agendamento - timedelta(days=1)
        await self.agendar_notificacao(
            tipo="lembrete_agendamento_24h",
            telefone=telefone,
            dados={
                "nome_cliente": dados_agendamento.get("nome_cliente", "Cliente"),
                "nome_pet": dados_agendamento.get("nome_pet"),
                "tipo_servico": dados_agendamento.get("tipo_servico"),
                "data": data_agendamento.strftime("%d/%m/%Y"),
                "horario": data_agendamento.strftime("%H:%M")
            },
            data_envio=data_lembrete_24h
        )
        
        # Lembrete 2h antes
        data_lembrete_2h = data_agendamento - timedelta(hours=2)
        await self.agendar_notificacao(
            tipo="lembrete_agendamento_2h",
            telefone=telefone,
            dados={
                "nome_pet": dados_agendamento.get("nome_pet"),
                "tipo_servico": dados_agendamento.get("tipo_servico"),
                "horario": data_agendamento.strftime("%H:%M"),
                "endereco": "Rua das Flores, 123"  # TODO: buscar do config
            },
            data_envio=data_lembrete_2h
        )
    
    async def notificar_aniversario_pet(
        self,
        telefone: str,
        nome_pet: str,
        nome_cliente: str
    ):
        """Notifica aniversário do pet"""
        return await self.enviar_notificacao(
            tipo="aniversario_pet",
            telefone=telefone,
            dados={
                "nome_pet": nome_pet,
                "nome_cliente": nome_cliente
            }
        )
    
    async def notificar_produto_voltou_estoque(
        self,
        telefone: str,
        produto: Dict[str, Any]
    ):
        """Notifica quando produto volta ao estoque"""
        return await self.enviar_notificacao(
            tipo="produto_voltou_estoque",
            telefone=telefone,
            dados={
                "nome_produto": produto.get("nome"),
                "preco": f"{produto.get('preco', 0):.2f}",
                "link_compra": f"https://loja.exemplo.com/produto/{produto.get('id')}"
            }
        )
    
    # ========================================================================
    # HELPERS
    # ========================================================================
    
    def _formatar_itens(self, itens: List[Dict[str, Any]]) -> str:
        """Formata lista de itens do pedido"""
        if not itens:
            return "Nenhum item"
        
        linhas = []
        for item in itens:
            linhas.append(
                f"• {item.get('quantidade')}x {item.get('nome')} - "
                f"R$ {item.get('preco', 0):.2f}"
            )
        
        return "\n".join(linhas)


# ============================================================================
# FUNÇÕES UTILITÁRIAS
# ============================================================================

async def processar_notificacoes_agendadas(db: Session):
    """
    Processa notificações agendadas que chegaram na hora de envio
    
    TODO: Rodar em background job (Celery)
    """
    try:
        # TODO: Buscar notificações agendadas do banco
        # Filtrar por data_envio <= agora
        # Enviar cada uma
        # Marcar como enviada
        
        logger.info("Processando notificações agendadas...")
        
    except Exception as e:
        logger.error(f"Erro ao processar notificações: {e}")


async def verificar_aniversarios_hoje(db: Session):
    """
    Verifica aniversários de hoje e envia notificações
    
    TODO: Rodar diariamente (Celery beat)
    """
    try:
        hoje = datetime.now().date()
        
        # TODO: Buscar clientes com aniversário hoje
        # TODO: Buscar pets com aniversário hoje
        # Enviar notificações
        
        logger.info(f"Verificando aniversários de {hoje}")
        
    except Exception as e:
        logger.error(f"Erro ao verificar aniversários: {e}")


async def verificar_lembretes_vacinas(db: Session):
    """
    Verifica vacinas próximas do vencimento
    
    TODO: Rodar semanalmente
    """
    try:
        # TODO: Buscar vacinas que vencem nos próximos 30 dias
        # Enviar notificações
        
        logger.info("Verificando lembretes de vacinas...")
        
    except Exception as e:
        logger.error(f"Erro ao verificar vacinas: {e}")


async def identificar_clientes_inativos(db: Session):
    """
    Identifica clientes inativos e envia campanha de reengajamento
    
    TODO: Rodar mensalmente
    """
    try:
        # TODO: Buscar clientes sem compra/agendamento há 60+ dias
        # Enviar notificação de reengajamento
        
        logger.info("Identificando clientes inativos...")
        
    except Exception as e:
        logger.error(f"Erro ao identificar inativos: {e}")
