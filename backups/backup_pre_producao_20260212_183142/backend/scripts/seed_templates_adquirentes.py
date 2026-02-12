"""
Script para popular templates de adquirentes padrão
Stone, Cielo, Rede, PagSeguro, etc
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import uuid
import json
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.db import SessionLocal
from app.financeiro_models import TemplateAdquirente


def criar_templates_padrão():
    """Cria templates padrão para os principais adquirentes brasileiros"""
    
    db = SessionLocal()
    
    templates = [
        {
            'nome_adquirente': 'Stone',
            'tipo_relatorio': 'extrato_ofx',
            'palavras_chave': ['stone', 'stone pagamentos', 'recebimento vendas'],
            'mapeamento': {
                'fitid': 'FITID',
                'data': 'DTPOSTED',
                'valor': 'TRNAMT',
                'tipo': 'TRNTYPE',
                'descricao': 'MEMO',
                'formato_data': '%Y%m%d%H%M%S'
            },
            'colunas_obrigatorias': ['FITID', 'DTPOSTED', 'TRNAMT'],
            'auto_aplicar': True,
        },
        {
            'nome_adquirente': 'Stone',
            'tipo_relatorio': 'recebimentos_csv',
            'palavras_chave': ['stone', 'recebimentos', 'stone id', 'nsu'],
            'mapeamento': {
                'stone_id': 'Stone ID',
                'nsu': 'NSU',
                'data_venda': 'Data da Venda',
                'data_pagamento': 'Data de Pagamento',
                'valor_bruto': 'Valor Bruto',
                'valor_liquido': 'Valor Líquido',
                'taxa_mdr': 'Desconto MDR',
                'taxa_transacao': 'Taxa de Transação',
                'taxa_antecipacao': 'Taxa de Antecipação',
                'bandeira': 'Bandeira',
                'parcelas': 'Parcelas',
                'status': 'Status',
                'formato_data': '%d/%m/%Y'
            },
            'colunas_obrigatorias': ['Stone ID', 'Valor Líquido'],
            'auto_aplicar': False,
        },
        {
            'nome_adquirente': 'Cielo',
            'tipo_relatorio': 'extrato_csv',
            'palavras_chave': ['cielo', 'numero logico', 'numero do resumo'],
            'mapeamento': {
                'numero_logico': 'Numero Logico',
                'numero_resumo': 'Numero do Resumo',
                'data_venda': 'Data da Venda',
                'data_pagamento': 'Data de Pagamento',
                'valor_bruto': 'Valor Bruto',
                'valor_liquido': 'Valor Liquido',
                'taxa_desconto': 'Taxa de Desconto',
                'bandeira': 'Bandeira',
                'parcelas': 'Parcelas',
                'formato_data': '%d/%m/%Y'
            },
            'colunas_obrigatorias': ['Numero Logico', 'Valor Liquido'],
            'auto_aplicar': False,
        },
        {
            'nome_adquirente': 'Rede',
            'tipo_relatorio': 'vendas_csv',
            'palavras_chave': ['rede', 'nsu', 'codigo de autorizacao'],
            'mapeamento': {
                'nsu': 'NSU',
                'autorizacao': 'Codigo de Autorizacao',
                'data_venda': 'Data da Venda',
                'data_pagamento': 'Data de Pagamento',
                'valor_bruto': 'Valor Bruto',
                'valor_liquido': 'Valor Liquido',
                'taxa': 'Taxa',
                'bandeira': 'Bandeira',
                'parcelas': 'Parcelas',
                'formato_data': '%d/%m/%Y'
            },
            'colunas_obrigatorias': ['NSU', 'Valor Liquido'],
            'auto_aplicar': False,
        },
        {
            'nome_adquirente': 'PagSeguro',
            'tipo_relatorio': 'transacoes_csv',
            'palavras_chave': ['pagseguro', 'codigo da transacao'],
            'mapeamento': {
                'codigo_transacao': 'Código da Transação',
                'data': 'Data',
                'tipo': 'Tipo',
                'status': 'Status',
                'valor_bruto': 'Valor Bruto',
                'taxa': 'Taxa',
                'valor_liquido': 'Valor Líquido',
                'formato_data': '%d/%m/%Y %H:%M:%S'
            },
            'colunas_obrigatorias': ['Código da Transação', 'Valor Líquido'],
            'auto_aplicar': False,
        },
        {
            'nome_adquirente': 'Mercado Pago',
            'tipo_relatorio': 'extrato_csv',
            'palavras_chave': ['mercado pago', 'id da transacao'],
            'mapeamento': {
                'id_transacao': 'ID da transação',
                'data_criacao': 'Data de criação',
                'data_liberacao': 'Data de liberação',
                'tipo': 'Tipo',
                'status': 'Status',
                'valor_bruto': 'Valor bruto',
                'taxa': 'Taxa',
                'valor_liquido': 'Valor líquido',
                'formato_data': '%d/%m/%Y %H:%M:%S'
            },
            'colunas_obrigatorias': ['ID da transação', 'Valor líquido'],
            'auto_aplicar': False,
        },
        {
            'nome_adquirente': 'Banco do Brasil',
            'tipo_relatorio': 'extrato_ofx',
            'palavras_chave': ['banco do brasil', 'bb', '001'],
            'mapeamento': {
                'fitid': 'FITID',
                'data': 'DTPOSTED',
                'valor': 'TRNAMT',
                'tipo': 'TRNTYPE',
                'descricao': 'MEMO',
                'formato_data': '%Y%m%d'
            },
            'colunas_obrigatorias': ['FITID', 'TRNAMT'],
            'auto_aplicar': True,
        },
        {
            'nome_adquirente': 'Santander',
            'tipo_relatorio': 'extrato_ofx',
            'palavras_chave': ['santander', '033'],
            'mapeamento': {
                'fitid': 'FITID',
                'data': 'DTPOSTED',
                'valor': 'TRNAMT',
                'tipo': 'TRNTYPE',
                'descricao': 'MEMO',
                'formato_data': '%Y%m%d%H%M%S'
            },
            'colunas_obrigatorias': ['FITID', 'TRNAMT'],
            'auto_aplicar': True,
        },
        {
            'nome_adquirente': 'Itaú',
            'tipo_relatorio': 'extrato_ofx',
            'palavras_chave': ['itau', 'itaú', '341'],
            'mapeamento': {
                'fitid': 'FITID',
                'data': 'DTPOSTED',
                'valor': 'TRNAMT',
                'tipo': 'TRNTYPE',
                'descricao': 'MEMO',
                'formato_data': '%Y%m%d%H%M%S'
            },
            'colunas_obrigatorias': ['FITID', 'TRNAMT'],
            'auto_aplicar': True,
        },
        {
            'nome_adquirente': 'Bradesco',
            'tipo_relatorio': 'extrato_ofx',
            'palavras_chave': ['bradesco', '237'],
            'mapeamento': {
                'fitid': 'FITID',
                'data': 'DTPOSTED',
                'valor': 'TRNAMT',
                'tipo': 'TRNTYPE',
                'descricao': 'MEMO',
                'formato_data': '%Y%m%d%H%M%S'
            },
            'colunas_obrigatorias': ['FITID', 'TRNAMT'],
            'auto_aplicar': True,
        },
    ]
    
    try:
        for template_data in templates:
            # Verifica se já existe
            existe = db.query(TemplateAdquirente).filter(
                and_(
                    TemplateAdquirente.nome_adquirente == template_data['nome_adquirente'],
                    TemplateAdquirente.tipo_relatorio == template_data['tipo_relatorio']
                )
            ).first()
            
            if existe:
                print(f"✓ Template '{template_data['nome_adquirente']} - {template_data['tipo_relatorio']}' já existe")
                continue
            
            # Cria novo template (global, sem tenant_id)
            template = TemplateAdquirente(
                id=str(uuid.uuid4()),
                tenant_id=str(uuid.uuid4()),  # Dummy tenant para templates globais
                nome_adquirente=template_data['nome_adquirente'],
                tipo_relatorio=template_data['tipo_relatorio'],
                palavras_chave=json.dumps(template_data['palavras_chave']),
                mapeamento=json.dumps(template_data['mapeamento']),
                colunas_obrigatorias=json.dumps(template_data['colunas_obrigatorias']),
                auto_aplicar=template_data['auto_aplicar'],
                vezes_usado=0,
                criado_em=datetime.utcnow(),
                atualizado_em=datetime.utcnow()
            )
            
            db.add(template)
            print(f"✓ Template '{template_data['nome_adquirente']} - {template_data['tipo_relatorio']}' criado")
        
        db.commit()
        print(f"\n✅ {len(templates)} templates criados/verificados com sucesso!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Erro ao criar templates: {e}")
        raise
    finally:
        db.close()


if __name__ == '__main__':
    print("🏦 Criando templates de adquirentes padrão...\n")
    criar_templates_padrão()
