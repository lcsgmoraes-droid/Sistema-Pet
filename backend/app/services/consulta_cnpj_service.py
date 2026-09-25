"""Consulta cadastral de CNPJ com fontes públicas e fallback."""

from collections import deque
from threading import Lock
from time import monotonic

import httpx

from app.utils.logger import logger


class CnpjInvalido(ValueError):
    pass


class CnpjNaoEncontrado(Exception):
    pass


class ConsultaCnpjIndisponivel(Exception):
    pass


_CACHE_TTL_SECONDS = 3600
_CACHE_MAX_ITEMS = 512
_FALLBACK_LIMIT = 3
_FALLBACK_WINDOW_SECONDS = 60
_cache: dict[str, tuple[float, dict]] = {}
_fallback_calls: deque[float] = deque()
_lock = Lock()


def _validar_cnpj(cnpj: str) -> str:
    numero = "".join(char for char in cnpj if char.isdigit())
    if len(numero) != 14 or len(set(numero)) == 1:
        raise CnpjInvalido("CNPJ inválido. Confira os 14 dígitos.")

    for tamanho, pesos in (
        (12, (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)),
        (13, (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)),
    ):
        resto = sum(int(numero[i]) * peso for i, peso in enumerate(pesos)) % 11
        digito = 0 if resto < 2 else 11 - resto
        if int(numero[tamanho]) != digito:
            raise CnpjInvalido("CNPJ inválido. Confira os dígitos verificadores.")
    return numero


def _normalizar_minha_receita(dados: dict) -> dict:
    campos = (
        "cnpj",
        "razao_social",
        "nome_fantasia",
        "email",
        "ddd_telefone_1",
        "cep",
        "logradouro",
        "numero",
        "complemento",
        "bairro",
        "municipio",
        "codigo_municipio_ibge",
        "uf",
        "cnae_fiscal",
        "cnae_fiscal_descricao",
        "cnaes_secundarios",
    )
    return {campo: dados.get(campo) for campo in campos}


def _normalizar_cnpj_ws(dados: dict) -> dict:
    estabelecimento = dados.get("estabelecimento") or {}
    atividade = estabelecimento.get("atividade_principal") or {}
    cidade = estabelecimento.get("cidade") or {}
    estado = estabelecimento.get("estado") or {}
    secundarias = estabelecimento.get("atividades_secundarias") or []
    return {
        "cnpj": estabelecimento.get("cnpj"),
        "razao_social": dados.get("razao_social"),
        "nome_fantasia": estabelecimento.get("nome_fantasia"),
        "email": estabelecimento.get("email"),
        "ddd_telefone_1": "".join(
            filter(
                None, (estabelecimento.get("ddd1"), estabelecimento.get("telefone1"))
            )
        ),
        "cep": estabelecimento.get("cep"),
        "logradouro": estabelecimento.get("logradouro"),
        "numero": estabelecimento.get("numero"),
        "complemento": estabelecimento.get("complemento"),
        "bairro": estabelecimento.get("bairro"),
        "municipio": cidade.get("nome"),
        "codigo_municipio_ibge": cidade.get("ibge_id"),
        "uf": estado.get("sigla"),
        "cnae_fiscal": atividade.get("id"),
        "cnae_fiscal_descricao": atividade.get("descricao"),
        "cnaes_secundarios": [
            {"codigo": item.get("id"), "descricao": item.get("descricao")}
            for item in secundarias
            if isinstance(item, dict)
        ],
    }


def _permitir_fallback() -> bool:
    agora = monotonic()
    with _lock:
        while (
            _fallback_calls and agora - _fallback_calls[0] >= _FALLBACK_WINDOW_SECONDS
        ):
            _fallback_calls.popleft()
        if len(_fallback_calls) >= _FALLBACK_LIMIT:
            return False
        _fallback_calls.append(agora)
        return True


def consultar_cnpj(cnpj: str) -> dict:
    numero = _validar_cnpj(cnpj)
    agora = monotonic()
    with _lock:
        cached = _cache.get(numero)
        if cached and agora - cached[0] < _CACHE_TTL_SECONDS:
            return cached[1].copy()
        _cache.pop(numero, None)

    fontes = (
        (
            "Minha Receita",
            f"https://minhareceita.org/{numero}",
            _normalizar_minha_receita,
        ),
        ("CNPJ.ws", f"https://publica.cnpj.ws/cnpj/{numero}", _normalizar_cnpj_ws),
    )
    nao_encontrado = 0
    with httpx.Client(timeout=8.0, headers={"User-Agent": "CorePet/1.0"}) as client:
        for nome, url, normalizar in fontes:
            if nome == "CNPJ.ws" and not _permitir_fallback():
                logger.warning(
                    "Consulta CNPJ: limite preventivo da fonte reserva atingido"
                )
                continue
            try:
                resposta = client.get(url)
                if resposta.status_code == 404:
                    nao_encontrado += 1
                    continue
                resposta.raise_for_status()
                dados = normalizar(resposta.json())
                if dados.get("cnpj") != numero or not dados.get("razao_social"):
                    raise ValueError("Resposta cadastral incompleta ou de outro CNPJ")
            except (httpx.HTTPError, ValueError, TypeError, AttributeError) as exc:
                logger.warning(
                    "consulta_cnpj_falha",
                    f"Falha na fonte {nome}: {type(exc).__name__}",
                )
                continue

            with _lock:
                if len(_cache) >= _CACHE_MAX_ITEMS:
                    _cache.pop(next(iter(_cache)))
                _cache[numero] = (monotonic(), dados)
            return dados.copy()

    if nao_encontrado == len(fontes):
        raise CnpjNaoEncontrado("CNPJ não encontrado nas fontes cadastrais.")
    raise ConsultaCnpjIndisponivel(
        "As fontes de consulta de CNPJ estão indisponíveis no momento. Tente novamente mais tarde."
    )
