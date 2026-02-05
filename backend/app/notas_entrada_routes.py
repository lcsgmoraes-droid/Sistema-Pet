"""
ROTAS DE ENTRADA POR XML - Sistema Pet Shop Pro
Upload e processamento de NF-e de fornecedores

Funcionalidades:
- Upload de XML de NF-e
- Parser automÃ¡tico de XML
- Matching automÃ¡tico de produtos
- Entrada automÃ¡tica no estoque
- GestÃ£o de produtos nÃ£o vinculados
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, desc
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
import xml.etree.ElementTree as ET
from difflib import SequenceMatcher

from app.clientes_routes import gerar_codigo_cliente

from .db import get_session
from .auth import get_current_user
from .auth.dependencies import get_current_user_and_tenant
from .models import User, Cliente
from .produtos_models import (
    Produto, ProdutoLote, EstoqueMovimentacao,
    NotaEntrada, NotaEntradaItem, ProdutoHistoricoPreco,
    ProdutoFornecedor
)
from .financeiro_models import ContaPagar

import logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notas-entrada", tags=["Notas de Entrada (XML)"])

# ============================================================================
# SCHEMAS
# ============================================================================

class NotaEntradaResponse(BaseModel):
    id: int
    numero_nota: str
    serie: str
    chave_acesso: str
    fornecedor_nome: str
    fornecedor_cnpj: str
    fornecedor_id: Optional[int] = None
    data_emissao: datetime
    valor_total: float
    status: str
    produtos_vinculados: Optional[int] = 0
    produtos_nao_vinculados: Optional[int] = 0
    entrada_estoque_realizada: Optional[bool] = False
    
    model_config = {"from_attributes": True}


# ============================================================================
# PARSER DE XML NF-e
# ============================================================================

def parse_nfe_xml(xml_content: str) -> dict:
    """
    Parse de XML de NF-e (padrÃ£o SEFAZ)
    Retorna dados estruturados da nota
    """
    try:
        root = ET.fromstring(xml_content)
        
        # Namespace do XML da NF-e
        ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
        
        # Buscar informaÃ§Ãµes principais
        inf_nfe = root.find('.//nfe:infNFe', ns)
        if not inf_nfe:
            raise ValueError("Tag infNFe nÃ£o encontrada no XML")
        
        # Chave de acesso
        chave_acesso = inf_nfe.get('Id', '').replace('NFe', '')
        
        # IdentificaÃ§Ã£o da nota
        ide = inf_nfe.find('.//nfe:ide', ns)
        numero_nota = ide.find('nfe:nNF', ns).text if ide.find('nfe:nNF', ns) is not None else ''
        serie = ide.find('nfe:serie', ns).text if ide.find('nfe:serie', ns) is not None else '1'
        data_emissao_str = ide.find('nfe:dhEmi', ns).text if ide.find('nfe:dhEmi', ns) is not None else ide.find('nfe:dEmi', ns).text
        # Usar date.fromisoformat para evitar problema de timezone (perda de 1 dia)
        from datetime import date
        data_emissao = date.fromisoformat(data_emissao_str.replace('Z', '+00:00').split('T')[0])
        
        # Emitente (fornecedor) - Dados completos
        emit = inf_nfe.find('.//nfe:emit', ns)
        fornecedor_cnpj = emit.find('nfe:CNPJ', ns).text if emit.find('nfe:CNPJ', ns) is not None else ''
        fornecedor_nome = emit.find('nfe:xNome', ns).text if emit.find('nfe:xNome', ns) is not None else ''
        fornecedor_fantasia = emit.find('nfe:xFant', ns).text if emit.find('nfe:xFant', ns) is not None else ''
        fornecedor_ie = emit.find('nfe:IE', ns).text if emit.find('nfe:IE', ns) is not None else ''
        
        # EndereÃ§o do fornecedor
        ender_emit = emit.find('nfe:enderEmit', ns)
        fornecedor_endereco = ''
        fornecedor_numero = ''
        fornecedor_bairro = ''
        fornecedor_cidade = ''
        fornecedor_uf = ''
        fornecedor_cep = ''
        fornecedor_telefone = ''
        
        if ender_emit is not None:
            fornecedor_endereco = ender_emit.find('nfe:xLgr', ns).text if ender_emit.find('nfe:xLgr', ns) is not None else ''
            fornecedor_numero = ender_emit.find('nfe:nro', ns).text if ender_emit.find('nfe:nro', ns) is not None else ''
            fornecedor_bairro = ender_emit.find('nfe:xBairro', ns).text if ender_emit.find('nfe:xBairro', ns) is not None else ''
            fornecedor_cidade = ender_emit.find('nfe:xMun', ns).text if ender_emit.find('nfe:xMun', ns) is not None else ''
            fornecedor_uf = ender_emit.find('nfe:UF', ns).text if ender_emit.find('nfe:UF', ns) is not None else ''
            fornecedor_cep = ender_emit.find('nfe:CEP', ns).text if ender_emit.find('nfe:CEP', ns) is not None else ''
            fornecedor_telefone = ender_emit.find('nfe:fone', ns).text if ender_emit.find('nfe:fone', ns) is not None else ''
        
        # Totais
        total = inf_nfe.find('.//nfe:total/nfe:ICMSTot', ns)
        valor_produtos = float(total.find('nfe:vProd', ns).text) if total.find('nfe:vProd', ns) is not None else 0
        valor_frete = float(total.find('nfe:vFrete', ns).text) if total.find('nfe:vFrete', ns) is not None else 0
        valor_desconto = float(total.find('nfe:vDesc', ns).text) if total.find('nfe:vDesc', ns) is not None else 0
        valor_total = float(total.find('nfe:vNF', ns).text) if total.find('nfe:vNF', ns) is not None else 0
        
        # Itens
        itens = []
        det_list = inf_nfe.findall('.//nfe:det', ns)
        
        for idx, det in enumerate(det_list, start=1):
            prod = det.find('nfe:prod', ns)
            
            codigo_produto = prod.find('nfe:cProd', ns).text if prod.find('nfe:cProd', ns) is not None else ''
            descricao = prod.find('nfe:xProd', ns).text if prod.find('nfe:xProd', ns) is not None else ''
            ncm = prod.find('nfe:NCM', ns).text if prod.find('nfe:NCM', ns) is not None else ''
            cest = prod.find('nfe:CEST', ns).text if prod.find('nfe:CEST', ns) is not None else ''
            cfop = prod.find('nfe:CFOP', ns).text if prod.find('nfe:CFOP', ns) is not None else ''
            origem = prod.find('nfe:orig', ns).text if prod.find('nfe:orig', ns) is not None else '0'
            unidade = prod.find('nfe:uCom', ns).text if prod.find('nfe:uCom', ns) is not None else 'UN'
            quantidade = float(prod.find('nfe:qCom', ns).text) if prod.find('nfe:qCom', ns) is not None else 0
            valor_unitario = float(prod.find('nfe:vUnCom', ns).text) if prod.find('nfe:vUnCom', ns) is not None else 0
            valor_total_item = float(prod.find('nfe:vProd', ns).text) if prod.find('nfe:vProd', ns) is not None else 0
            ean = prod.find('nfe:cEAN', ns).text if prod.find('nfe:cEAN', ns) is not None else ''
            
            # Extrair lote e validade da tag <rastro> (rastreabilidade)
            lote = ''
            data_validade = None
            
            # Buscar tag de rastreabilidade
            rastro = prod.find('nfe:rastro', ns)
            if rastro is not None:
                # NÃºmero do lote
                lote_elem = rastro.find('nfe:nLote', ns)
                if lote_elem is not None:
                    lote = lote_elem.text
                
                # Data de validade
                validade_elem = rastro.find('nfe:dVal', ns)
                if validade_elem is not None:
                    try:
                        data_validade = datetime.strptime(validade_elem.text, '%Y-%m-%d').date()
                    except:
                        pass
            
            # Extrair alÃ­quotas de impostos
            aliquota_icms = 0.0
            aliquota_pis = 0.0
            aliquota_cofins = 0.0
            
            # Buscar impostos do item
            imposto = det.find('nfe:imposto', ns)
            if imposto is not None:
                # ICMS - pode estar em vÃ¡rias tags (ICMS00, ICMS10, ICMS20, etc)
                icms_group = imposto.find('nfe:ICMS', ns)
                if icms_group is not None:
                    # Tentar vÃ¡rias possibilidades de tag ICMS
                    for icms_tag in ['ICMS00', 'ICMS10', 'ICMS20', 'ICMS30', 'ICMS40', 'ICMS51', 'ICMS60', 'ICMS70', 'ICMS90', 'ICMSSN101', 'ICMSSN102', 'ICMSSN201', 'ICMSSN202', 'ICMSSN500', 'ICMSSN900']:
                        icms_elem = icms_group.find(f'nfe:{icms_tag}', ns)
                        if icms_elem is not None:
                            picms = icms_elem.find('nfe:pICMS', ns)
                            if picms is not None:
                                try:
                                    aliquota_icms = float(picms.text)
                                    break
                                except:
                                    pass
                
                # PIS
                pis_group = imposto.find('nfe:PIS', ns)
                if pis_group is not None:
                    # PISAliq ou PISOutr
                    for pis_tag in ['PISAliq', 'PISOutr', 'PISNT']:
                        pis_elem = pis_group.find(f'nfe:{pis_tag}', ns)
                        if pis_elem is not None:
                            ppis = pis_elem.find('nfe:pPIS', ns)
                            if ppis is not None:
                                try:
                                    aliquota_pis = float(ppis.text)
                                    break
                                except:
                                    pass
                
                # COFINS
                cofins_group = imposto.find('nfe:COFINS', ns)
                if cofins_group is not None:
                    # COFINSAliq ou COFINSOutr
                    for cofins_tag in ['COFINSAliq', 'COFINSOutr', 'COFINSNT']:
                        cofins_elem = cofins_group.find(f'nfe:{cofins_tag}', ns)
                        if cofins_elem is not None:
                            pcofins = cofins_elem.find('nfe:pCOFINS', ns)
                            if pcofins is not None:
                                try:
                                    aliquota_cofins = float(pcofins.text)
                                    break
                                except:
                                    pass
            
            # Se nÃ£o encontrar em rastro, tentar em informaÃ§Ãµes adicionais do produto
            if not lote:
                inf_ad_prod = prod.find('nfe:infAdProd', ns)
                if inf_ad_prod is not None and inf_ad_prod.text:
                    texto_info = inf_ad_prod.text.upper()
                    # Tentar encontrar LOTE: XXXX
                    if 'LOTE' in texto_info or 'LOTE:' in texto_info:
                        import re
                        match = re.search(r'LOTE[:\s]+([A-Z0-9]+)', texto_info)
                        if match:
                            lote = match.group(1)
            
            itens.append({
                'numero_item': idx,
                'codigo_produto': codigo_produto,
                'descricao': descricao,
                'ncm': ncm,
                'cest': cest,
                'cfop': cfop,
                'origem': origem,
                'aliquota_icms': aliquota_icms,
                'aliquota_pis': aliquota_pis,
                'aliquota_cofins': aliquota_cofins,
                'unidade': unidade,
                'quantidade': quantidade,
                'valor_unitario': valor_unitario,
                'valor_total': valor_total_item,
                'ean': ean,
                'lote': lote,
                'data_validade': data_validade
            })
        
        # Duplicatas (CobranÃ§as) - FASE 4: Para gerar contas a pagar
        duplicatas = []
        cobr = inf_nfe.find('.//nfe:cobr', ns)
        if cobr is not None:
            dup_list = cobr.findall('.//nfe:dup', ns)
            for dup in dup_list:
                numero_dup = dup.find('nfe:nDup', ns).text if dup.find('nfe:nDup', ns) is not None else ''
                vencimento_str = dup.find('nfe:dVenc', ns).text if dup.find('nfe:dVenc', ns) is not None else ''
                valor_dup = float(dup.find('nfe:vDup', ns).text) if dup.find('nfe:vDup', ns) is not None else 0
                
                # Parse data de vencimento (formato YYYY-MM-DD) - usar date para evitar problema de timezone
                from datetime import date
                vencimento = date.fromisoformat(vencimento_str) if vencimento_str else (datetime.now() + timedelta(days=30)).date()
                
                duplicatas.append({
                    'numero': numero_dup,
                    'vencimento': vencimento,
                    'valor': valor_dup
                })
        
        return {
            'chave_acesso': chave_acesso,
            'numero_nota': numero_nota,
            'serie': serie,
            'data_emissao': data_emissao,
            'fornecedor_cnpj': fornecedor_cnpj,
            'fornecedor_nome': fornecedor_nome,
            'fornecedor_fantasia': fornecedor_fantasia,
            'fornecedor_ie': fornecedor_ie,
            'fornecedor_endereco': fornecedor_endereco,
            'fornecedor_numero': fornecedor_numero,
            'fornecedor_bairro': fornecedor_bairro,
            'fornecedor_cidade': fornecedor_cidade,
            'fornecedor_uf': fornecedor_uf,
            'fornecedor_cep': fornecedor_cep,
            'fornecedor_telefone': fornecedor_telefone,
            'valor_produtos': valor_produtos,
            'valor_frete': valor_frete,
            'valor_desconto': valor_desconto,
            'valor_total': valor_total,
            'itens': itens,
            'duplicatas': duplicatas
        }
        
    except ET.ParseError as e:
        raise ValueError(f"Erro ao fazer parse do XML: {str(e)}")
    except Exception as e:
        raise ValueError(f"Erro ao processar XML: {str(e)}")


def gerar_prefixo_fornecedor(nome: str) -> str:
    """
    Gera um prefixo baseado no nome do fornecedor
    Ex: Megazoo -> MGZ, Reino das Aves -> RA
    """
    # Remover palavras comuns
    palavras_ignorar = {'ltda', 'sa', 'me', 'epp', 'eireli', 'comercio', 'industria', 'distribuidora', 'de', 'da', 'do', 'das', 'dos', 'e'}
    palavras = [p for p in nome.lower().split() if p not in palavras_ignorar]
    
    if not palavras:
        return nome[:3].upper()
    
    # Se tiver uma palavra, pega as 3 primeiras letras
    if len(palavras) == 1:
        return palavras[0][:3].upper()
    
    # Se tiver 2-3 palavras, pega a primeira letra de cada
    if len(palavras) <= 3:
        return ''.join([p[0] for p in palavras]).upper()
    
    # Se tiver mais de 3, pega as mais significativas (maiores)
    palavras_ordenadas = sorted(palavras, key=len, reverse=True)[:3]
    return ''.join([p[0] for p in palavras_ordenadas]).upper()


def criar_fornecedor_automatico(dados_xml: dict, db: Session, current_user, tenant_id: int) -> tuple:
    """
    Cria um fornecedor automaticamente a partir dos dados do XML
    Se jÃ¡ existir um fornecedor inativo com o mesmo CNPJ, reativa ele
    Retorna (fornecedor, foi_criado_agora)
    """
    cnpj = dados_xml['fornecedor_cnpj']
    
    # Verificar se jÃ¡ existe (ativo ou inativo)
    fornecedor = db.query(Cliente).filter(Cliente.cnpj == cnpj).first()
    
    if fornecedor:
        # Se estiver inativo, reativar e atualizar dados
        if not fornecedor.ativo:
            logger.info(f"ðŸ”„ Reativando fornecedor inativo: {fornecedor.nome}")
            fornecedor.ativo = True
            fornecedor.nome = dados_xml['fornecedor_nome']
            fornecedor.razao_social = dados_xml['fornecedor_nome']
            fornecedor.nome_fantasia = dados_xml.get('fornecedor_fantasia', '')
            fornecedor.inscricao_estadual = dados_xml.get('fornecedor_ie', '')
            fornecedor.endereco = dados_xml.get('fornecedor_endereco', '')
            fornecedor.numero = dados_xml.get('fornecedor_numero', '')
            fornecedor.bairro = dados_xml.get('fornecedor_bairro', '')
            fornecedor.cidade = dados_xml.get('fornecedor_cidade', '')
            fornecedor.estado = dados_xml.get('fornecedor_uf', '')
            fornecedor.cep = dados_xml.get('fornecedor_cep', '')
            fornecedor.telefone = dados_xml.get('fornecedor_telefone', '')
            
            # Se nÃ£o tem cÃ³digo, gerar agora
            if not fornecedor.codigo:
                fornecedor.codigo = gerar_codigo_cliente(db, 'fornecedor', 'PJ', tenant_id)
            
            db.commit()
            db.refresh(fornecedor)
            logger.info(f"âœ… Fornecedor reativado: {fornecedor.nome} (CÃ³digo: {fornecedor.codigo})")
            return (fornecedor, True)
        
        # Se jÃ¡ estÃ¡ ativo, verificar se tem cÃ³digo
        if not fornecedor.codigo:
            fornecedor.codigo = gerar_codigo_cliente(db, 'fornecedor', 'PJ', tenant_id)
            db.commit()
            db.refresh(fornecedor)
            logger.info(f"âœ… CÃ³digo gerado para fornecedor existente: {fornecedor.nome} (CÃ³digo: {fornecedor.codigo})")
        
        return (fornecedor, False)
    
    # Gerar cÃ³digo para novo fornecedor
    codigo = gerar_codigo_cliente(db, 'fornecedor', 'PJ', tenant_id)
    
    # Criar novo fornecedor
    fornecedor = Cliente(
        tipo_cadastro='fornecedor',
        tipo_pessoa='PJ',
        nome=dados_xml['fornecedor_nome'],
        razao_social=dados_xml['fornecedor_nome'],
        nome_fantasia=dados_xml.get('fornecedor_fantasia', ''),
        cnpj=cnpj,
        inscricao_estadual=dados_xml.get('fornecedor_ie', ''),
        endereco=dados_xml.get('fornecedor_endereco', ''),
        numero=dados_xml.get('fornecedor_numero', ''),
        bairro=dados_xml.get('fornecedor_bairro', ''),
        cidade=dados_xml.get('fornecedor_cidade', ''),
        estado=dados_xml.get('fornecedor_uf', ''),
        cep=dados_xml.get('fornecedor_cep', ''),
        telefone=dados_xml.get('fornecedor_telefone', ''),
        codigo=codigo,
        ativo=True,
        user_id=current_user.id,
        tenant_id=tenant_id
    )
    
    db.add(fornecedor)
    db.commit()
    db.refresh(fornecedor)
    
    logger.info(f"âœ… Fornecedor criado automaticamente: {fornecedor.nome}")
    
    return (fornecedor, True)


def gerar_sku_automatico(prefixo: str, db: Session, user_id: int) -> str:
    """
    Gera um SKU Ãºnico automaticamente para produtos sem cÃ³digo
    Formato: {PREFIXO}-{NÃšMERO_SEQUENCIAL}
    Exemplo: PROD-00001
    """
    # Buscar Ãºltimo SKU com o mesmo prefixo
    ultimo_produto = db.query(Produto).filter(
        Produto.user_id == user_id,
        Produto.codigo.like(f"{prefixo}-%")
    ).order_by(Produto.id.desc()).first()
    
    if ultimo_produto:
        try:
            ultimo_numero = int(ultimo_produto.codigo.split("-")[-1])
            proximo_numero = ultimo_numero + 1
        except ValueError:
            proximo_numero = 1
    else:
        proximo_numero = 1
    
    # Gerar novo SKU
    novo_sku = f"{prefixo}-{proximo_numero:05d}"
    
    # Verificar se jÃ¡ existe
    existe = db.query(Produto).filter(
        Produto.codigo == novo_sku,
        Produto.user_id == user_id
    ).first()
    
    if existe:
        novo_sku = f"{prefixo}-{proximo_numero + 1:05d}"
    
    return novo_sku


def calcular_similaridade(texto1: str, texto2: str) -> float:
    """Calcula similaridade entre dois textos (0-1)"""
    if not texto1 or not texto2:
        return 0.0
    return SequenceMatcher(None, texto1.lower(), texto2.lower()).ratio()


def encontrar_produto_similar(descricao: str, codigo: str, db: Session, fornecedor_id: int = None) -> tuple:
    """
    Encontra produto similar no banco (ativo OU inativo)
    Retorna (produto, confianca, foi_encontrado_inativo)
    
    REGRAS DE MATCHING (RIGOROSAS):
    1. SKU exato (codigo) + fornecedor igual = match automático
    2. EAN exato (codigo_barras) = match automático
    3. Caso contrário = NÃO vincula (usuário decide manualmente)
    
    Matching por similaridade de nome foi REMOVIDO para evitar vínculos errados
    """
    # 1. Tentar por SKU exato (código do produto)
    if codigo:
        # Buscar por SKU exato
        query = db.query(Produto).filter(Produto.codigo == codigo)
        
        # Se tem fornecedor, verificar se produto pertence a ele
        if fornecedor_id:
            # Buscar produto que pertence ao fornecedor
            produto_com_fornecedor = query.join(
                ProdutoFornecedor,
                ProdutoFornecedor.produto_id == Produto.id
            ).filter(
                ProdutoFornecedor.fornecedor_id == fornecedor_id,
                ProdutoFornecedor.ativo == True
            ).first()
            
            if produto_com_fornecedor:
                foi_inativo = not produto_com_fornecedor.ativo
                logger.info(f"✅ Match por SKU + Fornecedor: {produto_com_fornecedor.nome}")
                return (produto_com_fornecedor, 1.0, foi_inativo)
        
        # Se não encontrou com fornecedor, buscar só por SKU
        produto = query.first()
        if produto:
            foi_inativo = not produto.ativo
            logger.info(f"✅ Match por SKU: {produto.nome}")
            return (produto, 1.0, foi_inativo)
    
    # 2. Tentar por EAN/Código de Barras exato
    if codigo:
        produto = db.query(Produto).filter(
            Produto.codigo_barras == codigo
        ).first()
        
        if produto:
            foi_inativo = not produto.ativo
            logger.info(f"✅ Match por EAN: {produto.nome}")
            return (produto, 1.0, foi_inativo)
    
    # 3. NÃO fazer matching automático por nome/similaridade
    # Usuário deve vincular manualmente para evitar erros
    logger.info(f"⚠️ Nenhum match encontrado para: {descricao[:50]} (SKU: {codigo})")
    return (None, 0, False)


def criar_contas_pagar_da_nota(nota: NotaEntrada, dados_xml: dict, db: Session, user_id: int, tenant_id: str) -> List[int]:
    """
    Cria contas a pagar automaticamente com base nas duplicatas do XML
    FASE 4: IntegraÃ§Ã£o NF-e â†’ Financeiro
    Retorna lista de IDs das contas criadas
    """
    logger.info(f"ðŸ’° Gerando contas a pagar para nota {nota.numero_nota}...")
    
    contas_criadas = []
    
    # Buscar duplicatas no XML (tag <dup>)
    duplicatas = dados_xml.get('duplicatas', [])
    
    if not duplicatas:
        # Se nÃ£o tem duplicatas, criar uma Ãºnica conta com vencimento em 30 dias
        logger.info("   âš ï¸ Sem duplicatas no XML, criando conta Ãºnica com vencimento +30 dias")
        duplicatas = [{
            'numero': f"{nota.numero_nota}-1",
            'vencimento': datetime.now() + timedelta(days=30),
            'valor': nota.valor_total
        }]
    
    total_duplicatas = len(duplicatas)
    eh_parcelado = total_duplicatas > 1
    
    for idx, dup in enumerate(duplicatas, 1):
        try:
            # Valor vem em reais do XML, usar Decimal para precisÃ£o
            from decimal import Decimal
            valor_reais = Decimal(str(dup['valor']))
            
            # Criar conta a pagar
            conta = ContaPagar(
                fornecedor_id=nota.fornecedor_id,
                descricao=f"NF-e {nota.numero_nota} - Parcela {dup['numero']}",
                valor_original=valor_reais,
                valor_final=valor_reais,
                valor_pago=Decimal('0'),
                data_emissao=nota.data_emissao,
                data_vencimento=dup['vencimento'],
                status='pendente',
                eh_parcelado=eh_parcelado,
                numero_parcela=idx if eh_parcelado else None,
                total_parcelas=total_duplicatas if eh_parcelado else None,
                nota_entrada_id=nota.id,
                nfe_numero=str(nota.numero_nota),
                documento=dup.get('numero', ''),  # NÃºmero da duplicata do XML (n1, n2, etc)
                percentual_online=nota.percentual_online or 0,  # Herdar rateio da nota
                percentual_loja=nota.percentual_loja or 100,
                user_id=user_id,
                tenant_id=tenant_id
            )
            
            db.add(conta)
            db.flush()
            
            contas_criadas.append(conta.id)
            
            logger.info(f"   âœ… Conta criada: {dup['numero']} - R$ {dup['valor']:.2f} - Venc: {dup['vencimento'].strftime('%d/%m/%Y')}")
            
        except Exception as e:
            logger.error(f"   âŒ Erro ao criar conta da duplicata {dup.get('numero')}: {str(e)}")
            raise
    
    logger.info(f"âœ… Total de contas criadas: {len(contas_criadas)}")
    return contas_criadas


# ============================================================================
# UPLOAD DE XML
# ============================================================================

@router.post("/upload")
async def upload_xml(
    file: UploadFile = File(...),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Upload de XML de NF-e e parse automÃ¡tico"""
    current_user, tenant_id = user_and_tenant
    
    logger.info(f"ðŸ“„ Upload de XML - Arquivo: {file.filename}")
    logger.info(f"   - Content-type: {file.content_type}")
    logger.info(f"   - UsuÃ¡rio: {current_user.email} (ID: {current_user.id})")
    
    try:
        # Validar extensÃ£o
        if not file.filename.endswith('.xml'):
            logger.error(f"âŒ Arquivo invÃ¡lido: {file.filename} (nÃ£o Ã© .xml)")
            raise HTTPException(status_code=400, detail="Arquivo deve ser .xml")
        
        # Ler conteÃºdo
        logger.info("ðŸ“– Lendo conteÃºdo do arquivo...")
        xml_content = await file.read()
        logger.info(f"   - Tamanho: {len(xml_content)} bytes")
        
        xml_str = xml_content.decode('utf-8')
        logger.info("âœ… Arquivo decodificado com sucesso")
        
        # Parse do XML
        logger.info("ðŸ” Fazendo parse do XML...")
        try:
            dados_nfe = parse_nfe_xml(xml_str)
            logger.info("âœ… Parse concluÃ­do:")
            logger.info(f"   - Chave: {dados_nfe.get('chave_acesso', 'N/A')}")
            logger.info(f"   - NÃºmero: {dados_nfe.get('numero_nota', 'N/A')}")
            logger.info(f"   - Fornecedor: {dados_nfe.get('fornecedor_nome', 'N/A')}")
            logger.info(f"   - Valor total: R$ {dados_nfe.get('valor_total', 0):.2f}")
            logger.info(f"   - Itens: {len(dados_nfe.get('itens', []))}")
        except ValueError as e:
            logger.error(f"âŒ Erro no parse do XML: {str(e)}")
            logger.error(f"   - Tipo: {type(e).__name__}")
            raise HTTPException(status_code=400, detail=f"Erro ao processar XML: {str(e)}")
        except Exception as e:
            logger.error(f"âŒ Erro inesperado no parse: {str(e)}")
            logger.error(f"   - Tipo: {type(e).__name__}")
            raise HTTPException(status_code=500, detail=f"Erro interno ao processar XML: {str(e)}")
        
        # Verificar se nota jÃ¡ existe
        logger.info(f"ðŸ”Ž Verificando se nota jÃ¡ existe (chave: {dados_nfe['chave_acesso']})...")
        nota_existente = db.query(NotaEntrada).filter(
            NotaEntrada.chave_acesso == dados_nfe['chave_acesso']
        ).first()
        
        if nota_existente:
            logger.warning(f"âš ï¸ Nota jÃ¡ cadastrada! ID: {nota_existente.id}")
            raise HTTPException(
                status_code=400, 
                detail=f"Nota fiscal jÃ¡ cadastrada (ID: {nota_existente.id})"
            )
        
        logger.info("âœ… Nota nÃ£o existe, prosseguindo...")
        
        # Buscar ou criar fornecedor automaticamente
        logger.info(f"ðŸ”Ž Buscando fornecedor por CNPJ: {dados_nfe['fornecedor_cnpj']}...")
        fornecedor = db.query(Cliente).filter(
            Cliente.cnpj == dados_nfe['fornecedor_cnpj'],
            Cliente.ativo == True
        ).first()
        
        fornecedor_criado_automaticamente = False
        
        if fornecedor:
            logger.info(f"âœ… Fornecedor encontrado: {fornecedor.nome} (ID: {fornecedor.id})")
        else:
            logger.warning(f"âš ï¸ Fornecedor nÃ£o cadastrado, criando automaticamente...")
            try:
                fornecedor, fornecedor_criado_automaticamente = criar_fornecedor_automatico(dados_nfe, db, current_user, tenant_id)
                logger.info(f"âœ… Fornecedor criado: {fornecedor.nome} (ID: {fornecedor.id})")
            except Exception as e:
                logger.error(f"âŒ Erro ao criar fornecedor: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Erro ao criar fornecedor: {str(e)}")
        
        # Criar nota
        logger.info("ðŸ’¾ Criando registro da nota no banco...")
        nota = NotaEntrada(
            numero_nota=dados_nfe['numero_nota'],
            serie=dados_nfe['serie'],
            chave_acesso=dados_nfe['chave_acesso'],
            fornecedor_cnpj=dados_nfe['fornecedor_cnpj'],
            fornecedor_nome=dados_nfe['fornecedor_nome'],
            fornecedor_id=fornecedor.id if fornecedor else None,
            data_emissao=dados_nfe['data_emissao'],
            data_entrada=datetime.utcnow(),
            valor_produtos=dados_nfe['valor_produtos'],
            valor_frete=dados_nfe['valor_frete'],
            valor_desconto=dados_nfe['valor_desconto'],
            valor_total=dados_nfe['valor_total'],
            xml_content=xml_str,
            status='pendente',
            user_id=current_user.id,
            tenant_id=tenant_id
        )
        
        db.add(nota)
        db.flush()
        logger.info(f"âœ… Nota criada com ID: {nota.id}")
        
        # Processar itens e fazer matching automÃ¡tico
        logger.info(f"ðŸ”„ Processando {len(dados_nfe['itens'])} itens...")
        vinculados = 0
        nao_vinculados = 0
        produtos_reativados = 0
        
        for item_data in dados_nfe['itens']:
            # Tentar encontrar produto similar (com fornecedor para matching mais preciso)
            produto, confianca, foi_inativo = encontrar_produto_similar(
                item_data['descricao'],
                item_data['codigo_produto'],
                db,
                fornecedor.id if fornecedor else None
            )
            
            if produto:
                vinculados += 1
                if foi_inativo:
                    produtos_reativados += 1
                produto_id = produto.id
                vinculado = True
                item_status = 'vinculado'
                
                # âœ… Apenas gerar SKU se necessÃ¡rio (nÃ£o atualizar outros dados no upload)
                if not produto.codigo or produto.codigo.strip() == '':
                    novo_sku = gerar_sku_automatico('PROD', db, current_user.id)
                    produto.codigo = novo_sku
                    logger.info(f"  ðŸ”– SKU gerado automaticamente: {novo_sku}")
                
                # Log de status do produto
                status_msg = " (INATIVO - serÃ¡ reativado no processamento)" if foi_inativo else ""
                logger.info(
                    f"  âœ… {item_data['descricao'][:50]} â†’ "
                    f"{produto.nome} (confianÃ§a: {confianca:.0%}){status_msg}"
                )
            else:
                nao_vinculados += 1
                produto_id = None
                vinculado = False
                item_status = 'nao_vinculado'
                confianca = 0
                logger.warning(f"  âš ï¸  {item_data['descricao'][:50]} â†’ NÃ£o vinculado")
            
            # Criar item
            item = NotaEntradaItem(
                nota_entrada_id=nota.id,
                numero_item=item_data['numero_item'],
                codigo_produto=item_data['codigo_produto'],
                descricao=item_data['descricao'],
                ncm=item_data['ncm'],
                cest=item_data.get('cest'),
                cfop=item_data['cfop'],
                origem=item_data.get('origem', '0'),
                aliquota_icms=item_data.get('aliquota_icms', 0),
                aliquota_pis=item_data.get('aliquota_pis', 0),
                aliquota_cofins=item_data.get('aliquota_cofins', 0),
                unidade=item_data['unidade'],
                quantidade=item_data['quantidade'],
                valor_unitario=item_data['valor_unitario'],
                valor_total=item_data['valor_total'],
                ean=item_data.get('ean'),
                lote=item_data.get('lote'),
                data_validade=item_data.get('data_validade'),
                produto_id=produto_id,
                vinculado=vinculado,
                confianca_vinculo=confianca,
                status=item_status,
                tenant_id=tenant_id
            )
            db.add(item)
        
        # Atualizar contadores
        nota.produtos_vinculados = vinculados
        nota.produtos_nao_vinculados = nao_vinculados
        
        db.commit()
        db.refresh(nota)
        
        # Log de resumo com informaÃ§Ã£o de reativaÃ§Ãµes
        if produtos_reativados > 0:
            logger.info(f"â™»ï¸  {produtos_reativados} produto(s) inativo(s) foram reativados automaticamente")
        
        logger.info(
            f"âœ… Nota {nota.numero_nota} processada: "
            f"{vinculados} vinculados, {nao_vinculados} nÃ£o vinculados"
        )
        
        return {
            "message": "XML processado com sucesso",
            "nota_id": nota.id,
            "numero_nota": nota.numero_nota,
            "chave_acesso": nota.chave_acesso,
            "fornecedor": nota.fornecedor_nome,
            "fornecedor_id": nota.fornecedor_id,
            "fornecedor_criado_automaticamente": fornecedor_criado_automaticamente,
            "valor_total": nota.valor_total,
            "itens_total": len(dados_nfe['itens']),
            "produtos_vinculados": vinculados,
            "produtos_nao_vinculados": nao_vinculados,
            "produtos_reativados": produtos_reativados
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions (jÃ¡ tratadas)
        raise
    except Exception as e:
        logger.error(f"âŒ Erro inesperado no upload: {str(e)}")
        logger.error(f"   - Tipo: {type(e).__name__}")
        logger.error(f"   - Stack: {e.__traceback__}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao processar XML: {str(e)}")


# ============================================================================
# UPLOAD EM LOTE DE MÃšLTIPLOS XMLs
# ============================================================================

@router.post("/upload-lote")
async def upload_lote_xml(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Upload de mÃºltiplos XMLs de NF-e e processamento em lote
    Retorna resumo de sucessos e erros
    """
    logger.info(f"ðŸ“¦ Upload em lote - {len(files)} arquivos")
    logger.info(f"   - UsuÃ¡rio: {current_user.email}")
    
    resultados = []
    sucessos = 0
    erros = 0
    
    for i, file in enumerate(files, 1):
        logger.info(f"\n{'='*60}")
        logger.info(f"ðŸ“„ Processando arquivo {i}/{len(files)}: {file.filename}")
        logger.info(f"{'='*60}")
        
        resultado = {
            "arquivo": file.filename,
            "ordem": i,
            "sucesso": False,
            "mensagem": "",
            "nota_id": None,
            "numero_nota": None,
            "fornecedor": None,
            "valor_total": None,
            "produtos_vinculados": None,
            "produtos_nao_vinculados": None
        }
        
        try:
            # Validar extensÃ£o
            if not file.filename.endswith('.xml'):
                raise ValueError("Arquivo deve ser .xml")
            
            # Ler e decodificar
            xml_content = await file.read()
            xml_str = xml_content.decode('utf-8')
            
            # Parse do XML
            dados_nfe = parse_nfe_xml(xml_str)
            
            # Verificar se nota jÃ¡ existe
            nota_existente = db.query(NotaEntrada).filter(
                NotaEntrada.chave_acesso == dados_nfe['chave_acesso']
            ).first()
            
            if nota_existente:
                raise ValueError(f"Nota jÃ¡ cadastrada (ID: {nota_existente.id})")
            
            # Buscar ou criar fornecedor
            fornecedor = db.query(Cliente).filter(
                Cliente.cnpj == dados_nfe['fornecedor_cnpj']
            ).first()
            
            fornecedor_criado = False
            if not fornecedor:
                fornecedor, fornecedor_criado = criar_fornecedor_automatico(dados_nfe, db)
            
            # Criar nota
            nota = NotaEntrada(
                numero_nota=dados_nfe['numero_nota'],
                serie=dados_nfe['serie'],
                chave_acesso=dados_nfe['chave_acesso'],
                fornecedor_cnpj=dados_nfe['fornecedor_cnpj'],
                fornecedor_nome=dados_nfe['fornecedor_nome'],
                fornecedor_id=fornecedor.id if fornecedor else None,
                data_emissao=dados_nfe['data_emissao'],
                data_entrada=datetime.utcnow(),
                valor_produtos=dados_nfe['valor_produtos'],
                valor_frete=dados_nfe['valor_frete'],
                valor_desconto=dados_nfe['valor_desconto'],
                valor_total=dados_nfe['valor_total'],
                xml_content=xml_str,
                status='pendente',
                user_id=current_user.id
            )
            
            db.add(nota)
            db.flush()
            
            # Processar itens com matching
            vinculados = 0
            nao_vinculados = 0
            produtos_reativados = 0
            
            for item_data in dados_nfe['itens']:
                produto, confianca, foi_reativado = encontrar_produto_similar(
                    item_data['descricao'],
                    item_data['codigo_produto'],
                    db
                )
                
                if produto:
                    vinculados += 1
                    if foi_reativado:
                        produtos_reativados += 1
                    produto_id = produto.id
                    vinculado = True
                    item_status = 'vinculado'
                else:
                    nao_vinculados += 1
                    produto_id = None
                    vinculado = False
                    item_status = 'nao_vinculado'
                    confianca = 0
                
                item = NotaEntradaItem(
                    nota_entrada_id=nota.id,
                    numero_item=item_data['numero_item'],
                    codigo_produto=item_data['codigo_produto'],
                    descricao=item_data['descricao'],
                    ncm=item_data['ncm'],
                    cfop=item_data['cfop'],
                    unidade=item_data['unidade'],
                    quantidade=item_data['quantidade'],
                    valor_unitario=item_data['valor_unitario'],
                    valor_total=item_data['valor_total'],
                    ean=item_data.get('ean'),
                    lote=item_data.get('lote'),
                    data_validade=item_data.get('data_validade'),
                    produto_id=produto_id,
                    vinculado=vinculado,
                    confianca_vinculo=confianca,
                    status=item_status
                )
                db.add(item)
            
            # Atualizar contadores
            nota.produtos_vinculados = vinculados
            nota.produtos_nao_vinculados = nao_vinculados
            
            db.commit()
            db.refresh(nota)
            
            # Log de reativaÃ§Ãµes
            if produtos_reativados > 0:
                logger.info(f"â™»ï¸  {produtos_reativados} produto(s) inativo(s) reativado(s) - Nota {nota.numero_nota}")
            
            # Sucesso!
            resultado["sucesso"] = True
            resultado["mensagem"] = "Processado com sucesso"
            resultado["nota_id"] = nota.id
            resultado["numero_nota"] = nota.numero_nota
            resultado["fornecedor"] = nota.fornecedor_nome
            resultado["valor_total"] = nota.valor_total
            resultado["produtos_vinculados"] = vinculados
            resultado["produtos_nao_vinculados"] = nao_vinculados
            
            sucessos += 1
            logger.info(f"âœ… {file.filename} processado com sucesso (Nota {nota.numero_nota})")
            
        except ValueError as e:
            resultado["mensagem"] = f"Erro de validaÃ§Ã£o: {str(e)}"
            erros += 1
            logger.error(f"âŒ {file.filename}: {str(e)}")
            db.rollback()
            
        except Exception as e:
            resultado["mensagem"] = f"Erro ao processar: {str(e)}"
            erros += 1
            logger.error(f"âŒ {file.filename}: Erro inesperado - {str(e)}")
            db.rollback()
        
        resultados.append(resultado)
    
    logger.info(f"\n{'='*60}")
    logger.info(f"ðŸ“Š RESUMO DO LOTE:")
    logger.info(f"   - Total de arquivos: {len(files)}")
    logger.info(f"   - âœ… Sucessos: {sucessos}")
    logger.info(f"   - âŒ Erros: {erros}")
    logger.info(f"{'='*60}\n")
    
    return {
        "message": f"Processamento em lote concluÃ­do: {sucessos} sucessos, {erros} erros",
        "total_arquivos": len(files),
        "sucessos": sucessos,
        "erros": erros,
        "resultados": resultados
    }


# ============================================================================
# LISTAR NOTAS
# ============================================================================

@router.get("/", response_model=List[NotaEntradaResponse])
def listar_notas(
    status: Optional[str] = Query(None, description="Filtrar por status"),
    fornecedor_id: Optional[int] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Lista notas de entrada"""
    user, tenant_id = user_and_tenant
    
    query = db.query(NotaEntrada).filter(NotaEntrada.tenant_id == tenant_id)
    
    if status:
        query = query.filter(NotaEntrada.status == status)
    if fornecedor_id:
        query = query.filter(NotaEntrada.fornecedor_id == fornecedor_id)
    
    query = query.order_by(desc(NotaEntrada.data_entrada))
    
    total = query.count()
    notas = query.offset(offset).limit(limit).all()
    
    logger.info(f"ðŸ“‹ {len(notas)} notas encontradas (total: {total})")
    
    # Converter explicitamente para o schema Pydantic (Pydantic v2)
    return [NotaEntradaResponse.model_validate(nota) for nota in notas]


# ============================================================================
# BUSCAR NOTA POR ID
# ============================================================================

@router.get("/{nota_id}")
def buscar_nota(
    nota_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Busca nota completa com itens"""
    user, tenant_id = user_and_tenant
    
    nota = db.query(NotaEntrada).options(
        joinedload(NotaEntrada.itens).joinedload(NotaEntradaItem.produto)
    ).filter(
        NotaEntrada.id == nota_id,
        NotaEntrada.tenant_id == tenant_id
    ).first()
    
    if not nota:
        raise HTTPException(status_code=404, detail="Nota nÃ£o encontrada")
    
    # Verificar se fornecedor foi criado recentemente (Ãºltimas 24h)
    fornecedor_criado_automaticamente = False
    if nota.fornecedor_id:
        fornecedor = db.query(Cliente).filter(Cliente.id == nota.fornecedor_id).first()
        if fornecedor and fornecedor.created_at:
            # Se o fornecedor foi criado menos de 24h antes da nota
            # Garantir compatibilidade de timezone
            data_entrada = nota.data_entrada.replace(tzinfo=None) if nota.data_entrada.tzinfo else nota.data_entrada
            created_at = fornecedor.created_at.replace(tzinfo=None) if fornecedor.created_at.tzinfo else fornecedor.created_at
            diferenca = data_entrada - created_at
            if diferenca < timedelta(hours=24):
                fornecedor_criado_automaticamente = True
    
    # Formatar resposta
    return {
        "id": nota.id,
        "numero_nota": nota.numero_nota,
        "serie": nota.serie,
        "chave_acesso": nota.chave_acesso,
        "fornecedor_nome": nota.fornecedor_nome,
        "fornecedor_cnpj": nota.fornecedor_cnpj,
        "fornecedor_id": nota.fornecedor_id,
        "fornecedor_criado_automaticamente": fornecedor_criado_automaticamente,
        "data_emissao": nota.data_emissao,
        "valor_total": nota.valor_total,
        "status": nota.status,
        "produtos_vinculados": nota.produtos_vinculados,
        "produtos_nao_vinculados": nota.produtos_nao_vinculados,
        "entrada_estoque_realizada": nota.entrada_estoque_realizada,
        "itens": [
            {
                "id": item.id,
                "numero_item": item.numero_item,
                "codigo_produto": item.codigo_produto,
                "descricao": item.descricao,
                "ncm": item.ncm,
                "cfop": item.cfop,
                "unidade": item.unidade,
                "quantidade": item.quantidade,
                "valor_unitario": item.valor_unitario,
                "valor_total": item.valor_total,
                "ean": item.ean,
                "lote": item.lote,
                "data_validade": item.data_validade.isoformat() if item.data_validade else None,
                "produto_id": item.produto_id,
                "produto_nome": item.produto.nome if item.produto else None,
                "vinculado": item.vinculado,
                "confianca_vinculo": item.confianca_vinculo,
                "status": item.status
            }
            for item in nota.itens
        ]
    }


# ============================================================================
# SUGERIR SKU PARA NOVO PRODUTO
# ============================================================================

@router.get("/{nota_id}/itens/{item_id}/sugerir-sku")
def sugerir_sku_produto(
    nota_id: int,
    item_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Sugere SKU para criar novo produto baseado no fornecedor"""
    # Buscar nota e item
    nota = db.query(NotaEntrada).filter(NotaEntrada.id == nota_id).first()
    if not nota:
        raise HTTPException(status_code=404, detail="Nota nÃ£o encontrada")
    
    item = db.query(NotaEntradaItem).filter(
        NotaEntradaItem.id == item_id,
        NotaEntradaItem.nota_entrada_id == nota_id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item nÃ£o encontrado")
    
    # Gerar prefixo do fornecedor
    prefixo = gerar_prefixo_fornecedor(nota.fornecedor_nome)
    
    # Tentar usar cÃ³digo do produto como base
    sku_base = item.codigo_produto if item.codigo_produto else ""
    
    # SugestÃµes de SKU
    sugestoes = []
    
    # 1. CÃ³digo original (verificar se estÃ¡ livre)
    if sku_base:
        if not db.query(Produto).filter(Produto.codigo == sku_base).first():
            sugestoes.append({
                "sku": sku_base,
                "descricao": "CÃ³digo original do fornecedor",
                "disponivel": True
            })
        else:
            sugestoes.append({
                "sku": sku_base,
                "descricao": "CÃ³digo original do fornecedor",
                "disponivel": False
            })
    
    # 2. Prefixo + CÃ³digo
    if sku_base:
        sku_com_prefixo = f"{prefixo}-{sku_base}"
        disponivel = not db.query(Produto).filter(Produto.codigo == sku_com_prefixo).first()
        sugestoes.append({
            "sku": sku_com_prefixo,
            "descricao": f"Prefixo {prefixo} + cÃ³digo do fornecedor",
            "disponivel": disponivel
        })
    
    # 3. CÃ³digo + Sufixo
    if sku_base:
        sku_com_sufixo = f"{sku_base}-{prefixo}"
        disponivel = not db.query(Produto).filter(Produto.codigo == sku_com_sufixo).first()
        sugestoes.append({
            "sku": sku_com_sufixo,
            "descricao": f"CÃ³digo do fornecedor + sufixo {prefixo}",
            "disponivel": disponivel
        })
    
    # 4. CÃ³digo sequencial com prefixo
    contador = 1
    while contador <= 3:
        sku_sequencial = f"{prefixo}{contador:04d}"
        if not db.query(Produto).filter(Produto.codigo == sku_sequencial).first():
            sugestoes.append({
                "sku": sku_sequencial,
                "descricao": f"CÃ³digo sequencial com prefixo {prefixo}",
                "disponivel": True
            })
            break
        contador += 1
    
    return {
        "item_id": item.id,
        "descricao_item": item.descricao,
        "codigo_fornecedor": item.codigo_produto,
        "fornecedor": nota.fornecedor_nome,
        "prefixo_sugerido": prefixo,
        "sugestoes": sugestoes,
        "dados_produto": {
            "nome": item.descricao,
            "unidade": item.unidade,
            "preco_custo": item.valor_unitario,
            "ncm": item.ncm if hasattr(item, 'ncm') else None,
            "ean": item.ean if hasattr(item, 'ean') else None
        }
    }


# ============================================================================
# VINCULAR PRODUTO MANUALMENTE
# ============================================================================

@router.post("/{nota_id}/itens/{item_id}/vincular")
def vincular_produto(
    nota_id: int,
    item_id: int,
    produto_id: int = Query(..., description="ID do produto a vincular"),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Vincula item a um produto manualmente"""
    item = db.query(NotaEntradaItem).filter(
        NotaEntradaItem.id == item_id,
        NotaEntradaItem.nota_entrada_id == nota_id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item nÃ£o encontrado")
    
    produto = db.query(Produto).filter(Produto.id == produto_id).first()
    if not produto:
        raise HTTPException(status_code=404, detail="Produto nÃ£o encontrado")
    
    # Atualizar vinculaÃ§Ã£o
    foi_nao_vinculado = not item.vinculado
    
    item.produto_id = produto_id
    item.vinculado = True
    item.confianca_vinculo = 1.0  # Manual = 100%
    item.status = 'vinculado'
    
    # Vincular produto ao fornecedor da nota automaticamente
    nota = db.query(NotaEntrada).filter(NotaEntrada.id == nota_id).first()
    if nota and nota.fornecedor_id:
        # Verificar se jÃ¡ existe vÃ­nculo
        vinculo_existente = db.query(ProdutoFornecedor).filter(
            ProdutoFornecedor.produto_id == produto_id,
            ProdutoFornecedor.fornecedor_id == nota.fornecedor_id
        ).first()
        
        if not vinculo_existente:
            # Criar vÃ­nculo produto-fornecedor
            novo_vinculo = ProdutoFornecedor(
                produto_id=produto_id,
                fornecedor_id=nota.fornecedor_id,
                preco_custo=item.valor_unitario,
                e_principal=True,  # Primeiro fornecedor Ã© principal
                ativo=True
            )
            db.add(novo_vinculo)
            logger.info(f"âœ… Produto {produto_id} vinculado ao fornecedor {nota.fornecedor_id}")
        else:
            # Atualizar preÃ§o se jÃ¡ existir
            vinculo_existente.preco_custo = item.valor_unitario
            vinculo_existente.ativo = True
            logger.info(f"ðŸ”„ VÃ­nculo produto-fornecedor atualizado")
    
    # Atualizar contadores da nota
    if foi_nao_vinculado:
        nota.produtos_vinculados += 1
        nota.produtos_nao_vinculados -= 1
    
    db.commit()
    
    logger.info(f"âœ… Item {item_id} vinculado manualmente ao produto {produto.nome}")
    
    return {
        "message": "Produto vinculado com sucesso",
        "item_id": item.id,
        "produto_id": produto.id,
        "produto_nome": produto.nome
    }


# ============================================================================
# DESVINCULAR PRODUTO
# ============================================================================

@router.post("/{nota_id}/itens/{item_id}/desvincular")
def desvincular_produto(
    nota_id: int,
    item_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Remove vinculaÃ§Ã£o de um item com produto"""
    item = db.query(NotaEntradaItem).filter(
        NotaEntradaItem.id == item_id,
        NotaEntradaItem.nota_entrada_id == nota_id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item nÃ£o encontrado")
    
    if not item.produto_id:
        raise HTTPException(status_code=400, detail="Item nÃ£o estÃ¡ vinculado a nenhum produto")
    
    # Remover vinculaÃ§Ã£o
    item.produto_id = None
    item.vinculado = False
    item.confianca_vinculo = None
    item.status = 'pendente'
    
    # Atualizar contadores da nota
    nota = db.query(NotaEntrada).filter(NotaEntrada.id == nota_id).first()
    nota.produtos_vinculados -= 1
    nota.produtos_nao_vinculados += 1
    
    db.commit()
    
    logger.info(f"âŒ Item {item_id} desvinculado")
    
    return {
        "message": "Produto desvinculado com sucesso",
        "item_id": item.id
    }


# ============================================================================
# CONFIGURAR RATEIO DA NOTA (100% ONLINE, 100% LOJA, OU PARCIAL)
# ============================================================================

class RateioNotaRequest(BaseModel):
    tipo_rateio: str  # 'online', 'loja', 'parcial'


@router.post("/{nota_id}/rateio")
def configurar_rateio_nota(
    nota_id: int,
    rateio: RateioNotaRequest,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Configura tipo de rateio da nota inteira:
    - 'online': 100% online
    - 'loja': 100% loja fÃ­sica  
    - 'parcial': configurar por produto
    """
    current_user, tenant_id = user_and_tenant
    
    if rateio.tipo_rateio not in ['online', 'loja', 'parcial']:
        raise HTTPException(status_code=400, detail="Tipo de rateio invÃ¡lido. Use: online, loja ou parcial")
    
    nota = db.query(NotaEntrada).options(
        joinedload(NotaEntrada.itens)
    ).filter(
        NotaEntrada.id == nota_id,
        NotaEntrada.tenant_id == tenant_id
    ).first()
    
    if not nota:
        raise HTTPException(status_code=404, detail="Nota nÃ£o encontrada")
    
    nota.tipo_rateio = rateio.tipo_rateio
    
    if rateio.tipo_rateio == 'online':
        nota.percentual_online = 100
        nota.percentual_loja = 0
        nota.valor_online = nota.valor_total
        nota.valor_loja = 0
        
        # Zerar rateio dos itens (nÃ£o Ã© parcial)
        for item in nota.itens:
            item.quantidade_online = 0
            item.valor_online = 0
            
    elif rateio.tipo_rateio == 'loja':
        nota.percentual_online = 0
        nota.percentual_loja = 100
        nota.valor_online = 0
        nota.valor_loja = nota.valor_total
        
        # Zerar rateio dos itens
        for item in nota.itens:
            item.quantidade_online = 0
            item.valor_online = 0
            
    else:  # parcial
        # SerÃ¡ calculado quando configurar os itens
        nota.percentual_online = 0
        nota.percentual_loja = 100
        nota.valor_online = 0
        nota.valor_loja = nota.valor_total
    
    db.commit()
    db.refresh(nota)
    
    logger.info(f"ðŸ“Š Rateio da nota configurado: {rateio.tipo_rateio}")
    
    return {
        "message": "Tipo de rateio configurado com sucesso",
        "nota_id": nota.id,
        "tipo_rateio": nota.tipo_rateio,
        "percentual_online": nota.percentual_online,
        "percentual_loja": nota.percentual_loja,
        "valor_online": nota.valor_online,
        "valor_loja": nota.valor_loja
    }


# ============================================================================
# CONFIGURAR QUANTIDADE ONLINE DE UM ITEM (PARA RATEIO PARCIAL)
# ============================================================================

class RateioItemRequest(BaseModel):
    quantidade_online: float  # Quantidade que Ã© do online


@router.post("/{nota_id}/itens/{item_id}/rateio")
def configurar_rateio_item(
    nota_id: int,
    item_id: int,
    rateio: RateioItemRequest,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Configura quantidade do item que Ã© online (para rateio parcial)
    Sistema calcula automaticamente os % da nota
    """
    current_user, tenant_id = user_and_tenant
    
    # Buscar nota
    nota = db.query(NotaEntrada).options(
        joinedload(NotaEntrada.itens)
    ).filter(
        NotaEntrada.id == nota_id,
        NotaEntrada.tenant_id == tenant_id
    ).first()
    
    if not nota:
        raise HTTPException(status_code=404, detail="Nota nÃ£o encontrada")
    
    if nota.tipo_rateio != 'parcial':
        raise HTTPException(
            status_code=400, 
            detail="Nota nÃ£o estÃ¡ configurada como rateio parcial. Configure primeiro o tipo de rateio."
        )
    
    # Buscar item
    item = db.query(NotaEntradaItem).filter(
        NotaEntradaItem.id == item_id,
        NotaEntradaItem.nota_entrada_id == nota_id,
        NotaEntradaItem.tenant_id == tenant_id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item nÃ£o encontrado")
    
    # Validar quantidade
    if rateio.quantidade_online < 0:
        raise HTTPException(status_code=400, detail="Quantidade online nÃ£o pode ser negativa")
    
    if rateio.quantidade_online > item.quantidade:
        raise HTTPException(
            status_code=400, 
            detail=f"Quantidade online ({rateio.quantidade_online}) nÃ£o pode ser maior que a quantidade total ({item.quantidade})"
        )
    
    # Atualizar item
    item.quantidade_online = rateio.quantidade_online
    item.valor_online = rateio.quantidade_online * item.valor_unitario
    
    # Recalcular totais da nota
    valor_online_total = 0
    for it in nota.itens:
        if it.id == item_id:
            valor_online_total += item.valor_online
        else:
            valor_online_total += (it.valor_online or 0)
    
    nota.valor_online = valor_online_total
    nota.valor_loja = nota.valor_total - valor_online_total
    nota.percentual_online = (valor_online_total / nota.valor_total * 100) if nota.valor_total > 0 else 0
    nota.percentual_loja = 100 - nota.percentual_online
    
    db.commit()
    db.refresh(item)
    db.refresh(nota)
    
    logger.info(
        f"ðŸ“Š Rateio item configurado - {item.descricao}: "
        f"{item.quantidade_online}/{item.quantidade} online = R$ {item.valor_online:.2f}"
    )
    logger.info(
        f"ðŸ“Š Nota {nota.numero_nota}: {nota.percentual_online:.1f}% online (R$ {nota.valor_online:.2f}) | "
        f"{nota.percentual_loja:.1f}% loja (R$ {nota.valor_loja:.2f})"
    )
    
    return {
        "message": "Rateio do item configurado com sucesso",
        "item": {
            "id": item.id,
            "quantidade_total": item.quantidade,
            "quantidade_online": item.quantidade_online,
            "valor_online": item.valor_online
        },
        "nota_totais": {
            "valor_total": nota.valor_total,
            "valor_online": nota.valor_online,
            "valor_loja": nota.valor_loja,
            "percentual_online": round(nota.percentual_online, 2),
            "percentual_loja": round(nota.percentual_loja, 2)
        }
    }


# ============================================================================
# PREVIEW DE ENTRADA NO ESTOQUE - REVISÃƒO DE PREÃ‡OS
# ============================================================================

@router.get("/{nota_id}/preview-processamento")
def preview_processamento(
    nota_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Retorna preview da entrada com comparaÃ§Ã£o de custos e preÃ§os atuais
    """
    nota = db.query(NotaEntrada).options(
        joinedload(NotaEntrada.itens).joinedload(NotaEntradaItem.produto)
    ).filter(NotaEntrada.id == nota_id).first()
    
    if not nota:
        raise HTTPException(status_code=404, detail="Nota nÃ£o encontrada")
    
    if nota.produtos_nao_vinculados > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Existem {nota.produtos_nao_vinculados} produtos nÃ£o vinculados"
        )
    
    preview_itens = []
    
    for item in nota.itens:
        # Dados do item da NF (sempre presente)
        item_nf = {
            "item_id": item.id,
            "codigo_produto_nf": item.codigo_produto,
            "descricao_nf": item.descricao,
            "quantidade_nf": item.quantidade,
            "valor_unitario_nf": item.valor_unitario,
            "ean_nf": item.ean,
            "ncm_nf": item.ncm,
            "vinculado": item.vinculado,
            "confianca_vinculo": item.confianca_vinculo
        }
        
        # Dados do produto vinculado (se houver)
        produto_vinculado = None
        if item.produto_id:
            produto = item.produto
            custo_atual = produto.preco_custo or 0
            custo_novo = item.valor_unitario
            variacao_custo = ((custo_novo - custo_atual) / custo_atual * 100) if custo_atual > 0 else 0
            
            # Calcular margem atual
            preco_venda_atual = produto.preco_venda or 0
            if preco_venda_atual > 0 and custo_novo > 0:
                margem_atual = ((preco_venda_atual - custo_novo) / preco_venda_atual) * 100
            else:
                margem_atual = 0
            
            produto_vinculado = {
                "produto_id": produto.id,
                "produto_codigo": produto.codigo,
                "produto_nome": produto.nome,
                "produto_ean": produto.codigo_barras,
                "custo_anterior": custo_atual,
                "custo_novo": custo_novo,
                "variacao_custo_percentual": round(variacao_custo, 2),
                "preco_venda_atual": preco_venda_atual,
                "margem_atual": round(margem_atual, 2),
                "estoque_atual": produto.estoque_atual or 0
            }
        
        preview_itens.append({
            **item_nf,
            "produto_vinculado": produto_vinculado
        })
    
    return {
        "nota_id": nota.id,
        "numero_nota": nota.numero_nota,
        "fornecedor_nome": nota.fornecedor_nome,
        "valor_total": nota.valor_total,
        "itens": preview_itens
    }


# ============================================================================
# ATUALIZAR PREÃ‡OS DOS PRODUTOS
# ============================================================================

class AtualizarPrecoRequest(BaseModel):
    produto_id: int
    preco_venda: float

@router.post("/{nota_id}/atualizar-precos")
def atualizar_precos_produtos(
    nota_id: int,
    precos: List[AtualizarPrecoRequest],
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Atualiza preÃ§os de venda dos produtos antes de processar a nota
    Registra histÃ³rico de alteraÃ§Ãµes
    """
    nota = db.query(NotaEntrada).filter(NotaEntrada.id == nota_id).first()
    if not nota:
        raise HTTPException(status_code=404, detail="Nota nÃ£o encontrada")
    
    for preco_data in precos:
        produto = db.query(Produto).filter(Produto.id == preco_data.produto_id).first()
        if produto:
            # Capturar valores anteriores
            preco_venda_anterior = produto.preco_venda
            preco_custo_anterior = produto.preco_custo
            margem_anterior = ((preco_venda_anterior - preco_custo_anterior) / preco_venda_anterior * 100) if preco_venda_anterior > 0 else 0
            
            # Atualizar preÃ§o
            produto.preco_venda = preco_data.preco_venda
            
            # Calcular nova margem
            margem_nova = ((produto.preco_venda - produto.preco_custo) / produto.preco_venda * 100) if produto.preco_venda > 0 else 0
            
            # Registrar histÃ³rico se houve alteraÃ§Ã£o
            if preco_venda_anterior != produto.preco_venda:
                variacao_venda = ((produto.preco_venda - preco_venda_anterior) / preco_venda_anterior * 100) if preco_venda_anterior > 0 else 0
                
                historico = ProdutoHistoricoPreco(
                    produto_id=produto.id,
                    preco_custo_anterior=preco_custo_anterior,
                    preco_custo_novo=produto.preco_custo,
                    preco_venda_anterior=preco_venda_anterior,
                    preco_venda_novo=produto.preco_venda,
                    margem_anterior=margem_anterior,
                    margem_nova=margem_nova,
                    variacao_custo_percentual=0,  # Custo nÃ£o mudou neste caso
                    variacao_venda_percentual=variacao_venda,
                    motivo="nfe_revisao_precos",
                    nota_entrada_id=nota.id,
                    referencia=f"NF-e {nota.numero_nota} - RevisÃ£o de PreÃ§os",
                    observacoes=f"PreÃ§o ajustado de R$ {preco_venda_anterior:.2f} para R$ {produto.preco_venda:.2f} (margem: {margem_anterior:.1f}% â†’ {margem_nova:.1f}%)",
                    user_id=current_user.id
                )
                db.add(historico)
                
                logger.info(
                    f"ðŸ“Š HistÃ³rico registrado: {produto.nome} - "
                    f"PreÃ§o R$ {preco_venda_anterior:.2f} â†’ R$ {produto.preco_venda:.2f} "
                    f"({variacao_venda:+.2f}%)"
                )
    
    db.commit()
    
    return {"message": "PreÃ§os atualizados com sucesso"}


# ============================================================================
# DAR ENTRADA NO ESTOQUE
# ============================================================================

@router.post("/{nota_id}/processar")
def processar_entrada_estoque(
    nota_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Processa entrada no estoque de todos os itens vinculados
    """
    current_user, tenant_id = user_and_tenant
    logger.info(f"ðŸ“¦ Processando entrada no estoque - Nota {nota_id}")
    
    nota = db.query(NotaEntrada).options(
        joinedload(NotaEntrada.itens).joinedload(NotaEntradaItem.produto)
    ).filter(NotaEntrada.id == nota_id).first()
    
    if not nota:
        raise HTTPException(status_code=404, detail="Nota nÃ£o encontrada")
    
    if nota.entrada_estoque_realizada:
        raise HTTPException(
            status_code=400,
            detail="Entrada no estoque jÃ¡ foi realizada"
        )
    
    if nota.produtos_nao_vinculados > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Existem {nota.produtos_nao_vinculados} produtos nÃ£o vinculados. "
                   "Vincule todos os produtos antes de processar."
        )
    
    itens_processados = []
    
    # Processar cada item
    for item in nota.itens:
        if not item.produto_id:
            continue
        
        produto = item.produto
        
        # âœ… REATIVAR produto se estiver inativo
        if not produto.ativo:
            produto.ativo = True
            logger.info(f"  â™»ï¸  Produto reativado: {produto.codigo} - {produto.nome}")
        
        # âœ… ATUALIZAR dados fiscais do produto com informaÃ§Ãµes do XML
        produto.ncm = item.ncm
        produto.cfop = item.cfop
        produto.cest = item.cest if hasattr(item, 'cest') else None
        produto.origem = item.origem if hasattr(item, 'origem') else '0'
        produto.aliquota_icms = item.aliquota_icms if hasattr(item, 'aliquota_icms') else 0
        produto.aliquota_pis = item.aliquota_pis if hasattr(item, 'aliquota_pis') else 0
        produto.aliquota_cofins = item.aliquota_cofins if hasattr(item, 'aliquota_cofins') else 0
        
        # âœ… ATUALIZAR EAN se fornecido e vÃ¡lido
        if item.ean and item.ean != 'SEM GTIN' and item.ean.strip():
            produto.codigo_barras = item.ean
            logger.info(f"  ðŸ”– EAN atualizado: {produto.codigo} â†’ {item.ean}")
        
        # âœ… VINCULAR ao fornecedor da nota
        if nota.fornecedor_id:
            vinculo_existente = db.query(ProdutoFornecedor).filter(
                ProdutoFornecedor.produto_id == produto.id,
                ProdutoFornecedor.fornecedor_id == nota.fornecedor_id
            ).first()
            
            if not vinculo_existente:
                novo_vinculo = ProdutoFornecedor(
                    produto_id=produto.id,
                    fornecedor_id=nota.fornecedor_id,
                    preco_custo=item.valor_unitario,
                    e_principal=True,
                    ativo=True,
                    tenant_id=tenant_id
                )
                db.add(novo_vinculo)
                logger.info(f"  ðŸ”— Produto {produto.codigo} vinculado ao fornecedor {nota.fornecedor_id}")
            else:
                # Reativar vÃ­nculo se estiver inativo
                if not vinculo_existente.ativo:
                    vinculo_existente.ativo = True
                    logger.info(f"  â™»ï¸  VÃ­nculo de fornecedor reativado: {produto.codigo}")
                # Atualizar preÃ§o de custo no vÃ­nculo
                vinculo_existente.preco_custo = item.valor_unitario
        
        # Criar lote
        nome_lote = item.lote if item.lote else f"NF{nota.numero_nota}-{item.numero_item}"
        
        # Preparar data de validade (converter de date para datetime se necessÃ¡rio)
        data_validade = None
        if item.data_validade:
            from datetime import datetime as dt
            if isinstance(item.data_validade, dt):
                data_validade = item.data_validade
            else:
                # Ã‰ um objeto date, converter para datetime
                data_validade = dt.combine(item.data_validade, dt.min.time())
        
        lote = ProdutoLote(
            produto_id=produto.id,
            nome_lote=nome_lote,
            quantidade_inicial=item.quantidade,
            quantidade_disponivel=item.quantidade,
            custo_unitario=item.valor_unitario,
            data_fabricacao=None,
            data_validade=data_validade,
            ordem_entrada=int(datetime.utcnow().timestamp()),
            tenant_id=tenant_id
        )
        db.add(lote)
        db.flush()
        
        # Atualizar estoque
        estoque_anterior = produto.estoque_atual or 0
        produto.estoque_atual = estoque_anterior + item.quantidade
        
        # Atualizar preÃ§o de custo e registrar histÃ³rico
        preco_custo_anterior = produto.preco_custo
        preco_venda_anterior = produto.preco_venda
        margem_anterior = ((preco_venda_anterior - preco_custo_anterior) / preco_venda_anterior * 100) if preco_venda_anterior > 0 else 0
        
        alterou_custo = False
        if item.valor_unitario != preco_custo_anterior:
            produto.preco_custo = item.valor_unitario
            alterou_custo = True
        
        # Calcular margem nova
        margem_nova = ((produto.preco_venda - produto.preco_custo) / produto.preco_venda * 100) if produto.preco_venda > 0 else 0
        
        # Registrar histÃ³rico de preÃ§o se houve alteraÃ§Ã£o
        if alterou_custo:
            variacao_custo = ((produto.preco_custo - preco_custo_anterior) / preco_custo_anterior * 100) if preco_custo_anterior > 0 else 0
            
            historico = ProdutoHistoricoPreco(
                produto_id=produto.id,
                preco_custo_anterior=preco_custo_anterior,
                preco_custo_novo=produto.preco_custo,
                preco_venda_anterior=preco_venda_anterior,
                preco_venda_novo=produto.preco_venda,
                margem_anterior=margem_anterior,
                margem_nova=margem_nova,
                variacao_custo_percentual=variacao_custo,
                variacao_venda_percentual=0,  # PreÃ§o de venda nÃ£o mudou
                motivo="nfe_entrada",
                nota_entrada_id=nota.id,
                referencia=f"NF-e {nota.numero_nota}",
                observacoes=f"Entrada via NF-e: custo alterado de R$ {preco_custo_anterior:.2f} para R$ {produto.preco_custo:.2f}",
                user_id=current_user.id,
                tenant_id=tenant_id
            )
            db.add(historico)
            
            logger.info(
                f"  ðŸ“Š HistÃ³rico registrado: {produto.nome} - "
                f"Custo R$ {preco_custo_anterior:.2f} â†’ R$ {produto.preco_custo:.2f} "
                f"({variacao_custo:+.2f}%)"
            )
        
        # Registrar movimentaÃ§Ã£o
        movimentacao = EstoqueMovimentacao(
            produto_id=produto.id,
            lote_id=lote.id,
            tipo="entrada",
            motivo="compra",
            quantidade=item.quantidade,
            quantidade_anterior=estoque_anterior,
            quantidade_nova=produto.estoque_atual,
            custo_unitario=item.valor_unitario,
            valor_total=item.valor_total,
            documento=nota.chave_acesso,
            referencia_tipo="nota_entrada",
            referencia_id=nota.id,
            observacao=f"Entrada NF-e {nota.numero_nota} - {item.descricao}",
            user_id=current_user.id,
            tenant_id=tenant_id
        )
        db.add(movimentacao)
        
        # Atualizar status do item
        item.status = 'processado'
        
        itens_processados.append({
            "produto_id": produto.id,
            "produto_nome": produto.nome,
            "quantidade": item.quantidade,
            "lote": nome_lote,
            "estoque_atual": produto.estoque_atual
        })
        
        logger.info(
            f"  âœ… {produto.nome}: +{item.quantidade} unidades "
            f"(estoque: {estoque_anterior} â†’ {produto.estoque_atual})"
        )
    
    # Atualizar nota
    nota.status = 'processada'
    nota.entrada_estoque_realizada = True
    nota.processada_em = datetime.utcnow()
    
    # CRIAR CONTAS A PAGAR apÃ³s processar estoque
    contas_ids = []
    try:
        # Buscar dados do XML salvos na nota para pegar duplicatas
        import xml.etree.ElementTree as ET
        dados_xml = parse_nfe_xml(nota.xml_content)
        
        contas_ids = criar_contas_pagar_da_nota(nota, dados_xml, db, current_user.id, tenant_id)
        logger.info(f"ðŸ’° {len(contas_ids)} contas a pagar criadas")
    except Exception as e:
        logger.error(f"âš ï¸ Erro ao criar contas a pagar: {str(e)}")
        # NÃ£o abortar o processo, apenas avisar
    
    db.commit()
    
    logger.info(f"âœ… Entrada processada: {len(itens_processados)} produtos")
    
    return {
        "message": "Entrada no estoque realizada com sucesso",
        "nota_id": nota.id,
        "numero_nota": nota.numero_nota,
        "itens_processados": len(itens_processados),
        "contas_pagar_criadas": len(contas_ids),
        "detalhes": itens_processados
    }


# ============================================================================
# REVERTER/ESTORNAR ENTRADA NO ESTOQUE
# ============================================================================

@router.post("/{nota_id}/reverter")
def reverter_entrada_estoque(
    nota_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Reverte a entrada no estoque de uma nota jÃ¡ processada
    Remove estoque, exclui lotes, movimentaÃ§Ãµes e contas a pagar
    Reverte preÃ§os de custo dos produtos
    """
    current_user, tenant_id = user_and_tenant
    
    logger.info(f"ðŸ”„ Revertendo entrada no estoque - Nota {nota_id}")
    
    nota = db.query(NotaEntrada).options(
        joinedload(NotaEntrada.itens).joinedload(NotaEntradaItem.produto)
    ).filter(
        NotaEntrada.id == nota_id,
        NotaEntrada.tenant_id == tenant_id
    ).first()
    
    if not nota:
        raise HTTPException(status_code=404, detail="Nota nÃ£o encontrada")
    
    if not nota.entrada_estoque_realizada:
        raise HTTPException(
            status_code=400,
            detail="Esta nota ainda nÃ£o foi processada"
        )
    
    # REVERTER CONTAS A PAGAR vinculadas a esta nota
    logger.info("ðŸ’° Excluindo contas a pagar vinculadas...")
    contas_pagar = db.query(ContaPagar).filter(
        ContaPagar.nota_entrada_id == nota.id,
        ContaPagar.tenant_id == tenant_id
    ).all()
    
    contas_excluidas = 0
    for conta in contas_pagar:
        if conta.status != 'pago':
            db.delete(conta)
            contas_excluidas += 1
            logger.info(f"   âœ… Conta excluÃ­da: {conta.descricao} - R$ {float(conta.valor_final):.2f}")
        else:
            logger.warning(f"   âš ï¸ Conta JÃ PAGA nÃ£o pode ser excluÃ­da: {conta.descricao}")
    
    if contas_excluidas > 0:
        logger.info(f"âœ… Total de contas excluÃ­das: {contas_excluidas}")
    
    itens_revertidos = []
    
    try:
        # Reverter cada item
        for item in nota.itens:
            if not item.produto_id:
                continue
            
            produto = item.produto
            
            # Buscar lote criado para esta entrada
            nome_lote = item.lote if item.lote else f"NF{nota.numero_nota}-{item.numero_item}"
            lote = db.query(ProdutoLote).filter(
                ProdutoLote.produto_id == produto.id,
                ProdutoLote.nome_lote == nome_lote,
                ProdutoLote.tenant_id == tenant_id
            ).first()
            
            if lote:
                # REVERTER PREÃ‡O DE CUSTO se foi alterado
                historico_preco = db.query(ProdutoHistoricoPreco).filter(
                    ProdutoHistoricoPreco.produto_id == produto.id,
                    ProdutoHistoricoPreco.nota_entrada_id == nota.id,
                    ProdutoHistoricoPreco.motivo.in_(["nfe_entrada", "nfe_revisao_precos"]),
                    ProdutoHistoricoPreco.tenant_id == tenant_id
                ).first()
                
                if historico_preco:
                    # Reverter preÃ§os anteriores (com fallback para 0 se None)
                    preco_custo_revertido = historico_preco.preco_custo_anterior if historico_preco.preco_custo_anterior is not None else 0
                    preco_venda_revertido = historico_preco.preco_venda_anterior if historico_preco.preco_venda_anterior is not None else 0
                    
                    logger.info(f"  ðŸ’° Revertendo preÃ§o de custo: R$ {produto.preco_custo:.2f} â†’ R$ {preco_custo_revertido:.2f}")
                    produto.preco_custo = preco_custo_revertido
                    produto.preco_venda = preco_venda_revertido
                    
                    # Excluir histÃ³rico
                    db.delete(historico_preco)
                
                # Remover quantidade do estoque
                estoque_anterior = produto.estoque_atual or 0
                produto.estoque_atual = max(0, estoque_anterior - item.quantidade)
                
                # Registrar movimentaÃ§Ã£o de estorno
                movimentacao_estorno = EstoqueMovimentacao(
                    produto_id=produto.id,
                    lote_id=lote.id,
                    tipo="saida",
                    motivo="ajuste",
                    quantidade=item.quantidade,
                    quantidade_anterior=estoque_anterior,
                    quantidade_nova=produto.estoque_atual,
                    custo_unitario=item.valor_unitario,
                    valor_total=item.valor_total,
                    documento=nota.chave_acesso,
                    referencia_tipo="estorno_nota_entrada",
                    referencia_id=nota.id,
                    observacao=f"Estorno NF-e {nota.numero_nota} - {item.descricao}",
                    user_id=current_user.id,
                    tenant_id=tenant_id
                )
                db.add(movimentacao_estorno)
                
                # Excluir lote
                db.delete(lote)
                
                itens_revertidos.append({
                    "produto_id": produto.id,
                    "produto_nome": produto.nome,
                    "quantidade_removida": item.quantidade,
                    "estoque_atual": produto.estoque_atual
                })
                
                logger.info(
                    f"  â†©ï¸  {produto.nome}: -{item.quantidade} unidades "
                    f"(estoque: {estoque_anterior} â†’ {produto.estoque_atual})"
                )
            
            # Restaurar status do item
            item.status = 'vinculado'
        
        # Atualizar status da nota
        nota.status = 'pendente'
        nota.entrada_estoque_realizada = False
        nota.processada_em = None
        
        db.commit()
        
        logger.info(f"âœ… Entrada revertida: {len(itens_revertidos)} produtos")
        
        return {
            "message": "Entrada no estoque revertida com sucesso",
            "nota_id": nota.id,
            "numero_nota": nota.numero_nota,
            "itens_revertidos": len(itens_revertidos),
            "detalhes": itens_revertidos
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"âŒ Erro ao reverter entrada: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao reverter entrada: {str(e)}")


# ============================================================================
# SUGERIR SKU PARA PRODUTO NOVO
# ============================================================================

@router.get("/{nota_id}/itens/{item_id}/sugerir-sku")
def sugerir_sku(
    nota_id: int,
    item_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Sugere SKU para produto baseado no cÃ³digo do fornecedor
    PadrÃ£o: PREFIXO_FORNECEDOR-CODIGO_FORNECEDOR
    """
    # Buscar nota e item
    nota = db.query(NotaEntrada).filter(NotaEntrada.id == nota_id).first()
    if not nota:
        raise HTTPException(status_code=404, detail="Nota nÃ£o encontrada")
    
    item = db.query(NotaEntradaItem).filter(
        NotaEntradaItem.id == item_id,
        NotaEntradaItem.nota_entrada_id == nota_id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item nÃ£o encontrado")
    
    # Buscar fornecedor
    fornecedor = db.query(Cliente).filter(Cliente.id == nota.fornecedor_id).first() if nota.fornecedor_id else None
    
    # Gerar prefixo do fornecedor
    if fornecedor:
        prefixo = gerar_prefixo_fornecedor(fornecedor.nome)
    else:
        prefixo = "PROD"
    
    # CÃ³digo base do produto
    codigo_base = item.codigo_produto or item.descricao[:10].upper().replace(" ", "")
    
    # SKU proposto
    sku_proposto = f"{prefixo}-{codigo_base}"
    
    logger.info(f"ðŸ·ï¸ SugestÃ£o de SKU:")
    logger.info(f"   - Prefixo: {prefixo}")
    logger.info(f"   - CÃ³digo base: {codigo_base}")
    logger.info(f"   - SKU proposto: {sku_proposto}")
    
    # Verificar se jÃ¡ existe
    produto_existente = db.query(Produto).filter(Produto.codigo == sku_proposto).first()
    
    sugestoes = []
    
    if produto_existente:
        # Gerar sugestÃµes alternativas
        for i in range(1, 6):
            sku_alternativo = f"{prefixo}-{codigo_base}-V{i}"
            existe = db.query(Produto).filter(Produto.codigo == sku_alternativo).first()
            if not existe:
                sugestoes.append({
                    "sku": sku_alternativo,
                    "disponivel": True,
                    "padrao": i == 1
                })
        
        return {
            "sku_proposto": sku_proposto,
            "ja_existe": True,
            "produto_existente": {
                "id": produto_existente.id,
                "codigo": produto_existente.codigo,
                "nome": produto_existente.nome
            },
            "sugestoes": sugestoes,
            "codigo_fornecedor": item.codigo_produto,
            "prefixo_fornecedor": prefixo
        }
    else:
        return {
            "sku_proposto": sku_proposto,
            "ja_existe": False,
            "sugestoes": [
                {
                    "sku": sku_proposto,
                    "disponivel": True,
                    "padrao": True
                }
            ],
            "codigo_fornecedor": item.codigo_produto,
            "prefixo_fornecedor": prefixo
        }


# ============================================================================
# CRIAR PRODUTO A PARTIR DO ITEM DA NOTA
# ============================================================================

class CriarProdutoRequest(BaseModel):
    sku: str
    nome: str
    descricao: Optional[str] = None
    preco_custo: float
    preco_venda: float
    margem_lucro: Optional[float] = None
    categoria_id: Optional[int] = None
    marca_id: Optional[int] = None
    estoque_minimo: Optional[int] = 10
    estoque_maximo: Optional[int] = 100


@router.post("/{nota_id}/itens/{item_id}/criar-produto")
def criar_produto_from_item(
    nota_id: int,
    item_id: int,
    dados: CriarProdutoRequest,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Cria um novo produto a partir do item da nota
    ATUALIZADO: Corrigido para usar descricao_curta e descricao_completa
    """
    current_user, tenant_id = user_and_tenant
    
    logger.info(f"ðŸ”¨ Criando produto: {dados.sku} - {dados.nome}")
    
    # Buscar nota e item
    nota = db.query(NotaEntrada).filter(NotaEntrada.id == nota_id).first()
    if not nota:
        raise HTTPException(status_code=404, detail="Nota nÃ£o encontrada")
    
    item = db.query(NotaEntradaItem).filter(
        NotaEntradaItem.id == item_id,
        NotaEntradaItem.nota_entrada_id == nota_id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item nÃ£o encontrado")
    
    # Verificar se SKU jÃ¡ existe
    produto_existente = db.query(Produto).filter(Produto.codigo == dados.sku).first()
    
    # Se existir produto ativo, vincular ao item automaticamente
    if produto_existente and produto_existente.ativo:
        logger.info(f"âœ… Produto jÃ¡ existe e estÃ¡ ativo: {produto_existente.codigo} - {produto_existente.nome}")
        
        # Vincular ao item da nota
        item.produto_id = produto_existente.id
        item.vinculado = True
        item.confianca_vinculo = 1.0
        item.status = 'vinculado'
        
        # IMPORTANTE: Flush antes de contar para garantir que o produto_id esteja no banco
        db.flush()
        
        # Atualizar contadores da nota
        nota.produtos_vinculados = db.query(NotaEntradaItem).filter(
            NotaEntradaItem.nota_entrada_id == nota_id,
            NotaEntradaItem.produto_id.isnot(None)
        ).count()
        
        nota.produtos_nao_vinculados = db.query(NotaEntradaItem).filter(
            NotaEntradaItem.nota_entrada_id == nota_id,
            NotaEntradaItem.produto_id.is_(None)
        ).count()
        
        db.commit()
        db.refresh(item)
        db.refresh(nota)
        db.refresh(produto_existente)
        
        return {
            "message": "Produto jÃ¡ existia e foi vinculado com sucesso",
            "produto": {
                "id": produto_existente.id,
                "codigo": produto_existente.codigo,
                "nome": produto_existente.nome,
                "descricao_curta": produto_existente.descricao_curta,
                "descricao_completa": produto_existente.descricao_completa,
                "preco_custo": produto_existente.preco_custo,
                "preco_venda": produto_existente.preco_venda
            },
            "item_vinculado": True,
            "produto_ja_existia": True
        }
    
    # Se existir produto inativo, reativar e atualizar
    if produto_existente and not produto_existente.ativo:
        try:
            # Preparar descriÃ§Ãµes
            descricao_texto = dados.descricao or item.descricao or ''
            descricao_curta = descricao_texto[:100] if descricao_texto else ''
            descricao_completa = descricao_texto
            
            # Atualizar produto existente com TODOS os dados do XML
            produto_existente.nome = dados.nome
            produto_existente.descricao_curta = descricao_curta
            produto_existente.descricao_completa = descricao_completa
            produto_existente.preco_custo = dados.preco_custo
            produto_existente.preco_venda = dados.preco_venda
            produto_existente.categoria_id = dados.categoria_id
            produto_existente.marca_id = dados.marca_id
            
            # DADOS FISCAIS DO XML
            produto_existente.ncm = item.ncm
            produto_existente.cfop = item.cfop
            produto_existente.cest = item.cest if hasattr(item, 'cest') else None
            produto_existente.origem = item.origem if hasattr(item, 'origem') else '0'
            produto_existente.aliquota_icms = item.aliquota_icms if hasattr(item, 'aliquota_icms') else 0
            produto_existente.aliquota_pis = item.aliquota_pis if hasattr(item, 'aliquota_pis') else 0
            produto_existente.aliquota_cofins = item.aliquota_cofins if hasattr(item, 'aliquota_cofins') else 0
            produto_existente.codigo_barras = item.ean if item.ean and item.ean != 'SEM GTIN' else None
            
            # ESTOQUE
            produto_existente.estoque_minimo = dados.estoque_minimo
            produto_existente.estoque_maximo = dados.estoque_maximo
            produto_existente.unidade = item.unidade
            produto_existente.controle_lote = True  # Sempre ativar controle de lote
            produto_existente.ativo = True
            produto_existente.user_id = current_user.id
            
            db.flush()
            
            # Vincular ao item da nota
            item.produto_id = produto_existente.id
            item.vinculado = True
            item.confianca_vinculo = 1.0
            item.status = 'vinculado'
            
            # Vincular produto ao fornecedor da nota automaticamente
            if nota.fornecedor_id:
                vinculo_existente = db.query(ProdutoFornecedor).filter(
                    ProdutoFornecedor.produto_id == produto_existente.id,
                    ProdutoFornecedor.fornecedor_id == nota.fornecedor_id
                ).first()
                
                if not vinculo_existente:
                    novo_vinculo = ProdutoFornecedor(
                        produto_id=produto_existente.id,
                        fornecedor_id=nota.fornecedor_id,
                        preco_custo=dados.preco_custo,
                        e_principal=True,
                        ativo=True,
                        tenant_id=tenant_id
                    )
                    db.add(novo_vinculo)
                    logger.info(f"âœ… Produto reativado {produto_existente.id} vinculado ao fornecedor {nota.fornecedor_id}")
                else:
                    vinculo_existente.preco_custo = dados.preco_custo
                    vinculo_existente.ativo = True
            
            # Atualizar contadores da nota
            nota.produtos_vinculados = db.query(NotaEntradaItem).filter(
                NotaEntradaItem.nota_entrada_id == nota_id,
                NotaEntradaItem.produto_id.isnot(None)
            ).count()
            
            nota.produtos_nao_vinculados = db.query(NotaEntradaItem).filter(
                NotaEntradaItem.nota_entrada_id == nota_id,
                NotaEntradaItem.produto_id.is_(None)
            ).count()
            
            db.commit()
            db.refresh(produto_existente)
            
            logger.info(f"âœ… Produto reativado e atualizado: {produto_existente.codigo} - {produto_existente.nome}")
            
            return {
                "message": "Produto reativado e vinculado com sucesso",
                "produto": {
                    "id": produto_existente.id,
                    "codigo": produto_existente.codigo,
                    "nome": produto_existente.nome,
                    "descricao_curta": produto_existente.descricao_curta,
                    "descricao_completa": produto_existente.descricao_completa,
                    "preco_custo": produto_existente.preco_custo,
                    "preco_venda": produto_existente.preco_venda
                },
                "item_vinculado": True
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"âŒ Erro ao reativar produto: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Erro ao reativar produto: {str(e)}")
    
    # Criar produto novo e vincular
    try:
        # Preparar descriÃ§Ãµes
        descricao_texto = dados.descricao or item.descricao or ''
        descricao_curta = descricao_texto[:100] if descricao_texto else ''
        descricao_completa = descricao_texto
        
        novo_produto = Produto(
            codigo=dados.sku,
            nome=dados.nome,
            descricao_curta=descricao_curta,
            descricao_completa=descricao_completa,
            preco_custo=dados.preco_custo,
            preco_venda=dados.preco_venda,
            categoria_id=dados.categoria_id,
            marca_id=dados.marca_id,
            
            # DADOS FISCAIS DO XML
            ncm=item.ncm,
            cfop=item.cfop,
            cest=item.cest if hasattr(item, 'cest') else None,
            origem=item.origem if hasattr(item, 'origem') else '0',
            aliquota_icms=item.aliquota_icms if hasattr(item, 'aliquota_icms') else 0,
            aliquota_pis=item.aliquota_pis if hasattr(item, 'aliquota_pis') else 0,
            aliquota_cofins=item.aliquota_cofins if hasattr(item, 'aliquota_cofins') else 0,
            codigo_barras=item.ean if item.ean and item.ean != 'SEM GTIN' else None,
            
            # ESTOQUE
            estoque_minimo=dados.estoque_minimo,
            estoque_maximo=dados.estoque_maximo,
            estoque_atual=0,
            unidade=item.unidade,
            controle_lote=True,  # Sempre ativar controle de lote para produtos do XML
            ativo=True,
            user_id=current_user.id,
            tenant_id=tenant_id
        )
        
        db.add(novo_produto)
        db.flush()
        
        # Vincular automaticamente ao item da nota
        item.produto_id = novo_produto.id
        item.vinculado = True
        item.confianca_vinculo = 1.0
        item.status = 'vinculado'
        
        # Vincular produto ao fornecedor da nota automaticamente
        if nota.fornecedor_id:
            novo_vinculo = ProdutoFornecedor(
                produto_id=novo_produto.id,
                fornecedor_id=nota.fornecedor_id,
                preco_custo=dados.preco_custo,
                e_principal=True,  # Primeiro fornecedor Ã© principal
                ativo=True,
                tenant_id=tenant_id
            )
            db.add(novo_vinculo)
            logger.info(f"âœ… Novo produto {novo_produto.id} vinculado ao fornecedor {nota.fornecedor_id}")
        
        # IMPORTANTE: Flush antes de contar para garantir que o produto_id esteja no banco
        db.flush()
        
        # Atualizar contadores da nota
        nota.produtos_vinculados = db.query(NotaEntradaItem).filter(
            NotaEntradaItem.nota_entrada_id == nota_id,
            NotaEntradaItem.produto_id.isnot(None)
        ).count()
        
        nota.produtos_nao_vinculados = db.query(NotaEntradaItem).filter(
            NotaEntradaItem.nota_entrada_id == nota_id,
            NotaEntradaItem.produto_id.is_(None)
        ).count()
        
        db.commit()
        db.refresh(novo_produto)
        db.refresh(item)
        db.refresh(nota)
        
    except Exception as e:
        db.rollback()
        logger.error(f"âŒ Erro ao criar produto: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao criar produto: {str(e)}")
    
    logger.info(f"âœ… Produto criado a partir da nota: {novo_produto.codigo} - {novo_produto.nome}")
    
    return {
        "message": "Produto criado e vinculado com sucesso",
        "produto": {
            "id": novo_produto.id,
            "codigo": novo_produto.codigo,
            "nome": novo_produto.nome,
            "descricao_curta": novo_produto.descricao_curta,
            "descricao_completa": novo_produto.descricao_completa,
            "preco_custo": novo_produto.preco_custo,
            "preco_venda": novo_produto.preco_venda
        },
        "item_vinculado": True
    }


# ============================================================================
# EXCLUIR NOTA
# ============================================================================

@router.delete("/{nota_id}")
def excluir_nota(
    nota_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Exclui uma nota de entrada e seus itens (cascade)"""
    nota = db.query(NotaEntrada).filter(NotaEntrada.id == nota_id).first()
    
    if not nota:
        raise HTTPException(status_code=404, detail="Nota nÃ£o encontrada")
    
    # Verificar se jÃ¡ teve entrada no estoque
    if nota.entrada_estoque_realizada:
        raise HTTPException(
            status_code=400, 
            detail="NÃ£o Ã© possÃ­vel excluir nota que jÃ¡ teve entrada no estoque"
        )
    
    numero_nota = nota.numero_nota
    total_itens = len(nota.itens)
    
    # Excluir contas a pagar vinculadas (se existirem)
    contas_pagar = db.query(ContaPagar).filter(
        ContaPagar.nota_entrada_id == nota.id
    ).all()
    
    contas_excluidas = 0
    pagamentos_excluidos = 0
    for conta in contas_pagar:
        # Excluir pagamentos da conta antes de excluir a conta
        from app.financeiro_models import Pagamento
        pagamentos = db.query(Pagamento).filter(Pagamento.conta_pagar_id == conta.id).all()
        for pagamento in pagamentos:
            db.delete(pagamento)
            pagamentos_excluidos += 1
        
        db.delete(conta)
        contas_excluidas += 1
    
    if contas_excluidas > 0:
        logger.info(f"ðŸ—‘ï¸ {contas_excluidas} contas a pagar e {pagamentos_excluidos} pagamentos excluÃ­dos junto com a nota")
    
    # Excluir nota (cascade deleta os itens automaticamente)
    db.delete(nota)
    db.commit()
    
    logger.info(f"ðŸ—‘ï¸ Nota excluÃ­da: {numero_nota} ({total_itens} itens)")
    
    return {
        "message": "Nota excluída com sucesso",
        "numero_nota": numero_nota,
        "itens_excluidos": total_itens,
        "contas_pagar_excluidas": contas_excluidas
    }


