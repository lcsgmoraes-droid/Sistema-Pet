"""
Helpers para detecção automática de operadora de cartão

Analisa estrutura de arquivos CSV/OFX para identificar operadora
"""
from typing import Optional, Dict, Any
import re


def detectar_operadora_csv(conteudo: str, nome_arquivo: str = "") -> Optional[Dict[str, Any]]:
    """
    Detecta operadora baseado no conteúdo do CSV e nome do arquivo.
    
    Retorna:
    {
        'operadora': 'Stone' | 'PagSeguro' | 'Rede' | 'Cielo' | etc,
        'tipo_arquivo': 'relatorio_recebimentos' | 'comprovante_pagamentos' | 'vendas',
        'confianca': float  # 0.0 a 1.0
    }
    """
    nome_arquivo_lower = nome_arquivo.lower()
    linhas = conteudo.strip().split('\n')
    
    if not linhas:
        return None
    
    primeira_linha = linhas[0]
    
    # ====================
    # STONE
    # ====================
    
    # Stone: Relatório de Recebimentos (18 colunas)
    if ';' in primeira_linha:
        colunas = [c.strip().upper() for c in primeira_linha.split(';')]
        
        # Verificar colunas características da Stone
        colunas_stone_recebimentos = [
            'DATA DE CRIAÇÃO',
            'DATA DE PAGAMENTO',
            'TIPO DE TRANSAÇÃO',
            'VALOR DA TRANSAÇÃO',
            'DESCONTO MDR',
            'VALOR LÍQUIDO',
            'NOME PORTADOR',
            'NSU',
            'TID'
        ]
        
        colunas_presentes = sum(1 for col in colunas_stone_recebimentos if col in colunas)
        
        if colunas_presentes >= 7:  # Pelo menos 7 de 9 colunas
            return {
                'operadora': 'Stone',
                'tipo_arquivo': 'relatorio_recebimentos',
                'confianca': min(1.0, colunas_presentes / 9)
            }
    
    # Stone: Comprovante de Pagamentos (19 colunas)
    if ';' in primeira_linha:
        colunas = [c.strip().upper() for c in primeira_linha.split(';')]
        
        colunas_stone_comprovante = [
            'VALOR',
            'STATUS',
            'TID',
            'DATA DO PAGAMENTO',
            'ID RASTREÁVEL'
        ]
        
        if all(col in colunas for col in colunas_stone_comprovante):
            return {
                'operadora': 'Stone',
                'tipo_arquivo': 'comprovante_pagamentos',
                'confianca': 1.0
            }
    
    # ====================
    # PAGSEGURO
    # ====================
    
    if 'pagseguro' in nome_arquivo_lower or 'pag seguro' in nome_arquivo_lower:
        return {
            'operadora': 'PagSeguro',
            'tipo_arquivo': 'relatorio_transacoes',
            'confianca': 0.9
        }
    
    # PagSeguro: Colunas características
    if ';' in primeira_linha or ',' in primeira_linha:
        separador = ';' if ';' in primeira_linha else ','
        colunas = [c.strip().upper() for c in primeira_linha.split(separador)]
        
        colunas_pagseguro = [
            'CÓDIGO DA TRANSAÇÃO',
            'STATUS',
            'MEIO DE PAGAMENTO',
            'VALOR BRUTO',
            'VALOR LÍQUIDO'
        ]
        
        if sum(1 for col in colunas_pagseguro if col in colunas) >= 3:
            return {
                'operadora': 'PagSeguro',
                'tipo_arquivo': 'relatorio_transacoes',
                'confianca': 0.8
            }
    
    # ====================
    # REDE
    # ====================
    
    if 'rede' in nome_arquivo_lower:
        return {
            'operadora': 'Rede',
            'tipo_arquivo': 'relatorio_vendas',
            'confianca': 0.9
        }
    
    # Rede: Colunas características
    if ',' in primeira_linha:
        colunas = [c.strip().upper() for c in primeira_linha.split(',')]
        
        colunas_rede = [
            'NSU',
            'CV',
            'VALOR BRUTO',
            'VALOR LÍQUIDO',
            'DATA VENDA',
            'DATA PAGAMENTO'
        ]
        
        if sum(1 for col in colunas_rede if any(cr in col for cr in ['NSU', 'CV', 'VALOR BRUTO'])) >= 2:
            return {
                'operadora': 'Rede',
                'tipo_arquivo': 'relatorio_vendas',
                'confianca': 0.8
            }
    
    # ====================
    # CIELO
    # ====================
    
    if 'cielo' in nome_arquivo_lower:
        return {
            'operadora': 'Cielo',
            'tipo_arquivo': 'extrato_vendas',
            'confianca': 0.9
        }
    
    # Cielo: Colunas características
    if ',' in primeira_linha or ';' in primeira_linha:
        separador = ';' if ';' in primeira_linha else ','
        colunas = [c.strip().upper() for c in primeira_linha.split(separador)]
        
        colunas_cielo = [
            'NÚMERO DO ESTABELECIMENTO',
            'NÚMERO DO CARTÃO',
            'DATA DA VENDA',
            'VALOR DA VENDA',
            'TAXA ADMINISTRATIVA'
        ]
        
        if sum(1 for col in colunas_cielo if col in colunas) >= 3:
            return {
                'operadora': 'Cielo',
                'tipo_arquivo': 'extrato_vendas',
                'confianca': 0.8
            }
    
    # ====================
    # GETNET
    # ====================
    
    if 'getnet' in nome_arquivo_lower or 'santander' in nome_arquivo_lower:
        return {
            'operadora': 'Getnet',
            'tipo_arquivo': 'relatorio_vendas',
            'confianca': 0.9
        }
    
    # ====================
    # FALLBACK: Tentar pelo nome do arquivo
    # ====================
    
    # Padrões comuns em nomes de arquivo
    padroes_operadora = {
        r'stone': 'Stone',
        r'pag\s?seguro': 'PagSeguro',
        r'p\.seguro': 'PagSeguro',
        r'rede': 'Rede',
        r'cielo': 'Cielo',
        r'getnet': 'Getnet',
        r'bin': 'Bin',
        r'mercado\s?pago': 'Mercado Pago',
        r'safrapay': 'SafraPay'
    }
    
    for padrao, operadora_nome in padroes_operadora.items():
        if re.search(padrao, nome_arquivo_lower):
            return {
                'operadora': operadora_nome,
                'tipo_arquivo': 'desconhecido',
                'confianca': 0.7
            }
    
    # Não foi possível detectar
    return None


