"""
Rotas para gerenciar Formas de Pagamento, Taxas e Análise de Vendas no PDV
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

from .db import get_session
from .auth import get_current_user
from .auth.dependencies import get_current_user_and_tenant
from .models import User
from .formas_pagamento_models import FormaPagamentoTaxa, ConfiguracaoImposto
from .financeiro_models import FormaPagamento
from .produtos_models import Produto
from .empresa_config_fiscal_models import EmpresaConfigFiscal
from app.utils.logger import logger

router = APIRouter(prefix="/formas-pagamento", tags=["Formas de Pagamento"])


def get_session():
    """Dependency para obter sessão do banco"""
    from .db import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ===== SCHEMAS =====

class FormaPagamentoTaxaCreate(BaseModel):
    forma_pagamento_id: int
    parcelas: int
    taxa_percentual: float
    descricao: Optional[str] = None


class FormaPagamentoTaxaResponse(BaseModel):
    id: int
    forma_pagamento_id: int
    parcelas: int
    taxa_percentual: float
    descricao: Optional[str]
    
    model_config = {"from_attributes": True}


class ItemAnaliseVenda(BaseModel):
    produto_id: int
    quantidade: float
    preco_venda: float
    custo: Optional[float] = None


class FormaPagamentoAnalise(BaseModel):
    forma_pagamento_id: int
    valor: float
    parcelas: int = 1


class AnaliseVendaRequest(BaseModel):
    items: List[ItemAnaliseVenda]
    desconto: float = 0
    taxa_entrega: float = 0
    formas_pagamento: List[FormaPagamentoAnalise] = []  # Múltiplas formas
    # Manter compatibilidade com código antigo
    forma_pagamento_id: Optional[int] = None
    parcelas: int = 1
    vendedor_id: Optional[int] = None


class AlertaAnalise(BaseModel):
    tipo: str  # "info", "warning", "error", "success"
    icone: str
    mensagem: str


class DetalhamentoComissao(BaseModel):
    produto: str
    percentual: float
    valor: float


class AnaliseVendaResponse(BaseModel):
    composicao: dict
    deducoes: dict
    resultado: dict
    alertas: List[AlertaAnalise]
    detalhamento_comissoes: List[DetalhamentoComissao]
    detalhamento_taxas: Optional[List[dict]] = []  # Detalhe de cada forma de pagamento


# ===== ENDPOINTS - TAXAS =====

@router.post("/taxas", response_model=FormaPagamentoTaxaResponse)
def criar_taxa(
    taxa: FormaPagamentoTaxaCreate, 
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Criar nova taxa para forma de pagamento"""
    
    # Verificar se forma de pagamento existe
    forma = db.query(FormaPagamento).filter(FormaPagamento.id == taxa.forma_pagamento_id).first()
    if not forma:
        raise HTTPException(status_code=404, detail="Forma de pagamento não encontrada")
    
    # Verificar se já existe taxa para esse número de parcelas
    taxa_existente = db.query(FormaPagamentoTaxa).filter(
        FormaPagamentoTaxa.forma_pagamento_id == taxa.forma_pagamento_id,
        FormaPagamentoTaxa.parcelas == taxa.parcelas
    ).first()
    
    if taxa_existente:
        raise HTTPException(
            status_code=400, 
            detail=f"Já existe taxa cadastrada para {taxa.parcelas}x nesta forma de pagamento"
        )
    
    nova_taxa = FormaPagamentoTaxa(
        forma_pagamento_id=taxa.forma_pagamento_id,
        parcelas=taxa.parcelas,
        taxa_percentual=taxa.taxa_percentual,
        descricao=taxa.descricao
    )
    
    db.add(nova_taxa)
    db.commit()
    db.refresh(nova_taxa)
    
    return nova_taxa


