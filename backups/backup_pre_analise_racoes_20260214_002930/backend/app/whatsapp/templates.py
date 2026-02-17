"""
Sistema de Templates de Resposta
Templates dinâmicos para respostas personalizadas da IA
"""
from typing import Dict, Any, Optional
from app.whatsapp.intents import IntentType
from datetime import datetime


# Templates por tipo de intenção
RESPONSE_TEMPLATES: Dict[IntentType, Dict[str, str]] = {
    IntentType.SAUDACAO: {
        "morning": "Bom dia! 🌅 Sou o assistente virtual do {loja_nome}. Como posso ajudar você hoje?",
        "afternoon": "Boa tarde! ☀️ Sou o assistente virtual do {loja_nome}. Em que posso ajudar?",
        "evening": "Boa noite! 🌙 Sou o assistente virtual do {loja_nome}. Como posso ajudar?",
        "default": "Olá! 👋 Sou o assistente virtual do {loja_nome}. Como posso ajudar você?"
    },
    
    IntentType.DESPEDIDA: {
        "default": "Até logo! 👋 Qualquer dúvida, estou por aqui. Tenha um ótimo dia! 🐾",
        "agradecimento": "Por nada! 😊 Foi um prazer ajudar. Até a próxima! 🐾"
    },
    
    IntentType.PRODUTOS: {
        "encontrado": "Encontrei {total} produto(s) para você:\n\n{produtos_list}\n\nGostaria de mais informações sobre algum?",
        "nao_encontrado": "Não encontrei produtos com '{query}' no momento. 😕\n\nPosso ajudar com algo mais? Temos ração, brinquedos, acessórios e muito mais!",
        "detalhes": "📦 *{produto_nome}*\n💰 R$ {preco}\n📊 Estoque: {estoque} unidades\n\n{descricao}"
    },
    
    IntentType.AGENDAMENTO: {
        "horarios_disponiveis": "Horários disponíveis para *{servico}* em {data}:\n\n{horarios}\n\nQual horário prefere?",
        "confirmar": "✅ Perfeito! Confirmo o agendamento:\n\n📅 *Data:* {data}\n⏰ *Horário:* {horario}\n🐾 *Serviço:* {servico}\n\nPode me passar o nome do pet?",
        "confirmado": "🎉 Agendamento confirmado!\n\n📋 *Resumo:*\n📅 {data} às {horario}\n🐾 Pet: {pet_nome}\n💇 Serviço: {servico}\n\nEnviaremos um lembrete 1 dia antes. Até lá! 👋"
    },
    
    IntentType.ENTREGA: {
        "em_transito": "📦 Seu pedido *{codigo}* está a caminho!\n\n🚚 Status: {status}\n📍 Previsão: {previsao}\n\nEm breve você receberá! 🎉",
        "entregue": "✅ Pedido *{codigo}* entregue com sucesso!\n\nObrigado pela preferência! 🐾",
        "nao_encontrado": "Não encontrei pedidos recentes no seu telefone. 🤔\n\nVocê tem o código do pedido? Assim consigo rastrear para você!"
    },
    
    IntentType.CONSULTA_HORARIO: {
        "default": "🕐 *Nosso horário de funcionamento:*\n\n{horario_semana}\n{horario_sabado}\n{horario_domingo}\n\nEstamos aqui para cuidar do seu pet! 🐾"
    },
    
    IntentType.RECLAMACAO: {
        "default": "Sinto muito pelo inconveniente! 😔\n\nVou transferir você para um atendente humano que poderá ajudar melhor. Por favor, aguarde um momento...",
        "registrada": "Sua reclamação foi registrada sob protocolo *{protocolo}*.\n\nUm atendente entrará em contato em breve. Pedimos desculpas pelo transtorno! 🙏"
    },
    
    IntentType.DUVIDA: {
        "default": "Estou aqui para ajudar! 😊\n\nPode me contar melhor sua dúvida? Posso ajudar com:\n• Produtos e preços\n• Agendamentos\n• Status de pedidos\n• Horários da loja\n• E muito mais!"
    }
}


# Templates para formatar listas de produtos
PRODUTO_TEMPLATE = "• *{nome}*\n  💰 R$ {preco}\n  📊 {estoque} em estoque"

PRODUTO_DETALHADO_TEMPLATE = """
📦 *{nome}*
━━━━━━━━━━━━━━━
💰 Preço: R$ {preco}
📊 Estoque: {estoque} unidades
🏷️ Categoria: {categoria}
📝 {descricao}
"""


# Templates para informações da loja
INFO_LOJA_TEMPLATE = """
🏪 *{nome}*
━━━━━━━━━━━━━━━
📍 {endereco}
📞 {telefone}

🕐 *Horário de Funcionamento:*
{horario_semana}
{horario_sabado}
{horario_domingo}

💳 Aceitamos: {formas_pagamento}
"""


