"""
Serviço de Acerto Financeiro de Parceiros
Consolidação periódica automática de comissões com compensação de dívidas
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
import json

from app.models import Cliente, AcertoParceiro, EmailTemplate, EmailEnvio, Tenant
from app.tenancy.context import get_current_tenant, tenant_context
from app.tenancy.rls import sync_rls_tenant
from app.utils.logger import logger


class AcertoService:
    """Serviço para gerenciamento de acertos financeiros de parceiros"""

    @staticmethod
    def calcular_periodo_acerto(
        tipo_acerto: str, dia_acerto: int, data_referencia: Optional[datetime] = None
    ) -> Tuple[datetime, datetime]:
        """
        Calcula o período (início, fim) do acerto baseado no tipo e dia configurados.

        Args:
            tipo_acerto: mensal, quinzenal, semanal, manual
            dia_acerto: Dia do mês/semana/quinzena
            data_referencia: Data de referência (default: hoje)

        Returns:
            (periodo_inicio, periodo_fim) em datetime
        """
        if data_referencia is None:
            data_referencia = datetime.now()

        if tipo_acerto == "mensal":
            # Acerto mensal: do dia X do mês anterior até dia X-1 do mês atual
            # Ex: dia_acerto=1 → de 01/12 até 31/12
            periodo_fim = data_referencia.replace(
                day=dia_acerto, hour=23, minute=59, second=59, microsecond=999999
            )

            # Calcular mês anterior
            if periodo_fim.month == 1:
                periodo_inicio = periodo_fim.replace(
                    year=periodo_fim.year - 1,
                    month=12,
                    day=dia_acerto,
                    hour=0,
                    minute=0,
                    second=0,
                    microsecond=0,
                )
            else:
                periodo_inicio = periodo_fim.replace(
                    month=periodo_fim.month - 1,
                    day=dia_acerto,
                    hour=0,
                    minute=0,
                    second=0,
                    microsecond=0,
                )

        elif tipo_acerto == "quinzenal":
            # Acerto quinzenal: a cada 15 dias
            # dia_acerto=1 → dias 1 e 16
            # dia_acerto=5 → dias 5 e 20
            if dia_acerto <= 15:
                periodo_fim = data_referencia.replace(
                    day=dia_acerto, hour=23, minute=59, second=59, microsecond=999999
                )
                periodo_inicio = periodo_fim - timedelta(days=15)
            else:
                periodo_fim = data_referencia.replace(
                    day=dia_acerto, hour=23, minute=59, second=59, microsecond=999999
                )
                periodo_inicio = periodo_fim - timedelta(days=15)

        elif tipo_acerto == "semanal":
            # Acerto semanal: dia_acerto representa dia da semana (0=segunda, 6=domingo)
            periodo_fim = data_referencia.replace(
                hour=23, minute=59, second=59, microsecond=999999
            )
            periodo_inicio = periodo_fim - timedelta(days=7)

        else:  # manual
            # Acerto manual: usa mês completo como padrão
            periodo_fim = data_referencia.replace(
                hour=23, minute=59, second=59, microsecond=999999
            )
            periodo_inicio = periodo_fim.replace(
                day=1, hour=0, minute=0, second=0, microsecond=0
            )

        return (periodo_inicio, periodo_fim)

    @staticmethod
    def gerar_acerto(
        db: Session,
        parceiro_id: int,
        tenant_id: UUID,
        user_id: int,
        data_acerto: Optional[datetime] = None,
        forcar_manual: bool = False,
    ) -> Dict:
        """
        Gera um acerto financeiro para o parceiro.

        FLUXO:
        1. Valida se parceiro existe e está ativo
        2. Calcula período do acerto
        3. **VERIFICA IDEMPOTÊNCIA** (se já existe acerto no período)
        4. Busca TODAS comissões pendentes (status != 'pago')
        5. Fecha cada comissão aplicando compensação automática
        6. Consolida valores totais
        7. Cria registro de acerto
        8. Prepara dados para email

        Args:
            db: Sessão do banco
            parceiro_id: ID do parceiro
            user_id: ID do usuário (multi-tenant)
            data_acerto: Data do acerto (default: hoje)
            forcar_manual: Se True, ignora configuração e faz acerto manual

        Returns:
            Dict com resultado do acerto e dados para email
        """
        if data_acerto is None:
            data_acerto = datetime.now()

        sync_rls_tenant(db, tenant_id)

        # 1. VALIDAR PARCEIRO
        parceiro = (
            db.query(Cliente)
            .filter(
                Cliente.id == parceiro_id,
                Cliente.tenant_id == tenant_id,
                Cliente.parceiro_ativo.is_(True),
            )
            .first()
        )

        if not parceiro:
            raise ValueError(f"Parceiro {parceiro_id} não encontrado ou inativo")

        # 2. CALCULAR PERÍODO
        if forcar_manual:
            tipo_acerto = "manual"
            dia_acerto = 1
        else:
            tipo_acerto = parceiro.parceiro_tipo_acerto or "mensal"
            dia_acerto = parceiro.parceiro_dia_acerto or 1

        periodo_inicio, periodo_fim = AcertoService.calcular_periodo_acerto(
            tipo_acerto, dia_acerto, data_acerto
        )

        # 3. **IDEMPOTÊNCIA** - Verificar se já existe acerto neste período
        acerto_existente = (
            db.query(AcertoParceiro)
            .filter(
                AcertoParceiro.parceiro_id == parceiro_id,
                AcertoParceiro.tenant_id == tenant_id,
                AcertoParceiro.user_id == user_id,
                AcertoParceiro.periodo_inicio == periodo_inicio,
                AcertoParceiro.periodo_fim == periodo_fim,
                AcertoParceiro.status.in_(["processado", "gerado"]),
            )
            .first()
        )

        if acerto_existente:
            # Acerto já foi gerado para este período
            return {
                "sucesso": True,
                "acerto_id": acerto_existente.id,
                "comissoes_fechadas": acerto_existente.comissoes_fechadas,
                "valor_bruto": float(acerto_existente.valor_bruto),
                "valor_compensado": float(acerto_existente.valor_compensado),
                "valor_liquido": float(acerto_existente.valor_liquido),
                "mensagem": "Acerto já foi gerado anteriormente para este período",
                "idempotente": True,
            }

        # 4. BUSCAR COMISSÕES PENDENTES
        # IMPORTANTE: Buscar no módulo correto (comissoes_routes ou comissoes_avancadas_routes)
        # Aqui usamos query direta para pegar IDs das comissões
        from app.comissoes_models import ComissaoItem

        comissoes_pendentes = (
            db.query(ComissaoItem)
            .filter(
                ComissaoItem.parceiro_id == parceiro_id,
                ComissaoItem.tenant_id == tenant_id,
                ComissaoItem.status != "pago",
                ComissaoItem.created_at >= periodo_inicio,
                ComissaoItem.created_at <= periodo_fim,
            )
            .all()
        )

        if not comissoes_pendentes:
            # Sem comissões pendentes no período
            observacoes = json.dumps(
                {
                    "mensagem": "Nenhuma comissão pendente no período",
                    "periodo": f"{periodo_inicio.strftime('%d/%m/%Y')} - {periodo_fim.strftime('%d/%m/%Y')}",
                },
                ensure_ascii=False,
            )

            acerto = AcertoParceiro(
                parceiro_id=parceiro_id,
                tenant_id=tenant_id,
                user_id=user_id,
                data_acerto=data_acerto,
                periodo_inicio=periodo_inicio,
                periodo_fim=periodo_fim,
                tipo_acerto=tipo_acerto,
                comissoes_fechadas=0,
                valor_bruto=Decimal("0.00"),
                valor_compensado=Decimal("0.00"),
                valor_liquido=Decimal("0.00"),
                status="processado",
                observacoes=observacoes,
            )
            db.add(acerto)
            db.commit()
            db.refresh(acerto)

            return {
                "sucesso": True,
                "acerto_id": acerto.id,
                "comissoes_fechadas": 0,
                "valor_bruto": 0.0,
                "valor_compensado": 0.0,
                "valor_liquido": 0.0,
                "mensagem": "Nenhuma comissão pendente no período",
            }

        # 4. FECHAR CADA COMISSÃO COM COMPENSAÇÃO
        # IMPORTANTE: Importar e usar fechar_com_pagamento_parcial
        # Por enquanto, simulamos o fechamento (será integrado depois)

        total_bruto = Decimal("0.00")
        total_compensado = Decimal("0.00")
        comissoes_fechadas_count = 0
        detalhes_fechamentos = []

        for comissao in comissoes_pendentes:
            # TODO: Chamar fechar_com_pagamento_parcial(comissao.id, db)
            # Por enquanto, apenas marca como processada
            valor_comissao = Decimal(str(comissao.valor_comissao or 0))
            total_bruto += valor_comissao
            comissoes_fechadas_count += 1

            detalhes_fechamentos.append(
                {
                    "comissao_id": comissao.id,
                    "valor": float(valor_comissao),
                    "status": "simulado",  # Será 'fechado' quando integrar
                }
            )

        # 5. CONSOLIDAR VALORES
        valor_liquido = total_bruto - total_compensado

        # 6. CRIAR REGISTRO DE ACERTO
        observacoes = json.dumps(
            {
                "detalhes_fechamentos": detalhes_fechamentos,
                "periodo": f"{periodo_inicio.strftime('%d/%m/%Y')} - {periodo_fim.strftime('%d/%m/%Y')}",
            },
            ensure_ascii=False,
        )

        acerto = AcertoParceiro(
            parceiro_id=parceiro_id,
            tenant_id=tenant_id,
            user_id=user_id,
            data_acerto=data_acerto,
            periodo_inicio=periodo_inicio,
            periodo_fim=periodo_fim,
            tipo_acerto=tipo_acerto,
            comissoes_fechadas=comissoes_fechadas_count,
            valor_bruto=total_bruto,
            valor_compensado=total_compensado,
            valor_liquido=valor_liquido,
            status="processado",
            observacoes=observacoes,
        )
        db.add(acerto)
        db.commit()
        db.refresh(acerto)

        # 7. PREPARAR DADOS PARA EMAIL
        dados_email = {
            "parceiro_nome": parceiro.nome,
            "periodo_inicio": periodo_inicio.strftime("%d/%m/%Y"),
            "periodo_fim": periodo_fim.strftime("%d/%m/%Y"),
            "comissoes_fechadas": comissoes_fechadas_count,
            "valor_bruto": f"R$ {float(total_bruto):.2f}",
            "valor_compensado": f"R$ {float(total_compensado):.2f}",
            "valor_liquido": f"R$ {float(valor_liquido):.2f}",
            "data_acerto": data_acerto.strftime("%d/%m/%Y %H:%M"),
        }

        return {
            "sucesso": True,
            "acerto_id": acerto.id,
            "comissoes_fechadas": comissoes_fechadas_count,
            "valor_bruto": float(total_bruto),
            "valor_compensado": float(total_compensado),
            "valor_liquido": float(valor_liquido),
            "dados_email": dados_email,
            "parceiro": {
                "id": parceiro.id,
                "nome": parceiro.nome,
                "email": parceiro.parceiro_email_principal or parceiro.email,
                "emails_copia": parceiro.parceiro_emails_copia,
                "notificar": parceiro.parceiro_notificar,
            },
        }


class EmailService:
    """Serviço para renderização e envio de emails"""

    @staticmethod
    def renderizar_template(
        db: Session, codigo_template: str, placeholders: Dict[str, str], user_id: int
    ) -> Tuple[str, str, str]:
        """
        Renderiza um template de email substituindo placeholders.

        Args:
            db: Sessão do banco
            codigo_template: Código do template (ex: ACERTO_PARCEIRO)
            placeholders: Dicionário com valores para substituição
            user_id: ID do usuário (multi-tenant)

        Returns:
            (assunto_renderizado, corpo_html_renderizado, corpo_texto_renderizado)
        """
        template = (
            db.query(EmailTemplate)
            .filter(
                EmailTemplate.codigo == codigo_template,
                EmailTemplate.user_id == user_id,
                EmailTemplate.ativo.is_(True),
            )
            .first()
        )

        if not template:
            raise ValueError(f"Template '{codigo_template}' não encontrado ou inativo")

        # Substituir placeholders no formato {{placeholder}}
        def substituir(texto: str) -> str:
            if not texto:
                return ""
            for chave, valor in placeholders.items():
                texto = texto.replace(f"{{{{{chave}}}}}", str(valor))
            return texto

        assunto = substituir(template.assunto)
        corpo_html = substituir(template.corpo_html)
        corpo_texto = substituir(template.corpo_texto) if template.corpo_texto else ""

        return (assunto, corpo_html, corpo_texto)

    @staticmethod
    def enviar_email(
        destinatarios: List[str],
        assunto: str,
        corpo_html: str,
        corpo_texto: Optional[str] = None,
    ) -> Dict:
        """
        Envia email para destinatários.

        TODO: Integrar com serviço SMTP ou API de email (SendGrid, AWS SES, etc)

        Args:
            destinatarios: Lista de emails
            assunto: Assunto do email
            corpo_html: Corpo em HTML
            corpo_texto: Corpo em texto puro (fallback)

        Returns:
            Dict com status do envio
        """
        # PLACEHOLDER: Implementar integração real
        logger.info("📧 EMAIL SIMULADO")
        logger.info(f"Para: {', '.join(destinatarios)}")
        logger.info(f"Assunto: {assunto}")
        logger.info(f"Corpo HTML: {len(corpo_html)} caracteres")
        logger.info(f"Corpo Texto: {len(corpo_texto or '')} caracteres")

        return {
            "sucesso": True,
            "destinatarios": destinatarios,
            "mensagem": "Email enviado com sucesso (SIMULADO)",
        }


class EmailQueueService:
    """Serviço para gerenciamento de fila de emails com governança"""

    @staticmethod
    def _resolver_tenant_id(tenant_id=None) -> Optional[UUID]:
        resolved = get_current_tenant() if tenant_id is None else tenant_id
        if resolved is None or resolved == "":
            return None
        return UUID(str(resolved))

    @staticmethod
    def enfileirar_email(
        db: Session,
        parceiro_id: int,
        user_id: int,
        assunto: str,
        corpo_html: str,
        corpo_texto: Optional[str],
        destinatarios: List[str],
        acerto_id: Optional[int] = None,
        template_id: Optional[int] = None,
    ) -> EmailEnvio:
        """
        Enfileira email para envio posterior.

        Args:
            db: Sessão do banco
            parceiro_id: ID do parceiro
            user_id: ID do usuário
            assunto: Assunto do email
            corpo_html: Corpo HTML renderizado
            corpo_texto: Corpo texto renderizado
            destinatarios: Lista de emails
            acerto_id: ID do acerto relacionado (opcional)
            template_id: ID do template usado (opcional)

        Returns:
            EmailEnvio criado
        """
        email_envio = EmailEnvio(
            parceiro_id=parceiro_id,
            acerto_id=acerto_id,
            template_id=template_id,
            user_id=user_id,
            destinatarios=", ".join(destinatarios),
            assunto=assunto,
            corpo_html=corpo_html,
            corpo_texto=corpo_texto,
            status="pendente",
            tentativas=0,
            max_tentativas=3,
            data_enfileiramento=datetime.now(),
            proxima_tentativa=datetime.now(),  # Tentar imediatamente
        )

        db.add(email_envio)
        db.commit()
        db.refresh(email_envio)

        return email_envio

    @staticmethod
    def processar_fila(db: Session, limite: int = 10, tenant_id=None) -> Dict:
        tenant_uuid = EmailQueueService._resolver_tenant_id(tenant_id)
        if tenant_uuid is None:
            raise ValueError("tenant_id e obrigatorio para processar a fila de emails")

        with tenant_context(tenant_uuid) as scoped_tenant:
            sync_rls_tenant(db, scoped_tenant)
            return EmailQueueService._processar_fila_tenant(
                db,
                limite=limite,
                scoped_tenant=scoped_tenant,
            )

    @staticmethod
    def _processar_fila_tenant(
        db: Session, limite: int = 10, scoped_tenant=None
    ) -> Dict:
        """
        Processa emails pendentes na fila.

        Args:
            db: Sessão do banco
            limite: Quantidade máxima de emails a processar

        Returns:
            Dict com estatísticas do processamento
        """
        # Buscar emails pendentes
        agora = datetime.now()

        emails_pendentes = (
            db.query(EmailEnvio)
            .filter(
                EmailEnvio.status == "pendente",
                EmailEnvio.tentativas < EmailEnvio.max_tentativas,
                EmailEnvio.proxima_tentativa <= agora,
                EmailEnvio.tenant_id == scoped_tenant,
            )
            .order_by(EmailEnvio.data_enfileiramento)
            .limit(limite)
            .all()
        )

        enviados = 0
        erros = 0

        for email in emails_pendentes:
            try:
                # Tentar enviar
                destinatarios_list = [e.strip() for e in email.destinatarios.split(",")]

                resultado = EmailService.enviar_email(
                    destinatarios=destinatarios_list,
                    assunto=email.assunto,
                    corpo_html=email.corpo_html,
                    corpo_texto=email.corpo_texto,
                )

                if resultado.get("sucesso"):
                    # Sucesso
                    email.status = "enviado"
                    email.data_envio = datetime.now()
                    email.ultimo_erro = None
                    enviados += 1
                else:
                    # Falha
                    raise Exception(resultado.get("erro", "Erro desconhecido"))

            except Exception as e:
                # Registrar erro
                email.tentativas += 1
                email.ultimo_erro = str(e)

                # Atualizar histórico
                historico = (
                    json.loads(email.historico_erros) if email.historico_erros else []
                )
                historico.append(
                    {
                        "tentativa": email.tentativas,
                        "data": datetime.now().isoformat(),
                        "erro": str(e),
                    }
                )
                email.historico_erros = json.dumps(historico, ensure_ascii=False)

                # Decidir próxima ação
                if email.tentativas >= email.max_tentativas:
                    email.status = "erro"
                    email.observacoes = f"Falhou após {email.tentativas} tentativas"
                else:
                    # Agendar próxima tentativa (exponencial backoff: 5min, 30min, 2h)
                    minutos_espera = (
                        [5, 30, 120][email.tentativas - 1]
                        if email.tentativas <= 3
                        else 120
                    )
                    email.proxima_tentativa = datetime.now() + timedelta(
                        minutes=minutos_espera
                    )

                erros += 1

            db.commit()

        return {
            "processados": len(emails_pendentes),
            "enviados": enviados,
            "erros": erros,
        }

    @staticmethod
    def processar_fila_global(db: Session, limite: int = 10) -> Dict:
        """
        Processa a fila de emails tenant por tenant.

        Uso esperado para schedulers globais, sem request HTTP autenticada.
        """
        tenant_rows = (
            db.query(Tenant.id)
            .filter(Tenant.status == "active")
            .order_by(Tenant.created_at.asc())
            .all()
        )

        processados = 0
        enviados = 0
        erros = 0
        tenants_processados = 0

        for row in tenant_rows:
            if processados >= limite:
                break

            tenant_id_raw = (
                row[0] if isinstance(row, tuple) else getattr(row, "id", row)
            )
            try:
                tenant_uuid = UUID(str(tenant_id_raw))
            except (TypeError, ValueError):
                logger.warning(
                    "[EMAIL] Ignorando tenant_id invalido na fila: %s", tenant_id_raw
                )
                continue

            restante = max(0, limite - processados)
            with tenant_context(tenant_uuid):
                resultado = EmailQueueService.processar_fila(
                    db,
                    limite=restante,
                    tenant_id=tenant_uuid,
                )

            processados += int(resultado.get("processados", 0) or 0)
            enviados += int(resultado.get("enviados", 0) or 0)
            erros += int(resultado.get("erros", 0) or 0)
            tenants_processados += 1

        return {
            "processados": processados,
            "enviados": enviados,
            "erros": erros,
            "tenants_processados": tenants_processados,
        }

    @staticmethod
    def reenviar_email(db: Session, email_id: int, tenant_id=None) -> Dict:
        tenant_uuid = EmailQueueService._resolver_tenant_id(tenant_id)
        if tenant_uuid is None:
            raise ValueError("tenant_id e obrigatorio para reenviar email")

        with tenant_context(tenant_uuid) as scoped_tenant:
            sync_rls_tenant(db, scoped_tenant)
            return EmailQueueService._reenviar_email_tenant(
                db,
                email_id=email_id,
                scoped_tenant=scoped_tenant,
            )

    @staticmethod
    def _reenviar_email_tenant(db: Session, email_id: int, scoped_tenant=None) -> Dict:
        """
        Reenvia um email que falhou anteriormente.

        Args:
            db: Sessão do banco
            email_id: ID do email a reenviar

        Returns:
            Dict com resultado do reenvio
        """
        email = (
            db.query(EmailEnvio)
            .filter(EmailEnvio.id == email_id, EmailEnvio.tenant_id == scoped_tenant)
            .first()
        )

        if not email:
            raise ValueError(f"Email {email_id} não encontrado")

        if email.status == "enviado":
            return {
                "sucesso": False,
                "mensagem": "Email já foi enviado com sucesso anteriormente",
            }

        # Resetar para reenvio
        email.status = "pendente"
        email.tentativas = 0
        email.proxima_tentativa = datetime.now()
        email.ultimo_erro = None

        db.commit()

        return {"sucesso": True, "mensagem": "Email reenfileirado para envio"}
