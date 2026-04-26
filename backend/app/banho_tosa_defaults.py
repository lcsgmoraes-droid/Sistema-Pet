"""Base padrao editavel para iniciar o modulo Banho & Tosa."""

from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.banho_tosa_api.utils import obter_ou_criar_configuracao
from app.banho_tosa_models import (
    BanhoTosaParametroPorte,
    BanhoTosaRecurso,
    BanhoTosaRetornoTemplate,
    BanhoTosaServico,
)


CONFIG_PADRAO = {
    "horario_inicio": "08:00",
    "horario_fim": "18:00",
    "dias_funcionamento": ["segunda", "terca", "quarta", "quinta", "sexta", "sabado"],
    "intervalo_slot_minutos": 30,
    "tolerancia_encaixe_minutos": 15,
    "custo_litro_agua": Decimal("0.0200"),
    "vazao_chuveiro_litros_min": Decimal("8.0000"),
    "custo_kwh": Decimal("1.0000"),
    "custo_toalha_padrao": Decimal("1.50"),
    "custo_higienizacao_padrao": Decimal("2.50"),
    "percentual_taxas_padrao": Decimal("3.5000"),
    "custo_rateio_operacional_padrao": Decimal("5.00"),
    "horas_produtivas_mes_padrao": Decimal("176.00"),
}

PARAMETROS_PORTE_PADRAO = [
    ("mini", None, "5.000", "18.000", "0.6000", 20, 20, 0, "0.8500"),
    ("pequeno", "5.001", "10.000", "25.000", "0.9000", 25, 25, 20, "1.0000"),
    ("medio", "10.001", "20.000", "35.000", "1.2000", 35, 35, 30, "1.2500"),
    ("grande", "20.001", "35.000", "50.000", "1.8000", 45, 45, 40, "1.5500"),
    ("gigante", "35.001", None, "70.000", "2.4000", 60, 60, 50, "2.0000"),
]

SERVICOS_PADRAO = [
    ("Banho Higienico", "banho", "Banho simples com shampoo, secagem e finalizacao basica.", 60, True, False, True, True),
    ("Banho Completo", "banho", "Banho completo com limpeza de ouvidos e acabamento.", 75, True, False, True, True),
    ("Banho + Tosa Higienica", "combo", "Banho completo com tosa higienica de patas, barriga e partes intimas.", 90, True, True, True, True),
    ("Tosa na Maquina", "tosa", "Tosa padronizada na maquina, sem banho obrigatorio.", 75, False, True, False, True),
    ("Tosa Completa", "combo", "Banho, secagem e tosa completa com acabamento.", 120, True, True, True, True),
    ("Desembaraco", "higiene", "Servico adicional para nos e pelagem embaraçada.", 45, False, False, False, False),
    ("Corte de Unhas", "higiene", "Corte e conferência rapida das unhas.", 15, False, False, False, False),
    ("Hidratacao de Pelagem", "higiene", "Tratamento adicional aplicado junto ao banho.", 30, True, False, True, True),
]

RECURSOS_PADRAO = [
    ("Banheira 1", "banheira", 1, None, "1.50"),
    ("Mesa de Tosa 1", "mesa_tosa", 1, None, "0.50"),
    ("Secador / Soprador 1", "secador", 1, "2400.00", "0.80"),
    ("Box de Espera", "box", 4, None, "0.00"),
    ("Taxi Dog", "veiculo", 1, None, "4.00"),
]

TEMPLATES_RETORNO_PADRAO = [
    (
        "Retorno banho preventivo",
        "sem_banho",
        "app",
        "Hora de cuidar de {pet_nome}",
        "Ola {cliente_nome}! Ja faz um tempinho desde o ultimo banho de {pet_nome}. Que tal agendar um novo cuidado?",
    ),
    (
        "Pacote vencendo",
        "pacote_vencendo",
        "app",
        "Pacote de {pet_nome} perto do vencimento",
        "Ola {cliente_nome}! O pacote de {pet_nome} esta perto do vencimento. Vamos aproveitar os creditos restantes?",
    ),
]


def aplicar_base_padrao_banho_tosa(db: Session, tenant_id) -> dict:
    """Cria dados iniciais editaveis sem sobrescrever cadastros existentes."""
    resumo = _novo_resumo()
    config = obter_ou_criar_configuracao(db, tenant_id)
    resumo["configuracao_atualizada"] = _preencher_configuracao(config)

    _criar_parametros(db, tenant_id, resumo)
    _criar_servicos(db, tenant_id, resumo)
    _criar_recursos(db, tenant_id, resumo)
    _criar_templates(db, tenant_id, resumo)

    db.commit()
    resumo["mensagem"] = "Base padrao aplicada. Os registros criados podem ser editados normalmente."
    return resumo