def detectar_operadora_ofx(conteudo: str) -> Optional[Dict[str, Any]]:
    """
    Detecta operadora/banco baseado no conteúdo do arquivo OFX.
    
    OFX geralmente contém tags como:
    - <FI><ORG>Stone Pagamentos</ORG></FI>
    - <BANKID>16501555</BANKID>
    """
    conteudo_upper = conteudo.upper()
    
    # Stone
    if 'STONE' in conteudo_upper or '<ORG>STONE' in conteudo_upper:
        return {
            'operadora': 'Stone',
            'tipo_arquivo': 'extrato_ofx',
            'confianca': 1.0
        }
    
    # PagBank (antigo PagSeguro)
    if 'PAGBANK' in conteudo_upper or 'PAGSEGURO' in conteudo_upper:
        return {
            'operadora': 'PagBank',
            'tipo_arquivo': 'extrato_ofx',
            'confianca': 1.0
        }
    
    # Bancos comuns
    bancos_ofx = {
        'BANCO DO BRASIL': 'Banco do Brasil',
        'BRADESCO': 'Bradesco',
        'ITAU': 'Itaú',
        'SANTANDER': 'Santander',
        'CAIXA ECONOMICA': 'Caixa Econômica',
        'NUBANK': 'Nubank',
        'INTER': 'Banco Inter'
    }
    
    for padrao, banco_nome in bancos_ofx.items():
        if padrao in conteudo_upper:
            return {
                'operadora': banco_nome,
                'tipo_arquivo': 'extrato_ofx',
                'confianca': 0.95
            }
    
    # OFX genérico (não conseguiu identificar banco)
    if '<OFX>' in conteudo_upper or '<STMTTRN>' in conteudo_upper:
        return {
            'operadora': 'Banco Desconhecido',
            'tipo_arquivo': 'extrato_ofx',
            'confianca': 0.5
        }
    
    return None


