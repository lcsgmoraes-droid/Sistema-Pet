"""
Serviço de processamento mensal com controle de idempotência.
Garante que provisões e fechamentos mensais rodem apenas 1x por período.

VERSÃO 2.4: Idempotência + Agendamento
"""

from sqlalchemy.orm import Session
from app.services.provisao_trabalhista_service import gerar_provisao_trabalhista_mensal
from app.controle_processamento_models import ControleProcessamentoMensal

import logging
logger = logging.getLogger(__name__)


def executar_provisao_trabalhista_mensal(
    db: Session,
    tenant_id: str,
    mes: int,
    ano: int,
    usuario_id: int = None,
    forcar_reprocessamento: bool = False
) -> dict:
    """
    Executa provisão trabalhista mensal com controle de idempotência.
    
    Garante que cada tenant/mês/ano seja processado apenas uma vez,
    evitando duplicidade de lançamentos no DRE.
    
    Args:
        db: Sessão do banco de dados
        tenant_id: ID do tenant
        mes: Mês de competência (1-12)
        ano: Ano de competência
        usuario_id: ID do usuário (opcional)
        forcar_reprocessamento: Se True, remove o lock e reprocessa
        
    Returns:
        dict com:
            - sucesso: bool
            - mensagem: str
            - ja_processado: bool
            - detalhes: dict (se processou)
    """
    
    logger.info(f"[PROCESSAMENTO MENSAL] Iniciando provisão trabalhista - tenant={tenant_id}, periodo={mes}/{ano}")
    
    # 1️⃣ Verificar se já foi processado
    ja_processado = (
        db.query(ControleProcessamentoMensal)
        .filter_by(
            tenant_id=tenant_id,
            tipo="PROVISAO_TRABALHISTA",
            mes=mes,
            ano=ano,
        )
        .first()
    )
    
    # 2️⃣ Se já rodou e não quer forçar → abortar
    if ja_processado and not forcar_reprocessamento:
        logger.warning(
            f"[PROCESSAMENTO MENSAL] ❌ Período já processado - "
            f"tenant={tenant_id}, periodo={mes}/{ano}, "
            f"processado_em={ja_processado.processado_em}"
        )
        return {
            "sucesso": False,
            "mensagem": f"Período {mes}/{ano} já foi processado em {ja_processado.processado_em}",
            "ja_processado": True,
            "processado_em": ja_processado.processado_em
        }
    
    # 3️⃣ Se forçar reprocessamento → remover registro anterior
    if forcar_reprocessamento and ja_processado:
        logger.info(
            f"[PROCESSAMENTO MENSAL] ♻️ Forçando reprocessamento - "
            f"removendo registro anterior para {mes}/{ano}"
        )
        db.delete(ja_processado)
        db.commit()
    
    try:
        # 4️⃣ Executar provisão trabalhista
        logger.info(f"[PROCESSAMENTO MENSAL] ▶️ Gerando provisões trabalhistas para {mes}/{ano}")
        
        resultado = gerar_provisao_trabalhista_mensal(
            db=db,
            tenant_id=tenant_id,
            mes=mes,
            ano=ano,
            usuario_id=usuario_id
        )
        
        # 5️⃣ Registrar processamento bem-sucedido
        registro = ControleProcessamentoMensal(
            tenant_id=tenant_id,
            tipo="PROVISAO_TRABALHISTA",
            mes=mes,
            ano=ano,
        )
        
        db.add(registro)
        db.commit()
        
        logger.info(
            f"[PROCESSAMENTO MENSAL] ✅ Provisão gerada com sucesso - "
            f"tenant={tenant_id}, periodo={mes}/{ano}"
        )
        
        return {
            "sucesso": True,
            "mensagem": f"Provisão trabalhista gerada para {mes}/{ano}",
            "ja_processado": False,
            "detalhes": resultado
        }
        
    except Exception as e:
        logger.error(
            f"[PROCESSAMENTO MENSAL] ❌ Erro ao gerar provisão - "
            f"tenant={tenant_id}, periodo={mes}/{ano}, erro={str(e)}"
        )
        db.rollback()
        raise


def verificar_periodo_ja_processado(
    db: Session,
    tenant_id: str,
    tipo: str,
    mes: int,
    ano: int
) -> bool:
    """
    Verifica se um período já foi processado para determinado tipo de processamento.
    
    Args:
        db: Sessão do banco
        tenant_id: ID do tenant
        tipo: Tipo de processamento (ex: PROVISAO_TRABALHISTA)
        mes: Mês (1-12)
        ano: Ano
        
    Returns:
        True se já foi processado, False caso contrário
    """
    registro = (
        db.query(ControleProcessamentoMensal)
        .filter_by(
            tenant_id=tenant_id,
            tipo=tipo,
            mes=mes,
            ano=ano
        )
        .first()
    )
    
    return registro is not None


def remover_registro_processamento(
    db: Session,
    tenant_id: str,
    tipo: str,
    mes: int,
    ano: int
) -> bool:
    """
    Remove registro de processamento mensal (permite reprocessamento).
    
    ⚠️ USO ADMINISTRATIVO: Use com cuidado para evitar duplicação de lançamentos.
    
    Args:
        db: Sessão do banco
        tenant_id: ID do tenant
        tipo: Tipo de processamento
        mes: Mês (1-12)
        ano: Ano
        
    Returns:
        True se removeu, False se não existia
    """
    registro = (
        db.query(ControleProcessamentoMensal)
        .filter_by(
            tenant_id=tenant_id,
            tipo=tipo,
            mes=mes,
            ano=ano
        )
        .first()
    )
    
    if registro:
        db.delete(registro)
        db.commit()
        logger.info(
            f"[CONTROLE PROCESSAMENTO] 🗑️ Registro removido - "
            f"tenant={tenant_id}, tipo={tipo}, periodo={mes}/{ano}"
        )
        return True
    
    return False
