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

    # Imagens de produtos
    PRODUCT_IMAGE_STORAGE_BACKEND: str = "local"  # local | s3
    PRODUCT_IMAGE_LOCAL_BASE_DIR: str = "uploads/produtos"
    PRODUCT_IMAGE_UPLOAD_MAX_BYTES: int = 10 * 1024 * 1024
    PRODUCT_IMAGE_MAX_DIMENSION: int = 1600
    PRODUCT_IMAGE_THUMBNAIL_SIZE: int = 420
    PRODUCT_IMAGE_WEBP_QUALITY: int = 82
    PRODUCT_IMAGE_S3_BUCKET: str = ""
    PRODUCT_IMAGE_S3_REGION: str = ""
    PRODUCT_IMAGE_S3_ENDPOINT_URL: str = ""
    PRODUCT_IMAGE_S3_ACCESS_KEY_ID: str = ""
    PRODUCT_IMAGE_S3_SECRET_ACCESS_KEY: str = ""
    PRODUCT_IMAGE_S3_PUBLIC_BASE_URL: str = ""
    PRODUCT_IMAGE_S3_PREFIX: str = "produtos"
    PRODUCT_IMAGE_S3_USE_PATH_STYLE: bool = False
    PRODUCT_IMAGE_S3_PUBLIC_READ: bool = False

    # SEFAZ (NF-e)
    SEFAZ_ENABLED: bool = False
    SEFAZ_MODO: str = "mock"  # mock | real
    SEFAZ_AMBIENTE: str = "homologacao"  # homologacao | producao
    SEFAZ_UF: str = ""
    SEFAZ_CNPJ: str = ""
    SEFAZ_CERT_PATH: str = ""
    SEFAZ_CERT_PASSWORD: str = ""
    SEFAZ_TIMEOUT_SECONDS: int = 30
    SEFAZ_IMPORTACAO_AUTOMATICA: bool = False
    SEFAZ_IMPORTACAO_INTERVALO_MIN: int = 15
    SEFAZ_ULTIMO_NSU: str = "000000000000000"

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
PRODUCT_IMAGE_STORAGE_BACKEND = settings.PRODUCT_IMAGE_STORAGE_BACKEND
PRODUCT_IMAGE_LOCAL_BASE_DIR = settings.PRODUCT_IMAGE_LOCAL_BASE_DIR
PRODUCT_IMAGE_UPLOAD_MAX_BYTES = settings.PRODUCT_IMAGE_UPLOAD_MAX_BYTES
PRODUCT_IMAGE_MAX_DIMENSION = settings.PRODUCT_IMAGE_MAX_DIMENSION
PRODUCT_IMAGE_THUMBNAIL_SIZE = settings.PRODUCT_IMAGE_THUMBNAIL_SIZE
PRODUCT_IMAGE_WEBP_QUALITY = settings.PRODUCT_IMAGE_WEBP_QUALITY
PRODUCT_IMAGE_S3_BUCKET = settings.PRODUCT_IMAGE_S3_BUCKET
PRODUCT_IMAGE_S3_REGION = settings.PRODUCT_IMAGE_S3_REGION
PRODUCT_IMAGE_S3_ENDPOINT_URL = settings.PRODUCT_IMAGE_S3_ENDPOINT_URL
PRODUCT_IMAGE_S3_ACCESS_KEY_ID = settings.PRODUCT_IMAGE_S3_ACCESS_KEY_ID
PRODUCT_IMAGE_S3_SECRET_ACCESS_KEY = settings.PRODUCT_IMAGE_S3_SECRET_ACCESS_KEY
PRODUCT_IMAGE_S3_PUBLIC_BASE_URL = settings.PRODUCT_IMAGE_S3_PUBLIC_BASE_URL
PRODUCT_IMAGE_S3_PREFIX = settings.PRODUCT_IMAGE_S3_PREFIX
PRODUCT_IMAGE_S3_USE_PATH_STYLE = settings.PRODUCT_IMAGE_S3_USE_PATH_STYLE
PRODUCT_IMAGE_S3_PUBLIC_READ = settings.PRODUCT_IMAGE_S3_PUBLIC_READ
SEFAZ_ENABLED = settings.SEFAZ_ENABLED
SEFAZ_MODO = settings.SEFAZ_MODO
SEFAZ_AMBIENTE = settings.SEFAZ_AMBIENTE
SEFAZ_UF = settings.SEFAZ_UF
SEFAZ_CNPJ = settings.SEFAZ_CNPJ
SEFAZ_CERT_PATH = settings.SEFAZ_CERT_PATH
SEFAZ_CERT_PASSWORD = settings.SEFAZ_CERT_PASSWORD
SEFAZ_TIMEOUT_SECONDS = settings.SEFAZ_TIMEOUT_SECONDS
SEFAZ_IMPORTACAO_AUTOMATICA = settings.SEFAZ_IMPORTACAO_AUTOMATICA
SEFAZ_IMPORTACAO_INTERVALO_MIN = settings.SEFAZ_IMPORTACAO_INTERVALO_MIN
SEFAZ_ULTIMO_NSU = settings.SEFAZ_ULTIMO_NSU
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
    print(f"PRODUCT_IMAGE_STORAGE_BACKEND={PRODUCT_IMAGE_STORAGE_BACKEND}")
    print("==========================")
