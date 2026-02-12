"""
Serviço de Gestão de Estoque
Responsável por todas as operações de estoque: baixa, estorno, validação e FIFO de lotes

REGRAS:
- Recebe sempre (db: Session) - NÃO faz commit
- Usa apenas db.flush() quando necessário
- Retorna dicts estruturados
- NÃO conhece regras de venda, caixa ou financeiro
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Dict, List, Optional
from decimal import Decimal
import json
import logging

from app.produtos_models import Produto, ProdutoLote, EstoqueMovimentacao

logger = logging.getLogger(__name__)


class EstoqueService:
    """Service isolado para operações de estoque"""
    
    @staticmethod
    def validar_disponibilidade(
        produto_id: int,
        quantidade: float,
        db: Session
    ) -> Dict:
        """
        Valida se há estoque disponível para um produto
        
        Args:
            produto_id: ID do produto
            quantidade: Quantidade desejada
            db: Sessão do banco (NÃO faz commit)
            
        Returns:
            dict com:
                - disponivel: bool
                - estoque_atual: float
                - estoque_necessario: float
                - mensagem: str (se indisponível)
        """
        produto = db.query(Produto).get(produto_id)
        
        if not produto:
            return {
                'disponivel': False,
                'estoque_atual': 0,
                'estoque_necessario': quantidade,
                'mensagem': f'Produto ID {produto_id} não encontrado'
            }
        
        estoque_atual = produto.estoque_atual or 0
        disponivel = estoque_atual >= quantidade
        
        return {
            'disponivel': disponivel,
            'estoque_atual': estoque_atual,
            'estoque_necessario': quantidade,
            'mensagem': None if disponivel else f'Estoque insuficiente. Disponível: {estoque_atual}, Necessário: {quantidade}'
        }
    
    @staticmethod
    def baixar_estoque(
        produto_id: int,
        quantidade: float,
        motivo: str,
        referencia_id: int,
        referencia_tipo: str,
        user_id: int,
        db: Session,
        tenant_id: str,
        documento: Optional[str] = None,
        observacao: Optional[str] = None
    ) -> Dict:
        """
        Baixa estoque de um produto com FIFO de lotes
        
        Args:
            produto_id: ID do produto
            quantidade: Quantidade a baixar
            motivo: Motivo da baixa (venda, ajuste, perda, etc)
            referencia_id: ID da entidade que originou (ex: venda_id)
            referencia_tipo: Tipo da referência (venda, ajuste, etc)
            user_id: ID do usuário
            db: Sessão do banco (NÃO faz commit)
            documento: Número do documento (opcional)
            observacao: Observação adicional (opcional)
            
        Returns:
            dict com:
                - sucesso: bool
                - estoque_anterior: float
                - estoque_novo: float
                - lotes_consumidos: List[dict]
                - movimentacao_id: int
                - mensagem: str (se erro)
                
        Raises:
            ValueError: Se estoque insuficiente ou produto não encontrado
        """
        produto = db.query(Produto).get(produto_id)
        
        if not produto:
            raise ValueError(f'Produto ID {produto_id} não encontrado')
        
        # 🔒 VALIDAÇÃO CRÍTICA: Produto PAI não pode movimentar estoque
        if produto.tipo_produto == 'PAI':
            raise ValueError(
                f"Produto '{produto.nome}' é do tipo PAI e não pode ter estoque movimentado. "
                f"Movimente o estoque das variações."
            )
        
        estoque_anterior = produto.estoque_atual or 0
        
        # 🔒 VALIDAR DISPONIBILIDADE DE ESTOQUE (com configuração de estoque negativo)
        if estoque_anterior < quantidade:
            # Buscar configuração do tenant
            from app.models import Tenant
            tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
            
            # Se o tenant não permite estoque negativo, bloquear a operação
            if not tenant or not tenant.permite_estoque_negativo:
                raise ValueError(
                    f'Estoque insuficiente para produto {produto.nome}. '
                    f'Disponível: {estoque_anterior}, Necessário: {quantidade}'
                )
            
            # 🟢 MODELO CONTROLADO: Registrar alerta de estoque negativo
            from app.estoque_models import AlertaEstoqueNegativo
            
            estoque_resultante = estoque_anterior - quantidade
            
            # Criar alerta persistente
            alerta = AlertaEstoqueNegativo(
                tenant_id=tenant_id,
                produto_id=produto.id,
                produto_nome=produto.nome,
                estoque_anterior=estoque_anterior,
                quantidade_vendida=quantidade,
                estoque_resultante=estoque_resultante,
                venda_id=contexto.get('venda_id') if contexto else None,
                venda_codigo=contexto.get('venda_codigo') if contexto else None,
                critico=(estoque_resultante < -5),  # Crítico se < -5 unidades
                status='pendente'
            )
            db.add(alerta)
            db.flush()  # Garante que foi salvo
            
            # Logar aviso detalhado
            logger.warning(
                f'⚠️ ESTOQUE NEGATIVO REGISTRADO [ID: {alerta.id}]: '
                f'Produto {produto.nome} - '
                f'Disponível: {estoque_anterior}, Necessário: {quantidade}, '
                f'Ficará com: {estoque_resultante} '
                f'{"🔴 CRÍTICO" if alerta.critico else "⚠️ ATENÇÃO"}'
            )
        
        # FIFO: Consumir lotes se existirem
        lotes_consumidos = []
        lotes_ativos = db.query(ProdutoLote).filter(
            ProdutoLote.produto_id == produto.id,
            ProdutoLote.quantidade_disponivel > 0,
            ProdutoLote.status == 'ativo'
        ).order_by(ProdutoLote.ordem_entrada).all()
        
        if lotes_ativos:
            quantidade_restante = quantidade
            
            for lote in lotes_ativos:
                if quantidade_restante <= 0:
                    break
                
                saldo_anterior = lote.quantidade_disponivel
                qtd_consumir = min(lote.quantidade_disponivel, quantidade_restante)
                
                # Baixar do lote
                lote.quantidade_disponivel -= qtd_consumir
                quantidade_restante -= qtd_consumir
                
                # Marcar como esgotado se zerou
                if lote.quantidade_disponivel == 0:
                    lote.status = 'esgotado'
                
                lotes_consumidos.append({
                    "lote_id": lote.id,
                    "nome_lote": lote.nome_lote,
                    "quantidade": qtd_consumir,
                    "saldo_anterior": saldo_anterior
                })
                
                logger.info(
                    f"Lote consumido: {lote.nome_lote} - "
                    f"Qtd: {qtd_consumir} (Saldo: {lote.quantidade_disponivel})"
                )
        
        # Baixar estoque total do produto
        produto.estoque_atual -= quantidade
        estoque_novo = produto.estoque_atual
        
        # Criar movimentação de estoque
        movimentacao = EstoqueMovimentacao(
            produto_id=produto.id,
            tipo='saida',
            motivo=motivo,
            quantidade=quantidade,
            quantidade_anterior=estoque_anterior,
            quantidade_nova=estoque_novo,
            custo_unitario=produto.preco_custo,
            valor_total=quantidade * (produto.preco_custo or 0),
            lotes_consumidos=json.dumps(lotes_consumidos) if lotes_consumidos else None,
            documento=documento,
            referencia_id=referencia_id,
            referencia_tipo=referencia_tipo,
            observacao=observacao,
            user_id=user_id,
            tenant_id=tenant_id
        )
        db.add(movimentacao)
        db.flush()  # Gera ID mas não commita
        
        logger.info(
            f"Estoque baixado: Produto {produto.nome} - "
            f"Qtd: {quantidade} ({estoque_anterior} → {estoque_novo})"
        )
        
        return {
            'sucesso': True,
            'estoque_anterior': estoque_anterior,
            'estoque_novo': estoque_novo,
            'lotes_consumidos': lotes_consumidos,
            'movimentacao_id': movimentacao.id,
            'produto_nome': produto.nome
        }
    
    @staticmethod
    def estornar_estoque(
        produto_id: int,
        quantidade: float,
        motivo: str,
        referencia_id: int,
        referencia_tipo: str,
        user_id: int,
        db: Session,
        tenant_id: str,
        documento: Optional[str] = None,
        observacao: Optional[str] = None
    ) -> Dict:
        """
        Devolve estoque ao produto (usado em devolução/cancelamento)
        
        Args:
            produto_id: ID do produto
            quantidade: Quantidade a devolver
            motivo: Motivo do estorno (devolucao, cancelamento, ajuste)
            referencia_id: ID da entidade que originou
            referencia_tipo: Tipo da referência
            user_id: ID do usuário
            db: Sessão do banco (NÃO faz commit)
            documento: Número do documento (opcional)
            observacao: Observação adicional (opcional)
            
        Returns:
            dict com:
                - sucesso: bool
                - estoque_anterior: float
                - estoque_novo: float
                - movimentacao_id: int
                - mensagem: str (se erro)
                
        Raises:
            ValueError: Se produto não encontrado
        """
        produto = db.query(Produto).get(produto_id)
        
        if not produto:
            raise ValueError(f'Produto ID {produto_id} não encontrado')
        
        # 🔒 VALIDAÇÃO CRÍTICA: Produto PAI não pode movimentar estoque
        if produto.tipo_produto == 'PAI':
            raise ValueError(
                f"Produto '{produto.nome}' é do tipo PAI e não pode ter estoque movimentado. "
                f"Movimente o estoque das variações."
            )
        
        estoque_anterior = produto.estoque_atual or 0
        
        # Adicionar ao estoque
        produto.estoque_atual += quantidade
        estoque_novo = produto.estoque_atual
        
        # Criar movimentação de estoque (entrada)
        movimentacao = EstoqueMovimentacao(
            produto_id=produto.id,
            tipo='entrada',
            motivo=motivo,
            quantidade=quantidade,
            quantidade_anterior=estoque_anterior,
            quantidade_nova=estoque_novo,
            custo_unitario=produto.preco_custo,
            valor_total=quantidade * (produto.preco_custo or 0),
            lotes_consumidos=None,  # Estorno não usa lotes
            documento=documento,
            referencia_id=referencia_id,
            referencia_tipo=referencia_tipo,
            observacao=observacao,
            user_id=user_id,
            tenant_id=tenant_id
        )
        db.add(movimentacao)
        db.flush()  # Gera ID mas não commita
        
        logger.info(
            f"Estoque estornado: Produto {produto.nome} - "
            f"Qtd: +{quantidade} ({estoque_anterior} → {estoque_novo})"
        )
        
        return {
            'sucesso': True,
            'estoque_anterior': estoque_anterior,
            'estoque_novo': estoque_novo,
            'movimentacao_id': movimentacao.id,
            'produto_nome': produto.nome
        }
    
    @staticmethod
    def validar_disponibilidade_multiplos(
        itens: List[Dict],
        db: Session
    ) -> Dict:
        """
        Valida disponibilidade de múltiplos produtos de uma vez
        
        Args:
            itens: Lista de dicts com produto_id e quantidade
            db: Sessão do banco
            
        Returns:
            dict com:
                - todos_disponiveis: bool
                - itens_validados: List[dict]
                - itens_indisponiveis: List[dict]
        """
        itens_validados = []
        itens_indisponiveis = []
        
        for item in itens:
            produto_id = item.get('produto_id')
            quantidade = item.get('quantidade', 0)
            
            if not produto_id or quantidade <= 0:
                continue
            
            validacao = EstoqueService.validar_disponibilidade(
                produto_id=produto_id,
                quantidade=quantidade,
                db=db
            )
            
            validacao['produto_id'] = produto_id
            validacao['quantidade_solicitada'] = quantidade
            
            if validacao['disponivel']:
                itens_validados.append(validacao)
            else:
                itens_indisponiveis.append(validacao)
        
        return {
            'todos_disponiveis': len(itens_indisponiveis) == 0,
            'total_itens': len(itens),
            'itens_validados': itens_validados,
            'itens_indisponiveis': itens_indisponiveis
        }
    
    @staticmethod
    def baixar_estoque_multiplos(
        itens: List[Dict],
        motivo: str,
        referencia_id: int,
        referencia_tipo: str,
        user_id: int,
        tenant_id: str,
        db: Session
    ) -> Dict:
        """
        Baixa estoque de múltiplos produtos de uma vez (transação única)
        
        Args:
            itens: Lista de dicts com produto_id e quantidade
            motivo: Motivo da baixa
            referencia_id: ID da referência
            referencia_tipo: Tipo da referência
            user_id: ID do usuário
            db: Sessão do banco (NÃO faz commit)
            
        Returns:
            dict com:
                - sucesso: bool
                - total_itens: int
                - itens_baixados: List[dict]
                - erros: List[dict]
        """
        itens_baixados = []
        erros = []
        
        for item in itens:
            produto_id = item.get('produto_id')
            quantidade = item.get('quantidade', 0)
            
            if not produto_id or quantidade <= 0:
                continue
            
            try:
                resultado = EstoqueService.baixar_estoque(
                    produto_id=produto_id,
                    quantidade=quantidade,
                    motivo=motivo,
                    referencia_id=referencia_id,
                    referencia_tipo=referencia_tipo,
                    user_id=user_id,
                    tenant_id=tenant_id,
                    db=db
                )
                itens_baixados.append(resultado)
                
            except ValueError as e:
                erros.append({
                    'produto_id': produto_id,
                    'quantidade': quantidade,
                    'erro': str(e)
                })
                logger.error(f"Erro ao baixar estoque produto {produto_id}: {e}")
        
        return {
            'sucesso': len(erros) == 0,
            'total_itens': len(itens),
            'itens_baixados': itens_baixados,
            'erros': erros
        }
