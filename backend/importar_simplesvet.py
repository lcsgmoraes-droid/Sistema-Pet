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

# ruff: noqa: E402

import sys
import argparse
from datetime import datetime
from typing import List, Optional
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from sqlalchemy import text
from sqlalchemy.orm import Session
from app.models import Cliente, Pet, Especie, Raca
from app.produtos_models import Produto, Marca
from app.vendas_models import Venda, VendaItem
from app.db import SessionLocal
from importar_simplesvet_state import ID_MAP, NAO_IMPORTADOS, STATS, TENANT_ID, USER_ID
from importar_simplesvet_summary import exibir_resumo as _exibir_resumo
from importar_simplesvet_utils import (
    carregar_contatos,
    ler_csv,
    limpar_cpf,
    log,
    parse_bool,
    parse_date,
    parse_decimal,
)


def obter_tenant_id(db: Session) -> str:
    """Busca o tenant_id do primeiro usuário do sistema"""
    global TENANT_ID
    if TENANT_ID:
        return TENANT_ID

    try:
        result = db.execute(
            text("SELECT tenant_id FROM users WHERE id = :user_id LIMIT 1"),
            {"user_id": USER_ID},
        )
        row = result.fetchone()
        if row and row[0]:
            TENANT_ID = str(row[0])
            log(f"Tenant ID encontrado: {TENANT_ID}")
            return TENANT_ID
        else:
            log("Nenhum tenant_id encontrado no banco!", "ERRO")
            sys.exit(1)
    except Exception as e:
        log(f"Erro ao buscar tenant_id: {e}", "ERRO")
        sys.exit(1)


# =====================================================================
# FASE 1: CADASTROS BASE
# =====================================================================


def importar_especies(db: Session, limite: Optional[int] = None):
    """Importa espécies de animais"""
    log("FASE 1.1 - ESPECIES")

    registros = ler_csv("vet_especie.csv", limite)
    STATS["especies"]["total"] = len(registros)

    for row in registros:
        try:
            # Verificar se já existe
            existe = (
                db.query(Especie).filter(Especie.nome == row["esp_var_nome"]).first()
            )

            if existe:
                ID_MAP["especies"][row["esp_int_codigo"]] = existe.id
                STATS["especies"]["duplicado"] += 1
                log(f"Espécie já existe: {row['esp_var_nome']}", "AVISO")
                continue

            if not row["esp_var_nome"] or row["esp_var_nome"] == "NULL":
                STATS["especies"]["erro"] += 1
                log("Espécie sem nome, pulando...", "AVISO")
                continue

            especie = Especie(
                nome=row["esp_var_nome"],
                ativo=True,
                tenant_id=TENANT_ID,
                created_at=parse_date(row.get("esp_dti_inclusao")),
            )

            db.add(especie)
            db.flush()

            ID_MAP["especies"][row["esp_int_codigo"]] = especie.id
            STATS["especies"]["sucesso"] += 1
            log(f"Espécie: {especie.nome}", "SUCESSO")

        except Exception as e:
            STATS["especies"]["erro"] += 1
            log(
                f"Erro espécie {row.get('esp_var_nome', 'DESCONHECIDO')}: {str(e)}",
                "ERRO",
            )
            continue  # Continua sem fazer rollback

    db.commit()
    log(f"✓ Espécies: {STATS['especies']['sucesso']}/{STATS['especies']['total']}")


