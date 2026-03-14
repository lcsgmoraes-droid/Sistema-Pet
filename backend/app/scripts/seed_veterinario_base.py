"""
Seed veterinario base (idempotente).

Popula, por tenant:
- Produtos de consumo veterinario (materias-primas)
- Catalogo de medicamentos
- Protocolos de vacina
- Catalogo de procedimentos com insumos vinculados

Opcional (somente DEV):
- Lancamentos teste: consulta, procedimento, exame e vacina registro

Uso:
  cd backend
  python -m app.scripts.seed_veterinario_base
  python -m app.scripts.seed_veterinario_base --tenant-id <TENANT_UUID>
  python -m app.scripts.seed_veterinario_base --with-test-launches
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Tenant, User, Pet
from app.produtos_models import Produto
from app.veterinario_models import (
    MedicamentoCatalogo,
    ProtocoloVacina,
    CatalogoProcedimento,
    ConsultaVet,
    ProcedimentoConsulta,
    ExameVet,
    VacinaRegistro,
)
from app.utils.logger import logger


MATERIAIS_BASE = [
    {"codigo": "MASK-DESC", "nome": "Mascara descartavel tripla", "unidade": "UN", "custo": 0.65, "venda": 1.20},
    {"codigo": "LUVA-LATEX-M", "nome": "Luva procedimento latex M", "unidade": "CX", "custo": 28.00, "venda": 39.90},
    {"codigo": "GAZE-EST-75", "nome": "Gaze esteril 7.5x7.5", "unidade": "PCT", "custo": 7.40, "venda": 11.90},
    {"codigo": "ALGODAO-HID", "nome": "Algodao hidrofilo 500g", "unidade": "PCT", "custo": 12.50, "venda": 18.00},
    {"codigo": "MICROPORE-25", "nome": "Fita micropore 25mm", "unidade": "UN", "custo": 4.20, "venda": 7.50},
    {"codigo": "ATADURA-10", "nome": "Atadura crepe 10cm", "unidade": "UN", "custo": 2.10, "venda": 3.90},
    {"codigo": "SERINGA-3ML", "nome": "Seringa descartavel 3ml", "unidade": "UN", "custo": 0.42, "venda": 0.90},
    {"codigo": "AGULHA-25X7", "nome": "Agulha hipodermica 25x7", "unidade": "UN", "custo": 0.18, "venda": 0.45},
    {"codigo": "SORO-500", "nome": "Soro fisiologico 0.9% 500ml", "unidade": "UN", "custo": 6.30, "venda": 11.90},
    {"codigo": "COLETOR-PERF", "nome": "Coletor perfurocortante 7L", "unidade": "UN", "custo": 8.90, "venda": 14.90},
]

MEDICAMENTOS_BASE = [
    {
        "nome": "Amoxicilina + Clavulanato",
        "nome_comercial": "Clavulin Vet",
        "principio_ativo": "Amoxicilina; Clavulanato",
        "forma_farmaceutica": "comprimido",
        "concentracao": "250mg",
        "especies_indicadas": ["cao", "gato"],
        "indicacoes": "Infeccoes bacterianas de pele, trato respiratorio e urinario.",
        "contraindicacoes": "Hipersensibilidade a betalactamicos.",
        "interacoes": "Cautela com bacteriostaticos.",
        "posologia_referencia": "12.5 a 25 mg/kg a cada 12h.",
        "dose_min_mgkg": 12.5,
        "dose_max_mgkg": 25.0,
        "eh_antibiotico": True,
    },
    {
        "nome": "Cefalexina",
        "nome_comercial": "Rilexine",
        "principio_ativo": "Cefalexina",
        "forma_farmaceutica": "comprimido",
        "concentracao": "300mg",
        "especies_indicadas": ["cao", "gato"],
        "indicacoes": "Piodermites e infeccoes de tecidos moles.",
        "contraindicacoes": "Hipersensibilidade a cefalosporinas.",
        "interacoes": "Cautela com aminoglicosideos.",
        "posologia_referencia": "15 a 30 mg/kg a cada 12h.",
        "dose_min_mgkg": 15.0,
        "dose_max_mgkg": 30.0,
        "eh_antibiotico": True,
    },
    {
        "nome": "Prednisolona",
        "nome_comercial": "Meticorten Vet",
        "principio_ativo": "Prednisolona",
        "forma_farmaceutica": "comprimido",
        "concentracao": "5mg",
        "especies_indicadas": ["cao", "gato"],
        "indicacoes": "Processos inflamatorios e alergicos.",
        "contraindicacoes": "Infeccoes fungicas sistemicas, ulceras GI sem controle.",
        "interacoes": "AINEs aumentam risco GI.",
        "posologia_referencia": "0.5 a 1 mg/kg a cada 12-24h.",
        "dose_min_mgkg": 0.5,
        "dose_max_mgkg": 1.0,
    },
    {
        "nome": "Meloxicam",
        "nome_comercial": "Maxicam",
        "principio_ativo": "Meloxicam",
        "forma_farmaceutica": "suspensao oral",
        "concentracao": "1.5mg/mL",
        "especies_indicadas": ["cao"],
        "indicacoes": "Dor e inflamacao osteoarticular.",
        "contraindicacoes": "Insuficiencia renal/hepatica descompensada.",
        "interacoes": "Nao associar com corticosteroides sem criterio.",
        "posologia_referencia": "0.1 mg/kg dose inicial; 0.05 mg/kg manutencao.",
        "dose_min_mgkg": 0.05,
        "dose_max_mgkg": 0.10,
    },
    {
        "nome": "Dipirona",
        "nome_comercial": "Dipimed",
        "principio_ativo": "Metamizol",
        "forma_farmaceutica": "gotas",
        "concentracao": "500mg/mL",
        "especies_indicadas": ["cao", "gato"],
        "indicacoes": "Dor e febre.",
        "contraindicacoes": "Cautela em hipotensao e doenca renal avancada.",
        "interacoes": "Potencializa efeito de sedativos.",
        "posologia_referencia": "25 mg/kg a cada 8-12h.",
        "dose_min_mgkg": 20.0,
        "dose_max_mgkg": 30.0,
    },
    {
        "nome": "Omeprazol",
        "nome_comercial": "Gastrozol",
        "principio_ativo": "Omeprazol",
        "forma_farmaceutica": "capsula",
        "concentracao": "10mg",
        "especies_indicadas": ["cao", "gato"],
        "indicacoes": "Gastrite e protecao gastrica.",
        "contraindicacoes": "Hipersensibilidade ao principio ativo.",
        "interacoes": "Pode alterar absorcao de alguns farmacos.",
        "posologia_referencia": "0.7 a 1 mg/kg a cada 24h.",
        "dose_min_mgkg": 0.7,
        "dose_max_mgkg": 1.0,
    },
    {
        "nome": "Metronidazol",
        "nome_comercial": "Flagyl Vet",
        "principio_ativo": "Metronidazol",
        "forma_farmaceutica": "comprimido",
        "concentracao": "250mg",
        "especies_indicadas": ["cao", "gato"],
        "indicacoes": "Diarreia por anaerobios e protozoarios.",
        "contraindicacoes": "Cautela em hepatopatias.",
        "interacoes": "Cautela com fenobarbital.",
        "posologia_referencia": "10 a 15 mg/kg a cada 12h.",
        "dose_min_mgkg": 10.0,
        "dose_max_mgkg": 15.0,
        "eh_antibiotico": True,
    },
    {
        "nome": "Tramadol",
        "nome_comercial": "Tramal Vet",
        "principio_ativo": "Tramadol",
        "forma_farmaceutica": "comprimido",
        "concentracao": "50mg",
        "especies_indicadas": ["cao", "gato"],
        "indicacoes": "Analgesia moderada.",
        "contraindicacoes": "Cautela em epilepsia.",
        "interacoes": "Cautela com antidepressivos serotoninergicos.",
        "posologia_referencia": "2 a 4 mg/kg a cada 8-12h.",
        "dose_min_mgkg": 2.0,
        "dose_max_mgkg": 4.0,
        "eh_controlado": True,
    },
]

PROTOCOLOS_VACINA_BASE = [
    {"nome": "V8 / V10", "especie": "cao", "dose_inicial_semanas": 6, "intervalo_doses_dias": 21, "numero_doses_serie": 3, "reforco_anual": True, "observacoes": "Serie primaria em filhotes com reforco anual."},
    {"nome": "Antirrabica", "especie": "cao", "dose_inicial_semanas": 12, "intervalo_doses_dias": 365, "numero_doses_serie": 1, "reforco_anual": True, "observacoes": "Obrigatoria por legislacao local."},
    {"nome": "Bordetella", "especie": "cao", "dose_inicial_semanas": 8, "intervalo_doses_dias": 365, "numero_doses_serie": 1, "reforco_anual": True, "observacoes": "Indicada para cao com convivencia coletiva."},
    {"nome": "V3 / V4 Felina", "especie": "gato", "dose_inicial_semanas": 8, "intervalo_doses_dias": 21, "numero_doses_serie": 3, "reforco_anual": True, "observacoes": "Serie primaria felina e reforco anual."},
    {"nome": "FeLV", "especie": "gato", "dose_inicial_semanas": 8, "intervalo_doses_dias": 28, "numero_doses_serie": 2, "reforco_anual": True, "observacoes": "Recomendado para felinos com acesso externo."},
]

PROCEDIMENTOS_BASE = [
    {
        "nome": "Consulta clinica geral",
        "categoria": "consulta",
        "valor_padrao": 120.0,
        "duracao_minutos": 30,
        "requer_anestesia": False,
        "observacoes": "Avaliacao clinica completa com sinais vitais.",
        "insumos_codigos": [("LUVA-LATEX-M", 0.1), ("MASK-DESC", 1), ("GAZE-EST-75", 1)],
    },
    {
        "nome": "Curativo simples",
        "categoria": "procedimento",
        "valor_padrao": 85.0,
        "duracao_minutos": 25,
        "requer_anestesia": False,
        "observacoes": "Higienizacao e cobertura de lesao superficial.",
        "insumos_codigos": [("LUVA-LATEX-M", 0.1), ("GAZE-EST-75", 2), ("MICROPORE-25", 0.3), ("ATADURA-10", 1), ("SORO-500", 0.1)],
    },
    {
        "nome": "Aplicacao de vacinas",
        "categoria": "vacina",
        "valor_padrao": 65.0,
        "duracao_minutos": 15,
        "requer_anestesia": False,
        "observacoes": "Aplicacao de vacina conforme protocolo da clinica.",
        "insumos_codigos": [("LUVA-LATEX-M", 0.1), ("SERINGA-3ML", 1), ("AGULHA-25X7", 1), ("ALGODAO-HID", 0.05)],
    },
    {
        "nome": "Coleta de sangue",
        "categoria": "exame",
        "valor_padrao": 70.0,
        "duracao_minutos": 20,
        "requer_anestesia": False,
        "observacoes": "Coleta para hemograma e bioquimica.",
        "insumos_codigos": [("LUVA-LATEX-M", 0.1), ("SERINGA-3ML", 1), ("AGULHA-25X7", 1), ("GAZE-EST-75", 1), ("MICROPORE-25", 0.1)],
    },
]


def _tenant_query(db: Session, tenant_id: str | None) -> list[Tenant]:
    q = db.query(Tenant).filter(Tenant.status == "active")
    if tenant_id:
        q = q.filter(Tenant.id == tenant_id)
    return q.all()


def _tenant_str(value) -> str:
    return str(value)


def _primary_user_for_tenant(db: Session, tenant_id: str) -> User | None:
    return (
        db.query(User)
        .filter(User.tenant_id == _tenant_str(tenant_id), User.is_active == True)  # noqa: E712
        .order_by(User.is_admin.desc(), User.id.asc())
        .first()
    )


def _find_product(db: Session, tenant_id: str, codigo: str) -> Produto | None:
    return db.query(Produto).filter(Produto.tenant_id == _tenant_str(tenant_id), Produto.codigo == codigo).first()


def _upsert_materiais(db: Session, tenant_id: str, user_id: int) -> dict[str, Produto]:
    material_map: dict[str, Produto] = {}
    tenant_key = _tenant_str(tenant_id)
    for item in MATERIAIS_BASE:
        codigo = f"VET-{tenant_key[:6]}-{item['codigo']}"
        produto = _find_product(db, tenant_id, codigo)
        if not produto:
            produto = Produto(
                tenant_id=tenant_key,
                user_id=user_id,
                codigo=codigo,
                nome=item["nome"],
                tipo="produto",
                tipo_produto="SIMPLES",
                is_parent=False,
                is_sellable=True,
                situacao=True,
                ativo=True,
                unidade=item["unidade"],
                preco_custo=float(item["custo"]),
                preco_venda=float(item["venda"]),
                estoque_atual=200.0,
                estoque_minimo=20.0,
                estoque_maximo=1000.0,
                descricao_curta="Material de consumo veterinario (seed base).",
                observacoes_recorrencia="SEED_VET_BASE",
            )
            db.add(produto)
            db.flush()
        else:
            produto.situacao = True
            produto.ativo = True
            produto.unidade = produto.unidade or item["unidade"]
            if (produto.preco_custo or 0) <= 0:
                produto.preco_custo = float(item["custo"])
            if (produto.preco_venda or 0) <= 0:
                produto.preco_venda = float(item["venda"])
            if (produto.estoque_atual or 0) <= 0:
                produto.estoque_atual = 100.0

        material_map[item["codigo"]] = produto

    return material_map


def _upsert_medicamentos(db: Session, tenant_id: str) -> None:
    tenant_key = _tenant_str(tenant_id)
    for item in MEDICAMENTOS_BASE:
        existente = (
            db.query(MedicamentoCatalogo)
            .filter(MedicamentoCatalogo.tenant_id == tenant_key, MedicamentoCatalogo.nome == item["nome"])
            .first()
        )
        if existente:
            continue

        db.add(MedicamentoCatalogo(tenant_id=tenant_key, ativo=True, **item))


def _upsert_protocolos(db: Session, tenant_id: str) -> None:
    tenant_key = _tenant_str(tenant_id)
    for item in PROTOCOLOS_VACINA_BASE:
        existente = (
            db.query(ProtocoloVacina)
            .filter(ProtocoloVacina.tenant_id == tenant_key, ProtocoloVacina.nome == item["nome"], ProtocoloVacina.especie == item["especie"])
            .first()
        )
        if existente:
            continue

        db.add(ProtocoloVacina(tenant_id=tenant_key, ativo=True, **item))


def _upsert_procedimentos(db: Session, tenant_id: str, materiais: dict[str, Produto]) -> None:
    tenant_key = _tenant_str(tenant_id)
    for item in PROCEDIMENTOS_BASE:
        existente = (
            db.query(CatalogoProcedimento)
            .filter(CatalogoProcedimento.tenant_id == tenant_key, CatalogoProcedimento.nome == item["nome"])
            .first()
        )

        insumos = []
        for codigo_base, qtd in item["insumos_codigos"]:
            produto = materiais.get(codigo_base)
            if not produto:
                continue
            insumos.append(
                {
                    "produto_id": int(produto.id),
                    "quantidade": float(qtd),
                    "nome": produto.nome,
                    "unidade": produto.unidade,
                    "baixar_estoque": True,
                }
            )

        payload = {
            "categoria": item["categoria"],
            "valor_padrao": Decimal(str(item["valor_padrao"])),
            "duracao_minutos": item["duracao_minutos"],
            "requer_anestesia": item["requer_anestesia"],
            "observacoes": item["observacoes"],
            "insumos": insumos,
            "ativo": True,
        }

        if not existente:
            db.add(CatalogoProcedimento(tenant_id=tenant_key, nome=item["nome"], **payload))
        else:
            existente.ativo = True
            existente.categoria = existente.categoria or payload["categoria"]
            existente.valor_padrao = existente.valor_padrao or payload["valor_padrao"]
            existente.duracao_minutos = existente.duracao_minutos or payload["duracao_minutos"]
            existente.insumos = payload["insumos"]


def _seed_test_launches(db: Session, tenant_id: str, user_id: int) -> int:
    """Cria poucos lancamentos teste para treino de fluxo (somente DEV)."""
    tenant_key = _tenant_str(tenant_id)
    pets = db.query(Pet).filter(Pet.tenant_id == tenant_key, Pet.ativo == True).order_by(Pet.id.asc()).limit(2).all()  # noqa: E712
    if not pets:
        return 0

    protocolo_v8 = db.query(ProtocoloVacina).filter(ProtocoloVacina.tenant_id == tenant_key, ProtocoloVacina.nome == "V8 / V10").first()
    proc_consulta = db.query(CatalogoProcedimento).filter(CatalogoProcedimento.tenant_id == tenant_key, CatalogoProcedimento.nome == "Consulta clinica geral").first()

    created = 0
    for pet in pets:
        marcador = f"SEED_VET_BASE_TESTE_PET_{pet.id}"
        ja_existe = db.query(ConsultaVet).filter(ConsultaVet.tenant_id == tenant_key, ConsultaVet.observacoes_internas == marcador).first()
        if ja_existe:
            continue

        consulta = ConsultaVet(
            tenant_id=tenant_id,
            pet_id=pet.id,
            cliente_id=pet.cliente_id,
            veterinario_id=None,
            user_id=user_id,
            inicio_atendimento=datetime.utcnow() - timedelta(minutes=35),
            fim_atendimento=datetime.utcnow() - timedelta(minutes=5),
            tipo="consulta",
            status="finalizada",
            queixa_principal="Lancamento de teste seed veterinario",
            historia_clinica="Paciente sem intercorrencias graves, acompanhamento de rotina.",
            exame_fisico="Sinais vitais estaveis.",
            diagnostico="Acompanhamento preventivo",
            conduta="Manter calendario preventivo e retorno programado.",
            observacoes_tutor="Registro de teste para validacao de fluxo.",
            observacoes_internas=marcador,
            finalizado_em=datetime.utcnow(),
            finalizado_por_id=user_id,
        )
        db.add(consulta)
        db.flush()

        if proc_consulta:
            db.add(
                ProcedimentoConsulta(
                    tenant_id=tenant_id,
                    consulta_id=consulta.id,
                    catalogo_id=proc_consulta.id,
                    user_id=user_id,
                    nome=proc_consulta.nome,
                    descricao=proc_consulta.descricao,
                    valor=proc_consulta.valor_padrao,
                    realizado=True,
                    observacoes="Procedimento teste (seed base)",
                    insumos=proc_consulta.insumos or [],
                    estoque_baixado=False,
                )
            )

        db.add(
            ExameVet(
                tenant_id=tenant_id,
                pet_id=pet.id,
                consulta_id=consulta.id,
                user_id=user_id,
                tipo="laboratorial",
                nome="Hemograma completo",
                data_solicitacao=date.today(),
                data_resultado=date.today(),
                status="disponivel",
                laboratorio="Seed Vet Lab",
                resultado_texto="Sem alteracoes criticas. Registro de teste.",
                observacoes="SEED_VET_BASE_TESTE",
            )
        )

        db.add(
            VacinaRegistro(
                tenant_id=tenant_id,
                pet_id=pet.id,
                consulta_id=consulta.id,
                veterinario_id=None,
                user_id=user_id,
                protocolo_id=protocolo_v8.id if protocolo_v8 else None,
                nome_vacina="V8 / V10",
                fabricante="Seed Farma",
                lote="SEED-LOTE-001",
                data_aplicacao=date.today(),
                data_proxima_dose=date.today() + timedelta(days=365),
                numero_dose=1,
                via_administracao="subcutanea",
                observacoes="SEED_VET_BASE_TESTE",
            )
        )

        created += 1

    return created


def run_seed(tenant_id: str | None, with_test_launches: bool) -> None:
    db: Session = SessionLocal()
    try:
        tenants = _tenant_query(db, tenant_id)
        if not tenants:
            logger.warning("Nenhum tenant ativo encontrado para seed veterinario.")
            return

        total_tenants = 0
        total_tests = 0

        for tenant in tenants:
            user = _primary_user_for_tenant(db, tenant.id)
            if not user:
                logger.warning(f"Tenant {tenant.id} sem usuario ativo; seed ignorado.")
                continue

            materiais = _upsert_materiais(db, tenant.id, user.id)
            _upsert_medicamentos(db, tenant.id)
            _upsert_protocolos(db, tenant.id)
            _upsert_procedimentos(db, tenant.id, materiais)

            if with_test_launches:
                total_tests += _seed_test_launches(db, tenant.id, user.id)

            total_tenants += 1

        db.commit()
        logger.info(f"Seed veterinario concluido. Tenants processados: {total_tenants}.")
        if with_test_launches:
            logger.info(f"Lancamentos teste criados: {total_tests}.")
    except Exception as exc:
        db.rollback()
        logger.error(f"Erro no seed veterinario: {exc}")
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed veterinario base")
    parser.add_argument("--tenant-id", dest="tenant_id", default=None, help="Tenant especifico para seed")
    parser.add_argument(
        "--with-test-launches",
        dest="with_test_launches",
        action="store_true",
        help="Cria lancamentos teste (somente ambiente DEV)",
    )
    args = parser.parse_args()

    run_seed(tenant_id=args.tenant_id, with_test_launches=args.with_test_launches)


if __name__ == "__main__":
    main()
