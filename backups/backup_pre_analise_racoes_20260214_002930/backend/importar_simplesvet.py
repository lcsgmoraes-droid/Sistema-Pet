"""
🔄 IMPORTADOR SIMPLESVET → Sistema Pet

Script modular para importar dados do sistema SimplesVet.
Importa em fases respeitando dependências.

Uso:
    python importar_simplesvet.py --fase 1 --limite 20
    python importar_simplesvet.py --fase 2 --limite 20
    python importar_simplesvet.py --all --limite 20  # Todas as fases
    python importar_simplesvet.py --all               # Importação completa

Fases:
    1 - Cadastros Base (espécies, raças)
    2 - Clientes e Produtos
    3 - Pets
    4 - Vendas e Itens
"""

import os
import sys
import csv
import argparse
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import re

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from app.models import Cliente, Pet, Especie, Raca
from app.produtos_models import Produto, Marca, Categoria
from app.vendas_models import Venda, VendaItem
from app.caixa_models import Caixa  # Necessário para resolver FK de vendas.caixa_id
from app.db import SessionLocal


# =====================================================================
# CONFIGURAÇÕES
# =====================================================================

# Caminho para os CSVs do SimplesVet  
SIMPLESVET_PATH = Path(r"c:\Users\Lucas\OneDrive\Área de Trabalho\Programa\Sistema Pet\simplesvet\banco")

# Mapeamento de IDs antigos → novos (para preservar relacionamentos)
ID_MAP = {
    'pessoas': {},      # pes_int_codigo → cliente.id
    'animais': {},      # ani_int_codigo → pet.id
    'produtos': {},     # pro_int_codigo → produto.id
    'vendas': {},       # ven_int_codigo → venda.id
    'especies': {},     # esp_int_codigo → especie.id
    'racas': {},        # rac_int_codigo → raca.id
    'marcas': {},       # mar_int_codigo → marca.id
}

# Estatísticas da importação
STATS = {
    'especies': {'total': 0, 'sucesso': 0, 'erro': 0, 'duplicado': 0},
    'racas': {'total': 0, 'sucesso': 0, 'erro': 0, 'duplicado': 0},
    'clientes': {'total': 0, 'sucesso': 0, 'erro': 0, 'duplicado': 0},
    'marcas': {'total': 0, 'sucesso': 0, 'erro': 0, 'duplicado': 0},
    'produtos': {'total': 0, 'sucesso': 0, 'erro': 0, 'duplicado': 0},
    'pets': {'total': 0, 'sucesso': 0, 'erro': 0, 'duplicado': 0},
    'vendas': {'total': 0, 'sucesso': 0, 'erro': 0, 'duplicado': 0},
    'itens_venda': {'total': 0, 'sucesso': 0, 'erro': 0, 'duplicado': 0},
}

# Usuário para importação (será o primeiro admin do sistema)
USER_ID = 1  # CONFIGURAR: ID do admin
TENANT_ID = None  # Será buscado automaticamente do banco

def obter_tenant_id(db: Session) -> str:
    """Busca o tenant_id do primeiro usuário do sistema"""
    global TENANT_ID
    if TENANT_ID:
        return TENANT_ID
    
    try:
        result = db.execute(text("SELECT tenant_id FROM users WHERE id = :user_id LIMIT 1"), 
                          {"user_id": USER_ID})
        row = result.fetchone()
        if row and row[0]:
            TENANT_ID = str(row[0])
            log(f"Tenant ID encontrado: {TENANT_ID}")
            return TENANT_ID
        else:
            log("Nenhum tenant_id encontrado no banco!", 'ERRO')
            sys.exit(1)
    except Exception as e:
        log(f"Erro ao buscar tenant_id: {e}", 'ERRO')
        sys.exit(1)


# =====================================================================
# UTILITÁRIOS
# =====================================================================

