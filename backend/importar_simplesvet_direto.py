"""
🔄 IMPORTADOR SIMPLESVET → Sistema Pet (VERSÃO SIMPLIFICADA)

Este script importa dados sem carregar todos os models pesados,
evitando problemas de dependência circular.

Uso:
    python importar_simplesvet_direto.py --limite 100
    python importar_simplesvet_direto.py --all
"""

import csv
import argparse
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Configuração do banco DEV
DATABASE_URL = "postgresql://postgres:postgres@localhost:5433/petshop_dev"
SIMPLESVET_PATH = Path(r"c:\Users\Lucas\OneDrive\Área de Trabalho\Programa\Sistema Pet\simplesvet\banco")

# IDs fixos
USER_ID = 1
TENANT_ID = None

# Mapeamento de IDs
ID_MAP = {
    'pessoas': {},
    'animais': {},
    'produtos': {},
    'vendas': {},
    'especies': {},
    'racas': {},
    'marcas': {},
}

# Estatísticas
STATS = {
    'especies': {'total': 0, 'novos': 0, 'duplicado': 0, 'erro': 0},
    'racas': {'total': 0, 'novos': 0, 'duplicado': 0, 'erro': 0},
    'clientes': {'total': 0, 'novos': 0, 'duplicado': 0, 'erro': 0},
    'marcas': {'total': 0, 'novos': 0, 'duplicado': 0, 'erro': 0},
    'produtos': {'total': 0, 'novos': 0, 'duplicado': 0, 'erro': 0},
    'pets': {'total': 0, 'novos': 0, 'duplicado': 0, 'erro': 0},
    'vendas': {'total': 0, 'novos': 0, 'duplicado': 0, 'erro': 0},
}

