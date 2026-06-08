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
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query, Form
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, desc
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import xml.etree.ElementTree as ET
import re

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
from .fiscal_patterns import aplicar_inteligencia_fiscal, identificar_padrao_fiscal
from .notas_entrada_pdf_parser import (
    PDFEntradaFornecedor,
    build_pdf_synthetic_nfe_xml,
    extract_pdf_text,
    parse_pedido_pdf_text,
)
from .notas_entrada.conferencia import (
    ACOES_CONFERENCIA_VALIDAS,
    CONFERENCIA_STATUS_COM_DIVERGENCIA,
    CONFERENCIA_STATUS_NAO_INICIADA,
    CONFERENCIA_STATUS_SEM_DIVERGENCIA,
    _data_para_datetime,
    _extrair_lote_validade_info_adicional,
    _mapear_lotes_rastro_xml,
    _montar_lotes_entrada_item,
    _montar_payload_nota,
    _normalizar_custo_unitario_override,
    _normalizar_texto_curto,
    _obter_acao_conferencia,
    _obter_override_mapa,
    _parse_data_validade_texto,
    _quantidades_conferencia_item,
    _resumir_conferencia_nota,
    _round_quantity,
    _serializar_conferencia_item,
    _status_conferencia_item,
)
from .notas_entrada.fiscal import (
    COST_COMPONENT_KEYS,
    TOTAL_PRECISION,
    UNIT_PRECISION,
    ZERO_DECIMAL,
    _decimal_to_float,
    _round_decimal,
    _to_decimal,
    calcular_composicao_custos_nota,
    calcular_quantidade_custo_efetivos,
    detectar_multiplicador_pack,
    extrair_resumo_fiscal_xml,
)
from .notas_entrada.financeiro import (
    _obter_tipo_produto_revenda_id,
    criar_contas_pagar_da_nota,
)
from .notas_entrada.fornecedores import (
    criar_fornecedor_automatico,
    gerar_prefixo_fornecedor,
)
from .notas_entrada.produtos import (
    _aplicar_codigos_barras_item_no_produto,
    _aplicar_dados_fiscais_item_no_produto,
    _buscar_produto_por_codigo_global,
    _codigo_barras_valido_nf,
    _codigos_barras_nf,
    _gerar_candidatos_sku_disponiveis,
    _montar_divergencia_codigo_barras_item,
    _montar_sugestao_sku_produto,
    _produto_pertence_ao_tenant,
    calcular_similaridade,
    encontrar_produto_similar,
    gerar_sku_automatico,
    normalizar_codigo_barras,
    obter_detalhe_vinculo_item,
)
from .services.produto_service import normalizar_sku_produto

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
    conferencia_status: Optional[str] = "nao_iniciada"
    divergencias_count: Optional[int] = 0
    
    model_config = {"from_attributes": True}


class ConferenciaItemPayload(BaseModel):
    item_id: int
    quantidade_conferida: float
    quantidade_avariada: float = 0
    observacao_conferencia: Optional[str] = None
    acao_sugerida: Optional[str] = "sem_acao"


