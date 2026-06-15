"""
Módulo de Criptografia - LGPD Compliance
Criptografa/descriptografa dados sensíveis
"""
from cryptography.fernet import Fernet
from app.config import ENCRYPTION_KEY
from app.utils.logger import logger

# Inicializar cipher se chave configurada
cipher = None
if ENCRYPTION_KEY:
    try:
        cipher = Fernet(ENCRYPTION_KEY.encode())
    except Exception as e:
        logger.info(f"⚠️  Erro ao inicializar criptografia: {e}")
        logger.info("💡 Gere uma nova chave com: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"")
else:
    logger.warning("⚠️  ENCRYPTION_KEY não configurada no .env. Criptografia desabilitada.")
    logger.info("💡 Gere uma chave com: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"")


def encrypt_data(data: str) -> str:
    """
    Criptografa dados sensíveis.
    
    Args:
        data: Dados em texto claro
        
    Returns:
        Dados criptografados (base64)
    """
    if not data or not cipher:
        return data
    
    try:
        return cipher.encrypt(data.encode()).decode()
    except Exception as e:
        logger.info(f"❌ Erro ao criptografar: {e}")
        return data  # Retorna original em caso de erro


def decrypt_data(encrypted_data: str) -> str:
    """
    Descriptografa dados sensíveis.
    
    Args:
        encrypted_data: Dados criptografados (base64)
        
    Returns:
        Dados em texto claro
    """
    if not encrypted_data or not cipher:
        return encrypted_data
    
    try:
        return cipher.decrypt(encrypted_data.encode()).decode()
    except Exception as e:
        logger.info(f"❌ Erro ao descriptografar: {e}")
        return encrypted_data  # Retorna original em caso de erro


def is_encryption_enabled() -> bool:
    """Verifica se criptografia está habilitada"""
    return cipher is not None