def detectar_operadora_automatico(conteudo: str, nome_arquivo: str = "", tipo_arquivo: str = "") -> Optional[Dict[str, Any]]:
    """
    Detecta operadora automaticamente baseado no tipo e conteúdo.
    
    Args:
        conteudo: Conteúdo do arquivo (texto)
        nome_arquivo: Nome do arquivo (usado como hint)
        tipo_arquivo: Extensão ou tipo conhecido (.csv, .ofx, etc)
    
    Returns:
        Dict com operadora, tipo_arquivo e confiança, ou None se não detectar
    """
    tipo_lower = tipo_arquivo.lower()
    
    # OFX
    if 'ofx' in tipo_lower or '<OFX>' in conteudo.upper():
        return detectar_operadora_ofx(conteudo)
    
    # CSV / TXT
    if 'csv' in tipo_lower or 'txt' in tipo_lower or ';' in conteudo or ',' in conteudo:
        return detectar_operadora_csv(conteudo, nome_arquivo)
    
    # Última tentativa: pelo nome do arquivo
    return detectar_operadora_csv("", nome_arquivo)


# ====================
# FUNÇÕES DE TESTE
# ====================

def testar_detectores():
    """Testa detecção de operadoras com exemplos"""
    
    # Teste Stone Relatório
    csv_stone_relatorio = """Data de criação;Data de pagamento;Tipo de transação;Valor da transação;Desconto MDR;Taxa antecipação;Valor líquido;Status do pagamento;Nome portador;NSU;TID;Número da parcela;Total de parcelas;Código de autorização;Canal de venda;Bandeira;Número do terminal;Taxa de processamento;Taxa garantia E-commerce
01/02/2024;15/02/2024;Cartão de crédito;100,00;3,79;0,00;96,21;Pago;JOAO SILVA;12345678;TID123;1;1;ABC123;Presencial;VISA;12345678;0,00;0,00"""
    
    resultado = detectar_operadora_csv(csv_stone_relatorio, "Stone_Relatorio_02_2024.csv")
    print("Teste Stone Relatório:", resultado)
    
    # Teste Stone Comprovante
    csv_stone_comprovante = """Valor;Tarifa Plano;Taxa Antecipação;Tarifa Antecipação;Valor Líquido;Status;TID;NSU;Código de Autorização;Data da Venda;Data do Pagamento;Bandeira;Tipo de Cartão;Número de Parcelas;Meio de Captura;ID Rastreável;Motivo de Contíngen;Tarifa de Transação;Descrição da Regra
1820,00;0,00;0,00;0,00;1820,00;paid;TID123;NSU456;AUTH789;10/02/2024;10/02/2024;Visa;Débito;1;POS;ABC123;;0,00;Taxa Zero"""
    
    resultado = detectar_operadora_csv(csv_stone_comprovante, "Comprovante_Pagamento.csv")
    print("Teste Stone Comprovante:", resultado)
    
    # Teste OFX Stone
    ofx_stone = """<OFX>
<SIGNONMSGSRSV1>
<SONRS>
<DTSERVER>20240210120000</DTSERVER>
<FI>
<ORG>Stone Pagamentos</ORG>
<FID>16501555</FID>
</FI>
</SONRS>
</SIGNONMSGSRSV1>
<STMTTRNRS>
<STMTTRN>
<TRNTYPE>CREDIT</TRNTYPE>
<DTPOSTED>20240210</DTPOSTED>
<TRNAMT>1820.00</TRNAMT>
<FITID>12345</FITID>
</STMTTRN>
</STMTTRNRS>
</OFX>"""
    
    resultado = detectar_operadora_ofx(ofx_stone)
    print("Teste OFX Stone:", resultado)


if __name__ == "__main__":
    testar_detectores()
