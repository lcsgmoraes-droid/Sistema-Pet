from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    DATABASE_URL: str

    # Campos legacy esperados pelo sistema
    SYSTEM_NAME: str = "PetShop ERP"
    SYSTEM_VERSION: str = "dev"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # Seguranca / Auth
    JWT_SECRET_KEY: str = "CHANGE_ME_IN_ENV"

    # Integracoes externas
    GOOGLE_MAPS_API_KEY: str = ""

    # Auditoria SQL (Pré-Prod Block 1)
    SQL_AUDIT_ENFORCE: bool = True
    SQL_AUDIT_ENFORCE_LEVEL: str = "error"  # warn, error, strict

    # Guard Rails (Pré-Prod Block 1)
    ENABLE_GUARDRAILS: bool = False
    
    # Logging (Pré-Prod Block 1)
    LOG_LEVEL: str = "INFO"
    
    # Alias para compatibilidade
    @property
    def ENV(self) -> str:
        """Alias para ENVIRONMENT"""
        return self.ENVIRONMENT

    # CORS - Em produ��o, definir dom�nios espec�ficos via ALLOWED_ORIGINS
    # Exemplo: ALLOWED_ORIGINS="https://app.seupetshop.com,https://www.seupetshop.com"
    # ?? NUNCA use "*" em produ��o!
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="allow",
    )


settings = Settings()

# ====== EXPORTS LEGACY (COMPATIBILIDADE) ======

DATABASE_URL = settings.DATABASE_URL
SYSTEM_NAME = settings.SYSTEM_NAME
SYSTEM_VERSION = settings.SYSTEM_VERSION
ENVIRONMENT = settings.ENVIRONMENT
ENV = settings.ENV  # Alias
DEBUG = settings.DEBUG
JWT_SECRET_KEY = settings.JWT_SECRET_KEY
GOOGLE_MAPS_API_KEY = settings.GOOGLE_MAPS_API_KEY
SQL_AUDIT_ENFORCE = settings.SQL_AUDIT_ENFORCE
SQL_AUDIT_ENFORCE_LEVEL = settings.SQL_AUDIT_ENFORCE_LEVEL
ENABLE_GUARDRAILS = settings.ENABLE_GUARDRAILS
LOG_LEVEL = settings.LOG_LEVEL

# CORS (esperado como list em alguns lugares)
ALLOWED_ORIGINS: List[str] = [
    origin.strip()
    for origin in settings.ALLOWED_ORIGINS.split(",")
    if origin.strip()
]

# ====== HELPERS ======

def get_database_url() -> str:
    if not settings.DATABASE_URL.startswith("postgresql"):
        raise RuntimeError(
            "Invalid database. This system supports PostgreSQL only."
        )
    return settings.DATABASE_URL


def print_config() -> None:
    print("=== APPLICATION CONFIG ===")
    print(f"SYSTEM_NAME={SYSTEM_NAME}")
    print(f"SYSTEM_VERSION={SYSTEM_VERSION}")
    print(f"ENVIRONMENT={ENVIRONMENT}")
    print(f"DEBUG={DEBUG}")
    print(f"ALLOWED_ORIGINS={ALLOWED_ORIGINS}")
    print(f"GOOGLE_MAPS_API_KEY={'SET' if GOOGLE_MAPS_API_KEY else 'NOT SET'}")
    print("==========================")
