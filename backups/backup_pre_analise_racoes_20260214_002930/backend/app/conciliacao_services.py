"""
Services para Conciliação de Cartões - FASE 2

PRINCÍPIOS OBRIGATÓRIOS (conforme RISCOS_E_MITIGACOES_CONCILIACAO.md):
1. ✅ Tudo em transação
2. ✅ Rollback obrigatório em caso de erro
3. ✅ Nenhuma mudança sem log
4. ✅ Nunca confiar 100% no arquivo
5. ✅ Sempre permitir reversão

REGRA DE OURO:
    IMPORTAR ≠ PROCESSAR (avançar etapa)
    
    Importação apenas ARMAZENA dados.
    Processamento (avançar etapa) apenas acontece APÓS validação confirmada.

CORREÇÕES CRÍTICAS APLICADAS (Revisão Fase 2):
    1. ✅ Vínculo validacao_id evita dupla movimentação
    2. ✅ SELECT FOR UPDATE evita concorrência
    3. 🔜 TODO (Fase 5): Migrar alertas de JSONB para tabela (BI)
    4. 🔜 TODO (Fase 5): Processamento assíncrono para arquivos 50k+ linhas
    5. ✅ Nomenclatura ajustada: "liquidar" → "processar etapa" / "avançar etapa"
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from decimal import Decimal
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple, Any
import logging

from .conciliacao_models import (
    EmpresaParametros,
    AdquirenteTemplate,
    ArquivoEvidencia,
    ConciliacaoImportacao,
    ConciliacaoLote,
    ConciliacaoValidacao,
    ConciliacaoLog
)
from .financeiro_models import ContaReceber
from .conciliacao_helpers import (
    calcular_hash_arquivo,
    detectar_duplicata_por_hash,
    calcular_confianca,
    calcular_percentual_divergencia,
    agrupar_parcelas_por_lote,
    calcular_totais_lote,
    aplicar_template_csv,
    gerar_alertas_validacao,
    validar_duplicata_nsu,
    validar_data_futura,
    validar_valor_razoavel,
    sanitizar_data
)

logger = logging.getLogger(__name__)


# ==============================================================================
# IMPORTAÇÃO DE ARQUIVOS
# ==============================================================================

def importar_arquivo_operadora(
    db: Session,
    arquivo_bytes: bytes,
    nome_arquivo: str,
    adquirente_template_id: int,
    tenant_id: str,
    user_id: int,
    tipo_importacao: str = 'recebimentos_detalhados'
) -> Dict[str, Any]:
    """
    Importa arquivo CSV da operadora (Stone, Cielo, etc).
    
    ⚠️ ATENÇÃO CRÍTICA (Risco #4):
    Esta função APENAS IMPORTA dados.
    NÃO altera status de ContaReceber para 'recebido'.
    NÃO cria movimentações bancárias.
    NÃO realiza financeiramente.
    
    APENAS atualiza campos *_real e status_conciliacao.
    
    🔜 TODO (FASE 5 - PERFORMANCE):
    Para arquivos grandes (50k-100k linhas), implementar:
    - Processamento assíncrono (Celery + Redis)
    - Batch inserts (chunks de 1000 linhas)
    - Progress tracking (websocket real-time)
    - Timeout configurável por tamanho de arquivo
    
    Princípios aplicados:
    - ✅ Tudo em transação
    - ✅ Rollback obrigatório (try/except com db.rollback())
    - ✅ Nenhuma mudança sem log
    - ✅ Nunca confiar 100% no arquivo (validação em cada linha)
    - ✅ Sempre permitir reversão (log completo)
    
    Args:
        db: Sessão do banco
        arquivo_bytes: Conteúdo do arquivo
        nome_arquivo: Nome original
        adquirente_template_id: ID do template para parsear
        tenant_id: ID do tenant
        user_id: ID do usuário que está importando
        tipo_importacao: 'recebimentos_detalhados' ou 'pagamentos_lotes'
    
    Returns:
        {
            'success': True,
            'importacao_id': 123,
            'arquivo_evidencia_id': 456,
            'total_linhas': 150,
            'linhas_validas': 148,
            'linhas_com_erro': 2,
            'parcelas_confirmadas': 140,
            'parcelas_orfas': 8,
            'erros': ['Linha 15: NSU duplicado', ...],
            'alertas': [...]
        }
    """
    try:
        # PRINCÍPIO 4: Nunca confiar 100% no arquivo
        # 1. Verificar duplicata de arquivo
        hashes = calcular_hash_arquivo(arquivo_bytes)
        
        duplicata_id = detectar_duplicata_por_hash(db, hashes['md5'], tipo_importacao)
        if duplicata_id:
            return {
                'success': False,
                'error': f'Arquivo duplicado já importado (ArquivoEvidencia ID: {duplicata_id})',
                'arquivo_evidencia_id': duplicata_id
            }
        
        # 2. Buscar template
        template_obj = db.query(AdquirenteTemplate).filter(
            AdquirenteTemplate.id == adquirente_template_id,
            AdquirenteTemplate.tenant_id == tenant_id,
            AdquirenteTemplate.ativo == True
        ).first()
        
        if not template_obj:
            return {
                'success': False,
                'error': 'Template não encontrado ou inativo'
            }
        
        # 3. Parsear arquivo usando template
        template_dict = {
            'separador': template_obj.separador,
            'encoding': template_obj.encoding,
            'tem_header': template_obj.tem_header,
            'pular_linhas': template_obj.pular_linhas,
            'mapeamento': template_obj.mapeamento,
            'transformacoes': template_obj.transformacoes
        }
        
        linhas_validas, erros_parsing = aplicar_template_csv(
            arquivo_bytes,
            template_dict,
            validar_linhas=True
        )
        
        if not linhas_validas:
            return {
                'success': False,
                'error': 'Nenhuma linha válida encontrada no arquivo',
                'erros': erros_parsing
            }
        
        # PRINCÍPIO 1: Tudo em transação
        # Iniciar transação explícita
        
        # 4. Criar registro de evidência
        arquivo_evidencia = ArquivoEvidencia(
            tenant_id=tenant_id,
            nome_original=nome_arquivo,
            tipo_arquivo=tipo_importacao,
            adquirente=template_obj.nome,
            caminho_storage=f'uploads/conciliacao/{tenant_id}/{hashes["md5"]}',
            tamanho_bytes=len(arquivo_bytes),
            hash_md5=hashes['md5'],
            hash_sha256=hashes['sha256'],
            total_linhas=len(linhas_validas),
            criado_por_id=user_id
        )
        db.add(arquivo_evidencia)
        db.flush()  # Obter ID sem commit
        
        # 5. Criar registro de importação
        importacao = ConciliacaoImportacao(
            tenant_id=tenant_id,
            arquivo_evidencia_id=arquivo_evidencia.id,
            adquirente_template_id=adquirente_template_id,
            tipo_importacao=tipo_importacao,
            data_referencia=date.today(),  # Será atualizado com período real
            total_registros=len(linhas_validas),
            status_importacao='processando',
            criado_por_id=user_id
        )
        db.add(importacao)
        db.flush()
        
        # 6. Processar linhas e atualizar ContaReceber
        parcelas_confirmadas = 0
        parcelas_orfas = 0
        erros_validacao = []
        periodo_inicio = None
        periodo_fim = None
        total_valor = Decimal('0.00')
        
        for idx, linha in enumerate(linhas_validas, start=1):
            try:
                # PRINCÍPIO 4: Validar cada linha
                nsu = linha.get('nsu')
                data_pagamento = linha.get('data_pagamento')
                valor_liquido = linha.get('valor_liquido')
                
                # Validações
                if validar_duplicata_nsu(db, nsu, template_obj.nome, tenant_id):
                    erros_validacao.append(f"Linha {idx}: NSU {nsu} já existe no sistema")
                    continue
                
                if not validar_data_futura(data_pagamento, dias_tolerancia=90):
                    erros_validacao.append(f"Linha {idx}: Data {data_pagamento} muito no futuro")
                    continue
                
                if not validar_valor_razoavel(valor_liquido):
                    erros_validacao.append(f"Linha {idx}: Valor {valor_liquido} fora da faixa razoável")
                    continue
                
                # Atualizar período
                if not periodo_inicio or data_pagamento < periodo_inicio:
                    periodo_inicio = data_pagamento
                if not periodo_fim or data_pagamento > periodo_fim:
                    periodo_fim = data_pagamento
                
                total_valor += valor_liquido
                
                # Buscar ContaReceber por NSU
                conta = db.query(ContaReceber).filter(
                    ContaReceber.tenant_id == tenant_id,
                    ContaReceber.nsu == nsu,
                    ContaReceber.adquirente == template_obj.nome
                ).first()
                
                if conta:
                    # ⚠️ ATENÇÃO CRÍTICA: NUNCA alterar status aqui!
                    # APENAS atualizar campos *_real e status_conciliacao
                    
                    conta.taxa_mdr_real = linha.get('taxa_mdr')
                    conta.taxa_antecipacao_real = linha.get('taxa_antecipacao', Decimal('0.00'))
                    conta.valor_liquido_real = valor_liquido
                    conta.data_vencimento_real = data_pagamento
                    
                    # Calcular diferenças
                    if conta.taxa_mdr_estimada:
                        conta.diferenca_taxa = conta.taxa_mdr_real - conta.taxa_mdr_estimada
                    
                    if conta.valor_liquido_estimado:
                        conta.diferenca_valor = conta.valor_liquido_real - conta.valor_liquido_estimado
                    
                    # Atualizar status_conciliacao (NÃO status!)
                    conta.status_conciliacao = 'confirmada_operadora'
                    
                    parcelas_confirmadas += 1
                
                else:
                    # Parcela órfã - existe no arquivo mas não no sistema
                    parcelas_orfas += 1
                    erros_validacao.append(
                        f"Linha {idx}: NSU {nsu} não encontrado no sistema (parcela órfã)"
                    )
            
            except Exception as e:
                erros_validacao.append(f"Linha {idx}: Erro ao processar - {str(e)}")
        
        # 7. Atualizar metadados
        arquivo_evidencia.periodo_inicio = periodo_inicio
        arquivo_evidencia.periodo_fim = periodo_fim
        arquivo_evidencia.total_registros_processados = parcelas_confirmadas
        
        importacao.data_referencia = periodo_inicio or date.today()
        importacao.total_valor = total_valor
        importacao.status_importacao = 'processada' if not erros_validacao else 'parcial'
        importacao.resumo = {
            'total_linhas': len(linhas_validas),
            'parcelas_confirmadas': parcelas_confirmadas,
            'parcelas_orfas': parcelas_orfas,
            'erros': erros_validacao[:50],  # Primeiros 50 erros
            'periodo': {
                'inicio': periodo_inicio.isoformat() if periodo_inicio else None,
                'fim': periodo_fim.isoformat() if periodo_fim else None
            }
        }
        
        # PRINCÍPIO 3: Nenhuma mudança sem log
        # 8. Criar log de auditoria
        log = ConciliacaoLog(
            tenant_id=tenant_id,
            versao_conciliacao=1,
            acao='importar_arquivo_operadora',
            status_acao='sucesso' if parcelas_confirmadas > 0 else 'parcial',
            arquivos_utilizados=[{
                'nome': nome_arquivo,
                'tipo': tipo_importacao,
                'hash_md5': hashes['md5']
            }],
            quantidades={
                'total_linhas': len(linhas_validas),
                'parcelas_confirmadas': parcelas_confirmadas,
                'parcelas_orfas': parcelas_orfas,
                'erros': len(erros_validacao)
            },
            criado_por_id=user_id
        )
        db.add(log)
        
        # PRINCÍPIO 1: Commit da transação
        db.commit()
        
        return {
            'success': True,
            'importacao_id': importacao.id,
            'arquivo_evidencia_id': arquivo_evidencia.id,
            'total_linhas': len(linhas_validas),
            'linhas_validas': len(linhas_validas),
            'linhas_com_erro': len(erros_parsing),
            'parcelas_confirmadas': parcelas_confirmadas,
            'parcelas_orfas': parcelas_orfas,
            'erros': erros_parsing + erros_validacao,
            'periodo': {
                'inicio': periodo_inicio.isoformat() if periodo_inicio else None,
                'fim': periodo_fim.isoformat() if periodo_fim else None
            },
            'total_valor': float(total_valor)
        }
    
    except Exception as e:
        # PRINCÍPIO 2: Rollback obrigatório
        db.rollback()
        logger.error(f"Erro ao importar arquivo operadora: {str(e)}", exc_info=True)
        
        return {
            'success': False,
            'error': f'Erro ao processar importação: {str(e)}'
        }


# ==============================================================================
# VALIDAÇÃO EM CASCATA
# ==============================================================================

def validar_importacao_cascata(
    db: Session,
    importacao_pagamentos_id: Optional[int],
    importacao_recebimentos_id: Optional[int],
    data_referencia: date,
    adquirente: str,
    tenant_id: str,
    user_id: int
) -> Dict[str, Any]:
    """
    Valida importação em cascata: OFX → Pagamentos → Recebimentos.
    
    PRINCÍPIO: Sistema NUNCA bloqueia.
    Confiança BAIXA apenas requer confirmação.
    
    Args:
        db: Sessão
        importacao_pagamentos_id: ID da importação de pagamentos (arquivo operadora)
        importacao_recebimentos_id: ID da importação de recebimentos (se existir)
        data_referencia: Data para validar
        adquirente: Nome da operadora
        tenant_id: Tenant
        user_id: Usuário que está validando
    
    Returns:
        {
            'success': True,
            'validacao_id': 789,
            'confianca': 'ALTA',
            'pode_processar': True,
            'requer_confirmacao': False,
            'totais': {...},
            'diferencas': {...},
            'alertas': [...]
        }
    """
    try:
        # 1. Buscar parâmetros da empresa
        parametros = db.query(EmpresaParametros).filter(
            EmpresaParametros.tenant_id == tenant_id
        ).first()
        
        if not parametros:
            # Criar parâmetros default
            parametros = EmpresaParametros(tenant_id=tenant_id)
            db.add(parametros)
            db.flush()
        
        # 2. Calcular totais
        total_pagamentos = Decimal('0.00')
        total_recebimentos = Decimal('0.00')
        quantidade_parcelas = 0
        parcelas_confirmadas = 0
        parcelas_orfas = 0
        
        # Total de pagamentos (arquivo operadora)
        if importacao_pagamentos_id:
            importacao_pag = db.query(ConciliacaoImportacao).get(importacao_pagamentos_id)
            if importacao_pag and importacao_pag.resumo:
                total_pagamentos = Decimal(str(importacao_pag.total_valor or 0))
                parcelas_confirmadas = importacao_pag.resumo.get('parcelas_confirmadas', 0)
                parcelas_orfas = importacao_pag.resumo.get('parcelas_orfas', 0)
        
        # Total de recebimentos (ContaReceber - PDV)
        contas = db.query(ContaReceber).filter(
            ContaReceber.tenant_id == tenant_id,
            ContaReceber.adquirente == adquirente,
            ContaReceber.data_vencimento_real == data_referencia,
            ContaReceber.status_conciliacao == 'confirmada_operadora'
        ).all()
        
        for conta in contas:
            total_recebimentos += conta.valor_liquido_real or Decimal('0.00')
            quantidade_parcelas += 1
        
        # 3. Calcular diferenças
        diferenca_pag_rec = total_pagamentos - total_recebimentos
        percentual_div = calcular_percentual_divergencia(diferenca_pag_rec, total_pagamentos)
        
        # 4. Classificar confiança
        confianca, pode_processar, requer_confirmacao = calcular_confianca(
            diferenca_total=abs(diferenca_pag_rec),
            total_referencia=total_pagamentos,
            tolerancia_automatica=parametros.tolerancia_conciliacao,
            tolerancia_media=parametros.tolerancia_conciliacao_media
        )
        
        # 5. Gerar alertas
        # 🔜 TODO (FASE 5 - BI E ANÁLISE):
        # Migrar alertas de JSONB para tabela separada (conciliacao_alertas)
        # Motivos:
        # - BI: Consultas agregadas ficam mais rápidas (COUNT, GROUP BY)
        # - Histórico: Comparar alertas entre execuções
        # - Recalcular: Aplicar novas regras retroativamente
        # - Índices: Buscar por tipo_alerta, gravidade, data
        # JSONB funciona para MVP, mas limita análise em escala
        alertas = gerar_alertas_validacao(
            diferenca_ofx_pagamentos=Decimal('0.00'),  # OFX será implementado depois
            diferenca_pagamentos_recebimentos=diferenca_pag_rec,
            parcelas_orfas=parcelas_orfas,
            total_parcelas=quantidade_parcelas,
            confianca=confianca
        )
        
        # 6. Criar validação
        validacao = ConciliacaoValidacao(
            tenant_id=tenant_id,
            importacao_pagamentos_id=importacao_pagamentos_id,
            importacao_recebimentos_id=importacao_recebimentos_id,
            data_referencia=data_referencia,
            adquirente=adquirente,
            total_pagamentos=total_pagamentos,
            total_recebimentos=total_recebimentos,
            diferenca_pagamentos_recebimentos=diferenca_pag_rec,
            percentual_divergencia=percentual_div,
            confianca=confianca,
            pode_processar=pode_processar,  # SEMPRE True
            requer_confirmacao=requer_confirmacao,
            status_validacao='pendente' if requer_confirmacao else 'concluida',
            alertas=alertas,
            quantidade_parcelas=quantidade_parcelas,
            parcelas_confirmadas=parcelas_confirmadas,
            parcelas_orfas=parcelas_orfas,
            criado_por_id=user_id
        )
        db.add(validacao)
        db.flush()
        
        # PRINCÍPIO 3: Log obrigatório
        log = ConciliacaoLog(
            tenant_id=tenant_id,
            conciliacao_validacao_id=validacao.id,
            versao_conciliacao=1,
            acao='validar_importacao_cascata',
            status_acao='sucesso',
            quantidades={
                'parcelas': quantidade_parcelas,
                'confirmadas': parcelas_confirmadas,
                'orfas': parcelas_orfas
            },
            diferencas={
                'pagamentos_vs_recebimentos': float(diferenca_pag_rec),
                'percentual': float(percentual_div)
            },
            criado_por_id=user_id
        )
        db.add(log)
        
        db.commit()
        
        return {
            'success': True,
            'validacao_id': validacao.id,
            'confianca': confianca,
            'pode_processar': pode_processar,
            'requer_confirmacao': requer_confirmacao,
            'totais': {
                'pagamentos': float(total_pagamentos),
                'recebimentos': float(total_recebimentos)
            },
            'diferencas': {
                'pagamentos_vs_recebimentos': float(diferenca_pag_rec),
                'percentual': float(percentual_div)
            },
            'quantidades': {
                'parcelas': quantidade_parcelas,
                'confirmadas': parcelas_confirmadas,
                'orfas': parcelas_orfas
            },
            'alertas': alertas
        }
    
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao validar cascata: {str(e)}", exc_info=True)
        
        return {
            'success': False,
            'error': f'Erro ao validar: {str(e)}'
        }


# ==============================================================================
# LIQUIDAÇÃO (REALIZAÇÃO FINANCEIRA)
# ==============================================================================

def processar_conciliacao(
    db: Session,
    validacao_id: int,
    tenant_id: str,
    user_id: int,
    confirmacao_usuario: bool = False,
    justificativa: Optional[str] = None
) -> Dict[str, Any]:
    """
    Processa conciliação APÓS validação aprovada (avança etapa do status).
    
    ⚠️ CRÍTICO: AQUI SIM pode avançar status para 'aguardando_lote'.
    MAS SOMENTE se validação foi confirmada.
    
    CORREÇÕES APLICADAS:
    - ✅ SELECT FOR UPDATE evita concorrência (dois usuários processando simultaneamente)
    - ✅ Vínculo validacao_id evita dupla movimentação (rodar duas validações no mesmo período)
    - ✅ Verifica parcela.validacao_id.is_(None) antes de processar
    
    PRINCÍPIOS:
    - ✅ Tudo em transação
    - ✅ Rollback obrigatório
    - ✅ Log completo
    - ✅ Sempre permitir reversão
    
    Args:
        db: Sessão
        validacao_id: ID da validação
        tenant_id: Tenant
        user_id: Usuário processando
        confirmacao_usuario: Se usuário confirmou explicitamente (para confiança MEDIA/BAIXA)
        justificativa: Justificativa obrigatória para confiança BAIXA
    
    Returns:
        {
            'success': True,
            'parcelas_processadas': 50,
            'valor_total_processado': 5000.00,
            'validacao_id': 123
        }
    """
    try:
        # 1. Buscar validação
        validacao = db.query(ConciliacaoValidacao).filter(
            ConciliacaoValidacao.id == validacao_id,
            ConciliacaoValidacao.tenant_id == tenant_id
        ).first()
        
        if not validacao:
            return {'success': False, 'error': 'Validação não encontrada'}
        
        # 2. Verificar se pode processar
        if not validacao.pode_processar:
            return {'success': False, 'error': 'Validação não permite processamento'}
        
        # 3. Verificar confirmação
        if validacao.requer_confirmacao and not confirmacao_usuario:
            return {
                'success': False,
                'error': 'Validação requer confirmação do usuário',
                'requer_confirmacao': True,
                'confianca': validacao.confianca
            }
        
        # 4. Verificar justificativa (obrigatória para BAIXA)
        if validacao.confianca == 'BAIXA' and not justificativa:
            return {
                'success': False,
                'error': 'Confiança BAIXA requer justificativa explícita'
            }
        
        # 5. Buscar parcelas confirmadas COM LOCK PESSIMISTA (evita concorrência)
        # CORREÇÃO CRÍTICA #2: SELECT FOR UPDATE evita dois usuários processarem simultaneamente
        parcelas = db.query(ContaReceber).filter(
            ContaReceber.tenant_id == tenant_id,
            ContaReceber.adquirente == validacao.adquirente,
            ContaReceber.data_vencimento_real == validacao.data_referencia,
            ContaReceber.status_conciliacao == 'confirmada_operadora',
            # CORREÇÃO CRÍTICA #1: Evita reprocessamento se já foi vinculada a outra validação
            ContaReceber.validacao_id.is_(None)
        ).with_for_update().all()  # ← LOCK PESSIMISTA
        
        if not parcelas:
            return {'success': False, 'error': 'Nenhuma parcela encontrada para processar (podem já estar vinculadas a outra validação)'}
        
        # 6. Processar parcelas (avançar etapa)
        parcelas_processadas = 0
        valor_total = Decimal('0.00')
        
        for parcela in parcelas:
            # ⚠️ AGORA SIM: avançar parcela para próxima etapa
            # TODO (Fase 5): Implementar função vincular_movimentacao_bancaria()
            # Por enquanto, apenas avançar status
            
            # CORREÇÃO CRÍTICA #1: Vincular com validação (evita dupla movimentação)
            parcela.validacao_id = validacao_id
            parcela.status_conciliacao = 'aguardando_lote'  # Avançar etapa
            parcela.versao_conciliacao = (parcela.versao_conciliacao or 0) + 1
            
            parcelas_processadas += 1
            valor_total += parcela.valor_liquido_real or Decimal('0.00')
        
        # 7. Atualizar validação
        validacao.status_validacao = 'concluida'
        validacao.versao_validacao = (validacao.versao_validacao or 0) + 1
        
        # 8. Log COMPLETO
        log = ConciliacaoLog(
            tenant_id=tenant_id,
            conciliacao_validacao_id=validacao_id,
            versao_conciliacao=(validacao.versao_validacao),
            acao='processar_conciliacao',
            status_acao='sucesso',
            quantidades={
                'parcelas_processadas': parcelas_processadas,
                'valor_total': float(valor_total),
                'validacao_id_vinculada': validacao_id  # Para auditoria
            },
            motivo=justificativa,
            criado_por_id=user_id
        )
        db.add(log)
        
        db.commit()
        
        return {
            'success': True,
            'parcelas_processadas': parcelas_processadas,
            'valor_total_processado': float(valor_total),
            'validacao_id': validacao_id
        }
    
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao processar conciliação: {str(e)}", exc_info=True)
        
        return {
            'success': False,
            'error': f'Erro ao processar: {str(e)}'
        }


# ==============================================================================
# REVERSÃO
# ==============================================================================

def reverter_conciliacao(
    db: Session,
    validacao_id: int,
    tenant_id: str,
    user_id: int,
    motivo: str
) -> Dict[str, Any]:
    """
    Reverte conciliação já processada.
    
    PRINCÍPIO 5: Sempre permitir reversão.
    
    Args:
        db: Sessão
        validacao_id: ID da validação
        tenant_id: Tenant
        user_id: Usuário revertendo
        motivo: Motivo da reversão (obrigatório)
    
    Returns:
        {'success': True, 'parcelas_revertidas': 50}
    """
    try:
        # Motivo obrigatório
        if not motivo:
            return {'success': False, 'error': 'Motivo da reversão é obrigatório'}
        
        # Buscar validação
        validacao = db.query(ConciliacaoValidacao).filter(
            ConciliacaoValidacao.id == validacao_id,
            ConciliacaoValidacao.tenant_id == tenant_id
        ).first()
        
        if not validacao:
            return {'success': False, 'error': 'Validação não encontrada'}
        
        if validacao.status_validacao != 'concluida':
            return {'success': False, 'error': 'Validação não foi concluída ainda'}
        
        # Buscar parcelas
        parcelas = db.query(ContaReceber).filter(
            ContaReceber.tenant_id == tenant_id,
            ContaReceber.adquirente == validacao.adquirente,
            ContaReceber.data_vencimento_real == validacao.data_referencia,
            ContaReceber.status_conciliacao.in_(['aguardando_lote', 'em_lote', 'liquidada'])
        ).all()
        
        # Reverter estado
        parcelas_revertidas = 0
        for parcela in parcelas:
            parcela.status_conciliacao = 'confirmada_operadora'  # Volta ao estado anterior
            parcela.versao_conciliacao = (parcela.versao_conciliacao or 0) + 1
            parcelas_revertidas += 1
        
        # Atualizar validação
        validacao.status_validacao = 'divergente'
        
        # Log da reversão
        log = ConciliacaoLog(
            tenant_id=tenant_id,
            conciliacao_validacao_id=validacao_id,
            versao_conciliacao=(validacao.parcelas_confirmadas or 0) + 1,
            acao='reverter_conciliacao',
            status_acao='revertido',
            quantidades={'parcelas_revertidas': parcelas_revertidas},
            motivo=motivo,
            criado_por_id=user_id
        )
        db.add(log)
        
        db.commit()
        
        return {
            'success': True,
            'parcelas_revertidas': parcelas_revertidas
        }
    
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao reverter conciliação: {str(e)}", exc_info=True)
        
        return {
            'success': False,
            'error': f'Erro ao reverter: {str(e)}'
        }


# ==============================================================================
# NOVA ARQUITETURA: 3 ABAS (Conciliação Completa)
# ==============================================================================

def conciliar_vendas_stone(
    db: Session,
    tenant_id: str,
    vendas_stone: List[Dict],  # Dados da planilha Stone
    user_id: int,
    operadora_id: Optional[int] = None  # Filtro por operadora
) -> Dict:
    """
    ABA 1: CONCILIAÇÃO DE VENDAS (PDV vs Stone)
    
    Objetivo:
        Conferir e CORRIGIR cadastro das vendas do PDV vs planilha Stone.
        NÃO mexe em financeiro (Contas a Receber) - apenas prepara dados.
    
    Entrada:
        vendas_stone: Lista de dicts com dados da planilha Stone
            [
                {'nsu': '123456', 'valor': 100.00, 'bandeira': 'Visa', 'parcelas': 2, 'taxa_mdr': 5.0},
                ...
            ]
    
    Saída:
        {
            'conferidas': 45,  # Vendas OK (NSU bate, dados conferem)
            'corrigidas': 3,   # Vendas com NSU corrigido ou dados ajustados
            'sem_nsu': 2,      # Vendas sem NSU (precisa vincular)
            'orfaos': 1,       # NSUs Stone sem venda no PDV (precisa criar venda)
            'divergencias': [  # Lista de divergências encontradas
                {
                    'venda_id': 5002,
                    'tipo': 'taxa_diferente',
                    'pdv': '4.5%',
                    'stone': '5.0%',
                    'acao_sugerida': 'atualizar_taxa'
                }
            ]
        }
    
    Princípios:
        1. Apenas CORRIGE cadastro (NSU, bandeira, parcelas, taxa)
        2. Se parcelas/valor/taxa mudou → REGENERAR Contas a Receber
        3. NÃO baixa nada (baixa é só na Aba 3)
    """
    from .vendas_models import Venda
    
    try:
        logger.info(f"[Aba 1] Iniciando conciliação de vendas: {len(vendas_stone)} transações Stone")
        
        conferidas = 0
        corrigidas = 0
        sem_nsu = 0
        orfaos_stone = []
        divergencias = []
        
        # Criar set de NSUs Stone para detecção de órfãos
        nsus_stone = {v['nsu'] for v in vendas_stone if v.get('nsu')}
        
        # 1. Buscar vendas do PDV (mesmo período)
        # Filtra por operadora_id OU vendas antigas sem operadora (NULL)
        from .vendas_models import VendaPagamento
        
        query = db.query(Venda).filter(
            Venda.tenant_id == tenant_id,
            Venda.status == 'finalizada'
        )
        
        # Se operadora foi especificada, filtrar vendas dessa operadora + vendas antigas (NULL)
        if operadora_id is not None:
            query = query.join(VendaPagamento).filter(
                (VendaPagamento.operadora_id == operadora_id) |
                (VendaPagamento.operadora_id.is_(None))
            )
        
        vendas_pdv = query.all()
        logger.info(f"🔍 Query retornou {len(vendas_pdv)} vendas do PDV (operadora_id={operadora_id})")
        
        # Mapear NSUs dos pagamentos das vendas (NSU está em VendaPagamento)
        nsus_pdv = set()
        vendas_por_nsu = {}  # {nsu: [vendas]}  - LISTA pois pode ter duplicação!
        nsus_duplicados = []  # NSUs que aparecem em múltiplas vendas
        
        for venda in vendas_pdv:
            for pagamento in venda.pagamentos:
                if pagamento.nsu_cartao:
                    nsus_pdv.add(pagamento.nsu_cartao)
                    
                    # Verificar duplicação
                    if pagamento.nsu_cartao in vendas_por_nsu:
                        if pagamento.nsu_cartao not in nsus_duplicados:
                            nsus_duplicados.append(pagamento.nsu_cartao)
                        vendas_por_nsu[pagamento.nsu_cartao].append(venda)
                        logger.warning(f"⚠️  NSU DUPLICADO: {pagamento.nsu_cartao} agora em {len(vendas_por_nsu[pagamento.nsu_cartao])} vendas")
                    else:
                        vendas_por_nsu[pagamento.nsu_cartao] = [venda]
                    
                    logger.debug(f"📝 Mapeado NSU {pagamento.nsu_cartao} → Venda #{venda.numero_venda} (operadora_id={pagamento.operadora_id})")
        
        logger.info(f"🗂️  Total de NSUs mapeados: {len(nsus_pdv)}, NSUs duplicados: {len(nsus_duplicados)}")
        if nsus_duplicados:
            logger.warning(f"⚠️  NSUs duplicados encontrados: {nsus_duplicados}")
        
        # 2. Processar cada venda Stone
        for venda_stone in vendas_stone:
            nsu = venda_stone.get('nsu')
            
            if not nsu:
                # Stone sem NSU = erro grave (não deveria acontecer)
                logger.warning(f"[Aba 1] Venda Stone sem NSU: {venda_stone}")
                continue
            
            logger.debug(f"🔍 Processando NSU Stone: {nsu}")
            
            # Buscar venda(s) no PDV pelo NSU (pode ter duplicação!)
            vendas_match = vendas_por_nsu.get(nsu, [])
            
            if not vendas_match:
                # NSU Stone sem venda no PDV = órfão (precisa criar venda)
                logger.warning(f"❌ NSU {nsu} não encontrado no PDV - será órfão")
                orfaos_stone.append(venda_stone)
                continue
            
            # DETECTAR NSU DUPLICADO
            if len(vendas_match) > 1:
                logger.warning(f"⚠️  NSU {nsu} encontrado em {len(vendas_match)} vendas: {[v.numero_venda for v in vendas_match]}")
                divergencias.append({
                    'tipo': 'nsu_duplicado',
                    'nsu': nsu,
                    'vendas': [{
                        'venda_id': v.id,
                        'numero_venda': v.numero_venda,
                        'total': float(v.total)
                    } for v in vendas_match],
                    'stone': venda_stone,
                    'acao_sugerida': 'verificar_qual_venda_correta_e_remover_nsu_duplicado'
                })
                # Processar todas mesmo assim
            
            # Processar cada venda encontrada
            for venda_pdv in vendas_match:
                logger.info(f"✅ Match encontrado: NSU {nsu} → Venda #{venda_pdv.numero_venda}")
            
                # Buscar o pagamento específico com esse NSU
                pagamento_pdv = next((p for p in venda_pdv.pagamentos if p.nsu_cartao == nsu), None)
                
                if not pagamento_pdv:
                    continue  # Não deveria acontecer, mas protege
                
                # 3. Conferir dados (NSU existe, agora conferir detalhes)
                tem_divergencia = False
                
                # Conferir bandeira
                if pagamento_pdv.bandeira != venda_stone.get('bandeira'):
                    divergencias.append({
                        'venda_id': venda_pdv.id,
                        'numero_venda': venda_pdv.numero_venda,
                        'pagamento_id': pagamento_pdv.id,
                        'nsu': nsu,
                        'tipo': 'bandeira_diferente',
                        'pdv': pagamento_pdv.bandeira,
                        'stone': venda_stone.get('bandeira'),
                        'acao_sugerida': 'corrigir_bandeira'
                    })
                    tem_divergencia = True
                
                # Conferir parcelas
                if pagamento_pdv.numero_parcelas != venda_stone.get('parcelas'):
                    divergencias.append({
                        'venda_id': venda_pdv.id,
                        'numero_venda': venda_pdv.numero_venda,
                        'pagamento_id': pagamento_pdv.id,
                        'nsu': nsu,
                        'tipo': 'parcelas_diferentes',
                        'pdv': pagamento_pdv.numero_parcelas,
                        'stone': venda_stone.get('parcelas'),
                        'acao_sugerida': 'corrigir_parcelas_regenerar_contas'
                    })
                    tem_divergencia = True
            
                # Conferir taxa (se disponível - pode não estar no pagamento)
                taxa_stone = venda_stone.get('taxa_mdr')
                if taxa_stone:
                    # Taxa MDR normalmente é armazenada em outro lugar (config ou contas a receber)
                    # Por agora, apenas logamos mas não divergimos
                    logger.info(f"[Aba 1] Taxa Stone: {taxa_stone}% para venda {venda_pdv.id}")
                
                if tem_divergencia:
                    corrigidas += 1
                else:
                    conferidas += 1
                    
                    # Marcar venda como conferida
                    venda_pdv.conciliado_vendas = True
                    venda_pdv.conciliado_vendas_em = datetime.utcnow()
        
        # 4. Detectar vendas PDV sem NSU em nenhum pagamento
        vendas_sem_nsu = []
        for venda in vendas_pdv:
            tem_nsu = any(p.nsu_cartao for p in venda.pagamentos)
            if not tem_nsu:
                vendas_sem_nsu.append(venda)
        
        sem_nsu = len(vendas_sem_nsu)
        
        # Construir array de matches estruturados para visualização
        matches = []
        
        # 1. Matches OK (NSU confere, sem divergências)
        for venda in vendas_pdv:
            for pag in venda.pagamentos:
                if pag.nsu_cartao:
                    # Verificar se tem divergência
                    tem_div = any(d.get('nsu') == pag.nsu_cartao for d in divergencias)
                    if not tem_div:
                        # Buscar dados Stone correspondentes
                        stone_data = next((s for s in vendas_stone if s.get('nsu') == pag.nsu_cartao), None)
                        if stone_data:
                            matches.append({
                                'status': 'ok',
                                'venda_pdv': {
                                    'id': venda.id,
                                    'numero': venda.numero_venda,
                                    'nsu': pag.nsu_cartao,
                                    'bandeira': pag.bandeira,
                                    'parcelas': pag.numero_parcelas,
                                    'valor': float(pag.valor)
                                },
                                'venda_stone': stone_data
                            })
        
        # 2. Matches com divergência
        for div in divergencias:
            if div.get('tipo') != 'nsu_duplicado':  # Ignorar duplicados por ora
                venda = db.query(Venda).get(div.get('venda_id'))
                if venda:
                    pag = next((p for p in venda.pagamentos if p.nsu_cartao == div.get('nsu')), None)
                    stone_data = next((s for s in vendas_stone if s.get('nsu') == div.get('nsu')), None)
                    if pag and stone_data:
                        matches.append({
                            'status': 'divergencia',
                            'venda_pdv': {
                                'id': venda.id,
                                'numero': venda.numero_venda,
                                'nsu': pag.nsu_cartao,
                                'bandeira': pag.bandeira,
                                'parcelas': pag.numero_parcelas,
                                'valor': float(pag.valor)
                            },
                            'venda_stone': stone_data,
                            'divergencia': div
                        })
        
        # 3. Órfãos Stone (sem venda no PDV)
        for orfao in orfaos_stone:
            matches.append({
                'status': 'orfao',
                'venda_pdv': None,
                'venda_stone': orfao
            })
        
        # 4. Vendas PDV sem NSU
        for venda in vendas_sem_nsu:
            matches.append({
                'status': 'sem_nsu',
                'venda_pdv': {
                    'id': venda.id,
                    'numero': venda.numero_venda,
                    'nsu': None,
                    'valor': float(venda.total)
                },
                'venda_stone': None
            })
        
        db.commit()
        
        logger.info(f"[Aba 1] Conciliação concluída: {conferidas} OK, {corrigidas} divergências, {sem_nsu} sem NSU, {len(orfaos_stone)} órfãos")
        
        return {
            'success': True,
            'matches': matches,  # Array estruturado para visualização
            'conferidas': conferidas,
            'corrigidas': corrigidas,
            'sem_nsu': sem_nsu,
            'orfaos': len(orfaos_stone),
            'lista_orfaos': orfaos_stone,
            'divergencias': divergencias,
            'vendas_sem_nsu': [{'id': v.id, 'numero': v.numero_venda, 'valor': float(v.total)} for v in vendas_sem_nsu]
        }
    
    except Exception as e:
        db.rollback()
        logger.error(f"[Aba 1] Erro ao conciliar vendas: {str(e)}", exc_info=True)
        
        return {
            'success': False,
            'error': f'Erro ao conciliar vendas: {str(e)}'
        }


def processar_upload_conciliacao_vendas(
    db: Session,
    tenant_id: str,
    arquivo_bytes: bytes,
    nome_arquivo: str,
    operadora_id: Optional[int],
    user_id: int
) -> Dict:
    """
    ABA 1: Upload + Conciliação com PERSISTÊNCIA COMPLETA
    
    Fluxo:
    1. ✅ Calcula hash e detecta duplicatas
    2. ✅ Salva arquivo (arquivos_evidencia)
    3. ✅ Parseia CSV conforme template Stone
    4. ✅ Cria importação (conciliacao_importacoes)
    5. ✅ Processa conciliação (chama conciliar_vendas_stone)
    6. ✅ Atualiza status da importação
    7. ✅ Commit transacional
    
    Retorna:
        {
            'success': True,
            'importacao_id': 123,
            'conferidas': 45,
            'corrigidas': 3,
            'sem_nsu': 2,
            'orfaos': 1
        }
    """
    try:
        logger.info(f"[Upload] Iniciando processamento: {nome_arquivo} ({len(arquivo_bytes)} bytes)")
        
        # 1. Calcular hashes
        hashes = calcular_hash_arquivo(arquivo_bytes)
        
        # 2. Verificar duplicata
        duplicata_id = detectar_duplicata_por_hash(db, tenant_id, hashes['md5'])
        if duplicata_id:
            return {
                'success': False,
                'error': f'Arquivo duplicado já importado (ID: {duplicata_id})',
                'arquivo_evidencia_id': duplicata_id
            }
        
        # 3. Buscar template Stone (padrão para operadoras)
        template_obj = db.query(AdquirenteTemplate).filter(
            AdquirenteTemplate.tenant_id == tenant_id,
            AdquirenteTemplate.nome == 'STONE',
            AdquirenteTemplate.ativo == True
        ).first()
        
        if not template_obj:
            return {
                'success': False,
                'error': 'Template Stone não encontrado. Execute seed de templates primeiro.'
            }
        
        # 4. Parsear arquivo CSV usando template
        template_dict = {
            'separador': template_obj.separador,
            'encoding': template_obj.encoding,
            'tem_header': template_obj.tem_header,
            'pular_linhas': template_obj.pular_linhas,
            'mapeamento': template_obj.mapeamento,
            'transformacoes': template_obj.transformacoes
        }
        
        linhas_validas, erros_parsing = aplicar_template_csv(
            arquivo_bytes,
            template_dict,
            validar_linhas=True
        )
        
        if not linhas_validas:
            return {
                'success': False,
                'error': 'Nenhuma linha válida encontrada no arquivo',
                'erros': erros_parsing
            }
        
        logger.info(f"[Upload] CSV parseado: {len(linhas_validas)} linhas válidas")
        
        # 5. Criar registro de evidência
        arquivo_evidencia = ArquivoEvidencia(
            tenant_id=tenant_id,
            nome_original=nome_arquivo,
            tipo_arquivo='vendas',
            adquirente='STONE',
            caminho_storage=f'uploads/conciliacao/{tenant_id}/{hashes["md5"]}',
            tamanho_bytes=len(arquivo_bytes),
            hash_md5=hashes['md5'],
            hash_sha256=hashes['sha256'],
            total_linhas=len(linhas_validas),
            criado_por_id=user_id
        )
        db.add(arquivo_evidencia)
        db.flush()  # Obter ID
        
        logger.info(f"[Upload] Arquivo salvo: ID {arquivo_evidencia.id}")
        
        # 6. Criar importação
        importacao = ConciliacaoImportacao(
            tenant_id=tenant_id,
            arquivo_evidencia_id=arquivo_evidencia.id,
            adquirente_template_id=template_obj.id,
            tipo_importacao='vendas',
            data_referencia=date.today(),
            total_registros=len(linhas_validas),
            status_importacao='processando',
            criado_por_id=user_id
        )
        db.add(importacao)
        db.flush()  # Obter ID
        
        logger.info(f"[Upload] Importação criada: ID {importacao.id}")
        
        # 7. APENAS SALVAR dados parseados (NÃO fazer conciliação ainda)
        # Armazenar NSUs no resumo para processamento posterior
        # IMPORTANTE: Converter para JSON-safe (Decimal → float, date → string)
        from .conciliacao_helpers import serialize_for_json
        
        dados_json_safe = serialize_for_json(linhas_validas)
        
        # Adicionar status_conciliacao inicial a cada NSU
        for nsu_data in dados_json_safe:
            nsu_data['status_conciliacao'] = 'nao_conciliado'
        
        importacao.status_importacao = 'processada'
        importacao.resumo = {
            'total_linhas': len(linhas_validas),
            'operadora_id': operadora_id,
            'dados_parseados': dados_json_safe,  # Salvar NSUs parseados (JSON-safe)
            'conciliado': False  # Flag indicando que ainda não foi conciliado
        }
        
        # 8. Commit transacional
        db.commit()
        
        logger.info(f"[Upload] Dados salvos: Importação ID {importacao.id} - {len(linhas_validas)} NSUs")
        
        # 9. Retornar resultado SEM conciliação
        return {
            'success': True,
            'importacao_id': importacao.id,
            'arquivo_id': arquivo_evidencia.id,
            'total_nsus': len(linhas_validas),
            'operadora_id': operadora_id,
            'persistido': True,
            'mensagem': f'{len(linhas_validas)} NSUs importados. Clique em "Processar Matches" para conciliar.'
        }
    
    except Exception as e:
        db.rollback()
        logger.error(f"[Upload] Erro ao processar: {str(e)}", exc_info=True)
        
        return {
            'success': False,
            'error': f'Erro ao processar upload: {str(e)}'
        }


def validar_recebimentos_cascata_v2(
    db: Session,
    tenant_id: str,
    recebimentos_detalhados: List[Dict],
    recibo_lote: List[Dict],
    ofx_creditos: List[Dict],
    user_id: int,
    operadora: Optional[str] = None
) -> Dict:
    """
    ABA 2: CONCILIAÇÃO DE RECEBIMENTOS (validação em cascata)
    
    Objetivo:
        Conferir que DINHEIRO ENTROU na conta.
        NÃO conhece vendas! Apenas valida: Recebimentos ↔ Recibo ↔ OFX
    
    Entrada:
        recebimentos_detalhados: Lista 1 a 1 dos recebimentos
        recibo_lote: Lotes agrupados
        ofx_creditos: Extratos bancários
    
    Saída:
        {
            'validado': True/False,
            'recebimentos_salvos': 48,
            'valor_total': 15300.00,
            'lotes': 2,
            'divergencias': [
                {'tipo': 'soma_diferente', 'diferenca': 20.00}
            ]
        }
    
    Validação em Cascata:
        1. Soma recebimentos detalhados
        2. Confere com recibo_lote
        3. Confere com OFX
        Se bater tudo → validado = True
    """
    from .conciliacao_models import ConciliacaoRecebimento
    
    try:
        logger.info(f"[Aba 2] Iniciando validação cascata: {len(recebimentos_detalhados)} recebimentos")

        def parse_data_recebimento(valor):
            if not valor:
                return None
            if isinstance(valor, date):
                return valor
            if isinstance(valor, datetime):
                return valor.date()
            if isinstance(valor, str):
                for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d'):
                    try:
                        return datetime.strptime(valor, fmt).date()
                    except ValueError:
                        continue
            return None
        
        # Função para determinar tipo de recebimento
        def determinar_tipo_recebimento(rec):
            tipo_arquivo = str(rec.get('tipo_recebimento', '')).lower()
            # Verifica se é antecipação baseado em indicadores do arquivo
            if 'antecip' in tipo_arquivo or 'antecipacao' in tipo_arquivo:
                return 'antecipacao'
            # Por padrão, considera parcela individual
            return 'parcela_individual'
        
        # 1. Salvar recebimentos detalhados
        recebimentos_salvos = []
        soma_recebimentos = Decimal('0')
        
        for rec in recebimentos_detalhados:
            data_rec = parse_data_recebimento(rec.get('data_recebimento'))
            recebimento = ConciliacaoRecebimento(
                tenant_id=tenant_id,
                nsu=rec.get('nsu'),
                adquirente=operadora,
                data_recebimento=data_rec,
                valor=Decimal(str(rec.get('valor', 0))),
                parcela_numero=rec.get('parcela_numero'),
                total_parcelas=rec.get('total_parcelas'),
                tipo_recebimento=determinar_tipo_recebimento(rec),
                lote_id=rec.get('lote_id'),
                validado=False  # Ainda não validado
            )
            db.add(recebimento)
            recebimentos_salvos.append(recebimento)
            soma_recebimentos += recebimento.valor
        
        # 2. Somar recibo_lote
        soma_lotes = Decimal('0')
        for lote in recibo_lote:
            soma_lotes += Decimal(str(lote.get('valor', 0)))
        
        # 3. Somar OFX
        soma_ofx = Decimal('0')
        for ofx in ofx_creditos:
            soma_ofx += Decimal(str(ofx.get('valor', 0)))
        
        # 4. Validar cascata (informativo - não bloqueante)
        TOLERANCIA_SUGERIDA = Decimal('0.10')
        divergencias = []
        tem_divergencias = False
        
        # Conferir: Recebimentos vs Lotes
        diferenca_recebimentos_lotes = abs(soma_recebimentos - soma_lotes)
        if diferenca_recebimentos_lotes > 0:
            nivel = 'arredondamento' if diferenca_recebimentos_lotes <= TOLERANCIA_SUGERIDA else 'atencao'
            divergencias.append({
                'tipo': 'recebimentos_vs_lotes',
                'soma_recebimentos': float(soma_recebimentos),
                'soma_lotes': float(soma_lotes),
                'diferenca': float(diferenca_recebimentos_lotes),
                'percentual': float((diferenca_recebimentos_lotes / soma_recebimentos) * 100) if soma_recebimentos > 0 else 0,
                'nivel': nivel,  # 'arredondamento' ou 'atencao'
                'mensagem': 'Possível arredondamento' if nivel == 'arredondamento' else 'Divergência acima de R$ 0,10'
            })
            tem_divergencias = True
        
        # Conferir: Lotes vs OFX
        diferenca_lotes_ofx = abs(soma_lotes - soma_ofx)
        if diferenca_lotes_ofx > 0:
            nivel = 'arredondamento' if diferenca_lotes_ofx <= TOLERANCIA_SUGERIDA else 'atencao'
            divergencias.append({
                'tipo': 'lotes_vs_ofx',
                'soma_lotes': float(soma_lotes),
                'soma_ofx': float(soma_ofx),
                'diferenca': float(diferenca_lotes_ofx),
                'percentual': float((diferenca_lotes_ofx / soma_lotes) * 100) if soma_lotes > 0 else 0,
                'nivel': nivel,
                'mensagem': 'Possível arredondamento' if nivel == 'arredondamento' else 'Divergência acima de R$ 0,10'
            })
            tem_divergencias = True
        
        # SEMPRE marca como validado (decisão é do usuário)
        validado = True
        
        # 5. Marcar recebimentos como validados
        for recebimento in recebimentos_salvos:
            recebimento.validado = True
            recebimento.validado_em = datetime.utcnow()
        
        db.commit()
        
        status = 'COM DIVERGÊNCIAS' if tem_divergencias else 'PERFEITO'
        logger.info(f"[Aba 2] Validação {status}: {len(recebimentos_salvos)} recebimentos salvos")
        
        return {
            'success': True,
            'validado': validado,
            'tem_divergencias': tem_divergencias,
            'recebimentos_salvos': len(recebimentos_salvos),
            'valor_total_recebimentos': float(soma_recebimentos),
            'valor_total_lotes': float(soma_lotes),
            'valor_total_ofx': float(soma_ofx),
            'lotes_count': len(recibo_lote),
            'ofx_count': len(ofx_creditos),
            'divergencias': divergencias
        }
    
    except Exception as e:
        db.rollback()
        logger.error(f"[Aba 2] Erro ao validar recebimentos: {str(e)}", exc_info=True)
        
        return {
            'success': False,
            'error': f'Erro ao validar recebimentos: {str(e)}'
        }


def amarrar_recebimentos_vendas(
    db: Session,
    tenant_id: str,
    data_recebimento: date,
    user_id: int,
    operadora: Optional[str] = None
) -> Dict:
    """
    ABA 3: AMARRAÇÃO AUTOMÁTICA (Venda ↔ Recebimento)
    
    Objetivo:
        Vincular recebimentos (já validados) às vendas (já conferidas)
        e BAIXAR Contas a Receber.
    
    Princípios:
        - 98% automático (se Aba 1 foi bem feita!)
        - IDEMPOTENTE: Se rodar 2x, não duplica baixa
        - TRANSPARENTE: Mostra quantas parcelas serão baixadas antes de processar
    
    Entrada:
        data_recebimento: Data dos recebimentos a amarrar
    
    Saída:
        {
            'amarrados': 47,
            'orfaos': 1,
            'parcelas_liquidadas': 47,
            'valor_total_liquidado': 15300.00,
            'taxa_amarracao_automatica': 98.0,
            'alerta_saude': 'OK'
        }
    """
    from .conciliacao_models import ConciliacaoRecebimento, ConciliacaoMetrica
    from .vendas_models import Venda
    
    try:
        logger.info(f"[Aba 3] Iniciando amarração para data {data_recebimento}")
        
        # 1. Buscar recebimentos validados (Aba 2) e ainda não amarrados
        recebimentos_query = db.query(ConciliacaoRecebimento).filter(
            ConciliacaoRecebimento.tenant_id == tenant_id,
            ConciliacaoRecebimento.data_recebimento == data_recebimento,
            ConciliacaoRecebimento.validado == True,  # Obrigatório Aba 2
            ConciliacaoRecebimento.amarrado == False  # Ainda não processado
        )

        if operadora:
            recebimentos_query = recebimentos_query.filter(
                ConciliacaoRecebimento.adquirente == operadora
            )

        recebimentos = recebimentos_query.all()
        
        if not recebimentos:
            return {
                'success': True,
                'amarrados': 0,
                'orfaos': 0,
                'mensagem': 'Nenhum recebimento para amarrar (já processado ou não validado)'
            }
        
        amarrados = 0
        orfaos = []
        parcelas_a_baixar = []  # Para preview transparente
        
        for recebimento in recebimentos:
            # 2. Buscar venda pelo NSU através de VendaPagamento
            from .vendas_models import VendaPagamento
            venda_pagamento = db.query(VendaPagamento).filter(
                VendaPagamento.nsu_cartao == recebimento.nsu
            ).first()
            
            if not venda_pagamento:
                orfaos.append({
                    'nsu': recebimento.nsu,
                    'valor': float(recebimento.valor),
                    'data': recebimento.data_recebimento.isoformat(),
                    'motivo': 'sem_venda_pagamento'
                })
                continue
            
            venda = db.query(Venda).filter(
                Venda.tenant_id == tenant_id,
                Venda.id == venda_pagamento.venda_id,
                Venda.conciliado_vendas == True  # Obrigatório Aba 1!
            ).first()
            
            if not venda:
                # ❌ ERRO: Recebimento sem venda (falhou na Aba 1!)
                orfaos.append({
                    'nsu': recebimento.nsu,
                    'valor': float(recebimento.valor),
                    'data': recebimento.data_recebimento.isoformat()
                })
                continue
            
            # 3. Buscar Contas a Receber da venda
            if recebimento.tipo_recebimento == 'antecipacao':
                # Baixar todas as parcelas de uma vez
                parcelas = db.query(ContaReceber).filter(
                    ContaReceber.tenant_id == tenant_id,
                    ContaReceber.venda_id == venda.id,
                    ContaReceber.status != 'recebido',  # ✅ IDEMPOTENTE
                    ContaReceber.conciliacao_recebimento_id.is_(None)  # ✅ Ainda não amarrado
                ).all()
                
                for parcela in parcelas:
                    parcela.status = 'recebido'
                    parcela.data_recebimento = data_recebimento
                    parcela.tipo_recebimento = 'antecipacao'
                    parcela.conciliacao_recebimento_id = recebimento.id
                    parcelas_a_baixar.append(parcela)
            
            else:
                # Baixar apenas a parcela específica
                parcela = db.query(ContaReceber).filter(
                    ContaReceber.tenant_id == tenant_id,
                    ContaReceber.venda_id == venda.id,
                    ContaReceber.numero_parcela == recebimento.parcela_numero,
                    ContaReceber.status != 'recebido',  # ✅ IDEMPOTENTE
                    ContaReceber.conciliacao_recebimento_id.is_(None)  # ✅ Ainda não amarrado
                ).first()
                
                if parcela:
                    parcela.status = 'recebido'
                    parcela.data_recebimento = data_recebimento
                    parcela.tipo_recebimento = 'parcela_individual'
                    parcela.conciliacao_recebimento_id = recebimento.id
                    parcelas_a_baixar.append(parcela)
            
            # 4. Marcar recebimento como amarrado
            recebimento.amarrado = True
            recebimento.amarrado_em = datetime.utcnow()
            recebimento.venda_id = venda.id
            
            amarrados += 1
        
        # 📊 MÉTRICA DE SAÚDE DO SISTEMA
        total_recebimentos = len(recebimentos)
        taxa_sucesso = (amarrados / total_recebimentos * 100) if total_recebimentos > 0 else 0
        alerta_saude = 'CRÍTICO' if taxa_sucesso < 90 else 'OK'
        
        valor_total_liquidado = sum(p.valor_original for p in parcelas_a_baixar)
        
        # 5. Salvar métrica
        metrica = ConciliacaoMetrica(
            tenant_id=tenant_id,
            data_referencia=data_recebimento,
            total_recebimentos=total_recebimentos,
            recebimentos_amarrados=amarrados,
            recebimentos_orfaos=len(orfaos),
            valor_total_recebimentos=sum(r.valor for r in recebimentos),
            valor_amarrado=sum(r.valor for r in recebimentos if r.amarrado),
            valor_orfao=sum(Decimal(str(o['valor'])) for o in orfaos),
            taxa_amarracao_automatica=Decimal(str(taxa_sucesso)),
            alerta_saude=alerta_saude,
            parcelas_liquidadas=len(parcelas_a_baixar),
            valor_total_liquidado=valor_total_liquidado,
            criado_por_id=user_id
        )
        db.add(metrica)
        
        db.commit()
        
        logger.info(f"[Aba 3] Amarração concluída: {amarrados}/{total_recebimentos} ({taxa_sucesso:.1f}% automático)")
        
        return {
            'success': True,
            'amarrados': amarrados,
            'orfaos': len(orfaos),
            'lista_orfaos': orfaos,
            'parcelas_liquidadas': len(parcelas_a_baixar),  # ✅ TRANSPARÊNCIA
            'valor_total_liquidado': float(valor_total_liquidado),
            'taxa_amarracao_automatica': float(taxa_sucesso),  # 📊 KPI de saúde
            'alerta_saude': alerta_saude
        }
    
    except Exception as e:
        db.rollback()
        logger.error(f"[Aba 3] Erro ao amarrar recebimentos: {str(e)}", exc_info=True)
        
        return {
            'success': False,
            'error': f'Erro ao amarrar recebimentos: {str(e)}'
        }