def ler_csv(arquivo: str, limite: Optional[int] = None) -> List[Dict]:
    """Lê arquivo CSV e retorna lista de dicionários"""
    caminho = SIMPLESVET_PATH / arquivo
    
    if not caminho.exists():
        print(f"[ERRO] Arquivo não encontrado: {caminho}")
        return []
    
    registros = []
    with open(caminho, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if limite and i >= limite:
                break
            registros.append(row)
    
    print(f"[INFO] Lidos {len(registros)} registros de {arquivo}")
    return registros


def limpar_cpf(cpf: Optional[str]) -> Optional[str]:
    """Remove formatação do CPF"""
    if not cpf or cpf == 'NULL' or cpf == '':
        return None
    return re.sub(r'[^0-9]', '', cpf)


def limpar_telefone(tel: Optional[str]) -> Optional[str]:
    """Remove formatação do telefone"""
    if not tel or tel == 'NULL' or tel == '':
        return None
    return re.sub(r'[^0-9]', '', tel)


def carregar_contatos() -> Dict[str, Dict[str, Optional[str]]]:
    """Carrega contatos (telefone/celular) do SimplesVet"""
    contatos = {}
    registros = ler_csv('glo_contato.csv', limite=None)

    for row in registros:
        pes_id = row.get('pes_int_codigo')
        if not pes_id:
            continue

        tipo = (row.get('tco_var_nome') or '').strip().lower()
        contato = limpar_telefone(row.get('con_var_contato'))
        if not contato:
            continue

        if pes_id not in contatos:
            contatos[pes_id] = {'telefone': None, 'celular': None}

        if 'cel' in tipo:
            contatos[pes_id]['celular'] = contatos[pes_id]['celular'] or contato
        elif 'tel' in tipo or 'fone' in tipo:
            contatos[pes_id]['telefone'] = contatos[pes_id]['telefone'] or contato

    return contatos


def parse_decimal(valor: Optional[str]) -> float:
    """Converte string decimal para float"""
    if not valor or valor == 'NULL' or valor == '':
        return 0.0
    try:
        return float(valor.replace(',', '.'))
    except:
        return 0.0


def parse_bool(valor: Optional[str], verdadeiro: str = 'Sim') -> bool:
    """Converte string para boolean"""
    if not valor or valor == 'NULL':
        return False
    return valor.strip() == verdadeiro


def parse_date(data: Optional[str]) -> Optional[datetime]:
    """Converte string de data para datetime"""
    if not data or data == 'NULL' or data == '':
        return None
    
    # Formatos comuns
    formatos = [
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d',
        '%d/%m/%Y',
        '%d/%m/%Y %H:%M:%S'
    ]
    
    for fmt in formatos:
        try:
            return datetime.strptime(data.strip(), fmt)
        except:
            continue
    
    return None


def log(msg: str, nivel: str = 'INFO'):
    """Log com timestamp"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    icones = {'INFO': '[INFO]', 'SUCESSO': '[OK]', 'ERRO': '[ERR]', 'AVISO': '[WARN]'}
    icone = icones.get(nivel, '[INFO]')
    try:
        print(f"[{timestamp}] {icone} {msg}")
    except UnicodeEncodeError:
        # Fallback para sistemas sem suporte a Unicode
        print(f"[{timestamp}] {nivel} {msg.encode('ascii', 'ignore').decode()}")


# =====================================================================
# FASE 1: CADASTROS BASE
# =====================================================================

def importar_especies(db: Session, limite: Optional[int] = None):
    """Importa espécies de animais"""
    log("FASE 1.1 - ESPECIES")
    
    registros = ler_csv('vet_especie.csv', limite)
    STATS['especies']['total'] = len(registros)
    
    for row in registros:
        try:
            # Verificar se já existe
            existe = db.query(Especie).filter(Especie.nome == row['esp_var_nome']).first()
            
            if existe:
                ID_MAP['especies'][row['esp_int_codigo']] = existe.id
                STATS['especies']['duplicado'] += 1
                log(f"Espécie já existe: {row['esp_var_nome']}", 'AVISO')
                continue
            
            if not row['esp_var_nome'] or row['esp_var_nome'] == 'NULL':
                STATS['especies']['erro'] += 1
                log(f"Espécie sem nome, pulando...", 'AVISO')
                continue
            
            especie = Especie(
                nome=row['esp_var_nome'],
                ativo=True,
                tenant_id=TENANT_ID,
                created_at=parse_date(row.get('esp_dti_inclusao'))
            )
            
            db.add(especie)
            db.flush()
            
            ID_MAP['especies'][row['esp_int_codigo']] = especie.id
            STATS['especies']['sucesso'] += 1
            log(f"Espécie: {especie.nome}", 'SUCESSO')
            
        except Exception as e:
            STATS['especies']['erro'] += 1
            log(f"Erro espécie {row.get('esp_var_nome', 'DESCONHECIDO')}: {str(e)}", 'ERRO')
            continue  # Continua sem fazer rollback
    
    db.commit()
    log(f"✓ Espécies: {STATS['especies']['sucesso']}/{STATS['especies']['total']}")


def importar_racas(db: Session, limite: Optional[int] = None):
    """Importa raças de animais"""
    log("═══ FASE 1.2 - RAÇAS ═══")
    
    registros = ler_csv('vet_raca.csv', limite)
    STATS['racas']['total'] = len(registros)
    
    for row in registros:
        try:
            especie_id = ID_MAP['especies'].get(row['esp_int_codigo'])
            
            if not especie_id:
                log(f"Espécie não encontrada: {row['esp_var_nome']}", 'AVISO')
                STATS['racas']['erro'] += 1
                continue
            
            existe = db.query(Raca).filter(
                Raca.nome == row['rac_var_nome'],
                Raca.especie_id == especie_id
            ).first()
            
            if existe:
                ID_MAP['racas'][row['rac_int_codigo']] = existe.id
                continue
            
            raca = Raca(
                nome=row['rac_var_nome'],
                especie_id=especie_id,
                ativo=True,
                tenant_id=TENANT_ID,
                created_at=parse_date(row.get('rac_dti_inclusao'))
            )
            
            db.add(raca)
            db.flush()
            
            ID_MAP['racas'][row['rac_int_codigo']] = raca.id
            STATS['racas']['sucesso'] += 1
            
        except Exception as e:
            STATS['racas']['erro'] += 1
            log(f"Erro raça {row.get('rac_var_nome', 'DESCONHECIDO')}: {str(e)}", 'ERRO')
            continue  # Continua sem fazer rollback
    
    db.commit()
    log(f"✓ Raças: {STATS['racas']['sucesso']}/{STATS['racas']['total']}")


# =====================================================================
# FASE 2: CLIENTES E PRODUTOS
# =====================================================================

def importar_clientes(db: Session, limite: Optional[int] = None):
    """Importa clientes"""
    log("═══ FASE 2.1 - CLIENTES ═══")

    contatos = carregar_contatos()
    registros = ler_csv('glo_pessoa.csv', limite)
    STATS['clientes']['total'] = len(registros)
    
    for row in registros:
        try:
            cpf = limpar_cpf(row.get('pes_var_cpf'))
            codigo = row.get('pes_var_chave')
            contato = contatos.get(row.get('pes_int_codigo'), {})

            # Verificar duplicata por codigo (prioridade)
            if codigo:
                existe = db.query(Cliente).filter(Cliente.codigo == codigo).first()
                if existe:
                    ID_MAP['pessoas'][row['pes_int_codigo']] = existe.id
                    STATS['clientes']['duplicado'] += 1
                    atualizado = False
                    if contato.get('telefone') and not existe.telefone:
                        existe.telefone = contato.get('telefone')
                        atualizado = True
                    if contato.get('celular') and not existe.celular:
                        existe.celular = contato.get('celular')
                        atualizado = True
                    if atualizado:
                        db.add(existe)
                        db.flush()
                        log(f"Cliente atualizado: {row['pes_var_nome']} (#{codigo})", 'AVISO')
                    else:
                        log(f"Cliente já existe: {row['pes_var_nome']} (#{codigo})", 'AVISO')
                    continue

            # Verificar duplicata por CPF
            if cpf:
                existe = db.query(Cliente).filter(Cliente.cpf == cpf).first()
                if existe:
                    ID_MAP['pessoas'][row['pes_int_codigo']] = existe.id
                    STATS['clientes']['duplicado'] += 1
                    atualizado = False
                    if contato.get('telefone') and not existe.telefone:
                        existe.telefone = contato.get('telefone')
                        atualizado = True
                    if contato.get('celular') and not existe.celular:
                        existe.celular = contato.get('celular')
                        atualizado = True
                    if atualizado:
                        db.add(existe)
                        db.flush()
                        log(f"Cliente atualizado (CPF): {row['pes_var_nome']}", 'AVISO')
                    else:
                        log(f"Cliente já existe (CPF): {row['pes_var_nome']}", 'AVISO')
                    continue
            
            cliente = Cliente(
                user_id=USER_ID,
                tenant_id=TENANT_ID,
                codigo=codigo,
                nome=row['pes_var_nome'],
                cpf=cpf,
                telefone=contato.get('telefone'),
                celular=contato.get('celular'),
                email=row.get('pes_var_email') if row.get('pes_var_email') and row['pes_var_email'] != 'NULL' else None,
                cep=row.get('end_var_cep') if row.get('end_var_cep') and row['end_var_cep'] != 'NULL' else None,
                endereco=row.get('end_var_endereco') if row.get('end_var_endereco') and row['end_var_endereco'] != 'NULL' else None,
                numero=row.get('end_var_numero') if row.get('end_var_numero') and row['end_var_numero'] != 'NULL' else None,
                complemento=row.get('end_var_complemento') if row.get('end_var_complemento') and row['end_var_complemento'] != 'NULL' else None,
                bairro=row.get('end_var_bairro') if row.get('end_var_bairro') and row['end_var_bairro'] != 'NULL' else None,
                cidade=row.get('end_var_municipio') if row.get('end_var_municipio') and row['end_var_municipio'] != 'NULL' else None,
                estado=row.get('end_var_uf') if row.get('end_var_uf') and row['end_var_uf'] != 'NULL' else None,
                observacoes=row.get('pes_txt_observacao') if row.get('pes_txt_observacao') and row['pes_txt_observacao'] != 'NULL' else None,
                ativo=True,
                created_at=parse_date(row.get('pes_dti_inclusao'))
            )
            
            db.add(cliente)
            db.flush()
            
            ID_MAP['pessoas'][row['pes_int_codigo']] = cliente.id
            STATS['clientes']['sucesso'] += 1
            log(f"Cliente: {cliente.nome} (#{cliente.codigo})", 'SUCESSO')
            
        except Exception as e:
            STATS['clientes']['erro'] += 1
            log(f"Erro cliente {row.get('pes_var_nome', 'DESCONHECIDO')}: {str(e)}", 'ERRO')
            continue
    
    db.commit()
    log(f"✓ Clientes: {STATS['clientes']['sucesso']}/{STATS['clientes']['total']}")


def importar_produtos(db: Session, limite: Optional[int] = None):
    """Importa produtos"""
    log("═══ FASE 2.2 - PRODUTOS ═══")

    importar_marcas(db)
    registros = ler_csv('eco_produto.csv', limite)
    STATS['produtos']['total'] = len(registros)
    
    for row in registros:
        try:
            codigo = row['pro_var_chave']

            marca_id = None
            if row.get('mar_int_codigo'):
                marca_id = ID_MAP['marcas'].get(row['mar_int_codigo'])
            if not marca_id and row.get('mar_var_nome') and row['mar_var_nome'] != 'NULL':
                marca = db.query(Marca).filter(Marca.nome == row['mar_var_nome']).first()
                if marca:
                    marca_id = marca.id
            
            # Verificar duplicata
            existe = db.query(Produto).filter(Produto.codigo == codigo).first()
            if existe:
                ID_MAP['produtos'][row['pro_int_codigo']] = existe.id
                STATS['produtos']['duplicado'] += 1
                if marca_id and not existe.marca_id:
                    existe.marca_id = marca_id
                    db.add(existe)
                    db.flush()
                    log(f"Produto atualizado (marca): {row['pro_var_nome']} (#{codigo})", 'AVISO')
                else:
                    log(f"Produto já existe: {row['pro_var_nome']} (#{codigo})", 'AVISO')
                continue
            
            tipo = 'produto' if row.get('pro_cha_tipo') == 'P' else 'servico'
            situacao = row.get('pro_var_status', 'Ativo') == 'Ativo'
            
            produto = Produto(
                user_id=USER_ID,
                tenant_id=TENANT_ID,
                codigo=codigo,
                nome=row['pro_var_nome'],
                tipo=tipo,
                situacao=situacao,
                marca_id=marca_id,
                preco_custo=parse_decimal(row.get('pro_dec_custo', '0')),
                preco_venda=parse_decimal(row.get('pro_dec_preco', '0')),
                codigo_barras=row.get('pro_var_codigobarra') if row.get('pro_var_codigobarra') and row['pro_var_codigobarra'] != 'NULL' else None,
                estoque_atual=parse_decimal(row.get('pro_dec_estoque', '0')),
                estoque_minimo=parse_decimal(row.get('pro_dec_minimo', '0')),
                estoque_maximo=parse_decimal(row.get('pro_dec_maximo', '0')),
                created_at=parse_date(row.get('pro_dti_inclusao'))
            )
            
            db.add(produto)
            db.flush()
            
            ID_MAP['produtos'][row['pro_int_codigo']] = produto.id
            STATS['produtos']['sucesso'] += 1
            log(f"Produto: {produto.nome} (SKU: {produto.codigo})", 'SUCESSO')
            
        except Exception as e:
            STATS['produtos']['erro'] += 1
            log(f"Erro produto {row.get('pro_var_nome', 'DESCONHECIDO')}: {str(e)}", 'ERRO')
            continue
    
    db.commit()
    log(f"✓ Produtos: {STATS['produtos']['sucesso']}/{STATS['produtos']['total']}")


def importar_marcas(db: Session):
    """Importa marcas de produtos"""
    if STATS['marcas']['total'] > 0:
        return

    log("═══ FASE 2.0 - MARCAS ═══")
    registros = ler_csv('eco_marca.csv', limite=None)
    STATS['marcas']['total'] = len(registros)

    for row in registros:
        try:
            nome = row.get('mar_var_nome')
            if not nome or nome == 'NULL':
                STATS['marcas']['erro'] += 1
                continue

            existe = db.query(Marca).filter(Marca.nome == nome).first()
            if existe:
                ID_MAP['marcas'][row['mar_int_codigo']] = existe.id
                continue

            marca = Marca(
                user_id=USER_ID,
                tenant_id=TENANT_ID,
                nome=nome,
                ativo=True,
                created_at=datetime.now()
            )

            db.add(marca)
            db.flush()

            ID_MAP['marcas'][row['mar_int_codigo']] = marca.id
            STATS['marcas']['sucesso'] += 1

        except Exception as e:
            STATS['marcas']['erro'] += 1
            log(f"Erro marca {row.get('mar_var_nome', 'DESCONHECIDO')}: {str(e)}", 'ERRO')
            continue

    db.commit()
    log(f"✓ Marcas: {STATS['marcas']['sucesso']}/{STATS['marcas']['total']}")


# =====================================================================
# FASE 3: PETS
# =====================================================================

def importar_pets(db: Session, limite: Optional[int] = None):
    """Importa animais/pets"""
    log("═══ FASE 3 - PETS ═══")
    
    registros = ler_csv('vet_animal.csv', limite)
    STATS['pets']['total'] = len(registros)
    
    for row in registros:
        try:
            cliente_id = ID_MAP['pessoas'].get(row['pes_int_codigo'])
            
            if not cliente_id:
                log(f"Cliente não encontrado para pet {row['ani_var_nome']}", 'AVISO')
                STATS['pets']['erro'] += 1
                continue
            
            codigo = row['ani_var_chave']
            existe = db.query(Pet).filter(Pet.codigo == codigo).first()
            
            if existe:
                ID_MAP['animais'][row['ani_int_codigo']] = existe.id
                STATS['pets']['duplicado'] += 1
                log(f"Pet já existe: {row['ani_var_nome']} (#{codigo})", 'AVISO')
                continue
            
            sexo_map = {'Macho': 'macho', 'Fêmea': 'fêmea', 'Fêmea': 'fêmea'}
            sexo = sexo_map.get(row.get('ani_var_sexo', ''), None)
            
            especie_nome = row.get('esp_var_nome') if row.get('esp_var_nome') and row['esp_var_nome'] != 'NULL' else None
            if not especie_nome:
                log(f"Pet {row['ani_var_nome']} sem espécie, pulando...", 'AVISO')
                STATS['pets']['erro'] += 1
                continue
            
            pet = Pet(
                cliente_id=cliente_id,
                user_id=USER_ID,
                tenant_id=TENANT_ID,
                codigo=codigo,
                nome=row['ani_var_nome'],
                especie=especie_nome,
                raca=row.get('rac_var_nome') if row.get('rac_var_nome') and row['rac_var_nome'] != 'NULL' else None,
                sexo=sexo,
                castrado=parse_bool(row.get('ani_var_esterilizacao')),
                data_nascimento=parse_date(row.get('ani_dat_nascimento')),
                peso=parse_decimal(row.get('ani_dec_peso')),
                cor=row.get('pel_var_nome') if row.get('pel_var_nome') and row['pel_var_nome'] != 'NULL' else None,
                microchip=row.get('ani_var_chip') if row.get('ani_var_chip') and row['ani_var_chip'] != 'NULL' else None,
                ativo=row.get('ani_var_morto', 'Não') != 'Sim',
                created_at=parse_date(row.get('ani_dti_inclusao'))
            )
            
            db.add(pet)
            db.flush()
            
            ID_MAP['animais'][row['ani_int_codigo']] = pet.id
            STATS['pets']['sucesso'] += 1
            log(f"Pet: {pet.nome} - {pet.especie}", 'SUCESSO')
            
        except Exception as e:
            STATS['pets']['erro'] += 1
            log(f"Erro pet {row.get('ani_var_nome', 'DESCONHECIDO')}: {str(e)}", 'ERRO')
            db.rollback()  # Rollback necessário após erro para continuar
            continue
    
    db.commit()
    log(f"✓ Pets: {STATS['pets']['sucesso']}/{STATS['pets']['total']}")


# =====================================================================
# FASE 4: VENDAS
# =====================================================================

def importar_vendas(db: Session, limite: Optional[int] = None, data_hoje: bool = False):
    """Importa vendas e itens"""
    log("═══ FASE 4 - VENDAS ═══")
    
    registros = ler_csv('eco_venda.csv', limite)
    STATS['vendas']['total'] = len(registros)
    
    vendas_ids_antigos = []
    
    for row in registros:
        try:
            cliente_id = None
            if row.get('pes_int_codigo') and row['pes_int_codigo'] != 'NULL':
                cliente_id = ID_MAP['pessoas'].get(row['pes_int_codigo'])
            
            subtotal = parse_decimal(row['ven_dec_bruto'])
            desconto_valor = parse_decimal(row.get('ven_dec_descontovalor', '0'))
            desconto_percentual = parse_decimal(row.get('ven_dec_descontopercentual', '0'))
            total = parse_decimal(row['ven_dec_liquido'])
            
            status_map = {'Baixado': 'finalizada', 'Aberto': 'aberta', 'Cancelado': 'cancelada'}
            status = status_map.get(row.get('ven_var_status', 'Aberto'), 'aberta')
            
            data_venda = parse_date(row['ven_dat_data']) or datetime.now()
            data_finalizacao = parse_date(row.get('ven_dat_pagamento')) if status == 'finalizada' else None

            if data_hoje:
                data_venda = datetime.now()
                data_finalizacao = datetime.now() if status == 'finalizada' else None
            
            numero_venda = f"IMP-{data_venda.strftime('%Y%m%d')}-{row['ven_var_chave']}"
            
            # Verificar duplicata
            existe = db.query(Venda).filter(Venda.numero_venda == numero_venda).first()
            if existe:
                ID_MAP['vendas'][row['ven_int_codigo']] = existe.id
                STATS['vendas']['duplicado'] += 1
                vendas_ids_antigos.append(row['ven_int_codigo'])
                log(f"Venda já existe: {numero_venda}", 'AVISO')
                continue
            
            venda = Venda(
                user_id=USER_ID,
                tenant_id=TENANT_ID,
                numero_venda=numero_venda,
                cliente_id=cliente_id,
                vendedor_id=USER_ID,
                subtotal=subtotal,
                desconto_valor=desconto_valor,
                desconto_percentual=desconto_percentual,
                total=total,
                observacoes=row.get('ven_txt_observacao') if row.get('ven_txt_observacao') and row['ven_txt_observacao'] != 'NULL' else None,
                status=status,
                data_venda=data_venda,
                data_finalizacao=data_finalizacao,
                created_at=parse_date(row.get('ven_dti_inclusao')) or datetime.now()
            )
            
            db.add(venda)
            db.flush()
            
            ID_MAP['vendas'][row['ven_int_codigo']] = venda.id
            vendas_ids_antigos.append(row['ven_int_codigo'])
            STATS['vendas']['sucesso'] += 1
            log(f"Venda: {venda.numero_venda} - R$ {venda.total:.2f}", 'SUCESSO')
            
        except Exception as e:
            STATS['vendas']['erro'] += 1
            log(f"Erro venda {row.get('ven_var_chave', 'DESCONHECIDO')}: {str(e)}", 'ERRO')
            db.rollback()  # Rollback necessário após erro
            continue
    
    db.commit()
    log(f"✓ Vendas: {STATS['vendas']['sucesso']}/{STATS['vendas']['total']}")
    
    # Importar itens
    importar_itens_venda(db, vendas_ids_antigos)


def importar_itens_venda(db: Session, vendas_ids: List[str]):
    """Importa itens das vendas"""
    log("═══ FASE 4.1 - ITENS DAS VENDAS ═══")
    
    registros = ler_csv('eco_venda_produto.csv', limite=None)
    itens_filtrados = [r for r in registros if r['ven_int_codigo'] in vendas_ids]
    
    STATS['itens_venda']['total'] = len(itens_filtrados)
    
    for row in itens_filtrados:
        try:
            venda_id = ID_MAP['vendas'].get(row['ven_int_codigo'])
            produto_id = ID_MAP['produtos'].get(row['pro_int_codigo'])
            
            if not venda_id or not produto_id:
                STATS['itens_venda']['erro'] += 1
                continue
            
            quantidade = parse_decimal(row['vpr_dec_quantidade'])
            preco_unitario = parse_decimal(row['vpr_dec_preco'])
            preco_total = quantidade * preco_unitario
            
            item = VendaItem(
                user_id=USER_ID,
                tenant_id=TENANT_ID,
                venda_id=venda_id,
                produto_id=produto_id,
                quantidade=quantidade,
                preco_unitario=preco_unitario,
                preco_total=preco_total,
                desconto=0.0,
                created_at=parse_date(row.get('vpr_dti_inclusao')) or datetime.now()
            )
            
            db.add(item)
            STATS['itens_venda']['sucesso'] += 1
            
        except Exception as e:
            STATS['itens_venda']['erro'] += 1
            log(f"Erro item: {str(e)}", 'ERRO')
            continue
    
    db.commit()
    log(f"✓ Itens: {STATS['itens_venda']['sucesso']}/{STATS['itens_venda']['total']}")


# =====================================================================
# MAIN
# =====================================================================

def exibir_resumo():
    """Exibe resumo da importação"""
    print("\n" + "="*80)
    print("RESUMO DA IMPORTACAO".center(80))
    print("="*80)
    print(f"{'ENTIDADE':<15} | {'TOTAL':>6} | {'NOVOS':>6} | {'DUPLIC':>6} | {'ERROS':>6} | {'TAXA':>6}")
    print("-"*80)
    
    for entidade, stats in STATS.items():
        if stats['total'] > 0:
            taxa = (stats['sucesso'] / stats['total']) * 100 if stats['total'] > 0 else 0
            print(f"{entidade.upper():<15} | {stats['total']:>6} | {stats['sucesso']:>6} | "
                  f"{stats['duplicado']:>6} | {stats['erro']:>6} | {taxa:>5.1f}%")
    
    print("="*80)
    
    # Resumo consolidado
    total_geral = sum(s['total'] for s in STATS.values())
    novos_geral = sum(s['sucesso'] for s in STATS.values())
    duplic_geral = sum(s['duplicado'] for s in STATS.values())
    erros_geral = sum(s['erro'] for s in STATS.values())
    
    print(f"\n{'TOTAL GERAL':<15} | {total_geral:>6} | {novos_geral:>6} | "
          f"{duplic_geral:>6} | {erros_geral:>6}")
    print("="*80 + "\n")


def main():
    """Executar importação"""
    parser = argparse.ArgumentParser(description='Importar dados do SimplesVet')
    parser.add_argument('--fase', type=int, help='Fase específica (1-4)')
    parser.add_argument('--all', action='store_true', help='Todas as fases')
    parser.add_argument('--limite', type=int, default=20, help='Limite de registros')
    parser.add_argument('--data-hoje', action='store_true', help='Força data das vendas para hoje')
    
    args = parser.parse_args()
    
    db = SessionLocal()
    
    try:
        log("INICIANDO IMPORTACAO SIMPLESVET")
        
        # Buscar tenant_id do banco
        obter_tenant_id(db)
        
        log(f"Limite de registros: {args.limite}")
        
        if args.all or args.fase == 1:
            importar_especies(db)
            importar_racas(db, args.limite)
        
        if args.all or args.fase == 2:
            importar_clientes(db, args.limite)
            importar_produtos(db, args.limite)
        
        if args.all or args.fase == 3:
            importar_pets(db, args.limite)
        
        if args.all or args.fase == 4:
            importar_vendas(db, args.limite, data_hoje=args.data_hoje)
        
        exibir_resumo()
        log("✅ IMPORTAÇÃO CONCLUÍDA")
        
    except Exception as e:
        log(f"ERRO FATAL: {str(e)}", 'ERRO')
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
