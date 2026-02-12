"""
Parser para arquivos OFX (Open Financial Exchange)
Suporta OFX 1.x (SGML) e 2.x (XML)
"""

import re
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Optional
from xml.etree import ElementTree as ET


class TransacaoOFX:
    """Representa uma transação do extrato OFX"""
    
    def __init__(self):
        self.fitid: Optional[str] = None  # ID único do banco
        self.tipo: Optional[str] = None  # CREDIT ou DEBIT
        self.data_movimento: Optional[datetime] = None
        self.valor: Optional[Decimal] = None
        self.memo: Optional[str] = None  # Descrição
        self.nome_beneficiario: Optional[str] = None
        self.checknum: Optional[str] = None  # Número cheque/doc
        
    def to_dict(self) -> Dict:
        """Converte para dicionário"""
        return {
            'fitid': self.fitid,
            'tipo': self.tipo,
            'data_movimento': self.data_movimento.isoformat() if self.data_movimento else None,
            'valor': float(self.valor) if self.valor else None,
            'memo': self.memo,
            'nome_beneficiario': self.nome_beneficiario,
            'checknum': self.checknum,
        }


class ExtratoOFX:
    """Representa um extrato OFX completo"""
    
    def __init__(self):
        self.conta_numero: Optional[str] = None
        self.conta_tipo: Optional[str] = None
        self.agencia: Optional[str] = None
        self.banco_id: Optional[str] = None
        self.data_inicio: Optional[datetime] = None
        self.data_fim: Optional[datetime] = None
        self.saldo_inicial: Optional[Decimal] = None
        self.saldo_final: Optional[Decimal] = None
        self.moeda: str = 'BRL'
        self.transacoes: List[TransacaoOFX] = []
        
    def to_dict(self) -> Dict:
        """Converte para dicionário"""
        return {
            'conta_numero': self.conta_numero,
            'conta_tipo': self.conta_tipo,
            'agencia': self.agencia,
            'banco_id': self.banco_id,
            'data_inicio': self.data_inicio.isoformat() if self.data_inicio else None,
            'data_fim': self.data_fim.isoformat() if self.data_fim else None,
            'saldo_inicial': float(self.saldo_inicial) if self.saldo_inicial else None,
            'saldo_final': float(self.saldo_final) if self.saldo_final else None,
            'moeda': self.moeda,
            'transacoes': [t.to_dict() for t in self.transacoes],
            'total_transacoes': len(self.transacoes),
        }


