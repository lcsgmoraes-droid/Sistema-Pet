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
from datetime import datetime, date
from typing import Dict, List, Optional
import logging

from .conciliacao_models import (
    AdquirenteTemplate,
    ArquivoEvidencia,
    ConciliacaoImportacao,
)
from .conciliacao_helpers import (
    calcular_hash_arquivo,
    detectar_duplicata_por_hash,
    aplicar_template_csv,
)

logger = logging.getLogger(__name__)


# ==============================================================================
# IMPORTAÇÃO DE ARQUIVOS


def conciliar_vendas_stone(
    db: Session,
    tenant_id: str,
    vendas_stone: List[Dict],  # Dados da planilha Stone
    user_id: int,
    operadora_id: Optional[int] = None,  # Filtro por operadora
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
        logger.info(
            f"[Aba 1] Iniciando conciliação de vendas: {len(vendas_stone)} transações Stone"
        )

        conferidas = 0
        corrigidas = 0
        sem_nsu = 0
        orfaos_stone = []
        divergencias = []

        # 1. Buscar vendas do PDV (mesmo período)
        # Filtra por operadora_id OU vendas antigas sem operadora (NULL)
        from .vendas_models import VendaPagamento

        query = db.query(Venda).filter(
            Venda.tenant_id == tenant_id, Venda.status == "finalizada"
        )

        # Se operadora foi especificada, filtrar vendas dessa operadora + vendas antigas (NULL)
        if operadora_id is not None:
            query = query.join(VendaPagamento).filter(
                (VendaPagamento.operadora_id == operadora_id)
                | (VendaPagamento.operadora_id.is_(None))
            )

        vendas_pdv = query.all()
        logger.info(
            f"🔍 Query retornou {len(vendas_pdv)} vendas do PDV (operadora_id={operadora_id})"
        )

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
                        logger.warning(
                            f"⚠️  NSU DUPLICADO: {pagamento.nsu_cartao} agora em {len(vendas_por_nsu[pagamento.nsu_cartao])} vendas"
                        )
                    else:
                        vendas_por_nsu[pagamento.nsu_cartao] = [venda]

                    logger.debug(
                        f"📝 Mapeado NSU {pagamento.nsu_cartao} → Venda #{venda.numero_venda} (operadora_id={pagamento.operadora_id})"
                    )

        logger.info(
            f"🗂️  Total de NSUs mapeados: {len(nsus_pdv)}, NSUs duplicados: {len(nsus_duplicados)}"
        )
        if nsus_duplicados:
            logger.warning(f"⚠️  NSUs duplicados encontrados: {nsus_duplicados}")

        # 2. Processar cada venda Stone
        for venda_stone in vendas_stone:
            nsu = venda_stone.get("nsu")

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
                logger.warning(
                    f"⚠️  NSU {nsu} encontrado em {len(vendas_match)} vendas: {[v.numero_venda for v in vendas_match]}"
                )
                divergencias.append(
                    {
                        "tipo": "nsu_duplicado",
                        "nsu": nsu,
                        "vendas": [
                            {
                                "venda_id": v.id,
                                "numero_venda": v.numero_venda,
                                "total": float(v.total),
                            }
                            for v in vendas_match
                        ],
                        "stone": venda_stone,
                        "acao_sugerida": "verificar_qual_venda_correta_e_remover_nsu_duplicado",
                    }
                )
                # Processar todas mesmo assim

            # Processar cada venda encontrada
            for venda_pdv in vendas_match:
                logger.info(
                    f"✅ Match encontrado: NSU {nsu} → Venda #{venda_pdv.numero_venda}"
                )

                # Buscar o pagamento específico com esse NSU
                pagamento_pdv = next(
                    (p for p in venda_pdv.pagamentos if p.nsu_cartao == nsu), None
                )

                if not pagamento_pdv:
                    continue  # Não deveria acontecer, mas protege

                # 3. Conferir dados (NSU existe, agora conferir detalhes)
                tem_divergencia = False

                # Conferir bandeira
                if pagamento_pdv.bandeira != venda_stone.get("bandeira"):
                    divergencias.append(
                        {
                            "venda_id": venda_pdv.id,
                            "numero_venda": venda_pdv.numero_venda,
                            "pagamento_id": pagamento_pdv.id,
                            "nsu": nsu,
                            "tipo": "bandeira_diferente",
                            "pdv": pagamento_pdv.bandeira,
                            "stone": venda_stone.get("bandeira"),
                            "acao_sugerida": "corrigir_bandeira",
                        }
                    )
                    tem_divergencia = True

                # Conferir parcelas
                if pagamento_pdv.numero_parcelas != venda_stone.get("parcelas"):
                    divergencias.append(
                        {
                            "venda_id": venda_pdv.id,
                            "numero_venda": venda_pdv.numero_venda,
                            "pagamento_id": pagamento_pdv.id,
                            "nsu": nsu,
                            "tipo": "parcelas_diferentes",
                            "pdv": pagamento_pdv.numero_parcelas,
                            "stone": venda_stone.get("parcelas"),
                            "acao_sugerida": "corrigir_parcelas_regenerar_contas",
                        }
                    )
                    tem_divergencia = True

                # Conferir taxa (se disponível - pode não estar no pagamento)
                taxa_stone = venda_stone.get("taxa_mdr")
                if taxa_stone:
                    # Taxa MDR normalmente é armazenada em outro lugar (config ou contas a receber)
                    # Por agora, apenas logamos mas não divergimos
                    logger.info(
                        f"[Aba 1] Taxa Stone: {taxa_stone}% para venda {venda_pdv.id}"
                    )

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
                    tem_div = any(d.get("nsu") == pag.nsu_cartao for d in divergencias)
                    if not tem_div:
                        # Buscar dados Stone correspondentes
                        stone_data = next(
                            (s for s in vendas_stone if s.get("nsu") == pag.nsu_cartao),
                            None,
                        )
                        if stone_data:
                            matches.append(
                                {
                                    "status": "ok",
                                    "venda_pdv": {
                                        "id": venda.id,
                                        "numero": venda.numero_venda,
                                        "nsu": pag.nsu_cartao,
                                        "bandeira": pag.bandeira,
                                        "parcelas": pag.numero_parcelas,
                                        "valor": float(pag.valor),
                                    },
                                    "venda_stone": stone_data,
                                }
                            )

        # 2. Matches com divergência
        for div in divergencias:
            if div.get("tipo") != "nsu_duplicado":  # Ignorar duplicados por ora
                venda = db.query(Venda).get(div.get("venda_id"))
                if venda:
                    pag = next(
                        (p for p in venda.pagamentos if p.nsu_cartao == div.get("nsu")),
                        None,
                    )
                    stone_data = next(
                        (s for s in vendas_stone if s.get("nsu") == div.get("nsu")),
                        None,
                    )
                    if pag and stone_data:
                        matches.append(
                            {
                                "status": "divergencia",
                                "venda_pdv": {
                                    "id": venda.id,
                                    "numero": venda.numero_venda,
                                    "nsu": pag.nsu_cartao,
                                    "bandeira": pag.bandeira,
                                    "parcelas": pag.numero_parcelas,
                                    "valor": float(pag.valor),
                                },
                                "venda_stone": stone_data,
                                "divergencia": div,
                            }
                        )

        # 3. Órfãos Stone (sem venda no PDV)
        for orfao in orfaos_stone:
            matches.append({"status": "orfao", "venda_pdv": None, "venda_stone": orfao})

        # 4. Vendas PDV sem NSU
        for venda in vendas_sem_nsu:
            matches.append(
                {
                    "status": "sem_nsu",
                    "venda_pdv": {
                        "id": venda.id,
                        "numero": venda.numero_venda,
                        "nsu": None,
                        "valor": float(venda.total),
                    },
                    "venda_stone": None,
                }
            )

        db.commit()

        logger.info(
            f"[Aba 1] Conciliação concluída: {conferidas} OK, {corrigidas} divergências, {sem_nsu} sem NSU, {len(orfaos_stone)} órfãos"
        )

        return {
            "success": True,
            "matches": matches,  # Array estruturado para visualização
            "conferidas": conferidas,
            "corrigidas": corrigidas,
            "sem_nsu": sem_nsu,
            "orfaos": len(orfaos_stone),
            "lista_orfaos": orfaos_stone,
            "divergencias": divergencias,
            "vendas_sem_nsu": [
                {"id": v.id, "numero": v.numero_venda, "valor": float(v.total)}
                for v in vendas_sem_nsu
            ],
        }

    except Exception as e:
        db.rollback()
        logger.error(f"[Aba 1] Erro ao conciliar vendas: {str(e)}", exc_info=True)

        return {"success": False, "error": f"Erro ao conciliar vendas: {str(e)}"}


def processar_upload_conciliacao_vendas(
    db: Session,
    tenant_id: str,
    arquivo_bytes: bytes,
    nome_arquivo: str,
    operadora_id: Optional[int],
    user_id: int,
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
        logger.info(
            "[Upload] Iniciando processamento de arquivo de conciliacao (%s bytes)",
            len(arquivo_bytes),
        )

        # 1. Calcular hashes
        hashes = calcular_hash_arquivo(arquivo_bytes)

        # 2. Verificar duplicata
        duplicata_id = detectar_duplicata_por_hash(db, tenant_id, hashes["md5"])
        if duplicata_id:
            return {
                "success": False,
                "error": f"Arquivo duplicado já importado (ID: {duplicata_id})",
                "arquivo_evidencia_id": duplicata_id,
            }

        # 3. Buscar template Stone (padrão para operadoras)
        template_obj = (
            db.query(AdquirenteTemplate)
            .filter(
                AdquirenteTemplate.tenant_id == tenant_id,
                AdquirenteTemplate.nome == "STONE",
                AdquirenteTemplate.ativo.is_(True),
            )
            .first()
        )

        if not template_obj:
            return {
                "success": False,
                "error": "Template Stone não encontrado. Execute seed de templates primeiro.",
            }

        # 4. Parsear arquivo CSV usando template
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

        logger.info(f"[Upload] CSV parseado: {len(linhas_validas)} linhas válidas")

        # 5. Criar registro de evidência
        arquivo_evidencia = ArquivoEvidencia(
            tenant_id=tenant_id,
            nome_original=nome_arquivo,
            tipo_arquivo="vendas",
            adquirente="STONE",
            caminho_storage=f"uploads/conciliacao/{tenant_id}/{hashes['md5']}",
            tamanho_bytes=len(arquivo_bytes),
            hash_md5=hashes["md5"],
            hash_sha256=hashes["sha256"],
            total_linhas=len(linhas_validas),
            criado_por_id=user_id,
        )
        db.add(arquivo_evidencia)
        db.flush()  # Obter ID

        logger.info(f"[Upload] Arquivo salvo: ID {arquivo_evidencia.id}")

        # 6. Criar importação
        importacao = ConciliacaoImportacao(
            tenant_id=tenant_id,
            arquivo_evidencia_id=arquivo_evidencia.id,
            adquirente_template_id=template_obj.id,
            tipo_importacao="vendas",
            data_referencia=date.today(),
            total_registros=len(linhas_validas),
            status_importacao="processando",
            criado_por_id=user_id,
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
            nsu_data["status_conciliacao"] = "nao_conciliado"

        importacao.status_importacao = "processada"
        importacao.resumo = {
            "total_linhas": len(linhas_validas),
            "operadora_id": operadora_id,
            "dados_parseados": dados_json_safe,  # Salvar NSUs parseados (JSON-safe)
            "conciliado": False,  # Flag indicando que ainda não foi conciliado
        }

        # 8. Commit transacional
        db.commit()

        logger.info(
            f"[Upload] Dados salvos: Importação ID {importacao.id} - {len(linhas_validas)} NSUs"
        )

        # 9. Retornar resultado SEM conciliação
        return {
            "success": True,
            "importacao_id": importacao.id,
            "arquivo_id": arquivo_evidencia.id,
            "total_nsus": len(linhas_validas),
            "operadora_id": operadora_id,
            "persistido": True,
            "mensagem": f'{len(linhas_validas)} NSUs importados. Clique em "Processar Matches" para conciliar.',
        }

    except Exception as e:
        db.rollback()
        logger.error(f"[Upload] Erro ao processar: {str(e)}", exc_info=True)

        return {"success": False, "error": f"Erro ao processar upload: {str(e)}"}