def importar_racas(db: Session, limite: Optional[int] = None):
    """Importa raças de animais"""
    log("═══ FASE 1.2 - RAÇAS ═══")

    registros = ler_csv("vet_raca.csv", limite)
    STATS["racas"]["total"] = len(registros)

    for row in registros:
        try:
            especie_id = ID_MAP["especies"].get(row["esp_int_codigo"])

            if not especie_id:
                log(f"Espécie não encontrada: {row['esp_var_nome']}", "AVISO")
                STATS["racas"]["erro"] += 1
                continue

            existe = (
                db.query(Raca)
                .filter(Raca.nome == row["rac_var_nome"], Raca.especie_id == especie_id)
                .first()
            )

            if existe:
                ID_MAP["racas"][row["rac_int_codigo"]] = existe.id
                continue

            raca = Raca(
                nome=row["rac_var_nome"],
                especie_id=especie_id,
                ativo=True,
                tenant_id=TENANT_ID,
                created_at=parse_date(row.get("rac_dti_inclusao")),
            )

            db.add(raca)
            db.flush()

            ID_MAP["racas"][row["rac_int_codigo"]] = raca.id
            STATS["racas"]["sucesso"] += 1

        except Exception as e:
            STATS["racas"]["erro"] += 1
            log(
                f"Erro raça {row.get('rac_var_nome', 'DESCONHECIDO')}: {str(e)}", "ERRO"
            )
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
    registros = ler_csv("glo_pessoa.csv", limite)
    STATS["clientes"]["total"] = len(registros)

    for row in registros:
        try:
            cpf = limpar_cpf(row.get("pes_var_cpf"))
            codigo = row.get("pes_var_chave")
            contato = contatos.get(row.get("pes_int_codigo"), {})

            # Verificar duplicata por codigo (prioridade)
            if codigo:
                existe = db.query(Cliente).filter(Cliente.codigo == codigo).first()
                if existe:
                    ID_MAP["pessoas"][row["pes_int_codigo"]] = existe.id
                    STATS["clientes"]["duplicado"] += 1
                    atualizado = False
                    if contato.get("telefone") and not existe.telefone:
                        existe.telefone = contato.get("telefone")
                        atualizado = True
                    if contato.get("celular") and not existe.celular:
                        existe.celular = contato.get("celular")
                        atualizado = True
                    if atualizado:
                        db.add(existe)
                        db.flush()
                        log(
                            f"Cliente atualizado: {row['pes_var_nome']} (#{codigo})",
                            "AVISO",
                        )
                    else:
                        log(
                            f"Cliente já existe: {row['pes_var_nome']} (#{codigo})",
                            "AVISO",
                        )
                    continue

            # Verificar duplicata por CPF
            if cpf:
                existe = db.query(Cliente).filter(Cliente.cpf == cpf).first()
                if existe:
                    ID_MAP["pessoas"][row["pes_int_codigo"]] = existe.id
                    STATS["clientes"]["duplicado"] += 1
                    atualizado = False
                    if contato.get("telefone") and not existe.telefone:
                        existe.telefone = contato.get("telefone")
                        atualizado = True
                    if contato.get("celular") and not existe.celular:
                        existe.celular = contato.get("celular")
                        atualizado = True
                    if atualizado:
                        db.add(existe)
                        db.flush()
                        log(f"Cliente atualizado (CPF): {row['pes_var_nome']}", "AVISO")
                    else:
                        log(f"Cliente já existe (CPF): {row['pes_var_nome']}", "AVISO")
                    continue

            # ✅ VALIDAÇÃO: Pular clientes sem nome
            nome = (
                row.get("pes_var_nome", "").strip() if row.get("pes_var_nome") else ""
            )
            if not nome:
                STATS["clientes"]["erro"] += 1
                log(f"Cliente sem nome pulado (código: {codigo})", "AVISO")
                continue

            cliente = Cliente(
                user_id=USER_ID,
                tenant_id=TENANT_ID,
                codigo=codigo,
                nome=nome,
                cpf=cpf,
                telefone=contato.get("telefone"),
                celular=contato.get("celular"),
                email=row.get("pes_var_email")
                if row.get("pes_var_email") and row["pes_var_email"] != "NULL"
                else None,
                cep=row.get("end_var_cep")
                if row.get("end_var_cep") and row["end_var_cep"] != "NULL"
                else None,
                endereco=row.get("end_var_endereco")
                if row.get("end_var_endereco") and row["end_var_endereco"] != "NULL"
                else None,
                numero=row.get("end_var_numero")
                if row.get("end_var_numero") and row["end_var_numero"] != "NULL"
                else None,
                complemento=row.get("end_var_complemento")
                if row.get("end_var_complemento")
                and row["end_var_complemento"] != "NULL"
                else None,
                bairro=row.get("end_var_bairro")
                if row.get("end_var_bairro") and row["end_var_bairro"] != "NULL"
                else None,
                cidade=row.get("end_var_municipio")
                if row.get("end_var_municipio") and row["end_var_municipio"] != "NULL"
                else None,
                estado=row.get("end_var_uf")
                if row.get("end_var_uf") and row["end_var_uf"] != "NULL"
                else None,
                observacoes=row.get("pes_txt_observacao")
                if row.get("pes_txt_observacao") and row["pes_txt_observacao"] != "NULL"
                else None,
                ativo=True,
                created_at=parse_date(row.get("pes_dti_inclusao")),
            )

            db.add(cliente)
            db.flush()

            ID_MAP["pessoas"][row["pes_int_codigo"]] = cliente.id
            STATS["clientes"]["sucesso"] += 1
            log(f"Cliente: {cliente.nome} (#{cliente.codigo})", "SUCESSO")

        except Exception as e:
            STATS["clientes"]["erro"] += 1
            log(
                f"Erro cliente {row.get('pes_var_nome', 'DESCONHECIDO')}: {str(e)}",
                "ERRO",
            )
            continue

    db.commit()
    log(f"✓ Clientes: {STATS['clientes']['sucesso']}/{STATS['clientes']['total']}")


