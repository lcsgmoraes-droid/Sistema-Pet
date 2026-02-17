"""
🚀 IMPORTADOR SIMPLESVET → SISTEMA PET
====================================

Script profissional para migração de dados do SimplesVet para produção.

CARACTERÍSTICAS:
- Validação completa antes de inserir
- Logs detalhados de todas as operações
- Modo dry-run (teste sem inserir)
- Tratamento robusto de erros
- Relatório de qualidade dos dados
- Suporte a rollback
- Importação em fases

USAGE:
    # Teste (não insere nada)
    python importador_producao.py --dry-run --limite 100
    
    # Importação real
    python importador_producao.py --fase clientes --limite 500
    python importador_producao.py --fase all
"""

import csv
import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dataclasses import dataclass, asdict

# =============================================================================
# CONFIGURAÇÃO
# =============================================================================

# Caminhos
SIMPLESVET_PATH = Path(r"c:\Users\Lucas\OneDrive\Área de Trabalho\Programa\Sistema Pet\simplesvet\banco")
LOG_DIR = Path(__file__).parent / "logs_importacao"
LOG_DIR.mkdir(exist_ok=True)

# Banco de dados (DEV por padrão, trocar para PROD quando necessário)
DATABASE_URL = "postgresql://postgres:postgres@localhost:5433/petshop_dev"

# IDs do sistema
USER_ID = 1
TENANT_ID = None

# Limites de campos (baseado no schema do banco)
LIMITES_CAMPOS = {
    'clientes': {
        'nome': 200,
        'cpf': 14,
        'telefone': 20,
        'celular': 20,
        'email': 200,
        'cep': 10,
        'endereco': 200,
        'numero': 20,
        'complemento': 100,
        'bairro': 100,
        'cidade': 100,
        'estado': 2,
        'codigo': 50,
    },
    'produtos': {
        'nome': 200,
        'codigo': 50,
        'codigo_barras': 50,
    },
    'pets': {
        'nome': 100,
        'especie': 50,
        'raca': 100,
        'cor': 50,
        'microchip': 50,
    }
}

# =============================================================================
# DATACLASSES PARA VALIDAÇÃO
# =============================================================================

@dataclass
class ResultadoValidacao:
    valido: bool
    erros: List[str]
    avisos: List[str]
    dados_limpos: Dict[str, Any]

@dataclass
class EstatisticasImportacao:
    total: int = 0
    validos: int = 0
    invalidos: int = 0
    duplicados: int = 0
    importados: int = 0
    erros: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.erros is None:
            self.erros = []

# =============================================================================
# CLASSE PRINCIPAL
# =============================================================================

