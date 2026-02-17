"""
RuleEngine - Motor de regras determinísticas
Adaptado da lógica existente em extrato_nlp.py e extrato_ia.py
"""
from typing import Optional, List, Dict, Any
import re
import time
from .base import DecisionEngine
from ..domain.context import DecisionContext, DecisionType
from ..domain.decision import DecisionResult, Evidence, Alternative, ConfidenceLevel


class RuleEngine(DecisionEngine):
    """
    Motor baseado em regras if/else para categorização de extratos.
    
    Migrado de: app.ia.extrato_nlp.ExtratoNLP
    
    Vantagens:
    - Extremamente rápido (< 10ms)
    - 100% explicável
    - Determinístico
    - Não precisa treinar
    
    Desvantagens:
    - Inflexível
    - Precisa atualizar código para novos casos
    """
    
    def __init__(self):
        super().__init__(name="rule_engine", tier=1)
        
        # Dicionário de palavras-chave → categoria
        # MIGRADO DE: extrato_nlp.py - PADROES_BENEFICIARIO
        self.keyword_rules = {
            "energia": {
                "keywords": ["energisa", "cemig", "copel", "cpfl", "enel", "light", "elektro"],
                "categoria_nome": "Energia Elétrica",
                "tipo_esperado": "despesa"
            },
            "agua": {
                "keywords": ["sabesp", "sanepar", "copasa", "cedae", "embasa"],
                "categoria_nome": "Água e Esgoto",
                "tipo_esperado": "despesa"
            },
            "telefone": {
                "keywords": ["vivo", "claro", "tim", "oi", "nextel", "algar", "vivo fibra", "oi fibra", "claro net"],
                "categoria_nome": "Telefone/Internet",
                "tipo_esperado": "despesa"
            },
            "combustivel": {
                "keywords": ["ipiranga", "shell", "br petrobras", "ale", "raizen"],
                "categoria_nome": "Combustível",
                "tipo_esperado": "despesa"
            },
            "supermercado": {
                "keywords": ["carrefour", "extra", "pao de acucar", "assai", "atacadao"],
                "categoria_nome": "Supermercado",
                "tipo_esperado": "despesa"
            },
            "farmacia": {
                "keywords": ["drogaria", "farmacia", "drogasil", "pacheco", "sao paulo"],
                "categoria_nome": "Farmácia",
                "tipo_esperado": "despesa"
            },
            "aluguel": {
                "keywords": ["aluguel", "locacao", "imovel"],
                "categoria_nome": "Aluguel",
                "tipo_esperado": "despesa"
            },
            "condominio": {
                "keywords": ["condominio", "taxa condominial"],
                "categoria_nome": "Condomínio",
                "tipo_esperado": "despesa"
            },
            "impostos": {
                "keywords": ["darf", "das", "iptu", "ipva", "receita federal"],
                "categoria_nome": "Impostos",
                "tipo_esperado": "despesa"
            }
        }
        
        # Tipos de transação
        # MIGRADO DE: extrato_nlp.py - TIPOS_TRANSACAO
        self.transaction_types = {
            'pix': ['pix', 'transferencia pix', 'transf pix'],
            'ted': ['ted', 'transf ted', 'transferencia ted'],
            'doc': ['doc', 'transf doc'],
            'boleto': ['boleto', 'pagamento boleto', 'pag boleto', 'cobranca'],
            'cartao': ['cartao', 'compra cartao', 'debito cartao'],
            'dinheiro': ['dinheiro', 'saque', 'deposito'],
            'debito_automatico': ['debito automatico', 'deb automatico'],
        }
    
    def can_handle(self, decision_type: str) -> bool:
        """Suporta apenas categorização de lançamentos"""
        return decision_type == DecisionType.CATEGORIZAR_LANCAMENTO.value
    
    async def decide(
        self, 
        context: DecisionContext,
        user_patterns: Optional[List] = None
    ) -> DecisionResult:
        """
        Categoriza lançamento bancário por regras de palavras-chave.
        
        Entrada esperada em context.primary_data:
        - descricao: str (obrigatório)
        - valor: float (obrigatório)
        - data: str (opcional)
        - tipo: str (opcional, 'entrada' ou 'saida')
        """
        start_time = time.time()
        
        # Extrair dados do contexto
        descricao = context.primary_data.get("descricao", "").upper()
        valor = context.primary_data.get("valor", 0.0)
        tipo_lancamento = context.primary_data.get("tipo", "saida" if valor < 0 else "entrada")
        
        # NLP: detectar tipo de transação
        tipo_transacao = self._detect_transaction_type(descricao)
        
        # Procurar palavra-chave que match
        matched_rule = None
        matched_keyword = None
        
        for rule_name, rule_data in self.keyword_rules.items():
            for keyword in rule_data["keywords"]:
                if keyword.upper() in descricao:
                    matched_rule = rule_data
                    matched_keyword = keyword
                    break
            if matched_rule:
                break
        
        # Se não encontrou, retornar baixa confiança
        if not matched_rule:
            processing_time = (time.time() - start_time) * 1000
            return self._create_low_confidence_result(
                context, processing_time, descricao, tipo_transacao
            )
        
        # Calcular confiança base
        confidence = 75.0  # Base para regra matched
        reasons = []
        evidence = []
        
        # Adicionar evidência da keyword
        evidence.append(Evidence(
            source="keyword_match",
            value=matched_keyword,
            weight=1.0,
            explanation=f"Palavra-chave '{matched_keyword}' encontrada na descrição"
        ))
        reasons.append(f"Palavra-chave '{matched_keyword}' indica categoria '{matched_rule['categoria_nome']}'")
        
        # Boost se tipo de lançamento bate com o esperado
        if tipo_lancamento == matched_rule["tipo_esperado"]:
            confidence += 10.0
            reasons.append(f"Tipo de lançamento '{tipo_lancamento}' consistente com a categoria")
        
        # Boost se tem padrão aprendido do usuário
        if user_patterns:
            for pattern in user_patterns:
                # Verificar se algum padrão bate com a categoria sugerida
                pattern_categoria = pattern.get("output_preference", {}).get("categoria_nome")
                if pattern_categoria == matched_rule["categoria_nome"]:
                    boost = pattern.get("confidence_boost", 10.0)
                    confidence += boost
                    occurrences = pattern.get("occurrences", 0)
                    reasons.append(f"Padrão aprendido: categoria aplicada {occurrences}x anteriormente")
                    evidence.append(Evidence(
                        source="user_pattern",
                        value=f"Padrão #{pattern.get('id', '?')}",
                        weight=0.5,
                        explanation=f"Usuário já categorizou transações similares como '{pattern_categoria}'"
                    ))
                    break
        
        # Boost se detectou tipo de transação
        if tipo_transacao:
            confidence += 5.0
            reasons.append(f"Tipo de transação identificado: {tipo_transacao}")
            evidence.append(Evidence(
                source="transaction_type",
                value=tipo_transacao,
                weight=0.3,
                explanation="Tipo de transação detectado na descrição"
            ))
        
        # Limitar confiança máxima (regras nunca são 100%)
        confidence = min(confidence, 95.0)
        
        # Determinar nível de confiança
        if confidence >= 80:
            level = ConfidenceLevel.ALTA
        elif confidence >= 60:
            level = ConfidenceLevel.MEDIA
        else:
            level = ConfidenceLevel.BAIXA
        
        processing_time = (time.time() - start_time) * 1000
        
        # Construir resultado
        return DecisionResult(
            request_id=context.request_id,
            decision_type=context.decision_type.value,
            decision={
                "categoria_nome": matched_rule["categoria_nome"],
                "categoria_id": None,  # Será preenchido pelo service
                "beneficiario": self._extract_beneficiary(descricao),
                "tipo_transacao": tipo_transacao
            },
            confidence=confidence,
            confidence_level=level,
            reasons=reasons,
            evidence=evidence,
            alternatives=self._find_alternatives(descricao, matched_rule),
            engine_used=self.name,
            processing_time_ms=processing_time,
            requires_human_review=(confidence < 80),
            suggested_actions=[
                "aplicar_categoria" if confidence >= 80 else "enviar_para_revisao"
            ]
        )
    
    def _detect_transaction_type(self, texto: str) -> Optional[str]:
        """Detecta tipo de transação pela descrição"""
        for tipo, keywords in self.transaction_types.items():
            for keyword in keywords:
                if keyword.upper() in texto:
                    return tipo
        return None
    
    def _extract_beneficiary(self, texto: str) -> Optional[str]:
        """
        Extrai nome do beneficiário.
        MIGRADO DE: extrato_nlp.py - extrair_beneficiario()
        """
        texto_upper = texto.upper()
        
        # Remover prefixos comuns
        prefixos = ['PIX', 'TED', 'DOC', 'BOLETO', 'PAGAMENTO', 'PAG', 'TRANSF', 'TRANSFERENCIA']
        
        beneficiario = texto
        for prefixo in prefixos:
            if prefixo in texto_upper:
                partes = texto.split(prefixo, 1)
                if len(partes) > 1:
                    beneficiario = partes[1].strip()
                    break
        
        # Limpar pontuação extra
        beneficiario = beneficiario.strip(' -/\\*')
        
        if len(beneficiario) < 3:
            return None
        
        return beneficiario[:100]  # Truncar
    
    def _find_alternatives(self, descricao: str, matched_rule: Dict) -> List[Alternative]:
        """Busca categorias alternativas com menor confiança"""
        alternatives = []
        
        # Procurar outras keywords que também aparecem
        for rule_name, rule_data in self.keyword_rules.items():
            if rule_data["categoria_nome"] == matched_rule["categoria_nome"]:
                continue  # Pular a categoria já escolhida
            
            for keyword in rule_data["keywords"]:
                if keyword.upper() in descricao:
                    alternatives.append(Alternative(
                        option=rule_data["categoria_nome"],
                        confidence=50.0,  # Confiança menor
                        reason_rejected="Palavra-chave menos específica ou secundária"
                    ))
                    break
            
            if len(alternatives) >= 3:
                break
        
        return alternatives
    
    def _create_low_confidence_result(
        self, 
        context: DecisionContext, 
        processing_time: float,
        descricao: str,
        tipo_transacao: Optional[str]
    ) -> DecisionResult:
        """Cria resultado de baixa confiança quando nenhuma regra aplicou"""
        
        reasons = ["Nenhuma palavra-chave conhecida encontrada na descrição"]
        evidence = []
        
        if tipo_transacao:
            reasons.append(f"Tipo de transação identificado: {tipo_transacao}")
            evidence.append(Evidence(
                source="transaction_type",
                value=tipo_transacao,
                weight=0.5,
                explanation="Único dado detectado pela análise"
            ))
        
        return DecisionResult(
            request_id=context.request_id,
            decision_type=context.decision_type.value,
            decision={
                "categoria_nome": "Sem Categoria",
                "categoria_id": None,
                "beneficiario": self._extract_beneficiary(descricao),
                "tipo_transacao": tipo_transacao
            },
            confidence=20.0,
            confidence_level=ConfidenceLevel.MUITO_BAIXA,
            reasons=reasons,
            evidence=evidence,
            alternatives=[],
            engine_used=self.name,
            processing_time_ms=processing_time,
            requires_human_review=True,
            suggested_actions=["solicitar_categorizacao_manual"]
        )
