from __future__ import annotations

import os
from urllib.parse import urlsplit, urlunsplit

import psycopg2


def required_env(*names: str) -> str:
    for name in names:
        value = os.getenv(name)
        if value:
            return value

    joined = " ou ".join(names)
    raise RuntimeError(f"Defina {joined} antes de executar este script.")


def database_url_from_env(*names: str) -> str:
    return required_env(*names)


def connect_database(*names: str):
    return psycopg2.connect(database_url_from_env(*names))


def masked_database_url(url: str) -> str:
    parts = urlsplit(url)
    secret = parts.password
    if not secret:
        return url

    netloc = parts.netloc.replace(f":{secret}@", ":***@")
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))
