"""Templates configuraveis para campanhas de retorno do Banho & Tosa."""

from datetime import date

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.banho_tosa_models import BanhoTosaRetornoTemplate


TIPOS_RETORNO = {"todos", "recorrencia", "pacote_vencendo", "pacote_saldo_baixo", "sem_banho"}
CANAIS_RETORNO = {"app", "email"}


def listar_templates_retorno(db: Session, tenant_id, *, tipo_retorno: str | None = None, canal: str | None = None, ativos_only: bool = False):
    query = db.query(BanhoTosaRetornoTemplate).filter(BanhoTosaRetornoTemplate.tenant_id == tenant_id)
    if tipo_retorno:
        query = query.filter(BanhoTosaRetornoTemplate.tipo_retorno == normalizar_tipo(tipo_retorno))
    if canal:
        query = query.filter(BanhoTosaRetornoTemplate.canal == normalizar_canal(canal))
    if ativos_only:
        query = query.filter(BanhoTosaRetornoTemplate.ativo == True)
    return query.order_by(BanhoTosaRetornoTemplate.nome.asc()).all()


def criar_template_retorno(db: Session, tenant_id, payload: dict) -> dict:
    payload = _normalizar_payload(payload)
    _validar_nome_disponivel(db, tenant_id, payload["nome"], payload["canal"])
    template = BanhoTosaRetornoTemplate(tenant_id=tenant_id, **payload)
    db.add(template)
    db.commit()
    db.refresh(template)
    return serializar_template_retorno(template)


def atualizar_template_retorno(db: Session, tenant_id, template_id: int, payload: dict) -> dict:
    template = obter_template_retorno(db, tenant_id, template_id)
    payload = _normalizar_payload(payload, parcial=True)
    nome = payload.get("nome", template.nome)
    canal = payload.get("canal", template.canal)
    if "nome" in payload or "canal" in payload:
        _validar_nome_disponivel(db, tenant_id, nome, canal, ignorar_id=template.id)
    for campo, valor in payload.items():
        setattr(template, campo, valor)
    db.commit()
    db.refresh(template)
    return serializar_template_retorno(template)


def obter_template_retorno(db: Session, tenant_id, template_id: int, *, ativo: bool = False):
    query = db.query(BanhoTosaRetornoTemplate).filter(
        BanhoTosaRetornoTemplate.id == template_id,
        BanhoTosaRetornoTemplate.tenant_id == tenant_id,
    )
    if ativo:
        query = query.filter(BanhoTosaRetornoTemplate.ativo == True)
    template = query.first()
    if not template:
        raise HTTPException(status_code=404, detail="Template de retorno nao encontrado.")
    return template


def serializar_template_retorno(template) -> dict:
    return {
        "id": template.id,
        "nome": template.nome,
        "tipo_retorno": template.tipo_retorno,
        "canal": template.canal,
        "assunto": template.assunto,
        "mensagem": template.mensagem,
        "ativo": template.ativo,
    }


def renderizar_template_retorno(template, item: dict) -> tuple[str, str]:
    assunto = getattr(template, "assunto", None) or item.get("titulo") or "Retorno de Banho & Tosa"
    mensagem = getattr(template, "mensagem", None) or item.get("mensagem") or ""
    contexto = _contexto_item(item)
    return _substituir(assunto, contexto), _substituir(mensagem, contexto)


def template_aplicavel(template, tipo: str) -> bool:
    if not template:
        return True
    return template.tipo_retorno == "todos" or template.tipo_retorno == tipo


def normalizar_canal(canal: str | None) -> str:
    valor = (canal or "app").strip().lower()
    if valor not in CANAIS_RETORNO:
        raise HTTPException(status_code=422, detail="Canal de retorno invalido.")
    return valor


def normalizar_tipo(tipo: str | None) -> str:
    valor = (tipo or "todos").strip().lower()
    if valor not in TIPOS_RETORNO:
        raise HTTPException(status_code=422, detail="Tipo de retorno invalido.")
    return valor


def _normalizar_payload(payload: dict, *, parcial: bool = False) -> dict:
    data = {k: v for k, v in payload.items() if v is not None}
    if "nome" in data:
        data["nome"] = data["nome"].strip()
    if "assunto" in data:
        data["assunto"] = data["assunto"].strip()
    if "mensagem" in data:
        data["mensagem"] = data["mensagem"].strip()
    if "tipo_retorno" in data or not parcial:
        data["tipo_retorno"] = normalizar_tipo(data.get("tipo_retorno"))
    if "canal" in data or not parcial:
        data["canal"] = normalizar_canal(data.get("canal"))
    if not parcial and not data.get("nome"):
        raise HTTPException(status_code=422, detail="Nome do template e obrigatorio.")
    return data


def _validar_nome_disponivel(db: Session, tenant_id, nome: str, canal: str, ignorar_id: int | None = None) -> None:
    query = db.query(BanhoTosaRetornoTemplate.id).filter(
        BanhoTosaRetornoTemplate.tenant_id == tenant_id,
        BanhoTosaRetornoTemplate.canal == canal,
        func.lower(BanhoTosaRetornoTemplate.nome) == nome.lower(),
    )
    if ignorar_id:
        query = query.filter(BanhoTosaRetornoTemplate.id != ignorar_id)
    if query.first():
        raise HTTPException(status_code=409, detail="Ja existe template com esse nome e canal.")


def _contexto_item(item: dict) -> dict:
    return {
        "cliente_nome": item.get("cliente_nome") or "cliente",
        "pet_nome": item.get("pet_nome") or "seu pet",
        "servico_nome": item.get("servico_nome") or "Banho & Tosa",
        "pacote_nome": item.get("pacote_nome") or "pacote",
        "data_referencia": _formatar_data(item.get("data_referencia")),
        "dias_para_acao": _formatar_dias(item.get("dias_para_acao")),
        "acao_sugerida": item.get("acao_sugerida") or "",
    }


def _substituir(texto: str, contexto: dict) -> str:
    for chave, valor in contexto.items():
        texto = texto.replace(f"{{{chave}}}", str(valor))
    return texto


def _formatar_data(valor) -> str:
    if isinstance(valor, date):
        return valor.strftime("%d/%m/%Y")
    return str(valor or "")


def _formatar_dias(valor) -> str:
    if valor is None:
        return "sem prazo"
    if valor < 0:
        return f"{abs(valor)} dia(s) em atraso"
    if valor == 0:
        return "hoje"
    return f"em {valor} dia(s)"