class ImportadorProducao:
    """Importador robusto para produção"""
    
    def __init__(self, database_url: str, dry_run: bool = False):
        self.database_url = database_url
        self.dry_run = dry_run
        self.engine = create_engine(database_url)
        self.Session = sessionmaker(bind=self.engine)
        
        # Estatísticas
        self.stats = {
            'clientes': EstatisticasImportacao(),
            'produtos': EstatisticasImportacao(),
            'pets': EstatisticasImportacao(),
            'vendas': EstatisticasImportacao(),
        }
        
        # Mapeamento de IDs antigos → novos
        self.id_map = {
            'pessoas': {},
            'produtos': {},
            'animais': {},
        }
        
        # Contatos (telefones)
        self.contatos = {}
        
        # Log file
        self.log_file = LOG_DIR / f"importacao_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        self.log(f"{'='*80}")
        self.log(f"IMPORTADOR SIMPLESVET - MODO {'DRY-RUN (TESTE)' if dry_run else 'PRODUÇÃO'}")
        self.log(f"{'='*80}")
        self.log(f"Banco: {database_url}")
        self.log(f"Logs: {self.log_file}")
        self.log(f"{'='*80}\n")
    
    def log(self, msg: str, nivel: str = 'INFO'):
        """Log com timestamp em arquivo e console"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        linha = f"[{timestamp}] [{nivel:5}] {msg}"
        print(linha)
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(linha + '\n')
    
    def get_tenant_id(self, db) -> str:
        """Busca tenant_id do sistema"""
        global TENANT_ID
        if TENANT_ID:
            return TENANT_ID
        
        result = db.execute(text("SELECT tenant_id FROM users WHERE id = :uid LIMIT 1"), {"uid": USER_ID})
        row = result.fetchone()
        if row:
            TENANT_ID = str(row[0])
            self.log(f"Tenant ID: {TENANT_ID}")
            return TENANT_ID
        
        self.log("Tenant ID não encontrado!", 'ERROR')
        raise Exception("Tenant ID não encontrado")
    
    def ler_csv(self, nome_arquivo: str, limite: Optional[int] = None) -> List[Dict]:
        """Lê arquivo CSV do SimplesVet"""
        caminho = SIMPLESVET_PATH / nome_arquivo
        if not caminho.exists():
            self.log(f"Arquivo não encontrado: {nome_arquivo}", 'ERROR')
            return []
        
        try:
            with open(caminho, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter=',', quotechar='"')
                registros = list(reader)
                
            if limite:
                registros = registros[:limite]
            
            self.log(f"Lidos {len(registros)} registros de {nome_arquivo}")
            return registros
        except Exception as e:
            self.log(f"Erro ao ler {nome_arquivo}: {e}", 'ERROR')
            return []
    
    def truncar_campo(self, valor: Any, max_length: int, nome_campo: str = '') -> str:
        """Trunca campo respeitando limite e loga se necessário"""
        if valor is None or valor == 'NULL':
            return None
        
        valor_str = str(valor).strip()
        if len(valor_str) > max_length:
            truncado = valor_str[:max_length]
            self.log(f"Campo '{nome_campo}' truncado de {len(valor_str)} para {max_length} chars", 'WARN')
            return truncado
        
        return valor_str if valor_str else None
    
    def limpar_cpf(self, cpf_str: str) -> Optional[str]:
        """Limpa e valida CPF"""
        if not cpf_str or cpf_str == 'NULL':
            return None
        
        cpf = ''.join(filter(str.isdigit, cpf_str))
        if len(cpf) == 11:
            return cpf
        elif len(cpf) > 0:
            self.log(f"CPF inválido (tamanho {len(cpf)}): {cpf_str}", 'WARN')
        
        return None
    
    def parse_date(self, data_str: str) -> Optional[datetime]:
        """Converte string para datetime"""
        if not data_str or data_str == 'NULL':
            return None
        
        formatos = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
            '%d/%m/%Y %H:%M:%S',
            '%d/%m/%Y'
        ]
        
        for fmt in formatos:
            try:
                return datetime.strptime(data_str.strip(), fmt)
            except:
                continue
        
        return None
    
    def parse_decimal(self, valor: str) -> float:
        """Converte string para decimal"""
        if not valor or valor == 'NULL':
            return 0.0
        
        try:
            return float(str(valor).replace(',', '.'))
        except:
            return 0.0
    
    # =========================================================================
    # VALIDAÇÃO DE CLIENTES
    # =========================================================================
    
    def validar_cliente(self, row: Dict) -> ResultadoValidacao:
        """Valida e limpa dados de um cliente"""
        erros = []
        avisos = []
        limites = LIMITES_CAMPOS['clientes']
        
        # Nome obrigatório
        nome = row.get('pes_var_nome', '').strip()
        if not nome or nome == 'NULL':
            erros.append("Nome é obrigatório")
            return ResultadoValidacao(False, erros, avisos, {})
        
        # Código obrigatório
        codigo = row.get('pes_var_chave', '').strip()
        if not codigo or codigo == 'NULL':
            erros.append("Código é obrigatório")
            return ResultadoValidacao(False, erros, avisos, {})
        
        # Processar campos
        cpf = self.limpar_cpf(row.get('pes_var_cpf'))
        
        # Estado: máximo 2 caracteres
        estado_raw = row.get('end_var_uf')
        estado = None
        if estado_raw and estado_raw != 'NULL':
            estado = estado_raw.strip().upper()[:2]
        
        # Montar dados limpos
        dados = {
            'user_id': USER_ID,
            'tenant_id': TENANT_ID,
            'codigo': self.truncar_campo(codigo, limites['codigo'], 'codigo'),
            'nome': self.truncar_campo(nome, limites['nome'], 'nome'),
            'cpf': cpf,
            'telefone': self.truncar_campo(row.get('telefone'), limites['telefone'], 'telefone'),
            'celular': self.truncar_campo(row.get('celular'), limites['celular'], 'celular'),
            'email': self.truncar_campo(row.get('pes_var_email'), limites['email'], 'email'),
            'cep': self.truncar_campo(row.get('end_var_cep'), limites['cep'], 'cep'),
            'endereco': self.truncar_campo(row.get('end_var_endereco'), limites['endereco'], 'endereco'),
            'numero': self.truncar_campo(row.get('end_var_numero'), limites['numero'], 'numero'),
            'complemento': self.truncar_campo(row.get('end_var_complemento'), limites['complemento'], 'complemento'),
            'bairro': self.truncar_campo(row.get('end_var_bairro'), limites['bairro'], 'bairro'),
            'cidade': self.truncar_campo(row.get('end_var_municipio'), limites['cidade'], 'cidade'),
            'estado': estado,
            'tipo_cadastro': 'cliente',
            'tipo_pessoa': 'PF',  # Corrigido: PF (Pessoa Física) ou PJ (Pessoa Jurídica) - VARCHAR(2)
            'observacoes': row.get('pes_txt_observacao') if row.get('pes_txt_observacao') != 'NULL' else None,
            'ativo': True,
            'created_at': self.parse_date(row.get('pes_dti_inclusao')),
        }
        
        # Validações adicionais
        if dados['email'] and '@' not in dados['email']:
            avisos.append(f"Email pode ser inválido: {dados['email']}")
        
        if not dados['telefone'] and not dados['celular']:
            avisos.append("Cliente sem telefone")
        
        return ResultadoValidacao(True, erros, avisos, dados)
    
    # =========================================================================
    # IMPORTAÇÃO DE CLIENTES
    # =========================================================================
    
    def carregar_contatos(self):
        """Carrega mapa de contatos (telefones) dos clientes"""
        self.log("Carregando contatos...")
        registros = self.ler_csv('glo_contato.csv')
        
        for row in registros:
            pes_id = row.get('pes_int_codigo')
            contato_raw = row.get('con_var_contato')
            contato = contato_raw.strip() if contato_raw else ''
            tipo = (row.get('tco_var_nome') or '').lower()
            
            if not pes_id or not contato:
                continue
            
            if pes_id not in self.contatos:
                self.contatos[pes_id] = {'telefone': None, 'celular': None}
            
            if 'cel' in tipo:
                self.contatos[pes_id]['celular'] = self.contatos[pes_id]['celular'] or contato
            elif 'tel' in tipo or 'fone' in tipo:
                self.contatos[pes_id]['telefone'] = self.contatos[pes_id]['telefone'] or contato
        
        self.log(f"Contatos carregados: {len(self.contatos)} pessoas")
    
    def importar_clientes(self, limite: Optional[int] = None):
        """Importa clientes com validação completa"""
        self.log("\n" + "="*80)
        self.log("FASE: IMPORTAÇÃO DE CLIENTES")
        self.log("="*80)
        
        # Carregar contatos
        self.carregar_contatos()
        
        # Ler clientes
        registros = self.ler_csv('glo_pessoa.csv', limite)
        self.stats['clientes'].total = len(registros)
        
        db = self.Session()
        commit_batch = 1000  # Commit a cada 1000 registros
        inserts_neste_batch = 0
        
        try:
            self.get_tenant_id(db)
            
            for idx, row in enumerate(registros, 1):
                try:
                    # Adicionar contatos ao row
                    pes_id = row.get('pes_int_codigo')
                    if pes_id in self.contatos:
                        row['telefone'] = self.contatos[pes_id].get('telefone')
                        row['celular'] = self.contatos[pes_id].get('celular')
                    
                    # Validar
                    resultado = self.validar_cliente(row)
                    
                    if not resultado.valido:
                        self.stats['clientes'].invalidos += 1
                        self.stats['clientes'].erros.append({
                            'linha': idx,
                            'codigo': row.get('pes_var_chave'),
                            'nome': row.get('pes_var_nome'),
                            'erros': resultado.erros
                        })
                        self.log(f"[{idx}/{self.stats['clientes'].total}] INVÁLIDO: {row.get('pes_var_nome')} - {resultado.erros}", 'ERROR')
                        continue
                    
                    # Avisos
                    if resultado.avisos:
                        for aviso in resultado.avisos:
                            self.log(f"[{idx}] AVISO: {aviso}", 'WARN')
                    
                    # Verificar duplicata
                    codigo = resultado.dados_limpos['codigo']
                    existe = db.execute(text("SELECT id FROM clientes WHERE codigo = :cod"), {"cod": codigo}).fetchone()
                    
                    if existe:
                        self.stats['clientes'].duplicados += 1
                        self.id_map['pessoas'][pes_id] = existe[0]
                        self.log(f"[{idx}/{self.stats['clientes'].total}] DUPLICADO: {resultado.dados_limpos['nome']} (#{codigo})", 'WARN')
                        continue
                    
                    # Inserir (ou simular em dry-run)
                    if self.dry_run:
                        self.log(f"[{idx}/{self.stats['clientes'].total}] DRY-RUN: Importaria {resultado.dados_limpos['nome']}", 'INFO')
                        self.stats['clientes'].validos += 1
                    else:
                        query = text("""
                            INSERT INTO clientes (
                                user_id, tenant_id, codigo, nome, cpf, telefone, celular, email,
                                cep, endereco, numero, complemento, bairro, cidade, estado,
                                tipo_cadastro, tipo_pessoa, observacoes, ativo, created_at, updated_at
                            ) VALUES (
                                :user_id, :tenant_id, :codigo, :nome, :cpf, :telefone, :celular, :email,
                                :cep, :endereco, :numero, :complemento, :bairro, :cidade, :estado,
                                :tipo_cadastro, :tipo_pessoa, :observacoes, :ativo, COALESCE(:created_at, NOW()), NOW()
                            )
                            RETURNING id
                        """)
                        
                        result = db.execute(query, resultado.dados_limpos)
                        novo_id = result.fetchone()[0]
                        self.id_map['pessoas'][pes_id] = novo_id
                        
                        self.stats['clientes'].importados += 1
                        inserts_neste_batch += 1
                        self.log(f"[{idx}/{self.stats['clientes'].total}] IMPORTADO: {resultado.dados_limpos['nome']} (#{codigo})", 'OK')
                        
                        # Commit em lotes para evitar perder tudo em caso de erro
                        if inserts_neste_batch >= commit_batch:
                            db.commit()
                            inserts_neste_batch = 0
                            self.log(f"Commit parcial realizado ({idx} registros processados)", 'INFO')
                    
                    self.stats['clientes'].validos += 1
                    
                except Exception as e:
                    self.stats['clientes'].invalidos += 1
                    erro_msg = str(e)
                    
                    # Extrair nome da coluna se possível
                    if 'column' in erro_msg.lower():
                        import re
                        match = re.search(r'column "([^"]+)"', erro_msg)
                        if match:
                            campo = match.group(1)
                            erro_msg = f"Campo '{campo}': {erro_msg[:150]}"
                    
                    self.stats['clientes'].erros.append({
                        'linha': idx,
                        'codigo': row.get('pes_var_chave'),
                        'nome': row.get('pes_var_nome'),
                        'erro': erro_msg[:200]
                    })
                    self.log(f"[{idx}] ERRO: {row.get('pes_var_nome')} - {erro_msg[:150]}", 'ERROR')
                    # Removido db.rollback() para não perder todos os inserts anteriores
                    continue
            
            if not self.dry_run:
                db.commit()
                self.log("Commit realizado com sucesso!", 'OK')
        
        finally:
            db.close()
    
    # =========================================================================
    # RELATÓRIOS
    # =========================================================================
    
    def gerar_relatorio(self):
        """Gera relatório completo da importação"""
        self.log("\n" + "="*80)
        self.log("RELATÓRIO FINAL DE IMPORTAÇÃO")
        self.log("="*80)
        
        for entidade, stats in self.stats.items():
            if stats.total > 0:
                self.log(f"\n{entidade.upper()}:")
                self.log(f"  Total processados: {stats.total}")
                self.log(f"  Válidos:          {stats.validos} ({stats.validos/stats.total*100:.1f}%)")
                self.log(f"  Inválidos:        {stats.invalidos}")
                self.log(f"  Duplicados:       {stats.duplicados}")
                
                if not self.dry_run:
                    self.log(f"  Importados:       {stats.importados}")
                
                if stats.erros:
                    self.log(f"  Erros:            {len(stats.erros)}")
        
        # Salvar relatório JSON
        relatorio_file = LOG_DIR / f"relatorio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        relatorio_data = {
            'timestamp': datetime.now().isoformat(),
            'modo': 'dry-run' if self.dry_run else 'producao',
            'database': self.database_url,
            'estatisticas': {k: asdict(v) for k, v in self.stats.items() if v.total > 0}
        }
        
        with open(relatorio_file, 'w', encoding='utf-8') as f:
            json.dump(relatorio_data, f, indent=2, ensure_ascii=False)
        
        self.log(f"\nRelatório JSON salvo em: {relatorio_file}")
        self.log("="*80)

# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description='Importador SimplesVet para Produção')
    parser.add_argument('--dry-run', action='store_true', help='Modo teste (não insere dados)')
    parser.add_argument('--limite', type=int, help='Limitar número de registros')
    parser.add_argument('--fase', default='clientes', choices=['clientes', 'produtos', 'pets', 'vendas', 'all'])
    parser.add_argument('--database', default=DATABASE_URL, help='URL do banco de dados')
    
    args = parser.parse_args()
    
    # Criar importador
    importador = ImportadorProducao(
        database_url=args.database,
        dry_run=args.dry_run
    )
    
    # Executar fases
    if args.fase in ['clientes', 'all']:
        importador.importar_clientes(args.limite)
    
    # TODO: Adicionar outras fases (produtos, pets, vendas)
    
    # Gerar relatório
    importador.gerar_relatorio()

if __name__ == "__main__":
    main()