def importar_produtos(db: Session, limite: Optional[int] = None):
    """Importa produtos"""
    log("═══ FASE 2.2 - PRODUTOS ═══")

    importar_marcas(db)
    registros = ler_csv("eco_produto.csv", limite)
    STATS["produtos"]["total"] = len(registros)

    linha = 0  # Contador de linha para relatório
    for row in registros:
        linha += 1
        try:
            # VALIDAÇÃO RIGOROSA DO SKU
            codigo_bruto = row.get("pro_var_chave", "").strip()
            nome = row.get("pro_var_nome", "DESCONHECIDO")

            if not codigo_bruto:
                STATS["produtos"]["sem_sku"] += 1
                STATS["produtos"]["erro"] += 1
                erro_msg = "SKU_VAZIO: Produto sem código/SKU"
                log(f"[{linha}/{len(registros)}] {erro_msg}: {nome}", "AVISO")
                NAO_IMPORTADOS["produtos"].append(
                    {
                        "linha": linha,
                        "sku": "VAZIO",
                        "nome": nome,
                        "motivo": "SEM_SKU",
                        "erro": erro_msg,
                    }
                )
                continue

            codigo = codigo_bruto

            marca_id = None
            if row.get("mar_int_codigo"):
                marca_id = ID_MAP["marcas"].get(row["mar_int_codigo"])
            if (
                not marca_id
                and row.get("mar_var_nome")
                and row["mar_var_nome"] != "NULL"
            ):
                marca = (
                    db.query(Marca).filter(Marca.nome == row["mar_var_nome"]).first()
                )
                if marca:
                    marca_id = marca.id

            # Verificar duplicata
            existe = db.query(Produto).filter(Produto.codigo == codigo).first()
            if existe:
                ID_MAP["produtos"][row["pro_int_codigo"]] = existe.id
                STATS["produtos"]["duplicado"] += 1
                NAO_IMPORTADOS["produtos"].append(
                    {
                        "linha": linha,
                        "sku": codigo,
                        "nome": nome,
                        "motivo": "DUPLICADO",
                        "erro": f"SKU {codigo} já existe (ID: {existe.id})",
                    }
                )
                if marca_id and not existe.marca_id:
                    existe.marca_id = marca_id
                    db.add(existe)
                    db.flush()
                    log(
                        f"Produto atualizado (marca): {row['pro_var_nome']} (#{codigo})",
                        "AVISO",
                    )
                else:
                    log(
                        f"Produto já existe: {row['pro_var_nome']} (#{codigo})", "AVISO"
                    )
                continue

            tipo = "produto" if row.get("pro_cha_tipo") == "P" else "servico"
            situacao = row.get("pro_var_status", "Ativo") == "Ativo"

            produto = Produto(
                user_id=USER_ID,
                tenant_id=TENANT_ID,
                codigo=codigo,
                nome=row["pro_var_nome"],
                tipo=tipo,
                situacao=situacao,
                marca_id=marca_id,
                preco_custo=parse_decimal(row.get("pro_dec_custo", "0")),
                preco_venda=parse_decimal(row.get("pro_dec_preco", "0")),
                codigo_barras=row.get("pro_var_codigobarra")
                if row.get("pro_var_codigobarra")
                and row["pro_var_codigobarra"] != "NULL"
                else None,
                estoque_atual=parse_decimal(row.get("pro_dec_estoque", "0")),
                estoque_minimo=parse_decimal(row.get("pro_dec_minimo", "0")),
                estoque_maximo=parse_decimal(row.get("pro_dec_maximo", "0")),
                created_at=parse_date(row.get("pro_dti_inclusao")),
            )

            db.add(produto)
            db.flush()

            ID_MAP["produtos"][row["pro_int_codigo"]] = produto.id
            STATS["produtos"]["sucesso"] += 1
            log(f"Produto: {produto.nome} (SKU: {produto.codigo})", "SUCESSO")

        except KeyError as e:
            STATS["produtos"]["erro"] += 1
            erro_msg = f"Campo obrigatório faltando: {str(e)}"
            log(
                f"Erro produto {row.get('pro_var_nome', 'DESCONHECIDO')}: {erro_msg}",
                "ERRO",
            )
            NAO_IMPORTADOS["produtos"].append(
                {
                    "linha": linha,
                    "sku": row.get("pro_var_chave", "N/A"),
                    "nome": row.get("pro_var_nome", "DESCONHECIDO"),
                    "motivo": "ERRO",
                    "erro": erro_msg,
                }
            )
            continue
        except Exception as e:
            STATS["produtos"]["erro"] += 1
            erro_msg = str(e)
            log(
                f"Erro produto {row.get('pro_var_nome', 'DESCONHECIDO')}: {erro_msg}",
                "ERRO",
            )
            NAO_IMPORTADOS["produtos"].append(
                {
                    "linha": linha,
                    "sku": row.get("pro_var_chave", "N/A"),
                    "nome": row.get("pro_var_nome", "DESCONHECIDO"),
                    "motivo": "ERRO",
                    "erro": erro_msg,
                }
            )
            continue

    db.commit()
    log(f"✓ Produtos: {STATS['produtos']['sucesso']}/{STATS['produtos']['total']}")

    # Gerar relatório de produtos NÃO importados
    if NAO_IMPORTADOS["produtos"]:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_file = (
            Path(__file__).parent
            / f"logs_importacao/produtos_nao_importados_{timestamp}.csv"
        )
        csv_file.parent.mkdir(exist_ok=True)

        with open(csv_file, "w", encoding="utf-8", newline="") as f:
            import csv as csv_module

            writer = csv_module.DictWriter(
                f, fieldnames=["linha", "sku", "nome", "motivo", "erro"]
            )
            writer.writeheader()
            writer.writerows(NAO_IMPORTADOS["produtos"])

        log(f"📄 Relatório de não importados: {csv_file}", "AVISO")