class ResponseFormatter:
    """Formata respostas usando templates dinâmicos"""
    
    def __init__(self, loja_nome: str = "Pet Shop"):
        self.loja_nome = loja_nome
    
    def format_saudacao(self) -> str:
        """Formata saudação baseada no horário"""
        hora = datetime.now().hour
        
        if 5 <= hora < 12:
            template_key = "morning"
        elif 12 <= hora < 18:
            template_key = "afternoon"
        elif 18 <= hora < 23:
            template_key = "evening"
        else:
            template_key = "default"
        
        template = RESPONSE_TEMPLATES[IntentType.SAUDACAO][template_key]
        return template.format(loja_nome=self.loja_nome)
    
    def format_produtos(self, produtos: list, query: str = "") -> str:
        """Formata lista de produtos"""
        if not produtos:
            template = RESPONSE_TEMPLATES[IntentType.PRODUTOS]["nao_encontrado"]
            return template.format(query=query)
        
        # Formatar cada produto
        produtos_list = []
        for p in produtos[:5]:  # Máximo 5 produtos
            produto_text = PRODUTO_TEMPLATE.format(
                nome=p.get("nome", "Produto"),
                preco=f"{p.get('preco', 0):.2f}",
                estoque=p.get("estoque", 0)
            )
            produtos_list.append(produto_text)
        
        produtos_str = "\n\n".join(produtos_list)
        
        template = RESPONSE_TEMPLATES[IntentType.PRODUTOS]["encontrado"]
        return template.format(
            total=len(produtos),
            produtos_list=produtos_str
        )
    
    def format_produto_detalhado(self, produto: Dict[str, Any]) -> str:
        """Formata detalhes completos de um produto"""
        return PRODUTO_DETALHADO_TEMPLATE.format(
            nome=produto.get("nome", "Produto"),
            preco=f"{produto.get('preco', 0):.2f}",
            estoque=produto.get("estoque", 0),
            categoria=produto.get("categoria", "Geral"),
            descricao=produto.get("descricao", "")
        )
    
    def format_horarios_disponiveis(
        self,
        servico: str,
        data: str,
        horarios: list
    ) -> str:
        """Formata horários disponíveis"""
        horarios_str = "\n".join([f"• {h}" for h in horarios])
        
        template = RESPONSE_TEMPLATES[IntentType.AGENDAMENTO]["horarios_disponiveis"]
        return template.format(
            servico=servico.title(),
            data=data,
            horarios=horarios_str
        )
    
    def format_agendamento_confirmado(
        self,
        data: str,
        horario: str,
        servico: str,
        pet_nome: str
    ) -> str:
        """Formata confirmação de agendamento"""
        template = RESPONSE_TEMPLATES[IntentType.AGENDAMENTO]["confirmado"]
        return template.format(
            data=data,
            horario=horario,
            servico=servico.title(),
            pet_nome=pet_nome
        )
    
    def format_status_entrega(self, pedido: Dict[str, Any]) -> str:
        """Formata status de entrega"""
        status = pedido.get("status", "")
        
        if status == "entregue":
            template = RESPONSE_TEMPLATES[IntentType.ENTREGA]["entregue"]
            return template.format(codigo=pedido.get("codigo", ""))
        
        elif status in ["em_transito", "enviado"]:
            template = RESPONSE_TEMPLATES[IntentType.ENTREGA]["em_transito"]
            return template.format(
                codigo=pedido.get("codigo", ""),
                status=pedido.get("status_descricao", "Em trânsito"),
                previsao=pedido.get("previsao_entrega", "Em breve")
            )
        
        else:
            return f"📦 Status do pedido *{pedido.get('codigo')}*: {pedido.get('status_descricao', 'Processando')}"
    
    def format_info_loja(self, info: Dict[str, Any]) -> str:
        """Formata informações da loja"""
        horario = info.get("horario", {})
        
        return INFO_LOJA_TEMPLATE.format(
            nome=info.get("nome", self.loja_nome),
            endereco=f"{info.get('endereco', '')} - {info.get('cidade', '')}",
            telefone=info.get("telefone", ""),
            horario_semana=horario.get("semana", ""),
            horario_sabado=horario.get("sabado", ""),
            horario_domingo=horario.get("domingo", ""),
            formas_pagamento=", ".join(info.get("formas_pagamento", []))
        )
    
    def get_template(
        self,
        intent: IntentType,
        template_key: str = "default",
        **kwargs
    ) -> str:
        """
        Obtém e formata template específico
        
        Args:
            intent: Tipo de intenção
            template_key: Chave do template dentro da intenção
            **kwargs: Variáveis para substituir no template
            
        Returns:
            String formatada
        """
        templates = RESPONSE_TEMPLATES.get(intent, {})
        template = templates.get(template_key, templates.get("default", ""))
        
        # Adicionar nome da loja por padrão
        if "loja_nome" not in kwargs:
            kwargs["loja_nome"] = self.loja_nome
        
        try:
            return template.format(**kwargs)
        except KeyError as e:
            # Se faltar alguma variável, retornar template sem formatação
            return template
    
    def format_error(self, error_message: str) -> str:
        """Formata mensagem de erro de forma amigável"""
        return f"😕 Ops! Tive um pequeno problema: {error_message}\n\nPode tentar novamente ou falar com um atendente?"
    
    def format_handoff(self, motivo: str = "") -> str:
        """Formata mensagem de transferência para humano"""
        msg = "👤 Vou transferir você para um atendente humano que poderá ajudar melhor."
        
        if motivo:
            msg += f"\n\nMotivo: {motivo}"
        
        msg += "\n\nAguarde um momento, por favor... ⏳"
        return msg
    
    def format_handoff_created(self, priority: str = "medium") -> str:
        """Formata mensagem quando handoff é criado"""
        priority_emojis = {
            "low": "🟢",
            "medium": "🟡",
            "high": "🟠",
            "urgent": "🔴"
        }
        
        emoji = priority_emojis.get(priority, "🟡")
        
        messages = {
            "urgent": f"{emoji} Entendo sua urgência! Estou transferindo você para um atendente humano agora mesmo.\n\nAguarde só um momento... ⏱️",
            "high": f"{emoji} Vou transferir você para um atendente que poderá ajudar melhor.\n\nAguarde, por favor... ⏳",
            "medium": f"{emoji} Vou conectar você com um atendente humano.\n\nUm momento, por favor... 👤",
            "low": f"{emoji} Vou direcionar você para um atendente.\n\nAguarde um instante... 💬"
        }
        
        return messages.get(priority, messages["medium"])


# Instância singleton
response_formatter = ResponseFormatter()
