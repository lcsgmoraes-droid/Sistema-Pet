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
from decimal import Decimal
from datetime import date
from typing import Dict, Optional, Any
import logging

from .conciliacao_models import (
    EmpresaParametros,
    AdquirenteTemplate,
    ArquivoEvidencia,
    ConciliacaoImportacao,
    ConciliacaoValidacao,
    ConciliacaoLog,
)
from .financeiro_models import ContaReceber
from .conciliacao_helpers import (
    calcular_hash_arquivo,
    detectar_duplicata_por_hash,
    calcular_confianca,
    calcular_percentual_divergencia,
    aplicar_template_csv,
    gerar_alertas_validacao,
    validar_duplicata_nsu,
    validar_data_futura,
    validar_valor_razoavel,
)

logger = logging.getLogger(__name__)


# ==============================================================================
# IMPORTAÇÃO DE ARQUIVOS


def importar_arquivo_operadora(
    db: Session,
    arquivo_bytes: bytes,
    nome_arquivo: str,
    adquirente_template_id: int,
    tenant_id: str,
    user_id: int,
    tipo_importacao: str = "recebimentos_detalhados",
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

        duplicata_id = detectar_duplicata_por_hash(db, hashes["md5"], tipo_importacao)
        if duplicata_id:
            return {
                "success": False,
                "error": f"Arquivo duplicado já importado (ArquivoEvidencia ID: {duplicata_id})",
                "arquivo_evidencia_id": duplicata_id,
            }

        # 2. Buscar template
        template_obj = (
            db.query(AdquirenteTemplate)
            .filter(
                AdquirenteTemplate.id == adquirente_template_id,
                AdquirenteTemplate.tenant_id == tenant_id,
                AdquirenteTemplate.ativo.is_(True),
            )
            .first()
        )

        if not template_obj:
            return {"success": False, "error": "Template não encontrado ou inativo"}

        # 3. Parsear arquivo usando template
        template_dict = {
            "separador": template_obj.separador,
            "encoding": template_obj.encoding,
            "tem_header": template_obj.tem_header,
            "pular_linhas": template_obj.pular_linhas,
            "mapeamento": template_obj.mapeamento,
            "transformacoes": template_obj.transformacoes,
        }

        linhas_validas, erros_parsing = aplicar_template_csv(
            arquivo_bytes, template_dict, validar_linhas=True
        )

        if not linhas_validas:
            return {
                "success": False,
                "error": "Nenhuma linha válida encontrada no arquivo",
                "erros": erros_parsing,
            }

        # PRINCÍPIO 1: Tudo em transação
        # Iniciar transação explícita

        # 4. Criar registro de evidência
        arquivo_evidencia = ArquivoEvidencia(
            tenant_id=tenant_id,
            nome_original=nome_arquivo,
            tipo_arquivo=tipo_importacao,
            adquirente=template_obj.nome,
            caminho_storage=f"uploads/conciliacao/{tenant_id}/{hashes['md5']}",
            tamanho_bytes=len(arquivo_bytes),
            hash_md5=hashes["md5"],
            hash_sha256=hashes["sha256"],
            total_linhas=len(linhas_validas),
            criado_por_id=user_id,
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
            status_importacao="processando",
            criado_por_id=user_id,
        )
        db.add(importacao)
        db.flush()

        # 6. Processar linhas e atualizar ContaReceber
        parcelas_confirmadas = 0
        parcelas_orfas = 0
        erros_validacao = []
        periodo_inicio = None
        periodo_fim = None
        total_valor = Decimal("0.00")

        for idx, linha in enumerate(linhas_validas, start=1):
            try:
                # PRINCÍPIO 4: Validar cada linha
                nsu = linha.get("nsu")
                data_pagamento = linha.get("data_pagamento")
                valor_liquido = linha.get("valor_liquido")

                # Validações
                if validar_duplicata_nsu(db, nsu, template_obj.nome, tenant_id):
                    erros_validacao.append(
                        f"Linha {idx}: NSU {nsu} já existe no sistema"
                    )
                    continue

                if not validar_data_futura(data_pagamento, dias_tolerancia=90):
                    erros_validacao.append(
                        f"Linha {idx}: Data {data_pagamento} muito no futuro"
                    )
                    continue

                if not validar_valor_razoavel(valor_liquido):
                    erros_validacao.append(
                        f"Linha {idx}: Valor {valor_liquido} fora da faixa razoável"
                    )
                    continue

                # Atualizar período
                if not periodo_inicio or data_pagamento < periodo_inicio:
                    periodo_inicio = data_pagamento
                if not periodo_fim or data_pagamento > periodo_fim:
                    periodo_fim = data_pagamento

                total_valor += valor_liquido

                # Buscar ContaReceber por NSU
                conta = (
                    db.query(ContaReceber)
                    .filter(
                        ContaReceber.tenant_id == tenant_id,
                        ContaReceber.nsu == nsu,
                        ContaReceber.adquirente == template_obj.nome,
                    )
                    .first()
                )

                if conta:
                    # ⚠️ ATENÇÃO CRÍTICA: NUNCA alterar status aqui!
                    # APENAS atualizar campos *_real e status_conciliacao

                    conta.taxa_mdr_real = linha.get("taxa_mdr")
                    conta.taxa_antecipacao_real = linha.get(
                        "taxa_antecipacao", Decimal("0.00")
                    )
                    conta.valor_liquido_real = valor_liquido
                    conta.data_vencimento_real = data_pagamento

                    # Calcular diferenças
                    if conta.taxa_mdr_estimada:
                        conta.diferenca_taxa = (
                            conta.taxa_mdr_real - conta.taxa_mdr_estimada
                        )

                    if conta.valor_liquido_estimado:
                        conta.diferenca_valor = (
                            conta.valor_liquido_real - conta.valor_liquido_estimado
                        )

                    # Atualizar status_conciliacao (NÃO status!)
                    conta.status_conciliacao = "confirmada_operadora"

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
        importacao.status_importacao = (
            "processada" if not erros_validacao else "parcial"
        )
        importacao.resumo = {
            "total_linhas": len(linhas_validas),
            "parcelas_confirmadas": parcelas_confirmadas,
            "parcelas_orfas": parcelas_orfas,
            "erros": erros_validacao[:50],  # Primeiros 50 erros
            "periodo": {
                "inicio": periodo_inicio.isoformat() if periodo_inicio else None,
                "fim": periodo_fim.isoformat() if periodo_fim else None,
            },
        }

        # PRINCÍPIO 3: Nenhuma mudança sem log
        # 8. Criar log de auditoria
        log = ConciliacaoLog(
            tenant_id=tenant_id,
            versao_conciliacao=1,
            acao="importar_arquivo_operadora",
            status_acao="sucesso" if parcelas_confirmadas > 0 else "parcial",
            arquivos_utilizados=[
                {
                    "nome": nome_arquivo,
                    "tipo": tipo_importacao,
                    "hash_md5": hashes["md5"],
                }
            ],
            quantidades={
                "total_linhas": len(linhas_validas),
                "parcelas_confirmadas": parcelas_confirmadas,
                "parcelas_orfas": parcelas_orfas,
                "erros": len(erros_validacao),
            },
            criado_por_id=user_id,
        )
        db.add(log)

        # PRINCÍPIO 1: Commit da transação
        db.commit()

        return {
            "success": True,
            "importacao_id": importacao.id,
            "arquivo_evidencia_id": arquivo_evidencia.id,
            "total_linhas": len(linhas_validas),
            "linhas_validas": len(linhas_validas),
            "linhas_com_erro": len(erros_parsing),
            "parcelas_confirmadas": parcelas_confirmadas,
            "parcelas_orfas": parcelas_orfas,
            "erros": erros_parsing + erros_validacao,
            "periodo": {
                "inicio": periodo_inicio.isoformat() if periodo_inicio else None,
                "fim": periodo_fim.isoformat() if periodo_fim else None,
            },
            "total_valor": float(total_valor),
        }

    except Exception as e:
        # PRINCÍPIO 2: Rollback obrigatório
        db.rollback()
        logger.error(f"Erro ao importar arquivo operadora: {str(e)}", exc_info=True)

        return {"success": False, "error": f"Erro ao processar importação: {str(e)}"}


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
    user_id: int,
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
        parametros = (
            db.query(EmpresaParametros)
            .filter(EmpresaParametros.tenant_id == tenant_id)
            .first()
        )

        if not parametros:
            # Criar parâmetros default
            parametros = EmpresaParametros(tenant_id=tenant_id)
            db.add(parametros)
            db.flush()

        # 2. Calcular totais
        total_pagamentos = Decimal("0.00")
        total_recebimentos = Decimal("0.00")
        quantidade_parcelas = 0
        parcelas_confirmadas = 0
        parcelas_orfas = 0

        # Total de pagamentos (arquivo operadora)
        if importacao_pagamentos_id:
            importacao_pag = db.query(ConciliacaoImportacao).get(
                importacao_pagamentos_id
            )
            if importacao_pag and importacao_pag.resumo:
                total_pagamentos = Decimal(str(importacao_pag.total_valor or 0))
                parcelas_confirmadas = importacao_pag.resumo.get(
                    "parcelas_confirmadas", 0
                )
                parcelas_orfas = importacao_pag.resumo.get("parcelas_orfas", 0)

        # Total de recebimentos (ContaReceber - PDV)
        contas = (
            db.query(ContaReceber)
            .filter(
                ContaReceber.tenant_id == tenant_id,
                ContaReceber.adquirente == adquirente,
                ContaReceber.data_vencimento_real == data_referencia,
                ContaReceber.status_conciliacao == "confirmada_operadora",
            )
            .all()
        )

        for conta in contas:
            total_recebimentos += conta.valor_liquido_real or Decimal("0.00")
            quantidade_parcelas += 1

        # 3. Calcular diferenças
        diferenca_pag_rec = total_pagamentos - total_recebimentos
        percentual_div = calcular_percentual_divergencia(
            diferenca_pag_rec, total_pagamentos
        )

        # 4. Classificar confiança
        confianca, pode_processar, requer_confirmacao = calcular_confianca(
            diferenca_total=abs(diferenca_pag_rec),
            total_referencia=total_pagamentos,
            tolerancia_automatica=parametros.tolerancia_conciliacao,
            tolerancia_media=parametros.tolerancia_conciliacao_media,
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
            diferenca_ofx_pagamentos=Decimal("0.00"),  # OFX será implementado depois
            diferenca_pagamentos_recebimentos=diferenca_pag_rec,
            parcelas_orfas=parcelas_orfas,
            total_parcelas=quantidade_parcelas,
            confianca=confianca,
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
            status_validacao="pendente" if requer_confirmacao else "concluida",
            alertas=alertas,
            quantidade_parcelas=quantidade_parcelas,
            parcelas_confirmadas=parcelas_confirmadas,
            parcelas_orfas=parcelas_orfas,
            criado_por_id=user_id,
        )
        db.add(validacao)
        db.flush()

        # PRINCÍPIO 3: Log obrigatório
        log = ConciliacaoLog(
            tenant_id=tenant_id,
            conciliacao_validacao_id=validacao.id,
            versao_conciliacao=1,
            acao="validar_importacao_cascata",
            status_acao="sucesso",
            quantidades={
                "parcelas": quantidade_parcelas,
                "confirmadas": parcelas_confirmadas,
                "orfas": parcelas_orfas,
            },
            diferencas={
                "pagamentos_vs_recebimentos": float(diferenca_pag_rec),
                "percentual": float(percentual_div),
            },
            criado_por_id=user_id,
        )
        db.add(log)

        db.commit()

        return {
            "success": True,
            "validacao_id": validacao.id,
            "confianca": confianca,
            "pode_processar": pode_processar,
            "requer_confirmacao": requer_confirmacao,
            "totais": {
                "pagamentos": float(total_pagamentos),
                "recebimentos": float(total_recebimentos),
            },
            "diferencas": {
                "pagamentos_vs_recebimentos": float(diferenca_pag_rec),
                "percentual": float(percentual_div),
            },
            "quantidades": {
                "parcelas": quantidade_parcelas,
                "confirmadas": parcelas_confirmadas,
                "orfas": parcelas_orfas,
            },
            "alertas": alertas,
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao validar cascata: {str(e)}", exc_info=True)

        return {"success": False, "error": f"Erro ao validar: {str(e)}"}


# ==============================================================================
# LIQUIDAÇÃO (REALIZAÇÃO FINANCEIRA)
# ==============================================================================


def processar_conciliacao(
    db: Session,
    validacao_id: int,
    tenant_id: str,
    user_id: int,
    confirmacao_usuario: bool = False,
    justificativa: Optional[str] = None,
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
        validacao = (
            db.query(ConciliacaoValidacao)
            .filter(
                ConciliacaoValidacao.id == validacao_id,
                ConciliacaoValidacao.tenant_id == tenant_id,
            )
            .first()
        )

        if not validacao:
            return {"success": False, "error": "Validação não encontrada"}

        # 2. Verificar se pode processar
        if not validacao.pode_processar:
            return {"success": False, "error": "Validação não permite processamento"}

        # 3. Verificar confirmação
        if validacao.requer_confirmacao and not confirmacao_usuario:
            return {
                "success": False,
                "error": "Validação requer confirmação do usuário",
                "requer_confirmacao": True,
                "confianca": validacao.confianca,
            }

        # 4. Verificar justificativa (obrigatória para BAIXA)
        if validacao.confianca == "BAIXA" and not justificativa:
            return {
                "success": False,
                "error": "Confiança BAIXA requer justificativa explícita",
            }

        # 5. Buscar parcelas confirmadas COM LOCK PESSIMISTA (evita concorrência)
        # CORREÇÃO CRÍTICA #2: SELECT FOR UPDATE evita dois usuários processarem simultaneamente
        parcelas = (
            db.query(ContaReceber)
            .filter(
                ContaReceber.tenant_id == tenant_id,
                ContaReceber.adquirente == validacao.adquirente,
                ContaReceber.data_vencimento_real == validacao.data_referencia,
                ContaReceber.status_conciliacao == "confirmada_operadora",
                # CORREÇÃO CRÍTICA #1: Evita reprocessamento se já foi vinculada a outra validação
                ContaReceber.validacao_id.is_(None),
            )
            .with_for_update()
            .all()
        )  # ← LOCK PESSIMISTA

        if not parcelas:
            return {
                "success": False,
                "error": "Nenhuma parcela encontrada para processar (podem já estar vinculadas a outra validação)",
            }

        # 6. Processar parcelas (avançar etapa)
        parcelas_processadas = 0
        valor_total = Decimal("0.00")

        for parcela in parcelas:
            # ⚠️ AGORA SIM: avançar parcela para próxima etapa
            # TODO (Fase 5): Implementar função vincular_movimentacao_bancaria()
            # Por enquanto, apenas avançar status

            # CORREÇÃO CRÍTICA #1: Vincular com validação (evita dupla movimentação)
            parcela.validacao_id = validacao_id
            parcela.status_conciliacao = "aguardando_lote"  # Avançar etapa
            parcela.versao_conciliacao = (parcela.versao_conciliacao or 0) + 1

            parcelas_processadas += 1
            valor_total += parcela.valor_liquido_real or Decimal("0.00")

        # 7. Atualizar validação
        validacao.status_validacao = "concluida"
        validacao.versao_validacao = (validacao.versao_validacao or 0) + 1

        # 8. Log COMPLETO
        log = ConciliacaoLog(
            tenant_id=tenant_id,
            conciliacao_validacao_id=validacao_id,
            versao_conciliacao=(validacao.versao_validacao),
            acao="processar_conciliacao",
            status_acao="sucesso",
            quantidades={
                "parcelas_processadas": parcelas_processadas,
                "valor_total": float(valor_total),
                "validacao_id_vinculada": validacao_id,  # Para auditoria
            },
            motivo=justificativa,
            criado_por_id=user_id,
        )
        db.add(log)

        db.commit()

        return {
            "success": True,
            "parcelas_processadas": parcelas_processadas,
            "valor_total_processado": float(valor_total),
            "validacao_id": validacao_id,
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao processar conciliação: {str(e)}", exc_info=True)

        return {"success": False, "error": f"Erro ao processar: {str(e)}"}


# ==============================================================================
# REVERSÃO
# ==============================================================================


def reverter_conciliacao(
    db: Session, validacao_id: int, tenant_id: str, user_id: int, motivo: str
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
            return {"success": False, "error": "Motivo da reversão é obrigatório"}

        # Buscar validação
        validacao = (
            db.query(ConciliacaoValidacao)
            .filter(
                ConciliacaoValidacao.id == validacao_id,
                ConciliacaoValidacao.tenant_id == tenant_id,
            )
            .first()
        )

        if not validacao:
            return {"success": False, "error": "Validação não encontrada"}

        if validacao.status_validacao != "concluida":
            return {"success": False, "error": "Validação não foi concluída ainda"}

        # Buscar parcelas
        parcelas = (
            db.query(ContaReceber)
            .filter(
                ContaReceber.tenant_id == tenant_id,
                ContaReceber.adquirente == validacao.adquirente,
                ContaReceber.data_vencimento_real == validacao.data_referencia,
                ContaReceber.status_conciliacao.in_(
                    ["aguardando_lote", "em_lote", "liquidada"]
                ),
            )
            .all()
        )

        # Reverter estado
        parcelas_revertidas = 0
        for parcela in parcelas:
            parcela.status_conciliacao = (
                "confirmada_operadora"  # Volta ao estado anterior
            )
            parcela.versao_conciliacao = (parcela.versao_conciliacao or 0) + 1
            parcelas_revertidas += 1

        # Atualizar validação
        validacao.status_validacao = "divergente"

        # Log da reversão
        log = ConciliacaoLog(
            tenant_id=tenant_id,
            conciliacao_validacao_id=validacao_id,
            versao_conciliacao=(validacao.parcelas_confirmadas or 0) + 1,
            acao="reverter_conciliacao",
            status_acao="revertido",
            quantidades={"parcelas_revertidas": parcelas_revertidas},
            motivo=motivo,
            criado_por_id=user_id,
        )
        db.add(log)

        db.commit()

        return {"success": True, "parcelas_revertidas": parcelas_revertidas}

    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao reverter conciliação: {str(e)}", exc_info=True)

        return {"success": False, "error": f"Erro ao reverter: {str(e)}"}