@router.get("/taxas/{forma_pagamento_id}", response_model=List[FormaPagamentoTaxaResponse])
def listar_taxas(
    forma_pagamento_id: int,
    db: Session = Depends(get_session),
    _user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Listar todas as taxas de uma forma de pagamento"""
    
    taxas = db.query(FormaPagamentoTaxa).filter(
        FormaPagamentoTaxa.forma_pagamento_id == forma_pagamento_id
    ).order_by(FormaPagamentoTaxa.parcelas).all()
    
    return taxas


@router.put("/taxas/{taxa_id}", response_model=FormaPagamentoTaxaResponse)
def atualizar_taxa(
    taxa_id: int, 
    taxa_data: FormaPagamentoTaxaCreate, 
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Atualizar taxa existente"""
    
    taxa = db.query(FormaPagamentoTaxa).filter(FormaPagamentoTaxa.id == taxa_id).first()
    if not taxa:
        raise HTTPException(status_code=404, detail="Taxa não encontrada")
    
    taxa.parcelas = taxa_data.parcelas
    taxa.taxa_percentual = taxa_data.taxa_percentual
    taxa.descricao = taxa_data.descricao
    taxa.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(taxa)
    
    return taxa


@router.delete("/taxas/{taxa_id}")
def deletar_taxa(
    taxa_id: int, 
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Deletar taxa"""
    
    taxa = db.query(FormaPagamentoTaxa).filter(FormaPagamentoTaxa.id == taxa_id).first()
    if not taxa:
        raise HTTPException(status_code=404, detail="Taxa não encontrada")
    
    db.delete(taxa)
    db.commit()
    
    return {"message": "Taxa deletada com sucesso"}


# ===== ENDPOINT - ANÁLISE DE VENDA =====

@router.post("/analisar-venda", response_model=AnaliseVendaResponse)
def analisar_venda(
    dados: AnaliseVendaRequest,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Analisa uma venda e retorna:
    - Composição financeira
    - Deduções (comissão, taxa cartão, impostos, custos)
    - Resultado (lucro e margem)
    - Alertas e sugestões
    """
    try:
        current_user, tenant_id = user_and_tenant
        
        # ===== 1. COMPOSIÇÃO FINANCEIRA =====
        total_produtos = sum(item.preco_venda * item.quantidade for item in dados.items)
        subtotal = total_produtos - dados.desconto - dados.taxa_entrega
        
        composicao = {
            "total_produtos": float(total_produtos),
            "desconto": float(dados.desconto),
            "taxa_entrega": float(dados.taxa_entrega),
            "subtotal": float(subtotal)
        }
        
        logger.info(f"📊 Analisando venda - Subtotal: R$ {subtotal:.2f}")
        
        # ===== 2. BUSCAR CUSTOS DOS PRODUTOS =====
        custos_total = 0
        detalhamento_comissoes = []
        
        try:
            for item in dados.items:
                produto = db.query(Produto).filter(
                    Produto.id == item.produto_id,
                    Produto.tenant_id == tenant_id
                ).first()
                if not produto:
                    logger.warning(f"⚠️ Produto {item.produto_id} não encontrado")
                    continue
                
                # Usar custo informado ou buscar do produto (campo correto: preco_custo)
                custo_item = item.custo if item.custo is not None else (produto.preco_custo or 0)
                custos_total += custo_item * item.quantidade
                
                # TODO: Buscar configuração de comissão do produto
                # Por enquanto, usar 10% como padrão
                percentual_comissao = 10.0
                valor_comissao_item = (item.preco_venda * item.quantidade) * (percentual_comissao / 100)
                
                detalhamento_comissoes.append(DetalhamentoComissao(
                    produto=produto.nome,
                    percentual=percentual_comissao,
                    valor=float(valor_comissao_item)
                ))
        except Exception as e:
            logger.error(f"❌ Erro ao calcular custos e comissões: {e}")
            # Continuar com valores zerados em caso de erro
            custos_total = 0
            detalhamento_comissoes = []
        
        # ===== 3. CALCULAR COMISSÃO TOTAL =====
        comissao_total = sum(d.valor for d in detalhamento_comissoes) if detalhamento_comissoes else 0
        
        # ===== 4. PROCESSAR FORMAS DE PAGAMENTO E CALCULAR TAXAS =====
        # Compatibilidade: se não enviou formas_pagamento, usar forma_pagamento_id/parcelas antigo
        if not dados.formas_pagamento and dados.forma_pagamento_id:
            dados.formas_pagamento = [
                FormaPagamentoAnalise(
                    forma_pagamento_id=dados.forma_pagamento_id,
                    valor=subtotal,
                    parcelas=dados.parcelas
                )
            ]
        
        detalhamento_taxas = []
        taxa_cartao_total = 0
        taxa_fixa_total = 0
        
        try:
            for forma_pag_item in dados.formas_pagamento:
                forma_pag = db.query(FormaPagamento).filter(
                    FormaPagamento.id == forma_pag_item.forma_pagamento_id
                ).first()
                
                if not forma_pag:
                    logger.warning(f"⚠️ Forma de pagamento {forma_pag_item.forma_pagamento_id} não encontrada")
                    continue
                
                logger.info(f"\n🔍 Processando: {forma_pag.nome} - Valor: R$ {forma_pag_item.valor:.2f} - Parcelas: {forma_pag_item.parcelas}")
                
                taxa_percentual = 0
                taxa_fixa = 0
                
                # PRIMEIRO: Se tem parcelamento, buscar do JSON taxas_por_parcela
                if forma_pag.permite_parcelamento and forma_pag.taxas_por_parcela and forma_pag_item.parcelas > 1:
                    try:
                        import json
                        taxas_json = json.loads(forma_pag.taxas_por_parcela)
                        taxa_key = str(forma_pag_item.parcelas)
                        
                        if taxa_key in taxas_json:
                            taxa_percentual = float(taxas_json[taxa_key])
                            logger.info(f"   ✅ Taxa do JSON: {taxa_percentual}% para {forma_pag_item.parcelas}x")
                    except Exception as e:
                        logger.info(f"   ❌ Erro ao processar JSON: {e}")
                
                # SEGUNDO: Se não encontrou, usar campos taxa_percentual e taxa_fixa
                if taxa_percentual == 0 and forma_pag.taxa_percentual:
                    taxa_percentual = float(forma_pag.taxa_percentual)
                    logger.info(f"   ✅ Taxa percentual: {taxa_percentual}%")
                
                if forma_pag.taxa_fixa:
                    taxa_fixa = float(forma_pag.taxa_fixa)
                    logger.info(f"   ✅ Taxa fixa: R$ {taxa_fixa:.2f}")
                
                # TERCEIRO: Buscar na tabela formas_pagamento_taxas
                if taxa_percentual == 0:
                    taxa_obj = db.query(FormaPagamentoTaxa).filter(
                        FormaPagamentoTaxa.forma_pagamento_id == forma_pag_item.forma_pagamento_id,
                        FormaPagamentoTaxa.parcelas == forma_pag_item.parcelas
                    ).first()
                    
                    if taxa_obj:
                        taxa_percentual = float(taxa_obj.taxa_percentual)
                        logger.info(f"   ✅ Taxa da tabela: {taxa_percentual}%")
                
                # Calcular valores das taxas
                valor_taxa_percentual = forma_pag_item.valor * (taxa_percentual / 100)
                valor_taxa_fixa = taxa_fixa
                
                taxa_cartao_total += valor_taxa_percentual
                taxa_fixa_total += valor_taxa_fixa
                
                # Adicionar ao detalhamento
                detalhamento_taxas.append({
                    "forma": f"{forma_pag.nome} {forma_pag_item.parcelas}x" if forma_pag_item.parcelas > 1 else forma_pag.nome,
                    "valor_pagamento": float(forma_pag_item.valor),
                    "taxa_percentual": float(taxa_percentual),
                    "valor_taxa_percentual": float(valor_taxa_percentual),
                    "taxa_fixa": float(taxa_fixa),
                    "valor_taxa_fixa": float(valor_taxa_fixa),
                    "total_taxas": float(valor_taxa_percentual + valor_taxa_fixa)
                })
        except Exception as e:
            logger.error(f"❌ Erro ao processar formas de pagamento: {e}")
            # Continuar sem taxas em caso de erro
            detalhamento_taxas = []
            taxa_cartao_total = 0
            taxa_fixa_total = 0

        taxa_cartao_valor = taxa_cartao_total + taxa_fixa_total

        
        # ===== 5. BUSCAR IMPOSTO PADRÃO =====
        imposto_percentual = 0
        imposto_valor = 0
        imposto_nome = ""
        imposto_origem = "cadastro"
        
        try:
            # 🔹 Prioridade 1: Simples Nacional (se ativo)
            config_fiscal = (
                db.query(EmpresaConfigFiscal)
                .filter(EmpresaConfigFiscal.tenant_id == tenant_id)
                .first()
            )
            
            if (
                config_fiscal
                and config_fiscal.simples_ativo
                and config_fiscal.aliquota_simples_vigente
            ):
                imposto_percentual = float(config_fiscal.aliquota_simples_vigente)
                imposto_valor = subtotal * (imposto_percentual / 100)
                imposto_nome = f"Simples Nacional - Anexo {config_fiscal.simples_anexo or 'I'}"
                imposto_origem = "fiscal"
            else:
                # 🔹 Prioridade 2: Imposto padrão cadastrado
                config_imposto = db.query(ConfiguracaoImposto).filter(
                    ConfiguracaoImposto.ativo == True,
                    ConfiguracaoImposto.padrao == True
                ).first()
                
                if config_imposto:
                    imposto_percentual = float(config_imposto.percentual)
                    imposto_valor = subtotal * (imposto_percentual / 100)
                    imposto_nome = config_imposto.nome
                    imposto_origem = "cadastro"
        except Exception as e:
            logger.error(f"❌ Erro ao buscar configuração fiscal: {e}")
            # Continuar sem impostos em caso de erro
            imposto_percentual = 0
            imposto_valor = 0
            imposto_nome = "Sem imposto"
            imposto_origem = "erro"
        
        # ===== 6. CALCULAR RESULTADO =====
        total_deducoes = comissao_total + taxa_cartao_valor + imposto_valor + custos_total
        lucro_liquido = subtotal - total_deducoes
        margem_liquida = (lucro_liquido / subtotal * 100) if subtotal > 0 else 0
        
        # Definir cor do indicador
        if margem_liquida >= 20:
            cor_indicador = "verde"
        elif margem_liquida >= 10:
            cor_indicador = "amarelo"
        else:
            cor_indicador = "vermelho"
        
        deducoes = {
            "comissao": {
                "valor": float(comissao_total),
                "percentual": 10.0,  # TODO: calcular média ponderada
                "tipo": "percentual"
            },
            "taxa_percentual": float(taxa_cartao_total),
            "taxa_fixa": float(taxa_fixa_total),
            "impostos": {
                "valor": float(imposto_valor),
                "percentual": float(imposto_percentual)
            },
            "custos": float(custos_total),
            "total_deducoes": float(total_deducoes)
        }
        
        resultado = {
            "lucro_liquido": float(lucro_liquido),
            "margem_liquida": float(round(margem_liquida, 2)),
            "cor_indicador": cor_indicador
        }
        
        # ===== 7. GERAR ALERTAS =====
        alertas = []
        
        # Alerta de margem
        if margem_liquida < 10:
            alertas.append(AlertaAnalise(
                tipo="error",
                icone="⚠️",
                mensagem="Margem baixa - evite mais descontos"
            ))
        elif margem_liquida >= 20:
            margem_disponivel = lucro_liquido * 0.3  # Pode usar até 30% da margem
            alertas.append(AlertaAnalise(
                tipo="success",
                icone="✅",
                mensagem=f"Margem excelente - permite desconto de até R$ {margem_disponivel:.2f}"
            ))
        elif margem_liquida >= 15:
            alertas.append(AlertaAnalise(
                tipo="info",
                icone="✅",
                mensagem="Margem boa - pode oferecer pequeno desconto adicional"
            ))
        else:
            alertas.append(AlertaAnalise(
                tipo="warning",
                icone="⚠️",
                mensagem="Margem moderada - cuidado com descontos adicionais"
            ))
        
        # Alerta de taxa de cartão (verificar maior taxa)
        maior_taxa = max([t["taxa_percentual"] for t in detalhamento_taxas], default=0)
        if maior_taxa > 5:
            alertas.append(AlertaAnalise(
                tipo="warning",
                icone="⚠️",
                mensagem=f"Taxa de cartão alta ({maior_taxa}%) - sugira à vista ou menos parcelas"
            ))
        
        # Alerta de custo
        percentual_custo = (custos_total / total_produtos * 100) if total_produtos > 0 else 0
        if percentual_custo > 70:
            alertas.append(AlertaAnalise(
                tipo="warning",
                icone="⚠️",
                mensagem=f"Custo muito alto ({percentual_custo:.1f}% do total) - verifique margem antes de parcelar"
            ))
        elif percentual_custo > 60:
            alertas.append(AlertaAnalise(
                tipo="info",
                icone="💡",
                mensagem=f"Custo dos produtos: {percentual_custo:.1f}% do total"
            ))
        
        # Alerta de desconto
        if dados.desconto > 0:
            percentual_desconto = (dados.desconto / total_produtos * 100) if total_produtos > 0 else 0
            if percentual_desconto > 15:
                alertas.append(AlertaAnalise(
                    tipo="warning",
                    icone="⚠️",
                    mensagem=f"Desconto alto ({percentual_desconto:.1f}%) aplicado - margem reduzida"
                ))
        
        # Se não houver alertas, adicionar mensagem positiva
        if not alertas:
            alertas.append(AlertaAnalise(
                tipo="success",
                icone="✅",
                mensagem="Venda com margem saudável"
            ))
        
        # ===== 8. RETORNAR RESPOSTA =====
        return AnaliseVendaResponse(
            composicao=composicao,
            deducoes=deducoes,
            resultado=resultado,
            alertas=alertas,
            detalhamento_comissoes=detalhamento_comissoes,
            detalhamento_taxas=detalhamento_taxas
        )
    
    except Exception as e:
        logger.error(f"❌ ERRO CRÍTICO em analisar_venda: {str(e)}", exc_info=True)
        
        # Retornar resposta com valores padrão para não quebrar o frontend
        total_produtos = sum(item.preco_venda * item.quantidade for item in dados.items) if dados.items else 0
        subtotal = total_produtos - dados.desconto - dados.taxa_entrega
        
        return AnaliseVendaResponse(
            composicao={
                "total_produtos": float(total_produtos),
                "desconto": float(dados.desconto),
                "taxa_entrega": float(dados.taxa_entrega),
                "subtotal": float(subtotal)
            },
            deducoes={
                "comissao": {"valor": 0.0, "percentual": 0.0, "tipo": "percentual"},
                "taxa_percentual": 0.0,
                "taxa_fixa": 0.0,
                "impostos": {"valor": 0.0, "percentual": 0.0},
                "custos": 0.0,
                "total_deducoes": 0.0
            },
            resultado={
                "lucro_liquido": float(subtotal),
                "margem_liquida": 100.0,
                "cor_indicador": "verde"
            },
            alertas=[AlertaAnalise(
                tipo="error",
                icone="⚠️",
                mensagem=f"Erro ao calcular análise: {str(e)}"
            )],
            detalhamento_comissoes=[],
            detalhamento_taxas=[]
        )


# ===== ENDPOINTS - CONFIGURAÇÃO DE IMPOSTOS =====

@router.get("/impostos")
def listar_impostos(
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Listar configurações de impostos.
    Inclui dinamicamente o Simples Nacional se ativo.
    """
    current_user, tenant_id = user_and_tenant
    
    # Buscar impostos cadastrados
    impostos = db.query(ConfiguracaoImposto).filter(
        ConfiguracaoImposto.ativo == True
    ).all()
    
    resultado = [i.to_dict() for i in impostos]
    
    # 🔹 Injetar Simples Nacional dinamicamente
    config_fiscal = (
        db.query(EmpresaConfigFiscal)
        .filter(EmpresaConfigFiscal.tenant_id == tenant_id)
        .first()
    )
    
    if (
        config_fiscal
        and config_fiscal.simples_ativo
        and config_fiscal.aliquota_simples_vigente
    ):
        resultado.append({
            "codigo": "SIMPLES_NACIONAL",
            "nome": f"Simples Nacional - Anexo {config_fiscal.simples_anexo or 'I'}",
            "percentual": float(config_fiscal.aliquota_simples_vigente),
            "origem": "fiscal",
            "editavel": False,
            "ativo": True,
            "padrao": False,
            "descricao": f"Alíquota vigente do Simples Nacional (atualizado em {config_fiscal.simples_ultima_atualizacao or 'não informado'})"
        })
    
    return resultado


@router.post("/impostos")
def criar_imposto(
    nome: str,
    percentual: float,
    padrao: bool = False,
    descricao: str = None,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Criar nova configuração de imposto"""
    
    # Se marcar como padrão, desmarcar outros
    if padrao:
        db.query(ConfiguracaoImposto).update({"padrao": False})
    
    novo_imposto = ConfiguracaoImposto(
        nome=nome,
        percentual=percentual,
        ativo=True,
        padrao=padrao,
        descricao=descricao
    )
    
    db.add(novo_imposto)
    db.commit()
    db.refresh(novo_imposto)
    
    return novo_imposto.to_dict()


@router.put("/impostos/{imposto_id}/padrao")
def definir_imposto_padrao(
    imposto_id: int, 
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Definir um imposto como padrão"""
    
    # Desmarcar todos como padrão
    db.query(ConfiguracaoImposto).update({"padrao": False})
    
    # Marcar o selecionado
    imposto = db.query(ConfiguracaoImposto).filter(
        ConfiguracaoImposto.id == imposto_id
    ).first()
    
    if not imposto:
        raise HTTPException(status_code=404, detail="Configuração de imposto não encontrada")
    
    imposto.padrao = True
    imposto.ativo = True
    db.commit()
    
    return {"message": "Imposto definido como padrão"}
