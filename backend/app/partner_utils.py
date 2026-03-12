"""
Utilitários de parceria entre tenants (pet shop <-> clínica veterinária).

Permite que veterinários parceiros enxerguem dados do pet shop
(clientes, pets, produtos) na interface principal.
"""
from sqlalchemy.orm import Session
from app.veterinario_models import VetPartnerLink


def get_empresa_tenant_ids(db: Session, tenant_id) -> list:
    """
    Retorna os empresa_tenant_ids cujo vet_tenant_id é o atual e o vínculo está ativo.
    Ex: Maiara (vet) → retorna o tenant_id do pet shop parceiro.
    """
    links = db.query(VetPartnerLink).filter(
        VetPartnerLink.vet_tenant_id == str(tenant_id),
        VetPartnerLink.ativo == True,
    ).all()
    return [link.empresa_tenant_id for link in links]


def get_all_accessible_tenant_ids(db: Session, tenant_id) -> list:
    """
    Retorna o próprio tenant_id + todos os empresa_tenant_ids parceiros.
    Usado para filtrar registros acessíveis (clientes, pets, produtos).
    """
    return [str(tenant_id)] + get_empresa_tenant_ids(db, tenant_id)


def is_partner_owned(tenant_id, item_tenant_id) -> bool:
    """
    Retorna True se o item pertence a um tenant parceiro (não ao próprio).
    Usado para restringir ações destrutivas em itens do parceiro.
    """
    return str(item_tenant_id) != str(tenant_id)
