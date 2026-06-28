from typing import Any

from app.lgpd_models import DataSubjectRequest
from app.services.lgpd_utils import iso, json_load, num
from app.whatsapp.security import DataPrivacyConsent


class PrivacySerializationMixin:
    def _serialize_cliente(self, cliente) -> dict[str, Any]:
        return {
            "id": cliente.id,
            "codigo": cliente.codigo,
            "tipo_cadastro": cliente.tipo_cadastro,
            "tipo_pessoa": cliente.tipo_pessoa,
            "nome": cliente.nome,
            "cpf": cliente.cpf,
            "cnpj": cliente.cnpj,
            "razao_social": cliente.razao_social,
            "nome_fantasia": cliente.nome_fantasia,
            "responsavel": cliente.responsavel,
            "email": cliente.email,
            "telefone": cliente.telefone,
            "celular": cliente.celular,
            "data_nascimento": iso(cliente.data_nascimento),
            "endereco": {
                "cep": cliente.cep,
                "endereco": cliente.endereco,
                "numero": cliente.numero,
                "complemento": cliente.complemento,
                "bairro": cliente.bairro,
                "cidade": cliente.cidade,
                "estado": cliente.estado,
                "endereco_entrega": cliente.endereco_entrega,
                "enderecos_adicionais": cliente.enderecos_adicionais,
            },
            "credito": num(cliente.credito),
            "ativo": bool(cliente.ativo),
            "observacoes": cliente.observacoes,
            "created_at": iso(cliente.created_at),
            "updated_at": iso(cliente.updated_at),
        }

    def _serialize_pet(self, pet) -> dict[str, Any]:
        return {
            "id": pet.id,
            "codigo": pet.codigo,
            "nome": pet.nome,
            "especie": pet.especie,
            "raca": pet.raca,
            "sexo": pet.sexo,
            "castrado": bool(pet.castrado),
            "data_nascimento": iso(pet.data_nascimento),
            "idade_aproximada": pet.idade_aproximada,
            "peso": num(pet.peso),
            "cor": pet.cor,
            "porte": pet.porte,
            "microchip": pet.microchip,
            "alergias": pet.alergias,
            "doencas_cronicas": pet.doencas_cronicas,
            "medicamentos_continuos": pet.medicamentos_continuos,
            "restricoes_alimentares_lista": pet.restricoes_alimentares_lista,
            "historico_clinico": pet.historico_clinico,
            "observacoes": pet.observacoes,
            "ativo": bool(pet.ativo),
            "created_at": iso(pet.created_at),
            "updated_at": iso(pet.updated_at),
        }

    def _serialize_venda(self, venda) -> dict[str, Any]:
        return {
            "id": venda.id,
            "numero_venda": venda.numero_venda,
            "status": venda.status,
            "canal": venda.canal,
            "subtotal": num(venda.subtotal),
            "desconto_valor": num(venda.desconto_valor),
            "total": num(venda.total),
            "tem_entrega": bool(venda.tem_entrega),
            "status_entrega": venda.status_entrega,
            "data_venda": iso(venda.data_venda),
            "data_finalizacao": iso(venda.data_finalizacao),
            "observacoes": venda.observacoes,
            "itens": [
                {
                    "id": item.id,
                    "tipo": item.tipo,
                    "produto_id": item.produto_id,
                    "descricao": item.servico_descricao
                    or (item.produto.nome if item.produto else None),
                    "quantidade": num(item.quantidade),
                    "preco_unitario": num(item.preco_unitario),
                    "subtotal": num(item.subtotal),
                    "pet_id": item.pet_id,
                }
                for item in getattr(venda, "itens", []) or []
            ],
            "pagamentos": [
                {
                    "id": pagamento.id,
                    "forma_pagamento": getattr(pagamento, "forma_pagamento", None),
                    "valor": num(getattr(pagamento, "valor", None)),
                    "data_pagamento": iso(getattr(pagamento, "data_pagamento", None)),
                }
                for pagamento in getattr(venda, "pagamentos", []) or []
            ],
        }

    def _serialize_consent(self, row: DataPrivacyConsent) -> dict[str, Any]:
        return {
            "id": row.id,
            "subject_type": row.subject_type,
            "subject_id": row.subject_id,
            "consent_type": row.consent_type,
            "consent_given": bool(row.consent_given),
            "consent_text": row.consent_text,
            "phone_number": row.phone_number,
            "email": row.email,
            "created_at": iso(row.created_at),
            "revoked_at": iso(row.revoked_at),
            "revoke_reason": row.revoke_reason,
        }

    def _serialize_request(self, row: DataSubjectRequest) -> dict[str, Any]:
        return {
            "id": row.id,
            "subject_type": row.subject_type,
            "subject_id": row.subject_id,
            "request_type": row.request_type,
            "status": row.status,
            "requester_name": row.requester_name,
            "requester_email": row.requester_email,
            "requester_phone": row.requester_phone,
            "channel": row.channel,
            "details": row.details,
            "request_payload": json_load(row.request_payload, {}),
            "response_payload": json_load(row.response_payload, {}),
            "resolution_notes": row.resolution_notes,
            "created_by_user_id": row.created_by_user_id,
            "processed_by_user_id": row.processed_by_user_id,
            "due_at": iso(row.due_at),
            "processed_at": iso(row.processed_at),
            "created_at": iso(row.created_at),
            "updated_at": iso(row.updated_at),
        }


__all__ = ["PrivacySerializationMixin"]