def _novo_resumo() -> dict:
    return {
        "configuracao_atualizada": False,
        "criados": {"parametros": 0, "servicos": 0, "recursos": 0, "templates": 0},
        "existentes": {"parametros": 0, "servicos": 0, "recursos": 0, "templates": 0},
    }


def _preencher_configuracao(config) -> bool:
    alterou = False
    for campo, valor in CONFIG_PADRAO.items():
        atual = getattr(config, campo, None)
        if atual in (None, "", [], 0, Decimal("0")):
            setattr(config, campo, valor)
            alterou = True
    return alterou


def _criar_parametros(db: Session, tenant_id, resumo: dict) -> None:
    for item in PARAMETROS_PORTE_PADRAO:
        porte = item[0]
        existe = db.query(BanhoTosaParametroPorte.id).filter(
            BanhoTosaParametroPorte.tenant_id == tenant_id,
            func.lower(BanhoTosaParametroPorte.porte) == porte,
        ).first()
        if existe:
            resumo["existentes"]["parametros"] += 1
            continue

        db.add(BanhoTosaParametroPorte(
            tenant_id=tenant_id,
            porte=porte,
            peso_min_kg=_dec(item[1]),
            peso_max_kg=_dec(item[2]),
            agua_padrao_litros=_dec(item[3]),
            energia_padrao_kwh=_dec(item[4]),
            tempo_banho_min=item[5],
            tempo_secagem_min=item[6],
            tempo_tosa_min=item[7],
            multiplicador_preco=_dec(item[8]),
            ativo=True,
        ))
        resumo["criados"]["parametros"] += 1


def _criar_servicos(db: Session, tenant_id, resumo: dict) -> None:
    for nome, categoria, descricao, duracao, banho, tosa, secagem, pacote in SERVICOS_PADRAO:
        existe = db.query(BanhoTosaServico.id).filter(
            BanhoTosaServico.tenant_id == tenant_id,
            func.lower(BanhoTosaServico.nome) == nome.lower(),
        ).first()
        if existe:
            resumo["existentes"]["servicos"] += 1
            continue

        db.add(BanhoTosaServico(
            tenant_id=tenant_id,
            nome=nome,
            categoria=categoria,
            descricao=descricao,
            duracao_padrao_minutos=duracao,
            requer_banho=banho,
            requer_tosa=tosa,
            requer_secagem=secagem,
            permite_pacote=pacote,
            ativo=True,
        ))
        resumo["criados"]["servicos"] += 1


def _criar_recursos(db: Session, tenant_id, resumo: dict) -> None:
    for nome, tipo, capacidade, potencia, manutencao in RECURSOS_PADRAO:
        existe = db.query(BanhoTosaRecurso.id).filter(
            BanhoTosaRecurso.tenant_id == tenant_id,
            func.lower(BanhoTosaRecurso.nome) == nome.lower(),
            BanhoTosaRecurso.tipo == tipo,
        ).first()
        if existe:
            resumo["existentes"]["recursos"] += 1
            continue

        db.add(BanhoTosaRecurso(
            tenant_id=tenant_id,
            nome=nome,
            tipo=tipo,
            capacidade_simultanea=capacidade,
            potencia_watts=_dec(potencia),
            custo_manutencao_hora=_dec(manutencao),
            ativo=True,
        ))
        resumo["criados"]["recursos"] += 1


def _criar_templates(db: Session, tenant_id, resumo: dict) -> None:
    for nome, tipo_retorno, canal, assunto, mensagem in TEMPLATES_RETORNO_PADRAO:
        existe = db.query(BanhoTosaRetornoTemplate.id).filter(
            BanhoTosaRetornoTemplate.tenant_id == tenant_id,
            func.lower(BanhoTosaRetornoTemplate.nome) == nome.lower(),
            BanhoTosaRetornoTemplate.canal == canal,
        ).first()
        if existe:
            resumo["existentes"]["templates"] += 1
            continue

        db.add(BanhoTosaRetornoTemplate(
            tenant_id=tenant_id,
            nome=nome,
            tipo_retorno=tipo_retorno,
            canal=canal,
            assunto=assunto,
            mensagem=mensagem,
            ativo=True,
        ))
        resumo["criados"]["templates"] += 1


def _dec(valor):
    return Decimal(str(valor)) if valor is not None else None
