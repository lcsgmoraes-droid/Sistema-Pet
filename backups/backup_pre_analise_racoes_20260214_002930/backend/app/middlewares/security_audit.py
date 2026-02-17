"""
Security Audit Middleware - Detecção de Ataques
================================================

Detecta e loga tentativas de:
- SQL Injection
- XSS (Cross-Site Scripting)
- Path Traversal
- Command Injection

IMPORTANTE: Este middleware apenas LOGA os ataques.
A PROTEÇÃO real vem de:
- Pydantic validation (rejeita payloads inválidos)
- SQLAlchemy ORM (parametrização previne SQL injection)
- FastAPI type hints (validação de tipos)
"""

import logging
import re
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from typing import List, Tuple
from urllib.parse import unquote


logger = logging.getLogger(__name__)


# ============================================================================
# PADRÕES DE ATAQUE (REGEX)
# ============================================================================

# SQL Injection patterns
SQL_INJECTION_PATTERNS = [
    r"(\bOR\b\s+\d+\s*=\s*\d+)",  # OR 1=1
    r"(\bUNION\b.*\bSELECT\b)",   # UNION SELECT
    r"(\bDROP\b.*\bTABLE\b)",     # DROP TABLE
    r"(--\s*$)",                   # SQL comment
    r"(/\*.*\*/)",                 # SQL block comment
    r"(\bEXEC\b.*\()",            # EXEC(
    r"(';.*--)",                   # '; --
    r"(\bDELETE\b.*\bFROM\b)",    # DELETE FROM
]

# XSS patterns
XSS_PATTERNS = [
    r"(<script[^>]*>.*?</script>)",              # <script>
    r"(<iframe[^>]*>)",                           # <iframe>
    r"(<object[^>]*>)",                           # <object>
    r"(<embed[^>]*>)",                            # <embed>
    r"(javascript:)",                             # javascript:
    r"(onerror\s*=)",                             # onerror=
    r"(onload\s*=)",                              # onload=
    r"(<img[^>]*onerror[^>]*>)",                 # <img onerror=>
    r"(<svg[^>]*onload[^>]*>)",                  # <svg onload=>
]

# Path Traversal patterns
PATH_TRAVERSAL_PATTERNS = [
    r"(\.\./)",                    # ../
    r"(\.\.\\)",                   # ..\
    r"(%2e%2e/)",                  # URL encoded ../
    r"(%2e%2e\\)",                 # URL encoded ..\
    r"(\.\.%2f)",                  # ..%2f
    r"(\.\.%5c)",                  # ..%5c
]

# Command Injection patterns
COMMAND_INJECTION_PATTERNS = [
    r"(;\s*\w+)",                  # ; command
    r"(\|\s*\w+)",                 # | command
    r"(&\s*\w+)",                  # & command
    r"(`.*`)",                     # `command`
    r"(\$\(.*\))",                 # $(command)
]


def compile_patterns(patterns: List[str]) -> List[re.Pattern]:
    """Compila lista de regex patterns"""
    return [re.compile(pattern, re.IGNORECASE) for pattern in patterns]


SQL_INJECTION_REGEX = compile_patterns(SQL_INJECTION_PATTERNS)
XSS_REGEX = compile_patterns(XSS_PATTERNS)
PATH_TRAVERSAL_REGEX = compile_patterns(PATH_TRAVERSAL_PATTERNS)
COMMAND_INJECTION_REGEX = compile_patterns(COMMAND_INJECTION_PATTERNS)


# ============================================================================
# DETECTOR DE ATAQUES
# ============================================================================

