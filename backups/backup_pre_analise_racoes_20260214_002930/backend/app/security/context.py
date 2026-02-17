"""
Contexto de Segurança Multi-Tenant
===================================

OBJETIVO DESTE MÓDULO
----------------------
Criar a base de segurança do sistema para SaaS multi-tenant.

Este arquivo:
- Lê o JWT já validado
- Extrai:
  - user_id (quem é o usuário)
  - tenant_id (qual empresa ele pertence)
  - role (o que ele pode fazer)
- Garante que nenhuma requisição avance sem essas informações

IMPORTANTE
----------
- NÃO cria tabelas
- NÃO altera banco
- NÃO muda rotas existentes
- Apenas prepara o terreno
"""

from fastapi import Depends, HTTPException, status
from jose import JWTError, jwt
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import JWT_SECRET_KEY

ALGORITHM = "HS256"
security = HTTPBearer()


def decode_access_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Decodifica o JWT e retorna o payload.
    Esta função é chamada antes de get_current_user.
    """
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise credentials_exception


class CurrentUser:
    """
    Representa o usuário autenticado no contexto da requisição.
    Esses dados vêm do JWT.
    """
    def __init__(self, user_id: str, tenant_id: str, role: str):
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.role = role


def get_current_user(token: dict = Depends(decode_access_token)) -> CurrentUser:
    """
    Dependency global que:
    - valida se o JWT contém as informações mínimas
    - impede requisições sem tenant ou role
    """
    user_id = token.get("sub")
    tenant_id = token.get("tenant_id")
    role = token.get("role")

    if not user_id or not tenant_id or not role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token inválido ou incompleto (tenant/role ausente)",
        )

    return CurrentUser(
        user_id=user_id,
        tenant_id=tenant_id,
        role=role,
    )


def get_current_tenant(user: CurrentUser = Depends(get_current_user)) -> str:
    """
    Dependency simples para obter o tenant atual.
    Usada pelos Services para garantir isolamento de dados.
    """
    return user.tenant_id
