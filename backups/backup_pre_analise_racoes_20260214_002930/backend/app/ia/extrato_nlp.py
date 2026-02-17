# -*- coding: utf-8 -*-
"""
NLP e Extração Inteligente - ABA 7
Extrai CNPJ, CPF, tipo de transação, beneficiário
Referência: ROADMAP_IA_AMBICOES.md (linhas 80-250)
"""

import re
from typing import Dict, Optional, List
from datetime import datetime


class ExtratoNLP:
    """
    Extração de informações usando NLP e regex.
    """
    
    # Regex patterns
    REGEX_CNPJ = r'\d{2}\.?\d{3}\.?\d{3}\/?\d{4}\-?\d{2}'
    REGEX_CPF = r'\d{3}\.?\d{3}\.?\d{3}\-?\d{2}'
    REGEX_CODIGO_BARRAS = r'\d{47,48}'
    
    # Tipos de transação
    TIPOS_TRANSACAO = {
        'pix': ['pix', 'transferencia pix', 'transf pix'],
        'ted': ['ted', 'transf ted', 'transferencia ted'],
        'doc': ['doc', 'transf doc'],
        'boleto': ['boleto', 'pagamento boleto', 'pag boleto', 'cobranca'],
        'cartao': ['cartao', 'compra cartao', 'debito cartao'],
        'dinheiro': ['dinheiro', 'saque', 'deposito'],
        'cheque': ['cheque'],
        'debito_automatico': ['debito automatico', 'deb automatico'],
        'transferencia': ['transferencia', 'transf'],
        'tarifa': ['tarifa', 'taxa'],
        'juros': ['juros', 'encargos'],
        'rendimento': ['rendimento', 'juros creditados']
    }
    
    # Padrões de beneficiários comuns
    PADROES_BENEFICIARIO = {
        'energia': ['energisa', 'cemig', 'copel', 'cpfl', 'enel', 'light', 'elektro'],
        'agua': ['sabesp', 'sanepar', 'copasa', 'cedae', 'embasa'],
        'telefone': ['vivo', 'claro', 'tim', 'oi', 'nextel', 'algar'],
        'internet': ['net', 'vivo fibra', 'oi fibra', 'claro net'],
        'combustivel': ['ipiranga', 'shell', 'br petrobras', 'ale', 'raizen'],
        'supermercado': ['carrefour', 'extra', 'pao de acucar', 'assai', 'atacadao'],
        'farmacia': ['drogaria', 'farmacia', 'drogasil', 'pacheco', 'sao paulo'],
        'aluguel': ['aluguel', 'locacao', 'imovel'],
        'condominio': ['condominio', 'taxa condominial'],
        'impostos': ['darf', 'das', 'iptu', 'ipva', 'receita federal']
    }
    
    def extrair_dados(self, descricao: str) -> Dict:
        """
        Extrai todas informações possíveis da descrição.
        
        Retorna:
            {
                'cnpj': str ou None,
                'cpf': str ou None,
                'tipo_transacao': str ou None,
                'beneficiario': str ou None,
                'categoria_sugerida': str ou None,
                'codigo_barras': str ou None,
                'palavras_chave': List[str]
            }
        """
        desc_upper = descricao.upper()
        
        return {
            'cnpj': self.extrair_cnpj(descricao),
            'cpf': self.extrair_cpf(descricao),
            'tipo_transacao': self.detectar_tipo_transacao(desc_upper),
            'beneficiario': self.extrair_beneficiario(descricao),
            'categoria_sugerida': self.sugerir_categoria(desc_upper),
            'codigo_barras': self.extrair_codigo_barras(descricao),
            'palavras_chave': self.extrair_palavras_chave(desc_upper)
        }
    
    def extrair_cnpj(self, texto: str) -> Optional[str]:
        """Extrai CNPJ da descrição."""
        match = re.search(self.REGEX_CNPJ, texto)
        if match:
            cnpj = match.group(0)
            # Normalizar: remover pontuação
            cnpj = re.sub(r'[^\d]', '', cnpj)
            if len(cnpj) == 14:
                return cnpj
        return None
    
    def extrair_cpf(self, texto: str) -> Optional[str]:
        """Extrai CPF da descrição."""
        match = re.search(self.REGEX_CPF, texto)
        if match:
            cpf = match.group(0)
            # Normalizar
            cpf = re.sub(r'[^\d]', '', cpf)
            if len(cpf) == 11:
                return cpf
        return None
    
    def extrair_codigo_barras(self, texto: str) -> Optional[str]:
        """Extrai código de barras de boleto."""
        match = re.search(self.REGEX_CODIGO_BARRAS, texto)
        if match:
            return match.group(0)
        return None
    
    def detectar_tipo_transacao(self, texto: str) -> Optional[str]:
        """
        Detecta tipo de transação pela descrição.
        """
        for tipo, keywords in self.TIPOS_TRANSACAO.items():
            for keyword in keywords:
                if keyword.upper() in texto:
                    return tipo
        return None
    
    def extrair_beneficiario(self, texto: str) -> Optional[str]:
        """
        Extrai nome do beneficiário.
        Heurística: pega texto após tipo de transação.
        """
        texto_upper = texto.upper()
        
        # Remover prefixos comuns
        prefixos = ['PIX', 'TED', 'DOC', 'BOLETO', 'PAGAMENTO', 'PAG', 'TRANSF', 'TRANSFERENCIA']
        
        beneficiario = texto
        for prefixo in prefixos:
            if prefixo in texto_upper:
                # Pegar texto após o prefixo
                partes = texto.split(prefixo, 1)
                if len(partes) > 1:
                    beneficiario = partes[1].strip()
                    break
        
        # Limpar números de documento
        beneficiario = re.sub(self.REGEX_CNPJ, '', beneficiario)
        beneficiario = re.sub(self.REGEX_CPF, '', beneficiario)
        beneficiario = re.sub(self.REGEX_CODIGO_BARRAS, '', beneficiario)
        
        # Limpar pontuação extra
        beneficiario = beneficiario.strip(' -/\\*')
        
        if len(beneficiario) < 3:
            return None
        
        return beneficiario
    
    def sugerir_categoria(self, texto: str) -> Optional[str]:
        """
        Sugere categoria baseado em padrões conhecidos.
        """
        for categoria, keywords in self.PADROES_BENEFICIARIO.items():
            for keyword in keywords:
                if keyword.upper() in texto:
                    return categoria
        return None
    
    def extrair_palavras_chave(self, texto: str) -> List[str]:
        """
        Extrai palavras-chave relevantes.
        Remove stopwords e palavras muito curtas.
        """
        # Stopwords básicas
        stopwords = {
            'DE', 'DA', 'DO', 'DAS', 'DOS', 'EM', 'NA', 'NO', 'NAS', 'NOS',
            'A', 'O', 'E', 'PARA', 'COM', 'POR', 'AO', 'AOS', 'AS', 'OS',
            'UM', 'UMA', 'UNS', 'UMAS', 'PELO', 'PELA', 'PELOS', 'PELAS'
        }
        
        # Tokenizar
        palavras = re.findall(r'\b\w+\b', texto)
        
        # Filtrar
        palavras_chave = [
            p for p in palavras 
            if len(p) > 2 and p.upper() not in stopwords
        ]
        
        return palavras_chave[:10]  # Top 10
    
    def calcular_similaridade(self, texto1: str, texto2: str) -> float:
        """
        Calcula similaridade entre dois textos (0.0 a 1.0).
        Usa Jaccard similarity de palavras.
        """
        palavras1 = set(self.extrair_palavras_chave(texto1.upper()))
        palavras2 = set(self.extrair_palavras_chave(texto2.upper()))
        
        if not palavras1 or not palavras2:
            return 0.0
        
        intersecao = palavras1.intersection(palavras2)
        uniao = palavras1.union(palavras2)
        
        return len(intersecao) / len(uniao)
    
    def detectar_recorrencia(self, transacoes: List[Dict]) -> List[Dict]:
        """
        Detecta transações recorrentes (mensais, semanais).
        
        Args:
            transacoes: Lista de {data, descricao, valor}
        
        Retorna:
            Lista de padrões: {beneficiario, frequencia, dia_tipico, valor_medio}
        """
        # Agrupar por beneficiário similar
        grupos = {}
        
        for t in transacoes:
            beneficiario = self.extrair_beneficiario(t['descricao'])
            if not beneficiario:
                continue
            
            # Normalizar
            beneficiario_norm = beneficiario.upper().strip()
            
            # Agrupar transações similares
            encontrou = False
            for grupo_key in grupos.keys():
                if self.calcular_similaridade(beneficiario_norm, grupo_key) > 0.7:
                    grupos[grupo_key].append(t)
                    encontrou = True
                    break
            
            if not encontrou:
                grupos[beneficiario_norm] = [t]
        
        # Analisar recorrência
        padroes = []
        for beneficiario, transacoes_grupo in grupos.items():
            if len(transacoes_grupo) < 2:
                continue
            
            # Ordenar por data
            transacoes_grupo.sort(key=lambda x: x['data'])
            
            # Calcular intervalos
            intervalos = []
            for i in range(1, len(transacoes_grupo)):
                delta = (transacoes_grupo[i]['data'] - transacoes_grupo[i-1]['data']).days
                intervalos.append(delta)
            
            if not intervalos:
                continue
            
            # Detectar frequência
            intervalo_medio = sum(intervalos) / len(intervalos)
            
            frequencia = None
            if 25 <= intervalo_medio <= 35:
                frequencia = 'mensal'
            elif 85 <= intervalo_medio <= 95:
                frequencia = 'trimestral'
            elif 5 <= intervalo_medio <= 9:
                frequencia = 'semanal'
            elif 350 <= intervalo_medio <= 375:
                frequencia = 'anual'
            
            if frequencia:
                # Dia do mês típico
                dias = [t['data'].day for t in transacoes_grupo]
                dia_tipico = int(sum(dias) / len(dias))
                
                # Valor médio
                valores = [t['valor'] for t in transacoes_grupo]
                valor_medio = sum(valores) / len(valores)
                
                padroes.append({
                    'beneficiario': beneficiario,
                    'frequencia': frequencia,
                    'dia_tipico': dia_tipico,
                    'valor_medio': valor_medio,
                    'total_ocorrencias': len(transacoes_grupo)
                })
        
        return padroes
