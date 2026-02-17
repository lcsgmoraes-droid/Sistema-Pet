# -*- coding: utf-8 -*-
"""
Serviço Principal de Importação de Extrato - ABA 7
Orquestra: Parser → NLP → IA → Linkagem → Validação
Referência: ROADMAP_IA_AMBICOES.md (implementação completa)
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import Dict, List, Optional, BinaryIO
from datetime import datetime, timedelta
import hashlib
from decimal import Decimal

from app.ia.aba7_extrato_models import (
    ArquivoExtratoImportado,
    LancamentoImportado,
    PadraoCategoriacaoIA
)
from app.ia.extrato_parser import ExtratoParser
from app.ia.extrato_nlp import ExtratoNLP
from app.ia.extrato_ia import MotorCategorizacaoIA
from app.financeiro_models import ContaPagar, ContaReceber, LancamentoManual, CategoriaFinanceira


class ServicoImportacaoExtrato:
    """
    Serviço completo de importação de extrato bancário.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.parser = ExtratoParser()
        self.nlp = ExtratoNLP()
        self.ia = MotorCategorizacaoIA(db)
    
    def importar_extrato(
        self,
        arquivo: bytes,
        nome_arquivo: str,
        user_id: int,
        conta_bancaria_id: Optional[int] = None
    ) -> Dict:
        """
        Fluxo completo de importação.
        
        Retorna:
            {
                'arquivo_id': int,
                'total_transacoes': int,
                'categorizadas_automaticamente': int,
                'necessitam_revisao': int,
                'duplicadas_ignoradas': int,
                'tempo_processamento': float
            }
        """
        inicio = datetime.now()
        
        # 1. Verificar hash do arquivo (evitar duplicatas)
        hash_arquivo = self._calcular_hash(arquivo)
        arquivo_existente = self.db.query(ArquivoExtratoImportado).filter_by(
            hash_arquivo=hash_arquivo
        ).first()
        
        if arquivo_existente:
            raise ValueError(f"Arquivo já foi importado em {arquivo_existente.data_upload}")
        
        # 2. Parse do arquivo
        try:
            transacoes, metadados = self.parser.parse(arquivo, nome_arquivo)
        except Exception as e:
            raise ValueError(f"Erro ao processar arquivo: {str(e)}")
        
        if not transacoes:
            raise ValueError("Nenhuma transação encontrada no arquivo")
        
        # 3. Criar registro do arquivo
        arquivo_registro = ArquivoExtratoImportado(
            nome_arquivo=nome_arquivo,
            tipo_arquivo=metadados['formato'],
            hash_arquivo=hash_arquivo,
            banco_detectado=metadados['banco'],
            total_transacoes=len(transacoes),
            user_id=user_id,
            conta_bancaria_id=conta_bancaria_id,
            data_upload=datetime.now(),
            status='processando'
        )
        self.db.add(arquivo_registro)
        self.db.flush()
        
        # 4. Processar cada transação
        total_categorizadas = 0
        total_necessitam_revisao = 0
        duplicadas = 0
        
        for t in transacoes:
            # Verificar duplicata
            hash_transacao = ExtratoParser.gerar_hash_transacao(
                t['data'], t['descricao'], t['valor']
            )
            
            existe = self.db.query(LancamentoImportado).filter_by(
                hash_transacao=hash_transacao
            ).first()
            
            if existe:
                duplicadas += 1
                continue
            
            # NLP: extrair dados
            dados_nlp = self.nlp.extrair_dados(t['descricao'])
            
            # IA: categorizar
            resultado_ia = self.ia.categorizar_transacao(
                data=t['data'],
                descricao=t['descricao'],
                valor=t['valor'],
                tipo=t['tipo']
            )
            
            # Linkagem automática
            linkagem = self._tentar_linkagem_automatica(
                data=t['data'],
                valor=t['valor'],
                tipo=t['tipo'],
                cnpj_cpf=dados_nlp['cnpj'] or dados_nlp['cpf']
            )
            
            # Criar lançamento importado
            lancamento = LancamentoImportado(
                arquivo_id=arquivo_registro.id,
                data_transacao=t['data'],
                descricao_original=t['descricao'],
                valor=Decimal(str(t['valor'])),
                tipo=t['tipo'],
                tipo_transacao=dados_nlp['tipo_transacao'],
                cnpj_cpf_extraido=dados_nlp['cnpj'] or dados_nlp['cpf'],
                beneficiario_extraido=dados_nlp['beneficiario'],
                codigo_barras=dados_nlp['codigo_barras'],
                categoria_financeira_id=resultado_ia['categoria_id'],
                padrao_sugerido_id=resultado_ia['padrao_usado_id'],
                confianca_ia=resultado_ia['confianca'],
                categorias_alternativas=resultado_ia['alternativas'],
                status_validacao='pendente',
                confirmado_usuario=False,
                conta_pagar_id=linkagem.get('conta_pagar_id'),
                conta_receber_id=linkagem.get('conta_receber_id'),
                linkagem_automatica=linkagem.get('automatica', False),
                confianca_linkagem=linkagem.get('confianca', 0.0),
                hash_transacao=hash_transacao,
                user_id=user_id
            )
            
            self.db.add(lancamento)
            
            # Contadores
            if resultado_ia['confianca'] >= 0.7:
                total_categorizadas += 1
            else:
                total_necessitam_revisao += 1
        
        # 5. Atualizar registro do arquivo
        arquivo_registro.total_categorizado_automatico = total_categorizadas
        arquivo_registro.total_precisa_revisao = total_necessitam_revisao
        arquivo_registro.tempo_processamento_segundos = (datetime.now() - inicio).total_seconds()
        arquivo_registro.status = 'concluido'
        
        self.db.commit()
        
        return {
            'arquivo_id': arquivo_registro.id,
            'total_transacoes': len(transacoes),
            'categorizadas_automaticamente': total_categorizadas,
            'necessitam_revisao': total_necessitam_revisao,
            'duplicadas_ignoradas': duplicadas,
            'tempo_processamento': arquivo_registro.tempo_processamento_segundos
        }
    
    def _tentar_linkagem_automatica(
        self,
        data: datetime,
        valor: float,
        tipo: str,
        cnpj_cpf: Optional[str]
    ) -> Dict:
        """
        Tenta vincular transação com contas a pagar/receber.
        
        Retorna:
            {
                'conta_pagar_id': int ou None,
                'conta_receber_id': int ou None,
                'automatica': bool,
                'confianca': float
            }
        """
        # Margem de 3 dias
        data_min = data - timedelta(days=3)
        data_max = data + timedelta(days=3)
        
        # Tolerância de valor: ±2%
        valor_min = valor * 0.98
        valor_max = valor * 1.02
        
        if tipo == 'saida':
            # Buscar conta a pagar
            query = self.db.query(ContaPagar).filter(
                ContaPagar.data_vencimento >= data_min,
                ContaPagar.data_vencimento <= data_max,
                ContaPagar.valor_total >= valor_min,
                ContaPagar.valor_total <= valor_max,
                ContaPagar.status != 'pago'
            )
            
            if cnpj_cpf:
                # Filtrar por fornecedor (se tiver CNPJ)
                # TODO: Adicionar join com fornecedores
                pass
            
            conta = query.first()
            
            if conta:
                # Verificar confiança
                confianca = self._calcular_confianca_linkagem(
                    data, valor, conta.data_vencimento, float(conta.valor_total)
                )
                
                return {
                    'conta_pagar_id': conta.id,
                    'conta_receber_id': None,
                    'automatica': confianca >= 0.8,
                    'confianca': confianca
                }
        
        elif tipo == 'entrada':
            # Buscar conta a receber
            query = self.db.query(ContaReceber).filter(
                ContaReceber.data_vencimento >= data_min,
                ContaReceber.data_vencimento <= data_max,
                ContaReceber.valor_total >= valor_min,
                ContaReceber.valor_total <= valor_max,
                ContaReceber.status != 'recebido'
            )
            
            conta = query.first()
            
            if conta:
                confianca = self._calcular_confianca_linkagem(
                    data, valor, conta.data_vencimento, float(conta.valor_total)
                )
                
                return {
                    'conta_pagar_id': None,
                    'conta_receber_id': conta.id,
                    'automatica': confianca >= 0.8,
                    'confianca': confianca
                }
        
        return {
            'conta_pagar_id': None,
            'conta_receber_id': None,
            'automatica': False,
            'confianca': 0.0
        }
    
    def _calcular_confianca_linkagem(
        self,
        data1: datetime,
        valor1: float,
        data2: datetime,
        valor2: float
    ) -> float:
        """
        Calcula confiança da linkagem (0.0-1.0).
        """
        # Diferença de dias
        diff_dias = abs((data1 - data2).days)
        score_data = max(0, 1.0 - (diff_dias / 3))  # 0 dias = 1.0, 3 dias = 0.0
        
        # Diferença de valor
        diff_valor_pct = abs(valor1 - valor2) / valor2 * 100
        score_valor = max(0, 1.0 - (diff_valor_pct / 2))  # 0% = 1.0, 2% = 0.0
        
        # Média ponderada
        confianca = (score_data * 0.3 + score_valor * 0.7)
        
        return confianca
    
    def _calcular_hash(self, arquivo: bytes) -> str:
        """Calcula MD5 do arquivo."""
        return hashlib.md5(arquivo).hexdigest()
    
    def listar_lancamentos_pendentes(
        self,
        user_id: int,
        limite: int = 50
    ) -> List[Dict]:
        """
        Lista lançamentos que necessitam validação.
        """
        lancamentos = self.db.query(LancamentoImportado).filter(
            LancamentoImportado.user_id == user_id,
            LancamentoImportado.status_validacao == 'pendente'
        ).order_by(
            LancamentoImportado.confianca_ia.asc(),  # Menor confiança primeiro
            LancamentoImportado.data_transacao.desc()
        ).limit(limite).all()
        
        resultado = []
        for lanc in lancamentos:
            categoria = None
            if lanc.categoria_financeira_id:
                categoria = self.db.query(CategoriaFinanceira).filter_by(
                    id=lanc.categoria_financeira_id
                ).first()
            
            resultado.append({
                'id': lanc.id,
                'data': lanc.data_transacao.isoformat(),
                'descricao': lanc.descricao_original,
                'valor': float(lanc.valor),
                'tipo': lanc.tipo,
                'beneficiario': lanc.beneficiario_extraido,
                'tipo_transacao': lanc.tipo_transacao,
                'categoria_sugerida': {
                    'id': categoria.id if categoria else None,
                    'nome': categoria.nome if categoria else None
                },
                'confianca': lanc.confianca_ia,
                'alternativas': lanc.categorias_alternativas,
                'linkado_com': {
                    'conta_pagar_id': lanc.conta_pagar_id,
                    'conta_receber_id': lanc.conta_receber_id,
                    'confianca': lanc.confianca_linkagem
                }
            })
        
        return resultado
    
    def validar_lote(
        self,
        lancamento_ids: List[int],
        user_id: int,
        aprovar: bool = True
    ):
        """
        Valida múltiplos lançamentos de uma vez.
        """
        for lanc_id in lancamento_ids:
            self.ia.validar_categorizacao(
                lancamento_id=lanc_id,
                aprovado=aprovar
            )
    
    def criar_lancamento_financeiro(
        self,
        lancamento_importado_id: int
    ):
        """
        Cria lançamento manual a partir de importado validado.
        """
        importado = self.db.query(LancamentoImportado).filter_by(
            id=lancamento_importado_id
        ).first()
        
        if not importado:
            raise ValueError("Lançamento não encontrado")
        
        if importado.status_validacao != 'aprovado':
            raise ValueError("Lançamento ainda não foi validado")
        
        # Categoria final (pode ter sido corrigida)
        categoria_id = importado.categoria_usuario_id or importado.categoria_financeira_id
        
        if not categoria_id:
            raise ValueError("Lançamento sem categoria")
        
        # Criar lançamento manual
        lancamento = LancamentoManual(
            descricao=importado.descricao_original,
            valor=importado.valor,
            tipo=importado.tipo,
            data_lancamento=importado.data_transacao,
            categoria_id=categoria_id,
            user_id=importado.user_id,
            observacoes=f"Importado de extrato bancário (#{importado.arquivo_id})"
        )
        
        self.db.add(lancamento)
        
        # Marcar como processado
        importado.lancamento_manual_criado_id = lancamento.id
        
        self.db.commit()
        
        return lancamento.id
    
    def obter_historico_importacoes(
        self,
        user_id: int
    ) -> List[Dict]:
        """
        Lista histórico de arquivos importados.
        """
        arquivos = self.db.query(ArquivoExtratoImportado).filter_by(
            user_id=user_id
        ).order_by(
            ArquivoExtratoImportado.data_upload.desc()
        ).all()
        
        resultado = []
        for arq in arquivos:
            resultado.append({
                'id': arq.id,
                'nome_arquivo': arq.nome_arquivo,
                'banco': arq.banco_detectado,
                'data_upload': arq.data_upload.isoformat(),
                'total_transacoes': arq.total_transacoes,
                'categorizadas': arq.total_categorizado_automatico,
                'precisam_revisao': arq.total_precisa_revisao,
                'tempo_processamento': arq.tempo_processamento_segundos,
                'status': arq.status
            })
        
        return resultado
