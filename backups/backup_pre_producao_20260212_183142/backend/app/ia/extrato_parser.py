# -*- coding: utf-8 -*-
"""
Parsers de Extrato Bancário - ABA 7
Suporta: Excel (XLS/XLSX), CSV, PDF (OCR), OFX
Referência: ROADMAP_IA_AMBICOES.md (linhas 1-250)
"""

import pandas as pd
import openpyxl
import csv
import hashlib
import re
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import chardet
from io import BytesIO, StringIO


class ExtratoParser:
    """
    Parser universal de extratos bancários.
    Detecta automaticamente o formato e banco.
    """
    
    BANCOS_CONHECIDOS = {
        'itau': ['itaú', 'itau', 'banco itau'],
        'bradesco': ['bradesco'],
        'nubank': ['nubank', 'nu pagamentos'],
        'santander': ['santander'],
        'bb': ['banco do brasil', 'bb'],
        'caixa': ['caixa', 'caixa economica'],
        'sicoob': ['sicoob'],
        'sicredi': ['sicredi'],
        'inter': ['inter', 'banco inter'],
        'c6': ['c6 bank', 'c6'],
        'original': ['banco original'],
        'safra': ['safra'],
        'banrisul': ['banrisul']
    }
    
    def __init__(self):
        self.formato_detectado = None
        self.banco_detectado = None
        self.encoding_detectado = None
    
    def detectar_formato(self, arquivo: bytes, nome_arquivo: str) -> str:
        """
        Detecta o formato do arquivo automaticamente.
        Retorna: 'excel', 'csv', 'pdf', 'ofx'
        """
        extensao = Path(nome_arquivo).suffix.lower()
        
        # Verificar por extensão primeiro
        if extensao in ['.xls', '.xlsx']:
            return 'excel'
        elif extensao == '.csv':
            return 'csv'
        elif extensao == '.pdf':
            return 'pdf'
        elif extensao == '.ofx':
            return 'ofx'
        
        # Verificar por magic bytes
        magic_bytes = arquivo[:8]
        
        # Excel (Office Open XML)
        if magic_bytes[:2] == b'PK':
            return 'excel'
        
        # Excel antigo (OLE)
        if magic_bytes[:8] == b'\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1':
            return 'excel'
        
        # PDF
        if magic_bytes[:4] == b'%PDF':
            return 'pdf'
        
        # OFX
        if b'OFX' in arquivo[:100] or b'OFXHEADER' in arquivo[:100]:
            return 'ofx'
        
        # Assume CSV se não detectou nada
        return 'csv'
    
    def detectar_banco(self, conteudo: str) -> Optional[str]:
        """
        Detecta o banco pelo conteúdo do extrato.
        """
        conteudo_lower = conteudo.lower()
        
        for banco, keywords in self.BANCOS_CONHECIDOS.items():
            for keyword in keywords:
                if keyword in conteudo_lower:
                    return banco
        
        return None
    
    def detectar_encoding(self, arquivo: bytes) -> str:
        """
        Detecta o encoding do arquivo.
        """
        resultado = chardet.detect(arquivo)
        return resultado.get('encoding', 'utf-8')
    
    def parse(self, arquivo: bytes, nome_arquivo: str) -> Tuple[List[Dict], Dict]:
        """
        Parse universal - detecta formato e processa.
        
        Retorna:
            (transacoes, metadados)
            
        transacoes = [
            {
                'data': datetime,
                'descricao': str,
                'valor': float,
                'tipo': 'entrada' ou 'saida'
            }
        ]
        
        metadados = {
            'formato': str,
            'banco': str,
            'total_transacoes': int,
            'encoding': str
        }
        """
        # Detectar formato
        formato = self.detectar_formato(arquivo, nome_arquivo)
        self.formato_detectado = formato
        
        # Chamar parser específico
        if formato == 'excel':
            transacoes = self._parse_excel(arquivo)
        elif formato == 'csv':
            transacoes = self._parse_csv(arquivo)
        elif formato == 'pdf':
            transacoes = self._parse_pdf(arquivo)
        elif formato == 'ofx':
            transacoes = self._parse_ofx(arquivo)
        else:
            raise ValueError(f"Formato não suportado: {formato}")
        
        # Metadados
        metadados = {
            'formato': formato,
            'banco': self.banco_detectado,
            'total_transacoes': len(transacoes),
            'encoding': self.encoding_detectado
        }
        
        return transacoes, metadados
    
    def _parse_excel(self, arquivo: bytes) -> List[Dict]:
        """
        Parser de Excel (XLS/XLSX).
        """
        try:
            # Ler Excel
            df = pd.read_excel(BytesIO(arquivo), sheet_name=0)
            
            # Detectar banco pelo conteúdo
            conteudo_preview = df.to_string()[:1000]
            self.banco_detectado = self.detectar_banco(conteudo_preview)
            
            # Normalizar colunas (remover espaços, lowercase)
            df.columns = [str(col).strip().lower() for col in df.columns]
            
            # Detectar colunas automaticamente
            col_data = self._detectar_coluna_data(df.columns)
            col_descricao = self._detectar_coluna_descricao(df.columns)
            col_valor = self._detectar_coluna_valor(df.columns)
            
            if not col_data or not col_descricao or not col_valor:
                raise ValueError("Não foi possível detectar colunas de data, descrição ou valor")
            
            # Processar linhas
            transacoes = []
            for idx, row in df.iterrows():
                try:
                    data = self._parse_data(row[col_data])
                    descricao = str(row[col_descricao]).strip()
                    valor = self._parse_valor(row[col_valor])
                    
                    if not data or not descricao or valor == 0:
                        continue
                    
                    transacoes.append({
                        'data': data,
                        'descricao': descricao,
                        'valor': abs(valor),
                        'tipo': 'entrada' if valor > 0 else 'saida'
                    })
                except:
                    continue
            
            return transacoes
            
        except Exception as e:
            raise ValueError(f"Erro ao processar Excel: {str(e)}")
    
    def _parse_csv(self, arquivo: bytes) -> List[Dict]:
        """
        Parser de CSV com detecção automática de encoding e delimitador.
        """
        try:
            # Detectar encoding
            self.encoding_detectado = self.detectar_encoding(arquivo)
            
            # Decodificar
            conteudo = arquivo.decode(self.encoding_detectado)
            
            # Detectar delimitador
            sniffer = csv.Sniffer()
            delimitador = sniffer.sniff(conteudo[:1024]).delimiter
            
            # Ler CSV
            df = pd.read_csv(StringIO(conteudo), delimiter=delimitador)
            
            # Detectar banco
            self.banco_detectado = self.detectar_banco(conteudo[:1000])
            
            # Normalizar colunas
            df.columns = [str(col).strip().lower() for col in df.columns]
            
            # Detectar colunas
            col_data = self._detectar_coluna_data(df.columns)
            col_descricao = self._detectar_coluna_descricao(df.columns)
            col_valor = self._detectar_coluna_valor(df.columns)
            
            if not col_data or not col_descricao or not col_valor:
                raise ValueError("Não foi possível detectar colunas necessárias")
            
            # Processar
            transacoes = []
            for idx, row in df.iterrows():
                try:
                    data = self._parse_data(row[col_data])
                    descricao = str(row[col_descricao]).strip()
                    valor = self._parse_valor(row[col_valor])
                    
                    if not data or not descricao or valor == 0:
                        continue
                    
                    transacoes.append({
                        'data': data,
                        'descricao': descricao,
                        'valor': abs(valor),
                        'tipo': 'entrada' if valor > 0 else 'saida'
                    })
                except:
                    continue
            
            return transacoes
            
        except Exception as e:
            raise ValueError(f"Erro ao processar CSV: {str(e)}")
    
    def _parse_pdf(self, arquivo: bytes) -> List[Dict]:
        """
        Parser de PDF com OCR (pytesseract).
        Extrai texto de PDF bancário usando Poppler + Tesseract.
        """
        try:
            # Importar bibliotecas
            try:
                from pdf2image import convert_from_bytes
                import pytesseract
            except ImportError:
                raise ValueError("PDF parsing requer: pip install pdf2image pytesseract Pillow")
            
            # Configurar caminho do Tesseract
            import os
            tesseract_paths = [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"
            ]
            for path in tesseract_paths:
                if os.path.exists(path):
                    pytesseract.pytesseract.tesseract_cmd = path
                    break
            
            # Configurar TESSDATA_PREFIX - procurar em vários locais
            # Priorizar venv local (tem português) antes das pastas do sistema
            possible_tessdata = [
                # Prioridade 1: venv local (tem por.traineddata)
                os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".venv", "tessdata"),
                # Prioridade 2: Pastas do sistema
                r"C:\Program Files\Tesseract-OCR\tessdata",
                r"C:\Tesseract-OCR\tessdata",
                r"C:\Program Files (x86)\Tesseract-OCR\tessdata",
            ]
            
            for tessdata_dir in possible_tessdata:
                if os.path.exists(tessdata_dir):
                    os.environ['TESSDATA_PREFIX'] = tessdata_dir
                    break
            
            # Configurar caminho do Poppler
            poppler_path = r"C:\poppler\poppler-24.08.0\Library\bin"
            if not os.path.exists(poppler_path):
                # Tentar outros caminhos comuns
                poppler_path = r"C:\Program Files\poppler\Library\bin"
            
            # Converter PDF para imagens
            if os.path.exists(poppler_path):
                imagens = convert_from_bytes(arquivo, poppler_path=poppler_path)
            else:
                # Tentar sem especificar path (se estiver no PATH do sistema)
                imagens = convert_from_bytes(arquivo)
            
            # OCR em cada página
            texto_completo = []
            for imagem in imagens:
                try:
                    # Tentar com português primeiro
                    texto = pytesseract.image_to_string(imagem, lang='por')
                except Exception:
                    try:
                        # Se falhar, tentar com inglês (mais disponível)
                        texto = pytesseract.image_to_string(imagem, lang='eng')
                    except Exception:
                        # Se ainda falhar, usar padrão (eng)
                        texto = pytesseract.image_to_string(imagem)
                
                texto_completo.append(texto)
            
            conteudo = '\n'.join(texto_completo)
            
            # Detectar banco
            self.banco_detectado = self.detectar_banco(conteudo[:1000])
            
            # Extrair transações com regex
            transacoes = self._extrair_transacoes_texto(conteudo)
            
            return transacoes
            
        except Exception as e:
            raise ValueError(f"Erro ao processar PDF: {str(e)}")
    
    def _parse_ofx(self, arquivo: bytes) -> List[Dict]:
        """
        Parser de OFX (Open Financial Exchange).
        """
        try:
            # Verificar se biblioteca está disponível
            try:
                from ofxparse import OfxParser
            except ImportError:
                raise ValueError("OFX parsing requer: pip install ofxparse")
            
            # Parse OFX
            ofx = OfxParser.parse(BytesIO(arquivo))
            
            # Detectar banco
            if hasattr(ofx, 'account') and hasattr(ofx.account, 'institution'):
                self.banco_detectado = ofx.account.institution.organization.lower()
            
            # Extrair transações
            transacoes = []
            for account in ofx.accounts:
                for transaction in account.statement.transactions:
                    valor = float(transaction.amount)
                    transacoes.append({
                        'data': transaction.date,
                        'descricao': transaction.memo or transaction.payee,
                        'valor': abs(valor),
                        'tipo': 'entrada' if valor > 0 else 'saida'
                    })
            
            return transacoes
            
        except Exception as e:
            raise ValueError(f"Erro ao processar OFX: {str(e)}")
    
    def _detectar_coluna_data(self, colunas: List[str]) -> Optional[str]:
        """Detecta coluna de data."""
        keywords = ['data', 'date', 'dt', 'vencimento', 'lancamento']
        for col in colunas:
            if any(kw in col for kw in keywords):
                return col
        return None
    
    def _detectar_coluna_descricao(self, colunas: List[str]) -> Optional[str]:
        """Detecta coluna de descrição."""
        keywords = ['descricao', 'historico', 'description', 'memo', 'lancamento', 'beneficiario']
        for col in colunas:
            if any(kw in col for kw in keywords):
                return col
        return None
    
    def _detectar_coluna_valor(self, colunas: List[str]) -> Optional[str]:
        """Detecta coluna de valor."""
        keywords = ['valor', 'value', 'amount', 'total', 'credito', 'debito']
        for col in colunas:
            if any(kw in col for kw in keywords):
                return col
        return None
    
    def _parse_data(self, valor) -> Optional[datetime]:
        """Parse flexível de data."""
        if pd.isna(valor):
            return None
        
        if isinstance(valor, datetime):
            return valor
        
        if isinstance(valor, pd.Timestamp):
            return valor.to_pydatetime()
        
        # String
        valor_str = str(valor).strip()
        
        # Formatos comuns brasileiros
        formatos = [
            '%d/%m/%Y',
            '%d/%m/%y',
            '%d-%m-%Y',
            '%d-%m-%y',
            '%Y-%m-%d',
            '%d.%m.%Y',
            '%d.%m.%y'
        ]
        
        for fmt in formatos:
            try:
                return datetime.strptime(valor_str, fmt)
            except:
                continue
        
        return None
    
    def _parse_valor(self, valor) -> float:
        """Parse flexível de valor monetário."""
        if pd.isna(valor):
            return 0.0
        
        if isinstance(valor, (int, float)):
            return float(valor)
        
        # String
        valor_str = str(valor).strip()
        
        # Remover símbolos de moeda
        valor_str = valor_str.replace('R$', '').replace('$', '').strip()
        
        # Normalizar separadores (brasileiro usa , para decimal)
        # Se tem ponto E vírgula, ponto é milhar
        if '.' in valor_str and ',' in valor_str:
            valor_str = valor_str.replace('.', '').replace(',', '.')
        # Se tem só vírgula, é decimal
        elif ',' in valor_str:
            valor_str = valor_str.replace(',', '.')
        
        # Remover espaços
        valor_str = valor_str.replace(' ', '')
        
        try:
            return float(valor_str)
        except:
            return 0.0
    
    def _extrair_transacoes_texto(self, texto: str) -> List[Dict]:
        """
        Extrai transações de texto OCR usando regex.
        Padrão: data + descrição + valor
        """
        transacoes = []
        
        # Regex para detectar linhas com data e valor
        # Ex: "10/01/2025 PIX MERCIO HIDEIOSHI 5.000,00"
        padrao = r'(\d{2}[\/\-\.]\d{2}[\/\-\.]\d{2,4})\s+(.+?)\s+([\d\.,]+)'
        
        for match in re.finditer(padrao, texto):
            data_str = match.group(1)
            descricao = match.group(2).strip()
            valor_str = match.group(3)
            
            data = self._parse_data(data_str)
            valor = self._parse_valor(valor_str)
            
            if data and descricao and valor > 0:
                # Detectar se é entrada ou saída (heurística)
                tipo = 'entrada'
                if any(kw in descricao.lower() for kw in ['pag', 'debito', 'compra', 'saque']):
                    tipo = 'saida'
                
                transacoes.append({
                    'data': data,
                    'descricao': descricao,
                    'valor': valor,
                    'tipo': tipo
                })
        
        return transacoes
    
    @staticmethod
    def gerar_hash_transacao(data: datetime, descricao: str, valor: float) -> str:
        """
        Gera hash único para evitar duplicatas.
        """
        conteudo = f"{data.isoformat()}{descricao}{valor}"
        return hashlib.md5(conteudo.encode()).hexdigest()
    
    @staticmethod
    def normalizar_descricao(descricao: str) -> str:
        """
        Normaliza descrição para facilitar matching.
        """
        # Uppercase
        desc = descricao.upper()
        
        # Remover acentos
        desc = desc.replace('Á', 'A').replace('É', 'E').replace('Í', 'I')
        desc = desc.replace('Ó', 'O').replace('Ú', 'U').replace('Ã', 'A')
        desc = desc.replace('Õ', 'O').replace('Ç', 'C')
        
        # Remover espaços extras
        desc = ' '.join(desc.split())
        
        return desc