class AttackDetector:
    """Detecta padrões maliciosos em strings"""
    
    @staticmethod
    def detect_sql_injection(value: str) -> Tuple[bool, str]:
        """Detecta SQL Injection"""
        for pattern in SQL_INJECTION_REGEX:
            if pattern.search(value):
                return True, pattern.pattern
        return False, ""
    
    @staticmethod
    def detect_xss(value: str) -> Tuple[bool, str]:
        """Detecta XSS"""
        for pattern in XSS_REGEX:
            if pattern.search(value):
                return True, pattern.pattern
        return False, ""
    
    @staticmethod
    def detect_path_traversal(value: str) -> Tuple[bool, str]:
        """Detecta Path Traversal"""
        for pattern in PATH_TRAVERSAL_REGEX:
            if pattern.search(value):
                return True, pattern.pattern
        return False, ""
    
    @staticmethod
    def detect_command_injection(value: str) -> Tuple[bool, str]:
        """Detecta Command Injection"""
        for pattern in COMMAND_INJECTION_REGEX:
            if pattern.search(value):
                return True, pattern.pattern
        return False, ""
    
    @classmethod
    def scan(cls, value: str) -> List[Tuple[str, str]]:
        """
        Escaneia valor por todos os tipos de ataque.
        
        Returns:
            List[(attack_type, matched_pattern), ...]
        """
        attacks = []
        
        # SQL Injection
        detected, pattern = cls.detect_sql_injection(value)
        if detected:
            attacks.append(("SQL_INJECTION", pattern))
        
        # XSS
        detected, pattern = cls.detect_xss(value)
        if detected:
            attacks.append(("XSS", pattern))
        
        # Path Traversal
        detected, pattern = cls.detect_path_traversal(value)
        if detected:
            attacks.append(("PATH_TRAVERSAL", pattern))
        
        # Command Injection
        detected, pattern = cls.detect_command_injection(value)
        if detected:
            attacks.append(("COMMAND_INJECTION", pattern))
        
        return attacks


# ============================================================================
# MIDDLEWARE DE AUDITORIA DE SEGURANÇA
# ============================================================================

class SecurityAuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware que detecta e loga tentativas de ataque.
    
    IMPORTANTE:
    - Não bloqueia requisições (apenas loga)
    - Proteção real vem de Pydantic/SQLAlchemy
    - Útil para auditoria e alertas de segurança
    """
    
    async def dispatch(self, request: Request, call_next):
        # Extrair dados da requisição
        path = request.url.path
        query_params = dict(request.query_params)
        client_ip = request.client.host if request.client else "unknown"
        
        # Escanear query parameters
        attacks_found = []
        for param_name, param_value in query_params.items():
            if param_value:
                # URL decode para detectar payloads encoded
                decoded_value = unquote(str(param_value))
                
                # Detectar ataques
                attacks = AttackDetector.scan(decoded_value)
                
                if attacks:
                    attacks_found.extend([
                        {
                            "type": attack_type,
                            "pattern": pattern,
                            "param": param_name,
                            "value": decoded_value[:100]  # Limitar tamanho do log
                        }
                        for attack_type, pattern in attacks
                    ])
        
        # Escanear path parameters (ex: /user/../../etc/passwd)
        decoded_path = unquote(path)
        path_attacks = AttackDetector.scan(decoded_path)
        if path_attacks:
            attacks_found.extend([
                {
                    "type": attack_type,
                    "pattern": pattern,
                    "param": "path",
                    "value": decoded_path[:100]
                }
                for attack_type, pattern in path_attacks
            ])
        
        # Logar ataques detectados
        if attacks_found:
            logger.warning(
                f"🚨 SECURITY ALERT: {len(attacks_found)} attack(s) detected",
                extra={
                    "security_event": True,
                    "client_ip": client_ip,
                    "path": path,
                    "method": request.method,
                    "attacks": attacks_found,
                    "user_agent": request.headers.get("user-agent", ""),
                }
            )
            
            # Log estruturado para SIEM
            from app.utils.logger import logger as structured_logger
            structured_logger.warning(
                event="security_attack_detected",
                message=f"Detected {len(attacks_found)} potential attack(s)",
                client_ip=client_ip,
                path=path,
                method=request.method,
                attacks=attacks_found,
                user_agent=request.headers.get("user-agent", "")
            )
        
        # Continuar processamento (Pydantic vai rejeitar se inválido)
        response = await call_next(request)
        return response