def importar_marcas(db: Session):
    """Importa marcas de produtos"""
    if STATS["marcas"]["total"] > 0:
        return

    log("═══ FASE 2.0 - MARCAS ═══")
    registros = ler_csv("eco_marca.csv", limite=None)
    STATS["marcas"]["total"] = len(registros)

    for row in registros:
        try:
            nome = row.get("mar_var_nome")
            if not nome or nome == "NULL":
                STATS["marcas"]["erro"] += 1
                continue

            existe = db.query(Marca).filter(Marca.nome == nome).first()
            if existe:
                ID_MAP["marcas"][row["mar_int_codigo"]] = existe.id
                continue

            marca = Marca(
                user_id=USER_ID,
                tenant_id=TENANT_ID,
                nome=nome,
                ativo=True,
                created_at=datetime.now(),
            )

            db.add(marca)
            db.flush()

            ID_MAP["marcas"][row["mar_int_codigo"]] = marca.id
            STATS["marcas"]["sucesso"] += 1

        except Exception as e:
            STATS["marcas"]["erro"] += 1
            log(
                f"Erro marca {row.get('mar_var_nome', 'DESCONHECIDO')}: {str(e)}",
                "ERRO",
            )
            continue

    db.commit()
    log(f"✓ Marcas: {STATS['marcas']['sucesso']}/{STATS['marcas']['total']}")