# Criar engine e session
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def log(msg, nivel='INFO'):
    """Log com timestamp"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    icones = {'INFO': '[INFO]', 'OK': '[OK]  ', 'ERRO': '[ERR] ', 'WARN': '[WARN]', 'SKIP': '[SKIP]'}
    icone = icones.get(nivel, '[INFO]')
    print(f"[{timestamp}] {icone} {msg}")


def ler_csv(nome_arquivo, limite=None):
    """Lê arquivo CSV"""
    caminho = SIMPLESVET_PATH / nome_arquivo
    if not caminho.exists():
        log(f"Arquivo não encontrado: {nome_arquivo}", 'ERRO')
        return []
    
    with open(caminho, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file, delimiter=',', quotechar='"')
        registros = list(reader)
        if limite:
            registros = registros[:limite]
        log(f"Lidos {len(registros)} registros de {nome_arquivo}", 'INFO')
        return registros


def limpar_cpf(cpf_str):
    """Remove formatação do CPF"""
    if not cpf_str or cpf_str == 'NULL':
        return None
    return ''.join(filter(str.isdigit, cpf_str)) or None


def parse_decimal(valor):
    """Converte string para decimal"""
    if not valor or valor == 'NULL':
        return 0.0
    try:
        return float(valor.replace(',', '.'))
    except:
        return 0.0


def parse_date(data_str):
    """Converte string para data"""
    if not data_str or data_str == 'NULL':
        return None
    formatos = ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d/%m/%Y']
    for fmt in formatos:
        try:
            return datetime.strptime(data_str.strip(), fmt)
        except:
            continue
    return None


def get_tenant_id(db):
    """Busca tenant_id do sistema"""
    global TENANT_ID
    if TENANT_ID:
        return TENANT_ID
    
    result = db.execute(text("SELECT tenant_id FROM users WHERE id = :uid LIMIT 1"), {"uid": USER_ID})
    row = result.fetchone()
    if row:
        TENANT_ID = str(row[0])
        log(f"Tenant ID: {TENANT_ID}", 'OK')
        return TENANT_ID
    log("Tenant ID não encontrado!", 'ERRO')
    return None


def carregar_contatos():
    """Carrega contatos (telefones) dos clientes"""
    contatos = {}
    registros = ler_csv('glo_contato.csv', limite=None)
    
    for row in registros:
        pes_id = row.get('pes_int_codigo')
        contato_raw = row.get('con_var_contato')
        contato = contato_raw.strip() if contato_raw else ''
        tipo = (row.get('tco_var_nome') or '').lower()
        
        if not pes_id or not contato:
            continue
        
        if pes_id not in contatos:
            contatos[pes_id] = {'telefone': None, 'celular': None}
        
        if 'cel' in tipo:
            contatos[pes_id]['celular'] = contatos[pes_id]['celular'] or contato
        elif 'tel' in tipo or 'fone' in tipo:
            contatos[pes_id]['telefone'] = contatos[pes_id]['telefone'] or contato
    
    log(f"Carregados contatos de {len(contatos)} pessoas", 'OK')
    return contatos


# =============================================================================
# IMPORTAÇÕES
# =============================================================================

def importar_clientes(db, limite=None):
    """Importa clientes"""
    log("=" * 50, 'INFO')
    log("IMPORTANDO CLIENTES", 'INFO')
    log("=" * 50, 'INFO')
    
    contatos = carregar_contatos()
    registros = ler_csv('glo_pessoa.csv', limite)
    STATS['clientes']['total'] = len(registros)
    
    for row in registros:
        try:
            codigo = row.get('pes_var_chave')
            cpf = limpar_cpf(row.get('pes_var_cpf'))
            nome = row.get('pes_var_nome', '').strip()
            
            if not nome or nome == 'NULL':
                STATS['clientes']['erro'] += 1
                continue
            
            # Verificar duplicata por código
            if codigo:
                result = db.execute(text("SELECT id FROM clientes WHERE codigo = :cod"), {"cod": codigo})
                existe = result.fetchone()
                if existe:
                    ID_MAP['pessoas'][row['pes_int_codigo']] = existe[0]
                    STATS['clientes']['duplicado'] += 1
                    log(f"Cliente já existe: {nome} (#{codigo})", 'SKIP')
                    continue
            
            # Inserir cliente
            contato = contatos.get(row.get('pes_int_codigo'), {})
            
            # Limpar e truncar dados
            estado_raw = row.get('end_var_uf')
            estado = None
            if estado_raw and estado_raw != 'NULL':
                estado = estado_raw.strip().upper()[:2]  # Máximo 2 caracteres
            
            query = text("""
                INSERT INTO clientes (
                    user_id, tenant_id, codigo, nome, cpf, telefone, celular, email,
                    cep, endereco, numero, complemento, bairro, cidade, estado,
                    tipo_cadastro, tipo_pessoa, observacoes, ativo, created_at, updated_at
                ) VALUES (
                    :user_id, :tenant_id, :codigo, :nome, :cpf, :telefone, :celular, :email,
                    :cep, :endereco, :numero, :complemento, :bairro, :cidade, :estado,
                    'cliente', 'fisica', :observacoes, true, COALESCE(:created_at, NOW()), NOW()
                )
                RETURNING id
            """)
            
            result = db.execute(query, {
                "user_id": USER_ID,
                "tenant_id": TENANT_ID,
                "codigo": codigo,
                "nome": nome,
                "cpf": cpf,
                "telefone": contato.get('telefone'),
                "celular": contato.get('celular'),
                "email": row.get('pes_var_email') if row.get('pes_var_email') != 'NULL' else None,
                "cep": row.get('end_var_cep') if row.get('end_var_cep') != 'NULL' else None,
                "endereco": row.get('end_var_endereco') if row.get('end_var_endereco') != 'NULL' else None,
                "numero": row.get('end_var_numero') if row.get('end_var_numero') != 'NULL' else None,
                "complemento": row.get('end_var_complemento') if row.get('end_var_complemento') != 'NULL' else None,
                "bairro": row.get('end_var_bairro') if row.get('end_var_bairro') != 'NULL' else None,
                "cidade": row.get('end_var_municipio') if row.get('end_var_municipio') != 'NULL' else None,
                "estado": estado,
                "observacoes": row.get('pes_txt_observacao') if row.get('pes_txt_observacao') != 'NULL' else None,
                "created_at": parse_date(row.get('pes_dti_inclusao')),
            })
            
            novo_id = result.fetchone()[0]
            ID_MAP['pessoas'][row['pes_int_codigo']] = novo_id
            STATS['clientes']['novos'] += 1
            
        except Exception as e:
            STATS['clientes']['erro'] += 1
            print(f">>>  ERRO: Cliente {row.get('pes_var_nome', '?')}: {str(e)}")
            import traceback
            traceback.print_exc()
            db.rollback()  # Rollback para continuar
            continue
    
    db.commit()
    log(f"Clientes: {STATS['clientes']['novos']} novos | {STATS['clientes']['duplicado']} duplicados | {STATS['clientes']['erro']} erros", 'OK')


def exibir_resumo():
    """Exibe resumo final"""
    print("\n" + "=" * 80)
    print("RESUMO DA IMPORTAÇÃO".center(80))
    print("=" * 80)
    print(f"{'ENTIDADE':<15} | {'TOTAL':>6} | {'NOVOS':>6} | {'DUPLIC':>6} | {'ERROS':>6}")
    print("-" * 80)
    
    for entidade, stats in STATS.items():
        if stats['total'] > 0:
            print(f"{entidade.upper():<15} | {stats['total']:>6} | {stats['novos']:>6} | "
                  f"{stats['duplicado']:>6} | {stats['erro']:>6}")
    
    print("=" * 80 + "\n")


def main():
    parser = argparse.ArgumentParser(description='Importar dados do SimplesVet (versão simplificada)')
    parser.add_argument('--limite', type=int, default=20, help='Limite de registros')
    parser.add_argument('--all', action='store_true', help='Importar todos os registros')
    
    args = parser.parse_args()
    
    if args.all:
        limite = None
        log("IMPORTAÇÃO COMPLETA (SEM LIMITE)", 'INFO')
    else:
        limite = args.limite
        log(f"IMPORTAÇÃO LIMITADA A {limite} REGISTROS", 'INFO')
    
    db = SessionLocal()
    
    try:
        # Buscar tenant_id
        if not get_tenant_id(db):
            return
        
        # Importar
        importar_clientes(db, limite)
        
        # Resumo
        exibir_resumo()
        log("IMPORTAÇÃO CONCLUÍDA", 'OK')
        
    except Exception as e:
        log(f"ERRO FATAL: {str(e)}", 'ERRO')
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