class OFXParser:
    """Parser para arquivos OFX"""
    
    @staticmethod
    def detectar_versao(conteudo: str) -> str:
        """Detecta se é OFX 1.x (SGML) ou 2.x (XML)"""
        if '<?xml' in conteudo[:200]:
            return '2.x'
        return '1.x'
    
    @staticmethod
    def _parse_data_ofx(data_str: str) -> Optional[datetime]:
        """
        Converte data OFX para datetime
        Formatos: YYYYMMDD, YYYYMMDDHHMMSS, YYYYMMDDHHMMSS.XXX[-TZ]
        """
        if not data_str:
            return None
            
        # Remove timezone e milissegundos
        data_str = data_str.split('[')[0].split('.')[0]
        
        # Tenta diferentes formatos
        formatos = [
            '%Y%m%d%H%M%S',  # 20240101120000
            '%Y%m%d',        # 20240101
        ]
        
        for formato in formatos:
            try:
                return datetime.strptime(data_str, formato)
            except ValueError:
                continue
        
        return None
    
    @staticmethod
    def _parse_valor(valor_str: str) -> Optional[Decimal]:
        """Converte string de valor para Decimal"""
        if not valor_str:
            return None
        try:
            return Decimal(valor_str.strip())
        except:
            return None
    
    @staticmethod
    def _extrair_tag_sgml(conteudo: str, tag: str) -> Optional[str]:
        """Extrai valor de tag SGML (OFX 1.x)"""
        padrao = f'<{tag}>([^<]+)'
        match = re.search(padrao, conteudo, re.IGNORECASE)
        return match.group(1).strip() if match else None
    
    @staticmethod
    def _parse_sgml(conteudo: str) -> ExtratoOFX:
        """Parse OFX 1.x (SGML)"""
        extrato = ExtratoOFX()
        
        # Dados da conta
        extrato.banco_id = OFXParser._extrair_tag_sgml(conteudo, 'BANKID')
        extrato.agencia = OFXParser._extrair_tag_sgml(conteudo, 'BRANCHID')
        extrato.conta_numero = OFXParser._extrair_tag_sgml(conteudo, 'ACCTID')
        extrato.conta_tipo = OFXParser._extrair_tag_sgml(conteudo, 'ACCTTYPE')
        
        # Período
        data_inicio_str = OFXParser._extrair_tag_sgml(conteudo, 'DTSTART')
        data_fim_str = OFXParser._extrair_tag_sgml(conteudo, 'DTEND')
        extrato.data_inicio = OFXParser._parse_data_ofx(data_inicio_str)
        extrato.data_fim = OFXParser._parse_data_ofx(data_fim_str)
        
        # Saldos
        saldo_inicial_str = OFXParser._extrair_tag_sgml(conteudo, 'BALAMT')
        saldo_final_str = OFXParser._extrair_tag_sgml(conteudo, 'BALAMT')
        extrato.saldo_inicial = OFXParser._parse_valor(saldo_inicial_str)
        extrato.saldo_final = OFXParser._parse_valor(saldo_final_str)
        
        # Moeda
        moeda = OFXParser._extrair_tag_sgml(conteudo, 'CURDEF')
        if moeda:
            extrato.moeda = moeda
        
        # Transações
        # Encontra todos os blocos <STMTTRN>...</STMTTRN>
        padrao_transacoes = r'<STMTTRN>(.*?)</STMTTRN>'
        blocos = re.findall(padrao_transacoes, conteudo, re.DOTALL | re.IGNORECASE)
        
        for bloco in blocos:
            transacao = TransacaoOFX()
            
            transacao.tipo = OFXParser._extrair_tag_sgml(bloco, 'TRNTYPE')
            transacao.fitid = OFXParser._extrair_tag_sgml(bloco, 'FITID')
            transacao.memo = OFXParser._extrair_tag_sgml(bloco, 'MEMO')
            transacao.nome_beneficiario = OFXParser._extrair_tag_sgml(bloco, 'NAME')
            transacao.checknum = OFXParser._extrair_tag_sgml(bloco, 'CHECKNUM')
            
            # Data
            data_str = OFXParser._extrair_tag_sgml(bloco, 'DTPOSTED')
            transacao.data_movimento = OFXParser._parse_data_ofx(data_str)
            
            # Valor
            valor_str = OFXParser._extrair_tag_sgml(bloco, 'TRNAMT')
            transacao.valor = OFXParser._parse_valor(valor_str)
            
            # Adiciona apenas se tiver dados essenciais
            if transacao.fitid and transacao.valor is not None:
                extrato.transacoes.append(transacao)
        
        return extrato
    
    @staticmethod
    def _parse_xml(conteudo: str) -> ExtratoOFX:
        """Parse OFX 2.x (XML)"""
        extrato = ExtratoOFX()
        
        try:
            root = ET.fromstring(conteudo)
            
            # Namespace OFX 2.x
            ns = {'ofx': 'http://www.ofx.net/ofx/OFX200'}
            
            # Tenta com e sem namespace
            for prefix in ['ofx:', '']:
                # Dados da conta
                banco = root.find(f'.//{prefix}BANKID')
                if banco is not None:
                    extrato.banco_id = banco.text
                
                agencia = root.find(f'.//{prefix}BRANCHID')
                if agencia is not None:
                    extrato.agencia = agencia.text
                
                conta = root.find(f'.//{prefix}ACCTID')
                if conta is not None:
                    extrato.conta_numero = conta.text
                
                tipo = root.find(f'.//{prefix}ACCTTYPE')
                if tipo is not None:
                    extrato.conta_tipo = tipo.text
                
                # Período
                dtstart = root.find(f'.//{prefix}DTSTART')
                if dtstart is not None:
                    extrato.data_inicio = OFXParser._parse_data_ofx(dtstart.text)
                
                dtend = root.find(f'.//{prefix}DTEND')
                if dtend is not None:
                    extrato.data_fim = OFXParser._parse_data_ofx(dtend.text)
                
                # Saldo
                balamt = root.find(f'.//{prefix}BALAMT')
                if balamt is not None:
                    extrato.saldo_final = OFXParser._parse_valor(balamt.text)
                
                # Moeda
                curdef = root.find(f'.//{prefix}CURDEF')
                if curdef is not None:
                    extrato.moeda = curdef.text
                
                # Transações
                for stmttrn in root.findall(f'.//{prefix}STMTTRN'):
                    transacao = TransacaoOFX()
                    
                    trntype = stmttrn.find(f'{prefix}TRNTYPE')
                    if trntype is not None:
                        transacao.tipo = trntype.text
                    
                    fitid = stmttrn.find(f'{prefix}FITID')
                    if fitid is not None:
                        transacao.fitid = fitid.text
                    
                    dtposted = stmttrn.find(f'{prefix}DTPOSTED')
                    if dtposted is not None:
                        transacao.data_movimento = OFXParser._parse_data_ofx(dtposted.text)
                    
                    trnamt = stmttrn.find(f'{prefix}TRNAMT')
                    if trnamt is not None:
                        transacao.valor = OFXParser._parse_valor(trnamt.text)
                    
                    memo = stmttrn.find(f'{prefix}MEMO')
                    if memo is not None:
                        transacao.memo = memo.text
                    
                    name = stmttrn.find(f'{prefix}NAME')
                    if name is not None:
                        transacao.nome_beneficiario = name.text
                    
                    checknum = stmttrn.find(f'{prefix}CHECKNUM')
                    if checknum is not None:
                        transacao.checknum = checknum.text
                    
                    if transacao.fitid and transacao.valor is not None:
                        extrato.transacoes.append(transacao)
                
                # Se encontrou transações, sai do loop
                if extrato.transacoes:
                    break
        
        except ET.ParseError as e:
            raise ValueError(f"Erro ao parsear XML OFX: {e}")
        
        return extrato
    
    @staticmethod
    def parse(conteudo: str) -> ExtratoOFX:
        """
        Parse arquivo OFX (detecta automaticamente versão)
        
        Args:
            conteudo: String com conteúdo do arquivo OFX
            
        Returns:
            ExtratoOFX com dados parseados
            
        Raises:
            ValueError: Se formato inválido
        """
        if not conteudo or len(conteudo) < 100:
            raise ValueError("Arquivo OFX vazio ou inválido")
        
        # Remove BOM e espaços
        conteudo = conteudo.strip()
        if conteudo.startswith('\ufeff'):
            conteudo = conteudo[1:]
        
        versao = OFXParser.detectar_versao(conteudo)
        
        if versao == '2.x':
            return OFXParser._parse_xml(conteudo)
        else:
            return OFXParser._parse_sgml(conteudo)
    
    @staticmethod
    def parse_arquivo(caminho_arquivo: str) -> ExtratoOFX:
        """
        Parse arquivo OFX do disco
        
        Args:
            caminho_arquivo: Caminho do arquivo .ofx
            
        Returns:
            ExtratoOFX com dados parseados
        """
        encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
        
        for encoding in encodings:
            try:
                with open(caminho_arquivo, 'r', encoding=encoding) as f:
                    conteudo = f.read()
                return OFXParser.parse(conteudo)
            except (UnicodeDecodeError, LookupError):
                continue
        
        raise ValueError(f"Não foi possível decodificar o arquivo com encodings: {encodings}")