# =====================================================================
# FASE 3: PETS
# =====================================================================


def importar_pets(db: Session, limite: Optional[int] = None):
    """Importa animais/pets"""
    log("═══ FASE 3 - PETS ═══")

    registros = ler_csv("vet_animal.csv", limite)
    STATS["pets"]["total"] = len(registros)

    for row in registros:
        try:
            cliente_id = ID_MAP["pessoas"].get(row["pes_int_codigo"])

            if not cliente_id:
                log(f"Cliente não encontrado para pet {row['ani_var_nome']}", "AVISO")
                STATS["pets"]["erro"] += 1
                continue

            codigo = row["ani_var_chave"]
            existe = db.query(Pet).filter(Pet.codigo == codigo).first()

            if existe:
                ID_MAP["animais"][row["ani_int_codigo"]] = existe.id
                STATS["pets"]["duplicado"] += 1
                log(f"Pet já existe: {row['ani_var_nome']} (#{codigo})", "AVISO")
                continue

            sexo_map = {"Macho": "macho", "Fêmea": "fêmea"}
            sexo = sexo_map.get(row.get("ani_var_sexo", ""), None)

            especie_nome = (
                row.get("esp_var_nome")
                if row.get("esp_var_nome") and row["esp_var_nome"] != "NULL"
                else None
            )
            if not especie_nome:
                log(f"Pet {row['ani_var_nome']} sem espécie, pulando...", "AVISO")
                STATS["pets"]["erro"] += 1
                continue

            pet = Pet(
                cliente_id=cliente_id,
                user_id=USER_ID,
                tenant_id=TENANT_ID,
                codigo=codigo,
                nome=row["ani_var_nome"],
                especie=especie_nome,
                raca=row.get("rac_var_nome")
                if row.get("rac_var_nome") and row["rac_var_nome"] != "NULL"
                else None,
                sexo=sexo,
                castrado=parse_bool(row.get("ani_var_esterilizacao")),
                data_nascimento=parse_date(row.get("ani_dat_nascimento")),
                peso=parse_decimal(row.get("ani_dec_peso")),
                cor=row.get("pel_var_nome")
                if row.get("pel_var_nome") and row["pel_var_nome"] != "NULL"
                else None,
                microchip=row.get("ani_var_chip")
                if row.get("ani_var_chip") and row["ani_var_chip"] != "NULL"
                else None,
                ativo=row.get("ani_var_morto", "Não") != "Sim",
                created_at=parse_date(row.get("ani_dti_inclusao")),
            )

            db.add(pet)
            db.flush()

            ID_MAP["animais"][row["ani_int_codigo"]] = pet.id
            STATS["pets"]["sucesso"] += 1
            log(f"Pet: {pet.nome} - {pet.especie}", "SUCESSO")

        except Exception as e:
            STATS["pets"]["erro"] += 1
            log(f"Erro pet {row.get('ani_var_nome', 'DESCONHECIDO')}: {str(e)}", "ERRO")
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

    registros = ler_csv("eco_venda.csv", limite)
    STATS["vendas"]["total"] = len(registros)

    vendas_ids_antigos = []

    for row in registros:
        try:
            cliente_id = None
            if row.get("pes_int_codigo") and row["pes_int_codigo"] != "NULL":
                cliente_id = ID_MAP["pessoas"].get(row["pes_int_codigo"])

            subtotal = parse_decimal(row["ven_dec_bruto"])
            desconto_valor = parse_decimal(row.get("ven_dec_descontovalor", "0"))
            desconto_percentual = parse_decimal(
                row.get("ven_dec_descontopercentual", "0")
            )
            total = parse_decimal(row["ven_dec_liquido"])

            status_map = {
                "Baixado": "finalizada",
                "Aberto": "aberta",
                "Cancelado": "cancelada",
            }
            status = status_map.get(row.get("ven_var_status", "Aberto"), "aberta")

            data_venda = parse_date(row["ven_dat_data"]) or datetime.now()
            data_finalizacao = (
                parse_date(row.get("ven_dat_pagamento"))
                if status == "finalizada"
                else None
            )

            if data_hoje:
                data_venda = datetime.now()
                data_finalizacao = datetime.now() if status == "finalizada" else None

            numero_venda = f"IMP-{data_venda.strftime('%Y%m%d')}-{row['ven_var_chave']}"

            # Verificar duplicata
            existe = db.query(Venda).filter(Venda.numero_venda == numero_venda).first()
            if existe:
                ID_MAP["vendas"][row["ven_int_codigo"]] = existe.id
                STATS["vendas"]["duplicado"] += 1
                vendas_ids_antigos.append(row["ven_int_codigo"])
                log(f"Venda já existe: {numero_venda}", "AVISO")
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
                observacoes=row.get("ven_txt_observacao")
                if row.get("ven_txt_observacao") and row["ven_txt_observacao"] != "NULL"
                else None,
                status=status,
                data_venda=data_venda,
                data_finalizacao=data_finalizacao,
                created_at=parse_date(row.get("ven_dti_inclusao")) or datetime.now(),
            )

            db.add(venda)
            db.flush()

            ID_MAP["vendas"][row["ven_int_codigo"]] = venda.id
            vendas_ids_antigos.append(row["ven_int_codigo"])
            STATS["vendas"]["sucesso"] += 1
            log(f"Venda: {venda.numero_venda} - R$ {venda.total:.2f}", "SUCESSO")

        except Exception as e:
            STATS["vendas"]["erro"] += 1
            log(
                f"Erro venda {row.get('ven_var_chave', 'DESCONHECIDO')}: {str(e)}",
                "ERRO",
            )
            db.rollback()  # Rollback necessário após erro
            continue

    db.commit()
    log(f"✓ Vendas: {STATS['vendas']['sucesso']}/{STATS['vendas']['total']}")

    # Importar itens
    importar_itens_venda(db, vendas_ids_antigos)


