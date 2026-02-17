#!/usr/bin/env python3
"""
IMPORTADOR DE PETS - SimplesVet → PetShop Pro
==============================================

Importa pets (animais) do SimplesVet mantendo relacionamento com clientes.

FONTE: simplesvet/banco/vet_animal.csv

CARACTERÍSTICAS:
- Dry-run mode (--dry-run) para testar antes de importar
- Limite customizável (--limite N) para testes incrementais
- Anti-duplicação via campo 'codigo' (UNIQUE)
- Logging detalhado em logs_importacao/
- Relatório JSON com estatísticas
- Validação de campos antes da inserção
- Busca de clientes por código do SimplesVet

MAPEAMENTO:
  SimplesVet              →  PetShop
  -------------------------------------------
  ani_int_codigo          →  codigo (UNIQUE)
  pes_int_codigo          →  cliente_id (via código)
  ani_var_nome            →  nome
  esp_var_nome            →  especie
  rac_var_nome            →  raca
  ani_var_sexo            →  sexo (Macho/Fêmea)
  ani_var_esterilizacao   →  castrado (boolean)
  ani_dat_nascimento      →  data_nascimento
  pel_var_nome            →  cor_pelagem
  ani_var_chip            →  microchip
  ani_dec_peso            →  peso
  ani_var_foto            →  foto_url
  ani_var_morto           →  ativo (NOT morto)

USO:
  # Testar com 10 pets (sem salvar no banco)
  python importador_pets.py --dry-run --limite 10

  # Importar 100 pets reais
  python importador_pets.py --limite 100

  # Importar todos os pets
  python importador_pets.py
"""

import os
import sys
import csv
import argparse
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

# =====================
# CONFIGURAÇÕES
# =====================
SIMPLESVET_PATH = r"c:\Users\Lucas\OneDrive\Área de Trabalho\Programa\Sistema Pet\simplesvet\banco"
DATABASE_URL = "postgresql://postgres:postgres@localhost:5433/petshop_dev"
TENANT_ID = "9df51a66-72bb-495f-a4a6-8a4953b20eae"
USER_ID = 1

# Limites de campos (VARCHAR constraints)
LIMITES_CAMPOS = {
    'codigo': 50,
    'nome': 255,
    'especie': 50,
    'raca': 100,
    'sexo': 10,
    'cor_pelagem': 100,
    'microchip': 50,
    'foto_url': 500,
}

# =====================
# DATACLASSES
# =====================
@dataclass
class ResultadoValidacao:
    valido: bool
    dados_limpos: Optional[Dict[str, Any]]
    erros: List[str]
    avisos: List[str]

@dataclass
class EstatisticasImportacao:
    total_processados: int = 0
    validos: int = 0
    invalidos: int = 0
    duplicados: int = 0
    importados: int = 0
    clientes_nao_encontrados: int = 0
    erros: List[str] = None
    
    def __post_init__(self):
        if self.erros is None:
            self.erros = []

