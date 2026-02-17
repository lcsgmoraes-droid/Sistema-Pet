# -*- coding: utf-8 -*-
"""
Motor de IA para Categorização Automática - ABA 7
Sistema auto-aprendizado com confiança e padrões
Referência: ALGORITMOS_ABA_5_6_7_8.md (linhas 201-450)
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from app.ia.aba7_extrato_models import PadraoCategoriacaoIA, LancamentoImportado
from app.ia.extrato_nlp import ExtratoNLP
from app.financeiro_models import CategoriaFinanceira
import json


class MotorCategorizacaoIA:
    """
    Motor de categorização automática com aprendizado.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.nlp = ExtratoNLP()
    
    def categorizar_transacao(
        self, 
        data: datetime,
        descricao: str,
        valor: float,
        tipo: str
    ) -> Dict:
        """
        Categoriza transação automaticamente.
        
        Retorna:
            {
                'categoria_id': int ou None,
                'categoria_nome': str ou None,
                'confianca': float (0.0-1.0),
                'alternativas': [{id, nome, confianca}],
                'padrao_usado_id': int ou None,
                'motivo': str (explicação)
            }
        """
        # Extrair dados NLP
        dados_nlp = self.nlp.extrair_dados(descricao)
        
        # Buscar padrões aplicáveis
        padroes = self._buscar_padroes_aplicaveis(
            tipo_transacao=dados_nlp['tipo_transacao'],
            beneficiario=dados_nlp['beneficiario'],
            cnpj_cpf=dados_nlp['cnpj'] or dados_nlp['cpf'],
            valor=valor,
            tipo_lancamento=tipo,
            data=data
        )
        
        if not padroes:
            # Sem padrões: usar categorização por palavras-chave
            return self._categorizar_por_keywords(dados_nlp, tipo)
        
        # Usar padrão com maior confiança
        melhor_padrao = padroes[0]
        
        # Buscar alternativas
        alternativas = []
        for padrao in padroes[1:4]:  # Top 3 alternativas
            categoria = self.db.query(CategoriaFinanceira).filter_by(
                id=padrao.categoria_financeira_id
            ).first()
            
            if categoria:
                alternativas.append({
                    'id': categoria.id,
                    'nome': categoria.nome,
                    'confianca': padrao.confianca_atual
                })
        
        return {
            'categoria_id': melhor_padrao.categoria_financeira_id,
            'categoria_nome': melhor_padrao.categoria_nome,
            'confianca': melhor_padrao.confianca_atual,
            'alternativas': alternativas,
            'padrao_usado_id': melhor_padrao.id,
            'motivo': self._gerar_motivo(melhor_padrao, dados_nlp)
        }
    
    def _buscar_padroes_aplicaveis(
        self,
        tipo_transacao: Optional[str],
        beneficiario: Optional[str],
        cnpj_cpf: Optional[str],
        valor: float,
        tipo_lancamento: str,
        data: datetime
    ) -> List[PadraoCategoriacaoIA]:
        """
        Busca padrões que se aplicam à transação.
        Ordena por confiança decrescente.
        """
        query = self.db.query(PadraoCategoriacaoIA).filter(
            PadraoCategoriacaoIA.ativo == True,
            PadraoCategoriacaoIA.tipo_lancamento == tipo_lancamento
        )
        
        # Filtros opcionais
        if tipo_transacao:
            query = query.filter(
                PadraoCategoriacaoIA.tipo_transacao == tipo_transacao
            )
        
        padroes = query.all()
        
        # Filtrar por critérios adicionais
        padroes_aplicaveis = []
        for padrao in padroes:
            score = self._calcular_score_padrao(
                padrao, beneficiario, cnpj_cpf, valor, data
            )
            if score > 0:
                padrao._score = score  # Temporary attribute
                padroes_aplicaveis.append(padrao)
        
        # Ordenar por score * confianca
        padroes_aplicaveis.sort(
            key=lambda p: p._score * p.confianca_atual,
            reverse=True
        )
        
        return padroes_aplicaveis
    
    def _calcular_score_padrao(
        self,
        padrao: PadraoCategoriacaoIA,
        beneficiario: Optional[str],
        cnpj_cpf: Optional[str],
        valor: float,
        data: datetime
    ) -> float:
        """
        Calcula score de compatibilidade (0.0-1.0).
        """
        score = 0.0
        
        # 1. CNPJ/CPF exato = +0.5
        if cnpj_cpf and padrao.cnpj_cpf and cnpj_cpf == padrao.cnpj_cpf:
            score += 0.5
        
        # 2. Beneficiário similar = +0.3
        if beneficiario and padrao.beneficiario_pattern:
            # Regex ou substring
            if '*' in padrao.beneficiario_pattern or '%' in padrao.beneficiario_pattern:
                # Pattern matching
                pattern_regex = padrao.beneficiario_pattern.replace('%', '.*').replace('*', '.*')
                import re
                if re.search(pattern_regex, beneficiario.upper()):
                    score += 0.3
            else:
                # Similaridade
                similaridade = self.nlp.calcular_similaridade(
                    beneficiario, padrao.beneficiario_pattern
                )
                score += similaridade * 0.3
        
        # 3. Valor dentro da tolerância = +0.2
        if padrao.valor_minimo and padrao.valor_maximo:
            if padrao.valor_minimo <= valor <= padrao.valor_maximo:
                score += 0.2
            else:
                # Fora da faixa: penalizar
                return 0.0
        elif padrao.valor_medio:
            # Tolerância percentual
            tolerancia = padrao.tolerancia_percentual or 10.0
            diferenca_percentual = abs(valor - padrao.valor_medio) / padrao.valor_medio * 100
            if diferenca_percentual <= tolerancia:
                score += 0.2
            else:
                return 0.0
        
        # 4. Frequência e dia típico = +0.2
        if padrao.frequencia and padrao.dia_mes_tipico:
            if padrao.frequencia == 'mensal':
                # Verificar se dia é próximo
                diferenca_dias = abs(data.day - padrao.dia_mes_tipico)
                if diferenca_dias <= 3:
                    score += 0.2
        
        return score
    
    def _categorizar_por_keywords(
        self, 
        dados_nlp: Dict, 
        tipo: str
    ) -> Dict:
        """
        Categorização fallback baseada em palavras-chave.
        """
        categoria_sugerida = dados_nlp.get('categoria_sugerida')
        
        if categoria_sugerida:
            # Buscar categoria por grupo DRE
            categoria = self.db.query(CategoriaFinanceira).filter(
                CategoriaFinanceira.grupo_dre == categoria_sugerida,
                CategoriaFinanceira.tipo == tipo
            ).first()
            
            if categoria:
                return {
                    'categoria_id': categoria.id,
                    'categoria_nome': categoria.nome,
                    'confianca': 0.4,  # Baixa confiança (keyword-based)
                    'alternativas': [],
                    'padrao_usado_id': None,
                    'motivo': f'Detectado pela palavra-chave: {categoria_sugerida}'
                }
        
        # Buscar por palavras-chave no JSON
        palavras = dados_nlp.get('palavras_chave', [])
        if palavras:
            categorias = self.db.query(CategoriaFinanceira).filter(
                CategoriaFinanceira.tipo == tipo,
                CategoriaFinanceira.palavras_chave.isnot(None)
            ).all()
            
            melhor_match = None
            melhor_score = 0
            
            for cat in categorias:
                try:
                    keywords_cat = json.loads(cat.palavras_chave or '[]')
                    # Contar matches
                    matches = sum(1 for p in palavras if p.upper() in [k.upper() for k in keywords_cat])
                    if matches > melhor_score:
                        melhor_score = matches
                        melhor_match = cat
                except:
                    continue
            
            if melhor_match:
                return {
                    'categoria_id': melhor_match.id,
                    'categoria_nome': melhor_match.nome,
                    'confianca': min(0.6, melhor_score * 0.15),
                    'alternativas': [],
                    'padrao_usado_id': None,
                    'motivo': f'{melhor_score} palavras-chave correspondentes'
                }
        
        # Sem categorização
        return {
            'categoria_id': None,
            'categoria_nome': None,
            'confianca': 0.0,
            'alternativas': [],
            'padrao_usado_id': None,
            'motivo': 'Nenhum padrão encontrado - necessita validação manual'
        }
    
    def _gerar_motivo(self, padrao: PadraoCategoriacaoIA, dados_nlp: Dict) -> str:
        """
        Gera explicação legível do motivo da categorização.
        """
        motivos = []
        
        if padrao.cnpj_cpf:
            motivos.append(f"CNPJ/CPF conhecido: {padrao.cnpj_cpf}")
        
        if padrao.beneficiario_pattern:
            motivos.append(f"Beneficiário: {padrao.beneficiario_pattern}")
        
        if padrao.frequencia:
            motivos.append(f"Pagamento {padrao.frequencia}")
        
        motivos.append(f"Confiança: {padrao.confianca_atual:.0%} ({padrao.total_acertos}/{padrao.total_aplicacoes} corretos)")
        
        return ' | '.join(motivos)
    
    def validar_categorizacao(
        self,
        lancamento_id: int,
        aprovado: bool,
        categoria_correta_id: Optional[int] = None
    ):
        """
        Validação humana: atualiza padrões e confiança.
        """
        lancamento = self.db.query(LancamentoImportado).filter_by(
            id=lancamento_id
        ).first()
        
        if not lancamento:
            raise ValueError("Lançamento não encontrado")
        
        if aprovado:
            # Aprovado: incrementar acertos
            lancamento.status_validacao = 'aprovado'
            lancamento.confirmado_usuario = True
            
            if lancamento.padrao_sugerido_id:
                self._incrementar_acerto(lancamento.padrao_sugerido_id)
        
        else:
            # Rejeitado/Editado
            if categoria_correta_id:
                lancamento.status_validacao = 'editado'
                lancamento.categoria_usuario_id = categoria_correta_id
                
                # Atualizar padrão errado
                if lancamento.padrao_sugerido_id:
                    self._incrementar_erro(lancamento.padrao_sugerido_id)
                
                # Criar/atualizar padrão correto
                self._aprender_novo_padrao(lancamento, categoria_correta_id)
            else:
                lancamento.status_validacao = 'rejeitado'
        
        self.db.commit()
    
    def _incrementar_acerto(self, padrao_id: int):
        """Incrementa contador de acertos e atualiza confiança."""
        padrao = self.db.query(PadraoCategoriacaoIA).filter_by(id=padrao_id).first()
        if padrao:
            padrao.total_aplicacoes += 1
            padrao.total_acertos += 1
            padrao.confianca_atual = padrao.total_acertos / padrao.total_aplicacoes
            self.db.commit()
    
    def _incrementar_erro(self, padrao_id: int):
        """Incrementa contador de erros e atualiza confiança."""
        padrao = self.db.query(PadraoCategoriacaoIA).filter_by(id=padrao_id).first()
        if padrao:
            padrao.total_aplicacoes += 1
            padrao.total_erros += 1
            padrao.confianca_atual = padrao.total_acertos / padrao.total_aplicacoes
            
            # Desativar padrão se confiança < 30%
            if padrao.confianca_atual < 0.3 and padrao.total_aplicacoes >= 10:
                padrao.ativo = False
            
            self.db.commit()
    
    def _aprender_novo_padrao(
        self, 
        lancamento: LancamentoImportado, 
        categoria_id: int
    ):
        """
        Cria novo padrão a partir de validação humana.
        """
        categoria = self.db.query(CategoriaFinanceira).filter_by(
            id=categoria_id
        ).first()
        
        if not categoria:
            return
        
        # Verificar se já existe padrão similar
        padroes_existentes = self.db.query(PadraoCategoriacaoIA).filter(
            PadraoCategoriacaoIA.categoria_financeira_id == categoria_id,
            PadraoCategoriacaoIA.tipo_lancamento == lancamento.tipo
        ).all()
        
        # Verificar por CNPJ/CPF
        if lancamento.cnpj_cpf_extraido:
            for p in padroes_existentes:
                if p.cnpj_cpf == lancamento.cnpj_cpf_extraido:
                    # Atualizar padrão existente
                    self._atualizar_padrao_valores(p, lancamento)
                    return
        
        # Verificar por beneficiário
        if lancamento.beneficiario_extraido:
            for p in padroes_existentes:
                if p.beneficiario_pattern:
                    similaridade = self.nlp.calcular_similaridade(
                        lancamento.beneficiario_extraido,
                        p.beneficiario_pattern
                    )
                    if similaridade > 0.8:
                        self._atualizar_padrao_valores(p, lancamento)
                        return
        
        # Criar novo padrão
        novo_padrao = PadraoCategoriacaoIA(
            tipo_transacao=lancamento.tipo_transacao,
            beneficiario_pattern=lancamento.beneficiario_extraido,
            cnpj_cpf=lancamento.cnpj_cpf_extraido,
            valor_medio=float(lancamento.valor),
            valor_minimo=float(lancamento.valor) * 0.9,
            valor_maximo=float(lancamento.valor) * 1.1,
            tolerancia_percentual=10.0,
            categoria_financeira_id=categoria_id,
            categoria_nome=categoria.nome,
            tipo_lancamento=lancamento.tipo,
            total_aplicacoes=1,
            total_acertos=1,
            total_erros=0,
            confianca_atual=1.0,
            ativo=True
        )
        
        self.db.add(novo_padrao)
        self.db.commit()
    
    def _atualizar_padrao_valores(
        self, 
        padrao: PadraoCategoriacaoIA, 
        lancamento: LancamentoImportado
    ):
        """
        Atualiza valores de padrão existente (learning).
        """
        # Atualizar faixa de valores
        if float(lancamento.valor) < padrao.valor_minimo:
            padrao.valor_minimo = float(lancamento.valor)
        if float(lancamento.valor) > padrao.valor_maximo:
            padrao.valor_maximo = float(lancamento.valor)
        
        # Recalcular valor médio
        padrao.valor_medio = (padrao.valor_minimo + padrao.valor_maximo) / 2
        
        self.db.commit()
    
    def obter_estatisticas(self) -> Dict:
        """
        Retorna estatísticas do sistema de IA.
        """
        total_padroes = self.db.query(func.count(PadraoCategoriacaoIA.id)).scalar()
        padroes_ativos = self.db.query(func.count(PadraoCategoriacaoIA.id)).filter(
            PadraoCategoriacaoIA.ativo == True
        ).scalar()
        
        total_lancamentos = self.db.query(func.count(LancamentoImportado.id)).scalar()
        aprovados = self.db.query(func.count(LancamentoImportado.id)).filter(
            LancamentoImportado.status_validacao == 'aprovado'
        ).scalar()
        pendentes = self.db.query(func.count(LancamentoImportado.id)).filter(
            LancamentoImportado.status_validacao == 'pendente'
        ).scalar()
        
        # Confiança média dos padrões
        confianca_media = self.db.query(
            func.avg(PadraoCategoriacaoIA.confianca_atual)
        ).filter(
            PadraoCategoriacaoIA.ativo == True
        ).scalar() or 0.0
        
        # Taxa de acerto global
        total_aplicacoes = self.db.query(
            func.sum(PadraoCategoriacaoIA.total_aplicacoes)
        ).scalar() or 0
        total_acertos = self.db.query(
            func.sum(PadraoCategoriacaoIA.total_acertos)
        ).scalar() or 0
        
        taxa_acerto_global = total_acertos / total_aplicacoes if total_aplicacoes > 0 else 0.0
        
        return {
            'total_padroes': total_padroes,
            'padroes_ativos': padroes_ativos,
            'total_lancamentos': total_lancamentos,
            'aprovados': aprovados,
            'pendentes': pendentes,
            'confianca_media': confianca_media,
            'taxa_acerto_global': taxa_acerto_global
        }