def importar_itens_venda(db: Session, vendas_ids: List[str]):
    """Importa itens das vendas"""
    log("═══ FASE 4.1 - ITENS DAS VENDAS ═══")

    registros = ler_csv("eco_venda_produto.csv", limite=None)
    itens_filtrados = [r for r in registros if r["ven_int_codigo"] in vendas_ids]

    STATS["itens_venda"]["total"] = len(itens_filtrados)

    for row in itens_filtrados:
        try:
            venda_id = ID_MAP["vendas"].get(row["ven_int_codigo"])
            produto_id = ID_MAP["produtos"].get(row["pro_int_codigo"])

            if not venda_id or not produto_id:
                STATS["itens_venda"]["erro"] += 1
                continue

            quantidade = parse_decimal(row["vpr_dec_quantidade"])
            preco_unitario = parse_decimal(row["vpr_dec_preco"])
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
                created_at=parse_date(row.get("vpr_dti_inclusao")) or datetime.now(),
            )

            db.add(item)
            STATS["itens_venda"]["sucesso"] += 1

        except Exception as e:
            STATS["itens_venda"]["erro"] += 1
            log(f"Erro item: {str(e)}", "ERRO")
            continue

    db.commit()
    log(f"✓ Itens: {STATS['itens_venda']['sucesso']}/{STATS['itens_venda']['total']}")


# =====================================================================
# MAIN
# =====================================================================


def exibir_resumo():
    """Exibe resumo da importacao."""
    _exibir_resumo(STATS, NAO_IMPORTADOS)


def main():
    """Executar importação"""
    parser = argparse.ArgumentParser(description="Importar dados do SimplesVet")
    parser.add_argument("--fase", type=int, help="Fase específica (1-4)")
    parser.add_argument("--all", action="store_true", help="Todas as fases")
    parser.add_argument("--limite", type=int, default=20, help="Limite de registros")
    parser.add_argument(
        "--data-hoje", action="store_true", help="Força data das vendas para hoje"
    )

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
        log(f"ERRO FATAL: {str(e)}", "ERRO")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
