"""
Models para o módulo de comissões
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
import logging

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from app.db import SessionLocal
from app.utils.tenant_safe_sql import execute_tenant_safe

# Logger
logger = logging.getLogger(__name__)


class ComissoesConfig:
    """Modelo para configuração de comissões"""
    
    @staticmethod
    def listar_por_funcionario(funcionario_id: int) -> List[Dict[str, Any]]:
        """
        Lista todas as configurações de comissão de um funcionário
        
        Args:
            funcionario_id: ID do funcionário
            
        Returns:
            Lista de configurações
        """
        db = SessionLocal()
        try:
            result = db.execute(
                text('''
                    SELECT 
                        cc.*,
                        CASE 
                            WHEN cc.tipo = 'categoria' THEN c.nome
                            WHEN cc.tipo = 'subcategoria' THEN sc.nome
                            WHEN cc.tipo = 'produto' THEN p.nome
                        END as nome_item
                    FROM comissoes_configuracao cc
                    LEFT JOIN categorias c ON cc.tipo = 'categoria' AND cc.referencia_id = c.id
                    LEFT JOIN categorias sc ON cc.tipo = 'subcategoria' AND cc.referencia_id = sc.id
                    LEFT JOIN produtos p ON cc.tipo = 'produto' AND cc.referencia_id = p.id
                    WHERE cc.funcionario_id = :funcionario_id AND cc.ativo = 1
                    ORDER BY cc.tipo, nome_item
                '''),
                {"funcionario_id": funcionario_id}
            )
            
            configs = []
            for row in result.fetchall():
                configs.append(dict(row))
            
            return configs
        finally:
            db.close()
    
    @staticmethod
    def buscar_configuracao(funcionario_id: int, produto_id: int, categoria_id: int = None, 
                           subcategoria_id: int = None) -> Optional[Dict[str, Any]]:
        """
        Busca configuração de comissão aplicável para um produto
        Segue hierarquia: Produto > Subcategoria > Categoria
        
        Args:
            funcionario_id: ID do funcionário
            produto_id: ID do produto
            categoria_id: ID da categoria (opcional)
            subcategoria_id: ID da subcategoria (opcional)
            
        Returns:
            Configuração encontrada ou None
        """
        db = SessionLocal()
        try:
            # 1. Tentar buscar por produto específico
            result = db.execute(
                text('''
                    SELECT * FROM comissoes_configuracao
                    WHERE funcionario_id = :funcionario_id 
                    AND tipo = 'produto' 
                    AND referencia_id = :produto_id
                    AND ativo = 1
                    LIMIT 1
                '''),
                {"funcionario_id": funcionario_id, "produto_id": produto_id}
            )
            
            config = result.fetchone()
            if config:
                return dict(config)
            
            # 2. Tentar buscar por subcategoria
            if subcategoria_id:
                result = db.execute(
                    text('''
                        SELECT * FROM comissoes_configuracao
                        WHERE funcionario_id = :funcionario_id 
                        AND tipo = 'subcategoria' 
                        AND referencia_id = :subcategoria_id
                        AND ativo = 1
                        LIMIT 1
                    '''),
                    {"funcionario_id": funcionario_id, "subcategoria_id": subcategoria_id}
                )
                
                config = result.fetchone()
                if config:
                    return dict(config)
            
            # 3. Tentar buscar por categoria
            if categoria_id:
                result = db.execute(
                    text('''
                        SELECT * FROM comissoes_configuracao
                        WHERE funcionario_id = :funcionario_id 
                        AND tipo = 'categoria' 
                        AND referencia_id = :categoria_id
                        AND ativo = 1
                        LIMIT 1
                    '''),
                    {"funcionario_id": funcionario_id, "categoria_id": categoria_id}
                )
                
                config = result.fetchone()
                if config:
                    return dict(config)
            
            return None
        finally:
            db.close()
    
    @staticmethod
    def criar_ou_atualizar(funcionario_id: int, tipo: str, referencia_id: int, 
                          tipo_calculo: str, percentual: float,
                          percentual_loja: float = None,
                          desconta_taxa_cartao: bool = True,
                          desconta_impostos: bool = True,
                          desconta_taxa_entrega: bool = False,
                          comissao_venda_parcial: bool = True,
                          permite_edicao_venda: bool = False,
                          observacoes: str = None,
                          usuario_id: int = None) -> int:
        """
        Cria ou atualiza uma configuração de comissão
        
        USA SQLALCHEMY ORM - FORMA CORRETA E SIMPLES!
        """
        from .db import SessionLocal
        
        db = SessionLocal()
        try:
            # Buscar se já existe usando ORM
            from sqlalchemy import text
            
            result = db.execute(
                text("SELECT id FROM comissoes_configuracao WHERE funcionario_id = :f AND tipo = :t AND referencia_id = :r"),
                {"f": funcionario_id, "t": tipo, "r": referencia_id}
            ).fetchone()
            
            if result:
                # Atualizar
                db.execute(
                    text("""UPDATE comissoes_configuracao SET
                        tipo_calculo = :tc, percentual = :p, percentual_loja = :pl,
                        desconta_taxa_cartao = :dtc, desconta_impostos = :di,
                        desconta_taxa_entrega = :dte, comissao_venda_parcial = :cvp,
                        permite_edicao_venda = :pev, observacoes = :obs, 
                        data_atualizacao = CURRENT_TIMESTAMP, usuario_atualizacao = :ua
                        WHERE id = :id"""),
                    {"tc": tipo_calculo, "p": percentual, "pl": percentual_loja,
                     "dtc": desconta_taxa_cartao, "di": desconta_impostos,
                     "dte": desconta_taxa_entrega, "cvp": comissao_venda_parcial,
                     "pev": permite_edicao_venda, "obs": observacoes, 
                     "ua": usuario_id, "id": result[0]}
                )
                config_id = result[0]
            else:
                # Criar
                result = db.execute(
                    text("""INSERT INTO comissoes_configuracao (
                        funcionario_id, tipo, referencia_id, tipo_calculo, percentual,
                        percentual_loja, desconta_taxa_cartao, desconta_impostos,
                        desconta_taxa_entrega, comissao_venda_parcial, permite_edicao_venda, 
                        observacoes, usuario_criacao
                    ) VALUES (:f, :t, :r, :tc, :p, :pl, :dtc, :di, :dte, :cvp, :pev, :obs, :uc)"""),
                    {"f": funcionario_id, "t": tipo, "r": referencia_id,
                     "tc": tipo_calculo, "p": percentual, "pl": percentual_loja,
                     "dtc": desconta_taxa_cartao, "di": desconta_impostos,
                     "dte": desconta_taxa_entrega, "cvp": comissao_venda_parcial,
                     "pev": permite_edicao_venda, "obs": observacoes, "uc": usuario_id}
                )
                config_id = result.lastrowid
            
            db.commit()
            return config_id
            
        except Exception as e:
            db.rollback()
            logger.error(f"Erro ao salvar configuração: {e}")
            raise
        finally:
            db.close()
    
    @staticmethod
    def deletar(config_id: int) -> bool:
        """
        Deleta (desativa) uma configuração de comissão
        
        Args:
            config_id: ID da configuração
            
        Returns:
            True se deletou com sucesso
        """
        from .db import SessionLocal
        from sqlalchemy import text
        
        db = SessionLocal()
        try:
            result = execute_tenant_safe(db, """
                UPDATE comissoes_configuracao SET ativo = false
                WHERE id = :config_id
                AND {tenant_filter}
            """, {'config_id': config_id})
            
            success = result.rowcount > 0
            db.commit()
            
            return success
        finally:
            db.close()
    
    @staticmethod
    def duplicar_configuracao(funcionario_origem_id: int, funcionario_destino_id: int,
                            usuario_id: int = None) -> int:
        """
        Duplica todas as configurações de um funcionário para outro
        
        Args:
            funcionario_origem_id: ID do funcionário origem
            funcionario_destino_id: ID do funcionário destino
            usuario_id: ID do usuário que está fazendo a duplicação
            
        Returns:
            Quantidade de configurações duplicadas
        """
        db = SessionLocal()
        try:
            # Buscar todas as configs do funcionário origem
            result = db.execute(
                text('''
                    SELECT * FROM comissoes_configuracao
                    WHERE funcionario_id = :funcionario_origem_id AND ativo = 1
                '''),
                {"funcionario_origem_id": funcionario_origem_id}
            )
            
            configs = result.fetchall()
            count = 0
            
            for config in configs:
                try:
                    db.execute(
                        text('''
                            INSERT INTO comissoes_configuracao (
                                funcionario_id, tipo, referencia_id, tipo_calculo, percentual,
                                percentual_loja, desconta_taxa_cartao, desconta_impostos,
                                desconta_taxa_entrega, permite_edicao_venda, observacoes,
                                usuario_criacao
                            ) VALUES (:funcionario_destino_id, :tipo, :referencia_id, :tipo_calculo, :percentual,
                                     :percentual_loja, :desconta_taxa_cartao, :desconta_impostos,
                                     :desconta_taxa_entrega, :permite_edicao_venda, :observacoes,
                                     :usuario_id)
                        '''),
                        {
                            "funcionario_destino_id": funcionario_destino_id,
                            "tipo": config['tipo'],
                            "referencia_id": config['referencia_id'],
                            "tipo_calculo": config['tipo_calculo'],
                            "percentual": config['percentual'],
                            "percentual_loja": config['percentual_loja'],
                            "desconta_taxa_cartao": config['desconta_taxa_cartao'],
                            "desconta_impostos": config['desconta_impostos'],
                            "desconta_taxa_entrega": config['desconta_taxa_entrega'],
                            "permite_edicao_venda": config['permite_edicao_venda'],
                            "observacoes": f"Duplicado de funcionário {funcionario_origem_id}",
                            "usuario_id": usuario_id
                        }
                    )
                    count += 1
                except IntegrityError:
                    # Já existe configuração para este item, pular
                    continue
            
            db.commit()
            return count
        finally:
            db.close()


class ComissoesItens:
    """Modelo para itens de comissão"""
    
    @staticmethod
    def registrar_comissao(venda_id: int, venda_item_id: int, funcionario_id: int,
                          produto_id: int, categoria_id: int, subcategoria_id: int,
                          data_venda: str, valor_venda: float, valor_custo: float,
                          quantidade: float, desconto_proporcional: float,
                          taxa_cartao_proporcional: float, taxa_entrega_proporcional: float,
                          imposto_proporcional: float, percentual_comissao: float,
                          tipo_calculo: str, valor_base_calculo: float,
                          valor_comissao: float, percentual_pago: float = 100.0) -> int:
        """
        Registra um item de comissão
        
        Returns:
            ID do item criado
        """
        db = SessionLocal()
        try:
            valor_comissao_gerada = valor_comissao * (percentual_pago / 100.0)
            
            result = db.execute(
                text('''
                    INSERT INTO comissoes_itens (
                        venda_id, venda_item_id, funcionario_id, produto_id, categoria_id,
                        subcategoria_id, data_venda, valor_venda, valor_custo, quantidade,
                        desconto_proporcional, taxa_cartao_proporcional, taxa_entrega_proporcional,
                        imposto_proporcional, percentual_comissao, tipo_calculo, valor_base_calculo,
                        valor_comissao, percentual_pago, valor_comissao_gerada, status
                    ) VALUES (:venda_id, :venda_item_id, :funcionario_id, :produto_id, :categoria_id,
                             :subcategoria_id, :data_venda, :valor_venda, :valor_custo, :quantidade,
                             :desconto_proporcional, :taxa_cartao_proporcional, :taxa_entrega_proporcional,
                             :imposto_proporcional, :percentual_comissao, :tipo_calculo, :valor_base_calculo,
                             :valor_comissao, :percentual_pago, :valor_comissao_gerada, 'pendente')
                '''),
                {
                    "venda_id": venda_id, "venda_item_id": venda_item_id, "funcionario_id": funcionario_id,
                    "produto_id": produto_id, "categoria_id": categoria_id, "subcategoria_id": subcategoria_id,
                    "data_venda": data_venda, "valor_venda": valor_venda, "valor_custo": valor_custo,
                    "quantidade": quantidade, "desconto_proporcional": desconto_proporcional,
                    "taxa_cartao_proporcional": taxa_cartao_proporcional,
                    "taxa_entrega_proporcional": taxa_entrega_proporcional,
                    "imposto_proporcional": imposto_proporcional, "percentual_comissao": percentual_comissao,
                    "tipo_calculo": tipo_calculo, "valor_base_calculo": valor_base_calculo,
                    "valor_comissao": valor_comissao, "percentual_pago": percentual_pago,
                    "valor_comissao_gerada": valor_comissao_gerada
                }
            )
            
            item_id = result.lastrowid
            db.commit()
            
            return item_id
        finally:
            db.close()
    
    @staticmethod
    def listar_pendentes(funcionario_id: int = None, data_inicio: str = None,
                        data_fim: str = None) -> List[Dict[str, Any]]:
        """
        Lista itens de comissão pendentes
        
        Args:
            funcionario_id: Filtrar por funcionário (opcional)
            data_inicio: Data início do período (opcional)
            data_fim: Data fim do período (opcional)
            
        Returns:
            Lista de itens pendentes
        """
        db = SessionLocal()
        try:
            query = '''
                SELECT 
                    ci.*,
                    p.nome as produto_nome,
                    v.numero as venda_numero,
                    u.nome as funcionario_nome
                FROM comissoes_itens ci
                LEFT JOIN produtos p ON ci.produto_id = p.id
                LEFT JOIN vendas v ON ci.venda_id = v.id
                LEFT JOIN users u ON ci.funcionario_id = u.id
                WHERE ci.status = 'pendente'
            '''
            
            params = {}
            
            if funcionario_id:
                query += ' AND ci.funcionario_id = :funcionario_id'
                params['funcionario_id'] = funcionario_id
            
            if data_inicio:
                query += ' AND ci.data_venda >= :data_inicio'
                params['data_inicio'] = data_inicio
            
            if data_fim:
                query += ' AND ci.data_venda <= :data_fim'
                params['data_fim'] = data_fim
            
            query += ' ORDER BY ci.data_venda DESC, ci.id DESC'
            
            result = execute_tenant_safe(db, query, params)
            
            itens = []
            for row in result.fetchall():
                itens.append(dict(row))
            
            return itens
        finally:
            db.close()


class ComissoesConfigSistema:
    """Modelo para configurações globais do sistema de comissões"""
    
    @staticmethod
    def get_config() -> Dict[str, Any]:
        """Retorna as configurações globais do sistema"""
        db = SessionLocal()
        try:
            result = execute_tenant_safe(db, 'SELECT * FROM comissoes_configuracoes_sistema LIMIT 1', {}, require_tenant=False)
            config = result.fetchone()
            
            if config:
                return dict(config)
            return {}
        finally:
            db.close()
    
    @staticmethod
    def atualizar_config(gerar_comissao_venda_parcial: bool = None,
                        percentual_imposto_padrao: float = None,
                        dias_vencimento_padrao: int = None,
                        email_assunto_template: str = None,
                        email_corpo_template: str = None,
                        pdf_formato_padrao: str = None) -> bool:
        """Atualiza configurações globais"""
        db = SessionLocal()
        try:
            updates = []
            params = {}
            
            if gerar_comissao_venda_parcial is not None:
                updates.append('gerar_comissao_venda_parcial = :gerar_comissao_venda_parcial')
                params['gerar_comissao_venda_parcial'] = gerar_comissao_venda_parcial
            
            if percentual_imposto_padrao is not None:
                updates.append('percentual_imposto_padrao = :percentual_imposto_padrao')
                params['percentual_imposto_padrao'] = percentual_imposto_padrao
            
            if dias_vencimento_padrao is not None:
                updates.append('dias_vencimento_padrao = :dias_vencimento_padrao')
                params['dias_vencimento_padrao'] = dias_vencimento_padrao
            
            if email_assunto_template:
                updates.append('email_assunto_template = :email_assunto_template')
                params['email_assunto_template'] = email_assunto_template
            
            if email_corpo_template:
                updates.append('email_corpo_template = :email_corpo_template')
                params['email_corpo_template'] = email_corpo_template
            
            if pdf_formato_padrao:
                updates.append('pdf_formato_padrao = :pdf_formato_padrao')
                params['pdf_formato_padrao'] = pdf_formato_padrao
            
            if not updates:
                return False
            
            updates.append('data_atualizacao = CURRENT_TIMESTAMP')
            
            query = f"UPDATE comissoes_configuracoes_sistema SET {', '.join(updates)}"
            result = execute_tenant_safe(db, query, params, require_tenant=False)
            
            success = result.rowcount > 0
            db.commit()
            
            return success
        finally:
            db.close()


# ====================
# MODELS SQLAlchemy
# Schema baseado em RELATORIO_SCHEMA_TABELAS_ORFAS.md - Fase 5.4
# ====================

from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Date, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from app.db import Base


class ComissaoConfiguracao(Base):
    """
    Configuração de percentuais de comissão por funcionário.
    Define regras de cálculo (tipo: categoria, produto, serviço, etc.)
    
    ⚠️ NOTA: Esta tabela NÃO possui tenant_id no schema original
    """
    __tablename__ = "comissoes_configuracao"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    funcionario_id = Column(Integer, ForeignKey('clientes.id'), nullable=False, index=True)
    
    # Tipo de referência polimórfica
    tipo = Column(String(20), nullable=False)  # 'categoria', 'produto', 'servico', etc.
    referencia_id = Column(Integer, nullable=False)  # ID da categoria/produto/serviço
    
    percentual = Column(Numeric, nullable=False)
    ativo = Column(Boolean, nullable=True, default=True)
    
    # Configurações de cálculo
    tipo_calculo = Column(String(50), nullable=True, default='percentual')
    desconta_taxa_cartao = Column(Boolean, nullable=True, default=False)
    desconta_impostos = Column(Boolean, nullable=True, default=False)
    desconta_custo_entrega = Column(Boolean, nullable=True, default=False)
    comissao_venda_parcial = Column(Boolean, nullable=True, default=False)
    percentual_loja = Column(Numeric, nullable=True, default=0)
    permite_edicao_venda = Column(Boolean, nullable=True, default=True)
    observacoes = Column(Text, nullable=True, default='')
    
    created_at = Column(DateTime, nullable=True, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, default=datetime.utcnow, onupdate=datetime.utcnow)


class ComissaoItem(Base):
    """
    Detalhamento de comissões por item de venda.
    Armazena cálculo detalhado com custos, descontos e status de pagamento.
    
    ⚠️ NOTA: tenant_id é NULLABLE no schema original (inconsistência)
    """
    __tablename__ = "comissoes_itens"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Relacionamentos
    venda_id = Column(Integer, ForeignKey('vendas.id'), nullable=False, index=True)
    venda_item_id = Column(Integer, nullable=True)
    funcionario_id = Column(Integer, ForeignKey('clientes.id'), nullable=False, index=True)
    produto_id = Column(Integer, nullable=True)
    categoria_id = Column(Integer, nullable=True)
    subcategoria_id = Column(Integer, nullable=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=True, index=True)  # ⚠️ NULLABLE
    
    # Data e valores base
    data_venda = Column(Date, nullable=False, index=True)
    quantidade = Column(Numeric, nullable=True)
    valor_venda = Column(Numeric, nullable=True)
    valor_custo = Column(Numeric, nullable=True)
    
    # Cálculo da comissão
    tipo_calculo = Column(String(50), nullable=True)
    valor_base_calculo = Column(Numeric, nullable=True)
    percentual_comissao = Column(Numeric, nullable=True)
    valor_comissao = Column(Numeric, nullable=True)
    valor_comissao_gerada = Column(Numeric, nullable=False)
    
    # Valores ajustados
    valor_base_original = Column(Numeric, nullable=True)
    valor_base_comissionada = Column(Numeric, nullable=True)
    percentual_aplicado = Column(Numeric, nullable=True)
    
    # Custos e descontos por item
    taxa_cartao_item = Column(Numeric, nullable=True, default=0)
    impostos_item = Column("impostos_item", Numeric, nullable=True, default=0)
    taxa_entregador_item = Column(Numeric, nullable=True, default=0)
    custo_operacional_item = Column(Numeric, nullable=True, default=0)
    receita_taxa_entrega_item = Column(Numeric, nullable=True, default=0)
    percentual_impostos = Column(Numeric, nullable=True, default=0)
    
    # Pagamento
    percentual_pago = Column(Numeric, nullable=True)
    valor_pago_referencia = Column(Numeric, nullable=True)
    parcela_numero = Column(Integer, nullable=True)
    data_pagamento = Column(Date, nullable=True)
    forma_pagamento = Column(String(50), nullable=True)
    valor_pago = Column(Numeric, nullable=True)
    saldo_restante = Column(Numeric, nullable=True)
    observacao_pagamento = Column(Text, nullable=True)
    
    # Status e controle
    status = Column(String(20), nullable=False, default='pendente', index=True)  # pendente, pago, estornado
    
    # Estorno
    data_estorno = Column(Date, nullable=True)
    motivo_estorno = Column(Text, nullable=True)
    
    # Auditoria
    data_criacao = Column(DateTime, nullable=False, default=datetime.utcnow)
    data_atualizacao = Column(DateTime, nullable=True, onupdate=datetime.utcnow)


class ComissaoVenda(Base):
    """
    Consolidação de comissão por venda completa.
    Gera conta a pagar quando comissão é aprovada.
    
    ⚠️ NOTA: Possui tenant_id NOT NULL (consistente)
    """
    __tablename__ = "comissoes_vendas"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Relacionamentos
    venda_id = Column(Integer, ForeignKey('vendas.id'), nullable=False, index=True)
    funcionario_id = Column(Integer, ForeignKey('clientes.id'), nullable=False, index=True)
    conta_pagar_id = Column(Integer, ForeignKey('contas_pagar.id'), nullable=True)
    user_id = Column(Integer, nullable=False)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Valores
    valor_venda = Column(Numeric, nullable=False)
    valor_comissao = Column(Numeric, nullable=False)
    percentual = Column(Numeric, nullable=False)
    
    # Status
    status = Column(String(20), nullable=True, default='pendente')  # pendente, pago, estornado
    
    # Auditoria
    created_at = Column(DateTime, nullable=True, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, default=datetime.utcnow, onupdate=datetime.utcnow)
