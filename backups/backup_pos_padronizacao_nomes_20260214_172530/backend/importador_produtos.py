#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Importador de Produtos do SimplesVet para o Sistema Pet
Versão de Produção com validação, logging e anti-duplicação
"""

import sys
import os
import csv
import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any
from dataclasses import dataclass
from pathlib import Path
import argparse

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Configurações
DATABASE_URL = "postgresql://postgres:postgres@localhost:5433/petshop_dev"
SIMPLESVET_PATH = r"c:\Users\Lucas\OneDrive\Área de Trabalho\Programa\Sistema Pet\simplesvet\banco"
TENANT_ID = "9df51a66-72bb-495f-a4a6-8a4953b20eae"
USER_ID = 1

# Limites de campos (para truncar se necessário)
LIMITES_CAMPOS = {
    'codigo': 50,
    'nome': 200,
    'tipo': 20,
    'unidade': 10,
    'codigo_barras': 13,
    'ncm': 8,
    'localizacao': 50,
}


@dataclass
class ResultadoValidacao:
    """Resultado da validação de um produto"""
    valido: bool
    dados_limpos: Optional[Dict[str, Any]] = None
    erros: list = None
    avisos: list = None


@dataclass
class EstatisticasImportacao:
    """Estatísticas da importação"""
    total: int = 0
    validos: int = 0
    invalidos: int = 0
    duplicados: int = 0
    importados: int = 0
    erros: list = None
    
    def __post_init__(self):
        if self.erros is None:
            self.erros = []


class ImportadorProdutos:
    """Importador de produtos do SimplesVet"""
    
    def __init__(self, database_url: str, tenant_id: str, user_id: int, dry_run: bool = False):
        self.database_url = database_url
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.dry_run = dry_run
        self.engine = create_engine(database_url)
        self.Session = sessionmaker(bind=self.engine)
        
        # Configurar logging
        log_dir = Path(__file__).parent / "logs_importacao"
        log_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"importacao_produtos_{timestamp}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='[%(asctime)s] [%(levelname)-5s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.log_file = log_file
        
        # Estatísticas
        self.stats = EstatisticasImportacao()
        
        # Cache de marcas/categorias criadas
        self.marcas_cache = {}
        self.categorias_cache = {}
        
    def log(self, mensagem: str, nivel: str = 'INFO'):
        """Log com suporte a diferentes níveis"""
        if nivel == 'INFO':
            self.logger.info(mensagem)
        elif nivel == 'WARN':
            self.logger.warning(mensagem)
        elif nivel == 'ERROR':
            self.logger.error(mensagem)
        elif nivel == 'DEBUG':
            self.logger.debug(mensagem)
    
    def truncar_campo(self, valor: Any, limite: int, nome_campo: str) -> Optional[str]:
        """Trunca campo se exceder limite"""
        if not valor or valor == 'NULL':
            return None
        
        valor_str = str(valor).strip()
        if len(valor_str) > limite:
            self.log(f"Campo '{nome_campo}' truncado de {len(valor_str)} para {limite} chars", 'WARN')
            return valor_str[:limite]
        
        return valor_str if valor_str else None
    
    def parse_decimal(self, valor: str) -> float:
        """Converte string para decimal"""
        if not valor or valor == 'NULL':
            return 0.0
        
        try:
            return float(str(valor).replace(',', '.'))
        except:
            return 0.0
    
    def obter_ou_criar_marca(self, nome_marca: str, session) -> Optional[int]:
        """Obtém ID de marca existente ou cria nova"""
        if not nome_marca or nome_marca == 'NULL':
            return None
        
        # Verificar cache
        nome_normalizado = nome_marca.strip().upper()
        if nome_normalizado in self.marcas_cache:
            return self.marcas_cache[nome_normalizado]
        
        # Buscar no banco
        result = session.execute(
            text("""
                SELECT id FROM marcas 
                WHERE tenant_id = :tenant_id AND UPPER(nome) = :nome AND ativo = true
                LIMIT 1
            """),
            {'tenant_id': self.tenant_id, 'nome': nome_normalizado}
        ).fetchone()
        
        if result:
            marca_id = result[0]
            self.marcas_cache[nome_normalizado] = marca_id
            return marca_id
        
        # Criar nova marca
        if not self.dry_run:
            result = session.execute(
                text("""
                    INSERT INTO marcas (nome, user_id, tenant_id, ativo, created_at, updated_at)
                    VALUES (:nome, :user_id, :tenant_id, true, NOW(), NOW())
                    RETURNING id
                """),
                {'nome': nome_marca.strip(), 'user_id': self.user_id, 'tenant_id': self.tenant_id}
            )
            marca_id = result.fetchone()[0]
            self.marcas_cache[nome_normalizado] = marca_id
            self.log(f"Nova marca criada: {nome_marca} (ID: {marca_id})")
            return marca_id
        
        return None
    
    def obter_ou_criar_categoria(self, nome_categoria: str, session) -> Optional[int]:
        """Obtém ID de categoria existente ou cria nova"""
        if not nome_categoria or nome_categoria == 'NULL':
            return None
        
        # Verificar cache
        nome_normalizado = nome_categoria.strip().upper()
        if nome_normalizado in self.categorias_cache:
            return self.categorias_cache[nome_normalizado]
        
        # Buscar no banco
        result = session.execute(
            text("""
                SELECT id FROM categorias 
                WHERE tenant_id = :tenant_id AND UPPER(nome) = :nome AND ativo = true
                LIMIT 1
            """),
            {'tenant_id': self.tenant_id, 'nome': nome_normalizado}
        ).fetchone()
        
        if result:
            cat_id = result[0]
            self.categorias_cache[nome_normalizado] = cat_id
            return cat_id
        
        # Criar nova categoria
        if not self.dry_run:
            result = session.execute(
                text("""
                    INSERT INTO categorias (nome, user_id, tenant_id, ativo, ordem, created_at, updated_at)
                    VALUES (:nome, :user_id, :tenant_id, true, 1, NOW(), NOW())
                    RETURNING id
                """),
                {'nome': nome_categoria.strip(), 'user_id': self.user_id, 'tenant_id': self.tenant_id}
            )
            cat_id = result.fetchone()[0]
            self.categorias_cache[nome_normalizado] = cat_id
            self.log(f"Nova categoria criada: {nome_categoria} (ID: {cat_id})")
            return cat_id
        
        return None
    
    def validar_produto(self, row: dict, session) -> ResultadoValidacao:
        """Valida e limpa dados de um produto"""
        erros = []
        avisos = []
        limites = LIMITES_CAMPOS
        
        # Campos obrigatórios
        codigo = self.truncar_campo(row.get('pro_var_chave'), limites['codigo'], 'codigo')
        nome = self.truncar_campo(row.get('pro_var_nome'), limites['nome'], 'nome')
        
        if not codigo:
            erros.append("Código do produto é obrigatório")
        
        if not nome:
            erros.append("Nome do produto é obrigatório")
        
        if erros:
            return ResultadoValidacao(valido=False, erros=erros, avisos=avisos)
        
        # Verificar duplicação por código
        result = session.execute(
            text("""
                SELECT id, nome FROM produtos 
                WHERE tenant_id = :tenant_id AND codigo = :codigo
                LIMIT 1
            """),
            {'tenant_id': self.tenant_id, 'codigo': codigo}
        ).fetchone()
        
        if result:
            avisos.append(f"DUPLICADO: Produto {nome} (#{codigo}) já existe com ID {result[0]}")
            return ResultadoValidacao(valido=False, erros=[], avisos=avisos)
        
        # Processar marca e categoria
        marca_id = self.obter_ou_criar_marca(row.get('mar_var_nome'), session)
        categoria_id = self.obter_ou_criar_categoria(row.get('tpr_var_nome'), session)
        
        # Processar situação (ativo/inativo)
        situacao_str = row.get('pro_var_status', 'Ativo')
        situacao = situacao_str.upper() == 'ATIVO' if situacao_str else True
        
        # Montar dados limpos
        dados = {
            'codigo': codigo,
            'nome': nome,
            'tipo': 'produto',  # Padrão
            'tipo_produto': 'SIMPLES',  # Padrão
            'situacao': situacao,
            'unidade': self.truncar_campo(row.get('pro_var_unidade', 'UN'), limites['unidade'], 'unidade') or 'UN',
            'codigo_barras': self.truncar_campo(row.get('pro_var_codigobarra'), limites['codigo_barras'], 'codigo_barras'),
            'ncm': self.truncar_campo(row.get('pro_var_codigoncm'), limites['ncm'], 'ncm'),
            'preco_custo': self.parse_decimal(row.get('pro_dec_custo')),
            'preco_venda': self.parse_decimal(row.get('pro_dec_preco')),
            'estoque_atual': self.parse_decimal(row.get('pro_dec_estoque')),
            'estoque_minimo': self.parse_decimal(row.get('pro_dec_minimo')),
            'estoque_maximo': self.parse_decimal(row.get('pro_dec_maximo')),
            'comissao_padrao': self.parse_decimal(row.get('pro_dec_comissao')),
            'marca_id': marca_id,
            'categoria_id': categoria_id,
            'user_id': self.user_id,
            'tenant_id': self.tenant_id,
            'ativo': True,  # Produto ativo por padrão
        }
        
        # Validações adicionais
        if dados['preco_venda'] <= 0:
            avisos.append("Preço de venda zerado ou negativo")
        
        if dados['estoque_atual'] < 0:
            avisos.append("Estoque negativo")
        
        return ResultadoValidacao(valido=True, dados_limpos=dados, erros=[], avisos=avisos)
    
    def importar_produtos(self, limite: Optional[int] = None):
        """Importa produtos do CSV"""
        csv_path = Path(SIMPLESVET_PATH) / "eco_produto.csv"
        
        if not csv_path.exists():
            self.log(f"Arquivo não encontrado: {csv_path}", 'ERROR')
            return
        
        self.log("="*80)
        self.log(f"{'DRY-RUN - ' if self.dry_run else ''}IMPORTADOR SIMPLESVET - PRODUTOS")
        self.log("="*80)
        self.log(f"Banco: {self.database_url}")
        self.log(f"Logs: {self.log_file}")
        self.log("="*80)
        
        session = self.Session()
        
        try:
            # Ler CSV
            self.log("Lendo arquivo eco_produto.csv...")
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter=',', quotechar='"')
                rows = list(reader)
            
            total_rows = len(rows)
            self.log(f"Lidos {total_rows} registros de eco_produto.csv")
            
            if limite:
                rows = rows[:limite]
                self.log(f"Limitando importação a {limite} registros")
            
            self.log(f"Tenant ID: {self.tenant_id}")
            self.log("")
            
            # Processar cada registro
            for idx, row in enumerate(rows, 1):
                self.stats.total += 1
                
                # Validar produto
                resultado = self.validar_produto(row, session)
                
                if resultado.avisos:
                    for aviso in resultado.avisos:
                        if 'DUPLICADO' in aviso:
                            self.log(f"[{idx}/{len(rows)}] {aviso}", 'WARN')
                            self.stats.duplicados += 1
                        else:
                            self.log(f"[{idx}] AVISO: {aviso}", 'WARN')
                
                if not resultado.valido:
                    if resultado.erros:
                        for erro in resultado.erros:
                            self.log(f"[{idx}/{len(rows)}] ERRO: {erro}", 'ERROR')
                            self.stats.erros.append(f"Linha {idx}: {erro}")
                        self.stats.invalidos += 1
                    continue
                
                self.stats.validos += 1
                
                # Inserir no banco (se não for dry-run)
                if not self.dry_run:
                    try:
                        session.execute(
                            text("""
                                INSERT INTO produtos (
                                    codigo, nome, tipo, tipo_produto, situacao, unidade,
                                    codigo_barras, ncm, preco_custo, preco_venda,
                                    estoque_atual, estoque_minimo, estoque_maximo,
                                    comissao_padrao, marca_id, categoria_id,
                                    user_id, tenant_id, ativo, created_at, updated_at
                                ) VALUES (
                                    :codigo, :nome, :tipo, :tipo_produto, :situacao, :unidade,
                                    :codigo_barras, :ncm, :preco_custo, :preco_venda,
                                    :estoque_atual, :estoque_minimo, :estoque_maximo,
                                    :comissao_padrao, :marca_id, :categoria_id,
                                    :user_id, :tenant_id, :ativo, NOW(), NOW()
                                )
                            """),
                            resultado.dados_limpos
                        )
                        self.stats.importados += 1
                        self.log(f"[{idx}/{len(rows)}] IMPORTADO: {resultado.dados_limpos['nome']} (#{resultado.dados_limpos['codigo']})", 'OK')
                    except Exception as e:
                        erro_msg = str(e)[:200]
                        self.log(f"[{idx}/{len(rows)}] ERRO ao inserir: {erro_msg}", 'ERROR')
                        self.stats.erros.append(f"Linha {idx}: {erro_msg}")
                        self.stats.invalidos += 1
                        self.stats.validos -= 1
                else:
                    self.log(f"[{idx}/{len(rows)}] VÁLIDO (dry-run): {resultado.dados_limpos['nome']} (#{resultado.dados_limpos['codigo']})")
            
            # Commit
            if not self.dry_run:
                session.commit()
                self.log("Commit realizado com sucesso!", 'OK')
            else:
                self.log("DRY-RUN: Nenhuma alteração foi feita no banco")
        
        except Exception as e:
            session.rollback()
            self.log(f"ERRO FATAL: {str(e)}", 'ERROR')
            raise
        finally:
            session.close()
        
        # Relatório final
        self.log("")
        self.log("="*80)
        self.log("RELATÓRIO FINAL DE IMPORTAÇÃO")
        self.log("="*80)
        self.log(f"\nPRODUTOS:")
        self.log(f"  Total processados: {self.stats.total}")
        self.log(f"  Válidos:          {self.stats.validos} ({self.stats.validos/self.stats.total*100:.1f}%)")
        self.log(f"  Inválidos:        {self.stats.invalidos}")
        self.log(f"  Duplicados:       {self.stats.duplicados}")
        self.log(f"  Importados:       {self.stats.importados}")
        
        if self.stats.erros:
            self.log(f"\nErros encontrados: {len(self.stats.erros)}")
            for erro in self.stats.erros[:10]:
                self.log(f"  - {erro}", 'ERROR')
        
        self.log("="*80)


def main():
    parser = argparse.ArgumentParser(description='Importador de Produtos SimplesVet')
    parser.add_argument('--dry-run', action='store_true', help='Simular importação sem gravar no banco')
    parser.add_argument('--limite', type=int, help='Limitar número de registros importados')
    
    args = parser.parse_args()
    
    importador = ImportadorProdutos(
        database_url=DATABASE_URL,
        tenant_id=TENANT_ID,
        user_id=USER_ID,
        dry_run=args.dry_run
    )
    
    importador.importar_produtos(limite=args.limite)


if __name__ == "__main__":
    main()