def validar_extrato(extrato: ExtratoOFX) -> Dict[str, any]:
    """
    Valida extrato OFX parseado
    
    Returns:
        Dict com {'valido': bool, 'erros': [], 'avisos': []}
    """
    resultado = {
        'valido': True,
        'erros': [],
        'avisos': []
    }
    
    # Validações críticas
    if not extrato.transacoes:
        resultado['erros'].append("Nenhuma transação encontrada")
        resultado['valido'] = False
    
    if not extrato.conta_numero:
        resultado['avisos'].append("Número da conta não identificado")
    
    # Verifica duplicatas de FITID
    fitids = [t.fitid for t in extrato.transacoes if t.fitid]
    duplicatas = set([f for f in fitids if fitids.count(f) > 1])
    if duplicatas:
        resultado['avisos'].append(f"FITIDs duplicados: {len(duplicatas)}")
    
    # Verifica transações sem data
    sem_data = [t for t in extrato.transacoes if not t.data_movimento]
    if sem_data:
        resultado['avisos'].append(f"{len(sem_data)} transações sem data")
    
    # Verifica transações sem memo/descrição
    sem_descricao = [t for t in extrato.transacoes if not t.memo and not t.nome_beneficiario]
    if sem_descricao:
        resultado['avisos'].append(f"{len(sem_descricao)} transações sem descrição")
    
    return resultado
