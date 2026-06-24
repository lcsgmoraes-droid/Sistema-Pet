import os


RESET_TOKEN_MINUTES = 30
EMAIL_VERIFICATION_TOKEN_HOURS = int(os.getenv("EMAIL_VERIFICATION_TOKEN_HOURS", "24"))
EMAIL_VERIFICATION_REQUIRED = os.getenv(
    "EMAIL_VERIFICATION_REQUIRED", "true"
).strip().lower() not in {"0", "false", "no"}
TERMS_VERSION = os.getenv("TERMS_VERSION", "termos-2026-05-08")
PRIVACY_VERSION = os.getenv("PRIVACY_VERSION", "privacidade-2026-05-08")