class ConferenciaNotaPayload(BaseModel):
    itens: List[ConferenciaItemPayload]
    observacao_geral: Optional[str] = None


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
            ean_tributario = prod.find('nfe:cEANTrib', ns).text if prod.find('nfe:cEANTrib', ns) is not None else ''
            
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
            
            # Se nao encontrar em rastro, tentar informacoes adicionais do item.
            # Na NF-e, infAdProd costuma ser filho de <det>, nao de <prod>.
            if not lote or not data_validade:
                inf_ad_prod = det.find('nfe:infAdProd', ns)
                if inf_ad_prod is None:
                    inf_ad_prod = prod.find('nfe:infAdProd', ns)

                if inf_ad_prod is not None and inf_ad_prod.text:
                    lote_info, validade_info = _extrair_lote_validade_info_adicional(
                        inf_ad_prod.text
                    )
                    if not lote and lote_info:
                        lote = lote_info
                    if not data_validade and validade_info:
                        data_validade = validade_info
            
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
                'ean_tributario': ean_tributario,
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
            Cliente.tenant_id == tenant_id,
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
            produto, confianca, foi_inativo, origem_vinculo, referencia_vinculo = encontrar_produto_similar(
                item_data['descricao'],
                item_data['codigo_produto'],
                db,
                tenant_id=tenant_id,
                fornecedor_id=fornecedor.id if fornecedor else None,
                ean=item_data.get('ean'),
                ean_tributario=item_data.get('ean_tributario'),
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
                detalhe_match = ""
                if origem_vinculo and referencia_vinculo:
                    detalhe_match = f" [match por {origem_vinculo}: {referencia_vinculo}]"
                logger.info(
                    f"  âœ… {item_data['descricao'][:50]} â†’ "
                    f"{produto.nome} (confianÃ§a: {confianca:.0%}){detalhe_match}{status_msg}"
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
                ean_tributario=item_data.get('ean_tributario'),
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
# UPLOAD DE PDF DE PEDIDO/ROMANEIO
# ============================================================================

@router.post("/upload-pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    fornecedor_id: int = Form(...),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Upload de pedido/romaneio PDF e entrada pelo fluxo existente."""
    current_user, tenant_id = user_and_tenant
    filename = file.filename or ""

    logger.info(f"Upload de PDF de entrada - Arquivo: {filename}")
    logger.info(f"   - Fornecedor ID: {fornecedor_id}")
    logger.info(f"   - Usuario: {current_user.email} (ID: {current_user.id})")

    try:
        if not filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Arquivo deve ser PDF")

        fornecedor = db.query(Cliente).filter(
            Cliente.id == fornecedor_id,
            Cliente.tenant_id == tenant_id,
            Cliente.tipo_cadastro == "fornecedor",
            Cliente.ativo == True,
        ).first()

        if not fornecedor:
            raise HTTPException(status_code=404, detail="Fornecedor ativo nao encontrado")

        pdf_content = await file.read()
        if not pdf_content:
            raise HTTPException(status_code=400, detail="PDF vazio")

        try:
            pdf_text = extract_pdf_text(pdf_content)
            pedido_pdf = parse_pedido_pdf_text(pdf_text)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        fornecedor_pdf = PDFEntradaFornecedor(
            id=fornecedor.id,
            nome=fornecedor.razao_social or fornecedor.nome_fantasia or fornecedor.nome,
            cnpj=fornecedor.cnpj or fornecedor.cpf or "",
        )
        xml_str = build_pdf_synthetic_nfe_xml(
            pedido_pdf,
            fornecedor_pdf,
            tenant_id=tenant_id,
        )
        dados_nfe = parse_nfe_xml(xml_str)

        nota_existente = db.query(NotaEntrada).filter(
            NotaEntrada.chave_acesso == dados_nfe["chave_acesso"]
        ).first()

        if nota_existente:
            raise HTTPException(
                status_code=400,
                detail=f"PDF ja importado como entrada (ID: {nota_existente.id})",
            )

        nota = NotaEntrada(
            numero_nota=dados_nfe["numero_nota"],
            serie=dados_nfe["serie"],
            chave_acesso=dados_nfe["chave_acesso"],
            fornecedor_cnpj=dados_nfe["fornecedor_cnpj"],
            fornecedor_nome=dados_nfe["fornecedor_nome"],
            fornecedor_id=fornecedor.id,
            data_emissao=dados_nfe["data_emissao"],
            data_entrada=datetime.utcnow(),
            valor_produtos=dados_nfe["valor_produtos"],
            valor_frete=dados_nfe["valor_frete"],
            valor_desconto=dados_nfe["valor_desconto"],
            valor_total=dados_nfe["valor_total"],
            xml_content=xml_str,
            status="pendente",
            user_id=current_user.id,
            tenant_id=tenant_id,
        )

        db.add(nota)
        db.flush()

        vinculados = 0
        nao_vinculados = 0
        produtos_reativados = 0

        for item_data in dados_nfe["itens"]:
            produto, confianca, foi_inativo, origem_vinculo, referencia_vinculo = encontrar_produto_similar(
                item_data["descricao"],
                item_data["codigo_produto"],
                db,
                tenant_id=tenant_id,
                fornecedor_id=fornecedor.id,
                ean=item_data.get("ean"),
                ean_tributario=item_data.get("ean_tributario"),
            )

            if produto:
                vinculados += 1
                if foi_inativo:
                    produtos_reativados += 1
                produto_id = produto.id
                vinculado = True
                item_status = "vinculado"

                if not produto.codigo or produto.codigo.strip() == "":
                    novo_sku = gerar_sku_automatico("PROD", db, current_user.id)
                    produto.codigo = novo_sku

                detalhe_match = ""
                if origem_vinculo and referencia_vinculo:
                    detalhe_match = f" [match por {origem_vinculo}: {referencia_vinculo}]"
                logger.info(
                    f"PDF item vinculado: {item_data['descricao'][:50]} -> "
                    f"{produto.nome} (confianca: {confianca:.0%}){detalhe_match}"
                )
            else:
                nao_vinculados += 1
                produto_id = None
                vinculado = False
                item_status = "nao_vinculado"
                confianca = 0

            item = NotaEntradaItem(
                nota_entrada_id=nota.id,
                numero_item=item_data["numero_item"],
                codigo_produto=item_data.get("codigo_produto"),
                descricao=item_data["descricao"],
                ncm=item_data.get("ncm"),
                cest=item_data.get("cest"),
                cfop=item_data.get("cfop"),
                origem=item_data.get("origem"),
                aliquota_icms=item_data.get("aliquota_icms"),
                aliquota_pis=item_data.get("aliquota_pis"),
                aliquota_cofins=item_data.get("aliquota_cofins"),
                unidade=item_data.get("unidade") or "UN",
                quantidade=item_data["quantidade"],
                valor_unitario=item_data["valor_unitario"],
                valor_total=item_data["valor_total"],
                ean=item_data.get("ean"),
                ean_tributario=item_data.get("ean_tributario"),
                lote=item_data.get("lote"),
                data_validade=item_data.get("data_validade"),
                produto_id=produto_id,
                vinculado=vinculado,
                confianca_vinculo=confianca,
                status=item_status,
                tenant_id=tenant_id,
            )
            db.add(item)

        nota.produtos_vinculados = vinculados
        nota.produtos_nao_vinculados = nao_vinculados

        db.commit()
        db.refresh(nota)

        avisos = [
            "PDF importado como pedido/romaneio; nao e NF-e validada pela SEFAZ.",
            "O PDF nao traz chave fiscal real, CFOP, NCM, impostos ou lotes. Revise os produtos antes de processar.",
            "Produtos ja cadastrados preservam os dados fiscais existentes quando o PDF nao trouxer essas informacoes.",
        ]

        return {
            "message": "PDF processado com sucesso",
            "origem_documento": "pdf",
            "nota_id": nota.id,
            "numero_nota": nota.numero_nota,
            "chave_acesso": nota.chave_acesso,
            "fornecedor": nota.fornecedor_nome,
            "fornecedor_id": nota.fornecedor_id,
            "fornecedor_criado_automaticamente": False,
            "valor_total": nota.valor_total,
            "itens_total": len(dados_nfe["itens"]),
            "produtos_vinculados": vinculados,
            "produtos_nao_vinculados": nao_vinculados,
            "produtos_reativados": produtos_reativados,
            "avisos": avisos,
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"Erro inesperado no upload PDF: {str(e)}")
        logger.error(f"   - Tipo: {type(e).__name__}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao processar PDF: {str(e)}")


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
    current_user, tenant_id = user_and_tenant

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
                Cliente.cnpj == dados_nfe['fornecedor_cnpj'],
                Cliente.tenant_id == tenant_id,
            ).first()
            
            fornecedor_criado = False
            if not fornecedor:
                fornecedor, fornecedor_criado = criar_fornecedor_automatico(dados_nfe, db, current_user, tenant_id)
            
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
                user_id=current_user.id,
                tenant_id=tenant_id
            )
            
            db.add(nota)
            db.flush()
            
            # Processar itens com matching
            vinculados = 0
            nao_vinculados = 0
            produtos_reativados = 0
            
            for item_data in dados_nfe['itens']:
                produto, confianca, foi_reativado, _, _ = encontrar_produto_similar(
                    item_data['descricao'],
                    item_data['codigo_produto'],
                    db,
                    tenant_id=tenant_id,
                    fornecedor_id=fornecedor.id if fornecedor else None,
                    ean=item_data.get('ean'),
                    ean_tributario=item_data.get('ean_tributario'),
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
                    ean_tributario=item_data.get('ean_tributario'),
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
    
    query = db.query(NotaEntrada).options(joinedload(NotaEntrada.itens)).filter(NotaEntrada.tenant_id == tenant_id)
    
    if status:
        query = query.filter(NotaEntrada.status == status)
    if fornecedor_id:
        query = query.filter(NotaEntrada.fornecedor_id == fornecedor_id)
    
    query = query.order_by(desc(NotaEntrada.data_entrada))
    
    total = query.count()
    notas = query.offset(offset).limit(limit).all()
    
    logger.info(f"ðŸ“‹ {len(notas)} notas encontradas (total: {total})")
    
    respostas = []
    for nota in notas:
        conferencia = _resumir_conferencia_nota(nota)
        respostas.append(
            NotaEntradaResponse.model_validate(
                {
                    "id": nota.id,
                    "numero_nota": nota.numero_nota,
                    "serie": nota.serie,
                    "chave_acesso": nota.chave_acesso,
                    "fornecedor_nome": nota.fornecedor_nome,
                    "fornecedor_cnpj": nota.fornecedor_cnpj,
                    "fornecedor_id": nota.fornecedor_id,
                    "data_emissao": nota.data_emissao,
                    "valor_total": nota.valor_total,
                    "status": nota.status,
                    "produtos_vinculados": nota.produtos_vinculados,
                    "produtos_nao_vinculados": nota.produtos_nao_vinculados,
                    "entrada_estoque_realizada": nota.entrada_estoque_realizada,
                    "conferencia_status": conferencia["status"],
                    "divergencias_count": conferencia["itens_com_divergencia"],
                }
            )
        )

    return respostas


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
    
    composicoes_custo = calcular_composicao_custos_nota(nota)
    itens_formatados = []
    for item in nota.itens:
        composicao_custo = composicoes_custo.get(item.id, {})
        detalhe_vinculo = obter_detalhe_vinculo_item(item)
        dados_pack = calcular_quantidade_custo_efetivos(
            item.descricao,
            item.quantidade,
            item.valor_unitario,
            item.valor_total
        )
        conferencia_item = _serializar_conferencia_item(item)
        itens_formatados.append({
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
            "ean_tributario": getattr(item, "ean_tributario", None),
            "lote": item.lote,
            "data_validade": item.data_validade.isoformat() if item.data_validade else None,
            "produto_id": item.produto_id,
            "produto_nome": item.produto.nome if item.produto else None,
            "produto_codigo": item.produto.codigo if item.produto else None,
            "produto_ean": (
                item.produto.codigo_barras
                or item.produto.gtin_ean
                or item.produto.gtin_ean_tributario
            ) if item.produto else None,
            "produto_codigo_barras": item.produto.codigo_barras if item.produto else None,
            "produto_gtin_ean": item.produto.gtin_ean if item.produto else None,
            "produto_ean_tributario": item.produto.gtin_ean_tributario if item.produto else None,
            "divergencia_codigo_barras": _montar_divergencia_codigo_barras_item(item),
            "vinculado": item.vinculado,
            "confianca_vinculo": item.confianca_vinculo,
            "origem_vinculo_automatico": detalhe_vinculo["origem"],
            "referencia_vinculo": detalhe_vinculo["referencia"],
            "status": item.status,
            "pack_detectado_automatico": dados_pack["pack_detectado"],
            "pack_multiplicador_detectado": dados_pack["multiplicador_pack"],
            "quantidade_efetiva": dados_pack["quantidade_efetiva"],
            "custo_unitario_efetivo": dados_pack["custo_unitario_efetivo"],
            "custo_aquisicao_unitario": composicao_custo.get("custo_aquisicao_unitario", dados_pack["custo_unitario_efetivo"]),
            "custo_aquisicao_total": composicao_custo.get("custo_aquisicao_total", item.valor_total),
            "composicao_custo": composicao_custo,
            **conferencia_item,
        })

    return _montar_payload_nota(
        nota,
        itens_formatados,
        fornecedor_criado_automaticamente=fornecedor_criado_automaticamente,
    )


@router.post("/{nota_id}/conferencia")
def salvar_conferencia_nota(
    nota_id: int,
    payload: ConferenciaNotaPayload,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Salva a conferência física da NF, assumindo tudo OK por padrão e ajustando apenas exceções."""
    current_user, tenant_id = user_and_tenant

    nota = db.query(NotaEntrada).options(
        joinedload(NotaEntrada.itens)
    ).filter(
        NotaEntrada.id == nota_id,
        NotaEntrada.tenant_id == tenant_id
    ).first()

    if not nota:
        raise HTTPException(status_code=404, detail="Nota não encontrada")

    itens_por_id = {item.id: item for item in nota.itens}
    payload_por_id = {item.item_id: item for item in payload.itens}

    itens_invalidos = [item_id for item_id in payload_por_id if item_id not in itens_por_id]
    if itens_invalidos:
        raise HTTPException(
            status_code=400,
            detail=f"Itens de conferência inválidos: {', '.join(str(item_id) for item_id in itens_invalidos)}",
        )

    for item in nota.itens:
        quantidade_nf = _round_quantity(item.quantidade)
        payload_item = payload_por_id.get(item.id)

        quantidade_conferida = item.quantidade_conferida if item.quantidade_conferida is not None else quantidade_nf
        quantidade_avariada = item.quantidade_avariada or 0
        observacao_conferencia = item.observacao_conferencia
        acao_sugerida = item.acao_sugerida

        if payload_item:
            quantidade_conferida = _round_quantity(payload_item.quantidade_conferida)
            quantidade_avariada = _round_quantity(payload_item.quantidade_avariada)
            observacao_conferencia = payload_item.observacao_conferencia
            acao_sugerida = payload_item.acao_sugerida

        if quantidade_conferida < 0 or quantidade_avariada < 0:
            raise HTTPException(
                status_code=400,
                detail=f"Quantidades inválidas para o item {item.numero_item}.",
            )

        if quantidade_conferida > quantidade_nf:
            raise HTTPException(
                status_code=400,
                detail=f"A quantidade conferida do item {item.numero_item} não pode ser maior que a quantidade da NF.",
            )

        if quantidade_conferida + quantidade_avariada > quantidade_nf:
            raise HTTPException(
                status_code=400,
                detail=f"A soma de conferida + avariada do item {item.numero_item} não pode ultrapassar a quantidade da NF.",
            )

        tem_divergencia = (quantidade_conferida + quantidade_avariada) < quantidade_nf or quantidade_avariada > 0

        item.quantidade_conferida = quantidade_conferida
        item.quantidade_avariada = quantidade_avariada
        item.observacao_conferencia = _normalizar_texto_curto(observacao_conferencia)
        item.acao_sugerida = _obter_acao_conferencia(acao_sugerida, tem_divergencia)

    nota.conferencia_observacoes = _normalizar_texto_curto(payload.observacao_geral)
    nota.conferencia_realizada_em = datetime.utcnow()

    resumo = _resumir_conferencia_nota(nota)
    nota.conferencia_status = (
        CONFERENCIA_STATUS_COM_DIVERGENCIA
        if resumo["itens_com_divergencia"] > 0
        else CONFERENCIA_STATUS_SEM_DIVERGENCIA
    )
    nota.conferencia_user_id = current_user.id

    db.commit()

    return {
        "message": "Conferência salva com sucesso",
        "nota_id": nota.id,
        "conferencia": _resumir_conferencia_nota(nota),
    }


@router.post("/{nota_id}/conferencia/desfazer")
def desfazer_conferencia_nota(
    nota_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Limpa a conferencia registrada da NF antes do processamento do estoque."""
    current_user, tenant_id = user_and_tenant

    nota = db.query(NotaEntrada).options(
        joinedload(NotaEntrada.itens)
    ).filter(
        NotaEntrada.id == nota_id,
        NotaEntrada.tenant_id == tenant_id
    ).first()

    if not nota:
        raise HTTPException(status_code=404, detail="Nota não encontrada")

    if nota.entrada_estoque_realizada:
        raise HTTPException(
            status_code=400,
            detail="Nao e possivel desfazer a conferencia apos processar a entrada no estoque.",
        )

    for item in nota.itens:
        item.quantidade_conferida = None
        item.quantidade_avariada = 0
        item.observacao_conferencia = None
        item.acao_sugerida = "sem_acao"

    nota.conferencia_observacoes = None
    nota.conferencia_realizada_em = None
    nota.conferencia_status = CONFERENCIA_STATUS_NAO_INICIADA
    nota.conferencia_user_id = None

    db.commit()

    return {
        "message": "Conferencia desfeita com sucesso",
        "nota_id": nota.id,
        "conferencia": _resumir_conferencia_nota(nota),
    }


@router.get("/{nota_id}/devolucao-draft")
def gerar_rascunho_nf_devolucao(
    nota_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Gera um rascunho de NF de devolução com base nos itens avariados da conferência."""
    _, tenant_id = user_and_tenant

    nota = db.query(NotaEntrada).options(
        joinedload(NotaEntrada.itens)
    ).filter(
        NotaEntrada.id == nota_id,
        NotaEntrada.tenant_id == tenant_id
    ).first()

    if not nota:
        raise HTTPException(status_code=404, detail="Nota não encontrada")

    itens_devolucao = []
    valor_total_estimado = 0.0

    for item in nota.itens:
        conferencia_item = _serializar_conferencia_item(item)
        quantidade_devolucao = conferencia_item["quantidade_para_devolucao"]
        if quantidade_devolucao <= 0:
            continue

        valor_total_item = round(quantidade_devolucao * float(item.valor_unitario or 0), 2)
        valor_total_estimado += valor_total_item
        itens_devolucao.append(
            {
                "item_id": item.id,
                "numero_item_nf": item.numero_item,
                "codigo_produto": item.codigo_produto,
                "descricao": item.descricao,
                "unidade": item.unidade,
                "quantidade_devolucao": quantidade_devolucao,
                "valor_unitario": float(item.valor_unitario or 0),
                "valor_total": valor_total_item,
                "observacao_conferencia": conferencia_item["observacao_conferencia"],
            }
        )

    observacao_padrao = (
        f"Rascunho de NF de devolução referente à NF de entrada {nota.numero_nota}. "
        "Gerado a partir das divergências por avaria registradas na conferência física."
    )

    return {
        "disponivel": len(itens_devolucao) > 0,
        "nota_entrada_id": nota.id,
        "numero_nota_origem": nota.numero_nota,
        "fornecedor_nome": nota.fornecedor_nome,
        "fornecedor_cnpj": nota.fornecedor_cnpj,
        "data_emissao_origem": nota.data_emissao.isoformat() if nota.data_emissao else None,
        "itens": itens_devolucao,
        "quantidade_itens": len(itens_devolucao),
        "valor_total_estimado": round(valor_total_estimado, 2),
        "observacao_sugerida": observacao_padrao,
        "message": (
            "Rascunho gerado com sucesso"
            if itens_devolucao
            else "Nenhuma divergência com avaria foi encontrada para gerar NF de devolução"
        ),
    }


def _buscar_nota_item_por_tenant(
    nota_id: int,
    item_id: int,
    tenant_id,
    db: Session,
) -> tuple[NotaEntrada, NotaEntradaItem]:
    nota = db.query(NotaEntrada).filter(
        NotaEntrada.id == nota_id,
        NotaEntrada.tenant_id == tenant_id,
    ).first()
    if not nota:
        raise HTTPException(status_code=404, detail="Nota nÃ£o encontrada")

    item = db.query(NotaEntradaItem).filter(
        NotaEntradaItem.id == item_id,
        NotaEntradaItem.nota_entrada_id == nota_id,
        NotaEntradaItem.tenant_id == tenant_id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item nÃ£o encontrado")

    return nota, item


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
    current_user, tenant_id = user_and_tenant
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
    
    # Atualizar dados fiscais do produto com informacoes do XML/PDF quando disponiveis.
    atualizar_fiscal = _aplicar_dados_fiscais_item_no_produto(produto, item)
    
    if atualizar_fiscal:
        logger.info(f"📋 Dados fiscais do produto {produto.id} atualizados com informações da NF")
    
    # Vincular produto ao fornecedor da nota automaticamente
    nota = db.query(NotaEntrada).filter(NotaEntrada.id == nota_id).first()
    custo_item_vinculo = item.valor_unitario
    if nota:
        composicao_custo = calcular_composicao_custos_nota(nota).get(item.id, {})
        custo_item_vinculo = composicao_custo.get("custo_aquisicao_unitario", item.valor_unitario)

    if nota and nota.fornecedor_id:
        # Busca o fornecedor PRINCIPAL atual do produto
        vinculo_principal = db.query(ProdutoFornecedor).filter(
            ProdutoFornecedor.produto_id == produto_id,
            ProdutoFornecedor.e_principal == True
        ).first()

        if not vinculo_principal:
            # Produto sem fornecedor -> registra o fornecedor da NF como principal
            novo_vinculo = ProdutoFornecedor(
                produto_id=produto_id,
                fornecedor_id=nota.fornecedor_id,
                preco_custo=custo_item_vinculo,
                e_principal=True,
                ativo=True,
                tenant_id=tenant_id
            )
            db.add(novo_vinculo)
            logger.info(f"✅ Produto {produto_id} vinculado ao fornecedor {nota.fornecedor_id} como principal")
        elif vinculo_principal.fornecedor_id == nota.fornecedor_id:
            # Mesmo fornecedor -> só atualiza o preço
            vinculo_principal.preco_custo = custo_item_vinculo
            vinculo_principal.ativo = True
            logger.info(f"🔄 Preço do fornecedor principal do produto {produto_id} atualizado")
        else:
            # Fornecedor diferente -> troca o fornecedor principal + atualiza preço
            vinculo_principal.fornecedor_id = nota.fornecedor_id
            vinculo_principal.preco_custo = custo_item_vinculo
            vinculo_principal.ativo = True
            logger.info(f"🔄 Fornecedor principal do produto {produto_id} alterado para {nota.fornecedor_id}")
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
    
    dados_pack = calcular_quantidade_custo_efetivos(
        item.descricao,
        item.quantidade,
        item.valor_unitario,
        item.valor_total
    )
    quantidade_total_disponivel = dados_pack["quantidade_efetiva"]
    composicao_custo = calcular_composicao_custos_nota(nota).get(item.id, {})
    custo_unitario_efetivo = composicao_custo.get("custo_aquisicao_unitario", dados_pack["custo_unitario_efetivo"])

    # Validar quantidade
    if rateio.quantidade_online < 0:
        raise HTTPException(status_code=400, detail="Quantidade online nÃ£o pode ser negativa")
    
    if rateio.quantidade_online > quantidade_total_disponivel:
        raise HTTPException(
            status_code=400, 
            detail=f"Quantidade online ({rateio.quantidade_online}) nÃ£o pode ser maior que a quantidade total ({quantidade_total_disponivel})"
        )
    
    # Atualizar item
    item.quantidade_online = rateio.quantidade_online
    item.valor_online = rateio.quantidade_online * custo_unitario_efetivo
    
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
            "quantidade_total": quantidade_total_disponivel,
            "quantidade_online": item.quantidade_online,
            "valor_online": item.valor_online,
            "pack_detectado_automatico": dados_pack["pack_detectado"],
            "pack_multiplicador_detectado": dados_pack["multiplicador_pack"]
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
    
    composicoes_custo = calcular_composicao_custos_nota(nota)
    preview_itens = []
    
    for item in nota.itens:
        composicao_custo = composicoes_custo.get(item.id, {})
        conferencia_item = _serializar_conferencia_item(item)
        # Dados do item da NF (sempre presente)
        dados_pack = calcular_quantidade_custo_efetivos(
            item.descricao,
            item.quantidade,
            item.valor_unitario,
            item.valor_total
        )

        item_nf = {
            "item_id": item.id,
            "codigo_produto_nf": item.codigo_produto,
            "descricao_nf": item.descricao,
            "quantidade_nf": item.quantidade,
            "valor_unitario_nf": item.valor_unitario,
            "quantidade_efetiva_nf": dados_pack["quantidade_efetiva"],
            "custo_unitario_efetivo_nf": dados_pack["custo_unitario_efetivo"],
            "custo_aquisicao_unitario_nf": composicao_custo.get("custo_aquisicao_unitario", dados_pack["custo_unitario_efetivo"]),
            "custo_aquisicao_total_nf": composicao_custo.get("custo_aquisicao_total", item.valor_total),
            "composicao_custo": composicao_custo,
            "pack_detectado_automatico": dados_pack["pack_detectado"],
            "pack_multiplicador_detectado": dados_pack["multiplicador_pack"],
            "ean_nf": item.ean,
            "ean_tributario_nf": getattr(item, "ean_tributario", None),
            "ncm_nf": item.ncm,
            "vinculado": item.vinculado,
            "confianca_vinculo": item.confianca_vinculo,
            "divergencia_codigo_barras": _montar_divergencia_codigo_barras_item(item),
            **conferencia_item,
        }

        detalhe_vinculo = obter_detalhe_vinculo_item(item)
        item_nf["origem_vinculo_automatico"] = detalhe_vinculo["origem"]
        item_nf["referencia_vinculo"] = detalhe_vinculo["referencia"]
        
        # Dados do produto vinculado (se houver)
        produto_vinculado = None
        if item.produto_id:
            produto = item.produto
            custo_atual = produto.preco_custo or 0
            custo_novo = composicao_custo.get("custo_aquisicao_unitario", dados_pack["custo_unitario_efetivo"])
            variacao_custo = ((custo_novo - custo_atual) / custo_atual * 100) if custo_atual > 0 else 0
            
            # Calcular margem de referencia (com custo atual do cadastro)
            preco_venda_atual = produto.preco_venda or 0
            if preco_venda_atual > 0 and custo_atual > 0:
                margem_atual = ((preco_venda_atual - custo_atual) / preco_venda_atual) * 100
            else:
                margem_atual = 0

            # Calcular margem projetada mantendo o preço de venda atual e aplicando o novo custo
            if preco_venda_atual > 0 and custo_novo > 0:
                margem_projetada = ((preco_venda_atual - custo_novo) / preco_venda_atual) * 100
            else:
                margem_projetada = 0
            
            produto_vinculado = {
                "produto_id": produto.id,
                "produto_codigo": produto.codigo,
                "produto_nome": produto.nome,
                "produto_ean": produto.codigo_barras,
                "produto_codigo_barras": produto.codigo_barras,
                "produto_gtin_ean": produto.gtin_ean,
                "produto_ean_tributario": produto.gtin_ean_tributario,
                "divergencia_codigo_barras": _montar_divergencia_codigo_barras_item(item),
                "custo_anterior": custo_atual,
                "custo_novo": custo_novo,
                "variacao_custo_percentual": round(variacao_custo, 2),
                "preco_venda_atual": preco_venda_atual,
                "margem_atual": round(margem_atual, 2),
                "margem_projetada_custo_novo": round(margem_projetada, 2),
                "estoque_atual": produto.estoque_atual or 0
            }
        
        preview_itens.append({
            **item_nf,
            "produto_vinculado": produto_vinculado
        })
    
    return {
        "nota_id": nota.id,
        "numero_nota": nota.numero_nota,
        "data_emissao": nota.data_emissao.isoformat() if nota.data_emissao else None,
        "fornecedor_nome": nota.fornecedor_nome,
        "fornecedor_cnpj": nota.fornecedor_cnpj,
        "valor_total": nota.valor_total,
        "conferencia": _resumir_conferencia_nota(nota),
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
    current_user, tenant_id = user_and_tenant

    nota = db.query(NotaEntrada).filter(
        NotaEntrada.id == nota_id,
        NotaEntrada.tenant_id == tenant_id
    ).first()
    if not nota:
        raise HTTPException(status_code=404, detail="Nota nÃ£o encontrada")
    
    for preco_data in precos:
        produto = db.query(Produto).filter(
            Produto.id == preco_data.produto_id,
            Produto.tenant_id == tenant_id
        ).first()
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
                    user_id=current_user.id,
                    tenant_id=tenant_id
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

class ProcessarConfig(BaseModel):
    # chave = str(item_id), valor = multiplicador (ex: {"42": 10})
    multiplicadores_override: dict = Field(default_factory=dict)
    # chave = str(item_id), valor = custo unitário manual a aplicar no sistema
    custos_override: dict = Field(default_factory=dict)


@router.post("/{nota_id}/processar")
def processar_entrada_estoque(
    nota_id: int,
    config: ProcessarConfig = ProcessarConfig(),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Processa entrada no estoque de todos os itens vinculados.
    Aceita:
    - multiplicadores_override: {"item_id": multiplicador} para packs manuais
    - custos_override: {"item_id": custo_unitario} para custo manual de sistema
    """
    current_user, tenant_id = user_and_tenant
    logger.info(f"ðŸ“¦ Processando entrada no estoque - Nota {nota_id}")
    
    nota = db.query(NotaEntrada).options(
        joinedload(NotaEntrada.itens).joinedload(NotaEntradaItem.produto)
    ).filter(
        NotaEntrada.id == nota_id,
        NotaEntrada.tenant_id == tenant_id
    ).first()
    
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
    composicoes_custo = calcular_composicao_custos_nota(nota)
    lotes_rastro_por_item = _mapear_lotes_rastro_xml(nota.xml_content)
    
    # Processar cada item
    for item in nota.itens:
        if not item.produto_id:
            continue

        composicao_custo = composicoes_custo.get(item.id, {})
        conferencia_item = _serializar_conferencia_item(item)
        quantidade_base_conferida = conferencia_item["quantidade_conferida"]

        # Verificar override manual antes de usar auto-deteccao
        override_raw = _obter_override_mapa(config.multiplicadores_override, item.id)
        try:
            override_mult = int(override_raw) if override_raw is not None else None
        except (ValueError, TypeError):
            override_mult = None
        custo_unitario_manual = _normalizar_custo_unitario_override(
            _obter_override_mapa(config.custos_override, item.id),
            item.id,
        )

        if override_mult is not None and 1 <= override_mult <= 200:
            multiplicador_pack = override_mult
            quantidade_total_efetiva_nf = (item.quantidade or 0) * override_mult
            quantidade_entrada = quantidade_base_conferida * override_mult
            custo_total_aquisicao = composicao_custo.get("custo_aquisicao_total", item.valor_total)
            custo_unitario_entrada = (
                (custo_total_aquisicao / quantidade_total_efetiva_nf)
                if quantidade_total_efetiva_nf > 0 else item.valor_unitario
            )
            logger.info(f"📦 Pack MANUAL no item {item.id}: x{override_mult} (qtd NF {item.quantidade} → qtd entrada {quantidade_entrada})")
        else:
            dados_pack = calcular_quantidade_custo_efetivos(
                item.descricao,
                item.quantidade,
                item.valor_unitario,
                item.valor_total
            )
            quantidade_entrada = quantidade_base_conferida * dados_pack["multiplicador_pack"]
            custo_unitario_entrada = composicao_custo.get("custo_aquisicao_unitario", dados_pack["custo_unitario_efetivo"])
            multiplicador_pack = dados_pack["multiplicador_pack"]

        if custo_unitario_manual is not None:
            custo_unitario_entrada = custo_unitario_manual
            logger.info(
                f"💰 Custo manual aplicado no item {item.id}: "
                f"R$ {custo_unitario_entrada:.4f} por unidade"
            )

        if quantidade_entrada <= 0:
            item.status = 'processado'
            itens_processados.append({
                "produto_id": item.produto.id,
                "produto_nome": item.produto.nome,
                "quantidade": 0,
                "lote": None,
                "estoque_atual": item.produto.estoque_atual or 0,
                "pack_multiplicador": multiplicador_pack,
                "status_conferencia": conferencia_item["status_conferencia"],
            })
            logger.info(
                f"  ⚠️ {item.produto.nome}: sem entrada em estoque "
                f"(conferida: {quantidade_base_conferida}, avariada: {conferencia_item['quantidade_avariada']}, "
                f"faltante: {conferencia_item['quantidade_faltante']})"
            )
            continue
        
        produto = item.produto
        
        # âœ… REATIVAR produto se estiver inativo
        if not produto.ativo:
            produto.ativo = True
            logger.info(f"  â™»ï¸  Produto reativado: {produto.codigo} - {produto.nome}")
        
        # Atualizar dados fiscais do produto com informacoes do XML quando vierem preenchidas.
        # Entradas PDF preservam o cadastro atual, pois o arquivo nao contem dados fiscais reais.
        _aplicar_dados_fiscais_item_no_produto(
            produto,
            item,
            sobrescrever=nota.serie != "PDF",
        )
        
        _aplicar_codigos_barras_item_no_produto(produto, item)
        
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
                    preco_custo=custo_unitario_entrada,
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
                vinculo_existente.preco_custo = custo_unitario_entrada
        
        lotes_entrada = _montar_lotes_entrada_item(
            item,
            nota,
            quantidade_entrada,
            lotes_rastro_por_item,
        )
        if not lotes_entrada:
            continue

        lotes_criados = []
        ordem_base = int(datetime.utcnow().timestamp())
        for lote_index, lote_entrada in enumerate(lotes_entrada):
            quantidade_lote = _round_quantity(lote_entrada["quantidade"])
            if quantidade_lote <= 0:
                continue

            lote = ProdutoLote(
                produto_id=produto.id,
                nome_lote=lote_entrada["nome_lote"],
                quantidade_inicial=quantidade_lote,
                quantidade_disponivel=quantidade_lote,
                custo_unitario=float(custo_unitario_entrada),
                data_fabricacao=lote_entrada.get("data_fabricacao"),
                data_validade=lote_entrada.get("data_validade"),
                ordem_entrada=ordem_base + lote_index,
                tenant_id=tenant_id
            )
            db.add(lote)
            db.flush()
            lotes_criados.append((lote, quantidade_lote))

        if not lotes_criados:
            continue
        
        # Atualizar estoque
        estoque_anterior = produto.estoque_atual or 0
        produto.estoque_atual = estoque_anterior + quantidade_entrada
        
        # Atualizar preÃ§o de custo e registrar histÃ³rico
        preco_custo_anterior = produto.preco_custo
        preco_venda_anterior = produto.preco_venda
        margem_anterior = ((preco_venda_anterior - preco_custo_anterior) / preco_venda_anterior * 100) if preco_venda_anterior > 0 else 0
        
        alterou_custo = False
        if custo_unitario_entrada != preco_custo_anterior:
            produto.preco_custo = custo_unitario_entrada
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
                observacoes=(
                    f"Entrada via NF-e: custo alterado de R$ {preco_custo_anterior:.2f} "
                    f"para R$ {produto.preco_custo:.2f}"
                    f"{' (ajuste manual aplicado no processamento)' if custo_unitario_manual is not None else ''}"
                ),
                user_id=current_user.id,
                tenant_id=tenant_id
            )
            db.add(historico)
            
            logger.info(
                f"  ðŸ“Š HistÃ³rico registrado: {produto.nome} - "
                f"Custo R$ {preco_custo_anterior:.2f} â†’ R$ {produto.preco_custo:.2f} "
                f"({variacao_custo:+.2f}%)"
            )
        
        observacao_movimentacao = (
            f"Entrada NF-e {nota.numero_nota} - {item.descricao}"
            if conferencia_item["status_conferencia"] == "ok"
            else (
                f"Entrada NF-e {nota.numero_nota} - {item.descricao} | "
                f"Conferida: {conferencia_item['quantidade_conferida']} | "
                f"Avariada: {conferencia_item['quantidade_avariada']} | "
                f"Faltante: {conferencia_item['quantidade_faltante']}"
            )
        ) + (
            f" | Custo sistema manual: R$ {custo_unitario_entrada:.4f}"
            if custo_unitario_manual is not None else ""
        )

        estoque_movimento_anterior = estoque_anterior
        for lote, quantidade_lote in lotes_criados:
            estoque_movimento_novo = _round_quantity(estoque_movimento_anterior + quantidade_lote)
            movimentacao = EstoqueMovimentacao(
                produto_id=produto.id,
                lote_id=lote.id,
                tipo="entrada",
                motivo="compra",
                quantidade=quantidade_lote,
                quantidade_anterior=estoque_movimento_anterior,
                quantidade_nova=estoque_movimento_novo,
                custo_unitario=float(custo_unitario_entrada),
                valor_total=float(quantidade_lote * custo_unitario_entrada),
                documento=nota.chave_acesso,
                referencia_tipo="nota_entrada",
                referencia_id=nota.id,
                observacao=observacao_movimentacao,
                user_id=current_user.id,
                tenant_id=tenant_id
            )
            db.add(movimentacao)
            estoque_movimento_anterior = estoque_movimento_novo
        
        # Atualizar status do item
        item.status = 'processado'
        
        itens_processados.append({
            "produto_id": produto.id,
            "produto_nome": produto.nome,
            "quantidade": quantidade_entrada,
            "lote": ", ".join(lote.nome_lote for lote, _ in lotes_criados),
            "estoque_atual": produto.estoque_atual,
            "pack_multiplicador": multiplicador_pack,
            "status_conferencia": conferencia_item["status_conferencia"],
            "custo_unitario_aplicado": float(custo_unitario_entrada),
            "custo_manual_aplicado": custo_unitario_manual is not None,
        })
        
        logger.info(
            f"  âœ… {produto.nome}: +{quantidade_entrada} unidades "
            f"em {len(lotes_criados)} lote(s) "
            f"(estoque: {estoque_anterior} â†’ {produto.estoque_atual})"
        )

        if multiplicador_pack > 1:
            logger.info(
                f"  ðŸ“¦ Pack detectado automaticamente no item {item.numero_item}: "
                f"x{multiplicador_pack} (qtd NF {item.quantidade} â†’ qtd entrada {quantidade_entrada})"
            )
    
    resumo_conferencia = _resumir_conferencia_nota(nota)
    if not nota.conferencia_realizada_em:
        nota.conferencia_realizada_em = datetime.utcnow()
        nota.conferencia_user_id = current_user.id
    nota.conferencia_status = (
        CONFERENCIA_STATUS_COM_DIVERGENCIA
        if resumo_conferencia["itens_com_divergencia"] > 0
        else CONFERENCIA_STATUS_SEM_DIVERGENCIA
    )
    resumo_conferencia = _resumir_conferencia_nota(nota)

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
    
    # SINCRONIZAR ESTOQUE COM BLING para todos os itens processados
    try:
        from app.bling_estoque_sync import sincronizar_bling_background
        for item_proc in itens_processados:
            sincronizar_bling_background(item_proc['produto_id'], item_proc['estoque_atual'], "entrada_nfe")
    except Exception as e_sync:
        logger.warning(f"[BLING-SYNC] Erro ao agendar sync (entrada_nfe): {e_sync}")
    
    # VERIFICAR E NOTIFICAR PENDÊNCIAS DE ESTOQUE
    from app.services.pendencia_estoque_service import verificar_e_notificar_pendencias
    try:
        for item_proc in itens_processados:
            produto_id = item_proc['produto_id']
            quantidade = item_proc['quantidade']
            notificacoes = verificar_e_notificar_pendencias(
                db=db,
                tenant_id=tenant_id,
                produto_id=produto_id,
                quantidade_entrada=quantidade
            )
            if notificacoes > 0:
                logger.info(f"WhatsApp: {notificacoes} clientes notificados sobre {item_proc['produto']}")
    except Exception as e:
        logger.error(f"Erro ao notificar pendencias: {str(e)}")
        # Não abortar, apenas logar o erro
    
    logger.info(f"âœ… Entrada processada: {len(itens_processados)} produtos")
    
    return {
        "message": "Entrada no estoque realizada com sucesso",
        "nota_id": nota.id,
        "numero_nota": nota.numero_nota,
        "itens_processados": len(itens_processados),
        "contas_pagar_criadas": len(contas_ids),
        "conferencia": resumo_conferencia,
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
            
            try:
                produto = item.produto
                
                # Buscar lotes criados para esta entrada. Notas podem ter mais de um
                # rastro/lote para o mesmo item do XML.
                lotes = (
                    db.query(ProdutoLote)
                    .join(EstoqueMovimentacao, EstoqueMovimentacao.lote_id == ProdutoLote.id)
                    .filter(
                        ProdutoLote.produto_id == produto.id,
                        ProdutoLote.tenant_id == tenant_id,
                        EstoqueMovimentacao.referencia_tipo == "nota_entrada",
                        EstoqueMovimentacao.referencia_id == nota.id,
                        EstoqueMovimentacao.produto_id == produto.id,
                        EstoqueMovimentacao.tenant_id == tenant_id,
                    )
                    .distinct()
                    .all()
                )

                if not lotes:
                    nome_lote = item.lote if item.lote else f"NF{nota.numero_nota}-{item.numero_item}"
                    lote_fallback = db.query(ProdutoLote).filter(
                        ProdutoLote.produto_id == produto.id,
                        ProdutoLote.nome_lote == nome_lote,
                        ProdutoLote.tenant_id == tenant_id
                    ).first()
                    lotes = [lote_fallback] if lote_fallback else []

                if lotes:
                    quantidade_lancada = float(sum(lote.quantidade_inicial or 0 for lote in lotes))
                    lote_base = lotes[0]

                    # REVERTER PREÇO DE CUSTO se foi alterado
                    try:
                        historico_preco = db.query(ProdutoHistoricoPreco).filter(
                            ProdutoHistoricoPreco.produto_id == produto.id,
                            ProdutoHistoricoPreco.nota_entrada_id == nota.id,
                            ProdutoHistoricoPreco.motivo.in_(["nfe_entrada", "nfe_revisao_precos"]),
                            ProdutoHistoricoPreco.tenant_id == tenant_id
                        ).first()
                        
                        if historico_preco:
                            # Reverter preços anteriores (com fallback para 0 se None)
                            preco_custo_revertido = float(historico_preco.preco_custo_anterior or 0)
                            preco_venda_revertido = float(historico_preco.preco_venda_anterior or 0)
                            
                            try:
                                logger.info(f"  💰 Revertendo preço de custo: R$ {float(produto.preco_custo or 0):.2f} → R$ {preco_custo_revertido:.2f}")
                            except:
                                logger.info(f"  💰 Revertendo preços do produto {produto.id}")
                            
                            produto.preco_custo = preco_custo_revertido
                            produto.preco_venda = preco_venda_revertido
                            
                            # Excluir histórico
                            db.delete(historico_preco)
                    except Exception as e:
                        logger.warning(f"  ⚠️ Erro ao reverter preços: {str(e)}")
                    
                    # Remover quantidade do estoque
                    estoque_anterior = produto.estoque_atual or 0
                    produto.estoque_atual = max(0, estoque_anterior - quantidade_lancada)
                    
                    # Registrar movimentação de estorno (sem referência ao lote que será deletado)
                    try:
                        movimentacao_estorno = EstoqueMovimentacao(
                            produto_id=produto.id,
                            lote_id=None,  # Não referenciar o lote que será deletado
                            tipo="saida",
                            motivo="ajuste",
                            quantidade=quantidade_lancada,
                            quantidade_anterior=float(estoque_anterior),
                            quantidade_nova=float(produto.estoque_atual or 0),
                            custo_unitario=float(lote_base.custo_unitario or item.valor_unitario or 0),
                            valor_total=float(quantidade_lancada * float(lote_base.custo_unitario or item.valor_unitario or 0)),
                            documento=nota.chave_acesso or "",
                            referencia_tipo="estorno_nota_entrada",
                            referencia_id=nota.id,
                            observacao=f"Estorno NF-e {nota.numero_nota} - {item.descricao or ''}",
                            user_id=current_user.id,
                            tenant_id=tenant_id
                        )
                        db.add(movimentacao_estorno)
                    except Exception as e:
                        logger.warning(f"  ⚠️ Erro ao criar movimentação: {str(e)}")
                    
                    for lote in lotes:
                        # Excluir movimentações de estoque vinculadas ao lote (antes de deletar o lote)
                        movimentacoes_lote = db.query(EstoqueMovimentacao).filter(
                            EstoqueMovimentacao.lote_id == lote.id,
                            EstoqueMovimentacao.tenant_id == tenant_id
                        ).all()

                        for mov in movimentacoes_lote:
                            db.delete(mov)

                        if movimentacoes_lote:
                            logger.info(f"  🗑️  {len(movimentacoes_lote)} movimentações do lote excluídas")

                        # Excluir lote
                        db.delete(lote)
                    
                    # Adicionar à lista de revertidos
                    itens_revertidos.append({
                        "produto_id": produto.id,
                        "produto_nome": produto.nome,
                        "quantidade_removida": quantidade_lancada,
                        "estoque_atual": float(produto.estoque_atual or 0)
                    })
                    
                    logger.info(
                        f"  ↩️  {produto.nome}: -{quantidade_lancada} unidades "
                        f"(estoque: {estoque_anterior} → {produto.estoque_atual})"
                    )
                
                # Restaurar status do item
                item.status = 'vinculado'
            
            except Exception as e:
                logger.error(f"  ❌ Erro ao reverter item {item.id}: {str(e)}")
                # Continuar com próximo item ao invés de parar tudo
        
        # Atualizar status da nota
        nota.status = 'pendente'
        nota.entrada_estoque_realizada = False
        nota.processada_em = None
        
        db.commit()
        
        # SINCRONIZAR ESTOQUE COM BLING para todos os itens revertidos
        try:
            from app.bling_estoque_sync import sincronizar_bling_background
            for item_rev in itens_revertidos:
                sincronizar_bling_background(item_rev['produto_id'], item_rev['estoque_atual'], "estorno_nfe")
        except Exception as e_sync:
            logger.warning(f"[BLING-SYNC] Erro ao agendar sync (estorno_nfe): {e_sync}")
        
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
    Sugere SKU para produto novo usando o SKU do fornecedor como primeira opÃ§Ã£o.
    """
    current_user, tenant_id = user_and_tenant
    nota, item = _buscar_nota_item_por_tenant(nota_id, item_id, tenant_id, db)
    return _montar_sugestao_sku_produto(
        nota=nota,
        item=item,
        db=db,
        tenant_id=tenant_id,
        user_id=current_user.id,
    )


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
    
    nota, item = _buscar_nota_item_por_tenant(nota_id, item_id, tenant_id, db)

    sku_solicitado = (dados.sku or "").strip()
    sku_final = sku_solicitado
    sku_ajustado_automaticamente = False

    if not sku_final:
        sugestao = _montar_sugestao_sku_produto(
            nota=nota,
            item=item,
            db=db,
            tenant_id=tenant_id,
            user_id=current_user.id,
        )
        sugestao_recomendada = next(
            (sug for sug in sugestao["sugestoes"] if sug.get("padrao")),
            sugestao["sugestoes"][0] if sugestao["sugestoes"] else None,
        )
        if not sugestao_recomendada:
            raise HTTPException(status_code=409, detail="NÃ£o foi possÃ­vel gerar um SKU para o novo produto")
        sku_final = normalizar_sku_produto(sugestao_recomendada["sku"])
        sku_ajustado_automaticamente = True

    sku_final = normalizar_sku_produto(sku_final)
    produto_existente = _buscar_produto_por_codigo_global(db, sku_final)
    if produto_existente:
        sugestao = _montar_sugestao_sku_produto(
            nota=nota,
            item=item,
            db=db,
            tenant_id=tenant_id,
            user_id=current_user.id,
            sku_base_customizado=sku_final,
        )
        sugestao_recomendada = next(
            (sug for sug in sugestao["sugestoes"] if sug.get("padrao")),
            sugestao["sugestoes"][0] if sugestao["sugestoes"] else None,
        )
        if not sugestao_recomendada:
            raise HTTPException(status_code=409, detail="O SKU informado jÃ¡ existe e nÃ£o foi possÃ­vel gerar alternativa")
        sku_final = normalizar_sku_produto(sugestao_recomendada["sku"])
        sku_ajustado_automaticamente = True
        logger.info(
            f"ðŸ”„ SKU ajustado automaticamente para criar novo produto: "
            f"{sku_solicitado or '<vazio>'} -> {sku_final}"
        )
    
    # Criar produto novo e vincular
    try:
        # Preparar descriÃ§Ãµes
        descricao_texto = dados.descricao or item.descricao or ''
        descricao_curta = descricao_texto[:100] if descricao_texto else ''
        descricao_completa = descricao_texto
        
        # Aplicar inteligência fiscal
        dados_produto = {
            "nome": dados.nome,
            "descricao": descricao_texto,
            "ncm": item.ncm if hasattr(item, 'ncm') else None,
            "cfop": item.cfop if hasattr(item, 'cfop') else None,
            "cest": item.cest if hasattr(item, 'cest') else None,
            "origem": item.origem if hasattr(item, 'origem') else None,
            "aliquota_icms": item.aliquota_icms if hasattr(item, 'aliquota_icms') else None,
            "aliquota_pis": item.aliquota_pis if hasattr(item, 'aliquota_pis') else None,
            "aliquota_cofins": item.aliquota_cofins if hasattr(item, 'aliquota_cofins') else None
        }
        
        # Aplicar padrões fiscais inteligentes
        dados_fiscais = aplicar_inteligencia_fiscal(dados_produto, {
            "ncm": item.ncm if hasattr(item, 'ncm') else None,
            "cfop": item.cfop if hasattr(item, 'cfop') else None,
            "cest": item.cest if hasattr(item, 'cest') else None,
            "origem": item.origem if hasattr(item, 'origem') else None,
            "aliquota_icms": item.aliquota_icms if hasattr(item, 'aliquota_icms') else None,
            "aliquota_pis": item.aliquota_pis if hasattr(item, 'aliquota_pis') else None,
            "aliquota_cofins": item.aliquota_cofins if hasattr(item, 'aliquota_cofins') else None
        })
        
        if dados_fiscais.get("padrao_fiscal_motivo"):
            logger.info(f"🎯 {dados_fiscais['padrao_fiscal_motivo']} (confiança: {dados_fiscais.get('padrao_fiscal_confianca', 0):.0%})")
        
        codigos_barras_nf = _codigos_barras_nf(item)

        novo_produto = Produto(
            codigo=sku_final,
            nome=dados.nome,
            descricao_curta=descricao_curta,
            descricao_completa=descricao_completa,
            preco_custo=dados.preco_custo,
            preco_venda=dados.preco_venda,
            categoria_id=dados.categoria_id,
            marca_id=dados.marca_id,
            
            # DADOS FISCAIS - Usar dados_fiscais com inteligência aplicada
            ncm=dados_fiscais.get("ncm"),
            cfop=dados_fiscais.get("cfop"),
            cest=dados_fiscais.get("cest"),
            origem=dados_fiscais.get("origem", "0"),
            aliquota_icms=dados_fiscais.get("aliquota_icms", 0),
            aliquota_pis=dados_fiscais.get("aliquota_pis", 0),
            aliquota_cofins=dados_fiscais.get("aliquota_cofins", 0),
            codigo_barras=codigos_barras_nf["principal"] or None,
            gtin_ean=codigos_barras_nf["ean"] or None,
            gtin_ean_tributario=codigos_barras_nf["ean_tributario"] or None,
            
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
        "message": (
            f"Produto criado e vinculado com sucesso com SKU ajustado para {novo_produto.codigo}"
            if sku_ajustado_automaticamente
            else "Produto criado e vinculado com sucesso"
        ),
        "produto": {
            "id": novo_produto.id,
            "codigo": novo_produto.codigo,
            "nome": novo_produto.nome,
            "descricao_curta": novo_produto.descricao_curta,
            "descricao_completa": novo_produto.descricao_completa,
            "preco_custo": novo_produto.preco_custo,
            "preco_venda": novo_produto.preco_venda
        },
        "item_vinculado": True,
        "sku_ajustado_automaticamente": sku_ajustado_automaticamente
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


# ============================================================================
# IMPORTAÇÃO AUTOMÁTICA DE DOCS DA SEFAZ (chamado pelo loop do main.py)
# ============================================================================

def importar_docs_sefaz(docs: list, tenant_id_str: str, db) -> dict:
    """
    Importa documentos retornados pela SEFAZ para a tabela notas_entrada.

    Chamada pelo loop de sincronização automática no main.py.
    Cada `doc` é um dict com chaves: nsu, schema, xml.

    Só importa documentos com schema procNFe (XML completo).
    Documentos resNFe (resumo) são ignorados pois não têm itens.
    Documentos onde o CNPJ emitente == CNPJ do tenant (NF de saída) são descartados.

    Retorna: {"importadas": N, "duplicadas": N, "erros": N, "saidas_descartadas": N}
    """
    from uuid import UUID
    from app.models import User

    importadas = 0
    duplicadas = 0
    erros = 0
    saidas_descartadas = 0

    # Buscar CNPJ do tenant na config SEFAZ para identificar NF de saída
    tenant_cnpj = ""
    try:
        from app.services.sefaz_tenant_config_service import SefazTenantConfigService
        cfg_tenant = SefazTenantConfigService.load_config(UUID(tenant_id_str))
        tenant_cnpj = "".join(ch for ch in str(cfg_tenant.get("cnpj", "")) if ch.isdigit())
    except Exception as exc_cfg:
        logger.warning(f"[SEFAZ] Não foi possível carregar CNPJ do tenant {tenant_id_str}: {exc_cfg}")

    # Buscar um usuário sistema do tenant para associar as notas
    try:
        tenant_uuid = UUID(tenant_id_str)
    except ValueError:
        logger.warning(f"[SEFAZ] tenant_id inválido: {tenant_id_str}")
        return {"importadas": 0, "duplicadas": 0, "erros": len(docs), "saidas_descartadas": 0}

    user_sistema = db.query(User).filter(
        User.tenant_id == tenant_id_str
    ).order_by(User.id).first()

    if not user_sistema:
        logger.warning(f"[SEFAZ] Nenhum usuário encontrado para tenant {tenant_id_str}")
        return {"importadas": 0, "duplicadas": 0, "erros": len(docs)}

    for doc in docs:
        schema = doc.get("schema", "")
        xml_str = doc.get("xml", "")
        nsu = doc.get("nsu", "")

        # Só processa XML completo de NF-e (procNFe) — resNFe não tem itens nem XML da nota
        if "procNFe" not in schema and "nfeProc" not in xml_str[:200]:
            logger.debug(f"[SEFAZ] NSU {nsu} ignorado (schema: {schema})")
            continue

        try:
            dados_nfe = parse_nfe_xml(xml_str)
        except Exception as exc:
            logger.warning(f"[SEFAZ] NSU {nsu}: erro no parse do XML — {exc}")
            erros += 1
            continue

        # Descartar NF de saída (emitida pela própria empresa)
        # emit.CNPJ == tenant CNPJ significa que a empresa emitiu essa NF (saída/venda)
        if tenant_cnpj:
            cnpj_emitente = "".join(ch for ch in str(dados_nfe.get("fornecedor_cnpj", "")) if ch.isdigit())
            if cnpj_emitente and cnpj_emitente == tenant_cnpj:
                logger.debug(f"[SEFAZ] NSU {nsu}: NF de saída descartada (emitente == tenant)")
                saidas_descartadas += 1
                continue

        chave = dados_nfe.get("chave_acesso", "")
        if not chave:
            logger.warning(f"[SEFAZ] NSU {nsu}: chave de acesso não encontrada no XML")
            erros += 1
            continue

        # Verificar se já existe
        existente = db.query(NotaEntrada).filter(
            NotaEntrada.chave_acesso == chave
        ).first()
        if existente:
            duplicadas += 1
            continue

        try:
            # Buscar ou criar fornecedor
            fornecedor = db.query(Cliente).filter(
                Cliente.cnpj == dados_nfe["fornecedor_cnpj"],
                Cliente.tenant_id == tenant_id_str,
                Cliente.ativo == True
            ).first()

            if not fornecedor:
                fornecedor, _ = criar_fornecedor_automatico(dados_nfe, db, user_sistema, tenant_id_str)

            # Criar nota com status pendente
            nota = NotaEntrada(
                numero_nota=dados_nfe["numero_nota"],
                serie=dados_nfe["serie"],
                chave_acesso=chave,
                fornecedor_cnpj=dados_nfe["fornecedor_cnpj"],
                fornecedor_nome=dados_nfe["fornecedor_nome"],
                fornecedor_id=fornecedor.id if fornecedor else None,
                data_emissao=dados_nfe["data_emissao"],
                data_entrada=datetime.utcnow(),
                valor_produtos=dados_nfe["valor_produtos"],
                valor_frete=dados_nfe["valor_frete"],
                valor_desconto=dados_nfe["valor_desconto"],
                valor_total=dados_nfe["valor_total"],
                xml_content=xml_str,
                status="pendente",
                user_id=user_sistema.id,
                tenant_id=tenant_id_str,
            )
            db.add(nota)
            db.flush()

            # Criar itens com matching automático
            vinculados = 0
            nao_vinculados = 0
            for item_data in dados_nfe["itens"]:
                produto, confianca, _, _, _ = encontrar_produto_similar(
                    item_data["descricao"],
                    item_data["codigo_produto"],
                    db,
                    tenant_id=tenant_id_str,
                    fornecedor_id=fornecedor.id if fornecedor else None,
                    ean=item_data.get("ean"),
                    ean_tributario=item_data.get("ean_tributario"),
                )
                item = NotaEntradaItem(
                    nota_entrada_id=nota.id,
                    numero_item=item_data["numero_item"],
                    codigo_produto=item_data["codigo_produto"],
                    descricao=item_data["descricao"],
                    ncm=item_data.get("ncm"),
                    cest=item_data.get("cest"),
                    cfop=item_data.get("cfop"),
                    origem=item_data.get("origem", "0"),
                    aliquota_icms=item_data.get("aliquota_icms", 0),
                    aliquota_pis=item_data.get("aliquota_pis", 0),
                    aliquota_cofins=item_data.get("aliquota_cofins", 0),
                    unidade=item_data.get("unidade", "UN"),
                    quantidade=item_data["quantidade"],
                    valor_unitario=item_data["valor_unitario"],
                    valor_total=item_data["valor_total"],
                    ean=item_data.get("ean"),
                    ean_tributario=item_data.get("ean_tributario"),
                    lote=item_data.get("lote"),
                    data_validade=item_data.get("data_validade"),
                    produto_id=produto.id if produto else None,
                    vinculado=bool(produto),
                    confianca_vinculo=confianca if produto else 0,
                    status="vinculado" if produto else "nao_vinculado",
                    tenant_id=tenant_id_str,
                )
                db.add(item)
                if produto:
                    vinculados += 1
                else:
                    nao_vinculados += 1

            nota.produtos_vinculados = vinculados
            nota.produtos_nao_vinculados = nao_vinculados
            db.commit()

            importadas += 1
            logger.info(
                f"[SEFAZ] ✅ NF-e {dados_nfe['numero_nota']} importada "
                f"(chave: {chave[:10]}..., {vinculados} vinculados, {nao_vinculados} não vinculados)"
            )

        except Exception as exc:
            db.rollback()
            logger.warning(f"[SEFAZ] NSU {nsu}: erro ao salvar nota {chave[:10]}... — {exc}")
            erros += 1

    return {"importadas": importadas, "duplicadas": duplicadas, "erros": erros, "saidas_descartadas": saidas_descartadas}
