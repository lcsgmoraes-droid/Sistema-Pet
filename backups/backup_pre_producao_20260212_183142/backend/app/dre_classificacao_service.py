"""
Serviço de Classificação Automática DRE
Motor de sugestões baseado em regras e aprendizado de máquina simples
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import List, Dict, Optional, Tuple
from decimal import Decimal
from datetime import datetime

from app.dre_regras_models import (
    RegraClassificacaoDRE,
    TipoRegraClassificacao,
    OrigemRegra,
    HistoricoClassificacao
)
from app.dre_plano_contas_models import DRESubcategoria
from app.financeiro_models import ContaPagar, ContaReceber
from app.utils.logger import logger


class ClassificadorDRE:
    """
    Motor de classificação automática e sugestões DRE
    """
    
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
    
    # ================================================================
    # ANÁLISE E SUGESTÃO
    # ================================================================
    
    def analisar_lancamento(
        self, 
        tipo: str,  # 'pagar' ou 'receber'
        lancamento_id: int
    ) -> List[Dict]:
        """
        Analisa um lançamento e retorna sugestões de classificação DRE
        ordenadas por confiança (maior primeiro)
        
        Returns:
            List[Dict]: [
                {
                    'dre_subcategoria_id': int,
                    'subcategoria_nome': str,
                    'confianca': int,  # 0-100
                    'regra_id': int,
                    'regra_nome': str,
                    'motivo': str,  # Explicação da sugestão
                    'aplicar_automaticamente': bool
                }
            ]
        """
        # Buscar lançamento
        if tipo == 'pagar':
            lancamento = self.db.query(ContaPagar).filter(
                ContaPagar.id == lancamento_id,
                ContaPagar.tenant_id == self.tenant_id
            ).first()
        else:
            lancamento = self.db.query(ContaReceber).filter(
                ContaReceber.id == lancamento_id,
                ContaReceber.tenant_id == self.tenant_id
            ).first()
        
        if not lancamento:
            return []
        
        # ================================================================
        # VERIFICAR SE FORNECEDOR/CLIENTE CONTROLA DRE
        # Fornecedores de produtos para revenda (Buendia, etc) não vão para DRE
        # ================================================================
        if tipo == 'pagar' and hasattr(lancamento, 'fornecedor') and lancamento.fornecedor:
            if not lancamento.fornecedor.controla_dre:
                # Retorna lista vazia - esse fornecedor não controla DRE
                return []
        
        if tipo == 'receber' and hasattr(lancamento, 'cliente') and lancamento.cliente:
            if not lancamento.cliente.controla_dre:
                # Retorna lista vazia - esse cliente não controla DRE
                return []
        
        # Buscar regras aplicáveis
        sugestoes = []
        
        # 1. Regras por tipo específico (vendas, notas entrada)
        if tipo == 'receber' and hasattr(lancamento, 'venda_id') and lancamento.venda_id:
            sugestoes.extend(self._aplicar_regras_venda(lancamento))
        
        if tipo == 'pagar' and hasattr(lancamento, 'nota_entrada_id') and lancamento.nota_entrada_id:
            sugestoes.extend(self._aplicar_regras_nota_entrada(lancamento))
        
        # 2. Regras por beneficiário
        # Verificar se tem fornecedor (ContaPagar) ou cliente (ContaReceber)
        tem_beneficiario = (
            (hasattr(lancamento, 'fornecedor') and lancamento.fornecedor) or 
            (hasattr(lancamento, 'cliente') and lancamento.cliente)
        )
        if tem_beneficiario:
            sugestoes.extend(self._aplicar_regras_beneficiario(lancamento))
        
        # 3. Regras por palavra-chave
        sugestoes.extend(self._aplicar_regras_palavra_chave(lancamento))
        
        # 4. Regras por tipo de documento
        if hasattr(lancamento, 'tipo_documento') and lancamento.tipo_documento:
            sugestoes.extend(self._aplicar_regras_tipo_documento(lancamento))
        
        # 5. Regras combo (múltiplos critérios)
        sugestoes.extend(self._aplicar_regras_combo(lancamento))
        
        # 6. Histórico de classificações similares (aprendizado)
        sugestoes.extend(self._sugerir_por_historico(lancamento, tipo))
        
        # Remover duplicatas e ordenar por confiança
        sugestoes_unicas = self._consolidar_sugestoes(sugestoes)
        
        return sorted(sugestoes_unicas, key=lambda x: x['confianca'], reverse=True)
    
    def _aplicar_regras_venda(self, lancamento: ContaReceber) -> List[Dict]:
        """Aplica regras para lançamentos de vendas"""
        regras = self.db.query(RegraClassificacaoDRE).filter(
            RegraClassificacaoDRE.tenant_id == self.tenant_id,
            RegraClassificacaoDRE.tipo_regra == TipoRegraClassificacao.VENDA_AUTOMATICA,
            RegraClassificacaoDRE.ativo.is_(True)
        ).all()
        
        sugestoes = []
        for regra in regras:
            sugestoes.append({
                'dre_subcategoria_id': regra.dre_subcategoria_id,
                'subcategoria_nome': regra.dre_subcategoria.nome if regra.dre_subcategoria else 'N/A',
                'confianca': regra.confianca,
                'regra_id': regra.id,
                'regra_nome': regra.nome,
                'motivo': 'Receita de venda (automático)',
                'aplicar_automaticamente': not regra.sugerir_apenas
            })
        
        return sugestoes
    
    def _aplicar_regras_nota_entrada(self, lancamento: ContaPagar) -> List[Dict]:
        """Aplica regras para lançamentos de compra de mercadoria"""
        regras = self.db.query(RegraClassificacaoDRE).filter(
            RegraClassificacaoDRE.tenant_id == self.tenant_id,
            RegraClassificacaoDRE.tipo_regra == TipoRegraClassificacao.NOTA_ENTRADA,
            RegraClassificacaoDRE.ativo.is_(True)
        ).all()
        
        sugestoes = []
        for regra in regras:
            sugestoes.append({
                'dre_subcategoria_id': regra.dre_subcategoria_id,
                'subcategoria_nome': regra.dre_subcategoria.nome if regra.dre_subcategoria else 'N/A',
                'confianca': regra.confianca,
                'regra_id': regra.id,
                'regra_nome': regra.nome,
                'motivo': 'Compra de mercadoria (vai para CMV quando vender)',
                'aplicar_automaticamente': not regra.sugerir_apenas
            })
        
        return sugestoes
    
    def _aplicar_regras_beneficiario(self, lancamento) -> List[Dict]:
        """Aplica regras baseadas no nome do beneficiário"""
        # Obter beneficiário do relacionamento correto
        beneficiario = None
        if hasattr(lancamento, 'fornecedor') and lancamento.fornecedor:
            beneficiario = lancamento.fornecedor.nome
        elif hasattr(lancamento, 'cliente') and lancamento.cliente:
            beneficiario = lancamento.cliente.nome
        
        if not beneficiario:
            return []
        
        regras = self.db.query(RegraClassificacaoDRE).filter(
            RegraClassificacaoDRE.tenant_id == self.tenant_id,
            RegraClassificacaoDRE.tipo_regra == TipoRegraClassificacao.BENEFICIARIO,
            RegraClassificacaoDRE.ativo.is_(True)
        ).all()
        
        sugestoes = []
        beneficiario_lower = beneficiario.lower()
        
        for regra in regras:
            criterios = regra.criterios or {}
            beneficiario_regra = criterios.get('beneficiario', '').lower()
            
            if beneficiario_regra and beneficiario_regra in beneficiario_lower:
                sugestoes.append({
                    'dre_subcategoria_id': regra.dre_subcategoria_id,
                    'subcategoria_nome': regra.dre_subcategoria.nome if regra.dre_subcategoria else 'N/A',
                    'confianca': regra.confianca,
                    'regra_id': regra.id,
                    'regra_nome': regra.nome,
                    'motivo': f'Beneficiário: {beneficiario}',
                    'aplicar_automaticamente': not regra.sugerir_apenas
                })
        
        return sugestoes
    
    def _aplicar_regras_palavra_chave(self, lancamento) -> List[Dict]:
        """Aplica regras baseadas em palavras-chave na descrição"""
        regras = self.db.query(RegraClassificacaoDRE).filter(
            RegraClassificacaoDRE.tenant_id == self.tenant_id,
            RegraClassificacaoDRE.tipo_regra == TipoRegraClassificacao.PALAVRA_CHAVE,
            RegraClassificacaoDRE.ativo.is_(True)
        ).all()
        
        sugestoes = []
        descricao_lower = lancamento.descricao.lower()
        
        for regra in regras:
            criterios = regra.criterios or {}
            palavras = criterios.get('palavras', [])
            modo = criterios.get('modo', 'any')  # 'any' ou 'all'
            
            if not palavras:
                continue
            
            # Verificar se alguma/todas as palavras estão na descrição
            matches = [palavra for palavra in palavras if palavra.lower() in descricao_lower]
            
            if modo == 'any' and len(matches) > 0:
                sugestoes.append({
                    'dre_subcategoria_id': regra.dre_subcategoria_id,
                    'subcategoria_nome': regra.dre_subcategoria.nome if regra.dre_subcategoria else 'N/A',
                    'confianca': regra.confianca,
                    'regra_id': regra.id,
                    'regra_nome': regra.nome,
                    'motivo': f'Palavra-chave encontrada: {", ".join(matches)}',
                    'aplicar_automaticamente': not regra.sugerir_apenas
                })
            elif modo == 'all' and len(matches) == len(palavras):
                sugestoes.append({
                    'dre_subcategoria_id': regra.dre_subcategoria_id,
                    'subcategoria_nome': regra.dre_subcategoria.nome if regra.dre_subcategoria else 'N/A',
                    'confianca': regra.confianca,
                    'regra_id': regra.id,
                    'regra_nome': regra.nome,
                    'motivo': f'Todas as palavras-chave encontradas',
                    'aplicar_automaticamente': not regra.sugerir_apenas
                })
        
        return sugestoes
    
    def _aplicar_regras_tipo_documento(self, lancamento) -> List[Dict]:
        """Aplica regras baseadas no tipo de documento"""
        if not hasattr(lancamento, 'tipo_documento') or not lancamento.tipo_documento:
            return []
        
        regras = self.db.query(RegraClassificacaoDRE).filter(
            RegraClassificacaoDRE.tenant_id == self.tenant_id,
            RegraClassificacaoDRE.tipo_regra == TipoRegraClassificacao.TIPO_DOCUMENTO,
            RegraClassificacaoDRE.ativo.is_(True)
        ).all()
        
        sugestoes = []
        
        for regra in regras:
            criterios = regra.criterios or {}
            tipo_doc_regra = criterios.get('tipo_documento', '').lower()
            
            if tipo_doc_regra == lancamento.tipo_documento.lower():
                sugestoes.append({
                    'dre_subcategoria_id': regra.dre_subcategoria_id,
                    'subcategoria_nome': regra.dre_subcategoria.nome if regra.dre_subcategoria else 'N/A',
                    'confianca': regra.confianca,
                    'regra_id': regra.id,
                    'regra_nome': regra.nome,
                    'motivo': f'Tipo de documento: {lancamento.tipo_documento}',
                    'aplicar_automaticamente': not regra.sugerir_apenas
                })
        
        return sugestoes
    
    def _aplicar_regras_combo(self, lancamento) -> List[Dict]:
        """Aplica regras combo (múltiplos critérios)"""
        regras = self.db.query(RegraClassificacaoDRE).filter(
            RegraClassificacaoDRE.tenant_id == self.tenant_id,
            RegraClassificacaoDRE.tipo_regra == TipoRegraClassificacao.COMBO,
            RegraClassificacaoDRE.ativo.is_(True)
        ).all()
        
        sugestoes = []
        descricao_lower = lancamento.descricao.lower()
        
        # Obter beneficiário do relacionamento correto
        beneficiario = None
        if hasattr(lancamento, 'fornecedor') and lancamento.fornecedor:
            beneficiario = lancamento.fornecedor.nome
        elif hasattr(lancamento, 'cliente') and lancamento.cliente:
            beneficiario = lancamento.cliente.nome
        
        for regra in regras:
            criterios = regra.criterios or {}
            score = 0
            total_criterios = 0
            motivos = []
            
            # Checar beneficiário
            if 'beneficiario' in criterios:
                total_criterios += 1
                if beneficiario and criterios['beneficiario'].lower() in beneficiario.lower():
                    score += 1
                    motivos.append(f"Beneficiário: {beneficiario}")
            
            # Checar palavras-chave
            if 'palavras' in criterios:
                total_criterios += 1
                palavras = criterios['palavras']
                matches = [p for p in palavras if p.lower() in descricao_lower]
                if matches:
                    score += 1
                    motivos.append(f"Palavra-chave: {', '.join(matches)}")
            
            # Checar tipo documento
            if 'tipo_documento' in criterios:
                total_criterios += 1
                if hasattr(lancamento, 'tipo_documento') and lancamento.tipo_documento:
                    if criterios['tipo_documento'].lower() == lancamento.tipo_documento.lower():
                        score += 1
                        motivos.append(f"Tipo: {lancamento.tipo_documento}")
            
            # Se todos os critérios foram atendidos, adicionar sugestão
            if score == total_criterios and score > 0:
                sugestoes.append({
                    'dre_subcategoria_id': regra.dre_subcategoria_id,
                    'subcategoria_nome': regra.dre_subcategoria.nome if regra.dre_subcategoria else 'N/A',
                    'confianca': regra.confianca,
                    'regra_id': regra.id,
                    'regra_nome': regra.nome,
                    'motivo': ' | '.join(motivos),
                    'aplicar_automaticamente': not regra.sugerir_apenas
                })
        
        return sugestoes
    
    def _sugerir_por_historico(self, lancamento, tipo: str) -> List[Dict]:
        """
        Sugere classificação baseada em histórico de lançamentos similares
        (aprendizado de máquina simples)
        """
        # Buscar lançamentos similares no histórico
        historicos = self.db.query(HistoricoClassificacao).filter(
            HistoricoClassificacao.tenant_id == self.tenant_id,
            HistoricoClassificacao.tipo_lancamento == tipo,
            HistoricoClassificacao.usuario_aceitou.is_(True)
        )
        
        # Filtrar por beneficiário se existir
        beneficiario = None
        if hasattr(lancamento, 'fornecedor') and lancamento.fornecedor:
            beneficiario = lancamento.fornecedor.nome
        elif hasattr(lancamento, 'cliente') and lancamento.cliente:
            beneficiario = lancamento.cliente.nome
        
        if beneficiario:
            historicos = historicos.filter(
                HistoricoClassificacao.beneficiario.ilike(f'%{beneficiario}%')
            )
        
        # Agrupar por subcategoria e contar
        resultados = historicos.with_entities(
            HistoricoClassificacao.dre_subcategoria_id,
            func.count(HistoricoClassificacao.id).label('qtd')
        ).group_by(
            HistoricoClassificacao.dre_subcategoria_id
        ).order_by(
            func.count(HistoricoClassificacao.id).desc()
        ).limit(3).all()
        
        sugestoes = []
        for subcat_id, qtd in resultados:
            if qtd >= 2:  # Mínimo 2 ocorrências para sugerir
                subcategoria = self.db.query(DRESubcategoria).filter(
                    DRESubcategoria.id == subcat_id
                ).first()
                
                if subcategoria:
                    confianca = min(50 + (qtd * 10), 95)  # Aumenta com mais ocorrências
                    
                    sugestoes.append({
                        'dre_subcategoria_id': subcat_id,
                        'subcategoria_nome': subcategoria.nome,
                        'confianca': confianca,
                        'regra_id': None,
                        'regra_nome': 'Aprendizado (Histórico)',
                        'motivo': f'Baseado em {qtd} classificações similares anteriores',
                        'aplicar_automaticamente': False  # Sempre sugerir, nunca aplicar auto
                    })
        
        return sugestoes
    
    def _consolidar_sugestoes(self, sugestoes: List[Dict]) -> List[Dict]:
        """Remove duplicatas, mantendo a de maior confiança"""
        consolidadas = {}
        
        for sug in sugestoes:
            subcat_id = sug['dre_subcategoria_id']
            
            if subcat_id not in consolidadas:
                consolidadas[subcat_id] = sug
            else:
                # Manter a de maior confiança
                if sug['confianca'] > consolidadas[subcat_id]['confianca']:
                    consolidadas[subcat_id] = sug
        
        return list(consolidadas.values())
    
    # ================================================================
    # APLICAÇÃO DE CLASSIFICAÇÃO
    # ================================================================
    
    def aplicar_classificacao(
        self,
        tipo: str,  # 'pagar' ou 'receber'
        lancamento_id: int,
        dre_subcategoria_id: int,
        canal: Optional[str] = None,
        regra_id: Optional[int] = None,
        forma_classificacao: str = 'manual',  # manual, automatico_regra, sugestao_aceita
        user_id: Optional[int] = None
    ) -> bool:
        """
        Aplica uma classificação DRE a um lançamento e registra no histórico
        
        Returns:
            bool: True se sucesso, False se erro
        """
        try:
            # Buscar lançamento
            if tipo == 'pagar':
                lancamento = self.db.query(ContaPagar).filter(
                    ContaPagar.id == lancamento_id,
                    ContaPagar.tenant_id == self.tenant_id
                ).first()
            else:
                lancamento = self.db.query(ContaReceber).filter(
                    ContaReceber.id == lancamento_id,
                    ContaReceber.tenant_id == self.tenant_id
                ).first()
            
            if not lancamento:
                logger.error(f"Lançamento {tipo} #{lancamento_id} não encontrado")
                return False
            
            # Validar subcategoria
            subcategoria = self.db.query(DRESubcategoria).filter(
                DRESubcategoria.id == dre_subcategoria_id,
                DRESubcategoria.tenant_id == self.tenant_id
            ).first()
            
            if not subcategoria:
                logger.error(f"Subcategoria DRE #{dre_subcategoria_id} não encontrada")
                return False
            
            # Aplicar classificação
            lancamento.dre_subcategoria_id = dre_subcategoria_id
            if canal:
                lancamento.canal = canal
            
            # Registrar no histórico
            historico = HistoricoClassificacao(
                tenant_id=self.tenant_id,
                tipo_lancamento=tipo,
                lancamento_id=lancamento_id,
                dre_subcategoria_id=dre_subcategoria_id,
                canal=canal,
                forma_classificacao=forma_classificacao,
                regra_aplicada_id=regra_id,
                descricao=lancamento.descricao,
                beneficiario=getattr(lancamento, 'beneficiario', None),
                tipo_documento=getattr(lancamento, 'tipo_documento', None),
                valor=int(lancamento.valor_original * 100),  # Centavos
                usuario_aceitou=True,
                classificado_por_user_id=user_id
            )
            
            self.db.add(historico)
            
            # Atualizar estatísticas da regra (se aplicável)
            if regra_id:
                regra = self.db.query(RegraClassificacaoDRE).filter(
                    RegraClassificacaoDRE.id == regra_id
                ).first()
                
                if regra:
                    regra.aplicacoes_sucesso += 1
            
            self.db.commit()
            
            logger.info(f"✅ Classificação aplicada: {tipo} #{lancamento_id} → {subcategoria.nome}")
            
            # Verificar se deve criar regra automática
            self._avaliar_criar_regra_automatica(lancamento, tipo, dre_subcategoria_id)
            
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Erro ao aplicar classificação: {e}")
            return False
    
    def _avaliar_criar_regra_automatica(
        self, 
        lancamento, 
        tipo: str, 
        dre_subcategoria_id: int
    ):
        """
        Avalia se deve criar uma regra automática baseada em padrões
        Cria regra se houver 3+ lançamentos similares com mesma classificação
        """
        # Obter beneficiário do relacionamento correto
        beneficiario = None
        if hasattr(lancamento, 'fornecedor') and lancamento.fornecedor:
            beneficiario = lancamento.fornecedor.nome
        elif hasattr(lancamento, 'cliente') and lancamento.cliente:
            beneficiario = lancamento.cliente.nome
        
        if not beneficiario:
            return
        
        # Contar lançamentos similares
        count = self.db.query(HistoricoClassificacao).filter(
            HistoricoClassificacao.tenant_id == self.tenant_id,
            HistoricoClassificacao.tipo_lancamento == tipo,
            HistoricoClassificacao.beneficiario == beneficiario,
            HistoricoClassificacao.dre_subcategoria_id == dre_subcategoria_id,
            HistoricoClassificacao.usuario_aceitou.is_(True)
        ).count()
        
        if count >= 3:
            # Verificar se já existe regra
            regra_existente = self.db.query(RegraClassificacaoDRE).filter(
                RegraClassificacaoDRE.tenant_id == self.tenant_id,
                RegraClassificacaoDRE.tipo_regra == TipoRegraClassificacao.BENEFICIARIO,
                RegraClassificacaoDRE.criterios['beneficiario'].astext == beneficiario
            ).first()
            
            if not regra_existente:
                # Criar nova regra
                nova_regra = RegraClassificacaoDRE(
                    tenant_id=self.tenant_id,
                    nome=f"Pagamentos para {beneficiario}",
                    descricao=f"Regra criada automaticamente após {count} classificações",
                    tipo_regra=TipoRegraClassificacao.BENEFICIARIO,
                    origem=OrigemRegra.APRENDIZADO,
                    criterios={'beneficiario': beneficiario},
                    dre_subcategoria_id=dre_subcategoria_id,
                    prioridade=80,
                    confianca=70 + min(count * 5, 25),  # 70-95%
                    ativo=True,
                    sugerir_apenas=True  # Por segurança, apenas sugere
                )
                
                self.db.add(nova_regra)
                self.db.commit()
                
                logger.info(f"🤖 Regra automática criada: {nova_regra.nome}")
    
    # ================================================================
    # LISTAGEM DE PENDENTES
    # ================================================================
    
    def listar_pendentes(
        self, 
        tipo: Optional[str] = None,  # None = ambos, 'pagar', 'receber'
        limit: int = 100
    ) -> Dict:
        """
        Lista lançamentos sem classificação DRE
        
        Returns:
            Dict: {
                'total_pendentes': int,
                'contas_pagar': List[Dict],
                'contas_receber': List[Dict]
            }
        """
        resultado = {
            'total_pendentes': 0,
            'contas_pagar': [],
            'contas_receber': []
        }
        
        # Contas a Pagar
        if tipo is None or tipo == 'pagar':
            # FILTRAR: Apenas lançamentos de fornecedores que CONTROLAM DRE
            # (Exclui fornecedores de produtos para revenda como Buendia)
            from app.models import Cliente
            pendentes_pagar = self.db.query(ContaPagar).outerjoin(
                Cliente,
                ContaPagar.fornecedor_id == Cliente.id
            ).filter(
                ContaPagar.tenant_id == self.tenant_id,
                ContaPagar.dre_subcategoria_id.is_(None),
                ContaPagar.status != 'cancelado',
                or_(
                    Cliente.controla_dre.is_(True),  # Fornecedor controla DRE
                    ContaPagar.fornecedor_id.is_(None)  # Sem fornecedor = controla DRE
                )
            ).order_by(ContaPagar.data_vencimento.desc()).limit(limit).all()
            
            for cp in pendentes_pagar:
                # Obter nome do fornecedor se existir
                beneficiario = None
                fornecedor_id = None
                if cp.fornecedor:
                    beneficiario = cp.fornecedor.nome
                    fornecedor_id = cp.fornecedor_id
                
                resultado['contas_pagar'].append({
                    'id': cp.id,
                    'descricao': cp.descricao,
                    'beneficiario': beneficiario,
                    'fornecedor_id': fornecedor_id,
                    'valor': float(cp.valor_original),
                    'data_vencimento': cp.data_vencimento.isoformat() if cp.data_vencimento else None,
                    'tipo_documento': getattr(cp, 'tipo_documento', None),
                    'nota_entrada_id': cp.nota_entrada_id
                })
        
        # Contas a Receber
        if tipo is None or tipo == 'receber':
            # FILTRAR: Apenas lançamentos de clientes que CONTROLAM DRE
            from app.models import Cliente
            pendentes_receber = self.db.query(ContaReceber).outerjoin(
                Cliente,
                ContaReceber.cliente_id == Cliente.id
            ).filter(
                ContaReceber.tenant_id == self.tenant_id,
                ContaReceber.dre_subcategoria_id.is_(None),
                ContaReceber.status != 'cancelado',
                or_(
                    Cliente.controla_dre.is_(True),  # Cliente controla DRE
                    ContaReceber.cliente_id.is_(None)  # Sem cliente = controla DRE
                )
            ).order_by(ContaReceber.data_vencimento.desc()).limit(limit).all()
            
            for cr in pendentes_receber:
                # Obter nome do cliente se existir
                beneficiario = None
                cliente_id = None
                if cr.cliente:
                    beneficiario = cr.cliente.nome
                    cliente_id = cr.cliente_id
                
                resultado['contas_receber'].append({
                    'id': cr.id,
                    'descricao': cr.descricao,
                    'beneficiario': beneficiario,
                    'cliente_id': cliente_id,
                    'valor': float(cr.valor_original),
                    'data_vencimento': cr.data_vencimento.isoformat() if cr.data_vencimento else None,
                    'tipo_documento': getattr(cr, 'tipo_documento', None),
                    'venda_id': cr.venda_id
                })
        
        resultado['total_pendentes'] = len(resultado['contas_pagar']) + len(resultado['contas_receber'])
        
        return resultado