# =====================
# IMPORTADOR
# =====================
class ImportadorPets:
    def __init__(self, database_url: str, tenant_id: str, user_id: int, dry_run: bool = False):
        self.database_url = database_url
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.dry_run = dry_run
        
        # Session
        self.engine = create_engine(database_url)
        self.Session = sessionmaker(bind=self.engine)
        
        # Cache de clientes (codigo_simplesvet -> cliente_id)
        self.clientes_cache: Dict[str, int] = {}
        
        # Mapeamento pes_int_codigo → pes_var_chave (para pets)
        self.mapa_id_codigo: Dict[str, str] = {}
        
        # Stats
        self.stats = EstatisticasImportacao()
        
        # Setup logs
        self.log_dir = Path("logs_importacao")
        self.log_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"pets_{timestamp}.log"
        self.json_file = self.log_dir / f"pets_{timestamp}.json"
        
    def log(self, msg: str, tipo: str = 'INFO'):
        """Log para arquivo e console"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        prefix = {'INFO': '[INFO]', 'OK': '[OK]  ', 'ERROR': '[ERR] ', 'WARN': '[WARN]'}
        log_msg = f"{timestamp} {prefix.get(tipo, '[INFO]')} {msg}"
        
        print(log_msg)
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_msg + '\n')
    
    def truncar_campo(self, valor: str, campo: str) -> str:
        """Trunca string para caber no VARCHAR do banco"""
        if not valor or campo not in LIMITES_CAMPOS:
            return valor
        
        limite = LIMITES_CAMPOS[campo]
        if len(valor) > limite:
            self.log(f"Campo '{campo}' truncado: {valor[:30]}... ({len(valor)} → {limite} chars)", 'WARN')
            return valor[:limite]
        return valor
    
    def normalizar_valor(self, valor: str) -> Optional[str]:
        """Converte 'NULL' em None"""
        if not valor or valor.strip().upper() == 'NULL':
            return None
        return valor.strip()
    
    def carregar_clientes(self, session):
        """Carrega cache de códigos de clientes"""
        self.log("Carregando cache de clientes...")
        result = session.execute(
            text("""
                SELECT id, codigo 
                FROM clientes 
                WHERE tenant_id = :tenant_id AND ativo = true
            """),
            {'tenant_id': self.tenant_id}
        ).fetchall()
        
        for cliente_id, codigo in result:
            if codigo:
                self.clientes_cache[str(codigo)] = cliente_id
        
        # Carregar mapeamento ID → Código do CSV SimplesVet
        csv_path = Path(SIMPLESVET_PATH) / "glo_pessoa.csv"
        if csv_path.exists():
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter=',', quotechar='"')
                for row in reader:
                    pes_int_codigo = row.get('pes_int_codigo')
                    pes_var_chave = row.get('pes_var_chave')
                    
                    # Validar campos
                    if pes_int_codigo and pes_var_chave:
                        pes_int_codigo = str(pes_int_codigo).strip()
                        pes_var_chave = str(pes_var_chave).strip()
                        
                        if pes_int_codigo and pes_var_chave:
                            # Map pes_int_codigo → pes_var_chave (codigo usado no banco)
                            self.mapa_id_codigo[pes_int_codigo] = pes_var_chave
        
        self.log(f"Cache: {len(self.clientes_cache)} clientes carregados")
        self.log(f"Mapeamento: {len(self.mapa_id_codigo)} IDs para códigos")
    
    def obter_cliente_id(self, codigo_simplesvet: str) -> Optional[int]:
        """Busca cliente por código do SimplesVet (pes_int_codigo → pes_var_chave →cliente_id)"""
        if not codigo_simplesvet:
            return None
        
        # Mapear pes_int_codigo para pes_var_chave
        codigo_chave = self.mapa_id_codigo.get(str(codigo_simplesvet))
        if not codigo_chave:
            return None
        
        # Buscar cliente_id pelo codigo (pes_var_chave)
        return self.clientes_cache.get(str(codigo_chave))
    
    def converter_data(self, data_str: str) -> Optional[str]:
        """Converte data do SimplesVet para ISO 8601"""
        if not data_str or data_str == 'NULL':
            return None
        
        try:
            # Formato: 2012-06-08 ou 2012-06-08 10:30:15
            dt = datetime.strptime(data_str.split()[0], '%Y-%m-%d')
            return dt.strftime('%Y-%m-%d')
        except:
            return None
    
    def validar_pet(self, row: dict, session) -> ResultadoValidacao:
        """Valida e prepara dados do pet"""
        erros = []
        avisos = []
        
        # Código único (OBRIGATÓRIO)
        codigo = self.normalizar_valor(row.get('ani_int_codigo', ''))
        if not codigo:
            return ResultadoValidacao(valido=False, dados_limpos=None, 
                                     erros=['Código do pet ausente'], avisos=[])
        
        codigo = self.truncar_campo(codigo, 'codigo')
        
        # Verificar duplicata
        existe = session.execute(
            text("SELECT 1 FROM pets WHERE codigo = :codigo AND tenant_id = :tenant_id LIMIT 1"),
            {'codigo': codigo, 'tenant_id': self.tenant_id}
        ).fetchone()
        
        if existe:
            return ResultadoValidacao(valido=False, dados_limpos=None,
                                     erros=[f'Pet com código {codigo} já existe'], avisos=[])
        
        # Cliente (OBRIGATÓRIO)
        codigo_cliente = self.normalizar_valor(row.get('pes_int_codigo', ''))
        cliente_id = self.obter_cliente_id(codigo_cliente)
        
        if not cliente_id:
            return ResultadoValidacao(valido=False, dados_limpos=None,
                                     erros=[f'Cliente {codigo_cliente} não encontrado'], avisos=[])
        
        # Nome (OBRIGATÓRIO)
        nome = self.normalizar_valor(row.get('ani_var_nome', ''))
        if not nome:
            erros.append('Nome do pet ausente')
        nome = self.truncar_campo(nome, 'nome')
        
        # Espécie (OBRIGATÓRIO)
        especie = self.normalizar_valor(row.get('esp_var_nome', ''))
        if not especie or especie == '':
            # Inferir da raça se possível
            raca = self.normalizar_valor(row.get('rac_var_nome', ''))
            if raca and any(x in raca.upper() for x in ['RETRIEVER', 'ROTTW', 'POODLE', 'BULLDOG', 'PASTOR']):
                especie = 'Canina'
            else:
                especie = 'Não Informado'  # Default
            avisos.append(f'Espécie não informada, usando: {especie}')
        
        especie = self.truncar_campo(especie, 'especie')
        
        # Raça
        raca = self.normalizar_valor(row.get('rac_var_nome', ''))
        raca = self.truncar_campo(raca, 'raca')
        
        # Sexo (mapear)
        sexo_raw = self.normalizar_valor(row.get('ani_var_sexo', ''))
        sexo = None
        if sexo_raw:
            if 'MACHO' in sexo_raw.upper():
                sexo = 'Macho'
            elif 'FÊMEA' in sexo_raw.upper() or 'FEMEA' in sexo_raw.upper():
                sexo = 'Fêmea'
        
        # Castrado (boolean)
        esterilizacao = self.normalizar_valor(row.get('ani_var_esterilizacao', ''))
        castrado = True if esterilizacao and 'CASTRADO' in esterilizacao.upper() else False
        
        # Data nascimento
        data_nascimento = self.converter_data(self.normalizar_valor(row.get('ani_dat_nascimento', '')))
        
        # Pelagem/Cor
        cor_pelagem = self.normalizar_valor(row.get('pel_var_nome', ''))
        cor_pelagem = self.truncar_campo(cor_pelagem, 'cor_pelagem')
        
        # Microchip
        microchip = self.normalizar_valor(row.get('ani_var_chip', ''))
        microchip = self.truncar_campo(microchip, 'microchip')
        
        # Peso
        peso_str = self.normalizar_valor(row.get('ani_dec_peso', ''))
        peso = None
        if peso_str:
            try:
                peso = float(peso_str.replace(',', '.'))
            except:
                avisos.append(f'Peso inválido: {peso_str}')
        
        # Foto
        foto_url = self.normalizar_valor(row.get('ani_var_foto', ''))
        foto_url = self.truncar_campo(foto_url, 'foto_url')
        
        # Ativo (inverso de morto)
        morto = self.normalizar_valor(row.get('ani_var_morto', ''))
        ativo = False if morto and morto.upper() == 'SIM' else True
        
        if erros:
            return ResultadoValidacao(valido=False, dados_limpos=None, erros=erros, avisos=avisos)
        
        # Dados limpos
        dados = {
            'codigo': codigo,
            'cliente_id': cliente_id,
            'nome': nome,
            'especie': especie,
            'raca': raca,
            'sexo': sexo,
            'castrado': castrado,
            'data_nascimento': data_nascimento,
            'cor_pelagem': cor_pelagem,
            'microchip': microchip,
            'peso': peso,
            'foto_url': foto_url,
            'ativo': ativo,
            'user_id': self.user_id,
            'tenant_id': self.tenant_id,
        }
        
        return ResultadoValidacao(valido=True, dados_limpos=dados, erros=[], avisos=avisos)
    
    def importar_pets(self, limite: Optional[int] = None):
        """Importa pets do CSV"""
        csv_path = Path(SIMPLESVET_PATH) / "vet_animal.csv"
        
        if not csv_path.exists():
            self.log(f"Arquivo não encontrado: {csv_path}", 'ERROR')
            return
        
        self.log("="*80)
        self.log(f"{'DRY-RUN - ' if self.dry_run else ''}IMPORTADOR SIMPLESVET - PETS")
        self.log("="*80)
        self.log(f"Banco: {self.database_url}")
        self.log(f"Logs: {self.log_file}")
        self.log("="*80)
        
        session = self.Session()
        
        try:
            # Carregar cache de clientes
            self.carregar_clientes(session)
            
            # Ler CSV
            self.log("Lendo arquivo vet_animal.csv...")
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter=',', quotechar='"')
                rows = list(reader)
            
            total_rows = len(rows)
            self.log(f"Lidos {total_rows} registros de vet_animal.csv")
            
            if limite:
                rows = rows[:limite]
                self.log(f"Limitando importação a {limite} registros")
            
            self.log(f"Tenant ID: {self.tenant_id}")
            self.log("")
            
            # Processar cada registro
            for idx, row in enumerate(rows, 1):
                self.stats.total_processados += 1
                
                # Validar
                resultado = self.validar_pet(row, session)
                
                if not resultado.valido:
                    self.stats.invalidos += 1
                    
                    # Verificar se é duplicata
                    if any('já existe' in erro for erro in resultado.erros):
                        self.stats.duplicados += 1
                        self.log(f"[{idx}/{len(rows)}] DUPLICADO: {row.get('ani_var_nome', 'N/A')} (#{row.get('ani_int_codigo', 'N/A')})", 'WARN')
                    elif any('não encontrado' in erro for erro in resultado.erros):
                        self.stats.clientes_nao_encontrados += 1
                        self.log(f"[{idx}/{len(rows)}] CLIENTE NÃO ENCONTRADO: {row.get('ani_var_nome', 'N/A')} (dono: {row.get('pes_int_codigo', 'N/A')})", 'WARN')
                    else:
                        self.log(f"[{idx}/{len(rows)}] ERRO: {', '.join(resultado.erros)}", 'ERROR')
                        self.stats.erros.append(f"Linha {idx}: {', '.join(resultado.erros)}")
                    continue
                
                # Avisos
                if resultado.avisos:
                    for aviso in resultado.avisos:
                        self.log(f"[{idx}/{len(rows)}] AVISO: {aviso}", 'WARN')
                
                self.stats.validos += 1
                
                # Inserir no banco (se não for dry-run)
                if not self.dry_run:
                    try:
                        session.execute(
                            text("""
                                INSERT INTO pets (
                                    codigo, cliente_id, nome, especie, raca, sexo,
                                    castrado, data_nascimento, cor_pelagem, microchip,
                                    peso, foto_url, ativo, user_id, tenant_id,
                                    created_at, updated_at
                                ) VALUES (
                                    :codigo, :cliente_id, :nome, :especie, :raca, :sexo,
                                    :castrado, :data_nascimento, :cor_pelagem, :microchip,
                                    :peso, :foto_url, :ativo, :user_id, :tenant_id,
                                    NOW(), NOW()
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
            self.stats.erros.append(f"FATAL: {str(e)}")
        finally:
            session.close()
        
        # Relatório final
        self.log("")
        self.log("="*80)
        self.log("RELATÓRIO FINAL")
        self.log("="*80)
        self.log(f"Total processados:          {self.stats.total_processados}")
        self.log(f"Válidos:                    {self.stats.validos}")
        self.log(f"Inválidos:                  {self.stats.invalidos}")
        self.log(f"  - Duplicados:             {self.stats.duplicados}")
        self.log(f"  - Clientes não encontr.:  {self.stats.clientes_nao_encontrados}")
        self.log(f"Importados com sucesso:     {self.stats.importados}")
        
        if self.stats.erros:
            self.log(f"Erros:                      {len(self.stats.erros)}")
        
        # Salvar JSON
        with open(self.json_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(self.stats), f, indent=2, ensure_ascii=False)
        
        self.log(f"Relatório JSON salvo em: {self.json_file}")
        self.log("="*80)

# =====================
# MAIN
# =====================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Importador de Pets SimplesVet')
    parser.add_argument('--dry-run', action='store_true', help='Simular importação (não salva no banco)')
    parser.add_argument('--limite', type=int, help='Limitar número de registros')
    
    args = parser.parse_args()
    
    importador = ImportadorPets(
        database_url=DATABASE_URL,
        tenant_id=TENANT_ID,
        user_id=USER_ID,
        dry_run=args.dry_run
    )
    
    importador.importar_pets(limite=args.limite)
